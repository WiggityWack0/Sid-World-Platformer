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
# Slice 4 D1 length table. Per-zone reset semantics remain intentional;
# only the numeric table changes. Zones 0-1 start at 6 screens and grow by 3;
# zones 2-3 start at 10 screens and grow by 5.
ZONE_START_LEN = (6, 6, 10, 10)
ZONE_LEN_GROWTH = (3, 3, 5, 5)
TILES_PER_SCREEN = VIEW_W // TILE # 25

# ------------------------------------------------------------------- zones
LEVELS_PER_ZONE = 5
LEVELS_PER_RUN = LEVELS_PER_ZONE * 4        # 20 levels (4 zones x 5)

ZONES = (
    {"name": "Green Hills", "music_a": "level_a", "music_b": "level_b",
     "ambient": "leaves", "palette": None,   # None = legacy palette (identity)
     "primer": "MASTER THE JUMP"},   # zone-0 = identity (6c)
    {"name": "Ember Caves", "music_a": "level_c", "music_b": "level_c",
     "ambient": "embers", "primer": "WATCH THE CEILING", "palette": {
         "sky_top": (40, 16, 28), "sky_bottom": (140, 60, 30),
         "cloud": (120, 80, 90), "cloud_dk": (90, 60, 70),
         "hills_far_body": (60, 30, 40), "hills_far_crest": (90, 50, 50),
         "hills_near_body": (90, 44, 36), "hills_near_crest": (130, 70, 50),
         "dirt": (70, 46, 40), "dirt_dk": (50, 32, 28), "dirt_lt": (95, 64, 52),
         "grass": (200, 90, 40), "grass_dk": (150, 60, 30),
         "grass_lt": (230, 140, 70),
         "brick": (140, 60, 50), "brick_dk": (100, 40, 34)}},
    {"name": "Frost Peaks", "music_a": "level_d", "music_b": "level_d",
     "ambient": "snow", "primer": "SPACE YOUR JUMPS", "palette": {
         "sky_top": (150, 190, 235), "sky_bottom": (225, 240, 252),
         "cloud": (250, 252, 255), "cloud_dk": (220, 230, 245),
         "hills_far_body": (140, 170, 200), "hills_far_crest": (180, 205, 228),
         "hills_near_body": (100, 140, 190), "hills_near_crest": (160, 195, 225),
         "dirt": (110, 140, 175), "dirt_dk": (80, 105, 135),
         "dirt_lt": (150, 180, 210),
         "grass": (225, 240, 250), "grass_dk": (190, 215, 235),
         "grass_lt": (245, 250, 255),
         "brick": (130, 150, 180), "brick_dk": (95, 115, 145)}},
    {"name": "Storm Keep", "music_a": "level_e", "music_b": "level_e",
     "ambient": "rain", "primer": "EVERYTHING COMBINED", "palette": {
         "sky_top": (52, 52, 74), "sky_bottom": (110, 105, 135),
         "cloud": (130, 130, 150), "cloud_dk": (100, 100, 120),
         "hills_far_body": (60, 60, 80), "hills_far_crest": (85, 85, 105),
         "hills_near_body": (70, 80, 70), "hills_near_crest": (100, 115, 100),
         "dirt": (80, 72, 64), "dirt_dk": (58, 50, 44), "dirt_lt": (104, 94, 84),
         "grass": (110, 140, 90), "grass_dk": (80, 105, 65),
         "grass_lt": (145, 175, 120),
         "brick": (105, 90, 100), "brick_dk": (78, 64, 74)}},
)  # palettes themed in 4b; zone 0 uses the legacy palette for identity


