#!/usr/bin/env python3
"""
Run the Sids World test suite (pytest under the hood).

Default mode runs the fast suite and excludes tests marked @pytest.mark.slow.
Use --full to include the heavy generator fuzz and headless playtests.

Usage:
  python run_tests.py
  python run_tests.py --full
"""

import argparse
import sys
from pathlib import Path

import pytest

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Sids World tests.")
    parser.add_argument(
        "--full",
        action="store_true",
        help="include slow-marked heavy fuzz/playtest tests",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root))
    cmd = [str(root / "tests"), "-q"]
    if not args.full:
        cmd.extend(["-m", "not slow"])
    code = pytest.main(cmd)
    sys.exit(code)
