"""Enemy AI: per-type behaviors, combat rules, manager wiring."""

import pygame

from src import config
from src.enemies import (Chaser, Enemy, Flyer, Jumper, Shellback, Spitter,
                         Walker, contact_result)
from src.enemies.spitter import Projectile
from src.enemy_manager import EnemyManager
from src.level import tiles as T
from src.level.level import Level
from src.player import Player


class FakeCam:
    x = 0.0
    y = 0.0
    ix = 0
    iy = 0


def _arena(cols=30, wall_col=None):
    lvl = Level(cols, 18)
    for tx in range(cols):
        for ty in range(12, 18):
            lvl.tiles.set(tx, ty, T.SOLID)
    if wall_col is not None:
        lvl.tiles.set(wall_col, 11, T.SOLID)
        lvl.tiles.set(wall_col, 10, T.SOLID)
    return lvl


GROUND_Y = 12 * 16


def test_walker_turns_at_ledge():
    lvl = Level(20, 18)                      # ground only cols 0..4
    for tx in range(5):
        for ty in range(12, 18):
            lvl.tiles.set(tx, ty, T.SOLID)
    w = Walker(2 * 16, GROUND_Y - 16)
    w.active = True
    w.facing = 1
    player = Player(0, GROUND_Y - 26)
    saw_turn = False
    for _ in range(40):
        w.update(lvl, player)
        if w.facing == -1:
            saw_turn = True
    for _ in range(160):
        w.update(lvl, player)
    assert saw_turn, "walker never turned at the ledge"
    assert w.rect.right <= 5 * 16 + 2, "walker walked off the ledge"
    assert w.y == GROUND_Y - 16, "walker left the ground plane"


def test_walker_turns_at_wall():
    lvl = _arena(wall_col=8)
    w = Walker(5 * 16, GROUND_Y - 16)
    w.active = True
    w.facing = 1
    player = Player(0, GROUND_Y - 26)
    saw_turn = False
    for _ in range(40):
        w.update(lvl, player)
        if w.facing == -1:
            saw_turn = True
    for _ in range(160):
        w.update(lvl, player)
    assert saw_turn, "walker never turned around at the wall"
    assert w.rect.right <= 8 * 16 + 2


def test_contact_rules_stomp_vs_side():
    lvl = _arena()
    w = Walker(100, GROUND_Y - 16)
    player = Player(100, GROUND_Y - 16)
    assert contact_result(player, w) == "hurt"
    player = Player(100, GROUND_Y - 16 - 20)
    player.vy = 4.0
    assert contact_result(player, w) == "stomp"
    assert w.stomped(player) == "stomp"
    assert w.state == "dying"

    class Spiky(Enemy):
        STOMP_PROOF = True

    spiky = Spiky(100, GROUND_Y - 16)
    player = Player(100, GROUND_Y - 16 - 20)
    player.vy = 4.0
    assert contact_result(player, spiky) == "hurt"   # stomping spikes hurts


def test_shell_stomp_kick_and_wall_bounce():
    lvl = _arena(wall_col=10)
    s = Shellback(8 * 16, GROUND_Y - 16)
    s.active = True
    player = Player(8 * 16, GROUND_Y - 16 - 20)
    player.vy = 4.0
    assert s.stomped(player) == "stomp"
    assert s.state == "shell" and s.vx == 0
    kicker = Player(int(s.x) + 24, GROUND_Y - 16)   # stand to the right
    assert s.stomped(kicker) == "kick"
    assert s.sliding and s.vx > 0
    player2 = Player(int(s.x) + 4, GROUND_Y - 16)
    assert s.side_contact(player2) == "harm"
    s.vx = 0.0
    assert s.side_contact(player2) == "kicked"
    # bounce off the wall while sliding
    s.state = "shell"
    s.shell_timer = 999
    s.vx = config.SHELL_SLIDE_SPEED
    s.x = 9 * 16
    for _ in range(60):
        s.update(lvl, Player(0, GROUND_Y - 26))
        if s.wall_hit:
            break
    assert s.vx < 0, "shell did not bounce off the wall"
    s.shell_timer = 2
    for _ in range(6):
        s.update(lvl, Player(0, GROUND_Y - 26))
    assert s.state == "patrol"


