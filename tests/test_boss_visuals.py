"""SI-E (Phase E) boss visuals: phase palettes, wind-up poses, staged
defeat sequence (proposal 5.2/5.3/5.4 + 3.2). Headless draws compared via
tobytes; behavioral contracts stay in test_boss_framework/test_boss_fights
and must remain untouched."""

import pygame

from src import config

TILE = config.TILE
GROUND = config.GROUND_ROW
BOSS_KINDS = ("boulder_brute", "crystal_golem", "warden_owl", "magma_monarch")
# midpoints of the 10 defeat frames: 18 ticks stagger / 36 crumble / 36 explode
DEATH_MARKS = (3, 9, 15, 22, 31, 40, 49, 60, 72, 84)


def _cam():
    class C:
        x = 0.0
        y = 0.0
        ix = 0
        iy = 0

        def visible(self, rect):
            return True
    return C()


def _spawn(kind):
    from src.enemy_manager import spawn_enemy
    return spawn_enemy(kind, 3, GROUND)


def _shot(boss, tick):
    """Render one headless frame of the boss's inline draw()."""
    surf = pygame.Surface((config.VIEW_W, config.VIEW_H), pygame.SRCALPHA)
    boss.draw(surf, _cam(), None, tick)
    return pygame.image.tobytes(surf, "RGBA")


def _blank():
    return pygame.image.tobytes(
        pygame.Surface((config.VIEW_W, config.VIEW_H), pygame.SRCALPHA),
        "RGBA")


# ------------------------------------------------------- phase palettes 5.2
# ------------------------------------------------------- phase palettes 5.2
def test_boss_phase_draws_differ(pygame_ready):
    """Every boss renders three distinct frames across phases 0/1/2."""
    for kind in BOSS_KINDS:
        b = _spawn(kind)
        shots = []
        for ph in (0, 1, 2):
            b.phase = ph
            shots.append(_shot(b, 10))
        assert len(set(shots)) == 3, f"{kind}: phase visuals must differ"


def test_golem_core_exposure_and_fractures(pygame_ready):
    """Sealed vs exposed differs; both track the phase (5.2/5.4)."""
    g = _spawn("crystal_golem")
    g.phase = 0
    sealed = _shot(g, 10)
    g.exposed = True
    g.expose_t = 60
    open0 = _shot(g, 10)
    assert sealed != open0, "core must show while exposed"
    g.phase = 2
    open2 = _shot(g, 10)
    assert open0 != open2, "exposed core must scale with phase"
    g.exposed = False
    assert _shot(g, 10) != sealed, \
        "sealed fracture layer must differ from the clean phase-0 shell"


def test_monarch_crown_breaks_off_by_phase(pygame_ready):
    """Spike tips: full crown p0, middle spike gone p1, shattered p2."""
    m = _spawn("magma_monarch")
    r = m.rect

    def tip(px, phase):
        m.phase = phase
        surf = pygame.Surface((config.VIEW_W, config.VIEW_H),
                              pygame.SRCALPHA)
        m.draw(surf, _cam(), None, 0)
        return surf.get_at((px, r.y - 5))[3] > 0

    left, middle = r.x + 7, r.x + 15          # apexes of the ox=4/12 spikes
    assert tip(left, 0) and tip(middle, 0), "phase 0: crown intact"
    assert tip(left, 1) and not tip(middle, 1), "phase 1: one spike missing"
    assert not tip(left, 2) and not tip(middle, 2), "phase 2: shattered"


def test_monarch_vein_pulse_period_per_phase(pygame_ready):
    """Vein brightness alternates at the phase's period: 12/8/4 ticks."""
    m = _spawn("magma_monarch")
    for ph, period in ((0, 12), (1, 8), (2, 4)):
        m.phase = ph
        assert _shot(m, 0) != _shot(m, period), \
            f"phase {ph}: lava veins must pulse every {period} ticks"


# ------------------------------------------------------ wind-up poses 5.3
def test_brute_windup_pose_crouches_and_shakes(pygame_ready):
    """telegraph > 0 crouches the body; the shake alternates each pose."""
    b = _spawn("boulder_brute")
    idle = _shot(b, 0)
    b.telegraph = 20
    b.mode = "telegraph"
    w_even, w_odd = _shot(b, 0), _shot(b, 2)
    assert w_even != idle, "wind-up must change the pose"
    assert w_even != w_odd, "wind-up body must shake"
    b.telegraph = 0
    b.mode = "idle"
    assert _shot(b, 0) == idle, "pose fully relaxes with the telegraph"


