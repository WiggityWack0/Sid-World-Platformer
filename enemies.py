"""
Enemy classes for Sids World
"""

import pygame

class Enemy:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 32
        self.height = 32
        self.speed = 2
        
    def update(self):
        """Update enemy position."""
        # Basic movement - move back and forth
        self.x += self.speed
        
        # Simple AI: turn around at edges (for now)
        if self.x > 768 or self.x < 0:
            self.speed *= -1
            
    def draw(self, screen, camera_x=0):
        """Draw the enemy on screen."""
        pygame.draw.rect(screen, (255, 0, 0), (self.x - camera_x, self.y, self.width, self.height))

class RedEnemy(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y)
        # Set a different color for this enemy
        self.color = (255, 0, 0)  # Red color
        
    def update(self, player_x, player_y):
        """Update enemy position to chase the player at half speed."""
        # Calculate distance to player  
        dx = player_x - self.x
        dy = player_y - self.y
        
        # Normalize direction vector (avoid division by zero)
        distance = max(1, (dx**2 + dy**2)**0.5)
        
        # Move toward player at half speed 
        move_speed = self.speed / 2
        
        if abs(dx) > 0 or abs(dy) > 0:
            # Calculate movement vector
            move_x = dx * move_speed / distance
            move_y = dy * move_speed / distance
            
            self.x += move_x
            self.y += move_y
            
    def draw(self, screen, camera_x=0):
        """Draw the red enemy with a distinctive appearance."""
        pygame.draw.rect(screen, self.color, (self.x - camera_x, self.y, self.width, self.height))
        
        # Add simple eyes to make it more recognizable as an enemy
        pygame.draw.circle(screen, (0, 0, 0), (int(self.x - camera_x + 8), int(self.y + 10)), 3)  
        pygame.draw.circle(screen, (0, 0, 0), (int(self.x - camera_x + 24), int(self.y + 10)), 3)
        
        # Draw a simple "angry" expression or enemy features
        pygame.draw.arc(screen, (0, 0, 0), (self.x - camera_x + 5, self.y + 15, 22, 10), 0, 3.14, 2)  # Smile

class EnemyManager:
    def __init__(self):
        self.enemies = []
        
    def add_enemy(self, enemy):
        """Add an enemy to the manager."""
        self.enemies.append(enemy)
        
    def update_enemies(self, player_x, player_y):
        """Update all enemies with AI behavior."""
        for enemy in self.enemies:
            if isinstance(enemy, RedEnemy):
                # Enemy that follows player
                enemy.update(player_x, player_y)
            else:
                # Basic movement for regular enemies
                enemy.update()
                
    def draw_enemies(self, screen, camera_x=0):
        """Draw all enemies."""
        for enemy in self.enemies:
            enemy.draw(screen, camera_x)
