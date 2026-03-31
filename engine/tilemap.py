"""Tile map rendering and collision — chunk-based for performance."""
import pygame
from settings import TILE_SIZE, WORLD_THEMES, SCREEN_WIDTH, SCREEN_HEIGHT

CHUNK_TILES = 16  # tiles per chunk side
CHUNK_PX = CHUNK_TILES * TILE_SIZE


class TileMap:
    def __init__(self, level_data):
        self.width = level_data["width"]
        self.height = level_data["height"]
        self.pixel_width = self.width * TILE_SIZE
        self.pixel_height = self.height * TILE_SIZE
        self.world = level_data.get("world", 1)
        self.theme = WORLD_THEMES.get(self.world, WORLD_THEMES[1])

        self.tile_data = level_data.get("tile_layers", {}).get("main", [])
        self.bg_data = level_data.get("tile_layers", {}).get("background", [])

        # Build collision lists (spatial hash by chunk)
        self.solid_rects = []
        self.one_way_rects = []
        self.hazard_rects = []
        self._solid_grid = {}
        self._oneway_grid = {}
        self._hazard_grid = {}
        self._build_collision()

        # Pre-render in chunks
        self._chunks = {}
        self._bg_chunks = {}
        self._prerender_chunks()

    # ------ collision --------------------------------------------------

    def _cell_key(self, x, y):
        return (x // CHUNK_PX, y // CHUNK_PX)

    def _build_collision(self):
        for row_i, row in enumerate(self.tile_data):
            for col_i, tile_id in enumerate(row):
                if tile_id == 0:
                    continue
                r = pygame.Rect(col_i * TILE_SIZE, row_i * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                key = self._cell_key(r.x, r.y)
                if tile_id == 1:
                    self.solid_rects.append(r)
                    self._solid_grid.setdefault(key, []).append(r)
                elif tile_id == 2:
                    self.one_way_rects.append(r)
                    self._oneway_grid.setdefault(key, []).append(r)
                elif tile_id == 3:
                    self.hazard_rects.append(r)
                    self._hazard_grid.setdefault(key, []).append(r)

    def _near_keys(self, rect, margin=TILE_SIZE * 2):
        x1 = (rect.x - margin) // CHUNK_PX
        y1 = (rect.y - margin) // CHUNK_PX
        x2 = (rect.right + margin) // CHUNK_PX
        y2 = (rect.bottom + margin) // CHUNK_PX
        for cx in range(x1, x2 + 1):
            for cy in range(y1, y2 + 1):
                yield (cx, cy)

    def get_solid_rects_near(self, rect, margin=TILE_SIZE * 3):
        out = []
        for k in self._near_keys(rect, margin):
            out.extend(self._solid_grid.get(k, ()))
        return out

    def get_one_way_near(self, rect, margin=TILE_SIZE * 3):
        out = []
        for k in self._near_keys(rect, margin):
            out.extend(self._oneway_grid.get(k, ()))
        return out

    def get_hazards_near(self, rect, margin=TILE_SIZE * 2):
        out = []
        for k in self._near_keys(rect, margin):
            out.extend(self._hazard_grid.get(k, ()))
        return out

    # ------ rendering --------------------------------------------------

    def _prerender_chunks(self):
        tile_color = self.theme["tile_color"]
        platform_color = self.theme["platform_color"]
        accent = self.theme["accent"]
        hazard_color = (200, 40, 40)
        bg_deco = tuple(min(255, c + 15) for c in self.theme["bg_color"])
        dark = tuple(max(0, c - 20) for c in tile_color)

        cols = (self.width + CHUNK_TILES - 1) // CHUNK_TILES
        rows = (self.height + CHUNK_TILES - 1) // CHUNK_TILES

        for cr in range(rows):
            for cc in range(cols):
                chunk_surf = pygame.Surface((CHUNK_PX, CHUNK_PX), pygame.SRCALPHA)
                bg_surf = pygame.Surface((CHUNK_PX, CHUNK_PX), pygame.SRCALPHA)
                has_main = False
                has_bg = False

                for lr in range(CHUNK_TILES):
                    tr = cr * CHUNK_TILES + lr
                    if tr >= self.height:
                        break
                    for lc in range(CHUNK_TILES):
                        tc = cc * CHUNK_TILES + lc
                        if tc >= self.width:
                            break
                        lx = lc * TILE_SIZE
                        ly = lr * TILE_SIZE

                        # Main tiles
                        tid = self.tile_data[tr][tc] if tr < len(self.tile_data) and tc < len(self.tile_data[tr]) else 0
                        if tid == 1:
                            pygame.draw.rect(chunk_surf, tile_color, (lx, ly, TILE_SIZE, TILE_SIZE))
                            pygame.draw.line(chunk_surf, accent, (lx, ly), (lx + TILE_SIZE, ly), 2)
                            pygame.draw.rect(chunk_surf, dark, (lx, ly, TILE_SIZE, TILE_SIZE), 1)
                            has_main = True
                        elif tid == 2:
                            pygame.draw.rect(chunk_surf, platform_color, (lx, ly, TILE_SIZE, TILE_SIZE // 3))
                            pygame.draw.line(chunk_surf, accent, (lx, ly), (lx + TILE_SIZE, ly), 2)
                            has_main = True
                        elif tid == 3:
                            pygame.draw.rect(chunk_surf, hazard_color, (lx, ly, TILE_SIZE, TILE_SIZE))
                            for sx in range(0, TILE_SIZE, TILE_SIZE // 3):
                                pts = [
                                    (lx + sx, ly + TILE_SIZE),
                                    (lx + sx + TILE_SIZE // 6, ly + TILE_SIZE // 3),
                                    (lx + sx + TILE_SIZE // 3, ly + TILE_SIZE),
                                ]
                                pygame.draw.polygon(chunk_surf, (255, 80, 60), pts)
                            has_main = True

                        # Background deco
                        if tr < len(self.bg_data) and tc < len(self.bg_data[tr]):
                            if self.bg_data[tr][tc] != 0:
                                pygame.draw.rect(bg_surf, bg_deco, (lx, ly, TILE_SIZE, TILE_SIZE))
                                has_bg = True

                if has_main:
                    self._chunks[(cc, cr)] = chunk_surf
                if has_bg:
                    self._bg_chunks[(cc, cr)] = bg_surf

    def _visible_chunks(self, cam_offset):
        """Yield (chunk_col, chunk_row, screen_x, screen_y) for on-screen chunks."""
        ox, oy = cam_offset
        c1 = max(0, int(ox) // CHUNK_PX)
        r1 = max(0, int(oy) // CHUNK_PX)
        c2 = (int(ox) + SCREEN_WIDTH) // CHUNK_PX + 1
        r2 = (int(oy) + SCREEN_HEIGHT) // CHUNK_PX + 1
        for cr in range(r1, r2 + 1):
            for cc in range(c1, c2 + 1):
                sx = cc * CHUNK_PX - int(ox)
                sy = cr * CHUNK_PX - int(oy)
                yield cc, cr, sx, sy

    def draw_background(self, surface, cam_offset):
        for cc, cr, sx, sy in self._visible_chunks(cam_offset):
            chunk = self._bg_chunks.get((cc, cr))
            if chunk:
                surface.blit(chunk, (sx, sy))

    def draw_main(self, surface, cam_offset):
        for cc, cr, sx, sy in self._visible_chunks(cam_offset):
            chunk = self._chunks.get((cc, cr))
            if chunk:
                surface.blit(chunk, (sx, sy))

    def draw_foreground(self, surface, cam_offset):
        pass
