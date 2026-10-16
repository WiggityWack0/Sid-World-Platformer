# Sid's World

A  **Super Mario World-style platformer** written in pure
Python + pygame-ce: **20 procedurally generated levels across 4 themed
zones**, provably completable, 11 enemy types, 4 bosses, elemental forms,
power-ups, puzzle mechanics, persistent progress — with **every sprite and
every note synthesized at runtime**. One dependency (`pygame-ce`), no
external asset files.

## Quick start

````powershell
pip install -r requirements.txt     # pygame-ce >= 2.5
python run_game.py                # play! (fades enabled)
python run_game.py --seed 12345   # reproduce a specific world
````

Run the test suite (headless-safe, no audio/display device needed):

````powershell
python run_tests.py                # or: python -m pytest tests -q
````

## The run at a glance

* **4 zones x 5 levels = 20 levels.** Zone 1 Green Hills (teaching ramp),
  Zone 2 Ember Caves (switches, lava, ceiling crawlers), Zone 3 Frost
  Peaks (combat focus, chargers, needlers), Zone 4 Storm Keep (everything
  combined). Difficulty rises linearly 0 -> 1.0 across the run; level
  length grows per zone (2 -> 6 screens).
* **One boss per zone** on a hand-authored arena carved into the level
  tail: Boulder Brute, Crystal Golem, Warden Owl, Magma Monarch — each a
  multi-phase fight with telegraphs, stagger windows, an HP bar, a
  WARNING intro, its own music, and a goal that stays locked until the
  boss falls.
* **Progression:** unlocks + best scores + settings persist to
  `save/progress.json` (atomic, schema-versioned, gitignored — see
  `docs/SAVE_FORMAT.md`). Title menu: New Game / Continue / Level Select /
  Options. Level select shows all 20 nodes with lock state, best scores,
  and boss markers.

## Controls

| Key | Action |
|---|---|
| <- / -> or A / D | Move |
| Z / Space | Jump (hold higher, tap shorter; stomp bounce holds higher) |
| X / Shift | Run |
| S | Crouch; **hold on a warp pipe to enter it** (Down also works) |
| C | Attack (fire/ice/lightning forms) |
| F | Cycle form (Sid -> fire -> ice -> lightning -> Sid) |
| P / Esc | Pause (menu: Resume / Restart / Options / Level Select / Quit) |
| R | Restart current level |
| M | Mute / unmute, everywhere (persisted) |
| Enter | Confirm (menus); on title = New Game |
| C (title) | Continue from the highest unlocked level |
| L (title) | Level select |
| S (title) | Roll a new random seed |
| Arrows + Enter | Menu navigation |

Feel: acceleration + skid turns, coyote time (6 frames), jump buffering
(6 frames), variable jump height, terminal velocity, crouch hitbox
shrink, i-frame flicker on damage/respawn.

## Features

* **HP + power-ups (D1):** 3 hearts (max 6), damage + knockback +
  i-frames, HUD heart icons; timed star (invincibility), speed and jump
  power-ups; 100 coins = 1-up.
* **Elemental forms (D2):** fire (killing fireball), ice (freezing
  shard), lightning (instant area zap) — offensive only (forms never
  required to finish a level, D6).
* **Puzzle mechanics:** floor switches + latched doors, pressure plates +
  timed doors (bonus loot only, D5), breakable bricks (bump, form, or
  Charger dash), lava (lethal), moving spike hazards (worst-case modeled
  in the proof), key-shard objectives (collect N keys to unlock the goal,
  KEYS k/n HUD counter).
* **11 enemies:** Walker, Shellback (kickable shell), Flyer, Chaser,
  Spitter, Jumper + Shieldkin (frontal shield), Bomber (arcing bombs),
  Wallcrawler (clings to walls/ceilings), Charger (telegraphed dash),
  Needler (leading shots). Bosses: Boulder Brute / Crystal Golem /
  Warden Owl / Magma Monarch.
* **UX:** zone-themed palettes + ambient particles (leaves/embers/snow/
  rain), zone primer banners, first-time tutorial hints (toggle in
  Options), screen shake, particles, floaters, boss HP bar + WARNING
  banner, fade transitions, NEW BEST flags, victory stats incl. bosses
  defeated, spatial SFX (checkpoint/switch/shard/warp pan with distance),
  8 original chiptune tracks (title, A/B, C/D/E zone themes, boss, +
  jingles) — all compositions original.

## How procedural generation works

* Levels are stitched left->right from a library of **hand-authored chunks**
  (flat runs, gaps, stairs, pipe alleys, floating steps, island chains,
  spike trenches, enemy gauntlets, moving-platform bridges, switch/door
  puzzles, lava pits, timed-door bonus rooms, floor-spiker tracks) with a
  difficulty curve — seeded `random.Random(seed)`, so **same seed +
  difficulty + level index produce a byte-identical level**.
* Every chunk is bounded by the **jump envelope derived from the real
  physics constants** (never hard-coded guesses).
