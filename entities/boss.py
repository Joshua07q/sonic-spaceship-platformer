"""Boss entities with state machines. One boss per world."""
import pygame
import math
import random
from settings import TILE_SIZE, BOSS_NAMES, DIFFICULTY
from engine.animation import load_boss_sprites


class Boss:
    """Base boss class with phase-based state machine."""

    def __init__(self, x, y, world_num):
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.world = world_num
        self.width = 80
        self.height = 96
        self.rect = pygame.Rect(x, y, self.width, self.height)
        self.hp = DIFFICULTY[world_num]["boss_hp"]
        self.max_hp = self.hp
        self.alive = True
        self.active = True
        self.phase = 1
        self.state = "idle"
        self.state_timer = 0
        self.hit_flash = 0
        self.vulnerable = False
        self.name = BOSS_NAMES.get(world_num, "BOSS")
        self.color = (180, 40, 40)
        self.facing_right = False
        self.attack_rects = []
        self.projectiles = []
        self.death_timer = 0
        self.defeated = False
        self.intro_timer = 120
        # Sprites
        self._sprite_frames = load_boss_sprites(world_num)
        self._frame_index = 0
        self._frame_timer = 0

    def take_damage(self, dmg):
        if not self.vulnerable or not self.alive:
            return False
        self.hp -= dmg
        self.hit_flash = 10
        if self.hp <= 0:
            self.alive = False
            self.death_timer = 150
            return True
        # Phase transitions
        if self.hp <= self.max_hp * 0.66 and self.phase == 1:
            self.phase = 2
            self._on_phase_change()
        elif self.hp <= self.max_hp * 0.33 and self.phase == 2:
            self.phase = 3
            self._on_phase_change()
        return False

    def _on_phase_change(self):
        self.state = "phase_transition"
        self.state_timer = 60

    def update(self, player_rect, solid_rects, dt_ms):
        if self.intro_timer > 0:
            self.intro_timer -= 1
            return

        if not self.alive:
            self.death_timer -= 1
            if self.death_timer <= 0:
                self.defeated = True
            return

        if self.hit_flash > 0:
            self.hit_flash -= 1

        self.state_timer -= 1
        self._ai_update(player_rect, dt_ms)

        # Apply velocity
        self.x += self.vx
        self.y += self.vy
        self.rect.topleft = (int(self.x), int(self.y))

        # Update projectiles
        for p in self.projectiles:
            p["rect"].x += p["vx"]
            p["rect"].y += p["vy"]
            if "gravity" in p:
                p["vy"] += p["gravity"]
            p["lifetime"] -= 1
        self.projectiles = [p for p in self.projectiles if p["lifetime"] > 0]

    def _ai_update(self, player_rect, dt_ms):
        pass  # Override in subclasses

    def draw(self, surface, cam_offset):
        if not self.active:
            return

        sx = int(self.x - cam_offset[0])
        sy = int(self.y - cam_offset[1])

        if not self.alive:
            alpha = int(255 * max(0, self.death_timer / 150))
            s = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            s.fill((*self.color[:3], alpha))
            surface.blit(s, (sx, sy))
            return

        # Animate sprite
        self._frame_timer += 1
        if self._frame_timer > 12:
            self._frame_timer = 0
            self._frame_index = (self._frame_index + 1) % len(self._sprite_frames)

        frame = self._sprite_frames[self._frame_index]
        if not self.facing_right:
            frame = pygame.transform.flip(frame, True, False)

        # Hit flash
        if self.hit_flash > 0:
            flash = frame.copy()
            flash.fill((255, 255, 255, 120), special_flags=pygame.BLEND_RGBA_ADD)
            frame = flash

        # Draw sprite centered on hitbox
        fw, fh = frame.get_size()
        draw_x = sx + (self.width - fw) // 2
        draw_y = sy + (self.height - fh)
        surface.blit(frame, (draw_x, draw_y))

        # Vulnerability glow
        if self.vulnerable:
            glow = pygame.Surface((self.width + 10, self.height + 10), pygame.SRCALPHA)
            pulse = int(80 + 60 * math.sin(pygame.time.get_ticks() * 0.01))
            glow.fill((255, 255, 0, pulse))
            surface.blit(glow, (sx - 5, sy - 5))

        # HP bar
        bar_w = 120
        bar_h = 8
        bar_x = sx + (self.width - bar_w) // 2
        bar_y = sy - 28
        fill = int(bar_w * self.hp / self.max_hp)
        pygame.draw.rect(surface, (60, 60, 60), (bar_x, bar_y, bar_w, bar_h))
        pygame.draw.rect(surface, (220, 30, 30), (bar_x, bar_y, fill, bar_h))
        pygame.draw.rect(surface, (255, 255, 255), (bar_x, bar_y, bar_w, bar_h), 1)

        # Name
        try:
            font = pygame.font.SysFont("monospace", 12)
            text = font.render(self.name, True, (255, 255, 255))
            surface.blit(text, (sx + (self.width - text.get_width()) // 2, bar_y - 16))
        except Exception:
            pass

        # Projectiles
        for p in self.projectiles:
            px = int(p["rect"].x - cam_offset[0])
            py_d = int(p["rect"].y - cam_offset[1])
            color = p.get("color", (255, 100, 50))
            pygame.draw.circle(surface, color, (px + 6, py_d), 6)


class PistonPrime(Boss):
    """World 1 boss: Hydraulic arm that slams down."""

    def __init__(self, x, y):
        super().__init__(x, y, 1)
        self.color = (140, 130, 120)
        self.slam_x = 0
        self.original_y = y
        self.speed_mult = 1.0

    def _ai_update(self, player_rect, dt_ms):
        self.facing_right = player_rect.centerx > self.rect.centerx
        speed_mult = 1.0 + (self.phase - 1) * 0.4

        if self.state == "phase_transition":
            if self.state_timer <= 0:
                self.state = "idle"
                self.state_timer = 30
            return

        if self.state == "idle":
            self.vulnerable = False
            self.vx = 0
            self.vy = 0
            if self.state_timer <= 0:
                self.state = "tracking"
                self.state_timer = int(60 / speed_mult)

        elif self.state == "tracking":
            self.vulnerable = False
            dx = player_rect.centerx - self.rect.centerx
            self.vx = (3 * speed_mult) if dx > 0 else (-3 * speed_mult)
            if self.state_timer <= 0:
                self.state = "slam_up"
                self.state_timer = 20
                self.vx = 0

        elif self.state == "slam_up":
            self.vy = -4
            if self.state_timer <= 0:
                self.state = "slam_down"
                self.state_timer = 15
                self.vy = 0

        elif self.state == "slam_down":
            self.vy = 12 * speed_mult
            if self.y >= self.original_y:
                self.y = self.original_y
                self.vy = 0
                self.state = "stunned"
                self.state_timer = int(90 / speed_mult)
                self.attack_rects = [pygame.Rect(
                    self.rect.x - 30, self.rect.bottom - 20,
                    self.width + 60, 20
                )]

        elif self.state == "stunned":
            self.vulnerable = True
            self.vx = 0
            self.vy = 0
            if self.state_timer <= 0:
                self.vulnerable = False
                self.attack_rects = []
                self.state = "idle"
                self.state_timer = int(40 / speed_mult)


class QueenSporax(Boss):
    """World 2 boss: Giant spore plant."""

    def __init__(self, x, y):
        super().__init__(x, y, 2)
        self.color = (60, 140, 60)
        self.width = 100
        self.height = 110
        self.rect = pygame.Rect(x, y, self.width, self.height)
        self.bulb_rect = pygame.Rect(x + 30, y, 40, 30)

    def _ai_update(self, player_rect, dt_ms):
        self.facing_right = player_rect.centerx > self.rect.centerx
        speed = 1.0 + (self.phase - 1) * 0.3

        if self.state == "phase_transition":
            if self.state_timer <= 0:
                self.state = "idle"
                self.state_timer = 30
            return

        if self.state == "idle":
            self.vulnerable = False
            if self.state_timer <= 0:
                choice = random.choice(["spit", "spit", "open"])
                self.state = choice
                self.state_timer = 60

        elif self.state == "spit":
            if self.state_timer == 50:
                for i in range(self.phase + 1):
                    angle = -0.5 + (i / max(1, self.phase)) * 1.0
                    dx = player_rect.centerx - self.rect.centerx
                    base_vx = 4 * speed if dx > 0 else -4 * speed
                    self.projectiles.append({
                        "rect": pygame.Rect(self.rect.centerx, self.rect.y + 20, 12, 12),
                        "vx": base_vx + angle * 2,
                        "vy": -3 - i * 0.5,
                        "gravity": 0.15,
                        "lifetime": 120,
                        "color": (100, 200, 50),
                    })
            if self.state_timer <= 0:
                self.state = "idle"
                self.state_timer = int(50 / speed)

        elif self.state == "open":
            self.vulnerable = True
            self.bulb_rect = pygame.Rect(
                self.rect.x + 30, self.rect.y - 10, 40, 30
            )
            if self.state_timer <= 0:
                self.vulnerable = False
                self.state = "idle"
                self.state_timer = int(40 / speed)

    def draw(self, surface, cam_offset):
        super().draw(surface, cam_offset)
        if self.vulnerable and self.alive:
            bx = int(self.bulb_rect.x - cam_offset[0])
            by = int(self.bulb_rect.y - cam_offset[1])
            pygame.draw.ellipse(surface, (200, 255, 50),
                                (bx, by, self.bulb_rect.width, self.bulb_rect.height))


class CryoColossus(Boss):
    """World 3 boss: Ice golem."""

    def __init__(self, x, y):
        super().__init__(x, y, 3)
        self.color = (100, 150, 200)
        self.ice_zones = []

    def _ai_update(self, player_rect, dt_ms):
        self.facing_right = player_rect.centerx > self.rect.centerx
        speed = 1.0 + (self.phase - 1) * 0.35

        if self.state == "phase_transition":
            if self.state_timer <= 0:
                self.state = "walk"
                self.state_timer = int(90 / speed)
            return

        if self.state == "idle":
            self.vulnerable = False
            if self.state_timer <= 0:
                self.state = "walk"
                self.state_timer = int(90 / speed)

        elif self.state == "walk":
            dx = player_rect.centerx - self.rect.centerx
            self.vx = (2 * speed) if dx > 0 else (-2 * speed)
            if self.state_timer <= 0:
                self.vx = 0
                self.state = random.choice(["throw", "freeze"])
                self.state_timer = 50

        elif self.state == "throw":
            if self.state_timer == 40:
                dx = player_rect.centerx - self.rect.centerx
                for i in range(self.phase):
                    self.projectiles.append({
                        "rect": pygame.Rect(self.rect.centerx, self.rect.y + 20, 14, 14),
                        "vx": (5 + i) * speed * (1 if dx > 0 else -1),
                        "vy": -4 - i,
                        "gravity": 0.2,
                        "lifetime": 100,
                        "color": (180, 220, 255),
                    })
            if self.state_timer <= 0:
                self.state = "stunned"
                self.state_timer = int(70 / speed)

        elif self.state == "freeze":
            if self.state_timer == 30:
                self.ice_zones = [
                    pygame.Rect(self.rect.x - 60, self.rect.bottom - 10, self.width + 120, 10)
                ]
            if self.state_timer <= 0:
                self.ice_zones = []
                self.state = "stunned"
                self.state_timer = int(70 / speed)

        elif self.state == "stunned":
            self.vulnerable = True
            self.vx = 0
            if self.state_timer <= 0:
                self.vulnerable = False
                self.state = "idle"
                self.state_timer = int(30 / speed)


class GeneralVolt(Boss):
    """World 4 boss: Electric mech suit."""

    def __init__(self, x, y):
        super().__init__(x, y, 4)
        self.color = (180, 160, 40)
        self.electric_panels = []
        self.drones = []

    def _ai_update(self, player_rect, dt_ms):
        self.facing_right = player_rect.centerx > self.rect.centerx
        speed = 1.0 + (self.phase - 1) * 0.3

        if self.state == "phase_transition":
            if self.state_timer <= 0:
                self.state = "idle"
                self.state_timer = 30
            return

        if self.state == "idle":
            self.vulnerable = False
            self.electric_panels = []
            if self.state_timer <= 0:
                self.state = random.choice(["dash", "electrify", "drones"])
                self.state_timer = 60

        elif self.state == "dash":
            dx = player_rect.centerx - self.rect.centerx
            self.vx = (8 * speed) if dx > 0 else (-8 * speed)
            if self.state_timer <= 0:
                self.vx = 0
                self.state = "recover"
                self.state_timer = int(80 / speed)

        elif self.state == "electrify":
            self.vx = 0
            if self.state_timer == 50:
                # Create electric floor panels
                for i in range(2 + self.phase):
                    px = self.rect.x + random.randint(-200, 200)
                    self.electric_panels.append(
                        pygame.Rect(px, self.rect.bottom - 10, TILE_SIZE * 2, TILE_SIZE)
                    )
            if self.state_timer <= 0:
                self.electric_panels = []
                self.state = "recover"
                self.state_timer = int(70 / speed)

        elif self.state == "drones":
            if self.state_timer == 50:
                for _ in range(self.phase):
                    self.projectiles.append({
                        "rect": pygame.Rect(self.rect.centerx, self.rect.y, 16, 16),
                        "vx": random.choice([-3, 3]) * speed,
                        "vy": -2,
                        "gravity": 0.05,
                        "lifetime": 150,
                        "color": (255, 255, 100),
                    })
            if self.state_timer <= 0:
                self.state = "recover"
                self.state_timer = int(70 / speed)

        elif self.state == "recover":
            self.vulnerable = True
            self.vx = 0
            if self.state_timer <= 0:
                self.vulnerable = False
                self.state = "idle"
                self.state_timer = 30


class RogueAI(Boss):
    """World 5 final boss: 4-phase fight."""

    def __init__(self, x, y):
        super().__init__(x, y, 5)
        self.color = (120, 40, 160)
        self.width = 100
        self.height = 120
        self.rect = pygame.Rect(x, y, self.width, self.height)
        self.phase = 1
        self.max_phases = 4
        self.beam_active = False
        self.beam_rect = None

    def take_damage(self, dmg):
        if not self.vulnerable or not self.alive:
            return False
        self.hp -= dmg
        self.hit_flash = 10
        if self.hp <= 0:
            self.alive = False
            self.death_timer = 200
            return True
        # 4 phase transitions
        thresholds = [0.75, 0.50, 0.25]
        for i, t in enumerate(thresholds):
            if self.hp <= self.max_hp * t and self.phase == i + 1:
                self.phase = i + 2
                self._on_phase_change()
                break
        return False

    def _ai_update(self, player_rect, dt_ms):
        self.facing_right = player_rect.centerx > self.rect.centerx
        speed = 1.0 + (self.phase - 1) * 0.2

        if self.state == "phase_transition":
            if self.state_timer <= 0:
                self.state = "idle"
                self.state_timer = 40
            return

        if self.phase == 1:
            self._phase1_ai(player_rect, speed)
        elif self.phase == 2:
            self._phase2_ai(player_rect, speed)
        elif self.phase == 3:
            self._phase3_ai(player_rect, speed)
        else:
            self._phase4_ai(player_rect, speed)

    def _phase1_ai(self, player_rect, speed):
        """Humanoid mech: charges and slams."""
        if self.state == "idle":
            self.vulnerable = False
            if self.state_timer <= 0:
                self.state = "charge"
                self.state_timer = 45
        elif self.state == "charge":
            dx = player_rect.centerx - self.rect.centerx
            self.vx = (7 * speed) if dx > 0 else (-7 * speed)
            if self.state_timer <= 0:
                self.vx = 0
                self.state = "slam"
                self.state_timer = 30
        elif self.state == "slam":
            self.attack_rects = [pygame.Rect(
                self.rect.x - 20, self.rect.bottom - 10, self.width + 40, 20
            )]
            if self.state_timer <= 0:
                self.attack_rects = []
                self.state = "vulnerable"
                self.state_timer = int(60 / speed)
        elif self.state == "vulnerable":
            self.vulnerable = True
            if self.state_timer <= 0:
                self.vulnerable = False
                self.state = "idle"
                self.state_timer = 30

    def _phase2_ai(self, player_rect, speed):
        """Two smaller mechs (simulated as fast movement)."""
        if self.state == "idle":
            self.vulnerable = False
            if self.state_timer <= 0:
                self.state = "split_attack"
                self.state_timer = 80
        elif self.state == "split_attack":
            # Rapid movement
            self.vx = math.sin(self.state_timer * 0.3) * 8 * speed
            if self.state_timer % 20 == 0:
                self.projectiles.append({
                    "rect": pygame.Rect(self.rect.centerx, self.rect.centery, 10, 10),
                    "vx": random.uniform(-4, 4),
                    "vy": random.uniform(-3, 1),
                    "gravity": 0.1,
                    "lifetime": 90,
                    "color": (200, 50, 200),
                })
            if self.state_timer <= 0:
                self.vx = 0
                self.state = "vulnerable"
                self.state_timer = int(50 / speed)
        elif self.state == "vulnerable":
            self.vulnerable = True
            if self.state_timer <= 0:
                self.vulnerable = False
                self.state = "idle"
                self.state_timer = 30

    def _phase3_ai(self, player_rect, speed):
        """Giant head, beam attacks."""
        self.beam_active = False
        self.beam_rect = None

        if self.state == "idle":
            self.vulnerable = False
            if self.state_timer <= 0:
                self.state = "beam"
                self.state_timer = 70
        elif self.state == "beam":
            if 20 < self.state_timer < 50:
                self.beam_active = True
                bx = self.rect.centerx - 15
                by = self.rect.bottom
                self.beam_rect = pygame.Rect(bx, by, 30, 400)
                # Slowly track player
                dx = player_rect.centerx - self.rect.centerx
                self.vx = (1.5 * speed) if dx > 0 else (-1.5 * speed)
            else:
                self.vx = 0
            if self.state_timer <= 0:
                self.beam_active = False
                self.beam_rect = None
                self.vx = 0
                self.state = "vulnerable"
                self.state_timer = int(55 / speed)
        elif self.state == "vulnerable":
            self.vulnerable = True
            if self.state_timer <= 0:
                self.vulnerable = False
                self.state = "idle"
                self.state_timer = 25

    def _phase4_ai(self, player_rect, speed):
        """Exposed core - vulnerable but still dangerous."""
        if self.state == "idle":
            self.vulnerable = True
            # Constant projectile spam
            if self.state_timer % 15 == 0:
                angle = random.uniform(0, math.pi * 2)
                self.projectiles.append({
                    "rect": pygame.Rect(self.rect.centerx, self.rect.centery, 10, 10),
                    "vx": math.cos(angle) * 4 * speed,
                    "vy": math.sin(angle) * 4 * speed,
                    "gravity": 0,
                    "lifetime": 100,
                    "color": (255, 200, 50),
                })
            if self.state_timer <= 0:
                self.state_timer = 200

    def draw(self, surface, cam_offset):
        super().draw(surface, cam_offset)
        if self.beam_active and self.beam_rect and self.alive:
            bx = int(self.beam_rect.x - cam_offset[0])
            by = int(self.beam_rect.y - cam_offset[1])
            s = pygame.Surface((self.beam_rect.width, self.beam_rect.height), pygame.SRCALPHA)
            s.fill((200, 50, 200, 120))
            surface.blit(s, (bx, by))


BOSS_TYPES = {
    1: PistonPrime,
    2: QueenSporax,
    3: CryoColossus,
    4: GeneralVolt,
    5: RogueAI,
}


def create_boss(world_num, x, y):
    cls = BOSS_TYPES.get(world_num, PistonPrime)
    return cls(x, y)
