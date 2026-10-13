"""
Boss framework (Phase 5b): HP pool, phase thresholds, telegraph and
stagger windows, multi-tick defeat sequence.

Concrete bosses arrive in 5c; this base is exercised by a test double.
The validator never simulates bosses — beatability is proven by
scripted-sim integration tests (plan §8.7 documented limitation).
"""

import pygame

from src.enemies.base import Enemy

BOSS_BODY = (148, 60, 72)
BOSS_BODY_HI = (196, 84, 92)
BOSS_OUTLINE = (40, 20, 28)


class Boss(Enemy):
    """Multi-segment HP, 2-3 attack phases, telegraph/stagger windows."""

    KIND = "boss"
    is_boss = True              # duck-typed flag (no isinstance dispatch)
    name = "BOSS"               # HP-bar label (concrete bosses override)
    W = 32
    H = 32
    MAX_HP = 6
    PHASE_THRESHOLDS = (0.66, 0.33)   # hp/max <= t -> next phase
    TELEGRAPH = 30                    # telegraph ticks before an attack
    STAGGER = 90                      # vulnerable window on phase change
    DEFEAT_TICKS = 90                 # explosion sequence length

    def __init__(self, x, y):
        super().__init__(x, y)
        self.max_hp = self.MAX_HP
        self.hp = self.MAX_HP
        self.phase = 0
        self.telegraph = 0
        self.stagger = 0
        self.defeat_timer = 0
        self.defeated = False

    # ----------------------------------------------------------- damage
    def take_damage(self, amount=1):
        """Forms/star/stomp damage against the HP pool. True = killed."""
        if self.state == "dying" or self.defeated:
            return False
        self.hp = max(0, self.hp - amount)
        if self.hp <= 0:
            self.start_defeat()
            return True
        new_phase = sum(1 for t in self.PHASE_THRESHOLDS
                        if self.hp <= self.max_hp * t)
        if new_phase > self.phase:
            self.phase = new_phase
            self.stagger = self.STAGGER      # phase change = stagger open
        return False

    def start_defeat(self):
        self.state = "dying"
        self.defeat_timer = self.DEFEAT_TICKS
        self.death_timer = self.DEFEAT_TICKS  # keep manager from culling
        self.vx = self.vy = 0.0

    def stomped(self, player=None):
        if self.stagger > 0:
            self.take_damage(1)
            return "stomp"
        return "bounce"                       # armored: bounce, no damage

    def reset(self):
        super().reset()
        self.hp = self.max_hp
        self.phase = 0
        self.telegraph = 0
        self.stagger = 0
        self.defeat_timer = 0
        self.defeated = False

    # ----------------------------------------------------------- update
    def update(self, level, player):
        if self.state == "dying":
            self.anim_t += 1
            self.defeat_timer -= 1
            self.death_timer = max(self.death_timer, self.defeat_timer)
            if self.defeat_timer <= 0:
                self.defeated = True
            return
        if self.stagger > 0:
            self.stagger -= 1
        if self.telegraph > 0:
            self.telegraph -= 1
        super().update(level, player)

    # -------------------------------------------------------------- draw
    def draw(self, surf, cam, assets, tick):
        """Runtime-drawn original body; concrete bosses (5c) override."""
        r = self.rect
        body = BOSS_BODY
        if self.stagger > 0 and (tick // 5) % 2 == 0:
            body = BOSS_BODY_HI               # flash while vulnerable
        pygame.draw.rect(surf, body,
                         pygame.Rect(r.x - cam.ix, r.y - cam.iy, r.w, r.h))
        pygame.draw.rect(surf, BOSS_OUTLINE,
                         pygame.Rect(r.x - cam.ix, r.y - cam.iy, r.w, r.h), 2)
        eye_y = r.y - cam.iy + 8
        pygame.draw.rect(surf, (255, 240, 200),
                         pygame.Rect(r.x - cam.ix + 6, eye_y, 5, 4))
        pygame.draw.rect(surf, (255, 240, 200),
                         pygame.Rect(r.x - cam.ix + r.w - 11, eye_y, 5, 4))