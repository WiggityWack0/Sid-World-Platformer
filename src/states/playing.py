"""Core gameplay state: level, player, enemies, combat, items, camera."""

import pygame

from src import inputs
from src import progress as progress_mod
from src.config import (AMBIENT_INTERVAL, ATTACK_COOLDOWN, BREAK_SCORE,
                        COIN_CLEAR_BONUS,
                        COIN_SCORE, COINS_PER_LIFE, FORM_KILL_SCORE,
                        FX_HURT, FX_ICE_TINT, HURT_TRAUMA,
                        ICE_FREEZE_TICKS, KICK_SCORE, LIGHTNING_MAX_TARGETS,
                        LIGHTNING_RADIUS,
                        PLAYER_H, PRIMER_TICKS, RUN_DUST_INTERVAL,
                        SHARD_SCORE,
                        SHAKE_DEATH, STAR_KILL_SCORE, TILE,
                        STOMP_BOUNCE, STOMP_BOUNCE_HOLD,
                        STOMP_SCORE, START_TIME, TIME_BONUS_PER_UNIT,
                        TIME_INTERVAL_FRAMES, VIEW_H, VIEW_W, ZONES,
                        WARP_ENTER_FRAMES, difficulty_for, zone_level_of,
                        zone_of)
from src.attacks import AttackProjectile
from src.camera import Camera
from src.enemies import contact_result
from src.enemy_manager import EnemyManager
from src.level.validator import ensure_level
from src.player import RUN, Input, Player
from src.states.base import State


