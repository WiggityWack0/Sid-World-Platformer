"""Level select (Phase 4d): 4x5 node grid, locking, best scores, boss markers.

Cursor navigation clamps at the grid edges; Enter plays an unlocked node
with a deterministic per-node seed (pure int math — no RNG consumption, so
the self-consistency determinism tests hold); Esc returns to title.
"""

import pygame

from src import inputs
from src import progress
from src.assets.asset_factory import DEFAULT_PAL
from src.config import (LEVELS_PER_RUN, LEVELS_PER_ZONE, VIEW_H, VIEW_W,
                        ZONES)
from src.states.base import State


def _accent(zone):
    """Zone accent color from the themed palette (4b) — keeps the grid on-
    theme without building any new surfaces."""
    pal = ZONES[zone]["palette"] or DEFAULT_PAL
    return pal.get("grass_lt", (255, 255, 255))


class LevelSelectState(State):
    name = "level_select"

    NODE_W = 30
    NODE_H = 22
    COL_GAP = 46
    ROW_GAP = 30
    ORIGIN_X = (VIEW_W - 4 * 46) // 2      # 5 cols -> width 4*46 + 30
    ORIGIN_Y = 64

    def on_enter(self, **kwargs):
        # start the cursor on the highest unlocked level (nice default)
        self.cursor = min(self.game.progress.get("unlocked_level_index", 0),
                          LEVELS_PER_RUN - 1)
        self.game.audio.play_music("title")

    # ----------------------------------------------------------- metadata
    def is_boss(self, idx):
        """Zone-final levels are boss nodes (bosses arrive in Phase 5)."""
        return idx % LEVELS_PER_ZONE == LEVELS_PER_ZONE - 1

    def best_score(self, idx):
        return self.game.progress.get("best_scores", {}).get(str(idx), 0)

    def node_rect(self, idx):
        row, col = divmod(idx, LEVELS_PER_ZONE)
        return pygame.Rect(self.ORIGIN_X + col * self.COL_GAP,
                           self.ORIGIN_Y + row * self.ROW_GAP,
                           self.NODE_W, self.NODE_H)

    # -------------------------------------------------------------- input
    def _try_play(self):
        idx = self.cursor
        if not progress.is_unlocked(self.game.progress, idx):
            self.game.audio.play_sfx("select", vol=0.5)   # denied
            return
        self.game.audio.play_sfx("confirm")
        # Deterministic per-node seed: pure int math, NO RNG (4d).
        self.game.seed = (self.game.seed + 104729 * (idx + 1)) % 100000
        self.game.new_run()
        self.game.run.level_index = idx
        self.game.switch_state("playing")

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN or event.key == pygame.K_m:
            return
        if event.key == pygame.K_ESCAPE:
            self.game.audio.play_sfx("select")
            self.game.switch_state("title")
            return
        row, col = divmod(self.cursor, LEVELS_PER_ZONE)
        moved = False
        if event.key == pygame.K_UP:
            row, moved = max(0, row - 1), True
        elif event.key == pygame.K_DOWN:
            row, moved = min(len(ZONES) - 1, row + 1), True
        elif event.key == pygame.K_LEFT:
            col, moved = max(0, col - 1), True
        elif event.key == pygame.K_RIGHT:
            col, moved = min(LEVELS_PER_ZONE - 1, col + 1), True
        elif inputs.key_to_action(event.key) == "confirm":
            self._try_play()
            return
        if moved:
            self.cursor = row * LEVELS_PER_ZONE + col
            self.game.audio.play_sfx("select", vol=0.5)

    def update(self):
        pass

    # --------------------------------------------------------------- draw
    def draw(self, surf):
        game = self.game
        surf.fill((16, 20, 40))
        dim = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 120))
        surf.blit(dim, (0, 0))
        hud = game.hud
        tick = game.tick

        zone = self.cursor // LEVELS_PER_ZONE
        hud.text_center(surf, VIEW_W // 2, 14, "LEVEL SELECT",
                        (255, 226, 96), hud.big_font)
        hud.text_center(surf, VIEW_W // 2, 44,
                        f"ZONE {zone + 1}: {ZONES[zone]['name']}")

        # path lines between consecutive nodes (Phase 4 T5): drawn under
        # the nodes, tinted by the destination zone's accent, dimmed when
        # the destination is still locked
        for idx in range(1, LEVELS_PER_RUN):
            a = self.node_rect(idx - 1).center
            b = self.node_rect(idx).center
            acc = _accent(idx // LEVELS_PER_ZONE)
            if not progress.is_unlocked(game.progress, idx):
                acc = tuple(c // 3 for c in acc)
            pygame.draw.line(surf, acc, a, b, 1)

        for idx in range(LEVELS_PER_RUN):
            rect = self.node_rect(idx)
            unlocked = progress.is_unlocked(game.progress, idx)
            accent = _accent(idx // LEVELS_PER_ZONE)
            body = accent if unlocked else (58, 62, 78)
            pygame.draw.rect(surf, body, rect)
            pygame.draw.rect(surf, (20, 24, 40), rect, 1)
            if not unlocked:                       # locked dim overlay
                ov = pygame.Surface(rect.size, pygame.SRCALPHA)
                ov.fill((0, 0, 0, 90))
                surf.blit(ov, rect.topleft)
            if self.is_boss(idx):
                # danger glyph (Phase 4 T5): triangle + "!" instead of "B"
                cx, cy = rect.centerx, rect.centery - 5
                col = (255, 255, 255) if unlocked else (110, 114, 130)
                pygame.draw.polygon(surf, (232, 64, 72) if unlocked
                                    else (90, 60, 70),
                                    [(cx, cy - 6), (cx + 6, cy + 4),
                                     (cx - 6, cy + 4)])
                hud.text_center(surf, cx, cy - 3, "!", col, hud.font)
            elif not unlocked:
                pygame.draw.rect(surf, (34, 38, 54), rect.inflate(-8, -8), 1)
            label = str(idx % LEVELS_PER_ZONE + 1)
            hud.text_center(surf, rect.centerx, rect.bottom + 3, label)
            # unlocked glint on the cursor node (Phase 4 T5)
            if idx == self.cursor and unlocked and (tick // 12) % 2 == 0:
                gx, gy = rect.right - 3, rect.top + 2
                for dx, dy in ((0, 0), (1, -1), (-1, -1), (1, 1), (-1, 1),
                               (0, -2), (0, 2)):
                    surf.set_at((gx + dx, gy + dy), (255, 255, 255))
            if idx == self.cursor:
                # cursor: arrow sprite left of the node + white border
                game.menu._cursor(surf, rect.left - 9, rect.centery - 3,
                                  tick, 255)
                pygame.draw.rect(surf, (255, 255, 255), rect.inflate(6, 6), 2)

        cursor_zone = _accent(zone)
        best = self.best_score(self.cursor)
        # info footer on a panel (Phase 4 T4 component)
        game.menu.panel(surf, VIEW_W // 2 - 110, VIEW_H - 60, 220, 46)
        hud.text_center(surf, VIEW_W // 2, VIEW_H - 52,
                        f"LEVEL {self.cursor + 1}"
                        f"{'  (BOSS)' if self.is_boss(self.cursor) else ''}",
                        cursor_zone)
        hud.text_center(surf, VIEW_W // 2, VIEW_H - 36,
                        f"BEST {best:06d}" if best else "BEST ------")
        hud.text_center(surf, VIEW_W // 2, VIEW_H - 18,
                        "ENTER PLAY   ESC TITLE   ARROWS MOVE")
