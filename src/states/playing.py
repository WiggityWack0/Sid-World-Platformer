"""Core gameplay state: level, player, enemies, combat, items, camera."""

import pygame

from src import inputs
from src.config import (BREAK_SCORE, COIN_CLEAR_BONUS, COIN_SCORE,
                        COINS_PER_LIFE, KICK_SCORE, LEVELS_PER_RUN,
                        PLAYER_H, STOMP_BOUNCE, STOMP_BOUNCE_HOLD,
                        STOMP_SCORE, START_TIME, TIME_BONUS_PER_UNIT,
                        TIME_INTERVAL_FRAMES, VIEW_H, VIEW_W,
                        WARP_ENTER_FRAMES)
from src.camera import Camera
from src.enemies import contact_result
from src.enemy_manager import EnemyManager
from src.level.validator import ensure_level
from src.player import Input, Player
from src.states.base import State


class PlayingState(State):
    name = "playing"

    # ------------------------------------------------------------ lifecycle
    def on_enter(self, **kwargs):
        run = self.game.run
        seed = run.seed + run.level_index * 1000003
        difficulty = run.level_index / max(1, LEVELS_PER_RUN - 1)
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
        self._cleared = False
        self.game.playing = self
        self.game.audio.play_music(
            "level_a" if run.level_index < (LEVELS_PER_RUN + 1) // 2
            else "level_b")

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN or event.key == pygame.K_m:
            return
        action = inputs.key_to_action(event.key)
        if action == "jump":
            self.player.queue_jump()
        elif action == "pause" or event.key == pygame.K_ESCAPE:
            self.game.pause()
        elif event.key == pygame.K_r:
            self.game.audio.play_sfx("select")
            self.game.switch_state("playing")

    # -------------------------------------------------------------- helpers
    def _music_for_level(self):
        run = self.game.run
        return ("level_a" if run.level_index < (LEVELS_PER_RUN + 1) // 2
                else "level_b")

    def _add_coin(self):
        run = self.game.run
        run.coins += 1
        self.level_coins += 1
        run.score += COIN_SCORE
        if run.coins >= COINS_PER_LIFE:
            run.coins -= COINS_PER_LIFE
            run.lives += 1
            self.game.audio.play_sfx("one_up")
        else:
            self.game.audio.play_sfx("coin")

    def _kill(self, cause):
        if self.player.dead:
            return
        self.player.die(cause)
        self.game.audio.stop_music(fade=80)
        self.game.audio.play_sfx("death")

    def _respawn(self):
        self.player.respawn_at(*self.respawn)
        self.enemies.reset()
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
        self.level.update()

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

        events = player.update(inp, self.level)
        if player.jumped and not self.was_jumped:
            self.game.audio.play_sfx("jump")
        self.was_jumped = player.jumped

        for ev in events:
            if ev[0] == "bump":
                if ev[1] == "coin":
                    self._add_coin()
                elif ev[1] == "break":
                    run.score += BREAK_SCORE
                    self.game.audio.play_sfx("brick")
                elif ev[1] == "hit":
                    self.game.audio.play_sfx("bump")
            elif ev[0] in ("pit", "hazard"):
                self._kill(ev[0])

        self.enemies.update(self.level, player, self.camera)
        self._combat(inp)
        if player.dead:
            return
        self._items()
        self._warp(inp)
        self._timer()
        self.camera.update(player.rect)

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
                    else:
                        run.score += STOMP_SCORE
                        self.game.audio.play_sfx("stomp")
                        self.game.audio.play_sfx("bounce")
            elif result == "hurt":
                outcome = enemy.side_contact(player)
                if outcome == "kicked":
                    run.score += KICK_SCORE
                    self.game.audio.play_sfx("kick")
                else:
                    self._kill("enemy")
                    return
        for proj in self.enemies.projectiles:
            if proj.rect.colliderect(player.rect):
                proj.life = 0
                self._kill("projectile")
                return

    def _items(self):
        player = self.player
        for coin in self.level.coins:
            if not coin.collected and coin.rect.colliderect(player.rect):
                coin.collected = True
                self._add_coin()
        for cp in self.level.checkpoints:
            if not cp.active and cp.rect.colliderect(player.rect):
                cp.active = True
                self.respawn = cp.respawn
                self.game.run.score += 100
                self.game.audio.play_sfx("checkpoint")
        goal = self.level.goal
        if goal is not None and goal.rect.colliderect(player.rect):
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
        self.game.audio.play_sfx("warp")

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
        surf.blit(g.assets.sky(), (0, 0))
        clouds = g.assets.clouds()
        cw = clouds.get_width()
        drift = int(cam.x * 0.1 + tick * 0.1) % cw
        surf.blit(clouds, (-drift, 0))
        surf.blit(clouds, (cw - drift, 0))
        far = g.assets.hills_far()
        fw = far.get_width()
        off = int(cam.x * 0.25) % fw
        y_far = VIEW_H - 96 + int(cam.y * 0.2)
        for x in range(-off - fw, VIEW_W + fw, fw):
            surf.blit(far, (x, y_far))
        near = g.assets.hills_near()
        nw = near.get_width()
        off = int(cam.x * 0.5) % nw
        y_near = VIEW_H - 72 + int(cam.y * 0.35)
        for x in range(-off - nw, VIEW_W + nw, nw):
            surf.blit(near, (x, y_near))

        self.level.draw(surf, cam, g.assets, tick)
        self.enemies.draw(surf, cam, g.assets, tick)
        self.player.draw(surf, cam, g.assets, tick)
        run = g.run
        g.hud.draw(surf, run.score, run.coins, run.lives, self.time_left,
                   f"1-{run.level_index + 1}")


