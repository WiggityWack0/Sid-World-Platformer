"""Effects service (Game.fx): particles + screen shake + floaters.

Visual-only feedback layer — never touches physics, collision, or any
gameplay state. States/enemies emit via the small helpers here; draw after
the world, before the HUD.
"""

from src.effects.floaters import Floaters
from src.effects.particles import ParticleSystem
from src.effects.shake import Shake


class Effects:
    def __init__(self):
        self.particles = ParticleSystem()
        self.shake = Shake()
        self.floaters = Floaters()

    # ------------------------------------------------------------- lifecycle
    def update(self):
        self.particles.update()
        self.shake.update()
        self.floaters.update()

    def draw(self, surf, cam):
        self.particles.draw(surf, cam)
        self.floaters.draw(surf, cam)

    # -------------------------------------------------------------- helpers
    def dust(self, x, y):
        self.particles.dust(x, y)

    def spark(self, x, y, color=None):
        self.particles.spark(x, y, color)

    def coin_burst(self, x, y):
        self.particles.coin_burst(x, y)

    def debris(self, x, y, color=None):
        self.particles.debris(x, y, color)

    def explosion(self, x, y):
        self.particles.explosion(x, y)

    def stomp_puff(self, x, y):
        self.particles.stomp_puff(x, y)

    def ambient(self, kind, cam):
        """One ambient particle for the zone's theme (4b)."""
        self.particles.ambient(kind, cam.x)

    def floater(self, x, y, text, color=None):
        self.floaters.spawn(x, y, text, color)

    def add_trauma(self, amount):
        self.shake.add(amount)

    def shake_offset(self):
        return self.shake.offset()
