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
        self.dead = False
        self.death_timer = 0
        self.warp_freeze = 0
        self.state = IDLE
        self.anim_t = 0
        self._on_mover = None

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

    def respawn_at(self, x, y):
        self.x, self.y = float(x), float(y)
        self.vx = self.vy = 0.0
        self.dead = False
        self.death_timer = 0
        self.invuln = config.RESPAWN_INVULN
        self.crouching = False
        self.h = self.H
        self.on_ground = False
        self.state = FALL
        self.jumped = False
        self.cut_done = False
        self._on_mover = None

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
        if self.invuln > 0:
            self.invuln -= 1

        if self.dead:
            self.death_timer -= 1
            self.vy = physics.clamp_velocity(self.vy + config.GRAVITY)
            self.y += self.vy
            self.state = DEAD
            return events

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
        target = config.MAX_RUN if inp.run else config.MAX_WALK
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
            self.vy = config.JUMP_VELOCITY
            self.jumped = True
            self.cut_done = False
            self.buffer = 0
            self.coyote = 0
            self.on_ground = False
        if (self.jumped and not inp.jump_held and self.vy < 0
                and not self.cut_done):
            self.vy *= config.JUMP_CUT_FACTOR
            self.cut_done = True

        # --------------------------------------------------------- integrate
        self.vy = physics.clamp_velocity(self.vy + config.GRAVITY)

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
            self.vy = 0.0
            self.on_ground = True
            self.jumped = False
            self.cut_done = False
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
        frame = assets.player_frame(self.state, self.anim_t, self.facing)
        surf.blit(frame, (int(self.x) - 2 - cam.x, int(self.y) - cam.y))
