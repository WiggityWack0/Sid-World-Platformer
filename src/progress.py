"""
Persistent meta-progression (Phase 4c, D3).

JSON at `config.SAVE_PATH` (project-local, gitignored), schema-versioned
from day one with a migration hook. Writes are atomic (tmp + os.replace)
and loads are tolerant: missing/corrupt/wrong-typed files yield defaults
and NEVER crash (fail-safe doctrine: a bad save must not cost a run).
Consumes no RNG — gameplay determinism is untouched by design.
"""

import json
import os

from src import config
from src.config import (LEVELS_PER_RUN, MASTER_VOLUME, MUSIC_VOLUME,
                        SFX_VOLUME)

# Migrations: {from_version: callable(data) -> data (at from_version + 1)}.
# Applied in ascending order during load() when schema_version < current.
MIGRATIONS = {}


def default_progress():
    """Fresh schema-v1 progress (Appendix A sketch)."""
    return {
        "schema_version": config.SCHEMA_VERSION,
        "unlocked_level_index": 0,
        "best_scores": {},
        "settings": {
            "master_volume": MASTER_VOLUME,
            "music_volume": MUSIC_VOLUME,
            "sfx_volume": SFX_VOLUME,
            "muted": False,
            "tutorial_enabled": True,
        },
        "tutorial_seen": [],
        "current_run": None,
        "play_stats": {"deaths": 0, "bosses_defeated": 0},
    }


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _sanitize(data):
    """Coerce a dict into a valid progress dict (tolerant; never raises)."""
    out = default_progress()
    if not isinstance(data, dict):
        return out
    u = data.get("unlocked_level_index")
    if _is_int(u) and 0 <= u < LEVELS_PER_RUN:
        out["unlocked_level_index"] = u
    bs = data.get("best_scores")
    if isinstance(bs, dict):
        for k, v in bs.items():
            if _is_int(v) and v >= 0:
                out["best_scores"][str(k)] = v
    st = data.get("settings")
    if isinstance(st, dict):
        for vol in ("master_volume", "music_volume", "sfx_volume"):
            v = st.get(vol)
            if isinstance(v, (int, float)) and not isinstance(v, bool) \
                    and 0.0 <= v <= 1.0:
                out["settings"][vol] = float(v)
        for flag in ("muted", "tutorial_enabled"):
            v = st.get(flag)
            if isinstance(v, bool):
                out["settings"][flag] = v
    seen = data.get("tutorial_seen")
    if isinstance(seen, list):
        out["tutorial_seen"] = [s for s in seen if isinstance(s, str)]
    cr = data.get("current_run")
    if isinstance(cr, dict):
        out["current_run"] = cr
    ps = data.get("play_stats")
    if isinstance(ps, dict):
        for key in ("deaths", "bosses_defeated"):
            v = ps.get(key)
            if _is_int(v) and v >= 0:
                out["play_stats"][key] = v
    return out


def load(path=None):
    """Load progress; any problem -> defaults. Never raises."""
    if path is None:
        path = config.SAVE_PATH
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return default_progress()
    if not isinstance(data, dict):
        return default_progress()
    ver = data.get("schema_version")
    if not _is_int(ver) or ver < 1:
        return default_progress()
    if ver > config.SCHEMA_VERSION:
        return default_progress()      # never downgrade a newer save
    while ver < config.SCHEMA_VERSION:
        mig = MIGRATIONS.get(ver)
        if mig is None:
            return default_progress()  # no upgrade path -> fresh start
        data = mig(data)
        if not isinstance(data, dict):
            return default_progress()
        ver += 1
        data["schema_version"] = ver
    return _sanitize(data)


def save(data, path=None):
    """Atomic save (tmp + os.replace). IO failures are swallowed (False)."""
    if path is None:
        path = config.SAVE_PATH
    payload = _sanitize(data)
    payload["schema_version"] = config.SCHEMA_VERSION
    try:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        os.replace(tmp, path)
        return True
    except OSError:
        return False


def is_unlocked(progress, level_index):
    """Levels 0..unlocked_level_index are playable."""
    return 0 <= level_index <= progress.get("unlocked_level_index", 0)


def record_clear(progress, level_index, score):
    """Clearing level N unlocks N+1 (monotone); best score keeps the max.

    Mutates `progress` in place and returns it. Consumes no RNG.
    """
    nxt = min(level_index + 1, LEVELS_PER_RUN - 1)
    if nxt > progress.get("unlocked_level_index", 0):
        progress["unlocked_level_index"] = nxt
    best = progress.setdefault("best_scores", {})
    if score > best.get(str(level_index), -1):
        best[str(level_index)] = score
    return progress