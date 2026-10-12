"""
Placeholder sprite classes for Sids World
"""

import pygame

class Sprite:
    def __init__(self, x, y, width=32, height=32, color=(100, 150, 255)):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.color = color
        self.rect = pygame.Rect(x, y, width, height)
        
    def draw(self, screen):
        """Draw a placeholder sprite."""
        pygame.draw.rect(screen, self.color, (self.x, self.y, self.width, self.height))
        # Add simple details to make it recognizable as a character
        pygame.draw.circle(screen, (255, 255, 0), (self.x + self.width//2, self.y + self.height//2), 5)
        
    def update(self):
        """Update sprite position."""
        pass

class PlayerSprite(Sprite):
    def __init__(self, x, y):
        super().__init__(x, y, 32, 32, (0, 255, 0))
        
    def draw(self, screen, camera_x=0):
        """Draw player character with a simple green rectangle and circle."""
        pygame.draw.rect(screen, self.color, (self.x - camera_x, self.y, self.width, self.height))
        # Draw eyes
        pygame.draw.circle(screen, (0, 0, 0), (self.x - camera_x + 8, self.y + 10), 3)
        pygame.draw.circle(screen, (0, 0, 0), (self.x - camera_x + 24, self.y + 10), 3)
        
    def update(self):
        """Update player sprite position."""
        pass

class EnemySprite(Sprite):
    def __init__(self, x, y):
        super().__init__(x, y, 32, 32, (255, 0, 0))
        
    def draw(self, screen, camera_x=0):
        """Draw enemy with a simple red rectangle."""
        pygame.draw.rect(screen, self.color, (self.x - camera_x, self.y, self.width, self.height))
        # Draw eyes
        pygame.draw.circle(screen, (0, 0, 0), (self.x - camera_x + 8, self.y + 10), 3)
        pygame.draw.circle(screen, (0, 0, 0), (self.x - camera_x + 24, self.y + 10), 3)

class PipeSprite(Sprite):
    def __init__(self, x, y, height):
        super().__init__(x, y, 32, height, (150, 75, 0))
        
    def draw(self, screen, camera_x=0):
        """Draw a pipe sprite."""
        # Draw the main pipe
        pygame.draw.rect(screen, self.color, (self.x - camera_x, self.y, self.width, self.height))
        # Draw top of pipe
        pygame.draw.rect(screen, (120, 60, 0), (self.x - camera_x - 5, self.y - 10, self.width + 10, 10))