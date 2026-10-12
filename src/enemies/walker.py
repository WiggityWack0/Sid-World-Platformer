"""Walker (Goomba-like) and Shellback (Koopa-like with shell mechanics)."""

from src import config
from src.enemies.base import Enemy, ledge_ahead


class Walker(Enemy):
    """Constant patrol; turns at walls and ledges; dies under a stomp."""

    KIND = "walker"

    def think(self, level, player):
        self.vx = self.facing * config.WALKER_SPEED
        if self.on_ground and not ledge_ahead(level, self):
            self.facing = -self.facing
            self.vx = self.facing * config.WALKER_SPEED

    def on_wall_bump(self, hit):
        self.facing = -hit
        self.vx = self.facing * config.WALKER_SPEED

    def draw(self, surf, cam, assets, tick):
        surf.blit(assets.enemy_frame(self),
                  (int(self.x) - cam.ix, int(self.y) - cam.iy))


class Shellback(Enemy):
    """Patrols like a walker; stomping retracts it into a kickable shell."""

    KIND = "shellback"

    def __init__(self, x, y):
        super().__init__(x, y)
        self.shell_timer = 0

    def think(self, level, player):
        if self.state == "shell":
            self.shell_timer -= 1
            if self.shell_timer <= 0:                 # re-emerge
                self.state = "patrol"
                self.vx = 0.0
            return                                    # slides via vx
        self.vx = self.facing * config.SHELLBACK_SPEED
        if self.on_ground and not ledge_ahead(level, self):
            self.facing = -self.facing
            self.vx = self.facing * config.SHELLBACK_SPEED

    def on_wall_bump(self, hit):
        if self.state == "shell":
            self.vx = -self.vx                        # bouncing shell
            self.facing = -hit
        else:
            self.facing = -hit
            self.vx = self.facing * config.SHELLBACK_SPEED

    def stomped(self, player=None):
        if self.state != "shell":
            self.state = "shell"
            self.shell_timer = config.SHELL_LIFETIME
            self.vx = 0.0
            return "stomp"
        if abs(self.vx) > 0.5:
            self.vx = 0.0                             # stomp stops it
            return "stop"
        return self.kick(player)                      # still: kick it

    def kick(self, player=None):
        direction = 1
        if player is not None:
            direction = 1 if player.cx > self.cx else -1
        self.state = "shell"
        self.shell_timer = config.SHELL_LIFETIME
        self.vx = direction * config.SHELL_SLIDE_SPEED
        self.facing = direction
        return "kick"

    def side_contact(self, player):
        if self.state == "shell" and abs(self.vx) < 0.5:
            self.kick(player)
            return "kicked"
        return "harm"

    @property
    def sliding(self):
        return self.state == "shell" and abs(self.vx) > 0.5

    def draw(self, surf, cam, assets, tick):
        surf.blit(assets.enemy_frame(self),
                  (int(self.x) - cam.ix, int(self.y) - cam.iy))
