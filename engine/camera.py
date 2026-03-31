"""Scrolling camera with smooth follow and deadzone."""
import pygame
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE


class Camera:
    def __init__(self, level_width, level_height):
        self.x = 0.0
        self.y = 0.0
        self.target_x = 0.0
        self.target_y = 0.0
        self.level_width = level_width
        self.level_height = level_height
        self.locked = False
        self.lock_rect = None
        self.auto_scroll = False
        self.auto_scroll_speed = 0.0
        self.look_ahead = 80
        self.deadzone_y = 100
        self.smooth_speed = 0.08
        self.shake_timer = 0
        self.shake_amplitude = 0
        self.shake_offset_x = 0
        self.shake_offset_y = 0

    def update(self, target_rect, facing_right, dt=1.0):
        if self.auto_scroll:
            self.x += self.auto_scroll_speed * dt
            self.target_x = self.x
            # Y still follows player
            self.target_y = target_rect.centery - SCREEN_HEIGHT // 2
            self.y += (self.target_y - self.y) * self.smooth_speed * 3
            self._clamp()
            self._update_shake()
            return

        if self.locked and self.lock_rect:
            self.target_x = self.lock_rect.x
            self.target_y = self.lock_rect.y
            self.x += (self.target_x - self.x) * 0.15
            self.y += (self.target_y - self.y) * 0.15
            self._update_shake()
            return

        # X: smooth follow with look-ahead
        ahead = self.look_ahead if facing_right else -self.look_ahead
        self.target_x = target_rect.centerx + ahead - SCREEN_WIDTH // 2
        self.x += (self.target_x - self.x) * self.smooth_speed

        # Y: deadzone
        screen_y = target_rect.centery - self.y
        center_y = SCREEN_HEIGHT // 2
        if screen_y < center_y - self.deadzone_y:
            self.target_y = target_rect.centery - (center_y - self.deadzone_y)
        elif screen_y > center_y + self.deadzone_y:
            self.target_y = target_rect.centery - (center_y + self.deadzone_y)
        self.y += (self.target_y - self.y) * self.smooth_speed

        self._clamp()
        self._update_shake()

    def _clamp(self):
        max_x = self.level_width - SCREEN_WIDTH
        max_y = self.level_height - SCREEN_HEIGHT
        self.x = max(0, min(self.x, max_x))
        self.y = max(0, min(self.y, max_y))

    def _update_shake(self):
        import random
        if self.shake_timer > 0:
            self.shake_timer -= 1
            intensity = self.shake_amplitude * (self.shake_timer / 20)
            self.shake_offset_x = random.randint(int(-intensity), int(intensity))
            self.shake_offset_y = random.randint(int(-intensity), int(intensity))
        else:
            self.shake_offset_x = 0
            self.shake_offset_y = 0

    def start_shake(self, amplitude=6, duration=15):
        self.shake_amplitude = amplitude
        self.shake_timer = duration

    def lock_to_rect(self, rect):
        self.locked = True
        self.lock_rect = rect

    def unlock(self):
        self.locked = False
        self.lock_rect = None

    def start_auto_scroll(self, speed):
        self.auto_scroll = True
        self.auto_scroll_speed = speed

    def stop_auto_scroll(self):
        self.auto_scroll = False
        self.auto_scroll_speed = 0

    def apply(self, rect):
        return pygame.Rect(
            rect.x - int(self.x) + self.shake_offset_x,
            rect.y - int(self.y) + self.shake_offset_y,
            rect.width,
            rect.height,
        )

    def apply_pos(self, x, y):
        return (
            x - int(self.x) + self.shake_offset_x,
            y - int(self.y) + self.shake_offset_y,
        )

    def get_offset(self):
        return (int(self.x) - self.shake_offset_x, int(self.y) - self.shake_offset_y)
