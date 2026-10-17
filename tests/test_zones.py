"""Zone mapping (Phase 4a): 4 zones x 5 levels = 20, per-zone lengths."""

from src import config


def test_zone_and_level_mapping():
    z, l = config.zone_of, config.zone_level_of
    assert (z(0), l(0)) == (0, 0)
    assert (z(4), l(4)) == (0, 4)
    assert (z(5), l(5)) == (1, 0)
    assert (z(9), l(9)) == (1, 4)
    assert (z(19), l(19)) == (3, 4)
    assert len(config.ZONES) == 4
    assert config.LEVELS_PER_RUN == config.LEVELS_PER_ZONE * 4 == 20


def test_difficulty_for_spans_run():
    d = config.difficulty_for
    assert d(0) == 0.0
    assert d(config.LEVELS_PER_RUN - 1) == 1.0
    vals = [d(i) for i in range(config.LEVELS_PER_RUN)]
    assert all(a <= b for a, b in zip(vals, vals[1:])), "not monotone"


def test_per_zone_length_resets():
    f = config.level_length_screens
    z = config.zone_of
    zl = config.zone_level_of

    assert [f(z(i), zl(i)) for i in range(5)] == [6, 9, 12, 15, 18]
    assert [f(z(i), zl(i)) for i in range(5, 10)] == [6, 9, 12, 15, 18]
    assert [f(z(i), zl(i)) for i in range(10, 15)] == [10, 15, 20, 25, 30]
    assert [f(z(i), zl(i)) for i in range(15, 20)] == [10, 15, 20, 25, 30]

    assert f(z(5), zl(5)) == 6, "length must reset each zone"
    assert f(z(10), zl(10)) == 10, "length must reset each zone"
    assert f(z(19), zl(19)) == 30


def test_zone0_matches_new_world_width():
    """Slice 4 semantic change: zone 0 now starts at 6 screens and grows by 3."""
    from src.level.generator import generate_level
    for idx in range(5):
        lvl = generate_level(idx * 3 + 1, config.difficulty_for(idx), idx)
        assert lvl.tiles.w == config.level_length_screens(
            config.zone_of(idx), config.zone_level_of(idx)
        ) * config.TILES_PER_SCREEN + 18


def test_high_index_level_valid_and_deterministic():
    from src.level.generator import generate_level
    from src.level.validator import validate
    idx = 17                                     # zone 3, zone-level 2
    a = generate_level(99991, config.difficulty_for(idx), idx)
    b = generate_level(99991, config.difficulty_for(idx), idx)
    ok, reason = validate(a)
    assert ok, reason
    assert bytes(a.tiles.data) == bytes(b.tiles.data)
    assert a.tiles.w == config.level_length_screens(
        config.zone_of(idx), config.zone_level_of(idx)
    ) * config.TILES_PER_SCREEN + 18

