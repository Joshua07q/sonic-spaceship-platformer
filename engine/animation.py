"""Sprite sheet parser with auto-detected bounding boxes and proper color-keying."""
import os
import pygame
from settings import SPRITE_DIR, SPRITE_FILES

# ---------------------------------------------------------------------------
# Hard-coded sprite regions obtained by scanning the actual PNGs.
# Each entry: (x, y, w, h)  — pixel rectangle in the source sheet.
# ---------------------------------------------------------------------------

# sonic.gif  265x351, bg=(0,128,128)
_SONIC_REGIONS = {
    # Row 0 – standing / idle / looking
    "idle": [
        (8, 5, 16, 40), (29, 5, 21, 40), (55, 5, 17, 40), (83, 5, 22, 40),
    ],
    # Row 1 – running
    "run": [
        (6, 52, 21, 32), (38, 52, 21, 32), (69, 52, 22, 32), (104, 52, 24, 32),
    ],
    # Row 2 – spin ball
    "spin": [
        (3, 92, 20, 24), (27, 92, 20, 24), (50, 92, 20, 24), (75, 92, 20, 24),
        (101, 92, 20, 24),
    ],
    # Row 3 – spring / big jump
    "jump": [
        (2, 124, 28, 32), (38, 124, 24, 32),
    ],
    # Row 4 – push / skid / misc
    "push": [
        (4, 161, 18, 33), (28, 161, 20, 33), (59, 161, 21, 33),
        (86, 161, 17, 33), (108, 161, 20, 33),
    ],
    # Row 5 – hurt / falling
    "hurt": [
        (4, 200, 18, 30), (28, 200, 17, 30), (52, 200, 18, 30), (76, 200, 17, 30),
    ],
    # Row 6 – looking up / crouching
    "crouch": [
        (3, 239, 24, 30), (30, 239, 23, 30),
    ],
}

# tails.png  300x120, bg=(0,71,139)
_TAILS_REGIONS = {
    # Row 0 – standing / idle (9 frames)
    "idle": [
        (15, 12, 21, 24), (44, 12, 22, 24), (74, 12, 22, 24), (104, 12, 22, 24),
    ],
    # Row 0 continued – walking / running
    "run": [
        (134, 12, 23, 24), (165, 12, 22, 24), (195, 12, 23, 24), (226, 12, 22, 24),
    ],
    # Row 1 – flying / tails spinning (8 frames)
    "fly": [
        (21, 41, 24, 29), (53, 41, 24, 29), (84, 41, 24, 29), (116, 41, 24, 29),
        (148, 41, 24, 29), (180, 41, 24, 29), (212, 41, 24, 29), (244, 41, 24, 29),
    ],
    # Row 2 – extra items (the actual tails sprites among the labels)
    "extra": [
        (109, 75, 24, 32), (140, 75, 22, 32), (170, 75, 20, 32),
    ],
}

# badniks.png  252x226, bg=(222,222,98) — Sonic 2 Master System enemies
_ENEMY_REGIONS = {
    # Row 0 – flying bug (Buzzer-like)
    "fly_bug": [
        (5, 11, 24, 24), (34, 11, 24, 24), (67, 11, 24, 24),
    ],
    # Row 0 right – crab / crawling
    "crab": [
        (110, 11, 23, 24), (138, 11, 24, 24), (168, 11, 24, 24),
    ],
    # Row 1 – walking enemies
    "walker1": [
        (3, 46, 23, 26), (34, 46, 24, 26), (65, 46, 24, 26),
    ],
    "walker2": [
        (97, 46, 24, 26), (132, 46, 24, 26), (164, 46, 24, 26),
    ],
    # Row 2 – bigger enemies
    "big1": [
        (2, 83, 24, 32), (34, 83, 24, 32), (63, 83, 23, 32),
    ],
    "big2": [
        (90, 83, 23, 32), (128, 83, 24, 32), (160, 83, 24, 32),
    ],
    # Row 3 – small walkers
    "small1": [
        (3, 126, 22, 32), (33, 126, 20, 32),
    ],
    "small2": [
        (72, 126, 16, 32), (96, 126, 16, 32), (121, 126, 16, 32), (141, 126, 16, 32),
    ],
}

