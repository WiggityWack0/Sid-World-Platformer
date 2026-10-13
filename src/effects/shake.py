"""Trauma-based screen shake (visual only).

Callers add trauma on impact events; the view offset follows trauma squared
so small adds barely register and big hits punch. Offset is a deterministic
function of (trauma, tick) — no random state involved.
"""

import math

from src import config


class Shake:
    def __init__(self):
        self.trauma = 0.0
        self.t = 0

    def add(self, amount):
        self.trauma = min(1.0, self.trauma + max(0.0, amount))

    def update(self):
        self.t += 1
        self.trauma = max(0.0, self.trauma - config.SHAKE_DECAY)

    def offset(self):
        """Current (dx, dy) view offset in px; zero when trauma has decayed."""
        if self.trauma <= 0.0:
            return (0, 0)
        mag = self.trauma * self.trauma * config.SHAKE_MAGNITUDE
        dx = math.sin(self.t * 2.399963) * mag
        dy = math.cos(self.t * 3.141593) * mag * 0.7
        lim = config.SHAKE_MAX_OFFSET
        return (int(round(max(-lim, min(lim, dx)))),
                int(round(max(-lim, min(lim, dy)))))
