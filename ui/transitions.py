"""Screen transitions between levels."""
import pygame
from settings import SCREEN_WIDTH, SCREEN_HEIGHT


class TransitionManager:
    def __init__(self):
        self.active = False
        self.phase = 0  # 0=slide in, 1=show, 2=slide out
        self.timer = 0
        self.world_text = ""
        self.level_text = ""
        self.bg_color = (0, 0, 0)
        self.slide_progress = 0

    def start(self, world_text, level_text, bg_color=(0, 0, 0)):
        self.active = True
        self.phase = 0
        self.timer = 0
        self.world_text = world_text
        self.level_text = level_text
        self.bg_color = bg_color
        self.slide_progress = 0

    def update(self, dt_ms):
        if not self.active:
            return True

        self.timer += dt_ms

        if self.phase == 0:
            # Slide in
            self.slide_progress = min(1.0, self.timer / 400)
            if self.slide_progress >= 1.0:
                self.phase = 1
                self.timer = 0
        elif self.phase == 1:
            # Show text
            if self.timer > 1500:
                self.phase = 2
                self.timer = 0
        elif self.phase == 2:
            # Slide out
            self.slide_progress = max(0.0, 1.0 - self.timer / 400)
            if self.slide_progress <= 0:
                self.active = False
                return True

        return False

    def draw(self, surface):
        if not self.active:
            return

        # Black bars sliding in/out
        bar_height = int(SCREEN_HEIGHT * self.slide_progress)
        top_bar = pygame.Surface((SCREEN_WIDTH, bar_height))
        top_bar.fill(self.bg_color)
        surface.blit(top_bar, (0, 0))

        bottom_bar = pygame.Surface((SCREEN_WIDTH, bar_height))
        bottom_bar.fill(self.bg_color)
        surface.blit(bottom_bar, (0, SCREEN_HEIGHT - bar_height))

        if self.phase == 1:
            # Text
            font_big = pygame.font.SysFont("arial", 44, bold=True)
            font_sub = pygame.font.SysFont("arial", 24)

            text1 = font_big.render(self.world_text, True, (255, 255, 255))
            surface.blit(text1, text1.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 25)))

            text2 = font_sub.render(self.level_text, True, (200, 200, 220))
            surface.blit(text2, text2.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20)))
