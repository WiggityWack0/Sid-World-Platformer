"""
EnemyManager: camera-proximity activation, polymorphic updates, shell vs
enemy collision, projectile lifecycle, culling and drawing.
"""

from src.config import ACTIVATION_FRAC, TILE, VIEW_W
from src.enemies import ENEMY_TYPES


def spawn_enemy(kind, tx, solid_row):
    """Create an enemy of `kind` standing on the tile row `solid_row`."""
    cls = ENEMY_TYPES[kind]
    x = tx * TILE + (TILE - cls.W) // 2
    y = solid_row * TILE - cls.H
    if kind == "flyer":
        y -= 44                              # hover above the ground
    return cls(x, y)


class EnemyManager:
    def __init__(self, spawns=None):
        self.spawns = list(spawns or [])
        self.enemies = [spawn_enemy(*s) for s in self.spawns]
        self.projectiles = []

    def reset(self):
        """Restore every enemy (player respawn)."""
        self.enemies = [spawn_enemy(*s) for s in self.spawns]
        self.projectiles = []

    def update(self, level, player, cam):
        lo = cam.x - 0.25 * VIEW_W
        hi = cam.x + ACTIVATION_FRAC * VIEW_W
        for enemy in self.enemies:
            enemy.active = lo <= enemy.cx <= hi
            if enemy.frozen > 0:          # ice form: uniform attr contract
                enemy.frozen -= 1         # (no isinstance dispatch)
                continue
            enemy.update(level, player)

        # sliding shells crush other enemies (never bosses — 5b)
        for shell in self.enemies:
            if (shell.alive and getattr(shell, "sliding", False)):
                for other in self.enemies:
                    if other is not shell and other.alive \
                            and not getattr(other, "is_boss", False) \
                            and shell.rect.colliderect(other.rect):
                        other.start_dying()

        # drain new spitter/boss shots without isinstance dispatch
        for enemy in self.enemies:
            shots = getattr(enemy, "shots", None)
            if shots:
                self.projectiles.extend(shots)
                shots.clear()
            reinf = getattr(enemy, "reinforcements", None)   # 5c (owl)
            if reinf:
                self.enemies.extend(spawn_enemy(*s) for s in reinf)
                reinf.clear()

        for proj in self.projectiles:
            proj.update(level)
        self.projectiles = [p for p in self.projectiles if not p.dead]
        self.enemies = [e for e in self.enemies
                        if e.state != "dying" or e.death_timer > 0]

    def living(self):
        return [e for e in self.enemies if e.alive and e.active]

    def draw(self, surf, cam, assets, tick):
        for enemy in self.enemies:
            if cam.visible(enemy.rect):
                enemy.draw(surf, cam, assets, tick)
        for proj in self.projectiles:
            if cam.visible(proj.rect):
                proj.draw(surf, cam, assets, tick)
