"""Enemy AI: per-type behaviors, combat rules, manager wiring."""

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