def test_sliding_shell_kills_other_enemies(flat_level):
    mgr = EnemyManager([("shellback", 6, 12), ("walker", 10, 12)])
    for e in mgr.enemies:
        e.active = True
    shell = mgr.enemies[0]
    walker = mgr.enemies[1]
    shell.state = "shell"
    shell.shell_timer = 10000
    shell.vx = config.SHELL_SLIDE_SPEED
    cam = FakeCam()
    player = Player(0, 12 * 16 - 26)
    for _ in range(200):
        mgr.update(flat_level, player, cam)
        if walker.state == "dying":
            break
        shell.vx = config.SHELL_SLIDE_SPEED
        shell.state = "shell"
        shell.shell_timer = 10000
    assert walker.state == "dying", "shell never hit the walker"
    for _ in range(40):                   # let the corpse timer run out
        mgr.update(flat_level, player, cam)
    assert walker not in mgr.enemies, "dead walker not removed"


def test_flyer_stays_on_sine_path():
    lvl = _arena()
    f = Flyer(100, 100)
    f.active = True
    player = Player(0, GROUND_Y - 26)
    anchor = (f.anchor_x, f.anchor_y)
    for _ in range(300):
        f.update(lvl, player)
    assert abs(f.x - anchor[0]) <= config.FLYER_AMP_X + 2
    assert abs(f.y - anchor[1]) <= config.FLYER_AMP_Y + 2
    assert not f.GRAVITY


def test_chaser_chases_on_ground_and_walls_stop_it():
    lvl = _arena(wall_col=14)
    c = Chaser(6 * 16, GROUND_Y - 16)
    c.active = True
    player = Player(15 * 16, GROUND_Y - 26)   # just past the wall
    for _ in range(40):
        c.update(lvl, player)
    assert c.state == "chase"
    assert c.x > 6 * 16 + 30, "chaser did not move toward the player"
    for _ in range(120):
        c.update(lvl, player)
    assert c.rect.right <= 14 * 16 + 2, "chaser tunneled through wall"
    assert c.y >= GROUND_Y - 16 - 2, "chaser left the ground"
    player.x = 1 * 16                     # player flees far away
    player.y = GROUND_Y - 26
    c.x = 28 * 16
    for _ in range(40):
        c.update(lvl, player)
    assert c.state == "patrol"


def test_spitter_fires_and_projectile_despawns():
    lvl = _arena(cols=40)
    sp = Spitter(5 * 16, GROUND_Y - 20)
    sp.active = True
    player = Player(12 * 16, GROUND_Y - 26)
    sp.update(lvl, player)
    assert not sp.shots
    sp.cooldown = 0
    sp.update(lvl, player)
    assert len(sp.shots) == 1, "spitter did not fire with player in range"
    proj = sp.shots[0]
    assert proj.rect.centerx > sp.rect.centerx
    p2 = Projectile(39 * 16, GROUND_Y - 8, 1)
    for _ in range(400):
        p2.update(lvl)
        if p2.dead:
            break
    assert p2.dead, "projectile never despawned"


def test_jumper_hops_toward_player():
    lvl = _arena()
    j = Jumper(6 * 16, GROUND_Y - 16)
    j.active = True
    player = Player(9 * 16, GROUND_Y - 26)
    hopped = False
    for _ in range(150):
        j.update(lvl, player)
        if not j.on_ground and j.vy < 0:
            hopped = True
            break
    assert hopped, "jumper never hopped"
    assert j.facing == 1, "jumper hopped away from the player"


def test_enemies_freeze_when_inactive():
    lvl = _arena()
    w = Walker(5 * 16, GROUND_Y - 16)
    w.active = False
    x0 = w.x
    for _ in range(30):
        w.update(lvl, Player(0, GROUND_Y - 26))
    assert w.x == x0, "inactive enemy moved"


def test_manager_activation_by_camera():
    lvl = _arena(cols=80)
    mgr = EnemyManager([("walker", 4, 12), ("walker", 60, 12)])
    cam = FakeCam()
    cam.x = 0.0
    player = Player(32, GROUND_Y - 26)
    mgr.update(lvl, player, cam)
    assert mgr.enemies[0].active and not mgr.enemies[1].active
    cam.x = 50 * 16
    mgr.update(lvl, player, cam)
    assert mgr.enemies[1].active


