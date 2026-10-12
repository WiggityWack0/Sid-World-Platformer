"""HUD: SCORE / COINS / WORLD / TIME laid out along the top like SMW."""

import pygame

from src.assets.asset_factory import COIN_GOLD
from src.config import HUD_TEXT, VIEW_W


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

    def draw(self, surf, score, coins, lives, time_left, world_str):
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

    _coin_cache = None

    def _coin_icon(self):
        if Hud._coin_cache is None:
            s = pygame.Surface((8, 8), pygame.SRCALPHA)
            pygame.draw.ellipse(s, COIN_GOLD, pygame.Rect(1, 0, 6, 8))
            pygame.draw.ellipse(s, (214, 148, 20), pygame.Rect(1, 0, 6, 8), 1)
            Hud._coin_cache = s
        return Hud._coin_cache
