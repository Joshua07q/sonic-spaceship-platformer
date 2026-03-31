"""Enemy entities with patrol/chase AI, per-world themed."""
import pygame
import math
import random
from settings import TILE_SIZE, SMALL_ENEMY_HP, MEDIUM_ENEMY_HP, GRAVITY, WORLD_THEMES
from engine.animation import load_enemy_sprites


class Enemy:
    """Base enemy class."""

    def __init__(self, x, y, enemy_type, hp=SMALL_ENEMY_HP, width=36, height=36):
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.width = width
        self.height = height
        self.rect = pygame.Rect(x, y, width, height)
        self.enemy_type = enemy_type
        self.hp = hp
        self.max_hp = hp
        self.alive = True
        self.active = True
        self.facing_right = True
        self.speed = 1.5
        self.damage = 1
        self.death_timer = 0
        self.hit_flash = 0
        self.color = (200, 40, 40)
        self.label = enemy_type[:3].upper()
        self.spawn_x = x
        self.spawn_y = y
        self.patrol_range = 4 * TILE_SIZE
        self.gravity = True
        self.on_ground = False
        # Sprite frames
        self._sprite_frames = None
        self._frame_index = 0
        self._frame_timer = 0
        self._world = 1

    def take_damage(self, dmg, knockback_dir=0):
        if not self.alive:
            return False
        self.hp -= dmg
        self.hit_flash = 8
        self.vx = knockback_dir * 4
        if self.hp <= 0:
            self.alive = False
            self.death_timer = 30
            return True
        return False

    def update(self, solid_rects, player_rect, dt_ms):
        if not self.alive:
            self.death_timer -= 1
            if self.death_timer <= 0:
                self.active = False
            return

        if self.hit_flash > 0:
            self.hit_flash -= 1

        self._ai_update(player_rect, dt_ms)

        # Apply gravity
        if self.gravity:
            self.vy += GRAVITY * 0.7
            if self.vy > 10:
                self.vy = 10

        # Move
        self.x += self.vx
        self.rect.x = int(self.x)
        for solid in solid_rects:
            if self.rect.colliderect(solid):
                if self.vx > 0:
                    self.rect.right = solid.left
                    self.vx = -self.speed
                    self.facing_right = False
                elif self.vx < 0:
                    self.rect.left = solid.right
                    self.vx = self.speed
                    self.facing_right = True
                self.x = float(self.rect.x)

        self.y += self.vy
        self.rect.y = int(self.y)
        self.on_ground = False
        for solid in solid_rects:
            if self.rect.colliderect(solid):
                if self.vy > 0:
                    self.rect.bottom = solid.top
                    self.on_ground = True
                elif self.vy < 0:
                    self.rect.top = solid.bottom
                self.vy = 0
                self.y = float(self.rect.y)

        # Don't walk off edges - check if there's ground ahead
        if self.on_ground and self.gravity:
            check_x = self.rect.right + 4 if self.vx > 0 else self.rect.left - 4
            check_rect = pygame.Rect(check_x, self.rect.bottom + 2, 4, 4)
            has_ground = False
            for solid in solid_rects:
                if check_rect.colliderect(solid):
                    has_ground = True
                    break
            if not has_ground:
                self.vx = -self.vx
                self.facing_right = not self.facing_right

    def _ai_update(self, player_rect, dt_ms):
        # Default: patrol back and forth
        if abs(self.x - self.spawn_x) > self.patrol_range:
            if self.x > self.spawn_x:
                self.vx = -self.speed
                self.facing_right = False
            else:
                self.vx = self.speed
                self.facing_right = True
        elif self.vx == 0:
            self.vx = self.speed

    def _load_sprites(self, world=1):
        if self._sprite_frames is None:
            self._sprite_frames = load_enemy_sprites(self.enemy_type, world)
            self._world = world

    def draw(self, surface, cam_offset):
        if not self.active:
            return

        sx = int(self.x - cam_offset[0])
        sy = int(self.y - cam_offset[1])

        if not self.alive:
            alpha = int(255 * (self.death_timer / 30))
            s = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            s.fill((*self.color[:3], alpha))
            surface.blit(s, (sx, sy))
            return

        # Load sprites lazily
        self._load_sprites(self._world)

        # Animate
        self._frame_timer += 1
        if self._frame_timer > 10:
            self._frame_timer = 0
            self._frame_index = (self._frame_index + 1) % len(self._sprite_frames)

        frame = self._sprite_frames[self._frame_index]
        if not self.facing_right:
            frame = pygame.transform.flip(frame, True, False)

        # Hit flash: tint white
        if self.hit_flash > 0:
            flash = frame.copy()
            flash.fill((255, 255, 255, 120), special_flags=pygame.BLEND_RGBA_ADD)
            frame = flash

        # Center sprite on hitbox
        fw, fh = frame.get_size()
        draw_x = sx + (self.width - fw) // 2
        draw_y = sy + (self.height - fh)
        surface.blit(frame, (draw_x, draw_y))

        # HP bar if damaged
        if self.hp < self.max_hp:
            bar_w = self.width
            bar_h = 4
            fill = int(bar_w * self.hp / self.max_hp)
            pygame.draw.rect(surface, (60, 60, 60), (sx, sy - 8, bar_w, bar_h))
            pygame.draw.rect(surface, (0, 220, 0), (sx, sy - 8, fill, bar_h))


