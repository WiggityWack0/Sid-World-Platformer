"""Keyboard mapping between pygame keys and high-level game actions.

Also hosts the single-controller adapter (pygame-ce joystick subsystem):
pad presses become synthetic KEYDOWN events using the same key vocabulary,
so every state works with a gamepad unchanged. First pass: one pad,
stick deadzones, edge detection; vibration and remapping are deferred to
a later polish slice.
"""

import math

import pygame

from src.config import (CONTROLS, CONTROLLER_BUTTONS, CONTROLLER_HELD,
                        STICK_DEADZONE)


def _key_code(name):
    if len(name) == 1:
        return getattr(pygame, "K_" + name.lower())
    if name == "Shift":
        return None                      # handled specially
    return getattr(pygame, "K_" + name.upper())


KEYMAP = {}          # action -> list of key codes
for _action, _names in CONTROLS.items():
    _codes = []
    for _n in _names:
        if _n == "Shift":
            _codes.extend([pygame.K_LSHIFT, pygame.K_RSHIFT])
        else:
            _codes.append(_key_code(_n))
    KEYMAP[_action] = _codes

_REVERSE = {}
for _action, _codes in KEYMAP.items():
    for _c in _codes:
        _REVERSE.setdefault(_c, _action)


def key_to_action(key):
    return _REVERSE.get(key)


# ------------------------------------------------------------- controller
# action -> buttons that count as pressed/held for that action. Derived
# from CONTROLLER_BUTTONS (shared vocabulary with the key map) plus the
# held-only bindings that have no keydown equivalent (run = shoulders).
_CTRL_BUTTONS = {}
for _btn, _names in CONTROLLER_BUTTONS.items():
    for _n in _names:
        _action = _REVERSE.get(_key_code(_n))
        if _action is not None:
            _CTRL_BUTTONS.setdefault(_action, set()).add(_btn)
for _action, _btns in CONTROLLER_HELD.items():
    _CTRL_BUTTONS.setdefault(_action, set()).update(_btns)

_DIRECTIONS = ("left", "right", "up", "down")
_ARROW_KEYS = {"left": pygame.K_LEFT, "right": pygame.K_RIGHT,
               "up": pygame.K_UP, "down": pygame.K_DOWN}


class ControllerAdapter:
    """State + translation layer for the first connected pad.

    Feed every pygame event through process_event(); it returns synthetic
    KEYDOWN events (edge-triggered: one per button press / d-pad step) that
    the existing state machine consumes directly. held() adds the analog
    side (d-pad + left stick with a deadzone) for per-tick polling.
    """

    def __init__(self):
        self._joy = None
        self._joy_id = None
        self._reset_state()

    # ---------------------------------------------------------- lifecycle
    def open(self):
        """Attach the first connected pad; safe no-op when none exists."""
        self.close()
        pygame.joystick.init()
        if pygame.joystick.get_count() > 0:
            self._attach(pygame.joystick.Joystick(0))

    def close(self):
        joy, self._joy = self._joy, None
        self._joy_id = None
        self._reset_state()
        if joy is not None:
            try:
                joy.quit()
            except pygame.error:
                pass                              # already detached

    def _attach(self, joy):
        # pygame-ce >= 2.4 auto-initializes on construction; init() is
        # deprecated and will be removed.
        self._joy = joy
        self._joy_id = (joy.get_instance_id()
                        if hasattr(joy, "get_instance_id") else joy.get_id())

    @property
    def connected(self):
        return self._joy is not None

    def _reset_state(self):
        self._down = set()          # held button indices
        self._edges = set()         # buttons pressed since just_pressed()
        self._dir_edges = set()     # direction actions newly pressed
        self._axes = {}             # axis index -> analog value
        self._hat = (0, 0)          # d-pad hat: +x right, +y up (SDL)

    # --------------------------------------------------------- event pump
    def process_event(self, event):
        """Update pad state; return synthetic KEYDOWN events to dispatch."""
        etype = event.type
        if etype == pygame.JOYDEVICEADDED:
            if self._joy is None and pygame.joystick.get_init():
                idx = getattr(event, "device", 0)
                if 0 <= idx < pygame.joystick.get_count():
                    self._attach(pygame.joystick.Joystick(idx))
            return []
        if etype == pygame.JOYDEVICEREMOVED:
            if self._joy is not None \
                    and getattr(event, "joy", None) == self._joy_id:
                self.close()
            return []
        if not self._ours(event):
            return []
        if etype == pygame.JOYBUTTONDOWN:
            return self._on_button(event, True)
        if etype == pygame.JOYBUTTONUP:
            return self._on_button(event, False)
        if etype == pygame.JOYAXISMOTION:
            return self._on_axis(event)
        if etype == pygame.JOYHATMOTION:
            return self._on_hat(event)
        return []

    def _ours(self, event):
        """True for our pad's events; an unopened adapter (tests) accepts
        every joystick event."""
        jid = getattr(event, "joy", None)
        return jid is None or self._joy_id is None or jid == self._joy_id

    def _on_button(self, event, down):
        btn = event.button
        if not down:
            self._down.discard(btn)
            return []                            # states are KEYDOWN-only
        if btn in self._down:
            return []                            # edge: never repeat a hold
        self._down.add(btn)
        self._edges.add(btn)
        return [self._synth(_key_code(n))
                for n in CONTROLLER_BUTTONS.get(btn, ())]

    def _on_axis(self, event):
        before = self._active_dirs()
        self._axes[event.axis] = event.value
        self._dir_edges |= self._active_dirs() - before
        return []                                # stick = held input only

    def _on_hat(self, event):
        if getattr(event, "hat", 0) != 0:
            return []
        before = self._active_dirs()
        self._hat = event.value
        new = self._active_dirs() - before       # edges: newly active only
        self._dir_edges |= new
        return [self._synth(_ARROW_KEYS[d]) for d in _DIRECTIONS if d in new]

    @staticmethod
    def _synth(key):
        return pygame.event.Event(pygame.KEYDOWN, key=key, mod=0)

    # ------------------------------------------------------------- queries
    def _stick(self, axis):
        """Deadzone + rescale: 0 inside, +/-1 at full tilt."""
        v = self._axes.get(axis, 0.0)
        if abs(v) < STICK_DEADZONE:
            return 0.0
        mag = (abs(v) - STICK_DEADZONE) / (1.0 - STICK_DEADZONE)
        return math.copysign(mag, v)

    def _active_dirs(self):
        hx, hy = self._hat
        x, y = self._stick(0), self._stick(1)
        return {d for d, cond in
                (("left", hx < 0 or x < 0), ("right", hx > 0 or x > 0),
                 ("up", hy > 0 or y < 0), ("down", hy < 0 or y > 0))
                if cond}

    def held(self, action):
        """True while the pad holds this action (buttons, d-pad, stick)."""
        if self._down & _CTRL_BUTTONS.get(action, set()):
            return True
        return action in self._active_dirs()

    def just_pressed(self, action):
        """Edge query: True once per press (each edge is consumed)."""
        buttons = _CTRL_BUTTONS.get(action, set())
        if self._edges & buttons:
            self._edges -= buttons
            return True
        if action in self._dir_edges:
            self._dir_edges.discard(action)
            return True
        return False


controller = ControllerAdapter()    # singleton; monkeypatchable in tests


def action_held(action):
    pressed = pygame.key.get_pressed()
    if any(pressed[c] for c in KEYMAP[action]):
        return True
    return controller.held(action)
