"""All game constants and tunables."""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Window
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
TILE_SIZE = 48

# Physics — FAST, snappy, arcade feel
GRAVITY = 1.1
MAX_FALL_SPEED = 18
FRICTION = 0.82

# Sonic — FAST
SONIC_WALK_SPEED = 7.0
SONIC_RUN_SPEED = 13.0
SONIC_SPRINT_SPEED = 18.0
SONIC_JUMP_FORCE = -16.5
SONIC_WALL_SLIDE_SPEED = 3.0
SONIC_PUNCH_DAMAGE = 3
SONIC_PUNCH_RANGE = 90
SONIC_PUNCH_COOLDOWN = 200
SONIC_SPRINT_THRESHOLD = 800

# Tails — also fast
TAILS_WALK_SPEED = 6.5
TAILS_RUN_SPEED = 11.0
TAILS_JUMP_FORCE = -15.0
TAILS_FLY_FORCE = -7.0
TAILS_FLY_DURATION = 4000
TAILS_FLY_COOLDOWN = 3000
TAILS_TAIL_WHIP_DAMAGE = 2
TAILS_TAIL_WHIP_RANGE = 80

# Enemies — die faster
SMALL_ENEMY_HP = 1
MEDIUM_ENEMY_HP = 3
BOSS_HP_MULTIPLIER = 20

# Rings & Lives
STARTING_LIVES = 3
RINGS_PER_LIFE = 100
HIT_RING_SCATTER = 20

# Player health
PLAYER_MAX_HP = 3

# Combo system (Sonic)
COMBO_WINDOW = 400  # ms between hits or reset
COMBO_HIT1_DAMAGE = 1
COMBO_HIT1_DURATION = 150
COMBO_HIT2_DAMAGE = 1
COMBO_HIT2_DURATION = 200
COMBO_HIT3_DAMAGE = 2
COMBO_HIT3_DURATION = 300

# Colors
COLOR_SONIC_BLUE = (0, 80, 200)
COLOR_TAILS_ORANGE = (220, 140, 20)
COLOR_ENEMY_RED = (200, 40, 40)
COLOR_TILE_GRAY = (100, 100, 110)
COLOR_RING_GOLD = (255, 200, 0)
COLOR_BG_DARK = (10, 10, 20)
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_HUD_BG = (0, 0, 0, 150)

# World themes
WORLD_THEMES = {
    1: {
        "name": "Engine Deck",
        "bg_color": (30, 25, 35),
        "tile_color": (80, 85, 95),
        "accent": (255, 140, 0),
        "platform_color": (100, 100, 115),
    },
    2: {
        "name": "Bio-Dome",
        "bg_color": (10, 30, 15),
        "tile_color": (30, 100, 40),
        "accent": (100, 200, 255),
        "platform_color": (50, 120, 55),
    },
    3: {
        "name": "Cryo Deck",
        "bg_color": (15, 20, 40),
        "tile_color": (140, 170, 200),
        "accent": (180, 220, 255),
        "platform_color": (160, 190, 220),
    },
    4: {
        "name": "Weapons Bay",
        "bg_color": (35, 15, 15),
        "tile_color": (90, 60, 60),
        "accent": (255, 60, 40),
        "platform_color": (110, 70, 65),
    },
    5: {
        "name": "Dimension Rift",
        "bg_color": (20, 10, 35),
        "tile_color": (80, 50, 120),
        "accent": (255, 200, 50),
        "platform_color": (100, 60, 140),
    },
}

# Level names
LEVEL_NAMES = {
    (1, 1): "Ignition Corridor",
    (1, 2): "Gear Gallery",
    (1, 3): "Pressure Chase",
    (1, 4): "Core Chamber",
    (2, 1): "Overgrowth",
    (2, 2): "Spore Caverns",
    (2, 3): "Canopy Run",
    (2, 4): "The Hive Heart",
    (3, 1): "Frozen Freight",
    (3, 2): "Crystal Labyrinth",
    (3, 3): "Avalanche Alley",
    (3, 4): "Sub-Zero Core",
    (4, 1): "Arsenal Approach",
    (4, 2): "Laser Grid",
    (4, 3): "Detonation Run",
    (4, 4): "Command Bridge",
    (5, 1): "Rift Walk",
    (5, 2): "Portal Maze",
    (5, 3): "Final Pursuit",
    (5, 4): "Omega Core",
}

# Boss names
BOSS_NAMES = {
    1: "PISTON PRIME",
    2: "QUEEN SPORAX",
    3: "CRYO COLOSSUS",
    4: "GENERAL VOLT",
    5: "THE ROGUE AI",
}

# Difficulty curve per world
DIFFICULTY = {
    1: {"enemy_count": (5, 8), "enemy_speed": 1.5, "chase_speed": 8.0, "boss_hp": 12, "ring_density": 1.4},
    2: {"enemy_count": (8, 12), "enemy_speed": 1.8, "chase_speed": 10.0, "boss_hp": 20, "ring_density": 1.2},
    3: {"enemy_count": (10, 15), "enemy_speed": 2.0, "chase_speed": 12.0, "boss_hp": 30, "ring_density": 1.0},
    4: {"enemy_count": (12, 18), "enemy_speed": 2.3, "chase_speed": 14.0, "boss_hp": 40, "ring_density": 0.85},
    5: {"enemy_count": (15, 20), "enemy_speed": 2.5, "chase_speed": 16.0, "boss_hp": 50, "ring_density": 0.7},
}

# Asset paths
SPRITE_DIR = os.path.join(BASE_DIR, "assets", "sprites")
TILE_DIR = os.path.join(BASE_DIR, "assets", "tiles")
BG_DIR = os.path.join(BASE_DIR, "assets", "backgrounds")
SFX_DIR = os.path.join(BASE_DIR, "assets", "sfx")
LEVEL_DIR = os.path.join(BASE_DIR, "levels")
SAVE_FILE = os.path.join(BASE_DIR, "save.json")

# Sprite sheet mappings to actual files
SPRITE_FILES = {
    "sonic_main": "sonic-3.png",
    "sonic_alt": "sonic-2.png",
    "tails": "tails.png",
    "enemies_1": "badniks.png",
    "enemies_2": "badniks-2.png",
    "bosses": "bosses.png",
    "rings": "rings.png",
    "objects": "objects.png",
    "silver_sonic": "silver-sonic.png",
    "intro": "intro.png",
}
