LI seed: `python run_game.py --seed N`; from the title screen, `S`
rolls a new random seed.

## Features

* **5 levels per run** with rising difficulty (0 → 1.0), lives (3),
  score, coins (100 coins = 1-up), countdown timer with time bonus,
  checkpoints, pause, game over, victory screen.
* **6 enemy types**, each with distinct AI: Walker (patrol, turns at
  walls/ledges), Shellback (stomp → kickable shell that crushes other
  enemies), Flyer (sine-wave hover, no gravity), Chaser (aggro radius,
  ground pursuit), Spitter (turret firing projectiles), Jumper
  (homing hops). Enemies activate only within ~1.5 screens of the
  camera.
* **Combat**: stomp kills (spiked STOMP_PROOF enemies hurt instead),
  shell stomp/kick/stop states, sliding-shell kills, i-frame flicker
  after respawn.
* **World objects**: warp pipes (typed links, hold ↓), coins, brick /
  question blocks (bump from below), spike hazards, pits, moving
  platforms (one-way carry), checkpoints, goal gate.
* **Graphics**: everything is generated at startup by
  `src/assets/asset_factory.py` — 16-way autotiled terrain, animated
  question blocks, spinning coins, per-state animated player sprite
  (idle/run/skid/jump/fall/crouch/death), per-type enemy sprites with
  walk/shell/squash frames, 3-layer parallax background (sky gradient,
  two tileable hill ranges, drifting clouds), SMW-style HUD.
* **Audio**: all chiptune sound and music is synthesized at runtime
  (`src/audio/`): 15 SFX (jump, coin, stomp, kick, death, 1-up, warp,
  checkpoint, brick, menu…) plus original looping tracks (title,
  level A/B) and clear/game-over jingles — original compositions, no
  sampled melodies. M mutes anywhere; the game degrades silently to
  muted mode if no audio device exists.

## Architecture

```
src/
  main.py            launcher (works as script or module)
  config.py          every tunable constant + derived jump envelope
  game.py            fixed-timestep loop (60 Hz), state machine, services
  inputs.py          key -> action mapping
  camera.py          SMW-style dead-zone camera + parallax offsets
  physics.py         float-precision axis-separated swept AABB collision
  player.py          player state machine + feel
  enemy_manager.py   camera activation, shells vs enemies, projectiles
  hud.py             score/coins/lives/time/world display
  states/            title, playing, paused, level_clear, game_over, victory
  level/             generator, validator, tiles, objects, level container
  enemies/           base FSM + walker, flyer, chaser, spitter, jumper
  assets/            runtime pixel-art factory
  audio/             SFX synth, music synth, mixer manager
tests/               pytest suite (headless-safe via SDL dummy drivers)
```

* Updates run on a **fixed 60 Hz accumulator** decoupled from rendering,
  so physics is deterministic and validator proofs stay meaningful.
* Rendering happens on a 400×240 virtual surface scaled ×3 with
  `pygame.transform.scale` (integer, never smoothed) for a crisp pixel
  look; off-camera tiles/entities are culled.

## Testing

`tests/` covers:

1. **Generator fuzz** — 200 seeds × difficulties: validator-proven
   completability, entity rules (enemies on ground, warp pipes paired,
   no coins inside walls), length bounds, determinism hashes.
2. **Physics** — landing, wall blocking, *measured* jump height and
   distance within the generator's envelope, coyote time, jump
   buffering, variable jump, crouch, moving-platform carry.
3. **Enemies** — every required behavior (ledge/wall turning, shell
   lifecycle, sine path, ground-only chasing with wall stop, projectile
   lifecycle, homing hops, camera activation).
4. **Combat/lives** — stomp rules, spike-proof rule, respawn i-frames,
   checkpoint respawn, game over at 0 lives.
5. **Audio** — synth output validity and graceful mixer-less operation.
6. **Integration smoke** — the real game driven headless through
   title → play → pause → clear → next level → victory and death →
   game over → title, with every state drawn.
7. **Scripted playtest** — a perfect-player controller driving the real
   physics to the goal on a curated set of representative levels.

## Notes

* One dependency: `pygame-ce` (Python 3.10+; developed on 3.14).
* All art/audio is generated programmatically; original designs only.
