"""HUD: health, rings, lives, timer, level name."""
import pygame
from settings import SCREEN_WIDTH


class HUD:
    def __init__(self):
        self.font = None
        self.font_small = None
        self._init_fonts()

    def _init_fonts(self):
        try:
            self.font = pygame.font.SysFont("arial", 22, bold=True)
            self.font_small = pygame.font.SysFont("arial", 16)
        except Exception:
            self.font = pygame.font.Font(None, 24)
            self.font_small = pygame.font.Font(None, 18)

    def draw(self, surface, hp, rings, lives, world, level, timer, level_name):
        if not self.font:
            self._init_fonts()

        bar_height = 36
        bar = pygame.Surface((SCREEN_WIDTH, bar_height), pygame.SRCALPHA)
        bar.fill((0, 0, 0, 160))
        surface.blit(bar, (0, 0))

        x_offset = 15

        # Hearts
        for i in range(3):
            if i < hp:
                color = (255, 50, 70)
            else:
                color = (80, 40, 40)
            self._draw_heart(surface, x_offset + i * 28, 8, 10, color)
        x_offset += 100

        # Ring icon + count
        pygame.draw.circle(surface, (255, 200, 0), (x_offset + 8, 18), 7, 2)
        ring_text = self.font.render(f"x{rings}", True, (255, 220, 100))
        surface.blit(ring_text, (x_offset + 20, 7))
        x_offset += 100

        # Lives
        lives_text = self.font.render(f"x{lives}", True, (200, 200, 220))
        pygame.draw.rect(surface, (100, 100, 200), (x_offset, 8, 18, 18), 2)
        surface.blit(lives_text, (x_offset + 22, 7))
        x_offset += 80

        # Level name (center)
        name_str = f"WORLD {world}-{level}  {level_name}"
        name_text = self.font.render(name_str, True, (200, 200, 220))
        name_rect = name_text.get_rect(center=(SCREEN_WIDTH // 2, 18))
        surface.blit(name_text, name_rect)

        # Timer (right)
        minutes = int(timer) // 60
        seconds = int(timer) % 60
        ms = int((timer % 1) * 100)
        time_str = f"{minutes:02d}:{seconds:02d}.{ms:02d}"
        time_text = self.font.render(time_str, True, (180, 180, 200))
        surface.blit(time_text, (SCREEN_WIDTH - 140, 7))

    def _draw_heart(self, surface, x, y, size, color):
        """Draw a heart shape."""
        points = []
        import math
        for i in range(20):
            t = i / 20 * math.pi * 2
            hx = size * (16 * math.sin(t) ** 3) / 16
            hy = -size * (13 * math.cos(t) - 5 * math.cos(2*t) - 2 * math.cos(3*t) - math.cos(4*t)) / 16
            points.append((x + hx, y + hy + size))
        if len(points) >= 3:
            pygame.draw.polygon(surface, color, points)
