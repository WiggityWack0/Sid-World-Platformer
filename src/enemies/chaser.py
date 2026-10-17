"""Chaser: patrols until the player enters aggro range, then runs the
player down along the ground (gravity + collision, never flies)."""

from src import config
from src.enemies.base import Enemy


class Chaser(Enemy):
    KIND = "chaser"

    def think(self, level, player):
        dx = player.cx - self.cx
        dy = abs(player.cy - self.cy)
        dist = abs(dx)
        if player.dead:
            dist = 9999
        # gaze locks toward the player before aggro (SI-C, proposal 4.1)
        rel = dx * self.facing
        if player.dead or abs(rel) <= 4:
            self.pupil_dx = 1 if self.state == "chase" else 0
        elif rel > 0:
            self.pupil_dx = 2 if self.state == "chase" else 1
        else:
            self.pupil_dx = -1
        if self.state == "chase":
            if dist > config.CHASER_DEAGGRO or dy > 96:
                self.state = "patrol"
            else:
                self.facing = 1 if dx > 0 else -1
                self.vx = self.facing * config.CHASER_CHASE_SPEED
                return
        # patrol
        if dist < config.CHASER_AGGRO and dy < 64:
            self.state = "chase"
            self.facing = 1 if dx > 0 else -1
            self.vx = self.facing * config.CHASER_CHASE_SPEED
        else:
            self.vx = self.facing * config.CHASER_PATROL_SPEED
            # chasers do not care about ledges (they will drop off)

    def on_wall_bump(self, hit):
        self.facing = -hit
        speed = (config.CHASER_CHASE_SPEED if self.state == "chase"
                 else config.CHASER_PATROL_SPEED)
        self.vx = self.facing * speed

    def draw(self, surf, cam, assets, tick):
        surf.blit(assets.enemy_frame(self),
                  (int(self.x) - cam.ix, int(self.y) - cam.iy))
