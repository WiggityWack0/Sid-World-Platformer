#!/usr/bin/env python3
"""
Sids World - A Mario World Clone

This is the main entry point for the Sids World game.
"""

import pygame
import sys
from player import Player
from enemies import Enemy, RedEnemy, EnemyManager
from levels import Level
from sprites import PlayerSprite, PipeSprite

# Initialize Pygame
pygame.init()

# Game constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Scrolling constants
MAX_SCROLL_X = 20 * SCREEN_WIDTH  # 20 screen lengths
SCROLL_THRESHOLD = SCREEN_WIDTH * 0.75  # 75% of screen width from right edge

def reset_level():
    """Reset the level to initial state."""
    # Create game objects
    player = Player(100, 300)
    level = Level()

    # Create enemy manager for better enemy handling
    enemy_manager = EnemyManager()

    # Add a red chasing enemy (only enemy now)
    red_enemy = RedEnemy(400, 250)
    enemy_manager.add_enemy(red_enemy)

    return player, enemy_manager, level


def find_pipe_platforms(level):
    """Find pipe platforms from the level that can be used for transitions.
    
    Pipes are identified by their narrow width (32px) and significant height (>80px).
    Returns a list of tuples: (platform_rect, platform_object)
    """
    pipes = []

    for platform in level.platforms:
        # Pipes are narrow (32px wide) and tall (>80px high)
        if platform.width == 32 and platform.height > 80:
            pipe_rect = pygame.Rect(platform.x, platform.y, platform.width, platform.height)
            pipes.append((pipe_rect, platform))

    return pipes


def create_pipe_pairs(pipes):
    """Create explicit pipe pairs where each pipe connects to its nearest unpaired neighbor to the right.
    
    This ensures predictable, non-random transitions. Each pipe is paired with exactly one other pipe.
    
    Args:
        pipes: List of (pipe_rect, platform) tuples sorted by x position
        
    Returns:
        dict: Mapping from source pipe index to destination pipe index
    """
    if len(pipes) < 2:
        return {}
    
    # Sort pipes by x position (left to right)
    sorted_indices = sorted(range(len(pipes)), key=lambda i: pipes[i][0].x)
    
    paired = set()
    pipe_pairs = {}  # Maps source index -> destination index
    
    # Greedy approach: for each unpaired pipe, find the nearest unpaired pipe to its right
    for i in sorted_indices:
        if i in paired:
            continue
        
        # Find nearest unpaired pipe to the right (higher x value)
        best_j = None
        best_distance = float('inf')
        
        for j in sorted_indices:
            if j in paired or j == i:
                continue
            
            distance = pipes[j][0].x - pipes[i][0].x
            if distance > 0 and distance < best_distance:
                best_j = j
                best_distance = distance
        
        if best_j is not None:
            # Create bidirectional pair (both pipes connect to each other)
            pipe_pairs[i] = best_j
            pipe_pairs[best_j] = i
            paired.add(i)
            paired.add(best_j)
    
    return pipe_pairs


def handle_pipe_transitions(player, level, down_pressed=False):
    """Handle player entering pipes for transitions.
    
    When the player stands on a pipe AND presses the DOWN arrow key,
    they transition to their paired pipe location. This simulates going 
    through a warp pipe (like in Mario games).
    
    Each pipe is explicitly paired with its nearest unpaired neighbor to the right.
    
    Args:
        player: The Player object
        level: The Level object containing platforms
        down_pressed: Whether the DOWN arrow key is currently pressed
        
    Returns:
        bool: whether a transition occurred
    """
    pipes = find_pipe_platforms(level)
    if len(pipes) < 2:
        return False
    
    # Create explicit pipe pairs for predictable transitions
    pipe_pairs = create_pipe_pairs(pipes)
    if not pipe_pairs:
        return False
    
    # Player's current rect for collision detection
    player_rect = pygame.Rect(player.x, player.y, player.width, player.height)
    
    # Check if player is standing on any pipe AND down arrow is pressed
    for i, (pipe_rect, pipe_platform) in enumerate(pipes):
        # Expand pipe rect slightly to make it easier to trigger transitions
        expanded_pipe = pipe_rect.inflate(10, 10)
        
        if player_rect.colliderect(expanded_pipe) and down_pressed:
            # Player is on this pipe AND pressed DOWN - transition to paired pipe
            if i in pipe_pairs:
                next_idx = pipe_pairs[i]
                exit_pipe_rect, _ = pipes[next_idx]
                
                # Calculate new position at the exit pipe
                new_x = exit_pipe_rect.x
                new_y = exit_pipe_rect.y - player.height
                
                print(f"Pipe transition! Moving from pipe {i} ({pipe_rect.x}) to pipe {next_idx} ({exit_pipe_rect.x})")
                
                # Teleport player to exit pipe
                player.x = new_x
                player.y = new_y
                player.vel_y = 0
                player.jumping = False
                
                return True
    
    return False

