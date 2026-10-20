# ART_STYLE.md — Sid's World art & visual-code rules

The single reference for how Sid's World looks and how visual code is
written. Record kept as of the visual overhaul (Phases 0-6, 2026-10).

## Design rules

* **Everything is generated at runtime.** No image/audio asset files are
  loaded, ever (design rule D7). All surfaces are built from pygame
  primitives at startup and cached.
* **Grid**: 16 px tiles (`TILE`), 400x240 virtual surface, integer upscale
  to the window (never smoothed). Sprites occupy the same 16px grid
  (some 8-14px wide inside it).
* **Style**: bold dark outlines (`OUTLINE = (28, 24, 32)`), limited
  palette, light from top-left (highlights upper-left, shadows lower-right).
* **Typography**: original 5x7 bitmap font (`src/assets/pixel_font.py`),
  1px advance spacing (ADV=6 at scale 1), faces at scale 1 (HUD/body),
  2 (menus), 3 (titles). Glyphs are authored as 7-row `'#'/'.'` string
  art. Unknown characters fall back to `'?'`.
* **Original designs only**: shapes/colors are written here, not derived
  from any external source.

## Palette discipline

* `DEFAULT_PAL` (asset_factory) is the zone-0 identity palette; zone themes
  override via `ZONES[n]["palette"]`.
* **`THEMED_KEYS` changes are atomic**: adding/removing a key in
  `DEFAULT_PAL` requires updating EVERY zone palette in `config.ZONES` in
  the same commit — `test_zone_palettes_complete` asserts the exact set.
* **Derived colors never become keys**: use `_shade(color, amount)` or
  `_mix(a, b, t)` for tints/shades of existing colors (mountains, hills
  speckle, ghost tints). Fixed per-zone moods that are NOT palette concerns
  live as fixed tuples: `GRADE_TINTS` (presentation), `FG_TINTS`
  (foreground silhouettes).
* Zone theming flows through `AssetFactory(pal=...)` / `for_zone(zone)`;
  zone 0 returns the base factory itself (identity by construction).

## Presentation layer (`src/render/presentation.py`)

* Frame-path rules: **precompute at init, accelerated blits only** — no
  per-pixel Python loops per frame. `apply()` is at most ~4 full-screen
  blits (`BLEND_RGB_MULT` grade, `set_alpha` vignette/veil/scanlines).
* Every cache is bounded: font string cache (512, wholesale clear),
  MenuPanel panels (64), boss name plates (8), ghost frames
  (`GHOST_CACHE_MAX`), floater/particle pools (config caps). Pinned by
  `test_balance_audit.py`.
* Settings are visual-only flags persisted in `progress["settings"]`
  (vignette, color_grade, scanlines, window_scale); tolerate garbage —
  bad values must fall back to defaults, never raise.

## Juice rules (`src/player.py`, `src/states/playing.py`, `src/transition.py`)

* **Pure tick math, no RNG, no wall-clock.** Same ticks -> same visuals;
  every juice test asserts determinism explicitly.
* **Visual-only fields never touch gameplay surfaces**: no hitbox, no
  `tiles.data`, no validator input, no save schema. Squash scales the
  DRAWN sprite only (feet anchored); hit-stop freezes updates but never
  rewinds them; trails sample at update time so frame rate is irrelevant.
* Freeze windows stay short (`HITSTOP_* <= 8`, pinned). Boss-watch fires
  once per hp drop (single wave; first sighting only records).
* Transitions: `step()`/`alpha()` semantics are contract-frozen by
  `test_transitions.py` — new styles add draw shapes + `progress()`, never
  timing changes.

## Recipes

* **Add a glyph**: author 7 rows of 5 chars (`'#'`/`'.'`) in `_G`
  (pixel_font.py); uppercase + lowercase a-z + digits + punctuation exist.
  Sweep `test_hud_menus_v2.py::test_font_covers_game_charset` if the game
  starts rendering a new character (extend the charset there too).
* **Add a decoration kind** (cosmetic tiles): sprite in `_make_decoration`,
  add to `DECORATION_KINDS` (+ `DECORATION_FRAMES` if animated), place it
  in `_scatter_decorations` (generator) — the scatter MUST use its own
  `random.Random(seed ^ 0xDEC0DE)` stream and stay outside `tiles.data`
  (hash/validator/save invisibility is test-enforced). Respect the density
  cap (1 per ~6 tiles, pinned).
* **Add a transition style**: draw branch in `Transition.draw` driven by
  `progress()`; wire a caller in `Game._transition_style`; add the style to
  `test_juice.py`'s contract loop (swap-once + identical alpha math).
* **Add an Options row**: key in `OptionsState.ROWS` + `LABELS`, default in
  `progress.default_progress()`, typed sanitization in `_sanitize`, display
  branch in the draw, live apply via audio/presentation `apply_settings`.
  Menu rows render through `MenuPanel` (`game.menu.draw`).
* **Add a HUD/menu text style**: reuse `Hud.text`/`text_center` (they take
  `font=` as any face with `render`/`size`); never re-introduce SysFont.

## Test doctrine

* Headless everywhere: SDL dummy drivers set in `tests/conftest.py` before
  pygame loads; no display/audio device assumptions; the suite must never
  touch the real `save/` (autouse fixture).
* **No wall-clock asserts** — perf numbers live in docs
  (`ProjectPlan.md` audit records); tests pin structure/invariants only
  (`tests/test_balance_audit.py`).
* Determinism is asserted, not assumed: juice/background/decoration tests
  replay identical tick sequences and compare bytes.
* **Pixel-test catalog obligation**: exact-render tests are catalogued in
  `ProjectPlan.md` (with per-file "owns" lists). Any art change must sweep
  the catalogued suites for its subjects and update rows in the same
  commit; new exact-render test files get added to the catalog.
* Visual-only work is test-proven invisible to gameplay: decorations vs
  hash/validator, squash vs `rect`, hit-stop vs resume, transitions'
  swap-once contract. Keep those proofs green when touching any of it.

