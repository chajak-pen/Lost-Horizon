import os

import pygame

pygame.init() #This intiializes all of the pygame modules

screen_width = 1000 
screen_height = 439 

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def resolve_asset_path(path):
    if not isinstance(path, str) or not path:
        return path
    if os.path.isabs(path):
        return path
    if os.path.exists(path):
        return path
    return os.path.join(BASE_DIR, path)


class Button():
    def __init__(self, x, y, image):
        # load image if given a string path (defer convert_alpha until display is ready)
        if isinstance(image, str):
            self.image = pygame.image.load(resolve_asset_path(image))
            self.image.set_colorkey((255, 255, 255))  # set transparency color
        else:
            self.image = image
        self.rect = self.image.get_rect(topleft=(x, y))
        self.clicked = False
        
    def draw(self):
        surf = pygame.display.get_surface()
        if surf:
            surf.blit(self.image, (self.rect.x, self.rect.y)) #draws the button image at its rectangular position

    def handle_event(self,event):
        action = False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos) and not self.clicked:
                self.clicked = True
                action = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            # reset clicked when the mouse button is released
            self.clicked = False
        return action
    #differentiates the actions based on the button name

class Text():
    def __init__(self,text, x,y, font, centered=False):
        self.text = text
        self.x = x
        self.y = y
        self.font = font
        self.centered = centered
        self.text_surface = self.font.render(self.text, True, (255,255,255)) # renders the text in white colour

    def draw_text(self):
        surf = pygame.display.get_surface()
        if surf:
            x = self.x
            # Center horizontally if centered flag is True
            if self.centered:
                text_width = self.text_surface.get_width()
                x = (surf.get_width() - text_width) // 2
            surf.blit(self.text_surface, (x, self.y)) #draws the text surface at the specified coordinates

class AnimatedText():
    def __init__(self, text, x, y, font, centered=False, fade_in_duration=1.0):
        self.text = text
        self.x = x
        self.y = y
        self.font = font
        self.centered = centered
        self.fade_in_duration = fade_in_duration
        self.elapsed_time = 0.0
        self.text_surface = self.font.render(self.text, True, (255,255,255))
        self.finished = False
    
    def update(self, dt):
        # Update animation timer
        self.elapsed_time += dt
        if self.elapsed_time >= self.fade_in_duration:
            self.elapsed_time = self.fade_in_duration
            self.finished = True
    
    def draw_text(self):
        surf = pygame.display.get_surface()
        if surf:
            # Calculate alpha (transparency) based on elapsed time
            alpha = int(255 * (self.elapsed_time / self.fade_in_duration))
            alpha = max(0, min(255, alpha))  # Clamp between 0 and 255
            
            # Create a copy of the surface with alpha
            animated_surface = self.text_surface.copy()
            animated_surface.set_alpha(alpha)
            
            x = self.x
            # Center horizontally if centered flag is True
            if self.centered:
                text_width = animated_surface.get_width()
                x = (surf.get_width() - text_width) // 2
            
            surf.blit(animated_surface, (x, self.y))

class Background():
    def __init__(self, image_path):
        self.image = pygame.image.load(resolve_asset_path(image_path)).convert()
        # Scale slightly wider than the screen so the parallax scroll has room to move
        screen = pygame.display.get_surface()
        if screen:
            w, h = screen.get_width(), screen.get_height()
            self.image = pygame.transform.scale(self.image, (int(w * 1.30), h))
        else:
            self.image = pygame.transform.scale(self.image, (1300, 600))  # fallback default

    def draw_background(self, screen, parallax_x=0):
        if screen:
            # Background scrolls at 18% of camera speed for a depth illusion
            max_offset = self.image.get_width() - screen.get_width()
            offset = int(min(max_offset, max(0, parallax_x * 0.18)))
            screen.blit(self.image, (-offset, 0))  #draws the background image

