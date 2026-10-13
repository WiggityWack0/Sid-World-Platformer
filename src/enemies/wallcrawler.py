"""Wallcrawler (5a): clings to walls/ceilings, drops to pursue.

FSM: patrol -> climb (up a wall ahead, gravity off) -> ceiling (walks
along the underside toward the player) -> drop (gravity back on) ->
patrol. Killable by stomp once it has dropped, plus forms/star.
"""

from src import config
from src.config import TILE
from src.enemies.base import Enemy, ledge_ahead


class Wallcrawler(Enemy):
    KIND = "wallcrawler"

    def __init__(self, x, y):
        super().__init__(x, y)
        self.state = "patrol"

    def reset(self):
        super().reset()
        self.GRAVITY = True

    def wall_ahead(self, level):
        px = self.cx + self.facing * (self.W // 2 + 2)
        for oy in (4, self.H - 4):
            if level.solid_at(int(px // TILE),
                              int((self.y + oy) // TILE)):
                return True
        return False

    def ceiling_here(self, level):
        py = self.rect.top - 3
        for ox in (self.W // 2 - 3, -(self.W // 2 - 3)):
            if level.solid_at(int((self.cx + ox) // TILE), int(py // TILE)):
                return True
        return False

    def think(self, level, player):
        if self.state == "patrol":
            self.vx = self.facing * config.WALLCRAWLER_SPEED
            if self.on_ground and not ledge_ahead(level, self):
                self.facing = -self.facing
                self.vx = self.facing * config.WALLCRAWLER_SPEED
            if self.on_ground and self.wall_ahead(level):
                self.state = "climb"
                self.GRAVITY = False
                self.vy = 0.0
        elif self.state == "climb":
            self.vx = 0.0
            self.vy = -config.WALLCRAWLER_CLIMB
            if not self.wall_ahead(level):
                self.state = "ceiling"
        elif self.state == "ceiling":
            self.vx = 0.0
            self.vy = 0.0
            if not self.ceiling_here(level):
                self.state = "drop"
                self.GRAVITY = True
                return
            if not player.dead:
                dx = player.cx - self.cx
                if abs(dx) > 1:
                    self.facing = 1 if dx > 0 else -1
                if (abs(dx) < config.WALLCRAWLER_DROP_DX
                        and player.cy > self.cy):
                    self.state = "drop"
                    self.GRAVITY = True
                    return
            self.vx = self.facing * config.WALLCRAWLER_SPEED
        elif self.state == "drop":
            self.vx = 0.0
            if self.on_ground:
                self.state = "patrol"

    def draw(self, surf, cam, assets, tick):
        surf.blit(assets.enemy_frame(self),
                  (int(self.x) - cam.ix, int(self.y) - cam.iy))