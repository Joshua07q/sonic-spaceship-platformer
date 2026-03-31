"""Physics engine: gravity, velocity, AABB collision resolution."""
import pygame
from settings import GRAVITY, MAX_FALL_SPEED, FRICTION, TILE_SIZE


class AABB:
    """Axis-aligned bounding box for collision detection."""

    @staticmethod
    def overlap(rect_a, rect_b):
        return rect_a.colliderect(rect_b)

    @staticmethod
    def resolve_horizontal(entity_rect, vx, solid_rects):
        entity_rect.x += vx
        for solid in solid_rects:
            if entity_rect.colliderect(solid):
                if vx > 0:
                    entity_rect.right = solid.left
                elif vx < 0:
                    entity_rect.left = solid.right
        return entity_rect

    @staticmethod
    def resolve_vertical(entity_rect, vy, solid_rects, one_way_rects=None):
        old_bottom = entity_rect.bottom
        entity_rect.y += vy
        on_ground = False
        hit_ceiling = False

        for solid in solid_rects:
            if entity_rect.colliderect(solid):
                if vy > 0:
                    entity_rect.bottom = solid.top
                    on_ground = True
                elif vy < 0:
                    entity_rect.top = solid.bottom
                    hit_ceiling = True

        if one_way_rects and vy > 0:
            for ow in one_way_rects:
                if entity_rect.colliderect(ow) and old_bottom <= ow.top + 4:
                    entity_rect.bottom = ow.top
                    on_ground = True

        return entity_rect, on_ground, hit_ceiling


def apply_gravity(vy, dt_mult=1.0):
    vy += GRAVITY * dt_mult
    if vy > MAX_FALL_SPEED:
        vy = MAX_FALL_SPEED
    return vy


def apply_friction(vx, friction=FRICTION):
    vx *= friction
    if abs(vx) < 0.3:
        vx = 0
    return vx


def check_wall_collision(entity_rect, direction, solid_rects):
    """Check if entity is touching a wall on given side. direction: 1=right, -1=left."""
    test_rect = entity_rect.copy()
    test_rect.x += direction * 2
    for solid in solid_rects:
        if test_rect.colliderect(solid):
            return True
    return False