# ------------------------------------------------- hit flash & death (SI-A)
def test_hit_flash_state_machine():
    """Lethal hits trigger the 6-tick recoil: 0.8 -> 0.9 -> 1.0 scale."""
    w = Walker(100, GROUND_Y - 16)
    assert w.hit_flash == 0 and w.hit_scale == 1.0
    assert Enemy.DEATH_TICKS == 30 and Enemy.HIT_FLASH_TICKS == 6
    w.start_dying()
    assert w.hit_flash == Enemy.HIT_FLASH_TICKS
    assert w.hit_scale == 0.8
    lvl = _arena()
    player = Player(0, GROUND_Y - 26)
    scales = []
    for _ in range(Enemy.HIT_FLASH_TICKS):
        w.update(lvl, player)
        scales.append(w.hit_scale)
    assert w.hit_flash == 0 and w.hit_scale == 1.0
    assert scales == [0.8, 0.9, 0.9, 1.0, 1.0, 1.0]


def test_hit_flash_nonlethal_trigger_and_reset():
    """Non-lethal reactions can flash without dying; reset clears both."""
    w = Walker(100, GROUND_Y - 16)
    w.start_hit_flash()
    assert w.hit_flash == Enemy.HIT_FLASH_TICKS
    assert w.alive and w.state == "patrol"
    w.reset()
    assert w.hit_flash == 0 and w.hit_scale == 1.0


def test_death_timer_is_30_and_manager_culls():
    """SI-A: corpses linger 30 ticks (was 26), then the manager culls."""
    lvl = _arena(cols=40)
    mgr = EnemyManager([("walker", 5, 12)])
    w = mgr.enemies[0]
    w.start_dying()
    assert w.death_timer == Enemy.DEATH_TICKS == 30
    cam = FakeCam()
    player = Player(0, GROUND_Y - 26)
    for _ in range(29):
        mgr.update(lvl, player, cam)
        assert w in mgr.enemies, "corpse culled too early"
    mgr.update(lvl, player, cam)
    assert w not in mgr.enemies, "dead walker not removed after 30 ticks"


def test_apply_hit_flash_phases(pygame_ready):
    """Phase 0/1/2: 0.8x white, 0.9x pale yellow, 1.0x normal colors."""
    from src.assets.asset_factory import _apply_hit_flash, make_surface
    src = make_surface(16, 16)
    src.fill((200, 100, 50, 255), pygame.Rect(2, 2, 12, 12))
    p0 = _apply_hit_flash(src, 0)
    p1 = _apply_hit_flash(src, 1)
    p2 = _apply_hit_flash(src, 2)
    assert p0.get_size() == (12, 12)
    assert p1.get_size() == (14, 14)
    assert p2.get_size() == (16, 16)
    assert p2.get_at((3, 3))[:3] == (200, 100, 50)   # untouched
    r, g, b, a = p0.get_at((5, 5))                   # 60% white over body
    assert a == 255
    assert abs(r - 233) <= 2 and abs(g - 193) <= 2 and abs(b - 173) <= 2
    assert p0.get_at((0, 0))[3] == 0                 # alpha preserved


def test_hit_frame_cache_covers_every_enemy_frame(pygame_ready):
    from src.assets import AssetFactory
    from src.assets.asset_factory import ENEMY_FRAMES, ENEMY_HIT_FRAMES
    AssetFactory()
    assert ENEMY_FRAMES, "no enemy frames built"
    for key in ENEMY_FRAMES:
        for hp in (0, 1, 2):
            assert (key, hp) in ENEMY_HIT_FRAMES, f"missing hit frame {key}/{hp}"


def test_enemy_frame_uses_hit_variants_while_flashing(pygame_ready, flat_level):
    from src.assets import AssetFactory
    from src.assets.asset_factory import ENEMY_FRAMES
    from src.enemy_manager import spawn_enemy
    fac = AssetFactory()
    w = spawn_enemy("walker", 5, 12)
    w.start_dying()
    player = Player(0, GROUND_Y - 26)
    sizes = []
    for _ in range(6):
        sizes.append(fac.enemy_frame(w).get_size())
        w.update(flat_level, player)
    assert sizes == [(12, 12), (12, 12), (14, 14), (14, 14),
                     (16, 16), (16, 16)]
    assert w.hit_flash == 0
    # 6 ticks elapsed during the flash -> death phase 1 (SI-D)
    assert fac.enemy_frame(w) is ENEMY_FRAMES[("walker", "dying", 1)]
    # left-facing flip path composes the hit key without error
    c = spawn_enemy("chaser", 5, 12)
    assert c.facing == -1
    base = fac.enemy_frame(c)
    c.start_hit_flash()
    assert fac.enemy_frame(c) is not base


