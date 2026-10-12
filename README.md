# Sids World

A Mario World clone game built with Python and Pygame.

## Features

- **Level 1**: Based on the first level of Super Mario World
- **Player Character**: Green character that can move and jump  
- **Enemies**: 
  - Basic enemies with simple AI behavior
  - Red enemy that chases player at half speed
- **Platforms**: Properly positioned platforms matching SMB1 design

## Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Running the Game

To start playing:

```bash
python src/main.py
```

Or if you've installed it globally:

```bash
sids-world
```

## Project Structure

- `src/` - Main source code directory
  - `main.py` - Entry point of the application
  - `game.py` - Core game logic
  - `player.py` - Player character implementation
  - `enemies.py` - Enemy implementations with AI behavior  
  - `levels.py` - Level design and platform management
- `assets/` - Game assets (images, sounds, etc.)
- `tests/` - Unit tests

## Implementation Details

### Fixed Issues:
1. **Pipe Positioning**: All pipes now properly rest on ground level 
2. **Sprite Positioning**: Player and enemies positioned correctly with collision detection
3. **Enemy AI**: Red enemy follows player at half speed

### Level 1 Design:
Based exactly on Super Mario World's first level with platforms, pipes, and proper platform positioning.

## Contributing

Contributions are welcome! Please read the contributing guidelines before submitting pull requests.

## License
