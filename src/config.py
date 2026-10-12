"""
Central configuration for Sids World.

Every tunable constant lives here. Physics values are expressed in
pixels per fixed 1/60 s tick (updates run on a fixed timestep).
"""

import math

# ------------------------------------------------------------------ display
TILE = 16
VIEW_W = 400                      # virtual playfield width  (25 tiles)
VIEW_H = 240                      # virtual playfield height (15 tiles)
WINDOW_SCALE = 3                  # integer upscale, pixel-crisp
WINDOW_W = VIEW_W * WINDOW_SCALE  # 1200
WINDOW_H = VIEW_H * WINDOW_SCALE  # 720
FPS = 60
FIXED_DT = 1.0 / FPS

# ------------------------------------------------------------------- level
LEVEL_H_TILES = 18                # 288 px -> some vertical camera travel
GROUND_ROW = 14                   # default surface row (solid begins here)
MIN_FLOOR_ROW = 11                # highest ground may climb
MAX_FLOOR_ROW = 15                # lowest ground may sink
START_LEN_SCREENS = 2             # level 1 is ~2 screens wide
LEN_GROWTH = 1                    # +1 screen per further level
MAX_LEVELS_PER_RUN = 5
LEVELS_PER_RUN = 5              # levels per play-through
TILES_PER_SCREEN = VIEW_W // TILE # 25

# --------------------------------------------------------- player physics
GRAVITY = 0.55
JUMP_VELOCITY = -9.5
JUMP_CUT_FACTOR = 0.45            # release jump => vy *= factor
TERMINAL_VY = 10.0
WALK_ACCEL = 0.40
RUN_ACCEL = 0.50
MAX_WALK = 2.6
MAX_RUN = 4.2
FRICTION = 0.30
SKID_DECEL = 0.80
COYOTE_FRAMES = 6
JUMP_BUFFER_FRAMES = 6
PLAYER_W = 12
PLAYER_H = 26
PLAYER_CROUCH_H = 16
STOMP_BOUNCE = -7.5
STOMP_BOUNCE_HOLD = -9.5          # full jump when jump held on stomp

# ------------------------------------------- derived jump envelope (validator)
MAX_JUMP_HEIGHT = JUMP_VELOCITY ** 2 / (2.0 * GRAVITY)   # ~82.0 px
APEX_FRAMES = abs(JUMP_VELOCITY) / GRAVITY                # ~17.3 ticks
FLIGHT_FRAMES = 2.0 * APEX_FRAMES                         # ~34.5 ticks
MAX_JUMP_DISTANCE = MAX_RUN * FLIGHT_FRAMES               # ~145 px
UP_TILES = int(MAX_JUMP_HEIGHT // TILE)                   # 5
DIST_TILES = int(MAX_JUMP_DISTANCE // TILE)               # 9
SAFE_GAP_TILES = 6            # generator hard cap for pits
SAFE_STEP_TILES = 4           # generator hard cap for a single jump-up
MAX_FALL_DRIFT_TILES = 4      # validator: horizontal drift while falling

# ----------------------------------------------------------------- camera
CAMERA_LAG = 0.12
CAMERA_PAN_FRAC = 0.60        # SMW: pan once player passes 60% of view
CAMERA_V_DEADZONE = 40
BG_PARALLAX = (0.15, 0.35, 0.6)   # sky/far, hills, bushes rates

# -------------------------------------------------------------- game rules
START_LIVES = 3
START_TIME = 400
TIME_INTERVAL_FRAMES = 24     # one timer unit per 24 ticks
COINS_PER_LIFE = 100
COIN_SCORE = 100
STOMP_SCORE = 200
KICK_SCORE = 300
BREAK_SCORE = 50
TIME_BONUS_PER_UNIT = 50
COIN_CLEAR_BONUS = 50
RESPAWN_INVULN = 90           # i-frames (flicker) after respawn
DEATH_ANIM_FRAMES = 70
STOMP_TOLERANCE = 10          # px below enemy top still counts as stomp
ACTIVATION_FRAC = 1.5         # enemies activate within 1.5 screens
WARP_ENTER_FRAMES = 12        # frames holding DOWN on a pipe to warp

# ----------------------------------------------------------------- enemies
WALKER_SPEED = 1.2
SHELLBACK_SPEED = 1.1
SHELL_SLIDE_SPEED = 5.0
SHELL_LIFETIME = 360
CHASER_PATROL_SPEED = 1.6
CHASER_CHASE_SPEED = 2.9
CHASER_AGGRO = 160
CHASER_DEAGGRO = 260
JUMPER_HOP_VY = -7.0
JUMPER_HOP_VX = 2.6
JUMPER_HOP_COOLDOWN = 55
JUMPER_RANGE = 190
SPITTER_COOLDOWN = 110
SPITTER_RANGE = 210
SPITTER_VY_TOL = 56
PROJECTILE_SPEED = 2.4
PROJECTILE_LIFE = 130
FLYER_AMP_Y = 26
FLYER_AMP_X = 48
FLYER_W = 0.035

# ------------------------------------------------------------------ audio
AUDIO_RATE = 44100
MASTER_VOLUME = 0.8
MUSIC_VOLUME = 0.45
SFX_VOLUME = 0.75

# ------------------------------------------------------------------ colors
SKY_TOP = (92, 148, 250)
SKY_BOTTOM = (172, 214, 255)
HUD_TEXT = (255, 255, 255)
HUD_OUTLINE = (24, 32, 64)
OVERLAY_DIM = (0, 0, 0, 150)

# -------------------------------------------------------------------- keys
# action name -> pygame key constants are mapped in src/inputs.py
CONTROLS = {
    "left":    ["Left", "A"],
    "right":   ["Right", "D"],
    "down":    ["Down", "S"],
    "jump":    ["Z", "Space"],
    "run":     ["X", "Shift"],
    "pause":   ["P"],
    "mute":    ["M"],
    "restart": ["R"],
    "confirm": ["Return", "Z", "Space"],
}


def jump_envelope():
    """Return the jump envelope used by generator + validator (px units)."""
    return {
        "max_height": MAX_JUMP_HEIGHT,
        "max_distance": MAX_JUMP_DISTANCE,
        "up_tiles": UP_TILES,
        "dist_tiles": DIST_TILES,
        "flight_frames": FLIGHT_FRAMES,
    }
