"""HUD: SCORE / COINS / WORLD / TIME laid out along the top like SMW.

Text goes through the baked pixel font (Phase 4): `font` / `mid_font` /
`big_font` are `PixelFont` faces (scale 1/2/3) — the `text` / `text_center`
signatures and SysFont-era behavior (1px shadow, width return) are
preserved so every existing caller works unchanged."""

import pygame

from src.assets.asset_factory import COIN_GOLD
from src.assets.pixel_font import PixelFont
from src.config import FX_KEY, HUD_TEXT, POWERUP_COLORS, VIEW_W


class Hud:
    def __init__(self):
        self.font = PixelFont(1)          # body / HUD row
        self.mid_font = PixelFont(2)      # menu rows
        self.big_font = PixelFont(3)      # titles
        self._panel = self._make_panel(372, 24)     # status-row plate
        self._sub_panel = self._make_panel(96, 18)  # hearts / bar plate
        # Objective variant of the sub-plate (UX fix): the KEYS counter at
        # (72, 40) used to hang off the 96px plate's right/bottom edge onto
        # bare sky. This plate stretches just far enough to swallow the
        # text + 1px shadow + 3px pad; height 19 covers the shadow row 47.
        keys_w = 72 + self.font.size("KEYS 9/9")[0] + 4 - 14
        self._sub_panel_obj = self._make_panel(keys_w, 19)
        self._boss_plate = {}             # name -> precomputed plate

    # ------------------------------------------------------------ panels
    @staticmethod
    def _make_panel(w, h):
        """9-slice-ish rounded plate (Phase 4 T3), precomputed."""
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(s, (10, 12, 26, 176), pygame.Rect(0, 0, w, h),
                         border_radius=4)
        pygame.draw.rect(s, (64, 72, 104, 220), pygame.Rect(0, 0, w, h), 1,
                         border_radius=4)
        s.fill((30, 34, 56, 120), pygame.Rect(1, 1, w - 2, 1))  # top edge
        return s

    def text(self, surf, x, y, s, color=HUD_TEXT, font=None):
        font = font or self.font
        shadow = font.render(s, True, (16, 20, 40))
        surf.blit(shadow, (x + 1, y + 1))
        img = font.render(s, True, color)
        surf.blit(img, (x, y))
        return img.get_width()

    def text_center(self, surf, cx, y, s, color=HUD_TEXT, font=None):
        font = font or self.font
        w = font.size(s)[0]
        return self.text(surf, int(cx - w / 2), y, s, color, font)

    def draw(self, surf, score, coins, lives, time_left, world_str,
             hearts=None, max_hearts=None, powerup=None, objective=None,
             tick=None):
        # status-row plate first so text/icons land on top (T3).
        # Coordinates are UNCHANGED from the SysFont era — the catalogued
        # region-scan tests (test_hp / test_powerups / test_puzzle_objects)
        # pin these positions.
        surf.blit(self._panel, (14, 2))
        # low-time pulse: red digits under 100 on a 15-tick blink (T3)
        time_color = HUD_TEXT
        if tick is not None and 0 < time_left < 100:
            if (tick // 15) % 2 == 0:
                time_color = (255, 96, 96)
        self.text(surf, 20, 6, "SCORE")
        self.text(surf, 20, 17, f"{score:06d}")
        self.text(surf, 124, 6, "COINS")
        icon = self._coin_icon()
        surf.blit(icon, (124, 18))
        self.text(surf, 138, 17, f"x{coins:02d}")
        self.text(surf, 208, 6, "WORLD")
        self.text(surf, 212, 17, world_str)
        self.text(surf, 296, 6, "TIME")
        self.text(surf, 304, 17, f"{max(0, time_left):03d}", time_color)
        # lives marker
        self.text(surf, 348, 6, "LIVES")
        self.text(surf, 356, 17, f"x{lives:d}")
        # sub-plate (D1): hearts/bar row — stretched when the KEYS counter
        # is shown so the objective renders ON the panel, never on the sky.
        if (hearts is not None and max_hearts) or objective is not None:
            surf.blit(self._sub_panel_obj if objective is not None
                      else self._sub_panel, (14, 29))
        if hearts is not None and max_hearts:
            low = hearts <= 1 and tick is not None and (tick // 12) % 2 == 1
            for i in range(max_hearts):
                img = self._heart_icon(i < hearts)
                if low and i < hearts:
                    img = img.copy()                 # pulse: never mutate cache
                    img.fill((255, 140, 140),
                             special_flags=pygame.BLEND_RGB_MULT)
                surf.blit(img, (14 + i * 11, 31))
        # power-up timer bar (2b) under the hearts row
        if powerup is not None:
            kind, frac = powerup
            color = POWERUP_COLORS.get(kind, HUD_TEXT)
            self.text(surf, 14, 40, kind[:1].upper(), color)
            pygame.draw.rect(surf, (40, 44, 60), pygame.Rect(24, 43, 40, 4))
            fill = int(40 * max(0.0, min(1.0, frac)))
            if fill > 0:
                pygame.draw.rect(surf, color, pygame.Rect(24, 43, fill, 4))
        # objective counter (3c): KEYS k/n (on the stretched plate above)
        if objective is not None:
            have, need = objective
            self.text(surf, 72, 40, f"KEYS {have}/{need}", FX_KEY)

    _coin_cache = None
    _heart_cache = {}

    def draw_boss_bar(self, surf, name, frac):
        """Top-center boss HP bar (5b): segmented fill + name plate (T3)."""
        w = 160
        x = (VIEW_W - w) // 2
        y = 46
        # name plate, precomputed per boss name
        plate = self._boss_plate.get(name)
        if plate is None:
            nw = self.font.size(name)[0] + 12
            plate = self._make_panel(nw, 13)
            self._boss_plate[name] = plate
        surf.blit(plate, ((VIEW_W - plate.get_width()) // 2, y - 15))
        self.text_center(surf, VIEW_W // 2, y - 13, name, (255, 226, 96))
        pygame.draw.rect(surf, (40, 44, 60), pygame.Rect(x, y, w, 7))
        fill = int(w * max(0.0, min(1.0, frac)))
        # segmented chunks (8px fill, 1px gap) for a gamey look
        seg = 8
        for sx in range(x + 1, x + w - 1, seg):
            chunk = max(0, min(sx + seg - 1, x + fill) - sx)
            if chunk > 1:
                pygame.draw.rect(surf, (232, 64, 72),
                                 pygame.Rect(sx, y + 1, min(chunk, 6), 5))
        pygame.draw.rect(surf, (16, 20, 40), pygame.Rect(x, y, w, 7), 1)

    def _coin_icon(self):
        if Hud._coin_cache is None:
            s = pygame.Surface((8, 8), pygame.SRCALPHA)
            pygame.draw.ellipse(s, COIN_GOLD, pygame.Rect(1, 0, 6, 8))
            pygame.draw.ellipse(s, (214, 148, 20), pygame.Rect(1, 0, 6, 8), 1)
            Hud._coin_cache = s
        return Hud._coin_cache

    def _heart_icon(self, full):
        """Tiny original heart (runtime pixel art); full or empty."""
        if full not in Hud._heart_cache:
            s = pygame.Surface((9, 9), pygame.SRCALPHA)
            fill = (232, 48, 64) if full else (52, 56, 72)
            pygame.draw.circle(s, fill, (2, 3), 2)
            pygame.draw.circle(s, fill, (6, 3), 2)
            pygame.draw.polygon(s, fill, [(0, 3), (8, 3), (4, 8)])
            if full:
                pygame.draw.circle(s, (255, 152, 160), (2, 2), 1)  # shine
            Hud._heart_cache[full] = s
        return Hud._heart_cache[full]
