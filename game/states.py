"""Game state machine: menu, playing, paused, boss, cutscene."""
import pygame
import math
import random
from settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE, FPS,
    WORLD_THEMES, LEVEL_NAMES, BOSS_NAMES, STARTING_LIVES,
)
from engine.camera import Camera
from engine.tilemap import TileMap
from engine.particles import ParticleSystem
from entities.player import Sonic, Tails
from entities.enemies import create_enemy
from entities.boss import create_boss
from entities.collectibles import (
    Ring, ScatteredRing, Checkpoint, ExitDoor,
    SteamVent, MovingPlatform,
)
from levels.level_loader import load_level
from game.chase_sequence import ChaseManager
from game.progression import Progression
from ui.hud import HUD
from ui.menus import TitleMenu, CharacterSelect, PauseMenu, GameOverScreen, LevelCompleteScreen
from ui.transitions import TransitionManager
from ui.touch_controls import TouchControls


class GameState:
    TITLE = "title"
    CHAR_SELECT = "char_select"
    PLAYING = "playing"
    BOSS_FIGHT = "boss_fight"
    PAUSED = "paused"
    GAME_OVER = "game_over"
    LEVEL_COMPLETE = "level_complete"
    TRANSITION = "transition"
    BOSS_INTRO = "boss_intro"
    GAME_WON = "game_won"