# --- World 1: Engine Deck enemies ---

class BoltBug(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, "bolt_bug", SMALL_ENEMY_HP, 30, 24)
        self.speed = 1.2
        self.vx = self.speed
        self.color = (180, 140, 40)
        self.label = "BLT"


class GearDrone(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, "gear_drone", SMALL_ENEMY_HP, 32, 28)
        self.speed = 1.5
        self.vx = self.speed
        self.color = (100, 100, 160)
        self.label = "GDR"
        self.gravity = False
        self.base_y = y
        self.sine_timer = random.uniform(0, math.pi * 2)

    def _ai_update(self, player_rect, dt_ms):
        super()._ai_update(player_rect, dt_ms)
        self.sine_timer += 0.05
        self.y = self.base_y + math.sin(self.sine_timer) * 30
        self.rect.y = int(self.y)


# --- World 2: Bio-Dome enemies ---

class VineCreeper(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, "vine_creeper", SMALL_ENEMY_HP, 28, 32)
        self.speed = 0.5
        self.color = (40, 150, 40)
        self.label = "VCR"
        self.lunge_cooldown = 0
        self.lunging = False

    def _ai_update(self, player_rect, dt_ms):
        dist = math.sqrt((player_rect.centerx - self.rect.centerx)**2 +
                         (player_rect.centery - self.rect.centery)**2)
        if dist < 120 and self.lunge_cooldown <= 0 and not self.lunging:
            self.lunging = True
            dx = player_rect.centerx - self.rect.centerx
            self.vx = 6 if dx > 0 else -6
            self.vy = -5
            self.lunge_cooldown = 90
            self.facing_right = dx > 0
        elif not self.lunging:
            self.vx = 0
        if self.on_ground and self.lunging:
            self.lunging = False
            self.vx = 0
        if self.lunge_cooldown > 0:
            self.lunge_cooldown -= 1


class SporePuff(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, "spore_puff", 1, 26, 26)
        self.speed = 0.8
        self.color = (150, 80, 180)
        self.label = "SPR"
        self.gravity = False
        self.base_y = y
        self.float_timer = random.uniform(0, math.pi * 2)

    def _ai_update(self, player_rect, dt_ms):
        self.float_timer += 0.03
        self.y = self.base_y + math.sin(self.float_timer) * 20
        self.rect.y = int(self.y)
        # Drift toward player slowly
        dx = player_rect.centerx - self.rect.centerx
        if abs(dx) < 200:
            self.vx = 0.3 if dx > 0 else -0.3
            self.facing_right = dx > 0
        else:
            self.vx = 0


# --- World 3: Cryo Deck enemies ---

class IceShard(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, "ice_shard", SMALL_ENEMY_HP, 24, 28)
        self.speed = 3.0
        self.color = (150, 200, 255)
        self.label = "ICE"

    def _ai_update(self, player_rect, dt_ms):
        dx = player_rect.centerx - self.rect.centerx
        if abs(dx) < 300:
            self.vx = self.speed if dx > 0 else -self.speed
            self.facing_right = dx > 0
        else:
            super()._ai_update(player_rect, dt_ms)