# ------------------------------------------------------- owl details 5.4
def test_owl_gaze_tracks_player(flat_level):
    from src.player import Player
    o = _spawn("warden_owl")
    o.think(flat_level, Player(300, 12 * 16 - 26))     # player to the right
    assert o.pupil_dx == 2
    o.think(flat_level, Player(0, 12 * 16 - 26))       # sneaks up behind
    assert o.pupil_dx == 0
    o.think(flat_level, Player(o.cx - config.PLAYER_W / 2, 12 * 16 - 26))
    assert o.pupil_dx == 1, "neutral gaze straight ahead"


def test_owl_gaze_and_mode_feathers_change_pixels(pygame_ready):
    o = _spawn("warden_owl")
    o.mode = "hover"
    o.pupil_dx = 0
    left = _shot(o, 6)
    o.pupil_dx = 2
    right = _shot(o, 6)
    assert left != right, "pupils must lock onto the player"
    o.pupil_dx = 1
    hover = _shot(o, 6)
    o.mode = "telegraph"                    # telegraph=0: feathers only
    assert _shot(o, 6) != hover, "raised feathers on the wind-up"
    o.mode = "dive"
    assert _shot(o, 6) != hover, "swept-back feathers during the dive"


# ------------------------------------------------ boss defeat sequence 3.2
def test_boss_death_ten_distinct_frames(pygame_ready):
    """Sampling each of the 10 frame slots yields 10 distinct renders."""
    for kind in BOSS_KINDS:
        b = _spawn(kind)
        b.start_defeat()
        got = []
        for e in DEATH_MARKS:
            b.defeat_timer = b.DEFEAT_TICKS - e
            got.append(_shot(b, e))
        assert len(set(got)) == 10, f"{kind}: defeat frames not distinct"


def test_boss_death_draws_every_tick_then_vanishes(pygame_ready):
    """The whole 90-tick window renders headless; nothing draws after."""
    for kind in BOSS_KINDS:
        b = _spawn(kind)
        b.start_defeat()
        for e in range(b.DEFEAT_TICKS):
            b.defeat_timer = b.DEFEAT_TICKS - e
            _shot(b, e)                     # never raises
        b.defeat_timer = 0
        assert _shot(b, 90) == _blank(), \
            f"{kind}: corpse must vanish after the sequence"


def test_playing_draw_renders_real_boss_death(pygame_ready):
    """End-to-end smoke: real boss, real defeat, PlayingState draws."""
    from src.game import Game
    game = Game(seed=42, max_frames=None)
    game.new_run(seed=42)
    game.run.level_index = 4                # Green Hills arena: brute
    game.switch_state("playing")
    state = game.state
    lvl = state.level
    p = state.player
    p.x = float(lvl.arena_x0 * TILE + 6)
    p.y = float(GROUND * TILE - config.PLAYER_H)
    state.camera.snap_to(p.rect)
    boss = next(e for e in state.enemies.enemies
                if getattr(e, "is_boss", False))
    boss.active = True
    assert boss.KIND == "boulder_brute"
    boss.take_damage(boss.hp)               # killing blow -> staged defeat
    for _ in range(6):                      # stagger/crumble/explode draws
        for _ in range(15):
            state.update()
        state.draw(game.surface)
    assert boss.defeated, "defeat sequence must complete"


# ----------------------------------------------------- idle cycles (SI-G)
def test_ground_bosses_breathe(pygame_ready):
    """1 px bob toggles at each boss's own period; clean 2-state cycle."""
    for kind, period in (("boulder_brute", 32), ("crystal_golem", 36),
                         ("magma_monarch", 40)):
        b = _spawn(kind)
        assert _shot(b, 0) != _shot(b, period), f"{kind}: must breathe"
        assert _shot(b, 0) == _shot(b, 2 * period), \
            f"{kind}: breathing must be a clean 2-state cycle"


def test_ground_bosses_blink(pygame_ready):
    """Eyes close during the blink window (ticks = 28-31 mod 96)."""
    for kind in ("boulder_brute", "crystal_golem", "magma_monarch"):
        b = _spawn(kind)
        assert b.blinking(28) and not b.blinking(0), kind
        assert _shot(b, 0) != _shot(b, 28), f"{kind}: blink must draw"


def test_owl_wing_flap_cycle(pygame_ready):
    """Wings beat up/down every 8 ticks while the owl is idling."""
    o = _spawn("warden_owl")
    o.mode = "hover"
    assert _shot(o, 0) != _shot(o, 8), "wings must beat up/down"