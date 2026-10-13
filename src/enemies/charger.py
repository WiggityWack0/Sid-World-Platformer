"""Charger (5a): slow patrol -> wind-up telegraph -> straight dash.

Breaks BRICK (soft) tiles while dashing; turns only at walls (per plan
§5.5). The stashed `_level` gives the wall-bump hook tile access.
"""

from src import config
from src.config import TILE
from src.enemies.base import Enemy, ledge_ahead
from src.level import tiles as T


class Charger(Enemy):
    KIND = "charger"

    def __init__(self, x, y):
        super().__init__(x, y)
        self.windup = 0
        self.flash = 0
        self._dash_ticks = 0
        self._level = None

    def think(self, level, player):
        self._level = level
        if self.flash > 0:
            self.flash -= 1
        if self.state == "attack":                       # dashing
            self.vx = self.facing * config.CHARGER_DASH_SPEED
            self.windup = 0
            self._dash_ticks -= 1
            if self._dash_ticks <= 0:
                self.state = "patrol"
                self.vx = self.facing * config.CHARGER_PATROL
            return
        if self.windup > 0:                              # telegraph
            self.vx = 0.0
            self.windup -= 1
            self.flash = 4
            if self.windup <= 0:
                self.state = "attack"
                self._dash_ticks = config.CHARGER_DASH_TICKS
            return
        self.vx = self.facing * config.CHARGER_PATROL
        if self.on_ground and not ledge_ahead(level, self):
            self.facing = -self.facing
            self.vx = self.facing * config.CHARGER_PATROL
        if not player.dead:
            dx = player.cx - self.cx
            dy = abs(player.cy - self.cy)
            if (abs(dx) <= config.CHARGER_RANGE
                    and dy <= config.CHARGER_ACQUIRE_DY):
                self.facing = 1 if dx > 0 else -1
                self.windup = config.CHARGER_WINDUP

    def _break_soft(self, hit):
        """Try to smash BRICK tiles at the bump column. Pure tile edits."""
        lvl = self._level
        if lvl is None:
            return False
        tx = int((self.cx + hit * (self.W // 2 + 1)) // TILE)
        broke = False
        for oy in (5, self.H // 2, self.H - 5):
            ty = int((self.y + oy) // TILE)
            if lvl.tiles.get(tx, ty) == T.BRICK:
                lvl.tiles.set(tx, ty, T.EMPTY)
                broke = True
        return broke

    def on_wall_bump(self, hit):
        if self.state == "attack":
            if self._break_soft(hit):
                if self._dash_ticks < 12:
                    self._dash_ticks = 12    # keep plowing briefly
                return                       # keep facing: dash continues
            self.state = "patrol"            # hard wall stops the dash
        self.facing = -hit
        self.vx = self.facing * config.CHARGER_PATROL

    def draw(self, surf, cam, assets, tick):
        surf.blit(assets.enemy_frame(self),
                  (int(self.x) - cam.ix, int(self.y) - cam.iy))