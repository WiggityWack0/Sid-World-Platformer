# Save format — `save/progress.json` (schema v1)

Design decisions **D3/D4** (locked): the file lives at
`<project>/save/progress.json`, is **gitignored**, and is written
**atomically** (temp file + `os.replace`). Loads are **tolerant**: a
missing, corrupt, wrongly-typed, or newer-schema file always yields safe
defaults — a bad save must never cost a run. `src/progress.py` owns all
reads/writes; nothing else touches the file.

## Schema v1

````json
{
  "schema_version": 1,
  "unlocked_level_index": 7,
  "best_scores": {"0": 4200, "1": 3800},
  "settings": {
    "master_volume": 0.8,
    "music_volume": 0.45,
    "sfx_volume": 0.75,
    "muted": false,
    "tutorial_enabled": true
  },
  "tutorial_seen": ["jump", "attack", "switch"],
  "current_run": null,
  "play_stats": {"deaths": 0, "bosses_defeated": 2}
}
````

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | int | Format version. Loads of NEWER versions fall back to defaults (never downgraded); OLDER versions run through `progress.MIGRATIONS` in ascending order. |
| `unlocked_level_index` | int 0..19 | Highest playable level. Level N is playable iff N <= this value. Cleared level N unlocks N+1 (monotone, capped at 19). |
| `best_scores` | object str->int | Best run score per level index (string keys for JSON). Updated with max() on every clear. |
| `settings.master/music/sfx_volume` | float 0..1 | Live-applied at startup and on every Options change (`AudioManager.apply_settings`). |
| `settings.muted` | bool | Global mute; also synced from the M key. |
| `settings.tutorial_enabled` | bool | Gates first-time tutorial hints. |
| `tutorial_seen` | array of str | Tutorial keys already shown (`jump`, `switch`, `shard`) — hints never repeat once seen. |
| `current_run` | object or null | **Reserved** for the mid-run-resume stretch goal (D4): will hold `{seed, level_index, score, coins, lives}` — enough to rebuild deterministically. Always null today. |
| `play_stats.deaths` | int | Reserved counter. |
| `play_stats.bosses_defeated` | int | Incremented (+ persisted) when a required boss is defeated. |

## Guarantees

* **Atomic:** writes go to `progress.json.tmp` then `os.replace` — readers
  never observe a half-written file.
* **Tolerant:** `load()` never raises. Unknown keys are ignored on load
  and dropped on the next save; invalid values are replaced with defaults
  field-by-field (`_sanitize`).
* **Isolated tests:** the pytest suite points `SAVE_PATH` at a temp
  directory via an autouse fixture — the real `save/` is never touched
  by tests.
* **No RNG:** progress I/O consumes no randomness (property-tested);
  gameplay determinism is unaffected.

## Migration hook

Register upgrades in `src/progress.py`:

````python
MIGRATIONS = {
    # 1: lambda data: {**data, "schema_version": 2, "new_field": default},
}
````

Bump `config.SCHEMA_VERSION` in the same change and add a test that an
old file loads (and migrates) correctly — see
`tests/test_progress.py::test_migration_hook_runs`.