def _assert_arena_carve(lvl):
    """Minimum append_arena invariants for a 30-screen zone-final tail."""
    from src.config import ARENA_COLS, GROUND_ROW, TILE

    assert lvl.has_arena
    assert lvl.boss_required
    assert lvl.arena_x0 == lvl.tiles.w - ARENA_COLS

    x0 = lvl.arena_x0
    ground = GROUND_ROW
    w = lvl.tiles.w

    # Open entry corridor and solid floor at the arena edge.
    assert not lvl.tiles.solid_at(x0 - 1, ground - 1)
    assert not lvl.tiles.solid_at(x0, ground - 1)
    assert lvl.tiles.solid_at(x0, ground)

    # At least two jump heights of vertical dodge space across the arena.
    perch = set(range(x0 + (ARENA_COLS - 4) // 2,
                      x0 + (ARENA_COLS + 4) // 2))
    clear_rows = 0
    for ty in range(2, ground):
        for tx in range(x0, w):
            solid = lvl.tiles.solid_at(tx, ty)
            if ty == ground - 3 and tx in perch:
                assert solid, "perch exists"
                continue
            assert not solid, f"row {ty} col {tx} must be clear"
        clear_rows += 1
    assert clear_rows >= 10

    # At least a six-tile flat runway with headroom.
    runway = 0
    for tx in range(x0, w):
        if (lvl.tiles.solid_at(tx, ground)
                and not lvl.tiles.solid_at(tx, ground - 1)
                and not lvl.tiles.solid_at(tx, ground - 2)):
            runway += 1
        else:
            runway = 0
    assert runway >= 6

    # Goal sits on the arena floor.
    assert lvl.goal is not None
    assert lvl.goal.rect.bottom == ground * TILE

    # A zone-final boss is present.
    from src.level.generator import BOSS_KINDS
    kinds = {kind for kind, _, _ in lvl.enemy_spawns}
    assert kinds & set(BOSS_KINDS), "30-screen zone-final missing its boss"


def test_30_screen_zone_final_arena_carve_is_valid():
    """Slice 4: longer zone finals must still carve a playable boss arena."""
    from src.level.generator import generate_level
    from src.level.validator import validate

    for idx in (14, 19):
        lvl = generate_level(31337 + idx, config.difficulty_for(idx), idx)
        ok, reason = validate(lvl)
        assert ok, f"idx={idx}: {reason}"
        assert lvl.tiles.w == config.level_length_screens(
            config.zone_of(idx), config.zone_level_of(idx)
        ) * config.TILES_PER_SCREEN + 18
        assert lvl.tiles.w == 30 * config.TILES_PER_SCREEN + 18
        _assert_arena_carve(lvl)




def test_run_context_finishes_at_20():
    from src.game import RunContext
    run = RunContext(seed=1)
    run.level_index = config.LEVELS_PER_RUN - 1
    assert not run.finished
    run.level_index = config.LEVELS_PER_RUN
    assert run.finished


def test_zone_music_selection():
    """Zone track pairs are wired per zone (placeholders until 4b)."""
    for zone in config.ZONES:
        assert zone["music_a"] and zone["music_b"]
        assert isinstance(zone["name"], str) and zone["name"]


# ------------------------------------------------------------------ 4b


def _playing(seed=7):
    from src.game import Game
    game = Game(seed=seed, max_frames=None)
    game.new_run(seed=seed)
    game.switch_state("playing")
    return game, game.state


def test_zone_palettes_complete():
    """Every themed zone palette covers exactly THEMED_KEYS; zone 0 defers
    to the legacy palette via None (merged with DEFAULT_PAL at build)."""
    from src.assets.asset_factory import THEMED_KEYS
    for z in config.ZONES[1:]:
        assert set(z["palette"]) == set(THEMED_KEYS), z["name"]
    assert config.ZONES[0]["palette"] is None


def test_zone0_palette_identity():
    """DEFAULT_PAL == the exact legacy palette constants (zone 0 identity)."""
    from src.assets import asset_factory as af
    assert af.DEFAULT_PAL == {
        "sky_top": (92, 148, 250), "sky_bottom": (172, 214, 255),
        "cloud": (252, 253, 255), "cloud_dk": (216, 228, 248),
        "hills_far_body": (94, 150, 152), "hills_far_crest": (130, 188, 178),
        "hills_near_body": (56, 138, 74), "hills_near_crest": (98, 180, 98),
        "dirt": af.DIRT, "dirt_dk": af.DIRT_DK, "dirt_lt": af.DIRT_LT,
        "grass": af.GRASS, "grass_dk": af.GRASS_DK, "grass_lt": af.GRASS_LT,
        "brick": af.BRICK, "brick_dk": af.BRICK_DK,
    }


def test_for_zone_identity_and_theming(pygame_ready):
    from src.assets.asset_factory import AssetFactory
    assets = AssetFactory()
    assert assets.for_zone(0) is assets       # zone 0 = the legacy factory
    base_sky = assets.sky().get_at((5, 5))
    base_cap = assets.terrain(0).get_at((2, 1))
    for zone in (1, 2, 3):
        themed = assets.for_zone(zone)
        assert themed is not assets
        assert assets.for_zone(zone) is themed    # cached
        assert themed.sky().get_at((5, 5)) != base_sky
        assert themed.terrain(0).get_at((2, 1)) != base_cap


def test_zone_music_registered():
    """The 3 new original zone tracks render headless and loop."""
    from src.audio.music_synthesizer import MUSIC_BUILDERS, LOOPING_MUSIC
    for name in ("level_c", "level_d", "level_e"):
        assert name in MUSIC_BUILDERS
        assert name in LOOPING_MUSIC
        assert len(MUSIC_BUILDERS[name]()) > 1000


def test_ambient_spawns_within_cap(pygame_ready):
    """fx.ambient spawns within the particle cap and draws headless."""
    game, state = _playing()
    fx = game.fx
    for _ in range(400):
        fx.ambient("snow", state.camera)
    assert 0 < len(fx.particles) <= config.PARTICLE_CAP
    fx.update()
    fx.draw(game.surface, state.camera)


def test_playing_update_spawns_ambient(pygame_ready):
    """PlayingState.update calls the ambient tick on the zone cadence."""
    game, state = _playing()
    for _ in range(config.AMBIENT_INTERVAL + 1):
        state.update()
    assert len(game.fx.particles) > 0


# ------------------------------------------- enemy zone palettes (SI-H)
def test_zone_enemy_frames_complete_and_tinted(pygame_ready):
    """Zones 1-3 mirror every cached frame + hit variant, tinted with the
    per-pixel alpha untouched; zone 0 keeps base identity (no copy)."""
    import pygame
    from src.assets import AssetFactory
    from src.assets.asset_factory import (ENEMY_FRAMES, ENEMY_HIT_FRAMES,
                                          ENEMY_ZONE_FRAMES,
                                          ENEMY_ZONE_HIT_FRAMES)
    AssetFactory()                              # builds all caches
    assert 0 not in ENEMY_ZONE_FRAMES, "zone 0 must reuse the base dicts"
    for zone in (1, 2, 3):
        assert set(ENEMY_ZONE_FRAMES[zone]) == set(ENEMY_FRAMES), zone
        assert set(ENEMY_ZONE_HIT_FRAMES[zone]) == set(ENEMY_HIT_FRAMES)
    key = ("walker", "patrol", 0)
    base, z1 = ENEMY_FRAMES[key], ENEMY_ZONE_FRAMES[1][key]
    assert z1 is not base and z1.get_size() == base.get_size()
    assert pygame.image.tobytes(z1, "RGBA") != pygame.image.tobytes(
        base, "RGBA"), "tint must change the pixels"

    def alpha(s):
        return bytes(pygame.image.tobytes(s, "RGBA"))[3::4]

    assert alpha(z1) == alpha(base), "per-pixel alpha must be preserved"


def test_zone_enemy_dispatch_uses_factory_zone(pygame_ready):
    """A themed factory serves its zone's frames; the base factory (and
    every pinned identity test) keeps serving the base frames."""
    import pygame
    from src.enemy_manager import spawn_enemy
    from src.assets import AssetFactory
    from src.assets.asset_factory import ENEMY_FRAMES, ENEMY_ZONE_FRAMES
    fac = AssetFactory()
    w = spawn_enemy("walker", 5, 12)
    w.facing = 1                               # unflipped identity (rule 7)
    w.anim_t = 0
    assert fac.enemy_frame(w) is ENEMY_FRAMES[("walker", "walk", 0)]
    themed = fac.for_zone(2)
    assert themed.enemy_frame(w) is \
        ENEMY_ZONE_FRAMES[2][("walker", "walk", 0)]
    assert fac.enemy_frame(w) is ENEMY_FRAMES[("walker", "walk", 0)], \
        "base factory must keep serving base frames"
    w.hit_flash = 5                            # themed recoil variant too
    assert themed.enemy_frame(w) is not fac.enemy_frame(w)
    pygame.image.tobytes(themed.enemy_frame(w), "RGBA")   # renders headless


def test_zone_death_frames_tinted(pygame_ready):
    """Corpses pick up the zone wash through the same dispatch."""
    import pygame
    from src.enemy_manager import spawn_enemy
    from src.assets import AssetFactory
    fac = AssetFactory()
    w = spawn_enemy("walker", 5, 12)
    w.facing = 1
    w.start_dying()
    w.hit_flash = 0                            # isolate the death frame
    base = pygame.image.tobytes(fac.enemy_frame(w), "RGBA")
    z3 = pygame.image.tobytes(fac.for_zone(3).enemy_frame(w), "RGBA")
    assert z3 != base, "corpse must pick up the zone wash"
