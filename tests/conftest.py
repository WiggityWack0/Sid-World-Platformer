"""Shared pytest configuration: headless SDL drivers before pygame loads."""

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402
import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _isolated_save(tmp_path, monkeypatch):
    """The suite must NEVER touch the real save/ dir (4c, D3 hygiene)."""
    from src import config
    monkeypatch.setattr(config, "SAVE_PATH",
                        str(tmp_path / "progress.json"))


@pytest.fixture(scope="session")
def pygame_ready():
    """Initialize pygame once for tests that need surfaces/fonts."""
    pygame.init()
    pygame.display.set_mode((64, 64))
    yield
    pygame.quit()


@pytest.fixture()
def flat_level():
    """A small hand-made flat level: ground at row 12, 40 cols wide."""
    from src.level.level import Level
    from src.level import tiles as T
    lvl = Level(40, 18)
    for tx in range(40):
        for ty in range(12, 18):
            lvl.tiles.set(tx, ty, T.SOLID)
    lvl.spawn = (32, 12 * 16 - 26)
    lvl.respawn = lvl.spawn
    return lvl
