"""Level loader: reads level JSON, creates tilemap, spawns entities.
Also contains the procedural level generator."""
import json
import os
import random
import math
from settings import (
    TILE_SIZE, LEVEL_DIR, DIFFICULTY, WORLD_THEMES, LEVEL_NAMES,
)
from entities.enemies import WORLD_ENEMIES, MEDIUM_ENEMIES


def generate_level(world, level, is_boss=False):
    """Procedurally generate a level JSON dict."""
    diff = DIFFICULTY[world]
    name = LEVEL_NAMES.get((world, level), f"World {world}-{level}")
    is_chase = (level == 3 and not is_boss)

    # Dimensions
    if is_boss:
        width = 25
        height = 15
    elif is_chase:
        width = 100
        height = 15
    else:
        base_width = 60 + world * 8 + level * 5
        width = base_width + random.randint(-5, 5)
        height = 15

    # Initialize tile layers
    main_tiles = [[0] * width for _ in range(height)]
    bg_tiles = [[0] * width for _ in range(height)]

    # Ground floor (bottom 2 rows)
    for x in range(width):
        main_tiles[height - 1][x] = 1
        main_tiles[height - 2][x] = 1

    if is_boss:
        # Boss arena: flat with walls on sides
        for y in range(height):
            main_tiles[y][0] = 1
            main_tiles[y][1] = 1
            main_tiles[y][width - 1] = 1
            main_tiles[y][width - 2] = 1
        # Ceiling
        for x in range(width):
            main_tiles[0][x] = 1

        # Some platforms
        for px in range(6, width - 6, 5):
            py = random.choice([5, 7, 9])
            for i in range(3):
                if px + i < width:
                    main_tiles[py][px + i] = 2

        level_data = {
            "world": world,
            "level": level,
            "name": name,
            "width": width,
            "height": height,
            "tile_layers": {"main": main_tiles, "background": bg_tiles, "foreground": []},
            "spawn": {"x": 4, "y": height - 4},
            "exit_door": None,
            "boss_spawn": {"x": width - 8, "y": height - 4},
            "checkpoints": [],
            "enemies": [],
            "rings": [],
            "hazards": [],
            "platforms": [],
            "chase_sequence": None,
            "is_boss": True,
        }
        return level_data

    # --- Generate terrain ---
    random.seed(world * 100 + level * 10)

    # Create gaps (pits) — small, jumpable, never near spawn/exit
    gap_positions = []
    if not is_chase:  # NO gaps in chase levels (continuous ground)
        num_gaps = 1 + world // 2
        for _ in range(num_gaps):
            gx = random.randint(12, width - 12)
            gw = 2  # always 2 tiles — very jumpable
            gap_positions.append((gx, gw))

    for gx, gw in gap_positions:
        for x in range(gx, min(gx + gw, width)):
            main_tiles[height - 1][x] = 0
            main_tiles[height - 2][x] = 0
        # Bridge: one-way platform right at gap
        for x in range(gx, min(gx + gw, width)):
            main_tiles[height - 4][x] = 2

    # Create elevated platforms — ALL one-way so they never block horizontal movement
    num_platforms = 8 + world * 2 + level * 2
    platform_data = []
    for _ in range(num_platforms):
        px = random.randint(5, width - 8)
        py = random.randint(3, height - 5)
        pw = random.randint(2, 5)
        for i in range(pw):
            if px + i < width:
                main_tiles[py][px + i] = 2  # always one-way
        platform_data.append({"x": px, "y": py, "w": pw})

    # Ramps / steps: short solid blocks (1 tile tall) as obstacles to jump over
    num_obstacles = 2 + world
    for _ in range(num_obstacles):
        ox = random.randint(10, width - 10)
        # Single tile obstacle at ground level — easy to jump over
        main_tiles[height - 3][ox] = 1

    # Hazards (spikes)
    hazards = []
    num_spikes = world + level
    for _ in range(num_spikes):
        sx = random.randint(10, width - 10)
        if main_tiles[height - 3][sx] == 0:
            main_tiles[height - 3][sx] = 3
            hazards.append({"type": "spike", "x": sx, "y": height - 3, "width": 1})

    # Background decoration
    for x in range(width):
        for y in range(height):
            if main_tiles[y][x] == 0 and random.random() < 0.03:
                bg_tiles[y][x] = 1

    # POST-GENERATION SAFETY: ensure the player running lane is clear
    # The running lane is at row height-3 and height-4 (above ground)
    # Remove any solid (type 1) blocks that would block horizontal movement
    for x in range(width):
        for y in [height - 3, height - 4, height - 5]:
            if main_tiles[y][x] == 1:
                main_tiles[y][x] = 0  # clear it

    # Spawn and exit
    spawn = {"x": 3, "y": height - 4}
    exit_door = {"x": width - 5, "y": height - 3}

    # Checkpoints
    checkpoints = []
    cp_spacing = width // (3 + level)
    for i in range(1, 3):
        cx = cp_spacing * i + random.randint(-5, 5)
        cx = max(10, min(cx, width - 10))
        checkpoints.append({"x": cx, "y": height - 3})

    # Enemies
    enemies = []
    world_enemy_types = WORLD_ENEMIES.get(world, ["bolt_bug"])
    min_e, max_e = diff["enemy_count"]
    num_enemies = random.randint(min_e, max_e)
    if is_chase:
        num_enemies = num_enemies // 2  # Fewer enemies in chase levels

    for _ in range(num_enemies):
        ex = random.randint(15, width - 10)
        ey = height - 3
        # Find ground level at this x
        for check_y in range(height - 3, 0, -1):
            if main_tiles[check_y][ex] != 0:
                ey = check_y - 1
                break
        etype = random.choice(world_enemy_types)
        enemies.append({
            "type": etype,
            "x": ex,
            "y": ey,
            "patrol_range": random.randint(3, 6),
        })

    # Medium enemies (from world 2+)
    if world >= 2:
        num_medium = min(3, world - 1)
        for _ in range(num_medium):
            ex = random.randint(20, width - 15)
            ey = height - 4
            etype = random.choice(MEDIUM_ENEMIES)
            enemies.append({"type": etype, "x": ex, "y": ey, "patrol_range": 5})

    # Rings
    rings = []
    ring_density = diff["ring_density"]
    num_ring_groups = int(15 * ring_density) + level * 2
    for _ in range(num_ring_groups):
        rx = random.randint(5, width - 5)
        ry = random.randint(3, height - 4)
        count = random.randint(3, 6)
        pattern = random.choice(["line", "arc"])
        rings.append({
            "x": rx, "y": ry, "count": count,
            "spacing": 1.5, "pattern": pattern,
        })

    # Steam vents (world 1 mechanic)
    steam_vents = []
    if world == 1:
        for _ in range(3 + level):
            vx = random.randint(10, width - 10)
            steam_vents.append({
                "type": "steam_vent", "x": vx, "y": height - 3,
                "interval": 2.0, "boost_force": -15,
            })
        hazards.extend(steam_vents)

    # Moving platforms
    moving_platforms = []
    num_moving = 2 + level
    for _ in range(num_moving):
        mpx = random.randint(10, width - 15)
        mpy = random.randint(4, height - 5)
        moving_platforms.append({
            "type": "moving",
            "x": mpx, "y": mpy, "width": 3,
            "path": [{"x": mpx, "y": mpy}, {"x": mpx, "y": mpy - 4}],
            "speed": 1.0 + random.random(),
        })

    # Chase sequence config
    chase_config = None
    if is_chase:
        chase_config = {
            "trigger_x": 20,
            "scroll_speed_start": diff["chase_speed"] * 0.7,
            "scroll_speed_max": diff["chase_speed"],
            "acceleration": 0.003 + world * 0.001,
            "mega_threat_projectile_interval": max(1.5, 4.0 - world * 0.5),
        }

    level_data = {
        "world": world,
        "level": level,
        "name": name,
        "width": width,
        "height": height,
        "tile_layers": {"main": main_tiles, "background": bg_tiles, "foreground": []},
        "spawn": spawn,
        "exit_door": exit_door,
        "checkpoints": checkpoints,
        "enemies": enemies,
        "rings": rings,
        "hazards": hazards,
        "platforms": moving_platforms,
        "chase_sequence": chase_config,
        "is_boss": False,
    }

    return level_data


def generate_all_levels():
    """Generate all 20 level JSON files."""
    os.makedirs(LEVEL_DIR, exist_ok=True)
    levels = {}

    for world in range(1, 6):
        for level in range(1, 5):
            is_boss = (level == 4)
            data = generate_level(world, level, is_boss)
            key = f"{world}-{level}"
            levels[key] = data

            # Save to file
            path = os.path.join(LEVEL_DIR, f"world_{world}_{level}.json")
            with open(path, "w") as f:
                json.dump(data, f)

    return levels


def load_level(world, level):
    """Load a level from JSON file, or generate it if missing."""
    path = os.path.join(LEVEL_DIR, f"world_{world}_{level}.json")

    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)

    # Generate and save
    is_boss = (level == 4)
    data = generate_level(world, level, is_boss)
    os.makedirs(LEVEL_DIR, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f)
    return data
