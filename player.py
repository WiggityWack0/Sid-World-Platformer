"""
Player character for Sids World
"""

import pygame

class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 32
        self.height = 32
        self.vel_y = 0
        self.jumping = False
        self.speed = 5
        self.on_ground = True
        self._moving_left = False
        self._moving_right = False
        
    def set_moving(self, left=False, right=False):
        """Set horizontal movement flags for integrated collision handling."""
        self._moving_left = left
        self._moving_right = right
    
    def update(self, platforms):
        """Update player position and handle physics with integrated horizontal+vertical collision."""
        # Apply gravity
        self.vel_y += 0.8  # Gravity
        self.on_ground = False
        
        # Handle horizontal movement flags (set via set_moving)
        move_x = 0
        if self._moving_left:
            move_x -= self.speed
        if self._moving_right:
            move_x += self.speed
        
        # Process horizontal movement first with collision detection
        if move_x != 0:
            old_x = self.x
            self.x += move_x
            
            # Check for horizontal collisions
            player_rect = pygame.Rect(self.x, self.y, self.width, self.height)
            for platform in platforms:
                if player_rect.colliderect(platform.rect):
                    # Collision - revert horizontal movement
                    self.x = old_x
                    break
        
        # Now process vertical movement with collision detection
        new_y = self.y + self.vel_y
        player_rect = pygame.Rect(self.x, new_y, self.width, self.height)
        
        collision_detected = False
        for platform in platforms:
            if player_rect.colliderect(platform.rect):
                platform_rect = platform.rect
                
                # Calculate overlap amounts to determine collision direction
                left_overlap = player_rect.right - platform_rect.left
                right_overlap = platform_rect.right - player_rect.left
                top_overlap = player_rect.bottom - platform_rect.top  
                bottom_overlap = platform_rect.bottom - player_rect.top
                
                # Find the smallest overlap to determine collision side
                overlaps = [
                    (left_overlap, 'left'),
                    (right_overlap, 'right'), 
                    (top_overlap, 'top'),
                    (bottom_overlap, 'bottom')
                ]
                
                min_overlap, side = min(overlaps, key=lambda x: x[0])
                
                # Handle collision based on which side we hit
                if side == 'top' and self.vel_y > 0:
                    # Landing on platform from above - stop falling and land
                    new_y = platform.y - self.height
                    self.vel_y = 0
                    self.jumping = False
                    self.on_ground = True
                    collision_detected = True
                    break
                elif side == 'bottom' and self.vel_y < 0: 
                    # Hitting platform from below (hitting head) - stop upward movement
                    new_y = platform.y + platform.height
                    self.vel_y = 0
                    collision_detected = True
                    break
        
        # Fallback: Check if player is standing on a platform even with zero/negative velocity
        # This fixes the issue where jumps don't work when landing precisely
        if not collision_detected and self.vel_y >= 0:
            player_rect_ground = pygame.Rect(self.x, self.y + self.vel_y + 1, self.width, self.height)
            for platform in platforms:
                if player_rect_ground.colliderect(platform.rect):
                    platform_rect = platform.rect
                    # Check if player's bottom is below or at the platform top (standing on it)
                    if self.y + self.height >= platform_rect.top and self.y + self.height <= platform_rect.top + 10:
                        new_y = platform_rect.top - self.height
                        self.vel_y = 0
                        self.jumping = False
                        self.on_ground = True
                        collision_detected = True
                        break
        
        # Apply vertical position
        if not collision_detected:
            self.y += self.vel_y
        else:
            self.y = new_y
            
        # Prevent player from going off the left side of the level
        if self.x < 0:
            self.x = 0
            
    def jump(self):
        """Make the player jump."""
        if not self.jumping and self.on_ground:
            self.vel_y = -15
            self.jumping = True
            self.on_ground = False
            
    def draw(self, screen):
        """Draw the player on screen."""
        pygame.draw.rect(screen, (0, 255, 0), (self.x, self.y, self.width, self.height))
        
        # Draw simple eyes to make it recognizable
        pygame.draw.circle(screen, (0, 0, 0), (int(self.x + 8), int(self.y + 10)), 3)  
        pygame.draw.circle(screen, (0, 0, 0), (int(self.x + 24), int(self.y + 10)), 3)