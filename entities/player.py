"""Player classes: base Player, Sonic, and Tails."""
import pygame
from settings import (
    GRAVITY, MAX_FALL_SPEED, FRICTION, TILE_SIZE,
    SONIC_WALK_SPEED, SONIC_RUN_SPEED, SONIC_SPRINT_SPEED,
    SONIC_JUMP_FORCE, SONIC_WALL_SLIDE_SPEED, SONIC_PUNCH_DAMAGE,
    SONIC_PUNCH_RANGE, SONIC_PUNCH_COOLDOWN, SONIC_SPRINT_THRESHOLD,
    TAILS_WALK_SPEED, TAILS_RUN_SPEED, TAILS_JUMP_FORCE,
    TAILS_FLY_FORCE, TAILS_FLY_DURATION, TAILS_FLY_COOLDOWN,
    TAILS_TAIL_WHIP_DAMAGE, TAILS_TAIL_WHIP_RANGE,
    PLAYER_MAX_HP, RINGS_PER_LIFE, HIT_RING_SCATTER,
    STARTING_LIVES, COMBO_WINDOW, COMBO_HIT1_DAMAGE,
    COMBO_HIT1_DURATION, COMBO_HIT2_DAMAGE, COMBO_HIT2_DURATION,
    COMBO_HIT3_DAMAGE, COMBO_HIT3_DURATION,
)
from engine.physics import apply_gravity, apply_friction, check_wall_collision, AABB
from engine.animation import load_sonic_sprites, load_tails_sprites


