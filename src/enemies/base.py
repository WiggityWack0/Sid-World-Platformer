"""
Enemy base FSM + shared combat rules.

States: patrol -> chase/attack (type specific), shell (stunned), dying.
Ground enemies obey gravity and collide with the tile map; flyers override
their movement entirely. All behaviour is polymorphic (think/update/draw),
so EnemyManager never needs isinstance dispatch.
"""

from src import config
from src import physics
import pygame


class Enemy:
    KIND = "enemy"
    W = 16
    H = 16
    GRAVITY = True
    STOMP_PROOF = False          # spiked enemies hurt on stomp
    CONTACT_HARM = True
    DEATH_TICKS = 30             # corpse linger window (SI-A; was 26)
    HIT_FLASH_TICKS = 6          # white recoil flash after a hit (SI-A)

    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.facing = -1
        self.state = "patrol"    # patrol|chase|shell|attack|dying
        self.active = False
        self.on_ground = False
        self.death_timer = 0
        self.anim_t = 0
        self.wall_hit = 0         # -1/1 from last move_x
        self.frozen = 0           # ice-form ticks remaining (uniform contract)
        self.hit_flash = 0        # hit-recoil ticks remaining (SI-A)
        self.hit_scale = 1.0      # recoil squash factor (SI-A)
        self.spawn = (x, y)

    # ------------------------------------------------------------ helpers
    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.W, self.H)

    @property
    def cx(self):
        return self.x + self.W / 2

    @property
    def cy(self):
        return self.y + self.H / 2

    @property
    def alive(self):
        return self.state != "dying"

    def start_dying(self, pop=False):
        if self.state == "dying":
            return
        self.state = "dying"
        self.death_timer = self.DEATH_TICKS
        self.start_hit_flash()
        if pop:
            self.vy = -4.0
            self.GRAVITY_CORPSE = True

    def start_hit_flash(self, ticks=None):
        """Recoil flash on taking a hit (SI-A). Lethal blows trigger it
        via start_dying(); non-lethal reactions (blocks, shell stops) may
        call it directly for feedback without dying."""
        self.hit_flash = self.HIT_FLASH_TICKS if ticks is None else ticks
        self.hit_scale = 0.8

    def stomped(self, player=None):
        """Player bounced on top: default death (types may override)."""
        if self.STOMP_PROOF:
            return False
        self.start_dying()
        return "stomp"

    def side_contact(self, player):
        """Called when the player touches this enemy's side/bottom."""
        return "harm"

    def reset(self):
        """Restore to spawn state (used when the player respawns)."""
        self.x, self.y = self.spawn
        self.vx = self.vy = 0.0
        self.state = "patrol"
        self.death_timer = 0
        self.active = False
        self.on_ground = False
        self.facing = -1
        self.frozen = 0
        self.hit_flash = 0
        self.hit_scale = 1.0

    # ------------------------------------------------------------- update
    def update(self, level, player):
        self.anim_t += 1
        if self.hit_flash > 0:              # recoil: 0.8 -> 0.9 -> 1.0 scale
            self.hit_flash -= 1
            self.hit_scale = (0.8 if self.hit_flash > 4 else
                              0.9 if self.hit_flash > 2 else 1.0)
        if self.state == "dying":
            self.death_timer -= 1
            if getattr(self, "GRAVITY_CORPSE", False):
                self.vy = physics.clamp_velocity(self.vy + config.GRAVITY)
                self.y += self.vy
            return
        if not self.active:
            return

        self.think(level, player)

        movers = level.mover_rects()
        if self.GRAVITY:
            self.vy = physics.clamp_velocity(self.vy + config.GRAVITY)

        new_x, hit = physics.move_x(
            self.x, self.y, self.W, self.H, self.vx, level)
        self.wall_hit = hit
        self.x = new_x
        if hit != 0:
            self.on_wall_bump(hit)

        new_y, landed, head, _surf = physics.move_y(
            self.x, self.y, self.W, self.H, self.vy, level,
            one_ways=movers)
        self.y = new_y
        self.on_ground = landed
        if landed:
            self.vy = 0.0
            self.landed()
        if head is not None:
            self.vy = 0.0
        if self.y > level.height + 32:
            self.state = "dying"
            self.death_timer = 0

    # ------------------------------------------------------- hooks (override)
    def think(self, level, player):
        self.vx = self.facing * 1.2

    def on_wall_bump(self, hit):
        self.facing = -hit
        self.vx = -self.vx if self.vx else self.vx

    def landed(self):
        pass

    def draw(self, surf, cam, assets, tick):
        raise NotImplementedError


def ledge_ahead(level, enemy):
    """True when there is floor just ahead of the enemy's feet."""
    px = enemy.cx + enemy.facing * (enemy.W // 2 + 3)
    py = enemy.rect.bottom + 4
    return level.solid_at(int(px // config.TILE), int(py // config.TILE))


def contact_result(player, enemy):
    """Shared combat rule: what happens when player rect meets enemy."""
    if not enemy.alive or player.dead:
        return "none"
    r = enemy.rect
    overlap = player.rect.clip(r) if player.rect.colliderect(r) else None
    if overlap is None:
        return "none"
    falling = player.vy > 0.5
    above = player.rect.bottom <= r.top + config.STOMP_TOLERANCE
    if falling and above and not enemy.STOMP_PROOF:
        return "stomp"
    if falling and above and enemy.STOMP_PROOF:
        return "hurt"            # spiked: stomping still hurts
    return "hurt"
