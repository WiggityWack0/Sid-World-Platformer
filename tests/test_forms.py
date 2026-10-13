"""Forms + C attack (Phase 2c): cycling, projectiles, freeze, lightning (D2)."""

import pygame  # noqa: F401  (conftest sets dummy drivers first)

from src import config
from src.player import Input, Player


def _playing(seed=7):
    from src.game import Game
    game = Game(seed=seed, max_frames=None)
    game.new_run(seed=seed)
    game.switch_state("playing")
    return game, game.state


def _press(state, key):
    state.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0))


class FakeCam:
    x = 0.0
    y = 0.0
    ix = 0
    iy = 0

    def visible(self, rect, margin=32):
        return True


# ---------------------------------------------------------------- unit
def test_cycle_form_order_and_wrap():
    p = Player(0, 0)
    assert p.form is None
    assert p.cycle_form() == "fire"
    assert p.cycle_form() == "ice"
    assert p.cycle_form() == "lightning"
    assert p.cycle_form() is None, "cycle must wrap back through Sid"


def test_cycle_respects_unlocked():
    p = Player(0, 0)
    p.forms_unlocked = ["ice"]
    assert p.cycle_form() == "ice"
    assert p.cycle_form() is None


def test_forms_never_change_stats():
    """D1: forms are strictly offensive."""
    p = Player(0, 0)
    for form in config.FORMS:
        p.form = form
        assert p.max_run == config.MAX_RUN
        assert p.max_walk == config.MAX_WALK
        assert p.jump_velocity == config.JUMP_VELOCITY
        assert p.gravity == config.GRAVITY
    p.form = None
    assert p.max_run == config.MAX_RUN


def test_attack_cooldown_ticks_down(flat_level):
    p = Player(32, 100)
    p.attack_cooldown = 3
    for _ in range(3):
        p.update(Input(), flat_level)
    assert p.attack_cooldown == 0


def test_attack_and_form_keys_do_not_collide():
    from src import inputs
    assert inputs.key_to_action(pygame.K_c) == "attack"
    assert inputs.key_to_action(pygame.K_f) == "form"
    assert inputs.key_to_action(pygame.K_x) == "run"
    assert inputs.key_to_action(pygame.K_z) == "jump"
    assert inputs.key_to_action(pygame.K_RETURN) == "confirm"


# ------------------------------------------------------------- wiring
def test_f_key_cycles_form_in_playing(pygame_ready):
    game, state = _playing()
    _press(state, pygame.K_f)
    assert state.player.form == "fire"
    _press(state, pygame.K_f)
    assert state.player.form == "ice"


def test_c_spawns_fireball_and_cooldown_blocks(pygame_ready):
    game, state = _playing()
    state.player.form = "fire"
    _press(state, pygame.K_c)
    assert len(state.attacks) == 1
    assert state.player.attack_cooldown == config.ATTACK_COOLDOWN
    _press(state, pygame.K_c)
    assert len(state.attacks) == 1, "cooldown must block a second attack"
    state.player.attack_cooldown = 0
    _press(state, pygame.K_c)
    assert len(state.attacks) == 2


def test_c_as_sid_does_nothing(pygame_ready):
    game, state = _playing()
    assert state.player.form is None
    _press(state, pygame.K_c)
    assert state.attacks == []
    assert state.player.attack_cooldown == 0


# ---------------------------------------------------------- combat (2c)
def test_fireball_kills_walker_and_despawns(pygame_ready):
    from src.attacks import AttackProjectile
    from src.enemies import Walker
    game, state = _playing()
    player = state.player
    walker = Walker(int(player.x) + 40, int(player.y))
    walker.active = True
    state.enemies.enemies.insert(0, walker)
    state.attacks.append(
        AttackProjectile("fire", player.x + 24, player.cy - 4, 1))
    for _ in range(40):
        state._update_attacks()
        if walker.state == "dying":
            break
    assert walker.state == "dying", "fireball never hit the walker"
    assert state.attacks == [], "spent fireball must despawn"


def test_ice_shard_freezes_enemy(pygame_ready):
    from src.attacks import AttackProjectile
    from src.enemies import Walker
    game, state = _playing()
    player = state.player
    walker = Walker(int(player.x) + 40, int(player.y))
    walker.active = True
    state.enemies.enemies.insert(0, walker)
    state.attacks.append(
        AttackProjectile("ice", player.x + 24, player.cy - 4, 1))
    for _ in range(40):
        state._update_attacks()
        if walker.frozen > 0:
            break
    assert walker.frozen == config.ICE_FREEZE_TICKS
    assert walker.alive, "ice must freeze, not kill"
    assert state.attacks == [], "spent shard must despawn"


def test_frozen_enemy_skipped_by_manager(flat_level, pygame_ready):
    from src.enemy_manager import EnemyManager
    mgr = EnemyManager([("walker", 10, 12)])
    walker = mgr.enemies[0]
    walker.frozen = 20
    player = Player(32, 12 * 16 - 26)
    cam = FakeCam()
    x0 = walker.x
    for _ in range(20):
        mgr.update(flat_level, player, cam)
    assert walker.x == x0, "frozen walker must not move"
    assert walker.frozen == 0
    for _ in range(120):                       # thawed: patrol resumes
        mgr.update(flat_level, player, cam)
    assert walker.x != x0, "thawed walker must move again"


def test_lightning_kills_up_to_3_in_range(pygame_ready):
    from src.enemies import Walker
    game, state = _playing()
    player = state.player
    player.form = "lightning"
    near = []
    for dx in (30, 50, 70):
        w = Walker(int(player.x) + dx, int(player.y))
        w.active = True
        state.enemies.enemies.append(w)
        near.append(w)
    far = Walker(int(player.x) + 300, int(player.y))
    far.active = True
    state.enemies.enemies.append(far)
    score_before = game.run.score
    state._try_attack()
    assert all(w.state == "dying" for w in near)
    assert far.state != "dying", "out-of-range enemy must be ignored"
    assert game.run.score >= score_before + 3 * config.FORM_KILL_SCORE
    assert player.attack_cooldown == config.ATTACK_COOLDOWN


def test_stomp_semantics_unchanged_with_form(pygame_ready):
    """R3: fire form active, stomp still bounces normally."""
    from src.enemies import Walker
    game, state = _playing()
    player = state.player
    player.form = "fire"
    walker = Walker(int(player.x), int(player.y) + 40)
    walker.active = True
    state.enemies.enemies.insert(0, walker)
    player.y = float(walker.y - 20)
    player.vy = 4.0
    state._combat(Input())
    assert walker.state == "dying"
    assert player.vy < -1, "stomp bounce must still apply with a form active"


def test_respawn_clears_form_and_attacks(pygame_ready):
    game, state = _playing()
    state.player.form = "ice"
    state.attacks.append(object())             # placeholder, cleared not ticked
    state._respawn()
    assert state.player.form is None
    assert state.attacks == []

