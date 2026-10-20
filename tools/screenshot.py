"""Screenshot rig (Phase 0 of the visual overhaul; dev-only, not shipped).

Headless-deterministic PNG gallery of every major state/scene, used as the
before/after reference for the visual overhaul (see ProjectPlan.md). Runs the
REAL Game/state machinery with SDL dummy drivers, a pinned seed, transitions
disabled, and a scripted input stream — no wall-clock, no real input devices.

Usage:
    python tools/screenshot.py            # write the gallery to screenshots/
    python tools/screenshot.py out_dir    # write to a custom directory

Determinism notes:
  * Seed 42 everywhere; tick counts are fixed per shot.
  * Gameplay frames use a scripted controller (hold right, periodic jump).
  * The real save file is never touched: config.SAVE_PATH is redirected to
    a temp file before Game is constructed (tutorial ticks save progress).
"""

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402

SEED = 42
ZONE_LEVELS = (0, 5, 10, 15)       # first level of each zone
BOSS_LEVELS = (4, 9, 14, 19)       # zone finals (arena + boss)
GAMEPLAY_TICKS = 90
BOSS_TICKS = 60


def _run_ticks(state, n):
    for _ in range(n):
        state.update()


def _shot(game, out_dir, name):
    """Draw the active state to the virtual surface and save it as PNG."""
    game.state.draw(game.surface)
    path = Path(out_dir) / f"{name}.png"
    pygame.image.save(game.surface, str(path))
    return path


def _script_input(held):
    """Patch inputs.action_held with a scripted held-key table."""
    from src import inputs
    inputs.action_held = lambda a: held.get(a, False)


def _play_level(game, level_index, ticks):
    """Enter a level and advance it under the scripted controller."""
    held = {"right": True}
    _script_input(held)
    game.new_run(seed=SEED)
    game.run.level_index = level_index
    game.switch_state("playing")
    for i in range(ticks):
        held["jump"] = (i % 40) < 4      # periodic hop
        game.state.update()
    held["jump"] = False
    return held


def _enter_boss_arena(state):
    """Teleport the player into the arena and activate the boss (the same
    pattern tests/test_boss_fights.py uses for scripted fights)."""
    from src import config
    lvl = state.level
    p = state.player
    p.x = float(lvl.arena_x0 * config.TILE + 6)
    p.y = float(config.GROUND_ROW * config.TILE - config.PLAYER_H)
    state.camera.snap_to(p.rect)
    boss = next(e for e in state.enemies.enemies
                if getattr(e, "is_boss", False))
    boss.active = True
    return boss


def capture_all(out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # never touch the real save/progress.json (D3 hygiene)
    from src import config
    tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    tmp.close()
    config.SAVE_PATH = tmp.name

    from src.game import Game
    game = Game(seed=SEED, transitions=False)
    written = []

    # --- menus / non-playing states -----------------------------------
    _run_ticks(game.state, 60)
    written.append(_shot(game, out_dir, "01_title"))

    game.switch_state("level_select")
    _run_ticks(game.state, 30)
    written.append(_shot(game, out_dir, "02_level_select"))

    game.switch_state("options")
    _run_ticks(game.state, 30)
    written.append(_shot(game, out_dir, "03_options"))

    # --- one gameplay frame per zone ----------------------------------
    for shot, idx in enumerate(ZONE_LEVELS, start=4):
        _play_level(game, idx, GAMEPLAY_TICKS)
        written.append(_shot(game, out_dir,
                             f"{shot:02d}_zone{idx // 5 + 1}_gameplay"))

    # --- pause over live gameplay -------------------------------------
    game.pause()
    _run_ticks(game.state, 10)
    written.append(_shot(game, out_dir, "08_paused"))
    game.resume()

    # --- one boss arena frame per zone boss ---------------------------
    for i, idx in enumerate(BOSS_LEVELS, start=9):
        _play_level(game, idx, 30)
        _enter_boss_arena(game.state)
        _run_ticks(game.state, BOSS_TICKS)   # WARNING banner + idle cycle
        written.append(_shot(game, out_dir,
                             f"{i:02d}_boss_zone{idx // 5 + 1}"))

    # --- end-of-run states (need a live run + playing backdrop) -------
    _play_level(game, 0, 30)
    game.switch_state("level_clear", time_left=100,
                      time_bonus=100 * 50, coin_bonus=12 * 100)
    _run_ticks(game.state, 20)
    written.append(_shot(game, out_dir, "13_level_clear"))

    game.run.score = 12345
    game.switch_state("game_over")
    _run_ticks(game.state, 30)
    written.append(_shot(game, out_dir, "14_game_over"))

    game.switch_state("victory", new_best=True)
    _run_ticks(game.state, 30)
    written.append(_shot(game, out_dir, "15_victory"))

    pygame.quit()
    os.unlink(tmp.name)
    return written


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "screenshots")
    written = capture_all(out_dir)
    print(f"Saved {len(written)} screenshots to {out_dir}")
    for p in written:
        print(f"  {p.name}")


if __name__ == "__main__":
    main()
