"""Keyboard mapping between pygame keys and high-level game actions."""

import pygame

from src.config import CONTROLS


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


def action_held(action):
    pressed = pygame.key.get_pressed()
    return any(pressed[c] for c in KEYMAP[action])
