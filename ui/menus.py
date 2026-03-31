"""Menu screens: title, character select, pause, game over, level complete."""
import pygame
import math
from settings import SCREEN_WIDTH, SCREEN_HEIGHT


class TitleMenu:
    def __init__(self, has_save=False):
        self.has_save = has_save
        self.options = ["START GAME"]
        if has_save:
            self.options.insert(0, "CONTINUE")
        self.options.append("QUIT")
        self.selected = 0
        self.timer = 0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % len(self.options)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % len(self.options)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                opt = self.options[self.selected].lower().replace(" ", "_")
                if opt == "start_game":
                    return "start"
                elif opt == "continue":
                    return "continue"
                elif opt == "quit":
                    return "quit"
        return None

    def update(self, dt_ms):
        self.timer += dt_ms * 0.001

    def draw(self, surface):
        # Title
        font_title = pygame.font.SysFont("arial", 64, bold=True)
        font_sub = pygame.font.SysFont("arial", 20)
        font_opt = pygame.font.SysFont("arial", 28)

        # Logo
        title = font_title.render("SONIC", True, (0, 120, 255))
        surface.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2 - 80, 150)))

        title2 = font_title.render("SPACESHIP", True, (255, 140, 0))
        surface.blit(title2, title2.get_rect(center=(SCREEN_WIDTH // 2 + 40, 220)))

        sub = font_sub.render("ASTRAL CARRIER", True, (180, 180, 200))
        surface.blit(sub, sub.get_rect(center=(SCREEN_WIDTH // 2, 275)))

        # Animated line
        line_y = 310
        for i in range(SCREEN_WIDTH // 4, 3 * SCREEN_WIDTH // 4):
            c = int(128 + 127 * math.sin(i * 0.02 + self.timer * 3))
            pygame.draw.line(surface, (0, c // 2, c), (i, line_y), (i, line_y + 2))

        # Options
        for i, opt in enumerate(self.options):
            color = (255, 255, 100) if i == self.selected else (180, 180, 200)
            text = font_opt.render(opt, True, color)
            y = 360 + i * 50
            rect = text.get_rect(center=(SCREEN_WIDTH // 2, y))
            surface.blit(text, rect)

            if i == self.selected:
                # Arrow indicator
                arrow_x = rect.left - 30
                bob = math.sin(self.timer * 5) * 4
                pygame.draw.polygon(surface, (255, 255, 100), [
                    (arrow_x + bob, y - 8),
                    (arrow_x + 15 + bob, y),
                    (arrow_x + bob, y + 8),
                ])

        # Footer
        footer = font_sub.render("Press ENTER to select", True, (100, 100, 120))
        surface.blit(footer, footer.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50)))


class CharacterSelect:
    def __init__(self):
        self.selected = 0  # 0=sonic, 1=tails
        self.timer = 0
        self.preselected = None

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_a):
                self.selected = 0
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.selected = 1
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                return "sonic" if self.selected == 0 else "tails"
        return None

    def update(self, dt_ms):
        self.timer += dt_ms * 0.001
        if self.preselected:
            self.selected = 0 if self.preselected == "sonic" else 1
            self.preselected = None

    def draw(self, surface):
        font_title = pygame.font.SysFont("arial", 40, bold=True)
        font_name = pygame.font.SysFont("arial", 32, bold=True)
        font_stat = pygame.font.SysFont("arial", 18)

        title = font_title.render("CHOOSE YOUR CHARACTER", True, (255, 255, 255))
        surface.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 80)))

        # Sonic panel (left)
        sonic_x = SCREEN_WIDTH // 4
        sonic_selected = self.selected == 0
        self._draw_character_panel(
            surface, sonic_x, 200, "SONIC", (0, 100, 230),
            {"Speed": 5, "Power": 4, "Jump": 4, "Special": 3},
            sonic_selected
        )

        # Tails panel (right)
        tails_x = 3 * SCREEN_WIDTH // 4
        tails_selected = self.selected == 1
        self._draw_character_panel(
            surface, tails_x, 200, "TAILS", (220, 140, 20),
            {"Speed": 3, "Flight": 5, "Jump": 3, "Special": 4},
            tails_selected
        )

        # Instructions
        font_sm = pygame.font.SysFont("arial", 20)
        inst = font_sm.render("< LEFT / RIGHT >  ENTER to confirm", True, (150, 150, 170))
        surface.blit(inst, inst.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 60)))

    def _draw_character_panel(self, surface, cx, cy, name, color, stats, selected):
        panel_w, panel_h = 280, 350
        px = cx - panel_w // 2
        py = cy

        # Panel background
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        border_color = (255, 255, 100) if selected else (80, 80, 90)
        panel.fill((20, 20, 30, 200))
        pygame.draw.rect(panel, border_color, (0, 0, panel_w, panel_h), 3)
        surface.blit(panel, (px, py))

        # Character sprite placeholder
        char_rect = pygame.Rect(cx - 30, py + 20, 60, 80)
        pygame.draw.rect(surface, color, char_rect)

        # Bob animation if selected
        bob_y = int(math.sin(self.timer * 4) * 5) if selected else 0

        font_name = pygame.font.SysFont("arial", 28, bold=True)
        name_text = font_name.render(name, True, color)
        surface.blit(name_text, name_text.get_rect(center=(cx, py + 120 + bob_y)))

        # Stats
        font_stat = pygame.font.SysFont("arial", 18)
        stat_y = py + 160
        for stat_name, value in stats.items():
            label = font_stat.render(f"{stat_name}:", True, (180, 180, 200))
            surface.blit(label, (px + 20, stat_y))

            # Star bar
            for i in range(5):
                star_x = px + 140 + i * 22
                star_color = (255, 220, 50) if i < value else (60, 60, 70)
                self._draw_star(surface, star_x, stat_y + 6, 8, star_color)

            stat_y += 30

    def _draw_star(self, surface, x, y, size, color):
        points = []
        for i in range(5):
            angle = math.pi / 2 + i * 4 * math.pi / 5
            points.append((x + size * math.cos(angle), y - size * math.sin(angle)))
            angle += 2 * math.pi / 5
            points.append((x + size * 0.4 * math.cos(angle), y - size * 0.4 * math.sin(angle)))
        pygame.draw.polygon(surface, color, points)


class PauseMenu:
    def __init__(self):
        self.options = ["RESUME", "RESTART LEVEL", "QUIT TO MENU"]
        self.selected = 0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % len(self.options)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % len(self.options)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                return ["resume", "restart", "quit"][self.selected]
            elif event.key == pygame.K_ESCAPE:
                return "resume"
        return None

    def draw(self, surface):
        # Overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))

        font_title = pygame.font.SysFont("arial", 48, bold=True)
        font_opt = pygame.font.SysFont("arial", 28)

        title = font_title.render("PAUSED", True, (255, 255, 255))
        surface.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 220)))

        for i, opt in enumerate(self.options):
            color = (255, 255, 100) if i == self.selected else (180, 180, 200)
            text = font_opt.render(opt, True, color)
            surface.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, 320 + i * 50)))