class Player:
    """Base player class with shared mechanics."""

    def __init__(self, x, y):
        self.spawn_x = x
        self.spawn_y = y
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.width = 36
        self.height = 52
        self.rect = pygame.Rect(x, y, self.width, self.height)

        self.facing_right = True
        self.on_ground = False
        self.on_wall = False
        self.wall_dir = 0  # -1 left, 1 right
        self.dropping = False
        self.drop_timer = 0

        # Stats (overridden by subclass)
        self.walk_speed = 4.5
        self.run_speed = 9.0
        self.sprint_speed = 14.0
        self.jump_force = -13.5

        # State
        self.hp = PLAYER_MAX_HP
        self.lives = STARTING_LIVES
        self.rings = 0
        self.total_rings = 0
        self.invincible_timer = 0
        self.hurt_timer = 0
        self.dead = False
        self.death_timer = 0
        self.at_door = False

        # Run timer for sprint
        self.run_timer = 0
        self.is_sprinting = False

        # Animation
        self.anim = None  # Set by subclass
        self.anim_state = "idle"

        # Attack
        self.attacking = False
        self.attack_timer = 0
        self.attack_cooldown = 0
        self.attack_rect = None
        self.attack_damage = 0

        # Checkpoint
        self.checkpoint_x = x
        self.checkpoint_y = y

        # Sound queue (drained by game loop)
        self.pending_sounds = []

        # --- Fluid jump helpers ---
        self.coyote_time = 0       # frames you can still jump after leaving ground
        self.jump_buffer = 0       # frames a jump press is remembered before landing
        self.air_jumps_left = 1    # allow one double-jump for more fluid feel
        self.air_jumps_max = 1

    @property
    def center_x(self):
        return self.rect.centerx

    @property
    def center_y(self):
        return self.rect.centery

    def set_checkpoint(self, x, y):
        self.checkpoint_x = x
        self.checkpoint_y = y

    def take_damage(self, damage=1):
        if self.invincible_timer > 0 or self.dead:
            return False

        if self.rings > 0:
            actual_damage = 1
        else:
            actual_damage = 2

        self.hp -= actual_damage

        # Scatter rings
        scattered = min(self.rings, HIT_RING_SCATTER)
        ring_scatter_data = []
        if scattered > 0:
            self.rings -= scattered
            ring_scatter_data = scattered

        self.invincible_timer = 90  # 1.5 seconds at 60fps
        self.hurt_timer = 20

        if self.hp <= 0:
            self.die()

        return ring_scatter_data

    def die(self):
        self.dead = True
        self.death_timer = 120
        self.lives -= 1
        self.vx = 0
        self.vy = -8

    def respawn(self):
        self.dead = False
        self.death_timer = 0
        self.hp = PLAYER_MAX_HP
        self.x = self.checkpoint_x
        self.y = self.checkpoint_y
        self.rect.topleft = (int(self.x), int(self.y))
        self.vx = 0
        self.vy = 0
        self.invincible_timer = 120
        self.hurt_timer = 0

    def collect_ring(self, count=1):
        self.rings += count
        self.total_rings += count
        if self.rings >= RINGS_PER_LIFE:
            self.rings -= RINGS_PER_LIFE
            self.lives += 1
            return True  # Got extra life
        return False

    def update(self, keys, solid_rects, one_way_rects, dt_ms):
        if self.dead:
            self.vy = apply_gravity(self.vy)
            self.y += self.vy
            self.rect.topleft = (int(self.x), int(self.y))
            self.death_timer -= 1
            if self.anim:
                self.anim.play("death")
                self.anim.update(dt_ms)
            return

        # Timers
        if self.invincible_timer > 0:
            self.invincible_timer -= 1
        if self.hurt_timer > 0:
            self.hurt_timer -= 1
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
        if self.drop_timer > 0:
            self.drop_timer -= 1
        if self.jump_buffer > 0:
            self.jump_buffer -= 1

        # Coyote time: count down when player just left ground
        was_on_ground = self.on_ground

        if self.hurt_timer > 0:
            # Can't move during hurt
            self.vx = apply_friction(self.vx)
            self.vy = apply_gravity(self.vy)
            self._resolve_collisions(solid_rects, one_way_rects)
            if self.anim:
                self.anim.play("hurt")
                self.anim.update(dt_ms)
            return

        # Attack update
        if self.attacking:
            self.attack_timer -= 1
            if self.attack_timer <= 0:
                self.attacking = False
                self.attack_rect = None

        # Movement — auto-run: Sonic always runs forward
        # Left/Right steer, Left also flips direction
        pressing_left = keys[pygame.K_LEFT] or keys[pygame.K_a]
        pressing_right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
        running = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]

        if pressing_left and not pressing_right:
            self.facing_right = False
        elif pressing_right and not pressing_left:
            self.facing_right = True
        # else: keep current facing (auto-run continues)

        move_dir = 1 if self.facing_right else -1

        # Speed tier: auto-run at walk speed, shift = run, sustained = sprint
        if running:
            self.run_timer += dt_ms
            if self.run_timer >= SONIC_SPRINT_THRESHOLD:
                target_speed = self.sprint_speed
                self.is_sprinting = True
            else:
                target_speed = self.run_speed
                self.is_sprinting = False
        else:
            target_speed = self.run_speed  # auto-run base is run speed
            self.run_timer = 0
            self.is_sprinting = False

        target_vx = move_dir * target_speed
        self.vx += (target_vx - self.vx) * 0.35  # snappy, instant feel

        # Drop through platform
        self.dropping = False
        if (keys[pygame.K_DOWN] or keys[pygame.K_s]) and self.on_ground and self.drop_timer <= 0:
            self.dropping = True
            self.drop_timer = 15

        # Wall detection
        self.on_wall = False
        self.wall_dir = 0
        if not self.on_ground:
            if move_dir != 0:
                if check_wall_collision(self.rect, move_dir, solid_rects):
                    self.on_wall = True
                    self.wall_dir = move_dir

        # Gravity and wall slide
        if self.on_wall and self.vy > 0:
            self.vy = min(self.vy, SONIC_WALL_SLIDE_SPEED)
            self.vy = apply_gravity(self.vy, 0.3)
        else:
            self.vy = apply_gravity(self.vy)

        # Collision resolution
        self._resolve_collisions(solid_rects, one_way_rects if not self.dropping else [])

        # Coyote time: if just left ground (didn't jump), allow brief window
        if was_on_ground and not self.on_ground and self.vy >= 0:
            self.coyote_time = 8  # ~130ms at 60fps
        elif self.on_ground:
            self.coyote_time = 0
            self.air_jumps_left = self.air_jumps_max
        elif self.coyote_time > 0:
            self.coyote_time -= 1

        # Jump buffer: if buffered and now on ground, auto-jump
        if self.on_ground and self.jump_buffer > 0:
            self.jump_buffer = 0
            self.jump()

        # Auto-jump: jump when approaching a gap (no ground ahead)
        if self.on_ground and abs(self.vx) > 3:
            look_dir = 1 if self.facing_right else -1
            # Check if there's ground 2 tiles ahead
            check_x = self.rect.centerx + look_dir * 80
            feet_y = self.rect.bottom + 12
            has_ground = False
            for s in solid_rects:
                if s.collidepoint(check_x, feet_y):
                    has_ground = True
                    break
            if not has_ground:
                for ow in one_way_rects:
                    if ow.collidepoint(check_x, feet_y):
                        has_ground = True
                        break
            if not has_ground:
                self.jump()

        # Update animation
        self._update_animation(dt_ms)

    def _resolve_collisions(self, solid_rects, one_way_rects):
        # Horizontal
        self.x += self.vx
        self.rect.x = int(self.x)
        for solid in solid_rects:
            if self.rect.colliderect(solid):
                if self.vx > 0:
                    self.rect.right = solid.left
                elif self.vx < 0:
                    self.rect.left = solid.right
                self.x = float(self.rect.x)
                self.vx = 0

        # Vertical
        old_bottom = self.rect.bottom
        self.y += self.vy
        self.rect.y = int(self.y)
        self.on_ground = False

        for solid in solid_rects:
            if self.rect.colliderect(solid):
                if self.vy > 0:
                    self.rect.bottom = solid.top
                    self.on_ground = True
                    self.vy = 0
                elif self.vy < 0:
                    self.rect.top = solid.bottom
                    self.vy = 0
                self.y = float(self.rect.y)

        # One-way platforms
        if self.vy >= 0 and not self.dropping:
            for ow in one_way_rects:
                if self.rect.colliderect(ow) and old_bottom <= ow.top + 6:
                    self.rect.bottom = ow.top
                    self.on_ground = True
                    self.vy = 0
                    self.y = float(self.rect.y)

        self.x = float(self.rect.x)
        self.y = float(self.rect.y)

    def _update_animation(self, dt_ms):
        if not self.anim:
            return

        if self.attacking:
            pass  # Attack anim already set
        elif not self.on_ground:
            if self.on_wall:
                self.anim.play("wall_slide")
            elif self.vy < 0:
                self.anim.play("jump")
            else:
                self.anim.play("fall")
        elif abs(self.vx) > 1:
            self.anim.play("run")
        else:
            self.anim.play("idle")

        self.anim.facing_right = self.facing_right
        self.anim.update(dt_ms)

    def jump(self):
        # Wall jump always has priority
        if self.on_wall and not self.on_ground:
            self.vx = -self.wall_dir * self.run_speed * 0.8
            self.vy = self.jump_force * 0.85
            self.facing_right = self.wall_dir < 0
            self.on_wall = False
            self.air_jumps_left = self.air_jumps_max
            self.pending_sounds.append("jump")
            return True

        # Ground jump (or coyote time)
        if self.on_ground or self.coyote_time > 0:
            self.vy = self.jump_force
            self.on_ground = False
            self.coyote_time = 0
            self.air_jumps_left = self.air_jumps_max
            self.pending_sounds.append("jump")
            return True

        # Double-jump / air jump
        if self.air_jumps_left > 0:
            self.air_jumps_left -= 1
            self.vy = self.jump_force * 0.82
            self.pending_sounds.append("jump")
            return True

        # If none worked, buffer the press
        self.jump_buffer = 8
        return False

    def get_attack_rect(self):
        return self.attack_rect

    def draw(self, surface, cam_offset):
        if self.dead and self.rect.y > self.rect.y + 1000:
            return

        # Invincibility flicker
        if self.invincible_timer > 0 and self.invincible_timer % 4 < 2:
            return

        frame = self.anim.get_frame() if self.anim else None
        sx = int(self.x - cam_offset[0])
        sy = int(self.y - cam_offset[1])

        if frame:
            # Center the sprite on the collision rect
            fw, fh = frame.get_size()
            draw_x = sx + (self.width - fw) // 2
            draw_y = sy + (self.height - fh)
            surface.blit(frame, (draw_x, draw_y))
        else:
            color = (0, 80, 200) if not self.hurt_timer else (255, 100, 100)
            pygame.draw.rect(surface, color, (sx, sy, self.width, self.height))