def zone_of(level_index):
    """Zone derived FROM level_index (§8.8) — never a free parameter."""
    return max(0, min(len(ZONES) - 1, level_index // LEVELS_PER_ZONE))


def zone_level_of(level_index):
    return max(0, level_index % LEVELS_PER_ZONE)


def difficulty_for(level_index):
    """Linear 0->1 across the full 20-level run (Phase 4a)."""
    return min(1.0, level_index / max(1, LEVELS_PER_RUN - 1))


def level_length_screens(zone, zone_level):
    """Per-zone length: resets each zone (§10 4a; recorded semantic change).

    Slice 4 makes the zone explicit so zones 2-3 can start longer than
    zones 0-1 while preserving the per-zone reset behavior.
    """
    zone = max(0, min(len(ZONES) - 1, int(zone)))
    zone_level = max(0, int(zone_level))
    return ZONE_START_LEN[zone] + zone_level * ZONE_LEN_GROWTH[zone]

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

# ---------------------------------------------------------------- effects
PARTICLE_CAP = 400            # hard cap; oldest recycled when full
SHAKE_DECAY = 0.03            # trauma lost per tick (~0.55 s from full)
SHAKE_MAGNITUDE = 8.0         # px at full trauma (before clamp)
SHAKE_MAX_OFFSET = 6          # hard clamp on shake px
SHAKE_DEATH = 0.7             # trauma added on player death
FLOATER_CAP = 32
FLOATER_LIFE = 48             # ticks a floater stays visible
FLOATER_RISE = 0.8            # px/tick upward drift
RUN_DUST_INTERVAL = 5         # ticks between run dust puffs

# -------------------------------------------------------------- game rules
START_LIVES = 3
START_TIME = 400
TIME_MAX = 700                  # upper bound for length-scaled level timers
TIME_PER_EXTRA_SCREEN = 12      # timer units granted per screen beyond 6
TIME_INTERVAL_FRAMES = 24       # one timer unit per 24 ticks
COINS_PER_LIFE = 100
def time_for(level_index):
    """Length-scaled level timer (Slice 5 D2).

    Pure function of level_index: short levels keep the original 400-unit
    budget, while longer levels receive extra time but not proportional time.
    This preserves the intended difficulty increase while avoiding unfair
    timeouts on 18- and 30-screen levels.
    """
    screens = level_length_screens(
        zone_of(level_index), zone_level_of(level_index))
    extra = max(0, screens - 6) * TIME_PER_EXTRA_SCREEN
    return max(START_TIME, min(TIME_MAX, START_TIME + extra))



# scoring ladder (2d-audited): coin 100 < stomp 200 < kick 300 <
# form kill 400 = star kill 400 < boss 5000 (Phase 5)
COIN_SCORE = 100
STOMP_SCORE = 200
KICK_SCORE = 300
BREAK_SCORE = 50
TIME_BONUS_PER_UNIT = 50
COIN_CLEAR_BONUS = 50
RESPAWN_INVULN = 90           # i-frames (flicker) after respawn
HEARTS_START = 3              # D1: hearts base (max raised by containers)
HEARTS_MAX = 6                # D1: hard cap on max hearts
HURT_INVULN = 90              # i-frames after taking damage
HURT_KNOCKBACK_X = 3.0        # px/tick away from the damage source
HURT_KNOCKBACK_Y = -5.0       # upward pop on being hurt
HURT_TRAUMA = 0.3             # screen shake added on damage

# ----------------------------------------------------------- power-ups (2b)
POWERUP_DURATION = 600        # ticks a timed power-up lasts (~10 s)
POWERUP_KINDS = ("star", "speed", "jump", "heart")
POWERUP_HEART_CHANCE = 12     # 1-in-N of placed power-ups is a heart container
POWERUP_SPEED_MULT = 1.25     # speed boost: max run/walk multiplier
POWERUP_JUMP_MULT = 1.15      # jump enhance: takeoff velocity multiplier
POWERUP_JUMP_GRAV_MULT = 0.85  # jump enhance: floatier arc
STAR_KILL_SCORE = 400         # side-contact kill while star is active

# --------------------------------------------------- forms & attack (2c)
FORMS = ("fire", "ice", "lightning")
ATTACK_COOLDOWN = 30          # ticks between C presses
FIREBALL_SPEED = 6.0
ICE_SHARD_SPEED = 4.5
FIREBALL_LIFE = 90            # ticks a fired projectile lives
ICE_FREEZE_TICKS = 180        # how long an ice shard locks an enemy
LIGHTNING_RADIUS = 80         # px (Chebyshev box) from the player
LIGHTNING_MAX_TARGETS = 3
FORM_KILL_SCORE = 400         # score for a form kill (provisional; 2d audits)

# ------------------------------------------------- plates & lava (3b-1)
TIMED_DOOR_TICKS = 300        # window a timed door stays open (~5 s)

# ------------------------------------------------- objectives (3c)
SHARDS_PLACED = 3             # shards dropped per generated level
SHARDS_REQUIRED = 2           # "collect K of N" goal-lock rule
SHARD_SCORE = 500
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
SPITTER_WINDUP = 16            # visible wind-up pose before firing (SI-C)
PROJECTILE_SPEED = 2.4
PROJECTILE_LIFE = 130
FLYER_AMP_Y = 26
FLYER_AMP_X = 48
FLYER_W = 0.035

# ------------------------------------------------- new enemy types (5a)
SHIELDKIN_SPEED = 0.9
BOMBER_SPEED = 0.7
BOMBER_COOLDOWN = 140
BOMBER_RANGE = 190
BOMBER_ARC_TOL = 120           # |dy| band where the bomber will lob
BOMB_GRAV = 0.22
BOMB_VY0 = -4.6
BOMB_LIFE = 150
BOMB_BURST = 22                # ticks of AoE burst after detonation
WALLCRAWLER_SPEED = 1.0
WALLCRAWLER_CLIMB = 1.1
WALLCRAWLER_DROP_DX = 36       # |dx| under which it drops from the ceiling
CHARGER_PATROL = 0.8
CHARGER_WINDUP = 34            # telegraph ticks before the dash
CHARGER_DASH_SPEED = 4.6
CHARGER_DASH_TICKS = 46
CHARGER_RANGE = 170
CHARGER_ACQUIRE_DY = 70
NEEDLER_COOLDOWN = 150
NEEDLER_RANGE = 260
NEEDLER_VY_TOL = 90
NEEDLER_SHOT_SPEED = 3.2
NEEDLER_LEAD = 0.85            # how much of the target's velocity is led

# ------------------------------------------------------ boss framework (5b)
ARENA_COLS = 16                # width of the carved boss arena tail
BOSS_BANNER_TICKS = 120        # WARNING banner duration on first activation

# ------------------------------------------------------ concrete bosses (5c)
BOULDER_HP = 6
BOULDER_SLAM_CYCLE = 130       # idle ticks between slams (minus phase)
BOULDER_ROCK_VY = -5.2
GOLEM_HP = 8
GOLEM_EXPOSE_TICKS = 220       # core stays exposed after a switch press
OWL_HP = 6
OWL_HOVER_RISE = 70            # px above its spawn floor the owl hovers
OWL_DIVE_SPEED = 5.0
MONARCH_HP = 9
MONARCH_VOLLEY_CD = 130        # minus phase scaling
MONARCH_PUDDLE_TICKS = 360     # lava puddle lifetime (runtime tile edit)

# ------------------------------------------------------------------ audio
AUDIO_RATE = 44100
MASTER_VOLUME = 0.8
MUSIC_VOLUME = 0.45
SFX_VOLUME = 0.75
VOLUME_STEP = 0.1               # options-menu adjust step (6a)
FADE_TICKS = 18                 # state-transition fade length (6b)

# ------------------------------------------- spatial SFX + tutorials (6c)
SPATIAL_PAN_PX = 160.0          # full stereo pan at +/- this offset
SPATIAL_RANGE = 480.0           # linear falloff to silence (1.5 screens)
PRIMER_TICKS = 150              # zone-primer banner duration

# ------------------------------------------------------------------ colors
SKY_TOP = (92, 148, 250)
SKY_BOTTOM = (172, 214, 255)
HUD_TEXT = (255, 255, 255)
HUD_OUTLINE = (24, 32, 64)
OVERLAY_DIM = (0, 0, 0, 150)
FX_DUST = (208, 196, 168)
FX_SPARK = (255, 236, 132)
FX_COIN = (255, 212, 96)
FX_DEBRIS = (168, 96, 56)
FX_STOMP = (255, 255, 255)
FX_DEATH_1 = (255, 128, 96)
FX_DEATH_2 = (255, 224, 128)
FX_HURT = (255, 96, 96)
FX_KEY = (120, 230, 255)
AMBIENT_INTERVAL = 10            # ticks between ambient particles (4b)
AMBIENT_COLORS = {"leaves": (96, 168, 64), "embers": (255, 140, 40),
                  "snow": (240, 248, 255), "rain": (150, 185, 235)}

# ---------------------------------------------------- save / progression (4c)
SAVE_PATH = "save/progress.json"   # project-local (D3); one line to relocate
SCHEMA_VERSION = 1                 # bumped on breaking schema changes
POWERUP_COLORS = {"star": (255, 224, 96), "speed": (96, 208, 255),
                  "jump": (140, 255, 130), "heart": (232, 48, 64)}
FORM_COLORS = {"fire": (255, 128, 48), "ice": (128, 224, 255),
               "lightning": (255, 240, 120)}
FX_ICE_TINT = (120, 200, 255, 90)

# -------------------------------------------------------------------- keys
# action name -> pygame key constants are mapped in src/inputs.py
CONTROLS = {
    "left":    ["Left", "A"],
    "right":   ["Right", "D"],
    "down":    ["Down", "S"],
    "jump":    ["Z", "Space"],
    "run":     ["X", "Shift"],
    "attack":  ["C"],
    "form":    ["F"],
    "pause":   ["P"],
    "mute":    ["M"],
    "restart": ["R"],
    "confirm": ["Return", "Z", "Space"],
}


# --------------------------------------------------------------- controller
# First-pass gamepad support (pygame-ce joystick subsystem): one pad, no
# vibration, no remapping (later polish slice). SDL's standard Xbox layout:
# A=0 B=1 X=2 Y=3 LB=4 RB=5 Back=6 Start=7.
# Button presses are translated into synthetic KEYDOWN events using the
# same key names as CONTROLS, so the whole state machine works unchanged.
CONTROLLER_BUTTONS = {
    0: ("Space", "Return"),   # A: Space = jump in play; Return = confirm in
                              #    menus (Space reads as "jump" there, so the
                              #    extra key makes one button do both)
    1: ("Escape",),           # B: back in menus / pause-resume in play
    2: ("C",),                # X: attack
    3: ("F",),                # Y: cycle form
    6: ("M",),                # Back: mute (global)
    7: ("P",),                # Start: pause
}
CONTROLLER_HELD = {           # action -> buttons polled as held (no keydown)
    "jump": (0,),             # A: keeps variable jump height + stomp hold
    "run": (4, 5),            # LB / RB
}
STICK_DEADZONE = 0.25         # analog stick deadzone (fraction of full tilt)


def jump_envelope():
    """Return the jump envelope used by generator + validator (px units)."""
    return {
        "max_height": MAX_JUMP_HEIGHT,
        "max_distance": MAX_JUMP_DISTANCE,
        "up_tiles": UP_TILES,
        "dist_tiles": DIST_TILES,
        "flight_frames": FLIGHT_FRAMES,
    }
