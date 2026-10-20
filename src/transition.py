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
        # style (Phase 5 T4): draw-shape only — step()/alpha() semantics
        # are untouched so tests/test_transitions.py contracts hold.
        self.style = "fade"      # fade | iris | wipe | zone_fade
        self.tint = None         # zone_fade: darkened zone tint
        self._overlay = None     # lazily built iris surface (one per inst)

    @property
    def active(self):
        return self.phase is not None

    def start(self, pending, style="fade", tint=None):
        """Begin a fade-out; `pending` = (state_name, kwargs).
        `style` picks the draw shape (pure visual; swap timing identical)."""
        self.phase = "out"
        self.t = 0
        self.pending = pending
        self.style = style
        self.tint = tint

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
        """Fade math — UNCHANGED for every style (pinned by tests)."""
        if self.phase is None:
            return 0
        f = self.t / self.ticks
        return int(255 * f) if self.phase == "out" else int(255 * (1 - f))

    def progress(self):
        """0..1 through the current phase (style-specific shapes read
        this instead of alpha())."""
        if self.phase is None:
            return 0.0
        return self.t / self.ticks

    def draw(self, surf):
        a = self.alpha()
        if a <= 0:
            return
        if self.style == "fade":
            dim = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
            dim.fill((0, 0, 0, min(255, a)))
            surf.blit(dim, (0, 0))
        elif self.style == "zone_fade":
            # fade through a darkened veil of the destination zone tint
            tint = self.tint or (0, 0, 0)
            col = tuple(int(c * 0.5 * a / 255) for c in tint)
            dim = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
            dim.fill((*col, min(255, a)))
            surf.blit(dim, (0, 0))
        elif self.style == "iris":
            # circular hole: full black overlay with the pupil erased
            # (draw writes alpha directly on SRCALPHA — verified)
            if self._overlay is None:
                self._overlay = pygame.Surface((VIEW_W, VIEW_H),
                                               pygame.SRCALPHA)
            ov = self._overlay
            ov.fill((0, 0, 0, 255))
            f = self.progress()
            frac = f if self.phase == "in" else 1.0 - f
            r = int(240 * frac)               # 240 covers the corners
            if r > 0:
                pygame.draw.circle(ov, (0, 0, 0, 0),
                                   (VIEW_W // 2, VIEW_H // 2), r)
            surf.blit(ov, (0, 0))
        elif self.style == "wipe":
            # two horizontal bars closing from top and bottom
            f = self.progress()
            h = int((f if self.phase == "out" else 1.0 - f)
                    * (VIEW_H // 2))
            if h > 0:
                pygame.draw.rect(surf, (0, 0, 0),
                                 pygame.Rect(0, 0, VIEW_W, h))
                pygame.draw.rect(surf, (0, 0, 0),
                                 pygame.Rect(0, VIEW_H - h, VIEW_W, h))
        else:                                     # unknown -> plain fade
            dim = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
            dim.fill((0, 0, 0, min(255, a)))
            surf.blit(dim, (0, 0))