* The **validator** (`src/level/validator.py`) then *proves*
  completability with the **base kit only** (D6 — power-ups/forms are
  never required):
  1. reachability graph over standable tiles,
  2. every jump/fall edge verified by a **per-tick trajectory simulation**
     using the exact game physics (walls, ceilings, landings, spike
     hazards, worst-case moving-hazard bands, worst-case timed doors),
  3. an **augmented BFS** whose state is (cell, pressed switches, shard
     bit-mask) with dominance pruning, plus moving-platform ride edges,
  4. spawn -> goal search; on failure the generator retries (up to 20
     seeds) and finally falls back to a known-good template — the game
     **never ships an unwinnable level**.
* **Boss arenas** (zone finals) are carved into the level tail without
  changing the width formula; the proof covers arena *traversal*. Boss
  *defeat* is combat and is proven separately by **deterministic
  scripted-sim fights** (documented limitation, plan section 8.7).
* A headless perfect-player runner additionally drives the real physics
  over a curated level set in the test suite.

## Save system

Unlocks, best scores, settings (volumes/mute/tutorial) and play stats
persist to `save/progress.json` (gitignored): atomic tmp+replace writes,
tolerant loads (missing/corrupt/newer-schema files safely fall back to
defaults), `schema_version` + migration hook from day one. Full field-by-field
documentation: **`docs/SAVE_FORMAT.md`**.

## Architecture

````
src/
  main.py            launcher (opts into fade transitions)
  config.py          every tunable + jump envelope + ZONES table
  game.py            fixed 60 Hz loop, state machine, services, transitions
  progress.py        save/load (schema v1, atomic, tolerant)
  transition.py      deterministic fade for state switches
  inputs.py          key -> action mapping
  camera.py          SMW-style dead-zone camera + parallax offsets + shake
  physics.py         float-precision axis-separated swept AABB collision
  player.py          player state machine, HP, forms, power-ups, feel
  attacks.py         form attack projectiles (fire/ice)
  enemy_manager.py   camera activation, shells vs enemies, projectile drain
  hud.py             SMW row + hearts + power-up bar + boss bar + objective
  effects/           pooled particles, screen shake, floaters
  states/            title, playing, paused, level_select, options,
                     level_clear, game_over, victory
  level/             generator, validator, tiles, objects, level container
  enemies/           base FSM; walker, shellback, flyer, chaser, spitter,
                     jumper, shieldkin, bomber, wallcrawler, charger,
                     needler; boss.py base + bosses/ (4 concrete)
  assets/            runtime pixel-art factory (+ per-zone themed caches)
  audio/             SFX synth, music synth (8 tracks), mixer manager
                     (volumes, mute, spatial SFX, graceful degradation)
tests/               557 headless-safe tests (SDL dummy drivers)
docs/SAVE_FORMAT.md  save-file documentation
````

* Updates run on a **fixed 60 Hz accumulator** decoupled from rendering,
  so physics is deterministic and validator proofs stay meaningful.
* Rendering happens on a 320x240 virtual surface scaled with
  `pygame.transform.scale` (integer, never smoothed); off-camera
  tiles/entities are culled. Pooled effects and capped audio channels
  keep per-frame cost ~0.6 ms headless (audited, Session 24).

## Testing

`tests/` holds **557 headless-safe tests** across 23 files:

1. **Generator fuzz** (260 seeds x difficulties, all 20 levels) —
   validator-proven completability, entity rules, length bounds,
   determinism self-consistency (no frozen hashes by design).
2. **Physics** — measured jump envelope, coyote time, buffering,
   variable jump, crouch, platform carry.
3. **Enemies + bosses** — every behavior per type; arena invariants;
   scripted-sim fights that deterministically beat all 4 bosses.
4. **Combat** — stomp rules, 12-cell form x enemy matrix, Shieldkin
   front/back, star/i-frame/lives flows.
5. **Puzzles/objectives** — switches/doors/plates/timed doors (D5
   proof), breakables, lava, moving hazards (worst-case bands), key
   shards + goal lock.
6. **Progress/menus** — save roundtrip + corruption tolerance +
   migrations, unlock rules, pause/options/title/level-select flows,
   transitions, tutorial once-only, spatial-SFX math.
7. **Integration** — the real game driven headless through every state,
   including a full 20-level run that beats each zone boss.
8. **Audit guards** — D1 constants, pool caps, density growth, fight
   length windows (Phase 7a).

## Notes & honest limitations

* One dependency: `pygame-ce` (Python 3.10+; developed on 3.14). All
  art/audio is generated programmatically; original designs only (D7).
* **Mid-run resume** (saving a run in flight) is an unimplemented
  stretch goal (D4); the save schema reserves a `current_run` slot.
* The validator proves *traversal* for boss arenas; boss *defeat* is
  proven by the deterministic fight tests, not by reachability (plan
  section 8.7 — deliberate, documented).
* Suite runtime ~86 s (557 tests) on the dev machine.