def main():
    """Main function to run the game."""
    print("Starting Sids World - Level 1")

    # Set up the display
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Sids World - Level 1")
    clock = pygame.time.Clock()

    def create_game_objects():
        """Create fresh game objects."""
        player, enemy_manager, level = reset_level()

        # Create placeholder sprites (for visual representation)
        player_sprite = PlayerSprite(100, 300)
        pipe_sprites = [
            PipeSprite(300, 400, 100),   # Left pipe - properly positioned at ground level
            PipeSprite(500, 330, 170),   # Right pipe - top of pipe at y=500 (ground)
            PipeSprite(800, 400, 100),   # Additional pipe at x=800
            PipeSprite(1100, 350, 150),  # Additional pipe at x=1100
            PipeSprite(1400, 300, 200),  # Additional pipe at x=1400
            PipeSprite(1700, 250, 250),  # Additional pipe at x=1700
            PipeSprite(2000, 400, 100),  # Additional pipe at x=2000
            PipeSprite(2300, 330, 170),  # Additional pipe at x=2300
            PipeSprite(2600, 300, 200),  # Additional pipe at x=2600
            PipeSprite(2900, 250, 250),  # Additional pipe at x=2900
        ]

        camera_x = 0

        return player, enemy_manager, level, player_sprite, pipe_sprites, camera_x

    # Create initial game objects
    player, enemy_manager, level, player_sprite, pipe_sprites, camera_x = create_game_objects()

    running = True
    while running:
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    player.jump()

        # Update game objects
        # Handle continuous key presses and set movement flags
        keys = pygame.key.get_pressed()
        moving_left = keys[pygame.K_LEFT]
        moving_right = keys[pygame.K_RIGHT]
        down_pressed = keys[pygame.K_DOWN]
        player.set_moving(left=moving_left, right=moving_right)

        # Update player position and handle physics (now includes horizontal movement)
        player.update(level.platforms)

        # Check for collisions between player and red enemies
        player_rect = pygame.Rect(player.x, player.y, player.width, player.height)
        enemy_hit = False
        for enemy in enemy_manager.enemies:
            if isinstance(enemy, RedEnemy):
                enemy_rect = pygame.Rect(enemy.x, enemy.y, enemy.width, enemy.height)
                if player_rect.colliderect(enemy_rect):
                    # Player hit by red enemy - restart level
                    print("Player touched red enemy! Restarting level...")
                    # Reset everything including camera
                    player, enemy_manager, level = reset_level()
                    player_sprite = PlayerSprite(player.x, player.y)
                    pipe_sprites = [
                        PipeSprite(300, 400, 100),
                        PipeSprite(500, 330, 170),
                        PipeSprite(800, 400, 100),
                        PipeSprite(1100, 350, 150),
                        PipeSprite(1400, 300, 200),
                        PipeSprite(1700, 250, 250),
                        PipeSprite(2000, 400, 100),
                        PipeSprite(2300, 330, 170),
                        PipeSprite(2600, 300, 200),
                        PipeSprite(2900, 250, 250),
                    ]
                    camera_x = 0
                    enemy_hit = True
                    break

        # Update enemies with AI behavior (only if player wasn't hit)
        if not enemy_hit:
            enemy_manager.update_enemies(player.x, player.y)

        # Handle pipe transitions (requires player to press DOWN arrow while on pipe)
        handle_pipe_transitions(player, level, down_pressed)

        # Update camera position to follow player horizontally
        if player.x > SCREEN_WIDTH * 0.75 and camera_x < MAX_SCROLL_X:
            # When player reaches right side, start scrolling
            camera_x = max(0, int(player.x - SCREEN_WIDTH * 0.75))

        # Ensure camera doesn't scroll beyond maximum
        camera_x = min(camera_x, MAX_SCROLL_X)

        # Fill the screen with a sky blue background (like Super Mario World)
        screen.fill((100, 150, 255))

        # Draw everything
        level.draw(screen, camera_x)

        # Draw sprites after platforms to ensure they appear above them
        player_sprite.x = player.x
        player_sprite.y = player.y

        # Draw the player sprite (with camera offset like other elements)
        player_sprite.draw(screen, camera_x)

        # Draw pipes
        for pipe in pipe_sprites:
            pipe.draw(screen, camera_x)

        # Draw enemies (using updated positions from manager)
        enemy_manager.draw_enemies(screen, camera_x)

        # Update display
        pygame.display.flip()
        clock.tick(FPS)

    print("Thanks for playing Sids World!")
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()