# silver-sonic.png  323x480, bg=(0,128,128) — Mecha / boss
_SILVER_SONIC_REGIONS = {
    "walk": [
        (18, 8, 20, 32), (17, 48, 20, 32), (16, 88, 22, 32), (17, 128, 22, 32),
    ],
    "attack": [
        (65, 88, 28, 32), (72, 128, 28, 32),
    ],
    "big": [
        (18, 168, 30, 32), (74, 168, 38, 32),
        (7, 208, 30, 32), (56, 208, 37, 32),
    ],
}

# rings.png  1000x284, bg=(0,128,128) — top-left has small ring rotation
_RING_REGIONS = [
    (2, 35, 15, 15), (22, 35, 15, 15), (42, 35, 15, 15), (63, 35, 13, 15),
    (84, 35, 11, 15), (104, 35, 11, 15), (125, 35, 9, 15), (147, 35, 5, 15),
]


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

def _extract(sheet, x, y, w, h, bg_color, scale):
    """Cut a rect from a sheet, colour-key the background, scale up."""
    if x + w > sheet.get_width() or y + h > sheet.get_height():
        return None
    sub = sheet.subsurface(pygame.Rect(x, y, w, h)).copy()
    sub.set_colorkey(bg_color, pygame.RLEACCEL)
    if scale != 1.0:
        sub = pygame.transform.scale(sub, (int(w * scale), int(h * scale)))
    return sub


def _load_sheet(filename):
    """Load a sprite sheet image and return (surface, bg_color) or None."""
    path = os.path.join(SPRITE_DIR, filename)
    if not os.path.exists(path):
        return None, None
    sheet = pygame.image.load(path).convert()
    bg = sheet.get_at((0, 0))[:3]
    return sheet, bg


# ---------------------------------------------------------------------------
# Animation classes (unchanged API)
# ---------------------------------------------------------------------------

class Animation:
    def __init__(self, frames, frame_duration=100, loop=True):
        self.frames = frames if frames else []
        self.frame_duration = frame_duration
        self.loop = loop
        self.current_frame = 0
        self.timer = 0
        self.finished = False

    def update(self, dt_ms):
        if not self.frames or self.finished:
            return
        self.timer += dt_ms
        if self.timer >= self.frame_duration:
            self.timer -= self.frame_duration
            self.current_frame += 1
            if self.current_frame >= len(self.frames):
                if self.loop:
                    self.current_frame = 0
                else:
                    self.current_frame = len(self.frames) - 1
                    self.finished = True

    def get_frame(self):
        if not self.frames:
            return None
        return self.frames[self.current_frame]

    def reset(self):
        self.current_frame = 0
        self.timer = 0
        self.finished = False


class AnimationSet:
    def __init__(self):
        self.animations = {}
        self.current_name = None
        self.facing_right = True

    def add(self, name, frames, frame_duration=100, loop=True):
        self.animations[name] = Animation(frames, frame_duration, loop)

    def play(self, name):
        if name != self.current_name and name in self.animations:
            self.current_name = name
            self.animations[name].reset()

    def update(self, dt_ms):
        if self.current_name and self.current_name in self.animations:
            self.animations[self.current_name].update(dt_ms)

    def get_frame(self):
        if self.current_name and self.current_name in self.animations:
            frame = self.animations[self.current_name].get_frame()
            if frame and not self.facing_right:
                return pygame.transform.flip(frame, True, False)
            return frame
        return None

    def is_finished(self):
        if self.current_name and self.current_name in self.animations:
            return self.animations[self.current_name].finished
        return True


# ---------------------------------------------------------------------------
# Public loaders
# ---------------------------------------------------------------------------