class FrostBat(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, "frost_bat", SMALL_ENEMY_HP, 30, 24)
        self.speed = 0
        self.color = (80, 80, 160)
        self.label = "BAT"
        self.gravity = False
        self.hanging = True
        self.drop_speed = 4

    def _ai_update(self, player_rect, dt_ms):
        if self.hanging:
            dx = abs(player_rect.centerx - self.rect.centerx)
            if dx < 60 and player_rect.centery > self.rect.centery:
                self.hanging = False
                self.gravity = True
                self.vy = self.drop_speed
        elif self.on_ground:
            # Fly back up
            self.gravity = False
            self.vy = -2
            if self.rect.y <= self.spawn_y:
                self.y = self.spawn_y
                self.rect.y = int(self.y)
                self.vy = 0
                self.hanging = True


# --- World 4: Weapons Bay enemies ---

class TurretBot(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, "turret_bot", SMALL_ENEMY_HP + 1, 32, 32)
        self.speed = 0
        self.color = (160, 80, 40)
        self.label = "TRT"
        self.fire_timer = 0
        self.fire_interval = 90
        self.bullets = []

    def _ai_update(self, player_rect, dt_ms):
        self.vx = 0
        self.fire_timer += 1
        dx = player_rect.centerx - self.rect.centerx
        self.facing_right = dx > 0

        if self.fire_timer >= self.fire_interval:
            self.fire_timer = 0
            bvx = 4 if self.facing_right else -4
            self.bullets.append({
                "rect": pygame.Rect(self.rect.centerx, self.rect.centery - 4, 8, 8),
                "vx": bvx,
                "lifetime": 120,
            })

        # Update bullets
        for b in self.bullets:
            b["rect"].x += b["vx"]
            b["lifetime"] -= 1
        self.bullets = [b for b in self.bullets if b["lifetime"] > 0]

    def draw(self, surface, cam_offset):
        super().draw(surface, cam_offset)
        for b in self.bullets:
            bx = b["rect"].x - cam_offset[0]
            by = b["rect"].y - cam_offset[1]
            pygame.draw.rect(surface, (255, 200, 50), (bx, by, 8, 8))


class ShieldDrone(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, "shield_drone", SMALL_ENEMY_HP + 1, 32, 32)
        self.speed = 1.5
        self.vx = self.speed
        self.color = (100, 140, 180)
        self.label = "SHD"
        self.gravity = False
        self.base_y = y
        self.sine_timer = random.uniform(0, math.pi * 2)
        self.shield_front = True

    def _ai_update(self, player_rect, dt_ms):
        self.sine_timer += 0.04
        self.y = self.base_y + math.sin(self.sine_timer) * 25
        self.rect.y = int(self.y)
        dx = player_rect.centerx - self.rect.centerx
        self.facing_right = dx > 0
        # Move toward player
        if abs(dx) < 300:
            self.vx = self.speed if dx > 0 else -self.speed

    def take_damage(self, dmg, knockback_dir=0):
        # Only take damage from behind
        from_front = (knockback_dir > 0 and not self.facing_right) or \
                     (knockback_dir < 0 and self.facing_right)
        if from_front:
            return False  # Blocked!
        return super().take_damage(dmg, knockback_dir)


# --- World 5: Dimension Rift enemies ---

class VoidWisp(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, "void_wisp", SMALL_ENEMY_HP, 24, 24)
        self.speed = 0
        self.color = (180, 100, 220)
        self.label = "WSP"
        self.gravity = False
        self.teleport_timer = 0
        self.orb_timer = 0
        self.orbs = []

    def _ai_update(self, player_rect, dt_ms):
        self.teleport_timer += 1
        self.orb_timer += 1

        if self.teleport_timer >= 120:
            self.teleport_timer = 0
            self.x = self.spawn_x + random.randint(-80, 80)
            self.y = self.spawn_y + random.randint(-60, 60)
            self.rect.topleft = (int(self.x), int(self.y))

        if self.orb_timer >= 90:
            self.orb_timer = 0
            dx = player_rect.centerx - self.rect.centerx
            dy = player_rect.centery - self.rect.centery
            dist = max(1, math.sqrt(dx*dx + dy*dy))
            self.orbs.append({
                "rect": pygame.Rect(self.rect.centerx, self.rect.centery, 10, 10),
                "vx": (dx / dist) * 3,
                "vy": (dy / dist) * 3,
                "lifetime": 90,
            })

        for o in self.orbs:
            o["rect"].x += o["vx"]
            o["rect"].y += o["vy"]
            o["lifetime"] -= 1
        self.orbs = [o for o in self.orbs if o["lifetime"] > 0]

    def draw(self, surface, cam_offset):
        super().draw(surface, cam_offset)
        for o in self.orbs:
            ox = int(o["rect"].x - cam_offset[0])
            oy = int(o["rect"].y - cam_offset[1])
            pygame.draw.circle(surface, (200, 120, 255), (ox, oy), 5)


