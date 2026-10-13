"""Shieldkin (5a): armored patrol — frontal stomps bounce off the shield.

Killed by a back stomp, a sliding shell, elemental forms, or a star.
The blocked ("bounce") stomp still bounces the player but scores nothing.
"""

from src import config
from src.enemies.base import Enemy, ledge_ahead


class Shieldkin(Enemy):
    KIND = "shieldkin"

    def think(self, level, player):
        self.vx = self.facing * config.SHIELDKIN_SPEED
        if self.on_ground and not ledge_ahead(level, self):
            self.facing = -self.facing
            self.vx = self.facing * config.SHIELDKIN_SPEED

    def on_wall_bump(self, hit):
        self.facing = -hit
        self.vx = self.facing * config.SHIELDKIN_SPEED

    def _hit_front(self, player):
        """True when the player's center is on the shielded side."""
        if player is None:
            return False
        return (player.cx >= self.cx) == (self.facing > 0)

    def stomped(self, player=None):
        if self._hit_front(player):
            return "bounce"                 # shield: bounce, no kill/score
        self.start_dying()
        return "stomp"

    def draw(self, surf, cam, assets, tick):
        surf.blit(assets.enemy_frame(self),
                  (int(self.x) - cam.ix, int(self.y) - cam.iy))