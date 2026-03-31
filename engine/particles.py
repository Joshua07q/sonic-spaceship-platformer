"""Particle system: dust, sparks, ring scatter, speed lines."""
import random
import math
import pygame


class Particle:
    def __init__(self, x, y, vx, vy, color, size, lifetime, gravity=0.1, shrink=True):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.size = size
        self.max_lifetime = lifetime
        self.lifetime = lifetime
        self.gravity = gravity
        self.shrink = shrink
        self.alive = True

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.alive = False

    def draw(self, surface, cam_offset):
        if not self.alive:
            return
        alpha = self.lifetime / self.max_lifetime
        sz = self.size * alpha if self.shrink else self.size
        if sz < 1:
            sz = 1
        sx = int(self.x - cam_offset[0])
        sy = int(self.y - cam_offset[1])
        color = (*self.color[:3], int(255 * alpha))
        s = pygame.Surface((int(sz * 2), int(sz * 2)), pygame.SRCALPHA)
        pygame.draw.circle(s, color, (int(sz), int(sz)), int(sz))
        surface.blit(s, (sx - int(sz), sy - int(sz)))


class SpeedLine:
    def __init__(self, x, y, length, speed):
        self.x = x
        self.y = y
        self.length = length
        self.speed = speed
        self.lifetime = 10
        self.alive = True

    def update(self):
        self.x -= self.speed
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.alive = False

    def draw(self, surface, cam_offset):
        if not self.alive:
            return
        alpha = int(200 * (self.lifetime / 10))
        sx = int(self.x - cam_offset[0])
        sy = int(self.y - cam_offset[1])
        color = (255, 255, 255, alpha)
        s = pygame.Surface((self.length, 2), pygame.SRCALPHA)
        s.fill(color)
        surface.blit(s, (sx, sy))


class ParticleSystem:
    def __init__(self):
        self.particles = []
        self.speed_lines = []

    def update(self):
        self.particles = [p for p in self.particles if p.alive]
        self.speed_lines = [s for s in self.speed_lines if s.alive]
        for p in self.particles:
            p.update()
        for s in self.speed_lines:
            s.update()

    def draw(self, surface, cam_offset):
        for p in self.particles:
            p.draw(surface, cam_offset)
        for s in self.speed_lines:
            s.draw(surface, cam_offset)

    def emit_dust(self, x, y, count=5):
        for _ in range(count):
            vx = random.uniform(-1.5, 1.5)
            vy = random.uniform(-2, -0.5)
            self.particles.append(
                Particle(x, y, vx, vy, (180, 170, 150), random.uniform(2, 4), 20, 0.05)
            )

    def emit_sparks(self, x, y, count=8):
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(2, 5)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            color = random.choice([(255, 255, 100), (255, 200, 50), (255, 150, 30)])
            self.particles.append(
                Particle(x, y, vx, vy, color, random.uniform(2, 4), 15, 0.08)
            )

    def emit_ring_scatter(self, x, y, count=10):
        for i in range(count):
            angle = (2 * math.pi / count) * i
            speed = random.uniform(3, 6)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed - 3
            self.particles.append(
                Particle(x, y, vx, vy, (255, 200, 0), 5, 40, 0.2, shrink=False)
            )

    def emit_speed_lines(self, x, y, height=60):
        for _ in range(3):
            ly = y + random.randint(-height // 2, height // 2)
            length = random.randint(20, 50)
            self.speed_lines.append(SpeedLine(x, ly, length, random.uniform(8, 14)))

    def emit_explosion(self, x, y, count=20, big=False):
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1, 6 if big else 4)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            color = random.choice([(255, 100, 30), (255, 200, 50), (255, 50, 10), (255, 255, 200)])
            size = random.uniform(3, 8 if big else 5)
            life = random.randint(20, 40 if big else 25)
            self.particles.append(Particle(x, y, vx, vy, color, size, life, 0.05))

    def emit_boss_death(self, x, y):
        """Multi-stage explosion for boss death."""
        self.emit_explosion(x, y, 30, big=True)

    def clear(self):
        self.particles.clear()
        self.speed_lines.clear()
