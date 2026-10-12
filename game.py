"""
Game logic for Sids World
"""

import pygame

class Game:
    def __init__(self):
        self.running = True
        self.clock = pygame.time.Clock()
        
    def run(self, screen):
        """Main game loop."""
        while self.running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
            
            # Update game state
            
            # Draw everything
            screen.fill((100, 150, 255))  # Sky blue background
            
            # Update display
            pygame.display.flip()
            self.clock.tick(60)