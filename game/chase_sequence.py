"""The 'run from the mega-threat' mechanic for chase levels."""
import pygame
import random
import math
from settings import SCREEN_WIDTH, SCREEN_HEIGHT


class MegaThreat:
    """The Rogue Mech that chases during X-3 levels."""

    def __init__(self, config):
        self.scroll_speed = config.get("scroll_speed_start", 4.0)
        self.max_speed = config.get("scroll_speed_max", 8.0)
        self.acceleration = config.get("acceleration", 0.005)
        self.projectile_interval = config.get("mega_threat_projectile_interval", 3.0)

        self.x = -300  # Off-screen left
        self.y = 0
        self.width = 300
        self.height = 400
        self.active = False
        self.triggered = False

        self.projectile_timer = 0
        self.projectiles = []

        # Visual
        self.eye_glow = 0
        self.shake = 0
        self.piston_offset = 0

    def trigger(self, camera_x, ground_y):
        """Start the chase."""
        self.active = True
        self.triggered = True
        self.x = camera_x - self.width + 20  # start partially visible
        self.y = ground_y - self.height + 40

    def update(self, camera, player_rect, dt_ms):
        if not self.active:
            return

        # Accelerate
        self.scroll_speed = min(self.scroll_speed + self.acceleration, self.max_speed)

        # Stay at left edge of screen, ~25% visible
        target_x = camera.x - self.width * 0.6
        self.x += (target_x - self.x) * 0.08
        # Don't let it go too far off-screen
        min_x = camera.x - self.width + 40
        if self.x < min_x:
            self.x = min_x

        # Visual animation
        self.eye_glow = (self.eye_glow + 0.1) % (math.pi * 2)
        self.piston_offset = math.sin(pygame.time.get_ticks() * 0.01) * 5
        self.shake = random.uniform(-2, 2)

        # Projectiles
        self.projectile_timer += dt_ms / 1000.0
        if self.projectile_timer >= self.projectile_interval:
            self.projectile_timer = 0
            self._fire_projectile(player_rect)

        # Update projectiles
        for p in self.projectiles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["lifetime"] -= 1
        self.projectiles = [p for p in self.projectiles if p["lifetime"] > 0]

    def _fire_projectile(self, player_rect):
        """Fire a projectile toward the player."""
        px = self.x + self.width
        py = self.y + self.height // 3
        dx = player_rect.centerx - px
        dy = player_rect.centery - py
        dist = max(1, math.sqrt(dx * dx + dy * dy))
        speed = 5
        self.projectiles.append({
            "x": px,
            "y": py,
            "vx": (dx / dist) * speed,
            "vy": (dy / dist) * speed,
            "lifetime": 180,
        })

    def get_projectile_rects(self):
        return [pygame.Rect(int(p["x"]), int(p["y"]), 16, 16) for p in self.projectiles]

    def draw(self, surface, cam_offset):
        if not self.active:
            return

        sx = int(self.x - cam_offset[0]) + int(self.shake)
        sy = int(self.y - cam_offset[1])

        # Main body (dark metal)
        body_rect = pygame.Rect(sx, sy, self.width, self.height)
        pygame.draw.rect(surface, (40, 35, 45), body_rect)

        # Armor plates
        for i in range(4):
            plate_y = sy + 40 + i * 80
            pygame.draw.rect(surface, (60, 55, 65),
                             (sx + 20, plate_y, self.width - 40, 60))
            pygame.draw.rect(surface, (80, 75, 85),
                             (sx + 20, plate_y, self.width - 40, 60), 2)

        # Head section
        head_y = sy + 30
        pygame.draw.rect(surface, (50, 45, 55), (sx + 80, head_y, 140, 80))

        # Eyes (glowing red)
        glow = int(180 + 75 * math.sin(self.eye_glow))
        eye_y = head_y + 30
        pygame.draw.circle(surface, (glow, 0, 0), (sx + 130, eye_y), 15)
        pygame.draw.circle(surface, (glow, 0, 0), (sx + 190, eye_y), 15)
        pygame.draw.circle(surface, (255, 200, 200), (sx + 130, eye_y), 6)
        pygame.draw.circle(surface, (255, 200, 200), (sx + 190, eye_y), 6)

        # Pistons
        piston_y = sy + 200 + int(self.piston_offset)
        pygame.draw.rect(surface, (100, 95, 105), (sx + 40, piston_y, 30, 120))
        pygame.draw.rect(surface, (100, 95, 105), (sx + self.width - 70, piston_y, 30, 120))

        # Arm reaching forward
        arm_x = sx + self.width - 20
        arm_y = sy + 150
        pygame.draw.rect(surface, (70, 65, 75), (arm_x, arm_y, 40, 25))
        pygame.draw.rect(surface, (70, 65, 75), (arm_x + 30, arm_y - 10, 20, 45))

        # Sparks
        if random.random() < 0.3:
            spark_x = sx + random.randint(0, self.width)
            spark_y = sy + random.randint(0, self.height)
            pygame.draw.circle(surface, (255, 200, 50), (spark_x, spark_y), 3)

        # Projectiles
        for p in self.projectiles:
            px = int(p["x"] - cam_offset[0])
            py_draw = int(p["y"] - cam_offset[1])
            pygame.draw.circle(surface, (255, 50, 30), (px, py_draw), 8)
            pygame.draw.circle(surface, (255, 200, 100), (px, py_draw), 4)


class ChaseManager:
    """Manages the chase sequence within a level."""

    def __init__(self, chase_config):
        self.config = chase_config
        # Trigger almost immediately
        self.trigger_x = 4 * 48
        self.mega_threat = MegaThreat(chase_config)
        self.active = False
        self.started = False

    def update(self, camera, player, dt_ms):
        if not self.config:
            return

        # Check if player reached trigger point
        if not self.started and player.rect.x >= self.trigger_x:
            self.started = True
            self.active = True
            ground_y = player.rect.bottom
            self.mega_threat.trigger(camera.x, ground_y - 100)
            camera.start_auto_scroll(self.config["scroll_speed_start"])

        if self.active:
            self.mega_threat.update(camera, player.rect, dt_ms)

            # Increase camera scroll speed
            new_speed = min(
                camera.auto_scroll_speed + self.config.get("acceleration", 0.005),
                self.config["scroll_speed_max"]
            )
            camera.auto_scroll_speed = new_speed

            # Check if player is behind the mega threat (death)
            if player.rect.right < self.mega_threat.x + self.mega_threat.width - 50:
                player.take_damage(99)

            # Check projectile collisions
            for proj_rect in self.mega_threat.get_projectile_rects():
                if player.rect.colliderect(proj_rect):
                    player.take_damage(1)

    def draw(self, surface, cam_offset):
        if self.active:
            self.mega_threat.draw(surface, cam_offset)

    def stop(self):
        self.active = False
        self.mega_threat.active = False
