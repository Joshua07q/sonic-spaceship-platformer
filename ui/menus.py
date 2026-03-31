"""Menu screens — all touch/click friendly for mobile browser."""
import pygame
import math
from settings import SCREEN_WIDTH, SCREEN_HEIGHT


class _Button:
    """Clickable/tappable button."""
    def __init__(self, x, y, w, h, text, value, color=(80, 80, 120)):
        self.rect = pygame.Rect(x - w // 2, y - h // 2, w, h)
        self.text = text
        self.value = value
        self.color = color
        self.hover = False

    def draw(self, surface, selected=False):
        c = (255, 255, 100) if selected or self.hover else self.color
        pygame.draw.rect(surface, c, self.rect, 0, 8)
        pygame.draw.rect(surface, (255, 255, 255), self.rect, 2, 8)
        font = pygame.font.SysFont("arial", 26, bold=True)
        t = font.render(self.text, True, (0, 0, 0) if selected else (255, 255, 255))
        surface.blit(t, t.get_rect(center=self.rect.center))

    def hit(self, pos):
        return self.rect.collidepoint(pos)


def _get_click_pos(event):
    if event.type == pygame.MOUSEBUTTONDOWN:
        return event.pos
    if event.type == pygame.FINGERDOWN:
        return (int(event.x * SCREEN_WIDTH), int(event.y * SCREEN_HEIGHT))
    return None


class TitleMenu:
    def __init__(self, has_save=False):
        cx = SCREEN_WIDTH // 2
        self.buttons = [_Button(cx, 380, 280, 56, "START GAME", "start")]
        if has_save:
            self.buttons.insert(0, _Button(cx, 380, 280, 56, "CONTINUE", "continue"))
            self.buttons[1] = _Button(cx, 450, 280, 56, "START GAME", "start")
        self.selected = 0
        self.timer = 0

    def handle_event(self, event):
        pos = _get_click_pos(event)
        if pos:
            for b in self.buttons:
                if b.hit(pos):
                    return b.value
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % len(self.buttons)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % len(self.buttons)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                return self.buttons[self.selected].value
        return None

    def update(self, dt_ms):
        self.timer += dt_ms * 0.001

    def draw(self, surface):
        font_title = pygame.font.SysFont("arial", 58, bold=True)
        font_sub = pygame.font.SysFont("arial", 22)

        title = font_title.render("SONIC", True, (0, 120, 255))
        surface.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2 - 70, 140)))
        title2 = font_title.render("SPACESHIP", True, (255, 140, 0))
        surface.blit(title2, title2.get_rect(center=(SCREEN_WIDTH // 2 + 50, 210)))
        sub = font_sub.render("THE ASTRAL CARRIER", True, (180, 180, 200))
        surface.blit(sub, sub.get_rect(center=(SCREEN_WIDTH // 2, 270)))

        for i in range(SCREEN_WIDTH // 4, 3 * SCREEN_WIDTH // 4):
            c = int(128 + 127 * math.sin(i * 0.02 + self.timer * 3))
            pygame.draw.line(surface, (0, c // 2, c), (i, 310), (i, 312))

        for i, b in enumerate(self.buttons):
            b.draw(surface, i == self.selected)

        hint = font_sub.render("Tap a button or press ENTER", True, (120, 120, 140))
        surface.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50)))


class CharacterSelect:
    def __init__(self):
        cx = SCREEN_WIDTH // 2
        self.sonic_btn = _Button(cx - 160, 400, 240, 280, "", "sonic", (20, 60, 140))
        self.tails_btn = _Button(cx + 160, 400, 240, 280, "", "tails", (140, 90, 10))
        self.selected = 0
        self.timer = 0
        self.preselected = None

    def handle_event(self, event):
        pos = _get_click_pos(event)
        if pos:
            if self.sonic_btn.hit(pos):
                return "sonic"
            if self.tails_btn.hit(pos):
                return "tails"
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
        font_title = pygame.font.SysFont("arial", 38, bold=True)
        font_name = pygame.font.SysFont("arial", 30, bold=True)
        font_stat = pygame.font.SysFont("arial", 18)

        title = font_title.render("CHOOSE YOUR CHARACTER", True, (255, 255, 255))
        surface.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 70)))

        self.sonic_btn.draw(surface, self.selected == 0)
        sr = self.sonic_btn.rect
        pygame.draw.rect(surface, (0, 100, 230), (sr.centerx - 25, sr.y + 20, 50, 70))
        name = font_name.render("SONIC", True, (0, 150, 255))
        surface.blit(name, name.get_rect(center=(sr.centerx, sr.y + 110)))
        for i, s in enumerate(["Speed: *****", "Power: ****", "Jump:  ****"]):
            t = font_stat.render(s, True, (200, 200, 220))
            surface.blit(t, (sr.x + 20, sr.y + 140 + i * 28))

        self.tails_btn.draw(surface, self.selected == 1)
        tr = self.tails_btn.rect
        pygame.draw.rect(surface, (220, 140, 20), (tr.centerx - 25, tr.y + 20, 50, 70))
        name2 = font_name.render("TAILS", True, (255, 180, 40))
        surface.blit(name2, name2.get_rect(center=(tr.centerx, tr.y + 110)))
        for i, s in enumerate(["Speed: ***", "Flight: *****", "Power: ***"]):
            t = font_stat.render(s, True, (200, 200, 220))
            surface.blit(t, (tr.x + 20, tr.y + 140 + i * 28))

        hint = font_stat.render("TAP a character to play!", True, (150, 150, 170))
        surface.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 40)))


