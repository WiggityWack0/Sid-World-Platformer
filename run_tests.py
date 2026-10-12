#!/usr/bin/env python3
"""
Run the full Sids World test suite (pytest under the hood).

Usage: python run_tests.py
"""

import sys
from pathlib import Path

import pytest

if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root))
    code = pytest.main([str(root / "tests"), "-q"])
    sys.exit(code)
