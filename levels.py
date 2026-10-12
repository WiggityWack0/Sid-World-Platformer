"""
Level design and management for Sids World - Level 1 based on Super Mario World's first level
"""

import pygame

class Platform:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.rect = pygame.Rect(x, y, width, height)
        
    def draw(self, screen, camera_x=0):
        """Draw the platform using a placeholder color."""
        # Green platforms like in Super Mario World
        pygame.draw.rect(screen, (0, 150, 0), (self.x - camera_x, self.y, self.width, self.height))
        # Draw platform top to simulate block texture
        pygame.draw.line(screen, (0, 120, 0), (self.x - camera_x, self.y), (self.x + self.width - camera_x, self.y), 2)

class Castle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 150
        self.height = 200
        self.rect = pygame.Rect(x, y, self.width, self.height)
        
    def draw(self, screen, camera_x=0):
        """Draw the castle with a door."""
        # Draw castle base
        pygame.draw.rect(screen, (139, 69, 19), (self.x - camera_x, self.y, self.width, self.height))
        
        # Draw castle towers (left and right)
        pygame.draw.rect(screen, (139, 69, 19), (self.x - camera_x - 20, self.y - 40, 20, 40))
        pygame.draw.rect(screen, (139, 69, 19), (self.x + self.width - camera_x, self.y - 40, 20, 40))
        
        # Draw castle roof
        pygame.draw.polygon(screen, (139, 69, 19), [
            (self.x - camera_x - 20, self.y - 40),
            (self.x + self.width // 2 - camera_x, self.y - 80),
            (self.x + self.width + 20 - camera_x, self.y - 40)
        ])
        
        # Draw door
        pygame.draw.rect(screen, (101, 67, 33), (self.x + 50 - camera_x, self.y + 100, 30, 80))
        
        # Draw window
        pygame.draw.rect(screen, (255, 255, 0), (self.x + 100 - camera_x, self.y + 50, 20, 20))

class Level:
    def __init__(self):
        # Create platforms for level 1 based on Super Mario World's first level
        self.platforms = [
            # Ground platforms - this should be at y=500 to match the screen height 
            Platform(0, 500, 800, 100),      # Main ground platform
            
            # First set of platforms (like in SMB1)
            Platform(200, 400, 150, 20),     # High platform on left side
            Platform(450, 350, 150, 20),     # Middle platform  
            Platform(100, 300, 100, 20),     # Low platform on left
            Platform(600, 250, 150, 20),     # High platform on right side
            
            # Pipes (like in SMB) - properly positioned to rest directly on the ground 
            # The pipe height is 100 units tall so we need y = 500-100=400 for a pipe that rests
            Platform(300, 400, 32, 100),     # Pipe 1 (height 100)
            Platform(500, 330, 32, 170),     # Pipe 2 (height 170)
            Platform(800, 400, 32, 100),     # Pipe 3 (height 100)
            Platform(1100, 350, 32, 150),    # Pipe 4 (height 150)
            Platform(1400, 300, 32, 200),    # Pipe 5 (height 200)
            Platform(1700, 250, 32, 250),    # Pipe 6 (height 250)
            Platform(2000, 400, 32, 100),    # Pipe 7 (height 100)
            Platform(2300, 330, 32, 170),    # Pipe 8 (height 170)
            Platform(2600, 300, 32, 200),    # Pipe 9 (height 200)
            Platform(2900, 250, 32, 250),    # Pipe 10 (height 250)
            
            # Floating platforms for jumping 
            Platform(150, 280, 60, 20),
            Platform(400, 260, 60, 20),
            Platform(650, 230, 60, 20),
            
            # Additional platforms throughout the level
            Platform(900, 400, 100, 20),     # Middle platform at right side
            Platform(1100, 350, 120, 20),    # High platform near the end
            Platform(1300, 300, 80, 20),     # Low platform in middle
            Platform(1500, 250, 150, 20),    # High platform towards the end
            Platform(1700, 200, 100, 20),    # Very high platform
            
            # More platforms for variety
            Platform(2000, 400, 100, 20),    # Middle platform at further right
            Platform(2200, 350, 120, 20),    # High platform 
            Platform(2400, 300, 80, 20),     # Low platform
            Platform(2600, 250, 150, 20),    # High platform
            
            # Final platforms leading to castle - ensure there's a clear path
            Platform(2800, 200, 100, 20),    # High platform near end
            Platform(3000, 150, 100, 20),    # Very high platform
            Platform(3200, 100, 100, 20),    # Even higher platform
            
            # Safety platforms - ensure no gaps where player can fall through
            # These connect floating platforms and prevent fall-through traps
            Platform(750, 480, 100, 20),     # Bridge between ground sections (overlaps with both)
            Platform(950, 450, 80, 20),      # Safety platform near pipe 3-4 gap
            Platform(1250, 450, 80, 20),     # Safety platform near pipe 4-5 gap
            Platform(1550, 450, 80, 20),     # Safety platform near pipe 5-6 gap
            Platform(1850, 450, 80, 20),     # Safety platform near pipe 6-7 gap
            Platform(2150, 450, 80, 20),     # Safety platform near pipe 7-8 gap
            Platform(2450, 450, 80, 20),     # Safety platform near pipe 8-9 gap
            Platform(2750, 450, 80, 20),     # Safety platform near pipe 9-10 gap
            
            # Extended ground to allow proper scrolling - make it really long
            Platform(800, 500, 10000, 100),   # Very long extended ground at the right end for proper scrolling
        ]
        
        # Create the castle finish line at the very end of the level
        self.castle = Castle(3200, 400)  # Positioned at the end of the level (closer to visible area)
        
    def draw(self, screen, camera_x=0):
        """Draw all platforms in the level."""
        for platform in self.platforms:
            platform.draw(screen, camera_x)
        
        # Draw the castle
        self.castle.draw(screen, camera_x)