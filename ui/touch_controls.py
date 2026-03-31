"""On-screen touch controls for mobile/browser: D-pad + action buttons."""
import pygame
from settings import SCREEN_WIDTH, SCREEN_HEIGHT


class TouchButton:
    def __init__(self, x, y, radius, label, key_code, color=(255, 255, 255)):
        self.x = x
        self.y = y
        self.radius = radius
        self.label = label
        self.key_code = key_code
        self.color = color
        self.pressed = False
        self.alpha = 60

    def contains(self, px, py):
        dx = px - self.x
        dy = py - self.y
        return (dx * dx + dy * dy) <= self.radius * self.radius

    def draw(self, surface):
        a = 120 if self.pressed else self.alpha
        s = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, a),
                           (self.radius, self.radius), self.radius)
        pygame.draw.circle(s, (*self.color, min(255, a + 60)),
                           (self.radius, self.radius), self.radius, 3)
        surface.blit(s, (self.x - self.radius, self.y - self.radius))

        try:
            font = pygame.font.SysFont("arial", max(14, self.radius // 2), bold=True)
            text = font.render(self.label, True, (255, 255, 255, min(255, a + 100)))
            tr = text.get_rect(center=(self.x, self.y))
            surface.blit(text, tr)
        except Exception:
            pass


class TouchControls:
    """Manages on-screen touch buttons and translates to key states."""

    def __init__(self):
        self.enabled = True
        self.buttons = []
        self.virtual_keys = {}  # key_code -> pressed
        self._setup_buttons()

    def _setup_buttons(self):
        # D-pad (bottom-left) — BIG for fat fingers
        pad_x = 120
        pad_y = SCREEN_HEIGHT - 130
        r = 48

        self.buttons = [
            TouchButton(pad_x - 75, pad_y, r, "<", pygame.K_LEFT, (100, 150, 255)),
            TouchButton(pad_x + 75, pad_y, r, ">", pygame.K_RIGHT, (100, 150, 255)),
            TouchButton(pad_x, pad_y - 70, r, "^", pygame.K_UP, (100, 150, 255)),
            TouchButton(pad_x, pad_y + 70, r, "v", pygame.K_DOWN, (100, 150, 255)),
        ]

        # Action buttons (bottom-right) — BIG
        act_x = SCREEN_WIDTH - 130
        act_y = SCREEN_HEIGHT - 130

        self.buttons.extend([
            TouchButton(act_x + 55, act_y, 52, "JUMP", pygame.K_SPACE, (80, 220, 80)),
            TouchButton(act_x - 40, act_y, 44, "ATK", pygame.K_j, (220, 80, 80)),
            TouchButton(act_x + 55, act_y - 85, 36, "RUN", pygame.K_LSHIFT, (220, 180, 50)),
            TouchButton(SCREEN_WIDTH - 50, 45, 28, "||", pygame.K_ESCAPE, (180, 180, 180)),
        ])

        for b in self.buttons:
            self.virtual_keys[b.key_code] = False

    def handle_event(self, event):
        """Process touch/mouse events. Returns list of (key_code, pressed) pairs."""
        if not self.enabled:
            return []

        results = []

        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
            if event.type == pygame.FINGERDOWN:
                px = int(event.x * SCREEN_WIDTH)
                py = int(event.y * SCREEN_HEIGHT)
            else:
                px, py = event.pos
            for b in self.buttons:
                if b.contains(px, py):
                    if not b.pressed:
                        b.pressed = True
                        self.virtual_keys[b.key_code] = True
                        results.append((b.key_code, True))

        elif event.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
            # Release all buttons on finger up
            for b in self.buttons:
                if b.pressed:
                    b.pressed = False
                    self.virtual_keys[b.key_code] = False
                    results.append((b.key_code, False))

        elif event.type in (pygame.MOUSEMOTION, pygame.FINGERMOTION):
            if event.type == pygame.FINGERMOTION:
                px = int(event.x * SCREEN_WIDTH)
                py = int(event.y * SCREEN_HEIGHT)
            else:
                if not pygame.mouse.get_pressed()[0]:
                    return results
                px, py = event.pos
            for b in self.buttons:
                inside = b.contains(px, py)
                if inside and not b.pressed:
                    b.pressed = True
                    self.virtual_keys[b.key_code] = True
                    results.append((b.key_code, True))
                elif not inside and b.pressed:
                    b.pressed = False
                    self.virtual_keys[b.key_code] = False
                    results.append((b.key_code, False))

        return results

    def get_keys(self, real_keys):
        """Return a merged key state: real keyboard + virtual touch buttons."""
        if not self.enabled:
            return real_keys
        return _MergedKeys(real_keys, self.virtual_keys)

    def draw(self, surface):
        if not self.enabled:
            return
        for b in self.buttons:
            b.draw(surface)


class _MergedKeys:
    """Proxies pygame key state merged with virtual touch button states."""

    def __init__(self, real_keys, virtual_keys):
        self._real = real_keys
        self._virtual = virtual_keys

    def __getitem__(self, key):
        if self._virtual.get(key, False):
            return True
        return self._real[key]
