"""Enemy type registry."""

from src.enemies.base import Enemy, contact_result, ledge_ahead
from src.enemies.bomber import Bomber, Bomb
from src.enemies.boss import Boss
from src.enemies.bosses import BOSS_TYPES
from src.enemies.chaser import Chaser
from src.enemies.charger import Charger
from src.enemies.flyer import Flyer
from src.enemies.jumper import Jumper
from src.enemies.needler import Needler, NeedlerShot
from src.enemies.spitter import Projectile, Spitter
from src.enemies.shieldkin import Shieldkin
from src.enemies.walker import Shellback, Walker
from src.enemies.wallcrawler import Wallcrawler

ENEMY_TYPES = {
    "walker": Walker,
    "shellback": Shellback,
    "flyer": Flyer,
    "chaser": Chaser,
    "spitter": Spitter,
    "jumper": Jumper,
    "shieldkin": Shieldkin,
    "bomber": Bomber,
    "wallcrawler": Wallcrawler,
    "charger": Charger,
    "needler": Needler,
}
ENEMY_TYPES.update(BOSS_TYPES)   # spawnable, but never in the RNG pools

__all__ = [
    "Enemy", "Walker", "Shellback", "Flyer", "Chaser", "Spitter", "Jumper",
    "Shieldkin", "Bomber", "Bomb", "Wallcrawler", "Charger", "Needler",
    "NeedlerShot", "Projectile", "ENEMY_TYPES", "contact_result",
    "ledge_ahead", "Boss", "BOSS_TYPES",
]
