"""Rising, fading text floaters (`+100`, `1-UP`). Visual-only.

Pooled like particles: zero-alloc steady state, oldest recycled at the cap.
HUD wiring (which events spawn floaters) lands in Phase 1b; this module plus
the Effects facade helper are in place now so callers can already spawn them.
"""

import pygame

from src import config


class Floater:
    __slots__ = ("x", "y", "text", "life", "max_life", "color")

    def active(self):
        return self.life > 0


class Floaters:
    def __init__(self):
        self._pool = [Floater() for _ in range(config.FLOATER_CAP)]
        self._count = 0
        self._font = None

    def __len__(self):
        return self._count

    @property
    def font(self):
        # Lazy: font creation deferred until first draw (tests of the
        # lifecycle don't need fonts; mirrors Hud's SysFont choice).
        if self._font is None:
            self._font = pygame.font.SysFont("consolas", 11, bold=True)
        return self._font

    def spawn(self, x, y, text, color=None):
        if self._count < config.FLOATER_CAP:
            f = self._pool[self._count]
            self._count += 1
        else:
            f = min(self._pool, key=lambda q: q.life)   # recycle oldest
        f.x = float(x)
        f.y = float(y)
        f.text = text
        f.life = config.FLOATER_LIFE
        f.max_life = config.FLOATER_LIFE
        f.color = color if color is not None else config.HUD_TEXT
        return f

    def update(self):
        i = 0
        while i < self._count:
            f = self._pool[i]
            f.y -= config.FLOATER_RISE
            f.life -= 1
            if f.life <= 0:
                self._count -= 1
                self._pool[i] = self._pool[self._count]
                self._pool[self._count] = f
            else:
                i += 1

    def draw(self, surf, cam):
        if self._count == 0:
            return
        ix, iy = cam.ix, cam.iy
        for i in range(self._count):
            f = self._pool[i]
            img = self.font.render(f.text, True, f.color)
            img.set_alpha(int(255 * f.life / f.max_life))
            surf.blit(img, (int(f.x) - ix - img.get_width() // 2,
                            int(f.y) - iy))