SONIC_SCALE = 2.5
TAILS_SCALE = 2.5
ENEMY_SCALE = 2.2
RING_SCALE = 2.5
BOSS_SCALE = 2.5


def load_sonic_sprites():
    """Load Sonic from sonic.gif (cleanest sheet)."""
    anims = AnimationSet()
    sheet, bg = _load_sheet("sonic.gif")
    if sheet is None:
        # Fallback: try sonic-2.png
        sheet, bg = _load_sheet("sonic-2.png")
    if sheet is None:
        return _placeholder_anims(anims, (0, 100, 230), "S")

    s = SONIC_SCALE

    def grab_list(regions):
        frames = []
        for (x, y, w, h) in regions:
            f = _extract(sheet, x, y, w, h, bg, s)
            if f:
                frames.append(f)
        return frames

    idle = grab_list(_SONIC_REGIONS["idle"])
    run = grab_list(_SONIC_REGIONS["run"])
    spin = grab_list(_SONIC_REGIONS["spin"])
    jump = grab_list(_SONIC_REGIONS["jump"])
    hurt = grab_list(_SONIC_REGIONS["hurt"])
    crouch = grab_list(_SONIC_REGIONS["crouch"])
    push = grab_list(_SONIC_REGIONS["push"])

    # Ensure at least one frame everywhere
    fb = idle[:1] or [_colored_frame(40, 80, (0, 100, 230), "S")]
    if not idle: idle = fb
    if not run: run = fb
    if not spin: spin = fb
    if not jump: jump = fb
    if not hurt: hurt = fb
    if not crouch: crouch = fb

    anims.add("idle", idle, 200, True)
    anims.add("run", run, 90, True)
    anims.add("jump", jump, 120, False)
    anims.add("fall", jump[-1:], 100, True)
    anims.add("wall_slide", crouch[:1], 100, True)
    anims.add("spin_dash", spin, 50, True)
    anims.add("spin_ball", spin, 40, True)
    anims.add("punch_1", push[:1] or fb, 150, False)
    anims.add("punch_2", push[1:2] or fb, 200, False)
    anims.add("punch_3", push[2:3] or fb, 300, False)
    anims.add("hurt", hurt[:2], 200, False)
    anims.add("death", hurt, 300, False)
    anims.add("door_enter", idle[:1], 150, False)
    anims.add("fly", jump, 60, True)          # not used by Sonic but keeps API uniform
    anims.add("tail_whip", push[:2] or fb, 100, False)

    return anims


def load_tails_sprites():
    """Load Tails from tails.png with exact regions."""
    anims = AnimationSet()
    sheet, bg = _load_sheet("tails.png")
    if sheet is None:
        return _placeholder_anims(anims, (220, 140, 20), "T")

    s = TAILS_SCALE

    def grab_list(regions):
        frames = []
        for (x, y, w, h) in regions:
            f = _extract(sheet, x, y, w, h, bg, s)
            if f:
                frames.append(f)
        return frames

    idle = grab_list(_TAILS_REGIONS["idle"])
    run = grab_list(_TAILS_REGIONS["run"])
    fly = grab_list(_TAILS_REGIONS["fly"])
    extra = grab_list(_TAILS_REGIONS["extra"])

    fb = idle[:1] or [_colored_frame(50, 60, (220, 140, 20), "T")]
    if not idle: idle = fb
    if not run: run = idle
    if not fly: fly = idle
    if not extra: extra = idle

    anims.add("idle", idle, 200, True)
    anims.add("run", run, 90, True)
    anims.add("jump", extra[:2] or idle[:1], 120, False)
    anims.add("fall", extra[1:2] or idle[:1], 100, True)
    anims.add("wall_slide", extra[:1] or idle[:1], 100, True)
    anims.add("spin_dash", run, 50, True)
    anims.add("fly", fly, 60, True)
    anims.add("tail_whip", fly[:3], 80, False)
    anims.add("hurt", idle[:1], 200, False)
    anims.add("death", idle[:1], 300, False)
    anims.add("door_enter", idle[:1], 150, False)
    anims.add("spin_ball", run, 40, True)
    anims.add("punch_1", run[:1], 150, False)
    anims.add("punch_2", run[1:2] or run[:1], 200, False)
    anims.add("punch_3", run[2:3] or run[:1], 300, False)

    return anims


