"""Concrete bosses (Phase 5c). All original designs; spawned only on
zone-final arenas via the generator — never in the regular enemy pools."""

from src.enemies.bosses.boulder_brute import BoulderBrute
from src.enemies.bosses.crystal_golem import CrystalGolem
from src.enemies.bosses.magma_monarch import MagmaMonarch
from src.enemies.bosses.warden_owl import WardenOwl

BOSS_TYPES = {
    "boulder_brute": BoulderBrute,
    "crystal_golem": CrystalGolem,
    "warden_owl": WardenOwl,
    "magma_monarch": MagmaMonarch,
}

__all__ = ["BoulderBrute", "CrystalGolem", "WardenOwl", "MagmaMonarch",
           "BOSS_TYPES"]