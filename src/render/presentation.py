"""Presentation layer (Phase 1, visual overhaul).

Post-processing applied in `Game.run_loop` between `state.draw(surface)` and
the window upscale. Visual-only: never touches physics, game state, or the
deterministic update loop.

Frame-path rules (recorded in ProjectPlan.md): everything heavy is
precomputed at init; `apply()` performs at most 4 full-screen accelerated
blits (BLEND_RGB_MULT / set_alpha) — no per-pixel Python loops per frame.
"""

import math

import pygame

from src.config import (DESAT_TICKS, PULSE_TICKS, SCANLINE_ALPHA,
                        VIGNETTE_ALPHA, VIEW_H, VIEW_W, VIGNETTE_ON,
                        COLOR_GRADE_ON, SCANLINES_ON, WINDOW_SCALE,
                        GRADE_TINTS)


def _make_vignette(w, h, strength):
    """Radial edge-darkening mask; built small, smoothscaled once."""
    sw, sh = w // 4, h // 4
    small = pygame.Surface((sw, sh), pygame.SRCALPHA)
    cx, cy = sw / 2.0, sh / 2.0
    max_d = math.hypot(cx, cy)
    for y in range(sh):
        for x in range(sw):
            d = math.hypot(x - cx, y - cy) / max_d
            a = int(strength * max(0.0, d - 0.5) / 0.5)
            if a > 0:
                small.set_at((x, y), (0, 0, 0, min(255, a)))
    return pygame.transform.smoothscale(small, (w, h))


def _make_scanlines(w, h, alpha):
    """1px alternating dark rows (CRT look); optional, off by default."""
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(0, h, 2):
        s.fill((0, 0, 0, alpha), pygame.Rect(0, y, w, 1))
    return s


def _make_grade(tint):
    """Opaque multiply-mask for BLEND_RGB_MULT (255 = unchanged channel)."""
    s = pygame.Surface((VIEW_W, VIEW_H))
    s.fill(tint)
    return s


class Presentation:
    def __init__(self):
        self.vignette_on = VIGNETTE_ON
        self.color_grade_on = COLOR_GRADE_ON
        self.scanlines_on = SCANLINES_ON
        self.window_scale = WINDOW_SCALE
        self._pulse = 0                      # damage-pulse ticks remaining
        self._desat = 0                      # boss phase-flash ticks (T5)
        self._desat_total = DESAT_TICKS
        # precompute once (init cost ~ms; never per frame)
        self._vignette = _make_vignette(VIEW_W, VIEW_H, VIGNETTE_ALPHA)
        self._scanlines = _make_scanlines(VIEW_W, VIEW_H, SCANLINE_ALPHA)
        self._pulse_surf = pygame.Surface((VIEW_W, VIEW_H))
        self._pulse_surf.fill((170, 28, 28))
        self._veil_surf = pygame.Surface((VIEW_W, VIEW_H))
        self._veil_surf.fill((235, 238, 250))  # desat flash veil (T5)
        self._grades = {z: _make_grade(t) for z, t in enumerate(GRADE_TINTS)
                        if t is not None}    # zone 0 = identity (no entry)

    # ---------------------------------------------------------- settings
    def apply_settings(self, settings):
        """Live-apply persisted settings (tolerant, consumes 4c's schema)."""
        for key, attr in (("vignette", "vignette_on"),
                          ("color_grade", "color_grade_on"),
                          ("scanlines", "scanlines_on")):
            v = settings.get(key)
            if isinstance(v, bool):
                setattr(self, attr, v)
        v = settings.get("window_scale")
        if isinstance(v, int) and not isinstance(v, bool) and v in (2, 3, 4):
            self.window_scale = v

    # ------------------------------------------------------------- pulse
    def pulse(self):
        """Start a damage red-vignette pulse (called from PlayingState)."""
        self._pulse = PULSE_TICKS

    def desat(self, ticks=DESAT_TICKS):
        """Brief bright veil on a boss phase shift (Phase 5 T5): one blit,
        decays over `ticks` applications of apply()."""
        self._desat = ticks
        self._desat_total = max(1, ticks)

    # -------------------------------------------------------------- apply
    def apply(self, surf, zone):
        """Post-process `surf` in place for `zone` (0-3)."""
        if self.color_grade_on:
            grade = self._grades.get(zone)
            if grade is not None:
                surf.blit(grade, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        if self.vignette_on:
            surf.blit(self._vignette, (0, 0))
        if self._desat > 0:
            self._veil_surf.set_alpha(
                int(72 * self._desat / self._desat_total))
            surf.blit(self._veil_surf, (0, 0))
            self._desat -= 1
        if self._pulse > 0:
            self._pulse -= 1
            self._pulse_surf.set_alpha(int(80 * self._pulse / PULSE_TICKS))
            surf.blit(self._pulse_surf, (0, 0))
        if self.scanlines_on:
            surf.blit(self._scanlines, (0, 0))