class Player():
    def __init__(self, image, x, y, w=26, h=40, orientation='right'): #this class gets the sprite and the desired position of the sprite
        self.original = pygame.image.load(resolve_asset_path(image)).convert_alpha()
        self.original.set_colorkey((0, 0, 0))  # Make black background transparent
        self.image = pygame.transform.scale(self.original, (w, h))
        self.rect = self.image.get_rect(topleft=(x, y))
        self.orientation = orientation

        #load animation frames from folders
        self.idle_images = self.load_animation('images/entities/player/idle/', w, h)
        self.jumping_images = self.load_animation('images/entities/player/jump/', w, h)
        self.running_images = self.load_animation('images/entities/player/run/', w, h)
        self.slide_images = self.load_animation('images/entities/player/slide/', w, h)
        self.wall_slide_images = self.load_animation('images/entities/player/wall_slide/', w, h)

        self.animation_state = 'idle' # can be 'idle', 'running', 'jumping', 'sliding', 'wall_sliding', 'dashing'
        self.current_frame = 0
        self.animation_timer = 0.0
        self.frame_duration = 0.1 # seconds per frame
        self._anim_state_lock = 0.0

        # create a smaller hitbox inset from the visible rect to avoid oversized collisions
        inset_x = max(1, w // 8)
        inset_y = max(1, h // 8)
        self.hitbox = pygame.Rect(self.rect.x + inset_x, self.rect.y + inset_y,
                                  max(1, self.rect.width - inset_x * 2),
                                  max(1, self.rect.height - inset_y * 2))
        
        self.float_powers = 0
        self.invincibility_powers = 0
        self.fire_powers = 0

    def load_animation(self, folder_path, w, h):
        frames = []
        full_path = resolve_asset_path(folder_path)

        if os.path.exists(full_path):
            image_files = [f for f in os.listdir(full_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            image_files.sort()  # Ensure consistent order
            print(f"Found {len(image_files)} animation frames in {folder_path}")

            for filename in image_files:
                try:
                    img_path = os.path.join(full_path, filename)
                    img = pygame.image.load(img_path).convert_alpha()
                    img.set_colorkey((0, 0, 0))  # Make black background transparent
                    img = pygame.transform.scale(img, (w, h))
                    frames.append(img)
                except pygame.error as e:
                    print(f"Error loading image {filename}: {e}")
        else:
            print(f"Animation folder not found: {full_path}")
            
        if not frames:
            frames = [self.image]  # Fallback to a single frame if none loaded

        return frames

    def update_position(self):
        self.rect.topleft = (self.rect.x, self.rect.y)
        # keep hitbox synced with player's world rect
        if hasattr(self, 'hitbox'):
            inset_x = (self.rect.width - self.hitbox.width) // 2
            inset_y = (self.rect.height - self.hitbox.height) // 2
            self.hitbox.topleft = (self.rect.x + inset_x, self.rect.y + inset_y) #update hitbox position

    def update_animation(self, dt, is_moving, jumping, sliding=False, wall_sliding=False, dashing=False):
        # Determine animation state — priority: wall_sliding > sliding > dashing > jumping > running > idle
        if wall_sliding:
            new_state = 'wall_sliding'
        elif sliding:
            new_state = 'sliding'
        elif dashing:
            new_state = 'dashing'
        elif jumping:
            new_state = 'jumping'
        elif is_moving:
            new_state = 'running'
        else:
            new_state = 'idle'

        if self._anim_state_lock > 0.0:
            self._anim_state_lock = max(0.0, self._anim_state_lock - dt)

        # Prevent rapid oscillation between nearby states causing visible flicker.
        if new_state != self.animation_state and self._anim_state_lock > 0.0:
            air_ground_states = {'idle', 'running', 'jumping'}
            if new_state in air_ground_states and self.animation_state in air_ground_states:
                new_state = self.animation_state

        # If state changed, reset frame and timer
        if new_state != self.animation_state:
            self.animation_state = new_state
            self.current_frame = 0
            self.animation_timer = 0.0
            self._anim_state_lock = 0.055

        # Slide and wall-slide use a faster frame rate to look snappier
        frame_dur = 0.07 if self.animation_state in ('sliding', 'wall_sliding', 'dashing') else self.frame_duration

        # Update timer
        self.animation_timer += dt

        if self.animation_state == 'idle':
            frames = self.idle_images
        elif self.animation_state == 'running':
            frames = self.running_images
        elif self.animation_state == 'jumping':
            frames = self.jumping_images
        elif self.animation_state == 'sliding':
            frames = self.slide_images
        elif self.animation_state == 'wall_sliding':
            frames = self.wall_slide_images
        elif self.animation_state == 'dashing':
            frames = self.running_images  # reuse run frames; visuals handled by afterimage in renderer
        else:
            frames = self.idle_images  # Fallback

        if self.animation_timer >= frame_dur and len(frames) > 1:
            steps = int(self.animation_timer // frame_dur)
            self.current_frame = (self.current_frame + steps) % len(frames)
            self.animation_timer -= steps * frame_dur
        
        if frames:
            self.current_frame %= len(frames)
            self.image = frames[self.current_frame]

    def draw_player(self, screen): # this method draws the player onto the screen
        screen.blit(self.image, self.rect.topleft)
    
    def get_image(self):
        if self.orientation == 'right':
            return self.image
        elif self.orientation == 'left':
            return pygame.transform.flip(self.image, True, False)
    
    def lives(self, amount, font):
        lives_text = font.render(f'Lives: {amount}', True, (255,255,255))
        return lives_text
    
    def draw_lives(self, screen, font, amount):
        if screen:
            lives_text = self.lives(amount, font)
            screen.blit(lives_text, (10, 10)) #draws the lives text at the top left corner

class Platform():
    def __init__(self,image_path, x, y, w, h):
        self.base_image = pygame.image.load(resolve_asset_path(image_path)).convert_alpha()
        self.base_image = pygame.transform.scale(self.base_image, (w, h))
        self.image = self.base_image.copy()
        self.rect = self.image.get_rect(topleft=(x, y))
        self.active = True  # platform starts as active
        self.decaying = False
        self.decay_time = 2.5
        self.decay_duration = 1.0
        # If True, platform will start decaying when player steps on it
        self.decay_on_step = False
        # Optional movement boost zone configured per-level.
        self.speed_boost_on_step = False
        self.speed_boost_multiplier = 1.25
        self.speed_boost_duration = 5.0
        self._speed_boost_consumed = False
        self.bounce_on_step = False

    def draw_platform(self, screen):
        if screen and self.active:
            screen.blit(self.image, self.rect.topleft) #draws the platform image at its rectangular position

    def refresh_visual_style(self):
        # Keep all platform types visually identical.
        self.image = self.base_image.copy()
    
    def start_decay(self):
        if not self.decaying and self.decay_duration > 0:
            self.decaying = True
            self.decay_time = self.decay_duration

    def apply_speed_boost(self, player):
        if not self.speed_boost_on_step or self._speed_boost_consumed:
            return False
        player.speed_boost_timer = self.speed_boost_duration
        player.speed_boost_multiplier = self.speed_boost_multiplier
        self._speed_boost_consumed = True
        return True

    def reset_speed_boost_trigger(self):
        self._speed_boost_consumed = False
    
    def update(self, dt):
        if self.decaying:
            self.decay_time -= dt
            if self.decay_time <= 0:
                self.active = False  # platform disappears
                self.decaying = False
        
    
class PlatformManager():
    def __init__(self, platforms=None):
        self.platforms = platforms or []
    
    def add(self, platform):
        self.platforms.append(platform)
    
    def all(self):
        return self.platforms

class Collisions():
    def check_collision(self, player, platform):
        return player.rect.colliderect(platform.rect)

class Camera_Movement():
    def __init__(self, x, y, width, height):
        self.x = float(x)
        self.y = float(y)
        self.width = width
        self.height = height
        self.target_x = x
        self.target_y = y
        self.speed = 5.0
        self.speed_x = 6.2
        self.speed_y = 3.8
        self.look_ahead_px = 110.0
        self.look_ahead_smoothing = 8.0
        self.look_ahead_current = 0.0
    
    def follow(self, target_rect, dt, target_vx=0.0, target_vy=0.0):
        # Look slightly ahead of movement direction for better jump/landing readability.
        desired_look_ahead = max(-self.look_ahead_px, min(self.look_ahead_px, float(target_vx) * 0.18))
        self.look_ahead_current += (desired_look_ahead - self.look_ahead_current) * min(1.0, self.look_ahead_smoothing * dt)
        self.target_x = target_rect.centerx - self.width / 2 + self.look_ahead_current

        # Keep vertical camera movement softer to reduce jitter during short hops.
        vertical_lead = max(-50.0, min(90.0, float(target_vy) * 0.08))
        self.target_y = target_rect.centery - self.height / 2 + vertical_lead

        self.x += (self.target_x - self.x) * self.speed_x * dt
        self.y += (self.target_y - self.y) * self.speed_y * dt
    
    def apply(self, rect):
        offset_rect = rect.copy()
        offset_rect.x -= int(self.x)   
        offset_rect.y -= int(self.y)
        return offset_rect
    
    def clamp_to_world(self, world_width, world_height):
        self.x = max(0, min(self.x, world_width - self.width)) #clamps the camera within the world boundaries
        # Allow camera to go above y=0 (negative y) to follow player jumping high
        self.y = min(self.y, world_height - self.height)

class Coin():
    _spin_cache = {}

    def __init__(self, image_path, x, y, w=20, h=20):
        _cache_key = (image_path, w, h)
        if _cache_key not in Coin._spin_cache:
            base = pygame.image.load(resolve_asset_path(image_path)).convert_alpha()
            base = pygame.transform.scale(base, (w, h))
            widths = [w, max(1,int(w*0.7)), max(1,int(w*0.35)), max(1,int(w*0.05)),
                      max(1,int(w*0.05)), max(1,int(w*0.35)), max(1,int(w*0.7)), w]
            frames = []
            for fw in widths:
                sq = pygame.transform.scale(base, (fw, h))
                pad = pygame.Surface((w, h), pygame.SRCALPHA)
                pad.blit(sq, ((w - fw) // 2, 0))
                frames.append(pad)
            Coin._spin_cache[_cache_key] = frames
        self._spin_frames = Coin._spin_cache[_cache_key]
        self._frame = 0
        self._frame_timer = 0.0
        self._frame_dur = 0.09
        self.image = self._spin_frames[0]
        self.rect = self.image.get_rect(topleft=(x, y))
        self.collected = False

    def update(self, dt):
        self._frame_timer += dt
        if self._frame_timer >= self._frame_dur:
            self._frame_timer = 0.0
            self._frame = (self._frame + 1) % len(self._spin_frames)
            self.image = self._spin_frames[self._frame]

    def draw_coin(self, screen):
        if screen:
            screen.blit(self.image, self.rect.topleft) #draws the coin image at its rectangular position
    
    def collect(self, player):
        return player.rect.colliderect(self.rect)

class CoinManager():
    def __init__(self, coins=None):
        self.coins = coins or []
        self.collected_count = 0
    
    def add(self, coin):
        self.coins.append(coin)
    
    def all(self):
        return self.coins
    
    def draw_coins_collected(self, screen, font, amount):
        if screen:
            coins_text = font.render(f'Coins: {amount}', True, (255,255,0))
            screen.blit(coins_text, (10, 40)) #draws the coins collected text below the lives text

class Melee_Enemy():
    def __init__(self, image_path, x, y, w=26, h=40, orientation='left', idle_folder=None, run_folder=None):
        self.original = pygame.image.load(resolve_asset_path(image_path)).convert_alpha()
        self.image = pygame.transform.scale(self.original, (w, h))
        self.rect = self.image.get_rect(topleft=(x, y))
        self.orientation = orientation
        self.w = w
        self.h = h
        inset_x = max(1, w // 6) # create a smaller hitbox inset from the visible rect to avoid oversized collisions
        inset_y = max(1, h // 6) # create a smaller hitbox inset from the visible rect to avoid oversized collisions
        self.hitbox = pygame.Rect(self.rect.x + inset_x, self.rect.y + inset_y,
                                  max(1, self.rect.width - inset_x * 2),
                                  max(1, self.rect.height - inset_y * 2)) #hitbox for more accurate collision detection
        self.alive = True
        self.max_health = 30
        self.health = self.max_health
        self.stagger_timer = 0.0
        self.stagger_duration = 0.22

        # AI state: 'patrol' moves back and forth on the platform; 'chase' moves toward the player
        self.ai_state = 'patrol'
        self.patrol_speed = 80   # pixels per second while patrolling
        self.chase_speed = 140   # pixels per second while chasing
        # Patrol direction: +1 = right, -1 = left
        self.patrol_direction = 1
        # Facing direction used for sprite flip: +1 = right, -1 = left
        self.facing_direction = -1
        # The platform this enemy stands on — set after spawn in levels.py
        self.platform = None
        # How many pixels above the platform floor the player must be to share the same platform
        self._chase_y_tolerance = 60

        # Physics
        self.y_velocity = 0.0
        self.on_ground = False

        # Animation
        self.idle_images = self._load_animation(idle_folder or 'images/entities/enemy/idle/', w, h)
        self.run_images  = self._load_animation(run_folder or 'images/entities/enemy/run/',  w, h)
        self.anim_state   = 'idle'   # 'idle' or 'run'
        self.current_frame = 0
        self.anim_timer    = 0.0
        self.frame_duration = 0.1  # seconds per frame

    def _load_animation(self, folder_path, w, h):
        frames = []
        full_path = resolve_asset_path(folder_path)
        if os.path.exists(full_path):
            files = sorted(f for f in os.listdir(full_path) if f.lower().endswith(('.png', '.jpg', '.jpeg')))
            for filename in files:
                try:
                    img = pygame.image.load(resolve_asset_path(os.path.join(full_path, filename))).convert_alpha()
                    img.set_colorkey((0, 0, 0))
                    img = pygame.transform.scale(img, (w, h))
                    frames.append(img)
                except pygame.error:
                    pass
        return frames if frames else [self.image]

    def update_animation(self, dt, is_moving):
        new_state = 'run' if is_moving else 'idle'
        if new_state != self.anim_state:
            self.anim_state = new_state
            self.current_frame = 0
            self.anim_timer = 0.0

        frames = self.run_images if self.anim_state == 'run' else self.idle_images
        self.anim_timer += dt
        if self.anim_timer >= self.frame_duration and len(frames) > 1:
            self.current_frame = (self.current_frame + 1) % len(frames)
            self.anim_timer = 0.0
        if frames:
            self.image = frames[self.current_frame]

    def update_ai(self, player, dt):
        """Move the enemy: patrol back and forth on its platform, or chase the player when on the same platform."""
        if not self.alive:
            return
        if self.stagger_timer > 0:
            return

        on_same_platform = False
        if self.platform is not None:
            plat = self.platform
            # Consider the player to be "on" the platform when their feet are near the platform top
            # and their X overlaps the platform width (with some margin for accessibility)
            margin = max(plat.rect.width // 2, 80)
            player_on_plat_x = plat.rect.left - margin <= player.rect.centerx <= plat.rect.right + margin
            player_on_plat_y = abs(player.rect.bottom - plat.rect.top) <= self._chase_y_tolerance
            on_same_platform = player_on_plat_x and player_on_plat_y

        if on_same_platform:
            self.ai_state = 'chase'
        else:
            self.ai_state = 'patrol'

        if self.ai_state == 'chase':
            # Move toward player horizontally and face them
            if player.rect.centerx < self.rect.centerx:
                self.rect.x -= int(self.chase_speed * dt)
                self.facing_direction = -1
            elif player.rect.centerx > self.rect.centerx:
                self.rect.x += int(self.chase_speed * dt)
                self.facing_direction = 1
        else:
            # Patrol: move in current direction and bounce at platform edges
            self.rect.x += int(self.patrol_speed * self.patrol_direction * dt)
            self.facing_direction = self.patrol_direction
            if self.platform is not None:
                plat = self.platform
                # Turn around at platform edges so the enemy stays on its tile
                if self.rect.right >= plat.rect.right:
                    self.rect.right = plat.rect.right
                    self.patrol_direction = -1
                    self.facing_direction = -1
                elif self.rect.left <= plat.rect.left:
                    self.rect.left = plat.rect.left
                    self.patrol_direction = 1
                    self.facing_direction = 1

    def draw_enemy(self, screen):
        if screen:
            screen.blit(self.image, self.rect.topleft) #draws the enemy image at its rectangular position
    
    def update_position(self):
        self.rect.topleft = (self.rect.x, self.rect.y)
        if hasattr(self, 'hitbox'): # keep hitbox synced with enemy's world rect
            inset_x = (self.rect.width - self.hitbox.width) // 2
            inset_y = (self.rect.height - self.hitbox.height) // 2
            self.hitbox.topleft = (self.rect.x + inset_x, self.rect.y + inset_y) #update hitbox position
    
    def get_image(self, player=None):
        # Flip based on movement direction rather than player position
        if self.facing_direction < 0:
            return pygame.transform.flip(self.image, True, False)
        return self.image
    
    def attack(self, player):
        # use hitboxes for a tighter, more accurate collision
        if hasattr(self, 'hitbox') and hasattr(player, 'hitbox'):
            return self.hitbox.colliderect(player.hitbox)
        return self.rect.colliderect(player.rect)
    
    def check_collision_direction(self, player, prev_player_rect):
        
        #Determine collision direction: 'top' if player jumped on head, 'side' if hit from side
        #Returns: 'top', 'side', or None if no collision
        
        if not self.alive:
            return None
        
        # Check if currently colliding
        if hasattr(player, 'hitbox') and hasattr(self, 'hitbox'):
            collided = player.hitbox.colliderect(self.hitbox)
        else:
            collided = player.rect.colliderect(self.rect)
        
        if not collided:
            return None
        
        # Determine collision direction based on player's previous position
        # Use the enemy hitbox top if available (keeps detection consistent with collision check)
        enemy_top = self.hitbox.top if hasattr(self, 'hitbox') else self.rect.top
        # small tolerance to allow forgiving stomps
        tol = 4
        if prev_player_rect.bottom <= enemy_top + tol:
            return 'top'
        else:
            return 'side'

    def take_damage(self, amount):
        if not self.alive:
            return False
        self.health -= amount
        self.stagger_timer = self.stagger_duration
        if self.health <= 0:
            self.alive = False
            return True
        return False
    
class Ranged_Enemy():
    def __init__(self, image_path, x, y, w=26, h=40, orientation='left', cooldown=1.5, bullet_speed=300, bullet_image_path="bullet.png", bullet_w=10, bullet_h=5, direction='left', idle_folder=None, run_folder=None):
        self.cooldown = cooldown
        self.bullet_speed = bullet_speed
        self.bullet_image_path = bullet_image_path
        self.bullet_w = bullet_w
        self.bullet_h = bullet_h
        self.direction = direction
        self.time_since_last_shot = 0.0
        self.original = pygame.image.load(resolve_asset_path(image_path)).convert_alpha()
        self.image = pygame.transform.scale(self.original, (w, h))
        self.rect = self.image.get_rect(topleft=(x, y))
        self.orientation = orientation
        inset_x = max(1, w // 6)
        inset_y = max(1, h // 6)
        self.hitbox = pygame.Rect(self.rect.x + inset_x, self.rect.y + inset_y,
                                  max(1, self.rect.width - inset_x * 2),
                                  max(1, self.rect.height - inset_y * 2))
        self.alive = True
        self.max_health = 30
        self.health = self.max_health
        self.stagger_timer = 0.0
        self.stagger_duration = 0.18
        self.idle_images = self._load_animation(idle_folder or 'images/entities/ranged/world1/idle/', w, h)
        self.run_images = self._load_animation(run_folder or 'images/entities/ranged/world1/run/', w, h)
        self.anim_state = 'idle'
        self.current_frame = 0
        self.anim_timer = 0.0
        self.frame_duration = 0.09
        if self.idle_images:
            self.image = self.idle_images[0]

    def _load_animation(self, folder_path, w, h):
        frames = []
        full_path = resolve_asset_path(folder_path)
        if os.path.exists(full_path):
            files = sorted(f for f in os.listdir(full_path) if f.lower().endswith(('.png', '.jpg', '.jpeg')))
            for filename in files:
                try:
                    img = pygame.image.load(resolve_asset_path(os.path.join(full_path, filename))).convert_alpha()
                    img = pygame.transform.scale(img, (w, h))
                    frames.append(img)
                except pygame.error:
                    pass
        return frames if frames else [self.image]

    def update_animation(self, dt, is_active=False):
        new_state = 'run' if is_active else 'idle'
        if new_state != self.anim_state:
            self.anim_state = new_state
            self.current_frame = 0
            self.anim_timer = 0.0

        frames = self.run_images if self.anim_state == 'run' else self.idle_images
        self.anim_timer += dt
        if self.anim_timer >= self.frame_duration and len(frames) > 1:
            self.current_frame = (self.current_frame + 1) % len(frames)
            self.anim_timer = 0.0
        if frames:
            self.image = frames[self.current_frame]
    
    def draw_enemy(self, screen):
        if screen:
            screen.blit(self.image, self.rect.topleft) #draws the enemy image at its rectangular position
    
    def update_position(self):
        self.rect.topleft = (self.rect.x, self.rect.y)
        if hasattr(self, 'hitbox'):
            inset_x = (self.rect.width - self.hitbox.width) // 2
            inset_y = (self.rect.height - self.hitbox.height) // 2
            self.hitbox.topleft = (self.rect.x + inset_x, self.rect.y + inset_y)
    
    def get_image(self, player):
        if self.rect.x < player.rect.x:
            return self.image
        else:
            return pygame.transform.flip(self.image, True, False)
    
    def check_collision_direction(self, player, prev_player_rect):
        
        #Determine collision direction: 'top' if player jumped on head, 'side' if hit from side
        #Returns: 'top', 'side', or None if no collision
        
        if not self.alive:
            return None
    
        # Check if currently colliding
        if hasattr(player, 'hitbox') and hasattr(self, 'hitbox'):
            collided = player.hitbox.colliderect(self.hitbox)
        else:
            collided = player.rect.colliderect(self.rect)
    
        if not collided:
            return None
    
        # Determine collision direction based on player's previous position
        # Use the enemy hitbox top if available (keeps detection consistent with collision check)
        enemy_top = self.hitbox.top if hasattr(self, 'hitbox') else self.rect.top
        tol = 4
        if prev_player_rect.bottom <= enemy_top + tol:
            return 'top'
        else:
            return 'side'
    
    @property
    def warn_active(self):
        """True when a shot is imminent; used to draw warning indicator."""
        return self.time_since_last_shot >= self.cooldown * 0.65

    def shoot(self, dt, bullet_manager, player=None):
        # Fire bullets using a time-based cooldown.
        if self.stagger_timer > 0:
            return False
        self.time_since_last_shot += dt
        if self.time_since_last_shot >= self.cooldown:
            # Prefer facing player, otherwise use configured direction.
            if player is not None:
                dir_left = self.rect.centerx > player.rect.centerx
            else:
                dir_left = (self.direction == 'left')

            if dir_left:
                bullet_x = self.rect.left - self.bullet_w
                bullet_velocity = -self.bullet_speed
            else:
                bullet_x = self.rect.right
                bullet_velocity = self.bullet_speed

            bullet_y = self.rect.centery - (self.bullet_h // 2)
            new_bullet = Bullet(self.bullet_image_path, bullet_x, bullet_y, self.bullet_w, self.bullet_h, bullet_velocity)
            new_bullet.hitbox = new_bullet.rect.copy()
            try:
                new_bullet.owner = self
            except Exception:
                pass
            try:
                if player is not None and new_bullet.rect.colliderect(player.rect):
                    if bullet_velocity < 0:
                        new_bullet.rect.x = player.rect.left - new_bullet.rect.width - 4
                    else:
                        new_bullet.rect.x = player.rect.right + 4
                    new_bullet.hitbox.topleft = new_bullet.rect.topleft
            except Exception:
                pass
            bullet_manager.add(new_bullet)
            self.time_since_last_shot = 0.0

        # Return whether enemy overlaps player (for contact damage).
        if hasattr(self, 'hitbox') and player is not None and hasattr(player, 'hitbox'):
            return self.hitbox.colliderect(player.hitbox)
        if player is not None:
            return self.rect.colliderect(player.rect)
        return False

    def take_damage(self, amount):
        if not self.alive:
            return False
        self.health -= amount
        self.stagger_timer = self.stagger_duration
        if self.health <= 0:
            self.alive = False
            return True
        return False


class Charger_Enemy(Melee_Enemy):
    """Melee enemy that telegraphs then performs a fast horizontal charge."""

    def __init__(self, image_path, x, y, w=28, h=42, idle_folder=None, run_folder=None):
        super().__init__(image_path, x, y, w=w, h=h, idle_folder=idle_folder, run_folder=run_folder)
        self.patrol_speed = 75
        self.chase_speed = 120
        self.charge_speed = 300
        self.charge_duration = 0.30
        self.charge_timer = 0.0
        self.charge_cooldown = 1.3
        self.charge_cooldown_timer = 0.2
        self.telegraph_duration = 0.40
        self.telegraph_timer = 0.0
        self.charge_direction = 1
        self.warn_active = False
        self.charge_contact_damage = 36

    def update_ai(self, player, dt):
        if not self.alive:
            return
        if self.stagger_timer > 0:
            self.warn_active = False
            return

        if self.charge_cooldown_timer > 0:
            self.charge_cooldown_timer = max(0.0, self.charge_cooldown_timer - dt)

        if self.telegraph_timer > 0:
            self.telegraph_timer = max(0.0, self.telegraph_timer - dt)
            self.ai_state = 'telegraph'
            self.warn_active = True
            self.facing_direction = self.charge_direction
            if self.telegraph_timer == 0:
                self.charge_timer = self.charge_duration
                self.charge_cooldown_timer = self.charge_cooldown
            return

        if self.charge_timer > 0:
            self.charge_timer = max(0.0, self.charge_timer - dt)
            self.ai_state = 'charge'
            self.warn_active = False
            self.rect.x += int(self.charge_speed * self.charge_direction * dt)
            self.facing_direction = self.charge_direction
            if self.platform is not None:
                if self.rect.left <= self.platform.rect.left:
                    self.rect.left = self.platform.rect.left
                    self.charge_timer = 0.0
                elif self.rect.right >= self.platform.rect.right:
                    self.rect.right = self.platform.rect.right
                    self.charge_timer = 0.0
            return

        self.warn_active = False

        can_start_charge = (
            self.platform is not None
            and self.charge_cooldown_timer <= 0
            and abs(player.rect.centerx - self.rect.centerx) <= 210
            and abs(player.rect.bottom - self.platform.rect.top) <= self._chase_y_tolerance
        )
        if can_start_charge:
            self.charge_direction = -1 if player.rect.centerx < self.rect.centerx else 1
            self.telegraph_timer = self.telegraph_duration
            self.ai_state = 'telegraph'
            self.warn_active = True
            self.facing_direction = self.charge_direction
            return

        super().update_ai(player, dt)


class Shield_Enemy(Melee_Enemy):
    """Melee enemy with frontal shield block and telegraphed shield bash."""

    def __init__(self, image_path, x, y, w=28, h=42, idle_folder=None, run_folder=None):
        super().__init__(image_path, x, y, w=w, h=h, idle_folder=idle_folder, run_folder=run_folder)
        self.patrol_speed = 60
        self.chase_speed = 90
        self.warn_active = False
        self.bash_windup = 0.34
        self.bash_windup_timer = 0.0
        self.bash_duration = 0.24
        self.bash_timer = 0.0
        self.bash_speed = 220
        self.bash_direction = 1
        self.bash_cooldown = 1.7
        self.bash_cooldown_timer = 0.5
        self.bash_contact_damage = 28

    def is_front_hit(self, source_x):
        if self.facing_direction >= 0:
            return source_x >= self.rect.centerx
        return source_x <= self.rect.centerx

    def blocks_from_front(self, player):
        return self.is_front_hit(player.rect.centerx)

    def update_ai(self, player, dt):
        if not self.alive:
            return
        if self.stagger_timer > 0:
            self.warn_active = False
            return

        if self.bash_cooldown_timer > 0:
            self.bash_cooldown_timer = max(0.0, self.bash_cooldown_timer - dt)

        if self.bash_windup_timer > 0:
            self.bash_windup_timer = max(0.0, self.bash_windup_timer - dt)
            self.ai_state = 'telegraph'
            self.warn_active = True
            self.facing_direction = self.bash_direction
            if self.bash_windup_timer == 0:
                self.bash_timer = self.bash_duration
                self.bash_cooldown_timer = self.bash_cooldown
            return

        if self.bash_timer > 0:
            self.bash_timer = max(0.0, self.bash_timer - dt)
            self.ai_state = 'bash'
            self.warn_active = False
            self.rect.x += int(self.bash_speed * self.bash_direction * dt)
            self.facing_direction = self.bash_direction
            if self.platform is not None:
                if self.rect.left <= self.platform.rect.left:
                    self.rect.left = self.platform.rect.left
                    self.bash_timer = 0.0
                elif self.rect.right >= self.platform.rect.right:
                    self.rect.right = self.platform.rect.right
                    self.bash_timer = 0.0
            return

        self.warn_active = False
        near_player = abs(player.rect.centerx - self.rect.centerx) <= 130
        same_height = True
        if self.platform is not None:
            same_height = abs(player.rect.bottom - self.platform.rect.top) <= self._chase_y_tolerance
        if near_player and same_height and self.bash_cooldown_timer <= 0:
            self.bash_direction = -1 if player.rect.centerx < self.rect.centerx else 1
            self.bash_windup_timer = self.bash_windup
            self.ai_state = 'telegraph'
            self.warn_active = True
            self.facing_direction = self.bash_direction
            return

        super().update_ai(player, dt)


class Healer_Enemy(Melee_Enemy):
    """Support enemy that periodically heals itself and nearby allies."""

    def __init__(self, image_path, x, y, w=28, h=42, idle_folder=None, run_folder=None):
        super().__init__(image_path, x, y, w=w, h=h, idle_folder=idle_folder, run_folder=run_folder)
        self.heal_cooldown = 5.0
        self.heal_timer = 2.0
        self.heal_amount = 14
        self.heal_radius = 210
        self.aura_active = False

    def update_ai(self, player, dt):
        super().update_ai(player, dt)
        self.aura_active = False
        self.heal_timer = max(0.0, self.heal_timer - dt)

    def try_heal(self, allies):
        if not self.alive or self.heal_timer > 0:
            return 0
        healed = 0
        for ally in allies:
            if ally is self or not getattr(ally, 'alive', False):
                continue
            if not hasattr(ally, 'health') or not hasattr(ally, 'max_health'):
                continue
            dx = ally.rect.centerx - self.rect.centerx
            dy = ally.rect.centery - self.rect.centery
            if (dx * dx + dy * dy) <= (self.heal_radius * self.heal_radius):
                new_hp = min(int(ally.max_health), int(ally.health) + self.heal_amount)
                if new_hp != ally.health:
                    ally.health = new_hp
                    healed += 1
        self.health = min(self.max_health, self.health + max(6, self.heal_amount // 2))
        self.heal_timer = self.heal_cooldown
        self.aura_active = healed > 0
        return healed


class Summoner_Enemy(Melee_Enemy):
    """Enemy that periodically requests melee reinforcements near itself."""

    def __init__(self, image_path, x, y, w=28, h=42, idle_folder=None, run_folder=None):
        super().__init__(image_path, x, y, w=w, h=h, idle_folder=idle_folder, run_folder=run_folder)
        self.summon_cooldown = 7.5
        self.summon_timer = 3.5
        self.summon_count = 1
        self.max_active_summons = 3
        self.summon_request = 0
        self.warn_active = False

    def update_ai(self, player, dt):
        super().update_ai(player, dt)
        if not self.alive:
            self.warn_active = False
            return
        self.summon_timer = max(0.0, self.summon_timer - dt)
        self.warn_active = self.summon_timer <= 0.7

    def consume_summon_request(self, active_spawned):
        if self.summon_timer > 0:
            return 0
        if active_spawned >= self.max_active_summons:
            self.summon_timer = 1.2
            self.warn_active = False
            return 0
        self.summon_timer = self.summon_cooldown
        self.warn_active = False
        return self.summon_count


class Teleport_Enemy(Melee_Enemy):
    """Assassin enemy that teleports near the player with a warning blink."""

    def __init__(self, image_path, x, y, w=28, h=42, idle_folder=None, run_folder=None):
        super().__init__(image_path, x, y, w=w, h=h, idle_folder=idle_folder, run_folder=run_folder)
        self.teleport_cooldown = 4.6
        self.teleport_timer = 2.0
        self.teleport_range = 240
        self.warn_active = False

    def update_ai(self, player, dt):
        super().update_ai(player, dt)
        if not self.alive:
            self.warn_active = False
            return
        self.teleport_timer = max(0.0, self.teleport_timer - dt)
        self.warn_active = self.teleport_timer <= 0.35

    def try_teleport(self, player):
        if self.teleport_timer > 0 or not self.alive:
            return False
        direction = -1 if player.rect.centerx < self.rect.centerx else 1
        target_x = player.rect.centerx - direction * self.teleport_range
        if self.platform is not None:
            target_x = max(self.platform.rect.left + 6, min(target_x, self.platform.rect.right - self.rect.width - 6))
            self.rect.bottom = self.platform.rect.top
        self.rect.x = int(target_x)
        self.facing_direction = direction
        self.teleport_timer = self.teleport_cooldown
        self.warn_active = False
        return True


class Boss():
    def __init__(self, image_path, x, y, health=100, w=90, h=120, min_x=None, max_x=None, speed=90,
                 animation_folder=None, arm_color=(180, 115, 65), wrist_color=(195, 130, 75),
                 shoulder_color=(200, 140, 85), axe_handle_color=(120, 80, 50), axe_head_color=(200, 200, 215)):
        self.frames = []
        if animation_folder:
            self.frames = self._load_animation_frames(animation_folder, w, h)
        try:
            self.original = pygame.image.load(resolve_asset_path(image_path)).convert_alpha()
            self.image = pygame.transform.scale(self.original, (w, h))
        except Exception:
            self.image = pygame.Surface((w, h), pygame.SRCALPHA)
            self.image.fill((160, 40, 40))
            pygame.draw.rect(self.image, (230, 180, 180), self.image.get_rect(), 3)
        if self.frames:
            self.image = self.frames[0]
        self.rect = self.image.get_rect(topleft=(x, y))
        inset_x = max(2, w // 8)
        inset_y = max(2, h // 8)
        self.hitbox = pygame.Rect(
            self.rect.x + inset_x,
            self.rect.y + inset_y,
            max(1, self.rect.width - inset_x * 2),
            max(1, self.rect.height - inset_y * 2),
        )
        self.max_health = max(1, int(health))
        self.health = self.max_health
        self.alive = True
        self.direction = 1          # 1 = facing right, -1 = facing left
        self.speed = speed          # stored for reference
        self.min_x = min_x if min_x is not None else x - 250
        self.max_x = max_x if max_x is not None else x + 250

        # Multi-phase thresholds + behavior table.
        self.phase_thresholds = [0.70, 0.38]
        self.phase_index = 0
        self.phase_table = [
            {
                'label': 'Phase 1',
                'move_speed': 72,
                'attack_cooldown': 1.85,
                'attack_damage': 24,
                'windup': 0.56,
                'telegraph_color': (240, 205, 90),
                'attack_kind': 'cleave',
            },
            {
                'label': 'Phase 2',
                'move_speed': 92,
                'attack_cooldown': 1.42,
                'attack_damage': 30,
                'windup': 0.44,
                'telegraph_color': (255, 160, 90),
                'attack_kind': 'sweep',
            },
            {
                'label': 'Phase 3',
                'move_speed': 112,
                'attack_cooldown': 1.05,
                'attack_damage': 36,
                'windup': 0.34,
                'telegraph_color': (255, 110, 96),
                'attack_kind': 'frenzy',
            },
        ]
        self.attack_windup_timer = 0.0
        self.telegraph_color = (240, 205, 90)
        self.pending_attack_kind = 'cleave'
        self.active_attack_kind = 'cleave'

        # Combat
        self.attack_damage = 25
        self.attack_cooldown = 1.8
        self.attack_cooldown_timer = 1.0   # initial delay before first attack
        self.attack_duration = 0.55
        self.attack_timer = 0.0
        self.attacking = False
        # axe_swing_active is True only during the damage window (middle of swing)
        self.axe_swing_active = False
        self.patrol_direction = 1
        self.anim_timer = 0.0
        self.current_frame = 0
        self.frame_duration = 0.11
        self.arm_color = arm_color
        self.wrist_color = wrist_color
        self.shoulder_color = shoulder_color
        self.axe_handle_color = axe_handle_color
        self.axe_head_color = axe_head_color
        self.axe_scale = 1.0

        # Movement — patrol full arena by default, and target player only when
        # the player is inside the boss platform X range.
        self.MOVE_SPEED = 75

        # Arm / axe geometry
        self.arm_length = max(40, int(w * 0.65))   # shoulder-to-hand distance (px)
        axe_w = max(20, w // 3)
        axe_h = max(30, int(h * 0.45))
        self.axe_image = pygame.Surface((axe_w, axe_h), pygame.SRCALPHA)
        # Handle
        pygame.draw.rect(self.axe_image, self.axe_handle_color,
                         (axe_w // 2 - 2, axe_h // 4, 4, axe_h * 3 // 4))
        # Head
        pygame.draw.polygon(
            self.axe_image, self.axe_head_color,
            [
                (axe_w // 2 + 2, axe_h // 4),
                (axe_w - 2,      axe_h // 4 + 5),
                (axe_w - 6,      axe_h // 4 + 18),
                (axe_w // 2 + 2, axe_h // 4 + 13),
            ],
        )
        # World-space axe hitbox — updated every frame in update()
        self.axe_world_rect = pygame.Rect(0, 0, max(14, axe_w), max(22, axe_h))

        self._apply_phase_tuning(force=True)

    def _load_animation_frames(self, folder_path, w, h):
        frames = []
        full_path = resolve_asset_path(folder_path)
        if os.path.exists(full_path):
            files = sorted(f for f in os.listdir(full_path) if f.lower().endswith(('.png', '.jpg', '.jpeg')))
            for filename in files:
                try:
                    img = pygame.image.load(resolve_asset_path(os.path.join(full_path, filename))).convert_alpha()
                    img = pygame.transform.scale(img, (w, h))
                    frames.append(img)
                except pygame.error:
                    pass
        return frames

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _get_attack_progress(self):
        if not self.attacking or self.attack_duration <= 0:
            return 0.0
        return max(0.0, min(1.0, 1.0 - self.attack_timer / self.attack_duration))

    def _arm_angle(self):
        """Arm angle in degrees (0° = right, clockwise positive)."""
        p = self._get_attack_progress()
        if self.direction >= 0:   # facing right: rest down-right, swing up-right
            return 80 + (-110) * p
        else:                     # facing left: mirror
            return 100 + 110 * p

    def _shoulder_world(self):
        """Shoulder anchor position in world coordinates."""
        w, h = self.rect.width, self.rect.height
        if self.direction >= 0:
            sx = self.rect.left + int(w * 0.72)
        else:
            sx = self.rect.left + int(w * 0.28)
        sy = self.rect.top + int(h * 0.20)
        return sx, sy

    def _update_axe_world_rect(self):
        import math
        sx, sy = self._shoulder_world()
        rad = math.radians(self._arm_angle())
        hx = sx + int(math.cos(rad) * self.arm_length)
        hy = sy + int(math.sin(rad) * self.arm_length)
        base_w = max(14, self.axe_image.get_width())
        base_h = max(22, self.axe_image.get_height())
        if self.active_attack_kind == 'frenzy':
            aw, ah = int(base_w * 1.42), int(base_h * 1.25)
        elif self.active_attack_kind == 'sweep':
            aw, ah = int(base_w * 1.28), int(base_h * 1.16)
        else:
            aw, ah = base_w, base_h
        aw = max(14, int(aw * float(getattr(self, 'axe_scale', 1.0))))
        ah = max(22, int(ah * float(getattr(self, 'axe_scale', 1.0))))
        self.axe_world_rect.size = (aw, ah)
        self.axe_world_rect.topleft = (hx - aw // 2, hy - ah // 2)

    # ------------------------------------------------------------------
    def start_attack(self):
        self.attacking = True
        self.active_attack_kind = self.pending_attack_kind
        self.attack_timer = self.attack_duration
        self.attack_cooldown_timer = self.attack_cooldown

    def _apply_phase_tuning(self, force=False):
        hp_ratio = 0.0 if self.max_health <= 0 else (self.health / float(self.max_health))
        idx = 0
        if hp_ratio <= self.phase_thresholds[1]:
            idx = 2
        elif hp_ratio <= self.phase_thresholds[0]:
            idx = 1
        if (not force) and idx == self.phase_index:
            return
        self.phase_index = idx
        row = self.phase_table[self.phase_index]
        self.MOVE_SPEED = float(row['move_speed'])
        self.attack_cooldown = float(row['attack_cooldown'])
        self.attack_damage = int(row['attack_damage'])
        self.telegraph_color = tuple(row['telegraph_color'])
        self.pending_attack_kind = row['attack_kind']

    def update(self, dt, player=None):
        if not self.alive:
            return

        if self.frames:
            self.anim_timer += dt
            if self.anim_timer >= self.frame_duration:
                self.anim_timer = 0.0
                self.current_frame = (self.current_frame + 1) % len(self.frames)
            self.image = self.frames[self.current_frame]

        self._apply_phase_tuning()

        player_in_arena_x = False
        if player is not None:
            player_in_arena_x = self.min_x <= player.rect.centerx <= self.max_x

        if player is not None and player_in_arena_x:
            # Target the player when they are within the boss platform X range.
            dx = player.rect.centerx - self.rect.centerx
            if abs(dx) > 4:
                move_dir = 1 if dx > 0 else -1
                self.rect.x += int(move_dir * self.MOVE_SPEED * dt)
                self.patrol_direction = move_dir
            self.direction = -1 if dx < 0 else 1
        else:
            # Keep moving across the full boss platform regardless of player position.
            self.rect.x += int(self.patrol_direction * self.MOVE_SPEED * dt)
            self.direction = self.patrol_direction

        # Clamp to patrol bounds
        if self.rect.left < self.min_x:
            self.rect.left = self.min_x
            self.patrol_direction = 1
        elif self.rect.right > self.max_x:
            self.rect.right = self.max_x
            self.patrol_direction = -1

        # Cooldown countdown
        if self.attack_cooldown_timer > 0:
            self.attack_cooldown_timer = max(0.0, self.attack_cooldown_timer - dt)

        # Attack state machine
        if self.attack_windup_timer > 0:
            self.attack_windup_timer = max(0.0, self.attack_windup_timer - dt)
            self.axe_swing_active = False
            if self.attack_windup_timer <= 0:
                self.start_attack()
        elif self.attacking:
            self.attack_timer -= dt
            progress = self._get_attack_progress()
            # Phase-specific damage windows improve readability and pacing.
            if self.active_attack_kind == 'frenzy':
                self.axe_swing_active = 0.18 <= progress <= 0.92
            elif self.active_attack_kind == 'sweep':
                self.axe_swing_active = 0.20 <= progress <= 0.86
            else:
                self.axe_swing_active = 0.25 <= progress <= 0.80
            if self.attack_timer <= 0:
                self.attacking = False
                self.attack_timer = 0.0
                self.axe_swing_active = False
        elif player is not None and self.attack_cooldown_timer <= 0:
            if player_in_arena_x and abs(self.rect.centerx - player.rect.centerx) < 200:
                row = self.phase_table[self.phase_index]
                self.pending_attack_kind = row['attack_kind']
                self.attack_windup_timer = float(row['windup'])
        else:
            self.axe_swing_active = False

        self._update_axe_world_rect()
        self.update_position()

    def update_position(self):
        inset_x = (self.rect.width - self.hitbox.width) // 2
        inset_y = (self.rect.height - self.hitbox.height) // 2
        self.hitbox.topleft = (self.rect.x + inset_x, self.rect.y + inset_y)

    def get_image(self):
        if self.direction < 0:
            return pygame.transform.flip(self.image, True, False)
        return self.image

    def draw(self, screen, camera):
        import math
        boss_offset = camera.apply(self.rect)
        screen.blit(self.get_image(), boss_offset)

        if self.attack_windup_timer > 0:
            cx = self.rect.centerx - int(camera.x)
            cy = self.rect.centery - int(camera.y)
            radius = int(58 + (self.phase_index * 10) + self.attack_windup_timer * 24)
            pygame.draw.circle(screen, self.telegraph_color, (cx, cy), radius, 3)

        try:
            ph_font = pygame.font.SysFont("Arial", 18, bold=True)
            ph = ph_font.render(self.phase_table[self.phase_index]['label'], True, self.telegraph_color)
            screen.blit(ph, (boss_offset.x + (self.rect.width - ph.get_width()) // 2, boss_offset.y - 20))
        except Exception:
            pass

        # Convert world shoulder + hand positions to screen space
        sx_w, sy_w = self._shoulder_world()
        rad = math.radians(self._arm_angle())
        hx_w = sx_w + int(math.cos(rad) * self.arm_length)
        hy_w = sy_w + int(math.sin(rad) * self.arm_length)
        cx = int(camera.x)
        cy = int(camera.y)
        sx_s = sx_w - cx
        sy_s = sy_w - cy
        hx_s = hx_w - cx
        hy_s = hy_w - cy

        # Draw arm bone
        pygame.draw.line(screen, self.arm_color, (sx_s, sy_s), (hx_s, hy_s), 7)
        pygame.draw.circle(screen, self.shoulder_color, (sx_s, sy_s), 5)   # shoulder
        pygame.draw.circle(screen, self.wrist_color, (hx_s, hy_s), 4)   # wrist

        # Rotate axe so its handle points along the arm direction
        axe_rot = pygame.transform.rotate(self.axe_image, -(self._arm_angle() + 90))
        axe_rect_s = axe_rot.get_rect(center=(hx_s, hy_s))
        screen.blit(axe_rot, axe_rect_s)

    def take_damage(self, amount):
        if not self.alive:
            return False
        self.health -= amount
        if self.health <= 0:
            self.health = 0
            self.alive = False
            return True
        return False

class melee_EnemyManager():
    def __init__(self, melee_enemies=None):
        self.enemies = melee_enemies or []
    
    def add(self, melee_enemy):
        self.enemies.append(melee_enemy)
    
    def all(self):
        return self.enemies

class ranged_EnemyManager():
    def __init__(self, ranged_enemies=None):
        self.enemies = ranged_enemies or []
    
    def add(self, ranged_enemy):
        self.enemies.append(ranged_enemy)
    
    def all(self):
        return self.enemies
    
class Gun():
    def __init__(self, image_path, x, y, w=10, h=5, orientation='left', owner=None):
        self.image = pygame.image.load(resolve_asset_path(image_path)).convert_alpha()
        self.image = pygame.transform.scale(self.image, (w,h))
        self.rect = self.image.get_rect(topleft=(x,y))
        self.orientation = orientation
        inset_x = max(1, w // 6) # create a smaller hitbox inset from the visible rect to avoid oversized collisions
        inset_y = max(1, h // 6) # create a smaller hitbox inset from the visible rect to avoid oversized collisions
        self.hitbox = pygame.Rect(self.rect.x + inset_x, self.rect.y + inset_y,
                                  max(1, self.rect.width - inset_x * 2),
                                  max(1, self.rect.height - inset_y * 2)) #hitbox for more accurate collision detection
        self.owner = owner

    def draw_gun(self, screen):
        if screen:
            screen.blit(self.image, self.rect.topleft) #draws the gun image at its rectangular position
    
    def update_position(self):
        self.rect.topleft = (self.rect.x, self.rect.y)
        if hasattr(self, 'hitbox'): # keep hitbox synced with gun's world rect
            inset_x = (self.rect.width - self.hitbox.width) // 2
            inset_y = (self.rect.height - self.hitbox.height) // 2
            self.hitbox.topleft = (self.rect.x + inset_x, self.rect.y + inset_y) #update hitbox position
    
    def get_image(self, player):
        if self.rect.x < player.rect.x:
            return self.image
        else:
            return pygame.transform.flip(self.image, True, False)

class gunManager():
    def __init__(self, guns=None):
        self.guns = guns or []
    
    def add(self, gun):
        self.guns.append(gun)
    
    def all(self):
        return self.guns

class Bullet():
    def __init__(self, image_path, x, y, w=10, h=5, velocity=300):
        self.image = pygame.image.load(resolve_asset_path(image_path)).convert_alpha()
        self.image = pygame.transform.scale(self.image, (w, h))
        self.rect = self.image.get_rect(topleft=(x, y))
        self.velocity = velocity
        # add a small hitbox for the bullet equal to its rect by default
        self.hitbox = self.rect.copy()
    
    def draw_bullet(self, screen):
        if screen:
            screen.blit(self.image, self.rect.topleft) #draws the bullet image at its rectangular position
    
    def update(self, dt):
        # keep sub-pixel movement using float accumulation if needed; simple int movement is fine here
        self.rect.x += int(self.velocity * dt) # updates bullet position based on its velocity and delta time
        # keep hitbox synced
        if hasattr(self, 'hitbox'):
            self.hitbox.topleft = self.rect.topleft

class BulletManager():
    def __init__(self, bullets=None):
        self.bullets = bullets or []
    
    def add(self, bullet):
        self.bullets.append(bullet)
    
    def all(self):
        return self.bullets

    def remove(self, bullet):
        for b in self.bullets:
            if b == bullet:
                self.bullets.remove(b)

class Finish():
    def __init__(self, image, x, y, w, h):
        self.image = pygame.image.load(resolve_asset_path(image)).convert_alpha()
        self.image = pygame.transform.scale(self.image, (w, h))
        self.image.set_colorkey((255, 255, 255))  # set transparency color
        self.rect = self.image.get_rect(topleft=(x, y))
    
    def draw_finish(self, screen):
        if screen:
            screen.blit(self.image, self.rect.topleft) #draws the finish image at its rectangular position
    
    def check_reach(self, player):
        return player.rect.colliderect(self.rect)

class Timer():
    def __init__(self):
        self.start_ticks = pygame.time.get_ticks() # gets the current time in milliseconds
        self.paused = False
        self.paused_ticks = 0
    
    def get_elapsed_time(self):
        if self.paused:
            elapsed_seconds = self.paused_ticks / 1000
        else:
            elapsed_ticks = pygame.time.get_ticks() - self.start_ticks
            elapsed_seconds = elapsed_ticks / 1000
        return elapsed_seconds
    
    def draw_timer(self, screen, font):
        if screen:
            elapsed_time = self.get_elapsed_time()
            timer_text = font.render(f'Time: {elapsed_time:.2f}s', True, (255,255,255))
            screen.blit(timer_text, (850, 10)) #draws the timer text at the top right corner
    
    def reset(self):
        self.start_ticks = pygame.time.get_ticks() # resets the start time to the current time
        self.paused = False

    def pause_timer(self):
        if not self.paused:
            self.paused_ticks = pygame.time.get_ticks() - self.start_ticks
            self.paused = True
    
    def resume_timer(self):
        if self.paused:
            self.start_ticks = pygame.time.get_ticks() - self.paused_ticks
            self.paused = False

class Score():
    def __init__(self, time, coins_collected, difficulty_multiplier=1):
        self.time = time
        self.coins_collected = coins_collected
        self.difficulty_multiplier = difficulty_multiplier
        self.total_score = 0
        self.bonus_score = 0

    def add_bonus(self, amount):
        self.bonus_score += max(0, int(amount))
        self.total_score = self.bonus_score
        return self.total_score

    def calculate_score(self, time, coins_collected, enemies_killed, death_count=0):
        clear_bonus = 2500
        time_bonus = max(600, 3400 - int(max(0.0, float(time)) * 18))
        coin_bonus = min(2400, int(max(0, int(coins_collected)) * 110))
        combat_bonus = min(1800, int(max(0, int(enemies_killed)) * 85))
        death_penalty = min(1800, int(max(0, int(death_count)) * 180))
        raw_score = clear_bonus + time_bonus + coin_bonus + combat_bonus + self.bonus_score - death_penalty
        score = max(0, int(raw_score * self.difficulty_multiplier))
        self.total_score = score
        return score

    def display_score(self, screen, font):
        if screen:
            score_value = self.total_score if self.total_score else self.calculate_score(self.time, self.coins_collected, 0, 0)
            score_text = font.render(f'Score: {score_value}', True, (255, 215, 0))
            screen.blit(score_text, (screen_width // 2 - 50, screen_height // 2 - 20)) #draws the score text at the center of the screen

class DamageNumber():
    """Floating text that appears on screen when damage is dealt or items collected."""
    _font = None

    @classmethod
    def _get_font(cls):
        if cls._font is None:
            cls._font = pygame.font.SysFont("Arial", 22, bold=True)
        return cls._font

    def __init__(self, text, world_x, world_y, color=(255, 60, 60)):
        self.text = text
        self.x = float(world_x)
        self.y = float(world_y)
        self.color = color
        self.lifetime = 1.0
        self.elapsed = 0.0
        self.speed_y = -55  # floats upward in world space
        self.alive = True

    def update(self, dt):
        self.elapsed += dt
        self.y += self.speed_y * dt
        if self.elapsed >= self.lifetime:
            self.alive = False

    def draw(self, screen, camera):
        if not self.alive or not screen:
            return
        alpha = max(0, int(255 * (1.0 - self.elapsed / self.lifetime)))
        surf = DamageNumber._get_font().render(self.text, True, self.color)
        surf.set_alpha(alpha)
        screen_x = int(self.x - camera.x) - surf.get_width() // 2
        screen_y = int(self.y - camera.y)
        screen.blit(surf, (screen_x, screen_y))


class DeathParticle():
    """Small coloured particle that flies outward when an enemy dies."""
    def __init__(self, world_x, world_y, vx, vy, color=(255, 100, 30)):
        self.world_x = float(world_x)
        self.world_y = float(world_y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.color = color
        self.lifetime = 0.55
        self.elapsed = 0.0
        self.radius = 4
        self.alive = True

    def update(self, dt):
        self.elapsed += dt
        if self.elapsed >= self.lifetime:
            self.alive = False
            return
        self.world_x += self.vx * dt
        self.world_y += self.vy * dt
        self.vy += 600 * dt  # gravity pulls particles down

    def draw(self, screen, camera):
        if not self.alive or not screen:
            return
        alpha = max(0, int(255 * (1.0 - self.elapsed / self.lifetime)))
        sx = int(self.world_x - camera.x)
        sy = int(self.world_y - camera.y)
        surf = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*self.color, alpha), (self.radius, self.radius), self.radius)
        screen.blit(surf, (sx - self.radius, sy - self.radius))


class Checkpoint():
    """A mid-level respawn flag the player can activate by touching."""
    def __init__(self, x, y, w=18, h=44):
        self.rect = pygame.Rect(x, y, w, h)
        self.activated = False

    def check_activate(self, player):
        if not self.activated and player.rect.colliderect(self.rect):
            self.activated = True
            return True
        return False

    def draw(self, screen, camera):
        sx = self.rect.x - int(camera.x)
        sy = self.rect.y - int(camera.y)
        cx = sx + self.rect.w // 2
        pygame.draw.line(screen, (200, 200, 200), (cx, sy), (cx, sy + self.rect.h), 3)
        flag_col = (50, 220, 100) if self.activated else (160, 160, 160)
        flag_pts = [(cx, sy), (cx + 15, sy + 8), (cx, sy + 16)]
        pygame.draw.polygon(screen, flag_col, flag_pts)
        pygame.draw.circle(screen, (200, 200, 200), (cx, sy + self.rect.h), 4)


class Float_Power():
    def __init__(self, image_path, x, y, w=30, h=30):
        self.image = pygame.image.load(resolve_asset_path(image_path)).convert_alpha()
        self.image = pygame.transform.scale(self.image, (w, h))
        self.image.set_colorkey((255, 255, 255))  # set transparency color
        self.rect = self.image.get_rect(topleft=(x, y))
        self.collected = False
    
    def draw_powerup(self, screen):
        if screen:
            screen.blit(self.image, self.rect.topleft) #draws the power-up image at its rectangular position
    
    def collect(self, player):
        return player.rect.colliderect(self.rect)
    
    def use_power(self, player):
        # Mark the player as having the float power available (activation handled by game loop)
        # Setting a collected flag leaves activation timing to code that calls this method.
        try:
            player.float_power_collected = True
        except Exception:
            player.float_power_collected = True
        # Optionally the game can call this method with direct activation by setting
        # player.float_power_active = True and player.float_time_remaining = <seconds>

class Invincibility_Power():
    def __init__(self, image_path, x, y, w=30, h=30):
        self.image = pygame.image.load(resolve_asset_path(image_path)).convert_alpha()
        self.image = pygame.transform.scale(self.image, (w, h))
        self.image.set_colorkey((255, 255, 255))  # set transparency color
        self.rect = self.image.get_rect(topleft=(x, y))
        self.collected = False
    
    def draw_powerup(self, screen):
        if screen:
            screen.blit(self.image, self.rect.topleft) #draws the power-up image at its rectangular position
    
    def collect(self, player):
        return player.rect.colliderect(self.rect)
    
    def use_power(self, player):
        # Mark the player as having the invincibility power available (activation handled by game loop)
        try:
            player.invincibility_collected = True
        except Exception:
            player.invincibility_collected = True
        # Activation and duration are controlled by the game loop (e.g. set player.invincibility_active)

class Fire_Power():
    def __init__(self, image_path, x, y, w=30, h=30):
        self.image = pygame.image.load(resolve_asset_path(image_path)).convert_alpha()
        self.image = pygame.transform.scale(self.image, (w, h))
        self.image.set_colorkey((255, 255, 255))  # set transparency color
        self.rect = self.image.get_rect(topleft=(x, y))
        self.collected = False

    def draw_powerup(self, screen, camera):
        if not self.collected and screen:
            screen.blit(self.image, camera.apply()) #draws the power-up image at its rectangular position

    def collect(self, player):
        if self.collected:
            return False
        # Use player's rect for collision
        if self.rect.colliderect(player.rect):
            self.collected = True
            # Set flags on the player (tutorial code expects these attributes)
            player.fire_power_collected = True
            # You might want to set some UI hint timestamp here too
            return True
        return False
    
    def use_power(self, player):
        try:
            player.fire_power_collected = True
        except:
            player.fire_power_collected = True
        # Additional logic for fire power can be implemented here

class FireProjectile():
    def __init__(self, x, y, vx, vy, w=10, h=10, damage=15):
        #load or create an orange circle
        
        self.image = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (255, 140, 0), (w//2, h//2), w//2)
        
        self.rect = self.image.get_rect(topleft=(x, y))
        self.vx = vx #velocity in x direction
        self.vy = vy #velocity in y direction
        self.gravity = 750 #same as people gravity for consistency
        self.bounce_damping = 0.8 #lose 20% speed on bounce
        self.alive = True
        self.damage = damage
    
    def update(self, dt, platforms, world_width, world_height):
        self.vy += self.gravity * dt

        #update position
        self.rect.x += int(self.vx * dt)
        self.rect.y += int(self.vy * dt)

        #bounce off walls
        if self.rect.left <= 0:
            self.rect.left = 0
            self.vx = -self.vx * self.bounce_damping
        elif self.rect.right >= world_width:
            self.rect.right = world_width
            self.vx = -self.vx * self.bounce_damping
        
        # Bounce off platforms (top/bottom)
        for plat in platforms:
            if self.rect.colliderect(plat.rect):
                # Hit bottom of platform
                if self.vy > 0 and self.rect.bottom <= plat.rect.bottom + 10:
                    self.rect.bottom = plat.rect.top
                    self.vy = -self.vy * self.bounce_damping
                # Hit top of platform
                elif self.vy < 0 and self.rect.top >= plat.rect.top - 10:
                    self.rect.top = plat.rect.bottom
                    self.vy = -self.vy * self.bounce_damping
        
        # Die if falls off bottom
        if self.rect.top > world_height:
            self.alive = False

    def draw(self, screen, camera):
        if screen and self.alive:
            offset_rect = camera.apply(self.rect)
            screen.blit(self.image, offset_rect)
    
    def check_enemy_collision(self, enemy):
        #Returns True if projectile hit enemy.
        return self.rect.colliderect(enemy.rect)

class Wall():
    def __init__(self, image_path, x, y, w, h):
        self.image = pygame.image.load(resolve_asset_path(image_path)).convert_alpha()
        self.image = pygame.transform.scale(self.image, (w, h))
        self.rect = self.image.get_rect(topleft=(x, y))
    
    def draw_wall(self, screen, camera):
        if screen:
            offset_rect = camera.apply(self.rect)
            screen.blit(self.image, offset_rect)


class RotatingFirewall():
    """A rotating firewall obstacle that spins around a center point."""
    def __init__(self, cx, cy, blade_width=80, blade_height=20, rotation_speed=180, animation_folder='images/hazards/firewall/'):
        """
        Initialize a rotating firewall.
        
        Args:
            cx: center X position in world coordinates
            cy: center Y position in world coordinates
            blade_width: width of the rotating blade
            blade_height: height of the rotating blade
            rotation_speed: degrees per second the blade rotates
        """
        self.center_x = cx
        self.center_y = cy
        self.blade_width = blade_width
        self.blade_height = blade_height
        self.rotation_speed = rotation_speed  # degrees per second
        self.angle = 0  # current rotation angle in degrees

        self.frames = self._load_animation_frames(animation_folder, blade_width, blade_height)
        self.current_frame = 0
        self.anim_timer = 0.0
        self.frame_duration = 0.08
        self.base_image = self.frames[0] if self.frames else self._build_default_blade(blade_width, blade_height)
        self.image = self.base_image.copy()
        # Create a rect based on the unrotated image, will update dynamically
        self.rect = self.image.get_rect(center=(cx, cy))
        
        # For collision detection, we'll use a rotated rect approximation
        self._update_rotated_image()
    
    def _update_rotated_image(self):
        """Rotate the blade image based on current angle."""
        # Rotate the base image
        self.image = pygame.transform.rotate(self.base_image, -self.angle)  # Negative for clockwise
        self.rect = self.image.get_rect(center=(self.center_x, self.center_y))

    def _build_default_blade(self, blade_width, blade_height):
        image = pygame.Surface((blade_width, blade_height), pygame.SRCALPHA)
        pygame.draw.rect(image, (255, 90, 20), (0, 2, blade_width, blade_height - 4), border_radius=max(4, blade_height // 3))
        pygame.draw.rect(image, (255, 220, 90), (blade_width // 6, blade_height // 4, blade_width * 2 // 3, blade_height // 2), border_radius=max(3, blade_height // 4))
        return image

    def _load_animation_frames(self, folder_path, blade_width, blade_height):
        frames = []
        full_path = resolve_asset_path(folder_path)
        if os.path.exists(full_path):
            files = sorted(f for f in os.listdir(full_path) if f.lower().endswith(('.png', '.jpg', '.jpeg')))
            for filename in files:
                try:
                    img = pygame.image.load(resolve_asset_path(os.path.join(full_path, filename))).convert_alpha()
                    img = pygame.transform.scale(img, (blade_width, blade_height))
                    frames.append(img)
                except pygame.error:
                    pass
        return frames
    
    def update(self, dt):
        """Update the rotation angle based on elapsed time."""
        if self.frames:
            self.anim_timer += dt
            if self.anim_timer >= self.frame_duration:
                self.current_frame = (self.current_frame + 1) % len(self.frames)
                self.base_image = self.frames[self.current_frame]
                self.anim_timer = 0.0
        self.angle += self.rotation_speed * dt
        self.angle %= 360  # Keep angle in 0-360 range
        self._update_rotated_image()
    
    def draw(self, screen, camera):
        """Draw the rotating firewall on the screen."""
        if screen:
            offset_rect = camera.apply(self.rect)
            screen.blit(self.image, offset_rect)
    
    def check_collision(self, player):
        """Check if the player collides with the firewall blade."""
        # Use pixel-perfect collision detection with alpha transparency
        # For a simple approximation, check if player rect overlaps with firewall rect
        return self.rect.colliderect(player.rect)
    
    def get_collision_mask(self):
        """Return a collision mask for pixel-perfect collisions."""
        # Create a mask from the rotated image for pixel-perfect detection
        return pygame.mask.from_surface(self.image)