class Sonic(Player):
    """Sonic: super speed, punching, wall climbing, spin dash."""

    def __init__(self, x, y):
        super().__init__(x, y)
        self.walk_speed = SONIC_WALK_SPEED
        self.run_speed = SONIC_RUN_SPEED
        self.sprint_speed = SONIC_SPRINT_SPEED
        self.jump_force = SONIC_JUMP_FORCE
        self.name = "sonic"

        # Combo system
        self.combo_step = 0
        self.combo_timer = 0

        # Spin dash
        self.spin_dashing = False
        self.spin_charge = 0
        self.spin_active = False

        # Load sprites
        self.anim = load_sonic_sprites()

    def update(self, keys, solid_rects, one_way_rects, dt_ms):
        # Spin dash logic
        if self.spin_dashing and self.on_ground:
            self.spin_charge = min(self.spin_charge + dt_ms, 1000)
            self.vx = 0
            if self.anim:
                self.anim.play("spin_dash")
                self.anim.update(dt_ms)
            return

        if self.spin_active:
            # Moving as a ball
            self.vy = apply_gravity(self.vy)
            self._resolve_collisions(solid_rects, one_way_rects)
            self.vx *= 0.99  # Slight friction
            if abs(self.vx) < 2:
                self.spin_active = False
            if self.anim:
                self.anim.play("spin_ball")
                self.anim.facing_right = self.facing_right
                self.anim.update(dt_ms)
            # Update timers
            if self.invincible_timer > 0:
                self.invincible_timer -= 1
            return

        super().update(keys, solid_rects, one_way_rects, dt_ms)

        # Combo timer
        if self.combo_timer > 0:
            self.combo_timer -= dt_ms
            if self.combo_timer <= 0:
                self.combo_step = 0

    def punch(self):
        if self.attack_cooldown > 0 or self.dead or self.hurt_timer > 0:
            return False

        self.combo_step += 1
        if self.combo_step > 3:
            self.combo_step = 1

        if self.combo_step == 1:
            self.attack_damage = COMBO_HIT1_DAMAGE
            self.attack_timer = 14   # ~230ms at 60fps
            anim_name = "punch_1"
        elif self.combo_step == 2:
            self.attack_damage = COMBO_HIT2_DAMAGE
            self.attack_timer = 16
            anim_name = "punch_2"
        else:
            self.attack_damage = COMBO_HIT3_DAMAGE
            self.attack_timer = 20   # big uppercut
            anim_name = "punch_3"

        self.attacking = True
        self.combo_timer = COMBO_WINDOW
        self.attack_cooldown = 8

        self.pending_sounds.append("punch_hit")

        # Create attack hitbox — generous range and height
        punch_range = 70
        punch_height = 48
        if self.facing_right:
            self.attack_rect = pygame.Rect(
                self.rect.right - 10, self.rect.centery - punch_height // 2,
                punch_range, punch_height
            )
        else:
            self.attack_rect = pygame.Rect(
                self.rect.left - punch_range + 10, self.rect.centery - punch_height // 2,
                punch_range, punch_height
            )

        if self.anim:
            self.anim.play(anim_name)

        return True

    def start_spin_dash(self):
        if self.on_ground and not self.spin_active:
            self.spin_dashing = True
            self.spin_charge = 0

    def release_spin_dash(self):
        if self.spin_dashing:
            self.spin_dashing = False
            speed = 10 + (self.spin_charge / 1000) * 10
            self.vx = speed if self.facing_right else -speed
            self.spin_active = True

    def handle_key_down(self, key, keys):
        if key == pygame.K_SPACE:
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                if self.on_ground:
                    self.start_spin_dash()
                    return True
            if not self.spin_dashing:
                return self.jump()
        elif key in (pygame.K_j, pygame.K_z):
            return self.punch()
        return False

    def handle_key_up(self, key):
        if key == pygame.K_SPACE and self.spin_dashing:
            self.release_spin_dash()
        # Variable jump height
        if key == pygame.K_SPACE and self.vy < 0 and not self.spin_active:
            self.vy *= 0.5