class Game:
    """Main game class managing all states."""

    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.state = GameState.TITLE
        self.prev_state = None

        self.progression = Progression()
        self.particles = ParticleSystem()
        self.hud = HUD()
        self.transition = TransitionManager()
        self.sound_manager = SoundManager()
        self.touch = TouchControls()

        # UI screens
        self.title_menu = TitleMenu(self.progression.has_save())
        self.char_select = CharacterSelect()
        self.pause_menu = PauseMenu()
        self.game_over_screen = GameOverScreen()
        self.level_complete_screen = None

        # Level state
        self.player = None
        self.tilemap = None
        self.camera = None
        self.enemies = []
        self.boss = None
        self.rings = []
        self.scattered_rings = []
        self.checkpoints = []
        self.exit_door = None
        self.hazards = []
        self.platforms = []
        self.chase_manager = None
        self.level_data = None

        # Timers
        self.level_timer = 0
        self.boss_intro_timer = 0
        self.slow_mo_timer = 0
        self.slow_mo_factor = 1.0

        # Stats for level complete
        self.rings_collected = 0
        self.enemies_defeated = 0

        # Background
        self.bg_stars = [(random.randint(0, SCREEN_WIDTH), random.randint(0, SCREEN_HEIGHT),
                          random.uniform(0.5, 2.0)) for _ in range(100)]

    async def run(self):
        import asyncio
        running = True
        while running:
            dt_ms = self.clock.tick(FPS)
            if dt_ms > 50:
                dt_ms = 50

            # Slow-mo
            if self.slow_mo_timer > 0:
                self.slow_mo_timer -= 1
                dt_ms = int(dt_ms * 0.3)

            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    running = False
                    break
                # Touch → virtual key events
                touch_results = self.touch.handle_event(event)
                for key_code, pressed in touch_results:
                    if pressed:
                        fake = pygame.event.Event(pygame.KEYDOWN, key=key_code)
                        self._handle_event(fake)
                    else:
                        fake = pygame.event.Event(pygame.KEYUP, key=key_code)
                        self._handle_event(fake)
                self._handle_event(event)

            self._update(dt_ms)
            self._draw()
            pygame.display.flip()
            await asyncio.sleep(0)  # Pygbag: yield to browser event loop

        return False

    def _handle_event(self, event):
        if self.state == GameState.TITLE:
            result = self.title_menu.handle_event(event)
            if result == "start":
                self.state = GameState.CHAR_SELECT
                self.progression.reset()
            elif result == "continue":
                self.progression.load()
                self.state = GameState.CHAR_SELECT
                self.char_select.preselected = self.progression.character
            elif result == "quit":
                pygame.event.post(pygame.event.Event(pygame.QUIT))

        elif self.state == GameState.CHAR_SELECT:
            result = self.char_select.handle_event(event)
            if result:
                self.progression.character = result
                self._start_level()

        elif self.state == GameState.PLAYING or self.state == GameState.BOSS_FIGHT:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.prev_state = self.state
                    self.state = GameState.PAUSED
                elif self.player and not self.player.dead:
                    keys = self.touch.get_keys(pygame.key.get_pressed())
                    self.player.handle_key_down(event.key, keys)
            elif event.type == pygame.KEYUP:
                if self.player:
                    self.player.handle_key_up(event.key)

        elif self.state == GameState.PAUSED:
            result = self.pause_menu.handle_event(event)
            if result == "resume":
                self.state = self.prev_state or GameState.PLAYING
            elif result == "restart":
                self._start_level()
            elif result == "quit":
                self.state = GameState.TITLE
                self.title_menu = TitleMenu(self.progression.has_save())

        elif self.state == GameState.GAME_OVER:
            result = self.game_over_screen.handle_event(event)
            if result == "continue":
                self.player.lives = STARTING_LIVES
                self._start_level()
            elif result == "quit":
                self.state = GameState.TITLE
                self.title_menu = TitleMenu(self.progression.has_save())

        elif self.state == GameState.LEVEL_COMPLETE:
            if self.level_complete_screen:
                result = self.level_complete_screen.handle_event(event)
                if result == "next":
                    game_won = self.progression.advance_level()
                    if game_won:
                        self.state = GameState.GAME_WON
                    else:
                        self._start_level()

        elif self.state == GameState.GAME_WON:
            if event.type == pygame.KEYDOWN:
                self.state = GameState.TITLE
                self.title_menu = TitleMenu(True)

    def _update(self, dt_ms):
        if self.state == GameState.TITLE:
            self.title_menu.update(dt_ms)

        elif self.state == GameState.CHAR_SELECT:
            self.char_select.update(dt_ms)

        elif self.state == GameState.TRANSITION:
            if self.transition.update(dt_ms):
                # Transition complete
                if self.level_data and self.level_data.get("is_boss"):
                    self.state = GameState.BOSS_INTRO
                    self.boss_intro_timer = 120
                else:
                    self.state = GameState.PLAYING

        elif self.state == GameState.BOSS_INTRO:
            self.boss_intro_timer -= 1
            if self.boss_intro_timer <= 0:
                self.state = GameState.BOSS_FIGHT

        elif self.state in (GameState.PLAYING, GameState.BOSS_FIGHT):
            self._update_gameplay(dt_ms)

        elif self.state == GameState.LEVEL_COMPLETE:
            if self.level_complete_screen:
                self.level_complete_screen.update(dt_ms)

    def _update_gameplay(self, dt_ms):
        if not self.player or not self.tilemap:
            return

        keys = self.touch.get_keys(pygame.key.get_pressed())

        # Get nearby collision rects
        solid_rects = self.tilemap.get_solid_rects_near(self.player.rect)
        one_way_rects = self.tilemap.get_one_way_near(self.player.rect)

        # Update player
        self.player.update(keys, solid_rects, one_way_rects, dt_ms)

        # Drain player sound queue
        for snd in self.player.pending_sounds:
            self.sound_manager.play(snd)
        self.player.pending_sounds.clear()

        # Sprint speed lines
        if self.player.is_sprinting and not self.player.dead:
            self.particles.emit_speed_lines(
                self.player.rect.left if self.player.facing_right else self.player.rect.right,
                self.player.rect.centery
            )

        # Landing dust
        was = getattr(self, '_was_on_ground', False)
        if self.player.on_ground and not was:
            self.particles.emit_dust(self.player.rect.centerx, self.player.rect.bottom)
        self._was_on_ground = self.player.on_ground

        # Update camera
        if self.camera:
            self.camera.update(self.player.rect, self.player.facing_right)

        # Update chase
        if self.chase_manager:
            self.chase_manager.update(self.camera, self.player, dt_ms)

        # Update platforms
        for plat in self.platforms:
            plat.update(dt_ms)

        # Add platform rects to collision (they act as one-way)
        for plat in self.platforms:
            if isinstance(plat, MovingPlatform):
                one_way_rects.append(plat.rect)
                # Move player with platform
                if self.player.on_ground and self.player.rect.colliderect(
                    plat.rect.inflate(4, 10)):
                    self.player.x += plat.dx
                    self.player.rect.x = int(self.player.x)

        # Update enemies
        for enemy in self.enemies:
            if enemy.active:
                enemy_solids = self.tilemap.get_solid_rects_near(enemy.rect)
                enemy.update(enemy_solids, self.player.rect, dt_ms)

                # Check player attack hitting enemy
                if self.player.attacking and self.player.attack_rect:
                    if enemy.alive and enemy.rect.colliderect(self.player.attack_rect):
                        kb_dir = 1 if self.player.facing_right else -1
                        killed = enemy.take_damage(self.player.attack_damage, kb_dir)
                        self.particles.emit_sparks(enemy.rect.centerx, enemy.rect.centery)
                        self.sound_manager.play("punch_hit")
                        if killed:
                            self.enemies_defeated += 1
                            self.particles.emit_explosion(enemy.rect.centerx, enemy.rect.centery)

                # Check spin dash hitting enemy
                if hasattr(self.player, 'spin_active') and self.player.spin_active:
                    if enemy.alive and enemy.rect.colliderect(self.player.rect):
                        kb_dir = 1 if self.player.facing_right else -1
                        killed = enemy.take_damage(3, kb_dir)
                        self.particles.emit_sparks(enemy.rect.centerx, enemy.rect.centery)
                        if killed:
                            self.enemies_defeated += 1

                # Check enemy hitting player
                if enemy.alive and not self.player.dead and self.player.invincible_timer <= 0:
                    if self.player.rect.colliderect(enemy.rect):
                        scatter = self.player.take_damage(1)
                        if scatter:
                            self._scatter_rings(scatter)
                            self.sound_manager.play("hurt")
                            self.camera.start_shake(6, 12)

                # Check enemy bullets/projectiles
                if hasattr(enemy, 'bullets'):
                    for b in enemy.bullets:
                        if self.player.rect.colliderect(b["rect"]):
                            scatter = self.player.take_damage(1)
                            if scatter:
                                self._scatter_rings(scatter)
                                self.camera.start_shake(4, 8)
                            b["lifetime"] = 0

                if hasattr(enemy, 'bombs'):
                    for b in enemy.bombs:
                        if self.player.rect.colliderect(b["rect"]):
                            scatter = self.player.take_damage(1)
                            if scatter:
                                self._scatter_rings(scatter)
                            b["lifetime"] = 0

                if hasattr(enemy, 'orbs'):
                    for o in enemy.orbs:
                        if self.player.rect.colliderect(o["rect"]):
                            scatter = self.player.take_damage(1)
                            if scatter:
                                self._scatter_rings(scatter)
                            o["lifetime"] = 0

        # Remove dead enemies
        self.enemies = [e for e in self.enemies if e.active]

        # Update boss
        if self.boss and self.state == GameState.BOSS_FIGHT:
            boss_solids = self.tilemap.get_solid_rects_near(self.boss.rect)
            self.boss.update(self.player.rect, boss_solids, dt_ms)

            # Player attack on boss
            if self.player.attacking and self.player.attack_rect:
                if self.boss.alive and self.boss.rect.colliderect(self.player.attack_rect):
                    killed = self.boss.take_damage(self.player.attack_damage)
                    if self.boss.vulnerable:
                        self.particles.emit_sparks(self.boss.rect.centerx, self.boss.rect.centery, 12)
                        self.sound_manager.play("punch_hit")
                        self.camera.start_shake(4, 8)
                    if killed:
                        self.slow_mo_timer = 30
                        self.camera.start_shake(10, 30)
                        self.particles.emit_boss_death(self.boss.rect.centerx, self.boss.rect.centery)
                        self.sound_manager.play("boss_explode")

            # Spin dash on boss
            if hasattr(self.player, 'spin_active') and self.player.spin_active:
                if self.boss.alive and self.boss.rect.colliderect(self.player.rect):
                    killed = self.boss.take_damage(3)
                    if self.boss.vulnerable:
                        self.particles.emit_sparks(self.boss.rect.centerx, self.boss.rect.centery)
                        self.camera.start_shake(4, 8)

            # Boss hitting player
            if self.boss.alive and not self.player.dead:
                # Boss body collision
                if self.player.invincible_timer <= 0 and self.player.rect.colliderect(self.boss.rect):
                    if not self.boss.vulnerable:
                        scatter = self.player.take_damage(2)
                        if scatter:
                            self._scatter_rings(scatter)
                            self.camera.start_shake(6, 12)

                # Boss attack rects
                for ar in self.boss.attack_rects:
                    if self.player.rect.colliderect(ar) and self.player.invincible_timer <= 0:
                        scatter = self.player.take_damage(2)
                        if scatter:
                            self._scatter_rings(scatter)
                            self.camera.start_shake(8, 15)

                # Boss projectiles
                for p in self.boss.projectiles:
                    if self.player.rect.colliderect(p["rect"]) and self.player.invincible_timer <= 0:
                        scatter = self.player.take_damage(1)
                        if scatter:
                            self._scatter_rings(scatter)
                        p["lifetime"] = 0

                # Boss beam
                if hasattr(self.boss, 'beam_rect') and self.boss.beam_rect:
                    if self.player.rect.colliderect(self.boss.beam_rect) and self.player.invincible_timer <= 0:
                        scatter = self.player.take_damage(1)
                        if scatter:
                            self._scatter_rings(scatter)

            # Boss defeated
            if self.boss.defeated:
                self.progression.record_boss_defeated(self.progression.current_world)
                self._level_complete()
                return

        # Update rings
        for ring in self.rings:
            ring.update(dt_ms)
            if not ring.collected and self.player.rect.colliderect(ring.rect):
                ring.collected = True
                self.rings_collected += 1
                extra_life = self.player.collect_ring()
                self.sound_manager.play("ring")

        # Update scattered rings
        for sr in self.scattered_rings:
            sr.update(dt_ms)
            if sr.can_collect() and self.player.rect.colliderect(sr.rect):
                sr.collected = True
                self.player.collect_ring()
        self.scattered_rings = [sr for sr in self.scattered_rings if not sr.collected and sr.lifetime > 0]

        # Update checkpoints
        for cp in self.checkpoints:
            if not cp.activated and self.player.rect.colliderect(cp.rect):
                cp.activate()
                self.player.set_checkpoint(cp.x, cp.y - 20)
                self.sound_manager.play("checkpoint")

        # Hazard collision
        for hazard_rect in self.tilemap.get_hazards_near(self.player.rect):
            if self.player.rect.colliderect(hazard_rect) and self.player.invincible_timer <= 0:
                scatter = self.player.take_damage(1)
                if scatter:
                    self._scatter_rings(scatter)
                    self.player.vy = self.player.jump_force * 0.5

        # Steam vent interaction
        for h in self.hazards:
            if isinstance(h, SteamVent):
                h.update(dt_ms)
                if h.active and self.player.rect.colliderect(h.rect):
                    self.player.vy = h.boost_force
                    self.particles.emit_dust(self.player.rect.centerx, self.player.rect.bottom, 8)

        # Exit door
        if self.exit_door and not self.level_data.get("is_boss"):
            self.exit_door.update(dt_ms)
            if self.player.rect.colliderect(self.exit_door.rect) and not self.player.dead:
                if not self.exit_door.open:
                    self.exit_door.open = True
                    self.sound_manager.play("door_open")
                if self.exit_door.open_progress >= 0.8:
                    self._level_complete()
                    return

        # Player death handling
        if self.player.dead and self.player.death_timer <= 0:
            if self.player.lives > 0:
                self.player.respawn()
                # Reset chase if applicable
                if self.chase_manager and self.chase_manager.active:
                    self._start_level()  # Restart the level
            else:
                self.state = GameState.GAME_OVER

        # Player fell off map
        if self.player.rect.y > self.tilemap.pixel_height + 200:
            if not self.player.dead:
                self.player.die()

        # Update particles
        self.particles.update()

        # Level timer
        self.level_timer += dt_ms / 1000.0

    def _scatter_rings(self, count):
        if isinstance(count, int):
            for i in range(min(count, 20)):
                angle = (2 * math.pi / min(count, 20)) * i
                speed = random.uniform(3, 6)
                vx = math.cos(angle) * speed
                vy = math.sin(angle) * speed - 4
                sr = ScatteredRing(
                    self.player.rect.centerx, self.player.rect.centery,
                    vx, vy
                )
                self.scattered_rings.append(sr)

    def _level_complete(self):
        self.progression.record_time(self.level_timer)
        self.progression.lives = self.player.lives
        self.progression.total_rings += self.rings_collected
        self.progression.save()

        self.level_complete_screen = LevelCompleteScreen(
            self.rings_collected,
            self.enemies_defeated,
            self.level_timer,
            self.level_data.get("name", ""),
        )
        self.state = GameState.LEVEL_COMPLETE

        if self.chase_manager:
            self.chase_manager.stop()
            if self.camera:
                self.camera.stop_auto_scroll()

    def _start_level(self):
        """Load and initialize the current level."""
        world = self.progression.current_world
        level = self.progression.current_level

        self.level_data = load_level(world, level)
        self.tilemap = TileMap(self.level_data)

        # Create player
        spawn = self.level_data["spawn"]
        sx = spawn["x"] * TILE_SIZE
        sy = spawn["y"] * TILE_SIZE
        if self.progression.character == "tails":
            self.player = Tails(sx, sy)
        else:
            self.player = Sonic(sx, sy)

        self.player.lives = self.progression.lives
        self.player.set_checkpoint(sx, sy)

        # Camera
        self.camera = Camera(self.tilemap.pixel_width, self.tilemap.pixel_height)
        self.camera.x = sx - SCREEN_WIDTH // 2
        self.camera.y = sy - SCREEN_HEIGHT // 2

        # Enemies
        self.enemies = []
        for e_data in self.level_data.get("enemies", []):
            ex = e_data["x"] * TILE_SIZE
            ey = e_data["y"] * TILE_SIZE
            enemy = create_enemy(e_data["type"], ex, ey)
            enemy._world = world
            if "patrol_range" in e_data:
                enemy.patrol_range = e_data["patrol_range"] * TILE_SIZE
            self.enemies.append(enemy)

        # Boss
        self.boss = None
        if self.level_data.get("is_boss"):
            bs = self.level_data.get("boss_spawn", {"x": 15, "y": 10})
            bx = bs["x"] * TILE_SIZE
            by = bs["y"] * TILE_SIZE
            self.boss = create_boss(world, bx, by)

            # Lock camera to boss room
            room_rect = pygame.Rect(0, 0,
                                    self.tilemap.pixel_width - SCREEN_WIDTH,
                                    self.tilemap.pixel_height - SCREEN_HEIGHT)
            self.camera.lock_to_rect(room_rect)

        # Rings
        self.rings = []
        Ring._shared_frames = None  # Reset shared frames
        for r_data in self.level_data.get("rings", []):
            rx = r_data["x"] * TILE_SIZE
            ry = r_data["y"] * TILE_SIZE
            count = r_data.get("count", 1)
            spacing = r_data.get("spacing", 1.5) * TILE_SIZE
            pattern = r_data.get("pattern", "line")

            for i in range(count):
                if pattern == "arc":
                    ring_x = rx + i * spacing
                    ring_y = ry - math.sin(i / count * math.pi) * TILE_SIZE * 2
                else:
                    ring_x = rx + i * spacing
                    ring_y = ry
                self.rings.append(Ring(ring_x, ring_y))

        self.scattered_rings = []

        # Checkpoints
        self.checkpoints = []
        for cp_data in self.level_data.get("checkpoints", []):
            cx = cp_data["x"] * TILE_SIZE
            cy = cp_data["y"] * TILE_SIZE
            self.checkpoints.append(Checkpoint(cx, cy))

        # Exit door
        self.exit_door = None
        if self.level_data.get("exit_door"):
            ed = self.level_data["exit_door"]
            self.exit_door = ExitDoor(ed["x"] * TILE_SIZE, ed["y"] * TILE_SIZE)

        # Hazards
        self.hazards = []
        for h_data in self.level_data.get("hazards", []):
            if h_data.get("type") == "steam_vent":
                hx = h_data["x"] * TILE_SIZE
                hy = h_data["y"] * TILE_SIZE
                self.hazards.append(SteamVent(
                    hx, hy,
                    h_data.get("boost_force", -15),
                    h_data.get("interval", 2.0)
                ))

        # Moving platforms
        self.platforms = []
        for p_data in self.level_data.get("platforms", []):
            if p_data.get("type") == "moving":
                mp = MovingPlatform(
                    p_data["x"], p_data["y"],
                    p_data.get("width", 3),
                    p_data.get("path", []),
                    p_data.get("speed", 1.5)
                )
                self.platforms.append(mp)

        # Chase sequence
        self.chase_manager = None
        chase_config = self.level_data.get("chase_sequence")
        if chase_config:
            self.chase_manager = ChaseManager(chase_config)

        # Reset state
        self.level_timer = 0
        self.rings_collected = 0
        self.enemies_defeated = 0
        self.particles.clear()

        # Transition
        self.transition.start(
            f"WORLD {world}-{level}",
            self.level_data.get("name", ""),
            WORLD_THEMES.get(world, WORLD_THEMES[1])["bg_color"]
        )
        self.state = GameState.TRANSITION

    def _draw(self):
        self.screen.fill((10, 10, 20))

        if self.state == GameState.TITLE:
            self._draw_starfield()
            self.title_menu.draw(self.screen)

        elif self.state == GameState.CHAR_SELECT:
            self._draw_starfield()
            self.char_select.draw(self.screen)

        elif self.state == GameState.TRANSITION:
            self.transition.draw(self.screen)

        elif self.state == GameState.BOSS_INTRO:
            self._draw_gameplay()
            # Boss intro overlay
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            self.screen.blit(overlay, (0, 0))

            font_big = pygame.font.SysFont("arial", 48, bold=True)
            font_sub = pygame.font.SysFont("arial", 24)

            boss_name = BOSS_NAMES.get(self.progression.current_world, "BOSS")
            text = font_big.render(boss_name, True, (255, 50, 50))
            text_rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20))

            # Slam effect
            if self.boss_intro_timer > 80:
                scale = 1.0 + (self.boss_intro_timer - 80) * 0.05
                text = pygame.transform.scale(text, (
                    int(text.get_width() * scale),
                    int(text.get_height() * scale)
                ))
                text_rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20))

            self.screen.blit(text, text_rect)

            sub = font_sub.render("GET READY!", True, (255, 200, 100))
            self.screen.blit(sub, sub.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 30)))

        elif self.state in (GameState.PLAYING, GameState.BOSS_FIGHT):
            self._draw_gameplay()

        elif self.state == GameState.PAUSED:
            self._draw_gameplay()
            self.pause_menu.draw(self.screen)

        elif self.state == GameState.GAME_OVER:
            self.game_over_screen.draw(self.screen)

        elif self.state == GameState.LEVEL_COMPLETE:
            if self.level_complete_screen:
                self.level_complete_screen.draw(self.screen)

        elif self.state == GameState.GAME_WON:
            self._draw_win_screen()

    def _draw_starfield(self):
        for x, y, brightness in self.bg_stars:
            c = int(brightness * 100)
            pygame.draw.circle(self.screen, (c, c, c + 20), (int(x), int(y)), 1)

    def _draw_gameplay(self):
        if not self.tilemap or not self.camera:
            return

        cam_offset = self.camera.get_offset()
        world = self.progression.current_world
        theme = WORLD_THEMES.get(world, WORLD_THEMES[1])

        # Background
        self.screen.fill(theme["bg_color"])
        self._draw_parallax_bg(cam_offset, theme)

        # Background tiles
        self.tilemap.draw_background(self.screen, cam_offset)

        # Moving platforms
        for plat in self.platforms:
            plat.draw(self.screen, cam_offset)

        # Hazards
        for h in self.hazards:
            h.draw(self.screen, cam_offset)

        # Main tiles
        self.tilemap.draw_main(self.screen, cam_offset)

        # Rings
        for ring in self.rings:
            ring.draw(self.screen, cam_offset)
        for sr in self.scattered_rings:
            sr.draw(self.screen, cam_offset)

        # Checkpoints
        for cp in self.checkpoints:
            cp.draw(self.screen, cam_offset)

        # Exit door
        if self.exit_door:
            self.exit_door.draw(self.screen, cam_offset)

        # Enemies
        for enemy in self.enemies:
            enemy.draw(self.screen, cam_offset)

        # Boss
        if self.boss:
            self.boss.draw(self.screen, cam_offset)

        # Chase mega threat
        if self.chase_manager:
            self.chase_manager.draw(self.screen, cam_offset)

        # Player
        if self.player:
            self.player.draw(self.screen, cam_offset)

        # Particles
        self.particles.draw(self.screen, cam_offset)

        # HUD
        if self.player:
            self.hud.draw(
                self.screen, self.player.hp, self.player.rings,
                self.player.lives, self.progression.current_world,
                self.progression.current_level, self.level_timer,
                self.level_data.get("name", "") if self.level_data else ""
            )

        # Touch overlay (always on top)
        self.touch.draw(self.screen)

    def _draw_parallax_bg(self, cam_offset, theme):
        """Draw procedural parallax background."""
        bg_color = theme["bg_color"]
        accent = theme["accent"]

        # Far layer: stars/particles
        for i in range(40):
            random.seed(i + self.progression.current_world * 50)
            sx = (i * 73 + 20) % SCREEN_WIDTH
            sy = (i * 47 + 30) % SCREEN_HEIGHT
            # Parallax
            sx = (sx - cam_offset[0] * 0.05) % SCREEN_WIDTH
            sy = (sy - cam_offset[1] * 0.05) % SCREEN_HEIGHT
            brightness = random.randint(60, 150)
            r = min(255, bg_color[0] + brightness)
            g = min(255, bg_color[1] + brightness)
            b = min(255, bg_color[2] + brightness)
            pygame.draw.circle(self.screen, (r, g, b), (int(sx), int(sy)),
                               random.choice([1, 1, 2]))

        # Mid layer: silhouettes
        mid_color = tuple(min(255, c + 20) for c in bg_color)
        for i in range(8):
            random.seed(i + self.progression.current_world * 100 + 999)
            bx = (i * 200 - int(cam_offset[0] * 0.2)) % (SCREEN_WIDTH + 200) - 100
            bw = random.randint(80, 200)
            bh = random.randint(100, 300)
            by = SCREEN_HEIGHT - bh - random.randint(0, 100)
            pygame.draw.rect(self.screen, mid_color, (bx, by, bw, bh))

    def _draw_win_screen(self):
        self.screen.fill((10, 5, 30))
        self._draw_starfield()

        font_big = pygame.font.SysFont("arial", 56, bold=True)
        font_med = pygame.font.SysFont("arial", 28)
        font_sm = pygame.font.SysFont("arial", 20)

        title = font_big.render("CONGRATULATIONS!", True, (255, 220, 50))
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 180)))

        msg = font_med.render("You have defeated the Rogue AI!", True, (200, 200, 220))
        self.screen.blit(msg, msg.get_rect(center=(SCREEN_WIDTH // 2, 260)))

        msg2 = font_med.render("The Astral Carrier is saved!", True, (200, 200, 220))
        self.screen.blit(msg2, msg2.get_rect(center=(SCREEN_WIDTH // 2, 300)))

        stats = font_sm.render(
            f"Total Rings: {self.progression.total_rings}  |  Bosses Defeated: {len(self.progression.bosses_defeated)}",
            True, (180, 180, 200)
        )
        self.screen.blit(stats, stats.get_rect(center=(SCREEN_WIDTH // 2, 380)))

        prompt = font_sm.render("Press any key to return to title", True, (150, 150, 170))
        if pygame.time.get_ticks() % 1000 < 700:
            self.screen.blit(prompt, prompt.get_rect(center=(SCREEN_WIDTH // 2, 480)))


class SoundManager:
    """Sound effects using raw byte buffers — no numpy needed, Pygbag safe."""

    def __init__(self):
        self.sounds = {}
        self.initialized = False
        try:
            pygame.mixer.init(22050, -16, 1, 512)
            self.initialized = True
            self._generate_sounds()
        except Exception:
            pass

    @staticmethod
    def _make_wave(freq, dur_ms, vol=0.3, sweep_to=None):
        """Generate a signed-16 mono waveform as bytes — pure Python, no numpy."""
        import struct, math
        sr = 22050
        n = int(sr * dur_ms / 1000)
        buf = bytearray(n * 2)
        for i in range(n):
            t = i / sr
            if sweep_to:
                f = freq + (sweep_to - freq) * (i / n)
            else:
                f = freq
            sample = math.sin(2 * math.pi * f * t) * vol
            val = max(-32767, min(32767, int(sample * 32767)))
            struct.pack_into('<h', buf, i * 2, val)
        snd = pygame.mixer.Sound(buffer=bytes(buf))
        return snd

    def _generate_sounds(self):
        if not self.initialized:
            return
        try:
            mk = self._make_wave
            self.sounds["jump"]        = mk(800,  80, 0.25, 1400)
            self.sounds["ring"]        = mk(1200, 60, 0.18, 1800)
            self.sounds["punch_hit"]   = mk(180, 120, 0.30)
            self.sounds["hurt"]        = mk(400, 160, 0.25, 180)
            self.sounds["door_open"]   = mk(500, 400, 0.20, 1100)
            self.sounds["boss_explode"]= mk(80,  600, 0.35)
            self.sounds["extra_life"]  = mk(600, 300, 0.20, 1200)
            self.sounds["checkpoint"]  = mk(900, 150, 0.18, 1300)
        except Exception:
            pass

    def play(self, name):
        if self.initialized and name in self.sounds:
            try:
                self.sounds[name].play()
            except Exception:
                pass
