"""Enemy type registry."""

from src.enemies.base import Enemy, contact_result, ledge_ahead
from src.enemies.chaser import Chaser
from src.enemies.flyer import Flyer
from src.enemies.jumper import Jumper
from src.enemies.spitter import Projectile, Spitter
from src.enemies.walker import Shellback, Walker

ENEMY_TYPES = {
    "walker": Walker,
    "shellback": Shellback,
    "flyer": Flyer,
    "chaser": Chaser,
    "spitter": Spitter,
    "jumper": Jumper,
}

__all__ = [
    "Enemy", "Walker", "Shellback", "Flyer", "Chaser", "Spitter", "Jumper",
    "Projectile", "ENEMY_TYPES", "contact_result", "ledge_ahead",
]
