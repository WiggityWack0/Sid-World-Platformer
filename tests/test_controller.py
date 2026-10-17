"""Controller (gamepad) support: adapter unit tests + game wiring.

Everything runs against a fake ControllerAdapter fed with synthetic pygame
joystick events - no physical pad or joystick driver is required.
"""

import pygame
import pytest

from src import config
from src import inputs


# ------------------------------------------------------------- event fakes
def _btn_down(button, joy=0):
    return pygame.event.Event(pygame.JOYBUTTONDOWN, joy=joy, button=button)


def _btn_up(button, joy=0):
    return pygame.event.Event(pygame.JOYBUTTONUP, joy=joy, button=button)


def _axis(axis, value, joy=0):
    return pygame.event.Event(pygame.JOYAXISMOTION, joy=joy, axis=axis,
                              value=value)


def _hat(x, y, joy=0):
    return pygame.event.Event(pygame.JOYHATMOTION, joy=joy, hat=0,
                              value=(x, y))


@pytest.fixture()
def pad():
    """A fresh, never-opened adapter: accepts synthetic joystick events."""
    return inputs.ControllerAdapter()


# ----------------------------------------------------------- button mapping
def test_non_joystick_events_pass_through(pad):
    key = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE, mod=0)
    motion = pygame.event.Event(pygame.MOUSEMOTION, pos=(0, 0), rel=(0, 0),
                                buttons=(0, 0, 0))
    assert pad.process_event(key) == []
    assert pad.process_event(motion) == []


def test_a_button_maps_to_jump_and_confirm(pad):
    events = pad.process_event(_btn_down(0))
    assert all(e.type == pygame.KEYDOWN for e in events)
    assert [e.key for e in events] == [pygame.K_SPACE, pygame.K_RETURN]
    # the pair keeps the single-action contract intact in both contexts
    assert inputs.key_to_action(pygame.K_SPACE) == "jump"
    assert inputs.key_to_action(pygame.K_RETURN) == "confirm"


def test_face_and_menu_button_mappings(pad):
    assert pad.process_event(_btn_down(1))[0].key == pygame.K_ESCAPE  # B
    assert pad.process_event(_btn_down(2))[0].key == pygame.K_c       # X
    assert pad.process_event(_btn_down(3))[0].key == pygame.K_f       # Y
    assert pad.process_event(_btn_down(6))[0].key == pygame.K_m       # Back
    assert pad.process_event(_btn_down(7))[0].key == pygame.K_p       # Start


# ---------------------------------------------------- edge detection + held
def test_press_is_edge_triggered_once(pad):
    assert pad.process_event(_btn_down(0)) != []
    assert pad.process_event(_btn_down(0)) == []     # no repeat while held
    assert pad.held("jump")
    assert pad.process_event(_btn_up(0)) == []       # release emits nothing
    assert not pad.held("jump")


def test_shoulder_buttons_drive_run_held(pad):
    assert pad.process_event(_btn_down(4)) == []     # no keydown mapping
    assert pad.held("run")
    pad.process_event(_btn_up(4))
    assert not pad.held("run")
    pad.process_event(_btn_down(5))                  # RB works too
    assert pad.held("run")


def test_just_pressed_is_consumed(pad):
    pad.process_event(_btn_down(0))
    assert pad.just_pressed("jump")
    assert not pad.just_pressed("jump")              # consumed on read
    assert pad.held("jump")                          # held state unaffected


# ------------------------------------------------------------------- d-pad
def test_dpad_edges_emit_arrow_keys(pad):
    assert [e.key for e in pad.process_event(_hat(1, 0))] == [pygame.K_RIGHT]
    assert pad.process_event(_hat(1, 0)) == []       # held: no repeat
    assert [e.key for e in pad.process_event(_hat(-1, 0))] == [pygame.K_LEFT]
    assert pad.process_event(_hat(0, -1))[0].key == pygame.K_DOWN
    assert pad.process_event(_hat(0, 1))[0].key == pygame.K_UP
    assert pad.process_event(_hat(0, 0)) == []       # release: silent


def test_dpad_held(pad):
    pad.process_event(_hat(1, 0))
    assert pad.held("right") and not pad.held("left")
    pad.process_event(_hat(0, -1))
    assert pad.held("down") and not pad.held("right")


# ------------------------------------------------------------ analog stick
def test_stick_deadzone_ignores_small_tilt(pad):
    pad.process_event(_axis(0, 0.2))
    assert not pad.held("right") and not pad.held("left")
    pad.process_event(_axis(0, -0.9))
    assert pad.held("left") and not pad.held("right")