class RiftWalker(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, "rift_walker", SMALL_ENEMY_HP, 30, 30)
        self.speed = 1.8
        self.vx = self.speed
        self.color = (120, 60, 180)
        self.label = "RFT"


# --- Medium enemies ---

class MechaGuard(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, "mecha_guard", MEDIUM_ENEMY_HP, 40, 48)
        self.speed = 2.0
        self.color = (140, 60, 60)
        self.label = "MCH"
        self.damage = 2
        self.charge_cooldown = 0
        self.blocking = False
        self.block_timer = 0
        self.stagger = 0

    def _ai_update(self, player_rect, dt_ms):
        self.charge_cooldown = max(0, self.charge_cooldown - 1)
        if self.stagger > 0:
            self.stagger -= 1
            self.vx = 0
            return

        dx = player_rect.centerx - self.rect.centerx
        dist = abs(dx)
        self.facing_right = dx > 0

        if dist < 200 and self.charge_cooldown <= 0:
            # Charge at player
            self.vx = (5 if dx > 0 else -5)
            self.charge_cooldown = 120
        elif dist < 80:
            # Block occasionally
            if random.random() < 0.01:
                self.blocking = True
                self.block_timer = 45
            if self.block_timer > 0:
                self.block_timer -= 1
                self.vx = 0
            else:
                self.blocking = False
                self.vx = (self.speed if dx > 0 else -self.speed) * 0.5
        else:
            super()._ai_update(player_rect, dt_ms)

    def take_damage(self, dmg, knockback_dir=0):
        if self.blocking:
            return False
        result = super().take_damage(dmg, knockback_dir)
        self.stagger = 15
        return result


class BomberDrone(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, "bomber_drone", MEDIUM_ENEMY_HP, 36, 30)
        self.speed = 1.5
        self.vx = self.speed
        self.color = (160, 100, 40)
        self.label = "BMB"
        self.gravity = False
        self.bomb_timer = 0
        self.bombs = []

    def _ai_update(self, player_rect, dt_ms):
        # Fly overhead
        dx = player_rect.centerx - self.rect.centerx
        if abs(dx) > 20:
            self.vx = self.speed if dx > 0 else -self.speed
        else:
            self.vx = 0
        self.facing_right = dx > 0

        # Drop bombs
        self.bomb_timer += 1
        if self.bomb_timer >= 100 and abs(dx) < 80:
            self.bomb_timer = 0
            self.bombs.append({
                "rect": pygame.Rect(self.rect.centerx - 6, self.rect.bottom, 12, 12),
                "vy": 0,
                "lifetime": 120,
            })

        for b in self.bombs:
            b["vy"] += 0.3
            b["rect"].y += b["vy"]
            b["lifetime"] -= 1
        self.bombs = [b for b in self.bombs if b["lifetime"] > 0]

    def draw(self, surface, cam_offset):
        super().draw(surface, cam_offset)
        for b in self.bombs:
            bx = int(b["rect"].x - cam_offset[0])
            by = int(b["rect"].y - cam_offset[1])
            pygame.draw.circle(surface, (60, 60, 60), (bx + 6, by + 6), 6)
            pygame.draw.circle(surface, (255, 100, 30), (bx + 6, by + 2), 3)


# Enemy type registry
ENEMY_TYPES = {
    "bolt_bug": BoltBug,
    "gear_drone": GearDrone,
    "vine_creeper": VineCreeper,
    "spore_puff": SporePuff,
    "ice_shard": IceShard,
    "frost_bat": FrostBat,
    "turret_bot": TurretBot,
    "shield_drone": ShieldDrone,
    "void_wisp": VoidWisp,
    "rift_walker": RiftWalker,
    "mecha_guard": MechaGuard,
    "bomber_drone": BomberDrone,
}

WORLD_ENEMIES = {
    1: ["bolt_bug", "gear_drone"],
    2: ["vine_creeper", "spore_puff"],
    3: ["ice_shard", "frost_bat"],
    4: ["turret_bot", "shield_drone"],
    5: ["void_wisp", "rift_walker"],
}

MEDIUM_ENEMIES = ["mecha_guard", "bomber_drone"]


def create_enemy(enemy_type, x, y):
    cls = ENEMY_TYPES.get(enemy_type)
    if cls:
        return cls(x, y)
    return Enemy(x, y, enemy_type)
