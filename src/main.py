"""
Launcher for Sid's World.

Works both as `python src/main.py` (package bootstrap below) and as the
package module `python -m src.main`. The root `run_game.py` simply calls
`main()`.
"""

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    # running as a plain script: make the `src` package importable
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "src"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Sid's World")
    parser.add_argument("--seed", type=int, default=None,
                        help="fixed level generation seed")
    parser.add_argument("--frames", type=int, default=None,
                        help=argparse.SUPPRESS)   # automated headless runs
    args = parser.parse_args(argv)

    from src.game import Game
    game = Game(seed=args.seed, max_frames=args.frames, transitions=True)
    game.run_loop()


if __name__ == "__main__":
    main()
