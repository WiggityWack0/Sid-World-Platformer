"""Pooled, hard-capped particle system. Visual-only: never touches physics.

Zero-alloc steady state: all Particle objects are allocated once at startup;
spawning reuses pooled slots and recycles the oldest particle when full.
"""

import math
import random

import pygame

from src import config

# Dedicated RNG: effects must never consume the global random state that
# gameplay/generation depend on (determinism contract).
_RNG = random.Random(0x5EED)


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "grav", "life", "max_life",
                 "size", "color")

    def active(self):
        return self.life > 0


class ParticleSystem:
    def __init__(self):
        self._pool = [Particle() for _ in range(config.PARTICLE_CAP)]
        self._count = 0

    def __len__(self):
        return self._count

    # ------------------------------------------------------------- spawning
    def _spawn(self, x, y, vx, vy, life, color, size, grav):
        if self._count < config.PARTICLE_CAP:
            p = self._pool[self._count]
            self._count += 1
        else:
            p = min(self._pool, key=lambda q: q.life)   # recycle oldest
        p.x = float(x)
        p.y = float(y)
        p.vx = vx
        p.vy = vy
        p.life = life
        p.max_life = life
        p.size = size
        p.color = color
        p.grav = grav
        return p

    def dust(self, x, y):
        """Soft puff at feet (running, landing, warping)."""
        for _ in range(4):
            self._spawn(x + _RNG.uniform(-3, 3), y,
                        _RNG.uniform(-0.6, 0.6), _RNG.uniform(-0.7, -0.2),
                        _RNG.randint(14, 24), config.FX_DUST, 2, 0.02)

    def spark(self, x, y, color=None):
        """Quick radial burst (checkpoints, switches, hits)."""
        col = color if color is not None else config.FX_SPARK
        for _ in range(6):
            ang = _RNG.uniform(0.0, 6.28318)
            spd = _RNG.uniform(0.8, 2.0)
            self._spawn(x, y,
                        spd * math.cos(ang), spd * math.sin(ang),
                        _RNG.randint(10, 18), col, 2, 0.05)

    def coin_burst(self, x, y):
        """Gold sparkle when a coin is collected or bumped out."""
        for _ in range(8):
            self._spawn(x + _RNG.uniform(-4, 4), y + _RNG.uniform(-4, 4),
                        _RNG.uniform(-0.8, 0.8), _RNG.uniform(-2.6, -1.4),
                        _RNG.randint(18, 30), config.FX_COIN, 2, 0.12)

    def debris(self, x, y, color=None):
        """Brick chunks flying from a broken block."""
        col = color if color is not None else config.FX_DEBRIS
        for _ in range(8):
            self._spawn(x + _RNG.uniform(-6, 6), y + _RNG.uniform(-6, 6),
                        _RNG.uniform(-2.2, 2.2), _RNG.uniform(-4.0, -2.0),
                        _RNG.randint(28, 44), col, 3, 0.35)

    def explosion(self, x, y):
        """Death/impact burst: hot radial spray."""
        colors = (config.FX_DEATH_1, config.FX_DEATH_2)
        for i in range(14):
            ang = _RNG.uniform(0.0, 6.28318)
            spd = _RNG.uniform(1.0, 3.2)
            self._spawn(x, y,
                        spd * math.cos(ang), spd * math.sin(ang),
                        _RNG.randint(16, 30), colors[i % 2], 3, 0.08)

    def stomp_puff(self, x, y):
        """White puff when the player stomps an enemy."""
        for _ in range(6):
            self._spawn(x + _RNG.uniform(-5, 5), y,
                        _RNG.uniform(-1.2, 1.2), _RNG.uniform(-1.4, -0.4),
                        _RNG.randint(12, 20), config.FX_STOMP, 2, 0.03)

    def ambient(self, kind, cam_x):
        """One light per-theme ambient particle (4b). Visual-only.

        Kind comes from the zone config (leaves/embers/snow/rain); the
        particle drifts across the view using the shared cap-safe pool.
        """
        color = config.AMBIENT_COLORS.get(kind, (255, 255, 255))
        x = cam_x + _RNG.uniform(0, config.VIEW_W)
        if kind == "rain":
            self._spawn(x, -4.0, 0.5, 3.4, 90, color, 1, 0.0)
        elif kind == "snow":
            self._spawn(x, -4.0, _RNG.uniform(-0.3, 0.3),
                        _RNG.uniform(0.4, 0.9), 420, color, 2, 0.0)
        elif kind == "embers":
            self._spawn(x, config.VIEW_H + 4.0,
                        _RNG.uniform(-0.3, 0.3), _RNG.uniform(-1.0, -0.5),
                        420, color, 2, 0.0)
        else:                                       # leaves (default)
            self._spawn(x, -4.0, _RNG.uniform(-0.5, 0.5),
                        _RNG.uniform(0.5, 0.9), 420, color, 2, 0.02)

    # ------------------------------------------------------------- sim/draw
    def update(self):
        i = 0
        while i < self._count:
            p = self._pool[i]
            p.vy += p.grav
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life <= 0:
                # swap-recycle: move last active into this slot (no alloc)
                self._count -= 1
                self._pool[i] = self._pool[self._count]
                self._pool[self._count] = p
            else:
                i += 1

    def draw(self, surf, cam):
        ix, iy = cam.ix, cam.iy
        for i in range(self._count):
            p = self._pool[i]
            sz = max(1, p.size * p.life // p.max_life)
            surf.fill(p.color, (int(p.x) - ix, int(p.y) - iy, sz, sz))
