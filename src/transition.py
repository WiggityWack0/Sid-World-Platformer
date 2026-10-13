"""Deterministic screen fade for state transitions (Phase 6b).

Visual-only, pure tick math — no RNG, no wall-clock. Owned by Game:
`Game(..., transitions=True)` defers `switch_state` through a fade-out,
swaps the state exactly once at black, then fades back in. Tests (and
any direct Game construction) default to transitions=False — RECORDED:
every existing synchronous flow test keeps its exact timing; the
shipped game (main.py) opts in explicitly.
"""

import pygame

from src.config import FADE_TICKS, VIEW_H, VIEW_W


class Transition:
    def __init__(self, ticks=FADE_TICKS):
        self.ticks = max(1, ticks)
        self.phase = None        # None | "out" | "in"
        self.t = 0
        self.pending = None      # (name, kwargs) swapped at black

    @property
    def active(self):
        return self.phase is not None

    def start(self, pending):
        """Begin a fade-out; `pending` = (state_name, kwargs)."""
        self.phase = "out"
        self.t = 0
        self.pending = pending

    def step(self):
        """Advance one tick. Returns 'swap' exactly once, at black."""
        self.t += 1
        if self.phase == "out" and self.t >= self.ticks:
            self.phase = "in"
            self.t = 0
            return "swap"
        if self.phase == "in" and self.t >= self.ticks:
            self.phase = None
            self.pending = None
        return None

    def alpha(self):
        if self.phase is None:
            return 0
        f = self.t / self.ticks
        return int(255 * f) if self.phase == "out" else int(255 * (1 - f))

    def draw(self, surf):
        a = self.alpha()
        if a > 0:
            dim = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
            dim.fill((0, 0, 0, min(255, a)))
            surf.blit(dim, (0, 0))