class PauseMenu:
    def __init__(self):
        cx = SCREEN_WIDTH // 2
        self.buttons = [
            _Button(cx, 300, 260, 50, "RESUME", "resume"),
            _Button(cx, 370, 260, 50, "RESTART", "restart"),
            _Button(cx, 440, 260, 50, "QUIT", "quit"),
        ]
        self.selected = 0

    def handle_event(self, event):
        pos = _get_click_pos(event)
        if pos:
            for b in self.buttons:
                if b.hit(pos):
                    return b.value
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % len(self.buttons)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % len(self.buttons)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                return self.buttons[self.selected].value
            elif event.key == pygame.K_ESCAPE:
                return "resume"
        return None

    def draw(self, surface):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))
        font = pygame.font.SysFont("arial", 48, bold=True)
        t = font.render("PAUSED", True, (255, 255, 255))
        surface.blit(t, t.get_rect(center=(SCREEN_WIDTH // 2, 200)))
        for i, b in enumerate(self.buttons):
            b.draw(surface, i == self.selected)


class GameOverScreen:
    def __init__(self):
        cx = SCREEN_WIDTH // 2
        self.buttons = [
            _Button(cx, 380, 260, 50, "CONTINUE", "continue"),
            _Button(cx, 450, 260, 50, "QUIT", "quit"),
        ]
        self.selected = 0
        self.timer = 0

    def handle_event(self, event):
        pos = _get_click_pos(event)
        if pos:
            for b in self.buttons:
                if b.hit(pos):
                    return b.value
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % len(self.buttons)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % len(self.buttons)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                return self.buttons[self.selected].value
        return None

    def draw(self, surface):
        surface.fill((15, 5, 5))
        self.timer += 1
        font = pygame.font.SysFont("arial", 60, bold=True)
        alpha = int(200 + 55 * math.sin(self.timer * 0.1))
        t = font.render("GAME OVER", True, (alpha, 30, 30))
        surface.blit(t, t.get_rect(center=(SCREEN_WIDTH // 2, 240)))
        for i, b in enumerate(self.buttons):
            b.draw(surface, i == self.selected)


class LevelCompleteScreen:
    def __init__(self, rings, enemies, time_seconds, level_name):
        self.rings = rings
        self.enemies = enemies
        self.time = time_seconds
        self.level_name = level_name
        self.timer = 0
        self.phase = 0
        self.btn = _Button(SCREEN_WIDTH // 2, 500, 280, 56, "NEXT LEVEL >>", "next", (40, 140, 40))

    def handle_event(self, event):
        pos = _get_click_pos(event)
        if pos and self.btn.hit(pos):
            return "next"
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
            return "next"
        return None

    def update(self, dt_ms):
        self.timer += dt_ms
        if self.timer > 300:
            self.phase = 3

    def draw(self, surface):
        surface.fill((10, 10, 30))
        font_title = pygame.font.SysFont("arial", 38, bold=True)
        font_stat = pygame.font.SysFont("arial", 26)

        t = font_title.render(f"{self.level_name} COMPLETE!", True, (255, 220, 50))
        surface.blit(t, t.get_rect(center=(SCREEN_WIDTH // 2, 140)))

        cy = 230
        for txt, col in [
            (f"Rings:   {self.rings}", (255, 200, 0)),
            (f"Enemies: {self.enemies}", (255, 100, 100)),
            (f"Time:    {int(self.time)//60:02d}:{int(self.time)%60:02d}", (100, 200, 255)),
        ]:
            r = font_stat.render(txt, True, col)
            surface.blit(r, r.get_rect(center=(SCREEN_WIDTH // 2, cy)))
            cy += 50

        score = self.rings * 10 + self.enemies * 100
        s = font_title.render(f"SCORE: {score}", True, (255, 255, 255))
        surface.blit(s, s.get_rect(center=(SCREEN_WIDTH // 2, cy + 20)))

        self.btn.draw(surface, True)
