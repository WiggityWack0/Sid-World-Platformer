"""Shared menu component (Phase 4, T4): 9-slice panel + row list with an
animated cursor and staggered fade-in.

Pure draw helper — selection state, input handling, and row identity stay
in the states, so `tests/test_menus.py` behavior contracts hold unchanged.
All text goes through the baked pixel font via the state's Hud."""

import pygame


class MenuPanel:
    """Draws a centered panel of rows; the caller owns `sel` and `tick`."""

    def __init__(self, hud):
        self.hud = hud
        self._cache = {}                 # (w, h) -> panel surface

    # ------------------------------------------------------------ panels
    def panel(self, surf, x, y, w, h):
        key = (w, h)
        plate = self._cache.get(key)
        if plate is None:
            plate = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(plate, (12, 14, 30, 216),
                             pygame.Rect(0, 0, w, h), border_radius=5)
            pygame.draw.rect(plate, (78, 88, 128, 235),
                             pygame.Rect(0, 0, w, h), 1, border_radius=5)
            plate.fill((36, 42, 68, 150), pygame.Rect(1, 1, w - 2, 1))
            plate.fill((6, 8, 18, 150), pygame.Rect(1, h - 2, w - 2, 1))
            if len(self._cache) >= 64:
                self._cache.clear()
            self._cache[key] = plate
        surf.blit(plate, (x, y))

    # -------------------------------------------------------------- rows
    def draw(self, surf, cx, y0, labels, sel, tick, row_h=18,
             font=None, colors=None, values=None, value_x=None,
             panel_pad_x=16, panel_pad_y=10, panel=True):
        """Rows centered at `cx` starting `y0`.

        colors   -- optional per-row color override list (None = default
                    white/gray pair; disabled rows pass their own)
        values   -- optional right column (Options: "0.50", "ON"...)
        value_x  -- left edge of the value column (falls back to cx+40)
        tick     -- drives fade-in (first ~20 ticks) and cursor animation;
                    0..24 all render (tests draw before ticking) — fade
                    starts visible and only brightens.
        """
        font = font or self.hud.mid_font
        # staggered fade-in: row i finishes at tick 6 + i*3 (capped at 20)
        def alpha(i):
            return min(255, 96 + max(0, tick - i * 3) * 12)

        # measure for the panel box
        text_w = max((font.size(lbl)[0] for lbl in labels), default=0)
        if values:
            vw = max((self.hud.font.size(v)[0] for v in values), default=0)
            vx = value_x if value_x is not None else cx + 40
            right = vx + vw
        else:
            right = cx + text_w // 2
        left = cx - text_w // 2 - 12          # leave room for the cursor
        if panel:
            self.panel(surf, left - panel_pad_x, y0 - panel_pad_y,
                       (right - left) + panel_pad_x * 2,
                       len(labels) * row_h + panel_pad_y * 2 - (row_h - 7))

        cursor_x = left - 2
        for i, label in enumerate(labels):
            y = y0 + i * row_h
            if colors is not None and colors[i] is not None:
                color = colors[i]
            else:
                color = (255, 255, 255) if i == sel else (150, 156, 175)
            a = alpha(i)
            if i == sel:
                self._cursor(surf, cursor_x, y, tick, a)
            self._text(surf, left, y, label, color, font, a)
            if values and values[i] is not None:
                vx = value_x if value_x is not None else cx + 40
                self._text(surf, vx, y, values[i], color,
                           self.hud.font, a)

    # ----------------------------------------------------------- helpers
    def _text(self, surf, x, y, s, color, font, a):
        """Shadowed text with per-row alpha (copies: cache is shared)."""
        shadow = font.render(s, True, (16, 20, 40)).copy()
        img = font.render(s, True, color).copy()
        if a < 255:
            shadow.set_alpha(a)
            img.set_alpha(a)
        surf.blit(shadow, (x + 1, y + 1))
        surf.blit(img, (x, y))

    @staticmethod
    def _cursor(surf, x, y, tick, a):
        """Small arrow sprite, blinking on a 30-tick cadence, 1px bob."""
        if (tick // 15) % 2 == 0:
            return                                  # blink off-phase
        s = pygame.Surface((5, 7), pygame.SRCALPHA)
        for i, row in enumerate(("#....", "##...", "###..",
                                 "####.", "###..", "##...", "#....")):
            if row[0] == "#":
                s.set_at((0, i), (255, 226, 96, 255))
            if len(row) > 1 and row[1] == "#":
                s.set_at((1, i), (255, 226, 96, 255))
            if len(row) > 2 and row[2] == "#":
                s.set_at((2, i), (255, 226, 96, 255))
            if len(row) > 3 and row[3] == "#":
                s.set_at((3, i), (255, 226, 96, 255))
        if a < 255:
            s.set_alpha(a)
        surf.blit(s, (x, y + ((tick // 15) % 3) - 1))   # 1px bob
