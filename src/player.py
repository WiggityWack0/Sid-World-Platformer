"""
Player entity: movement state machine + feel (coyote time, jump buffer,
variable jump height, skid, crouch, i-frames).
"""

import pygame

from src import config
from src import physics


class Input:
    __slots__ = ("left", "right", "down", "jump_pressed", "jump_held", "run")

    def __init__(self):
        self.left = self.right = self.down = False
        self.jump_pressed = False
        self.jump_held = False
        self.run = False


# animation states
IDLE, RUN, SKID, JUMP, FALL, CROUCH, DEAD = (
    "idle", "run", "skid", "jump", "fall", "crouch", "dead")

# afterimage ghosts (Phase 5 T3): tint applied via BLEND_RGB_MULT to a
# frame copy, baked once per (frame, form) then alpha-frozen
GHOST_TINT = (150, 200, 255)     # neutral Sid ghost (cool blue)
GHOST_ALPHA = 72
GHOST_CACHE_MAX = 64             # pinned by test_balance_audit (Phase 6)
_GHOSTS = {}                     # (id(frame), form) -> tinted surface


class Player:
    W = config.PLAYER_W
    H = config.PLAYER_H
    CROUCH_H = config.PLAYER_CROUCH_H

    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.w = self.W
        self.h = self.H
        self.facing = 1
        self.on_ground = False
        self.coyote = 0
        self.buffer = 0
        self.jumped = False
        self.cut_done = False
        self.crouching = False
        self.invuln = 0
        self.max_hearts = config.HEARTS_START
        self.hearts = self.max_hearts
        self.active_powerup = None       # "star" | "speed" | "jump" | None
        self.powerup_timer = 0
        self.form = None                 # None (Sid) | fire | ice | lightning
        self.forms_unlocked = list(config.FORMS)
        self.attack_cooldown = 0
        self.dead = False
        self.death_timer = 0
        self.warp_freeze = 0
        self.state = IDLE
        self.anim_t = 0
        self._on_mover = None
        # visual-only juice (Phase 5): squash/stretch + afterimage trail.
        # NEVER touches rect/hitbox — draw transforms only.
        self.squash = 0                    # remaining ticks
        self.squash_total = 1              # for the decay ratio
        self.squash_kind = "land"          # land | stretch | stomp
        self.form_flash = 0                # trail window after a form swap
        self.trail = []                    # [(x, y, state, anim_t, facing)]
        self._trail_t = 0

    # ------------------------------------------------------------- helpers
    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    @property
    def feet_rect(self):
        r = self.rect
        return pygame.Rect(r.x, r.bottom - 4, r.w, 4)

    @property
    def cx(self):
        return self.x + self.w / 2

    @property
    def cy(self):
        return self.y + self.h / 2

    # ------------------------------------------------------- power-ups (2b)
    @property
    def star_active(self):
        return self.active_powerup == "star"

    @property
    def max_run(self):
        m = (config.POWERUP_SPEED_MULT
             if self.active_powerup == "speed" else 1.0)
        return config.MAX_RUN * m

    @property
    def max_walk(self):
        m = (config.POWERUP_SPEED_MULT
             if self.active_powerup == "speed" else 1.0)
        return config.MAX_WALK * m

    @property
    def jump_velocity(self):
        m = (config.POWERUP_JUMP_MULT
             if self.active_powerup == "jump" else 1.0)
        return config.JUMP_VELOCITY * m

    @property
    def gravity(self):
        m = (config.POWERUP_JUMP_GRAV_MULT
             if self.active_powerup == "jump" else 1.0)
        return config.GRAVITY * m

    @property
    def powerup_frac(self):
        """0..1 HUD bar fill for the active timed power-up."""
        if self.active_powerup is None:
            return 0.0
        return self.powerup_timer / config.POWERUP_DURATION

    def apply_powerup(self, kind):
        """Apply a pickup. Returns True for timed power-ups.

        Heart containers apply immediately (max HP +1 up to HEARTS_MAX,
        refill); the timed kinds set active_powerup + timer.
        """
        if kind == "heart":
            if self.max_hearts < config.HEARTS_MAX:
                self.max_hearts += 1
            self.hearts = self.max_hearts
            return False
        self.active_powerup = kind
        self.powerup_timer = config.POWERUP_DURATION
        return True

    # -------------------------------------------------------- forms (2c)
    def cycle_form(self):
        """F (D2): None -> each unlocked form -> None. Offensive only."""
        order = [None] + [f for f in config.FORMS if f in self.forms_unlocked]
        if self.form not in order:
            self.form = None
            self.form_flash = config.TRAIL_FORM_TICKS   # swap trail (T3)
            return self.form
        self.form = order[(order.index(self.form) + 1) % len(order)]
        self.form_flash = config.TRAIL_FORM_TICKS        # swap trail (T3)
        return self.form

    def set_squash(self, ticks, kind):
        """Start a visual squash/stretch (Phase 5 T2). Draw-only: the
        hitbox never changes."""
        self.squash = ticks
        self.squash_total = max(1, ticks)
        self.squash_kind = kind

    def queue_jump(self):
        self.buffer = config.JUMP_BUFFER_FRAMES

    def die(self, cause="enemy"):
        """Start the death sequence (Playing handles lives/respawn)."""
        if self.dead:
            return
        self.dead = True
        self.death_timer = config.DEATH_ANIM_FRAMES
        self.vy = -7.0
        self.vx = 0.0
        self.state = DEAD
        self.crouching = False
        self.h = self.H

    def damage(self, source_x):
        """Lose one heart of damage (D1). Returns True if the hit applied.

        Blocked while dead or within i-frames; knocks the player away from
        source_x; at zero hearts the normal death flow takes over.
        """
        if self.dead or self.invuln > 0:
            return False
        self.hearts -= 1
        self.invuln = config.HURT_INVULN
        if self.hearts <= 0:
            self.die("hp")
            return True
        self.vx = config.HURT_KNOCKBACK_X * (1 if self.cx >= source_x else -1)
        self.vy = config.HURT_KNOCKBACK_Y
        return True

    def respawn_at(self, x, y):
        self.x, self.y = float(x), float(y)
        self.vx = self.vy = 0.0
        self.dead = False
        self.death_timer = 0
        self.invuln = config.RESPAWN_INVULN
        self.hearts = self.max_hearts
        self.active_powerup = None
        self.powerup_timer = 0
        self.form = None
        self.attack_cooldown = 0
        self.crouching = False
        self.h = self.H
        self.on_ground = False
        self.state = FALL
        self.jumped = False
        self.cut_done = False
        self._on_mover = None
        self.squash = 0                      # juice resets (Phase 5)
        self.form_flash = 0
        del self.trail[:]

    def _set_crouch(self, value, level):
        if value and not self.crouching:
            self.y += self.H - self.CROUCH_H
            self.h = self.CROUCH_H
            self.crouching = True
        elif not value and self.crouching:
            self.y -= self.H - self.CROUCH_H
            self.h = self.H
            self.crouching = False

    def _head_blocked(self, level):
        r = pygame.Rect(int(self.x), int(self.y - (self.H - self.CROUCH_H)),
                        self.w, self.H)
        return level.tiles.any_solid_rect(r)


    # ------------------------------------------------------------- update
    def update(self, inp, level):
        """Advance one fixed tick. Returns a list of event tuples."""
        events = []
        movers = level.mover_rects()
        self.anim_t += 1
        if self.squash > 0:
            self.squash -= 1                # visual decay (Phase 5 T2)
        if self.form_flash > 0:
            self.form_flash -= 1
        if self.invuln > 0:
            self.invuln -= 1

        if self.dead:
            self.death_timer -= 1
            self.vy = physics.clamp_velocity(self.vy + config.GRAVITY)
            self.y += self.vy
            self.state = DEAD
            return events

        if self.powerup_timer > 0:
            self.powerup_timer -= 1
            if self.powerup_timer == 0:
                self.active_powerup = None

        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1

        if self.warp_freeze > 0:
            self.warp_freeze -= 1
            return events

        # carried by a moving platform from the previous tick
        if self._on_mover is not None:
            m = self._on_mover
            if m in level.movers and self.rect.bottom == m.rect.top \
                    and self.rect.right > m.rect.left \
                    and self.rect.left < m.rect.right:
                self.x += m.dx
                self.y += m.dy
            else:
                self._on_mover = None

        # ------------------------------------------------------- crouching
        if inp.down and self.on_ground and not self.crouching:
            self._set_crouch(True, level)
        elif self.crouching and not inp.down:
            if not self._head_blocked(level):
                self._set_crouch(False, level)

        # -------------------------------------------------- horizontal move
        direction = 0 if self.crouching else (
            (1 if inp.right else 0) - (1 if inp.left else 0))
        target = self.max_run if inp.run else self.max_walk
        accel = config.RUN_ACCEL if inp.run else config.WALK_ACCEL

        if direction != 0:
            self.facing = direction
            skidding = (self.vx * direction < -0.5 and abs(self.vx) > 1.2)
            if skidding:
                self.vx += direction * config.SKID_DECEL
            else:
                self.vx += direction * accel
            if abs(self.vx) > target:
                self.vx = target * (1 if self.vx > 0 else -1)
        else:
            if abs(self.vx) <= config.FRICTION:
                self.vx = 0.0
            else:
                self.vx -= config.FRICTION * (1 if self.vx > 0 else -1)

        # ---------------------------------------------------------- jumping
        if self.buffer > 0:
            self.buffer -= 1
        if self.on_ground:
            self.coyote = config.COYOTE_FRAMES
        elif self.coyote > 0:
            self.coyote -= 1

        if self.buffer > 0 and self.coyote > 0 and not self.crouching:
            self.vy = self.jump_velocity
            self.jumped = True
            self.cut_done = False
            self.buffer = 0
            self.coyote = 0
            self.on_ground = False
            self.set_squash(config.STRETCH_JUMP, "stretch")   # T2
        if (self.jumped and not inp.jump_held and self.vy < 0
                and not self.cut_done):
            self.vy *= config.JUMP_CUT_FACTOR
            self.cut_done = True

        # --------------------------------------------------------- integrate
        self.vy = physics.clamp_velocity(self.vy + self.gravity)

        new_x, hit = physics.move_x(
            self.x, self.y, self.w, self.h, self.vx, level)
        if hit != 0:
            self.vx = 0.0
        self.x = new_x

        new_y, landed, head_hit, surface = physics.move_y(
            self.x, self.y, self.w, self.h, self.vy, level,
            one_ways=movers)
        self.y = new_y
        self.on_ground = False
        if landed:
            impact = abs(self.vy)            # measured BEFORE the clamp
            self.vy = 0.0
            self.on_ground = True
            self.jumped = False
            self.cut_done = False
            if not self.crouching and impact >= 1.5:
                # land squash, proportional to fall speed, capped (T2)
                self.set_squash(max(3, min(config.SQUASH_LAND,
                                           int(impact))), "land")
            for m in level.movers:
                if surface is m.rect:
                    self._on_mover = m
                    break
        elif head_hit is not None:
            self.vy = 0.0
            if not any(head_hit is m.rect for m in level.movers):
                tx = head_hit.left // config.TILE
                ty = head_hit.top // config.TILE
                events.append(("bump", level.bump(tx, ty), tx, ty))

        # ------------------------------------------------------- hazards/pit
        if self.y > level.height:
            events.append(("pit",))
        elif level.overlaps_hazard(self.rect):
            events.append(("hazard",))

        self._update_state(inp)
        # afterimage trail sampling (Phase 5 T3): update-time, every N
        # ticks, so it is deterministic regardless of frame rate. Drains
        # when inactive so the ghosts fade out quickly. Speed-gated only —
        # no state==RUN clause (bugfix: the sprint blur used to vanish the
        # instant you jumped, because _update_state switches to JUMP/FALL
        # the moment you leave the ground). Airborne/crouch slides at run
        # speed now keep their afterimages; slowing down still drains.
        dashing = abs(self.vx) >= self.max_run * config.TRAIL_RUN_FRAC
        active = (dashing or self.form_flash > 0) and not self.dead
        self._trail_t += 1
        if self._trail_t % config.TRAIL_INTERVAL == 0:
            if active:
                self.trail.append((self.x, self.y, self.state,
                                   self.anim_t, self.facing))
                if len(self.trail) > config.TRAIL_LEN:
                    del self.trail[0]
            elif self.trail:
                self.trail.pop(0)
        return events

    def _update_state(self, inp):
        if self.dead:
            self.state = DEAD
            return
        if not self.on_ground:
            self.state = JUMP if self.vy < 0 else FALL
        elif self.crouching:
            self.state = CROUCH
        elif abs(self.vx) > 0.4:
            moving_left = self.vx < 0
            if (inp.left and not moving_left) or (inp.right and moving_left):
                self.state = SKID if abs(self.vx) > 1.4 else RUN
            else:
                self.state = RUN
        else:
            self.state = IDLE

    # --------------------------------------------------------------- draw
    def draw(self, surf, cam, assets, tick):
        if self.invuln > 0 and not self.dead and (tick // 3) % 2 == 0:
            return                                   # i-frame flicker
        # afterimage ghosts (Phase 5 T3): behind the player, tinted and
        # translucent — cached per (frame, form), never mutated after build
        for gx, gy, gstate, ganim, gfacing in self.trail:
            gframe = assets.player_frame(gstate, ganim, gfacing)
            key = (id(gframe), self.form)
            ghost = _GHOSTS.get(key)
            if ghost is None:
                ghost = gframe.copy()
                tint = (config.FORM_COLORS.get(self.form, GHOST_TINT)
                        if self.form else GHOST_TINT)
                ghost.fill(tint, special_flags=pygame.BLEND_RGB_MULT)
                ghost.set_alpha(GHOST_ALPHA)
                if len(_GHOSTS) >= GHOST_CACHE_MAX:
                    _GHOSTS.clear()
                _GHOSTS[key] = ghost
            surf.blit(ghost, (int(gx) - 2 - cam.ix, int(gy) - cam.iy))
        frame = assets.player_frame(self.state, self.anim_t, self.facing)
        bx, by = int(self.x) - 2, int(self.y)
        sx, sy = self._draw_scale()
        if (sx, sy) != (1.0, 1.0):
            # squash/stretch (Phase 5 T2): visual transform only, feet
            # stay planted (blit y compensates the height delta)
            w, h = frame.get_size()
            nw, nh = max(1, round(w * sx)), max(1, round(h * sy))
            frame = pygame.transform.scale(frame, (nw, nh))
            bx -= (nw - w) // 2               # keep horizontally centered
            by -= (nh - h)                    # feet anchored
        surf.blit(frame, (bx - cam.ix, by - cam.iy))

    def _draw_scale(self):
        """(sx, sy) for the current squash window; (1.0, 1.0) when idle."""
        if self.squash <= 0:
            return 1.0, 1.0
        k = self.squash / float(self.squash_total)
        if self.squash_kind == "stretch":
            return 1.0 - 0.18 * k, 1.0 + 0.22 * k   # tall & narrow
        if self.squash_kind == "stomp":
            return 1.0 + 0.28 * k, 1.0 - 0.24 * k   # big flat impact
        return 1.0 + 0.22 * k, 1.0 - 0.18 * k       # land squash