class GameOverScreen:
    def __init__(self):
        self.options = ["CONTINUE", "QUIT TO MENU"]
        self.selected = 0
        self.timer = 0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % len(self.options)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % len(self.options)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                return ["continue", "quit"][self.selected]
        return None

    def draw(self, surface):
        surface.fill((15, 5, 5))

        self.timer += 1
        font_big = pygame.font.SysFont("arial", 64, bold=True)
        font_opt = pygame.font.SysFont("arial", 28)

        # Flickering GAME OVER
        alpha = int(200 + 55 * math.sin(self.timer * 0.1))
        text = font_big.render("GAME OVER", True, (alpha, 30, 30))
        surface.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, 250)))

        for i, opt in enumerate(self.options):
            color = (255, 255, 100) if i == self.selected else (180, 180, 200)
            t = font_opt.render(opt, True, color)
            surface.blit(t, t.get_rect(center=(SCREEN_WIDTH // 2, 380 + i * 50)))


class LevelCompleteScreen:
    def __init__(self, rings, enemies, time_seconds, level_name):
        self.rings = rings
        self.enemies = enemies
        self.time = time_seconds
        self.level_name = level_name
        self.timer = 0
        self.display_rings = 0
        self.display_enemies = 0
        self.display_time = 0
        self.phase = 0  # 0=rings counting, 1=enemies, 2=time, 3=done

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                if self.phase >= 3:
                    return "next"
                else:
                    # Skip animation
                    self.phase = 3
                    self.display_rings = self.rings
                    self.display_enemies = self.enemies
                    self.display_time = self.time
        return None

    def update(self, dt_ms):
        self.timer += dt_ms

        if self.phase == 0:
            self.display_rings = min(self.rings, self.display_rings + 1)
            if self.display_rings >= self.rings:
                self.phase = 1
        elif self.phase == 1:
            self.display_enemies = min(self.enemies, self.display_enemies + 1)
            if self.display_enemies >= self.enemies:
                self.phase = 2
        elif self.phase == 2:
            self.display_time += 0.1
            if self.display_time >= self.time:
                self.display_time = self.time
                self.phase = 3

    def draw(self, surface):
        surface.fill((10, 10, 30))

        font_title = pygame.font.SysFont("arial", 40, bold=True)
        font_stat = pygame.font.SysFont("arial", 28)
        font_sm = pygame.font.SysFont("arial", 20)

        title = font_title.render(f"{self.level_name} COMPLETE!", True, (255, 220, 50))
        surface.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 150)))

        # Stats
        cy = 260
        ring_text = font_stat.render(f"Rings:    {int(self.display_rings)}", True, (255, 200, 0))
        surface.blit(ring_text, ring_text.get_rect(center=(SCREEN_WIDTH // 2, cy)))

        enemy_text = font_stat.render(f"Enemies:  {int(self.display_enemies)}", True, (255, 100, 100))
        surface.blit(enemy_text, enemy_text.get_rect(center=(SCREEN_WIDTH // 2, cy + 50)))

        minutes = int(self.display_time) // 60
        seconds = int(self.display_time) % 60
        time_text = font_stat.render(f"Time:     {minutes:02d}:{seconds:02d}", True, (100, 200, 255))
        surface.blit(time_text, time_text.get_rect(center=(SCREEN_WIDTH // 2, cy + 100)))

        # Score
        score = int(self.display_rings) * 10 + int(self.display_enemies) * 100
        score_text = font_title.render(f"SCORE: {score}", True, (255, 255, 255))
        surface.blit(score_text, score_text.get_rect(center=(SCREEN_WIDTH // 2, cy + 170)))

        if self.phase >= 3:
            prompt = font_sm.render("Press ENTER to continue", True, (150, 150, 170))
            if pygame.time.get_ticks() % 1000 < 700:
                surface.blit(prompt, prompt.get_rect(center=(SCREEN_WIDTH // 2, cy + 240)))
