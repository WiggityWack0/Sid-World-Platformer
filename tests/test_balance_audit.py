"""Balance + performance audit (Phase 7a): pinned regression guards for
the recorded audit findings. NO wall-clock asserts (plan anti-pattern) —
perf numbers live in the Progress Log; these tests pin the invariants
that must not silently drift."""

from src import config


# ------------------------------------------------------- balance (7a)
def test_d1_envelope_constants_pinned():
    """Damage cadence matches plan D1 (audit-verified)."""
    assert config.HEARTS_START == 3
    assert config.HEARTS_MAX == 6
    assert config.HURT_INVULN == 90
    assert config.RESPAWN_INVULN == 90


def test_pool_caps_pinned():
    """Pool/channel caps verified under spam during the 7a audit."""
    assert config.PARTICLE_CAP == 400
    from src.audio.mixer_manager import AudioManager
    assert AudioManager.NUM_CHANNELS == 12


def test_density_grows_within_length_class():
    """Recorded 7a finding: per-screen enemy density rises WITHIN a
    zone-length class (zl4 finals: idx 9 < idx 19). Zone-length resets
    legitimately make zl0 levels breather levels."""
    from src.level.generator import generate_level

    def mean_per_screen(idx):
        screens = config.level_length_screens(
            config.zone_of(idx), config.zone_level_of(idx))
        total = 0.0
        for seed in range(8):
            lvl = generate_level(seed * 37 + 5, config.difficulty_for(idx),
                                 idx)
            total += len([k for k, _, _ in lvl.enemy_spawns
                          if k not in ("boulder_brute", "crystal_golem",
                                       "warden_owl", "magma_monarch")])
        return total / 8 / screens

    assert mean_per_screen(19) > mean_per_screen(9), \
        "late zl4 levels must be denser than early zl4 levels"


def test_zone_finals_always_have_arena_and_boss():
    """Recorded 7a finding: every zone-final spawns its arena + boss."""
    from src.level.generator import BOSS_KINDS, generate_level
    for idx in (4, 9, 14, 19):
        lvl = generate_level(11, config.difficulty_for(idx), idx)
        assert lvl.has_arena and lvl.boss_required
        kinds = {k for k, _, _ in lvl.enemy_spawns}
        assert kinds & set(BOSS_KINDS), f"idx={idx} missing its boss"


def test_fights_within_window(monkeypatch, pygame_ready):
    """Recorded 7a fight lengths: brute 3.2s, golem 5.3s, owl 13.4s,
    monarch 6.4s — all inside the 2-15s (120-900 tick) window."""
    from test_boss_fights import _boss_game, _enter_arena, _run_fight
    for idx in (4, 9, 14, 19):
        game, state = _boss_game(idx)
        boss = _enter_arena(state)
        ticks = _run_fight(state, boss, monkeypatch, max_ticks=1800)
        assert not boss.alive, f"idx={idx} fight never ended"
        assert 30 <= ticks <= 900, \
            f"idx={idx} fight length {ticks} ticks outside 2-15s window"