def test_stick_down_reads_as_down(pad):
    pad.process_event(_axis(1, 0.9))
    assert pad.held("down") and not pad.held("up")
    pad.process_event(_axis(1, -0.9))
    assert pad.held("up") and not pad.held("down")


def test_stick_rescales_past_deadzone(pad):
    pad.process_event(_axis(0, -1.0))
    assert pad._stick(0) == -1.0
    dz = config.STICK_DEADZONE
    pad.process_event(_axis(0, dz))                  # exactly at the edge
    assert pad._stick(0) == 0.0
    pad.process_event(_axis(0, dz + (1.0 - dz) * 0.5))
    assert abs(pad._stick(0) - 0.5) < 1e-9


def test_just_pressed_directions(pad):
    pad.process_event(_axis(1, 0.9))
    assert pad.just_pressed("down")
    assert not pad.just_pressed("down")


# -------------------------------------------------------- device lifecycle
def test_foreign_pad_events_are_ignored(pad):
    pad._joy_id = 3                              # pretend pad 3 is attached
    assert pad.process_event(_btn_down(0, joy=1)) == []
    assert not pad.held("jump")
    assert pad.process_event(_btn_down(0, joy=3)) != []
    assert pad.held("jump")


class _FakeJoy:
    """Minimal stand-in for pygame.joystick.Joystick."""

    def __init__(self, instance_id):
        self._iid = instance_id

    def init(self):
        pass

    def quit(self):
        pass

    def get_instance_id(self):
        return self._iid


def test_hotplug_attaches_and_clears(pad, monkeypatch):
    monkeypatch.setattr(pygame.joystick, "get_init", lambda: True)
    monkeypatch.setattr(pygame.joystick, "get_count", lambda: 1)
    monkeypatch.setattr(pygame.joystick, "Joystick", lambda i: _FakeJoy(42))
    added = pygame.event.Event(pygame.JOYDEVICEADDED, device=0, guid=0)
    assert pad.process_event(added) == []
    assert pad.connected and pad._joy_id == 42
    assert pad.process_event(_btn_down(0, joy=42)) != []   # now filtered
    removed = pygame.event.Event(pygame.JOYDEVICEREMOVED, joy=42)
    assert pad.process_event(removed) == []
    assert not pad.connected and not pad.held("jump")


def test_open_without_pad_is_noop(pad, monkeypatch):
    monkeypatch.setattr(pygame.joystick, "get_init", lambda: True)
    monkeypatch.setattr(pygame.joystick, "get_count", lambda: 0)
    pad.open()
    assert not pad.connected
    assert not pad.held("jump")


# --------------------------------------------------------- game integration
def _install_fake_pad(monkeypatch):
    """Swap the module singleton for a pad that never touches hardware."""
    pad = inputs.ControllerAdapter()
    monkeypatch.setattr(pad, "open", lambda: None)
    monkeypatch.setattr(inputs, "controller", pad)
    return pad


def test_action_held_falls_back_to_pad(pygame_ready, monkeypatch):
    pad = _install_fake_pad(monkeypatch)
    assert not inputs.action_held("jump")
    pad.process_event(_btn_down(0))
    assert inputs.action_held("jump")
    pad.process_event(_axis(0, -0.9))
    assert inputs.action_held("left") and not inputs.action_held("right")
    pad.process_event(_btn_down(4))
    assert inputs.action_held("run")


def test_a_button_starts_new_game_from_title(pygame_ready, monkeypatch):
    from src.game import Game
    _install_fake_pad(monkeypatch)
    game = Game(seed=42)
    assert game.state_name == "title"
    game._pump(_btn_down(0))                      # A: Space (nop) + Return
    game._pump(_btn_up(0))
    assert game.state_name == "playing"


def test_start_pauses_and_b_resumes(pygame_ready, monkeypatch):
    from src.game import Game
    _install_fake_pad(monkeypatch)
    game = Game(seed=42)
    game._pump(_btn_down(0))                      # A: enter a run
    game._pump(_btn_up(0))
    game._pump(_btn_down(7))                      # Start -> P -> pause
    game._pump(_btn_up(7))
    assert game.state_name == "paused"
    game._pump(_btn_down(1))                      # B -> Escape -> resume
    game._pump(_btn_up(1))
    assert game.state_name == "playing"


def test_back_button_mutes_everywhere(pygame_ready, monkeypatch):
    from src.game import Game
    _install_fake_pad(monkeypatch)
    game = Game(seed=42)
    was = game.audio.muted
    game._pump(_btn_down(6))                      # Back -> M -> mute toggle
    assert game.audio.muted == (not was)
    assert game.progress["settings"]["muted"] == game.audio.muted
    game._pump(_btn_up(6))
