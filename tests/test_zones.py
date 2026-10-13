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
    zl = config.zone_level_of
    assert [f(zl(i)) for i in range(5)] == [2, 3, 4, 5, 6]
    assert f(zl(5)) == 2, "length must reset each zone"
    assert f(zl(19)) == 6


def test_zone0_matches_old_world_width():
    """Recorded semantic change scope: idx 0-4 keep the OLD widths."""
    from src.level.generator import generate_level
    for idx in range(5):
        lvl = generate_level(idx * 3 + 1, config.difficulty_for(idx), idx)
        assert lvl.tiles.w == (config.START_LEN_SCREENS
                               + idx * config.LEN_GROWTH
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
    assert a.tiles.w == (config.START_LEN_SCREENS
                         + config.zone_level_of(idx) * config.LEN_GROWTH
                         ) * config.TILES_PER_SCREEN + 18


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
