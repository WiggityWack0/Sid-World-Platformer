"""HUD: SCORE / COINS / WORLD / TIME laid out along the top like SMW."""

import pygame

from src.assets.asset_factory import COIN_GOLD
from src.config import FX_KEY, HUD_TEXT, POWERUP_COLORS, VIEW_W


class Hud:
    def __init__(self):
        self.font = pygame.font.SysFont("consolas", 11, bold=True)
        self.big_font = pygame.font.SysFont("consolas", 26, bold=True)
        self.mid_font = pygame.font.SysFont("consolas", 16, bold=True)

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
             hearts=None, max_hearts=None, powerup=None, objective=None):
        self.text(surf, 14, 5, "SCORE")
        self.text(surf, 14, 17, f"{score:06d}")
        self.text(surf, 122, 5, "COINS")
        icon = self._coin_icon()
        surf.blit(icon, (122, 18))
        self.text(surf, 136, 17, f"x{coins:02d}")
        self.text(surf, 210, 5, "WORLD")
        self.text(surf, 214, 17, world_str)
        self.text(surf, 300, 5, "TIME")
        self.text(surf, 308, 17, f"{max(0, time_left):03d}")
        # lives marker
        self.text(surf, 356, 5, "LIVES")
        self.text(surf, 364, 17, f"x{lives:d}")
        # hearts row (D1) under the left of the SMW row
        if hearts is not None and max_hearts:
            for i in range(max_hearts):
                surf.blit(self._heart_icon(i < hearts), (14 + i * 11, 31))
        # power-up timer bar (2b) under the hearts row
        if powerup is not None:
            kind, frac = powerup
            color = POWERUP_COLORS.get(kind, HUD_TEXT)
            self.text(surf, 14, 40, kind[:1].upper(), color)
            pygame.draw.rect(surf, (40, 44, 60), pygame.Rect(24, 43, 40, 4))
            fill = int(40 * max(0.0, min(1.0, frac)))
            if fill > 0:
                pygame.draw.rect(surf, color, pygame.Rect(24, 43, fill, 4))
        # objective counter (3c): KEYS k/n
        if objective is not None:
            have, need = objective
            self.text(surf, 72, 40, f"KEYS {have}/{need}", FX_KEY)

    _coin_cache = None
    _heart_cache = {}

    def draw_boss_bar(self, surf, name, frac):
        """Top-center boss HP bar (5b, backward-compatible separate method)."""
        w = 160
        x = (VIEW_W - w) // 2
        y = 46
        self.text_center(surf, VIEW_W // 2, y - 12, name, (255, 226, 96))
        pygame.draw.rect(surf, (40, 44, 60), pygame.Rect(x, y, w, 7))
        fill = int(w * max(0.0, min(1.0, frac)))
        if fill > 2:
            pygame.draw.rect(surf, (232, 64, 72), pygame.Rect(x + 1, y + 1,
                                                              fill - 2, 5))
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
