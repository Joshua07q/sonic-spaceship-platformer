"""Collectible entities: rings, power-ups, checkpoints, exit doors."""
import pygame
import math
from engine.animation import load_ring_frames


class Ring:
    """A collectible ring that bobs in place."""

    _shared_frames = None

    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.base_y = y
        self.rect = pygame.Rect(x, y, 20, 20)
        self.collected = False
        self.bob_offset = x * 0.1  # Phase offset based on position
        self.bob_timer = self.bob_offset

        if Ring._shared_frames is None:
            Ring._shared_frames = load_ring_frames()
        self.frames = Ring._shared_frames
        self.frame_timer = 0
        self.frame_index = 0

    def update(self, dt_ms):
        if self.collected:
            return
        self.bob_timer += 0.05
        self.y = self.base_y + math.sin(self.bob_timer) * 4
        self.rect.topleft = (int(self.x), int(self.y))

        self.frame_timer += dt_ms
        if self.frame_timer > 80:
            self.frame_timer = 0
            self.frame_index = (self.frame_index + 1) % max(1, len(self.frames))

    def draw(self, surface, cam_offset):
        if self.collected:
            return
        sx = int(self.x - cam_offset[0])
        sy = int(self.y - cam_offset[1])
        if self.frames:
            frame = self.frames[self.frame_index % len(self.frames)]
            fw, fh = frame.get_size()
            surface.blit(frame, (sx + (20 - fw) // 2, sy + (20 - fh) // 2))
        else:
            pygame.draw.circle(surface, (255, 200, 0), (sx + 10, sy + 10), 9, 2)


class ScatteredRing(Ring):
    """A ring that was scattered from the player on hit. Has physics and fades."""

    def __init__(self, x, y, vx, vy):
        super().__init__(x, y)
        self.vx = vx
        self.vy = vy
        self.lifetime = 180  # 3 seconds at 60fps
        self.bounced = False
        self.collectable_delay = 15  # Brief delay before can be recollected

    def update(self, dt_ms):
        if self.collected:
            return
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.collected = True
            return

        if self.collectable_delay > 0:
            self.collectable_delay -= 1

        self.vy += 0.3
        self.x += self.vx
        self.y += self.vy

        # Bounce once
        if self.vy > 0 and not self.bounced and self.y > self.base_y + 50:
            self.vy = -self.vy * 0.5
            self.vx *= 0.7
            self.bounced = True

        self.rect.topleft = (int(self.x), int(self.y))
        self.frame_timer += dt_ms
        if self.frame_timer > 60:
            self.frame_timer = 0
            self.frame_index = (self.frame_index + 1) % max(1, len(self.frames))

    def draw(self, surface, cam_offset):
        if self.collected or self.lifetime <= 0:
            return
        alpha = min(255, int(255 * (self.lifetime / 60)))
        sx = int(self.x - cam_offset[0])
        sy = int(self.y - cam_offset[1])
        s = pygame.Surface((20, 20), pygame.SRCALPHA)
        pygame.draw.circle(s, (255, 200, 0, alpha), (10, 10), 9, 2)
        surface.blit(s, (sx, sy))

    def can_collect(self):
        return self.collectable_delay <= 0 and not self.collected


class Checkpoint:
    """Mid-level checkpoint lamppost."""

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.rect = pygame.Rect(x, y - 48, 16, 64)
        self.activated = False

    def activate(self):
        self.activated = True

    def draw(self, surface, cam_offset):
        sx = int(self.x - cam_offset[0])
        sy = int(self.y - 48 - cam_offset[1])

        # Post
        pygame.draw.rect(surface, (120, 120, 130), (sx + 5, sy, 6, 64))

        # Lamp
        if self.activated:
            pygame.draw.circle(surface, (0, 255, 100), (sx + 8, sy + 8), 10)
            # Glow
            gs = pygame.Surface((30, 30), pygame.SRCALPHA)
            pygame.draw.circle(gs, (0, 255, 100, 50), (15, 15), 15)
            surface.blit(gs, (sx - 7, sy - 7))
        else:
            pygame.draw.circle(surface, (100, 100, 110), (sx + 8, sy + 8), 10)


DOOR_WIDTH = 64
DOOR_HEIGHT = 96


class ExitDoor:
    """Level exit blast door — wide trigger zone."""

    def __init__(self, x, y):
        self.x = x
        self.y = y - DOOR_HEIGHT
        # Collision rect is wider than visual for reliable triggering
        self.rect = pygame.Rect(x - 16, y - DOOR_HEIGHT - 20, DOOR_WIDTH + 32, DOOR_HEIGHT + 40)
        self.open = False
        self.open_progress = 0  # 0 to 1
        self.glow_timer = 0

    def update(self, dt_ms):
        self.glow_timer += 0.05
        if self.open and self.open_progress < 1:
            self.open_progress = min(1.0, self.open_progress + 0.03)

    def draw(self, surface, cam_offset):
        sx = int(self.x - cam_offset[0])
        sy = int(self.y - cam_offset[1])

        # Door frame
        pygame.draw.rect(surface, (80, 80, 90), (sx - 4, sy - 4, DOOR_WIDTH + 8, DOOR_HEIGHT + 8))

        if not self.open:
            # Closed door
            pygame.draw.rect(surface, (60, 65, 75), (sx, sy, DOOR_WIDTH, DOOR_HEIGHT))
            # Center line
            pygame.draw.line(surface, (40, 45, 55),
                             (sx + DOOR_WIDTH // 2, sy),
                             (sx + DOOR_WIDTH // 2, sy + DOOR_HEIGHT), 2)
            # Glowing panel
            glow = int(128 + 127 * math.sin(self.glow_timer))
            pygame.draw.rect(surface, (0, glow, glow),
                             (sx + DOOR_WIDTH // 2 - 8, sy + DOOR_HEIGHT // 2 - 8, 16, 16))
        else:
            # Opening animation
            gap = int(DOOR_WIDTH * self.open_progress * 0.5)
            left_w = DOOR_WIDTH // 2 - gap
            right_x = sx + DOOR_WIDTH // 2 + gap
            right_w = DOOR_WIDTH // 2 - gap
            if left_w > 0:
                pygame.draw.rect(surface, (60, 65, 75), (sx, sy, left_w, DOOR_HEIGHT))
            if right_w > 0:
                pygame.draw.rect(surface, (60, 65, 75), (right_x, sy, right_w, DOOR_HEIGHT))
            # Light behind door
            light_s = pygame.Surface((DOOR_WIDTH, DOOR_HEIGHT), pygame.SRCALPHA)
            light_s.fill((255, 255, 200, int(150 * self.open_progress)))
            surface.blit(light_s, (sx, sy))


class SteamVent:
    """Boost pad that launches player upward."""

    def __init__(self, x, y, boost_force=-15, interval=2.0):
        self.x = x
        self.y = y
        self.rect = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE // 2)
        self.boost_force = boost_force
        self.interval = interval
        self.timer = 0
        self.active = False
        self.active_timer = 0

    def update(self, dt_ms):
        self.timer += dt_ms / 1000.0
        if self.timer >= self.interval:
            self.timer = 0
            self.active = True
            self.active_timer = 30

        if self.active:
            self.active_timer -= 1
            if self.active_timer <= 0:
                self.active = False

    def draw(self, surface, cam_offset):
        sx = int(self.x - cam_offset[0])
        sy = int(self.y - cam_offset[1])
        pygame.draw.rect(surface, (100, 100, 110), (sx, sy, TILE_SIZE, TILE_SIZE // 2))
        if self.active:
            # Steam effect
            for i in range(3):
                steam_y = sy - 10 - i * 12
                alpha = 150 - i * 40
                ss = pygame.Surface((TILE_SIZE - 8, 10), pygame.SRCALPHA)
                ss.fill((200, 200, 220, max(0, alpha)))
                surface.blit(ss, (sx + 4, steam_y))


class MovingPlatform:
    """A platform that moves along a path."""

    def __init__(self, x, y, width, path, speed=1.5):
        self.width = width * TILE_SIZE
        self.height = TILE_SIZE // 3
        self.path = path  # List of (x, y) waypoints in tiles
        self.speed = speed
        self.path_index = 0
        self.x = float(x * TILE_SIZE)
        self.y = float(y * TILE_SIZE)
        self.rect = pygame.Rect(int(self.x), int(self.y), self.width, self.height)
        self.dx = 0
        self.dy = 0

    def update(self, dt_ms):
        if not self.path or len(self.path) < 2:
            return

        target = self.path[self.path_index]
        tx = target["x"] * TILE_SIZE if isinstance(target, dict) else target[0] * TILE_SIZE
        ty = target["y"] * TILE_SIZE if isinstance(target, dict) else target[1] * TILE_SIZE

        ddx = tx - self.x
        ddy = ty - self.y
        dist = max(1, (ddx**2 + ddy**2)**0.5)

        if dist < self.speed * 2:
            self.path_index = (self.path_index + 1) % len(self.path)
        else:
            old_x, old_y = self.x, self.y
            self.x += (ddx / dist) * self.speed
            self.y += (ddy / dist) * self.speed
            self.dx = self.x - old_x
            self.dy = self.y - old_y

        self.rect.topleft = (int(self.x), int(self.y))

    def draw(self, surface, cam_offset):
        sx = int(self.x - cam_offset[0])
        sy = int(self.y - cam_offset[1])
        pygame.draw.rect(surface, (130, 130, 145), (sx, sy, self.width, self.height))
        pygame.draw.rect(surface, (180, 180, 195), (sx, sy, self.width, 3))


from settings import TILE_SIZE