def load_enemy_sprites(enemy_type, world):
    """Load enemy animation frames from badniks.png."""
    sheet, bg = _load_sheet("badniks.png")
    if sheet is None:
        color = {
            1: (180, 140, 40), 2: (40, 150, 40), 3: (150, 200, 255),
            4: (160, 80, 40), 5: (180, 100, 220),
        }.get(world, (200, 40, 40))
        return [_colored_frame(44, 44, color, enemy_type[:3].upper())]

    s = ENEMY_SCALE
    # Pick enemy graphic set based on type
    key_map = {
        "bolt_bug": "walker1", "gear_drone": "fly_bug",
        "vine_creeper": "walker2", "spore_puff": "fly_bug",
        "ice_shard": "small2", "frost_bat": "fly_bug",
        "turret_bot": "big1", "shield_drone": "crab",
        "void_wisp": "fly_bug", "rift_walker": "walker2",
        "mecha_guard": "big2", "bomber_drone": "fly_bug",
    }
    key = key_map.get(enemy_type, "walker1")
    regions = _ENEMY_REGIONS.get(key, _ENEMY_REGIONS["walker1"])

    frames = []
    for (x, y, w, h) in regions:
        f = _extract(sheet, x, y, w, h, bg, s)
        if f:
            frames.append(f)
    if not frames:
        color = (200, 40, 40)
        frames = [_colored_frame(44, 44, color, enemy_type[:3].upper())]
    return frames


def load_boss_sprites(world):
    """Load boss frames from silver-sonic.png (mecha enemy)."""
    sheet, bg = _load_sheet("silver-sonic.png")
    if sheet is None:
        return [_colored_frame(80, 80, (160, 40, 40), "BOSS")]

    s = BOSS_SCALE
    regions = _SILVER_SONIC_REGIONS.get("big", _SILVER_SONIC_REGIONS["walk"])
    frames = []
    for (x, y, w, h) in regions:
        f = _extract(sheet, x, y, w, h, bg, s)
        if f:
            frames.append(f)
    if not frames:
        frames = [_colored_frame(80, 80, (160, 40, 40), "BOSS")]
    return frames


def load_ring_frames():
    """Load ring rotation frames from rings.png."""
    sheet, bg = _load_sheet("rings.png")
    if sheet is None:
        return _fallback_ring_frames()

    frames = []
    for (x, y, w, h) in _RING_REGIONS:
        f = _extract(sheet, x, y, w, h, bg, RING_SCALE)
        if f:
            frames.append(f)
    if not frames:
        return _fallback_ring_frames()
    return frames


def _fallback_ring_frames():
    frames = []
    for i in range(4):
        s = pygame.Surface((24, 24), pygame.SRCALPHA)
        pygame.draw.circle(s, (255, 200, 0), (12, 12), 10, 3)
        frames.append(s)
    return frames


# ---------------------------------------------------------------------------
# Placeholder helpers
# ---------------------------------------------------------------------------

def _colored_frame(w, h, color, label):
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    surf.fill((*color, 200))
    try:
        font = pygame.font.SysFont("monospace", max(10, h // 4))
        text = font.render(label, True, (255, 255, 255))
        surf.blit(text, (4, 4))
    except Exception:
        pass
    return surf


def _placeholder_anims(anims, color, label):
    w, h = 48, 64
    base = _colored_frame(w, h, color, label)
    frames = [base]
    for name in ("idle", "run", "jump", "fall", "wall_slide", "spin_dash",
                 "spin_ball", "punch_1", "punch_2", "punch_3", "hurt",
                 "death", "door_enter", "fly", "tail_whip"):
        anims.add(name, frames, 150, True)
    return anims