class PlayingState(State):
    name = "playing"

    # ------------------------------------------------------------ lifecycle
    def on_enter(self, **kwargs):
        run = self.game.run
        seed = run.seed + run.level_index * 1000003
        difficulty = difficulty_for(run.level_index)
        self.level = ensure_level(seed, difficulty, run.level_index)
        self.player = Player(*self.level.spawn)
        self.camera = Camera(self.level.width, self.level.height)
        self.camera.snap_to(self.player.rect)
        self.enemies = EnemyManager(self.level.enemy_spawns)
        self.respawn = self.level.spawn
        self.time_left = START_TIME
        self.timer_ticks = 0
        self.level_coins = 0
        self.warp_hold = 0
        self.was_jumped = False
        self.attacks = []                 # player projectiles (2c)
        self._ambient_t = 0               # zone ambient particle cadence (4b)
        self._lock_msg_cd = 0             # throttle for locked-goal hints
        self._boss = None                 # tracked boss (5b; None until spawn)
        self._boss_seen = False           # intro banner + music once
        self._banner_t = 0                # WARNING banner countdown
        self._cleared = False
        self.game.playing = self
        self._primer_t = 0                # zone-primer banner (6c)
        self._tutorial_t = 0              # tutorial hint cadence (6c)
        self._start_zone_primer()
        self.game.audio.play_music(self._music_for_level())

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN or event.key == pygame.K_m:
            return
        action = inputs.key_to_action(event.key)
        if action == "jump":
            self.player.queue_jump()
        elif action == "attack":
            self._try_attack()
        elif action == "form":
            name = self.player.cycle_form()
            self.game.audio.play_sfx("select")
            self.game.fx.floater(self.player.cx, self.player.cy - 26,
                                 (name or "SID").upper())
        elif action == "pause" or event.key == pygame.K_ESCAPE:
            self.game.pause()
        elif event.key == pygame.K_r:
            self.game.audio.play_sfx("select")
            self.game.switch_state("playing")

    # -------------------------------------------------------------- helpers
    def _music_for_level(self):
        """Zone track pair: early zone levels use music_a, late music_b."""
        zone = ZONES[zone_of(self.game.run.level_index)]
        return (zone["music_a"] if zone_level_of(self.game.run.level_index) < 3
                else zone["music_b"])

    def _add_coin(self):
        run = self.game.run
        run.coins += 1
        self.level_coins += 1
        run.score += COIN_SCORE
        self.game.fx.coin_burst(self.player.cx, self.player.cy - 8)
        self.game.fx.floater(self.player.cx, self.player.cy - 18, "+100")
        if run.coins >= COINS_PER_LIFE:
            run.coins -= COINS_PER_LIFE
            run.lives += 1
            # slightly higher than the +100 so the two texts never overlap
            self.game.fx.floater(self.player.cx, self.player.cy - 28, "1-UP")
            self.game.audio.play_sfx("one_up")
        else:
            self.game.audio.play_sfx("coin")

    def _kill(self, cause):
        if self.player.dead:
            return
        self.player.die(cause)
        self.game.fx.explosion(self.player.cx, self.player.cy)
        self.game.fx.add_trauma(SHAKE_DEATH)
        self.game.audio.stop_music(fade=80)
        self.game.audio.play_sfx("death")

    def _hurt(self, source_x):
        """One heart of damage with feedback (D1); no-op during i-frames."""
        if not self.player.damage(source_x):
            return
        g = self.game
        g.fx.floater(self.player.cx, self.player.cy - 18, "-1", FX_HURT)
        g.fx.add_trauma(HURT_TRAUMA)
        g.audio.play_sfx("hurt")

    def _respawn(self):
        self.player.respawn_at(*self.respawn)
        self.enemies.reset()
        self.attacks = []
        self.camera.snap_to(self.player.rect)
        self.warp_hold = 0
        self.game.audio.play_music(self._music_for_level())

    def _clear_level(self):
        if self._cleared:
            return
        self._cleared = True
        run = self.game.run
        time_bonus = self.time_left * TIME_BONUS_PER_UNIT
        coin_bonus = self.level_coins * COIN_CLEAR_BONUS
        run.score += time_bonus + coin_bonus
        self.game.audio.play_music("clear")
        self.game.switch_state(
            "level_clear",
            time_left=self.time_left,
            time_bonus=time_bonus,
            coin_bonus=coin_bonus)

    # -------------------------------------------------------------- update
    def update(self):
        run = self.game.run
        player = self.player
        fx = self.game.fx
        self.camera.set_shake(*fx.shake_offset())
        self.level.update()
        self._tutorial_t += 1
        self._tutorial_tick()
        if self._primer_t > 0:
            self._primer_t -= 1
        self._ambient_t += 1
        if self._ambient_t % AMBIENT_INTERVAL == 0:
            fx.ambient(ZONES[zone_of(run.level_index)]["ambient"],
                       self.camera)
        if self._lock_msg_cd > 0:
            self._lock_msg_cd -= 1

        if player.dead:
            player.update(Input(), self.level)
            if player.death_timer <= 0:
                run.lives -= 1
                if run.lives < 0:
                    self.game.audio.play_music("game_over")
                    self.game.switch_state("game_over")
                else:
                    self._respawn()
            return

        inp = Input()
        inp.left = inputs.action_held("left")
        inp.right = inputs.action_held("right")
        inp.down = inputs.action_held("down")
        inp.run = inputs.action_held("run")
        inp.jump_held = inputs.action_held("jump")

        was_grounded = player.on_ground
        events = player.update(inp, self.level)
        if player.jumped and not self.was_jumped:
            self.game.audio.play_sfx("jump")
        self.was_jumped = player.jumped

        if player.on_ground and not was_grounded and not player.dead:
            fx.dust(player.cx, player.rect.bottom)
        if (player.on_ground and player.state == RUN
                and abs(player.vx) > 0.5
                and self.game.tick % RUN_DUST_INTERVAL == 0):
            fx.dust(player.cx - 4 * player.facing, player.rect.bottom)

        for ev in events:
            if ev[0] == "bump":
                if ev[1] == "coin":
                    self._add_coin()
                elif ev[1] == "break":
                    run.score += BREAK_SCORE
                    self.game.audio.play_sfx("brick")
                    fx.debris(ev[2] * TILE + TILE // 2,
                              ev[3] * TILE + TILE // 2)
                elif ev[1] == "hit":
                    self.game.audio.play_sfx("bump")
            elif ev[0] == "pit":
                self._kill(ev[0])
            elif ev[0] == "hazard":
                if self.level.overlaps_lethal(player.rect):
                    self._kill("lava")      # lava is lethal (3b-1)
                else:
                    self._hurt(player.cx)   # spikes hurt; i-frames escape

        self.enemies.update(self.level, player, self.camera)
        self._boss_tick()
        self._update_attacks()
        self._combat(inp)
        if player.dead:
            return
        self._items()
        self._warp(inp)
        self._timer()
        self.camera.update(player.rect)

    # ------------------------------------------------------ forms (2c)
    def _try_attack(self):
        """C (D2): form-dependent attack; no-op as Sid or on cooldown."""
        player = self.player
        if player.dead or player.attack_cooldown > 0 or player.form is None:
            return
        player.attack_cooldown = ATTACK_COOLDOWN
        g = self.game
        if player.form == "lightning":
            self._lightning()
            return
        x = player.cx - 4 + player.facing * 8
        y = player.cy - 4
        self.attacks.append(
            AttackProjectile(player.form, x, y, player.facing))
        g.audio.play_sfx("kick")

    def _lightning(self):
        """Instant zap: up to LIGHTNING_MAX_TARGETS in range die."""
        player = self.player
        g = self.game
        targets = sorted(self.enemies.living(),
                         key=lambda e: abs(e.cx - player.cx)
                         + abs(e.cy - player.cy))
        zapped = 0
        for enemy in targets:
            if zapped >= LIGHTNING_MAX_TARGETS:
                break
            if (abs(enemy.cx - player.cx) <= LIGHTNING_RADIUS
                    and abs(enemy.cy - player.cy) <= LIGHTNING_RADIUS):
                if getattr(enemy, "is_boss", False):
                    killed = enemy.take_damage(1)   # HP pool (5b)
                else:
                    enemy.start_dying()   # elemental: beats STOMP_PROOF
                    killed = True
                if killed:
                    g.run.score += FORM_KILL_SCORE
                g.fx.spark(enemy.rect.centerx, enemy.rect.centery)
                zapped += 1
        if zapped:
            g.audio.play_sfx("stomp")

    def _attack_kill(self, enemy):
        """Elemental/star kill path (2d matrix): burns everything but
        STOMP_PROOF enemies (those deflect the hit). Returns True on kill.
        Bosses (5b) have an HP pool — damage, never instakill."""
        if enemy.STOMP_PROOF:
            return False
        if getattr(enemy, "is_boss", False):
            return enemy.take_damage(1)
        enemy.start_dying()
        return True

    def _start_zone_primer(self):
        """Zone primer banner (6c): once per zone per RUN, pure tick math."""
        run = self.game.run
        zone = zone_of(run.level_index)
        if zone not in run.zones_seen:
            run.zones_seen.add(zone)
            self._primer_t = PRIMER_TICKS

    def _tutorial_tick(self):
        """First-time tutorial hints (6c): persisted in `tutorial_seen`,
        gated by the options toggle; shown as a rising floater (no new
        banner state). Deterministic — no RNG."""
        prog = self.game.progress
        if not prog["settings"].get("tutorial_enabled", True):
            return
        seen = prog["tutorial_seen"]
        lvl = self.level
        key = text = None
        delay = 45
        if lvl.level_index == 0:
            key, text = "jump", "Z/SPACE JUMP   X RUN   C ATTACK"
        elif lvl.switches and "switch" not in seen:
            key, text = "switch", "HIT SWITCHES TO OPEN DOORS"
            delay = 30
        elif lvl.key_shards and "shard" not in seen:
            key, text = "shard", f"COLLECT {lvl.required} KEYS TO OPEN GOAL"
            delay = 30
        if key is None or key in seen:
            return
        if self._tutorial_t >= delay:
            seen.append(key)
            progress_mod.save(prog)
            self.game.fx.floater(self.player.cx, self.player.y - 24,
                                 text)

    def _boss_tick(self):
        """Boss framework hook (5b): intro banner/music, defeat explosions,
        goal unlock. Duck-typed via `is_boss` — no isinstance dispatch."""
        from src.config import BOSS_BANNER_TICKS
        lvl = self.level
        g = self.game
        boss = None
        for e in self.enemies.enemies:
            if getattr(e, "is_boss", False):
                boss = e
                break
        self._boss = boss
        if boss is None:
            return
        if boss.state == "dying":
            if boss.defeat_timer > 0 and boss.defeat_timer % 15 == 0:
                step = boss.defeat_timer // 15
                g.fx.explosion(boss.rect.centerx + ((step % 3) - 1) * 12,
                               boss.rect.centery + ((step % 2) * 10 - 5))
                g.audio.play_sfx("kick", vol=0.6)
            if boss.defeated and lvl.boss_required and not lvl.boss_defeated:
                lvl.boss_defeated = True
                stats = g.progress.setdefault("play_stats", {})   # 6b
                stats["bosses_defeated"] = stats.get("bosses_defeated",
                                                     0) + 1
                progress_mod.save(g.progress)
                g.fx.floater(lvl.goal.rect.centerx, lvl.goal.rect.top - 14,
                             "GOAL OPEN!")
                g.fx.add_trauma(0.4)
                g.audio.play_sfx("checkpoint")
                g.audio.play_music(self._music_for_level())
        elif boss.active and not self._boss_seen:
            self._boss_seen = True
            self._banner_t = BOSS_BANNER_TICKS
            g.audio.play_music("boss")
        if self._banner_t > 0:
            self._banner_t -= 1

    def _update_attacks(self):
        """Tick player projectiles (2d matrix).

        fire  -> kills via _attack_kill (deflects off STOMP_PROOF), despawns
        ice   -> freezes, despawns
        either -> mutual destruction with enemy projectiles
        """
        if not self.attacks:
            return
        for atk in self.attacks:
            atk.update(self.level)
            for enemy in self.enemies.living():
                if atk.rect.colliderect(enemy.rect):
                    if atk.kind == "ice":
                        enemy.frozen = ICE_FREEZE_TICKS
                        self.game.fx.spark(enemy.rect.centerx,
                                           enemy.rect.centery)
                        self.game.audio.play_sfx("bump")
                    elif self._attack_kill(enemy):
                        self.game.audio.play_sfx("kick")
                    else:
                        self.game.audio.play_sfx("bump")   # deflect
                    atk.life = 0
                    break
            else:
                for proj in self.enemies.projectiles:
                    if atk.rect.colliderect(proj.rect):
                        proj.life = 0                      # both despawn
                        atk.life = 0
                        self.game.fx.spark(proj.rect.centerx,
                                           proj.rect.centery)
                        break
        self.attacks = [a for a in self.attacks if not a.dead]

    def _combat(self, inp):
        player = self.player
        run = self.game.run
        for enemy in self.enemies.living():
            result = contact_result(player, enemy)
            if result == "stomp":
                outcome = enemy.stomped(player)
                if outcome:
                    player.vy = (STOMP_BOUNCE_HOLD if inp.jump_held
                                 else STOMP_BOUNCE)
                    player.jumped = True
                    player.cut_done = False
                    if outcome == "kick":
                        run.score += KICK_SCORE
                        self.game.audio.play_sfx("kick")
                    elif outcome == "bounce":
                        # blocked stomp (Shieldkin shield): bounce with
                        # feedback, but NO kill and NO score (5a)
                        self.game.audio.play_sfx("bounce")
                    else:
                        run.score += STOMP_SCORE
                        self.game.audio.play_sfx("stomp")
                        self.game.audio.play_sfx("bounce")
                    self.game.fx.stomp_puff(enemy.rect.centerx,
                                            enemy.rect.bottom)
            elif result == "hurt":
                if player.star_active and self._attack_kill(enemy):
                    # star: contact kills (no damage, stomp branch untouched)
                    run.score += STAR_KILL_SCORE
                    self.game.audio.play_sfx("kick")
                    self.game.fx.explosion(enemy.rect.centerx,
                                           enemy.rect.bottom - 6)
                    self.game.fx.floater(enemy.rect.centerx, enemy.rect.top,
                                         str(STAR_KILL_SCORE))
                    continue
                outcome = enemy.side_contact(player)
                if outcome == "kicked":
                    run.score += KICK_SCORE
                    self.game.audio.play_sfx("kick")
                else:
                    self._hurt(enemy.rect.centerx)
                    return
        for proj in self.enemies.projectiles:
            if proj.rect.colliderect(player.rect):
                proj.life = 0
                self._hurt(proj.rect.centerx)
                return

    def _items(self):
        player = self.player
        for coin in self.level.coins:
            if not coin.collected and coin.rect.colliderect(player.rect):
                coin.collected = True
                self._add_coin()
        for k in self.level.key_shards:
            if not k.collected and k.rect.colliderect(player.rect):
                k.collected = True
                self.level.shards_collected += 1
                self.game.run.score += SHARD_SCORE
                self.game.audio.play_sfx("coin")
                self.game.fx.spark(k.rect.centerx, k.rect.centery)
                have = self.level.shards_collected
                need = self.level.required
                self.game.fx.floater(k.rect.centerx, k.rect.y - 6,
                                     f"KEY {have}/{need}")
                if need > 0 and have == need:
                    self.game.fx.add_trauma(0.25)
                    self.game.fx.floater(k.rect.centerx, k.rect.y - 20,
                                         "GOAL OPEN!")
                    self.game.audio.play_sfx_at(
                        "checkpoint", self.level.goal.rect.centerx,
                        player.cx)                              # spatial 6c
        for pu in self.level.powerups:
            if not pu.collected and pu.rect.colliderect(player.rect):
                pu.collected = True
                player.apply_powerup(pu.kind)
                self.game.audio.play_sfx("powerup")
                label = {"star": "STAR!", "speed": "SPEED!",
                         "jump": "JUMP!", "heart": "MAX HP +"}[pu.kind]
                self.game.fx.floater(player.cx, player.cy - 18, label)
                self.game.fx.spark(player.cx, player.cy)
        for cp in self.level.checkpoints:
            if not cp.active and cp.rect.colliderect(player.rect):
                cp.active = True
                self.respawn = cp.respawn
                self.game.run.score += 100
                self.game.fx.spark(cp.rect.centerx, cp.rect.centery)
                self.game.audio.play_sfx_at(
                    "checkpoint", cp.rect.centerx, player.cx)   # spatial 6c
        for sw in self.level.switches:
            if not sw.active and sw.rect.colliderect(player.rect):
                sw.active = True
                self.level.open_doors_for(sw.switch_id)
                self.game.fx.floater(sw.rect.centerx, sw.rect.top - 6, "OPEN")
                self.game.fx.add_trauma(0.25)
                self.game.audio.play_sfx_at(
                    "warp", sw.rect.centerx, player.cx)          # spatial 6c
        for pl in self.level.plates:
            if pl.rect.colliderect(player.rect):
                self.level.press_plate(pl.plate_id)   # refreshes windows
                if not pl.active:
                    pl.active = True
                    self.game.fx.floater(pl.rect.centerx, pl.rect.top - 6,
                                         "PRESS")
                    self.game.fx.add_trauma(0.15)
                    self.game.audio.play_sfx("bump")
        goal = self.level.goal
        if goal is not None and goal.rect.colliderect(player.rect):
            if self.level.goal_locked():
                if self._lock_msg_cd == 0:      # throttled hint (3c)
                    self._lock_msg_cd = 60
                    self.game.fx.floater(
                        goal.rect.centerx, goal.rect.top - 8,
                        f"KEYS {self.level.shards_collected}"
                        f"/{self.level.required}")
                    self.game.audio.play_sfx("bump")
            else:
                self._clear_level()

    def _warp(self, inp):
        player = self.player
        if not (inp.down and player.on_ground):
            self.warp_hold = 0
            return
        pipe = self.level.pipe_at_feet(player.rect)
        if pipe is None or pipe.warp_id is None:
            self.warp_hold = 0
            return
        self.warp_hold += 1
        if self.warp_hold < WARP_ENTER_FRAMES:
            return
        target = next((p for p in self.level.pipes
                       if p.warp_id == pipe.warp_id and p is not pipe), None)
        if target is None:
            self.warp_hold = 0
            return
        player.x = float(target.rect.x + 4)
        player.y = float(target.rect.top - PLAYER_H)
        player.warp_freeze = 14
        self.warp_hold = 0
        self.camera.snap_to(player.rect)
        self.game.fx.dust(pipe.rect.centerx, pipe.rect.top)
        self.game.fx.dust(target.rect.centerx, target.rect.top)
        self.game.audio.play_sfx_at(
            "warp", pipe.rect.centerx, player.cx)               # spatial 6c

    def _timer(self):
        self.timer_ticks += 1
        if self.timer_ticks >= TIME_INTERVAL_FRAMES:
            self.timer_ticks = 0
            self.time_left -= 1
            if self.time_left <= 0:
                self.time_left = 0
                self._kill("time")

    # ---------------------------------------------------------------- draw
    def draw(self, surf):
        g = self.game
        cam = self.camera
        tick = g.tick
        assets = g.assets.for_zone(zone_of(g.run.level_index))   # 4b theme
        surf.blit(assets.sky(), (0, 0))
        clouds = assets.clouds()
        cw = clouds.get_width()
        drift = int(cam.x * 0.1 + tick * 0.1) % cw
        # near layers shake with the view; the far hills layer stays static
        surf.blit(clouds, (-drift - cam.shake_dx, -cam.shake_dy))
        surf.blit(clouds, (cw - drift - cam.shake_dx, -cam.shake_dy))
        far = assets.hills_far()
        fw = far.get_width()
        off = int(cam.x * 0.25) % fw
        y_far = VIEW_H - 96 + int(cam.y * 0.2)
        for x in range(-off - fw, VIEW_W + fw, fw):
            surf.blit(far, (x, y_far))
        near = assets.hills_near()
        nw = near.get_width()
        off = int(cam.x * 0.5) % nw
        y_near = VIEW_H - 72 + int(cam.y * 0.35)
        for x in range(-off - nw, VIEW_W + nw, nw):
            surf.blit(near, (x - cam.shake_dx, y_near - cam.shake_dy))

        self.level.draw(surf, cam, assets, tick)
        self.enemies.draw(surf, cam, assets, tick)
        for enemy in self.enemies.enemies:          # frozen overlay (visual)
            if enemy.frozen > 0 and cam.visible(enemy.rect):
                tint = pygame.Surface((enemy.rect.w, enemy.rect.h),
                                      pygame.SRCALPHA)
                tint.fill(FX_ICE_TINT)
                surf.blit(tint, cam.apply(enemy.rect.x, enemy.rect.y))
        for atk in self.attacks:
            atk.draw(surf, cam, assets, tick)
        self.player.draw(surf, cam, assets, tick)
        g.fx.draw(surf, cam)
        run = g.run
        pl = self.player
        idx = run.level_index
        g.hud.draw(surf, run.score, run.coins, run.lives, self.time_left,
                   f"{zone_of(idx) + 1}-{zone_level_of(idx) + 1}",
                   pl.hearts, pl.max_hearts,
                   (pl.active_powerup, pl.powerup_frac)
                   if pl.active_powerup else None,
                   (self.level.shards_collected, self.level.required)
                   if self.level.required else None)
        boss = self._boss
        if (boss is not None and boss.alive and boss.active
                and boss.state != "dying"):
            g.hud.draw_boss_bar(surf, getattr(boss, "name", "BOSS"),
                                boss.hp / max(1, boss.max_hp))
        if self._banner_t > 0 and (tick // 20) % 2 == 0:
            g.hud.text_center(surf, VIEW_W // 2, 100, "WARNING!",
                              (255, 96, 96), g.hud.big_font)
        if self._primer_t > 0:                          # zone primer (6c)
            zone = zone_of(run.level_index)
            g.hud.text_center(surf, VIEW_W // 2, 64,
                              f"ZONE {zone + 1}: {ZONES[zone]['name']}",
                              (255, 226, 96), g.hud.mid_font)
            g.hud.text_center(surf, VIEW_W // 2, 84,
                              ZONES[zone].get("primer", ""))