class Tails(Player):
    """Tails: flight, tail whip, hacking."""

    def __init__(self, x, y):
        super().__init__(x, y)
        self.walk_speed = TAILS_WALK_SPEED
        self.run_speed = TAILS_RUN_SPEED
        self.sprint_speed = TAILS_RUN_SPEED + 2
        self.jump_force = TAILS_JUMP_FORCE
        self.name = "tails"

        # Flight
        self.flying = False
        self.fly_timer = 0
        self.fly_cooldown_timer = 0
        self.can_fly = True

        # Load sprites
        self.anim = load_tails_sprites()

    def update(self, keys, solid_rects, one_way_rects, dt_ms):
        # Fly cooldown
        if self.fly_cooldown_timer > 0:
            self.fly_cooldown_timer -= dt_ms
            if self.fly_cooldown_timer <= 0:
                self.can_fly = True

        if self.flying:
            self.fly_timer -= dt_ms
            if self.fly_timer <= 0:
                self.flying = False
                self.can_fly = False
                self.fly_cooldown_timer = TAILS_FLY_COOLDOWN

            # Fly physics: hold space for upward thrust
            if keys[pygame.K_SPACE]:
                self.vy += TAILS_FLY_FORCE * 0.06
                if self.vy < TAILS_FLY_FORCE:
                    self.vy = TAILS_FLY_FORCE
            else:
                self.vy = apply_gravity(self.vy, 0.5)

            # Horizontal movement during flight
            move_dir = 0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                move_dir = -1
            elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                move_dir = 1

            if move_dir != 0:
                self.facing_right = move_dir > 0
                self.vx += move_dir * 0.5
                self.vx = max(-self.run_speed, min(self.vx, self.run_speed))
            else:
                self.vx = apply_friction(self.vx)

            self._resolve_collisions(solid_rects, one_way_rects)

            if self.on_ground:
                self.flying = False

            if self.anim:
                self.anim.play("fly")
                self.anim.facing_right = self.facing_right
                self.anim.update(dt_ms)

            # Timers
            if self.invincible_timer > 0:
                self.invincible_timer -= 1
            return

        super().update(keys, solid_rects, one_way_rects, dt_ms)

        if self.on_ground:
            if not self.can_fly and self.fly_cooldown_timer <= 0:
                self.can_fly = True

    def tail_whip(self):
        if self.attack_cooldown > 0 or self.dead or self.hurt_timer > 0:
            return False

        self.attacking = True
        self.attack_timer = 18  # generous active frames
        self.attack_damage = TAILS_TAIL_WHIP_DAMAGE + 1
        self.attack_cooldown = 12

        self.pending_sounds.append("punch_hit")

        # Wide 360 spin — big hitbox around Tails
        whip_range = 70
        self.attack_rect = pygame.Rect(
            self.rect.centerx - whip_range,
            self.rect.centery - whip_range // 2,
            whip_range * 2,
            whip_range,
        )

        if self.anim:
            self.anim.play("tail_whip")

        return True

    def start_fly(self):
        if not self.on_ground and self.can_fly and not self.flying:
            self.flying = True
            self.fly_timer = TAILS_FLY_DURATION
            self.vy = TAILS_FLY_FORCE * 0.5
            return True
        return False

    def handle_key_down(self, key, keys):
        if key == pygame.K_SPACE:
            if self.on_ground:
                return self.jump()
            else:
                return self.start_fly()
        elif key in (pygame.K_j, pygame.K_z):
            return self.tail_whip()
        return False

    def handle_key_up(self, key):
        # Variable jump height
        if key == pygame.K_SPACE and self.vy < 0 and not self.flying:
            self.vy *= 0.5