# ------------------------------------------------------- walk cycles (SI-B)
SI_WALK_KINDS = ("walker", "shellback", "shieldkin", "bomber", "wallcrawler")


def test_walk_cycle_frames_exist(pygame_ready):
    """All five ground enemies get a distinct 4-frame stride (walk 0..3)."""
    from src.assets import AssetFactory
    from src.assets.asset_factory import ENEMY_FRAMES
    AssetFactory()
    for kind in SI_WALK_KINDS:
        frames = [ENEMY_FRAMES.get((kind, "walk", p)) for p in range(4)]
        assert all(f is not None for f in frames), f"{kind}: missing walk frame"
        blobs = [pygame.image.tobytes(f, "RGBA") for f in frames]
        assert len(set(blobs)) == 4, f"{kind}: walk frames not all distinct"
        # the old patrol fallback keys still exist for the generic path
        for p in range(2):
            assert ENEMY_FRAMES.get((kind, "patrol", p)) is not None


def test_walk_dispatch_cycles_four_frames(pygame_ready):
    """Dispatch selects walk_0..3 at (anim_t // 6) % 4 — deterministic."""
    from src.assets import AssetFactory
    from src.assets.asset_factory import ENEMY_FRAMES
    from src.enemy_manager import spawn_enemy
    fac = AssetFactory()
    w = spawn_enemy("walker", 5, 12)
    w.facing = 1                              # unflipped for direct compare
    got = []
    for t in range(24):                       # one full 4-frame cycle
        w.anim_t = t
        got.append(fac.enemy_frame(w))
    expect = [ENEMY_FRAMES[("walker", "walk", (t // 6) % 4)]
              for t in range(24)]
    assert got == expect
    assert len({id(img) for img in got}) == 4, "stride is not cycling 4 frames"


def test_flyer_body_bob(pygame_ready):
    """Downstroke drops the body 1px (proposal 1.2): belly reaches row 13
    only on frame 1."""
    from src.assets import AssetFactory
    from src.assets.asset_factory import ENEMY_FRAMES
    AssetFactory()
    up = ENEMY_FRAMES[("flyer", "patrol", 0)]
    down = ENEMY_FRAMES[("flyer", "patrol", 1)]
    assert pygame.image.tobytes(up, "RGBA") != \
        pygame.image.tobytes(down, "RGBA")
    assert up.get_at((8, 5))[3] == 255        # body on the upstroke
    assert down.get_at((8, 13))[3] == 255     # belly shifted down 1px
    assert up.get_at((8, 13))[3] == 0


# ------------------------------------------- poses & telegraphs (SI-C)
def _fac_enemy(kind):
    """Factory + right-facing spawned enemy (unflipped for identity checks)."""
    from src.assets import AssetFactory
    from src.enemy_manager import spawn_enemy
    fac = AssetFactory()
    e = spawn_enemy(kind, 5, 12)
    e.facing = 1
    return fac, e


def test_spitter_attack_pose_dispatch(pygame_ready):
    from src.assets.asset_factory import ENEMY_FRAMES
    fac, sp = _fac_enemy("spitter")
    assert fac.enemy_frame(sp) is ENEMY_FRAMES[("spitter", "patrol", 0)]
    sp.windup = 1
    assert fac.enemy_frame(sp) is ENEMY_FRAMES[("spitter", "attack", 0)]
    sp.windup = 0
    sp.flash = 10                                # just fired: execute
    assert fac.enemy_frame(sp) is ENEMY_FRAMES[("spitter", "attack", 1)]
    sp.flash = 3                                 # settling: recovery
    assert fac.enemy_frame(sp) is ENEMY_FRAMES[("spitter", "attack", 2)]
    blobs = {pygame.image.tobytes(ENEMY_FRAMES[("spitter", "attack", p)],
                                  "RGBA") for p in range(3)}
    assert len(blobs) == 3, "attack poses not visually distinct"


def test_spitter_windup_sets_flag_in_think(flat_level):
    from src.enemies.spitter import Spitter
    from src.player import Player
    sp = Spitter(5 * 16, 12 * 16 - 20)
    sp.active = True
    player = Player(10 * 16, 12 * 16 - 26)      # level with the turret
    sp.cooldown = config.SPITTER_WINDUP + 1     # one tick from the telegraph
    sp.update(flat_level, player)
    assert sp.windup == 1, "no wind-up telegraph at end of cooldown"
    assert not sp.shots
    for _ in range(config.SPITTER_WINDUP + 2):  # wind-up then fire
        sp.update(flat_level, player)
    assert sp.shots, "spitter never fired"


def test_needler_barrel_glow_dispatch_and_think(pygame_ready, flat_level):
    from src.assets.asset_factory import ENEMY_FRAMES
    from src.enemies.needler import Needler
    from src.player import Player
    fac, n = _fac_enemy("needler")
    assert fac.enemy_frame(n) is ENEMY_FRAMES[("needler", "patrol", 0)]
    n.barrel_glow = 1                            # think() computes the tier
    assert fac.enemy_frame(n) is ENEMY_FRAMES[("needler", "attack", 0)]
    n.barrel_glow = 2
    assert fac.enemy_frame(n) is ENEMY_FRAMES[("needler", "attack", 1)]
    n.barrel_glow = 0
    n.flash = 6
    assert fac.enemy_frame(n) is ENEMY_FRAMES[("needler", "attack", 2)]
    n.flash = 2
    assert fac.enemy_frame(n) is ENEMY_FRAMES[("needler", "attack", 3)]
    # think() ramps the glow as the cooldown drains
    n2 = Needler(5 * 16, 12 * 16 - 16)
    n2.active = True
    player = Player(20 * 16, 12 * 16 - 26)
    for _ in range(config.NEEDLER_COOLDOWN):
        n2.update(flat_level, player)
    assert n2.barrel_glow == 2, "barrel must glow bright when ready"


def test_charger_horn_glow_dispatch_and_ramp(pygame_ready, flat_level):
    from src.assets.asset_factory import ENEMY_FRAMES
    from src.player import Player
    fac, c = _fac_enemy("charger")
    c.windup = config.CHARGER_WINDUP
    c.horn_glow = 1
    assert fac.enemy_frame(c) is ENEMY_FRAMES[("charger", "windup", 0)]
    c.horn_glow = 3
    assert fac.enemy_frame(c) is ENEMY_FRAMES[("charger", "windup", 2)]
    c.state = "attack"
    assert fac.enemy_frame(c) is ENEMY_FRAMES[("charger", "attack", 0)]
    c.state, c.windup, c.anim_t = "patrol", 0, 0
    assert fac.enemy_frame(c) is ENEMY_FRAMES[("charger", "patrol", 0)]
    # think() ramps horn glow 1 -> 3 across the wind-up (never decreases)
    from src.enemy_manager import spawn_enemy
    c2 = spawn_enemy("charger", 4, 12)
    c2.active = True
    player = Player(8 * 16, 12 * 16 - 26)
    glows = []
    for _ in range(config.CHARGER_WINDUP):
        c2.update(flat_level, player)
        if c2.windup > 0 and c2.horn_glow:
            glows.append(c2.horn_glow)
    assert glows and glows == sorted(glows)
    assert glows[-1] == 3, "horns must peak white right before the dash"


def test_chaser_gaze_tracks_player(pygame_ready, flat_level):
    from src.assets.asset_factory import ENEMY_FRAMES
    from src.enemies.chaser import Chaser
    from src.player import Player
    fac, c = _fac_enemy("chaser")
    c.facing = 1
    player = Player(300, 80)                     # ahead, but too low to aggro
    c.think(flat_level, player)
    assert c.pupil_dx == 1
    player.x = 0                                 # sneaks up behind (chaser x~88)
    c.think(flat_level, player)
    assert c.pupil_dx == -1
    back = fac.enemy_frame(c)
    c.pupil_dx = 1
    fwd = fac.enemy_frame(c)
    assert back is not fwd, "gaze frames must differ"
    assert fwd is ENEMY_FRAMES[("chaser", "patrol", 0, 1)]
    c.state = "chase"
    c.pupil_dx = 2
    assert fac.enemy_frame(c) is ENEMY_FRAMES[("chaser", "chase", 0, 2)]


def test_bomber_targeting_doubles_flicker(pygame_ready, flat_level):
    from src.assets.asset_factory import ENEMY_FRAMES
    from src.player import Player
    fac, b = _fac_enemy("bomber")
    b.anim_t = 4
    assert fac.enemy_frame(b) is ENEMY_FRAMES[("bomber", "walk", 0)]
    b.targeting = True                           # (4 // 3) % 4 == 1
    assert fac.enemy_frame(b) is ENEMY_FRAMES[("bomber", "walk", 1)]
    # think() sets targeting from range
    _, b2 = _fac_enemy("bomber")
    b2.active = True
    b2.update(flat_level, Player(8 * 16, 12 * 16 - 26))
    assert b2.targeting, "bomber must target an in-range player"


def test_shell_slide_glow_and_wallcrawler_grip(pygame_ready):
    from src.assets.asset_factory import ENEMY_FRAMES
    fac, s = _fac_enemy("shellback")
    s.state = "shell"
    s.vx = config.SHELL_SLIDE_SPEED
    s.anim_t = 5                                 # (5 // 5) % 3 == 1
    assert fac.enemy_frame(s) is ENEMY_FRAMES[("shellback", "shell", 1, 1)]
    s.vx = 0.0
    assert fac.enemy_frame(s) is ENEMY_FRAMES[("shellback", "shell", 0, 0)]
    plain = pygame.image.tobytes(
        ENEMY_FRAMES[("shellback", "shell", 0, 0)], "RGBA")
    glow = pygame.image.tobytes(
        ENEMY_FRAMES[("shellback", "shell", 0, 1)], "RGBA")
    assert plain != glow, "slide glow must alter the shell frame"
    fac, w = _fac_enemy("wallcrawler")
    w.state = "ceiling"
    assert fac.enemy_frame(w) is ENEMY_FRAMES[("wallcrawler", "grip", 0)]
    grip = ENEMY_FRAMES[("wallcrawler", "grip", 0)]
    walk = ENEMY_FRAMES[("wallcrawler", "walk", 0)]
    assert grip.get_at((4, 1))[3] == 255         # claw-mark pixel
    assert walk.get_at((4, 1))[3] == 0


# --------------------------------------------- death sequences (SI-D)
def test_death_frames_five_phases(pygame_ready):
    """5 distinct frames per kind; canvas preserved; opacity 255 -> 51."""
    from src.assets import AssetFactory
    from src.assets.asset_factory import ENEMY_FRAMES
    AssetFactory()
    for kind in ("walker", "spitter"):
        frames = [ENEMY_FRAMES[(kind, "dying", p)] for p in range(5)]
        size = frames[0].get_size()
        assert {f.get_size() for f in frames} == {size}, \
            f"{kind}: canvas size must not change mid-death"
        blobs = [pygame.image.tobytes(f, "RGBA") for f in frames]
        assert len(set(blobs)) == 5, f"{kind}: death frames not distinct"
        peaks = [max(f.get_at((x, y))[3]
                     for x in range(size[0]) for y in range(size[1]))
                 for f in frames]
        assert peaks == [255, 204, 153, 102, 51], \
            f"{kind}: fade curve wrong: {peaks}"


def test_death_dispatch_cycles_five_frames(pygame_ready, flat_level):
    """death_timer drives phase 0..4 at 6 ticks per phase, then culls."""
    from src.assets import AssetFactory
    from src.assets.asset_factory import ENEMY_FRAMES
    from src.enemy_manager import spawn_enemy
    fac = AssetFactory()
    w = spawn_enemy("walker", 5, 12)
    w.start_dying()
    w.hit_flash = 0                              # isolate the death cycle
    player = Player(0, GROUND_Y - 26)
    got = []
    for _ in range(30):
        got.append(fac.enemy_frame(w))
        w.update(flat_level, player)
    expect = [ENEMY_FRAMES[("walker", "dying", e // 6)] for e in range(30)]
    assert got == expect
    assert len({id(img) for img in got}) == 5, "death sequence not cycling"
    assert w.death_timer == 0
    # flyer pop-corpse pops UP first, then falls WHILE the sequence plays
    f = spawn_enemy("flyer", 5, 12)
    f.start_dying(pop=True)
    f.hit_flash = 0
    y0 = f.y
    assert fac.enemy_frame(f) is ENEMY_FRAMES[("flyer", "dying", 0)]
    fell = False
    for _ in range(60):                           # pop arc: up, then down
        f.update(flat_level, player)
        if f.y > y0:
            fell = True
            break
    assert fell, "popped flyer corpse must fall back below the spawn"
    phase = min(4, (30 - f.death_timer) // 6)    # whatever tick it landed
    assert fac.enemy_frame(f) is ENEMY_FRAMES[("flyer", "dying", phase)]
    assert fac.enemy_frame(f) is not ENEMY_FRAMES[("flyer", "dying", 0)]

