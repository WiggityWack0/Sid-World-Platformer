"""SMW-style camera: right-pans freely, never shows left of x=0, smooth
vertical follow with a dead zone, clamped to level bounds."""

from src.config import VIEW_W, VIEW_H, CAMERA_LAG, CAMERA_PAN_FRAC


class Camera:
    def __init__(self, level_w, level_h):
        self.x = 0.0
        self.y = 0.0
        self.max_x = max(0, level_w - VIEW_W)
        self.max_y = max(0, level_h - VIEW_H)
        self.shake_dx = 0                # visual-only view offset (Game.fx)
        self.shake_dy = 0

    def set_shake(self, dx, dy):
        """Apply a visual shake offset; gameplay math keeps using x/y.

        Clamped away from level edges so shaking never reveals the void
        beyond the world bounds.
        """
        dx, dy = int(dx), int(dy)
        if self.x <= 0.0:
            dx = max(0, dx)
        elif self.x >= self.max_x:
            dx = min(0, dx)
        if self.y <= 0.0:
            dy = max(0, dy)
        elif self.y >= self.max_y:
            dy = min(0, dy)
        self.shake_dx = dx
        self.shake_dy = dy

    def snap_to(self, target):
        """Jump instantly (used on spawn/respawn)."""
        self.x = min(max(0.0, target.right - VIEW_W * CAMERA_PAN_FRAC),
                     self.max_x)
        self.y = min(max(0.0, target.centery - VIEW_H * 0.55), self.max_y)

    def update(self, target):
        desired = self.x
        pan_edge = self.x + VIEW_W * CAMERA_PAN_FRAC
        if target.right > pan_edge:
            desired = target.right - VIEW_W * CAMERA_PAN_FRAC
        if target.left < self.x + 4:
            desired = target.left - 4
        self.x += (desired - self.x) * CAMERA_LAG
        self.x = min(max(0.0, self.x), self.max_x)

        center = target.centery
        if center < self.y + VIEW_H * 0.40:
            desired_y = center - VIEW_H * 0.40
        elif center > self.y + VIEW_H * 0.72:
            desired_y = center - VIEW_H * 0.72
        else:
            desired_y = self.y
        self.y += (desired_y - self.y) * CAMERA_LAG
        self.y = min(max(0.0, self.y), self.max_y)

    @property
    def ix(self):
        return int(self.x) + self.shake_dx

    @property
    def iy(self):
        return int(self.y) + self.shake_dy

    def apply(self, x, y):
        return x - self.ix, y - self.iy

    def visible(self, rect, margin=32):
        return (rect.right > self.x - margin
                and rect.left < self.x + VIEW_W + margin
                and rect.bottom > self.y - margin
                and rect.top < self.y + VIEW_H + margin)
