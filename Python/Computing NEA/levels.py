import pygame
import random
import math
import json
import base64
import tracemalloc
from datetime import date
from Classes import (
    Background,
    Boss,
    BulletManager,
    Camera_Movement,
    Checkpoint,
    Coin,
    DamageNumber,
    DeathParticle,
    Finish,
    Fire_Power,
    FireProjectile,
    Float_Power,
    Gun,
    Invincibility_Power,
    Charger_Enemy,
    Healer_Enemy,
    Melee_Enemy,
    Platform,
    Player,
    Ranged_Enemy,
    Shield_Enemy,
    Summoner_Enemy,
    Teleport_Enemy,
    RotatingFirewall,
    Score,
    Text,
    Timer,
    Wall,
    melee_EnemyManager,
    ranged_EnemyManager,
)
from Pausing import pause_game
from win_screen import win_screen
from database import (create_connection, initialize_database, save_score, save_time,
                       get_fastest_times, get_high_scores, add_total_coins, get_player_lives,
                       subtract_life, get_powerup_count, remove_powerup, unlock_level,
                       get_unlocked_levels, get_player_best_score, get_player_best_time,
                       get_player_death_count, increment_level_death,
                       get_player_skin, get_owned_skins, buy_skin,
                       is_ng_plus_enabled, unlock_ng_plus, log_analytics_event,
                       get_meta_upgrades, save_replay_timeline, get_best_replay_for_level,
                       add_quest_progress, add_prestige_points,
                       save_level_medal)
from game_settings import load_settings, get_keybind_keycodes, get_accessibility_settings
from level_data import LEVELS
from world_progression import compute_unlocks_after_completion, WORLD_DEFS
from seasonal_events import get_active_event
from challenge_codes import parse_challenge_code
from input_actions import action_down, action_pressed
import os
try:
    pygame.mixer.init()
except Exception:
    pass

JUMP_SFX_PATH = os.path.join(os.path.dirname(__file__), "..", "jump_sfx.mp3")
try:
    if os.path.exists(JUMP_SFX_PATH):
        JUMP_SFX = pygame.mixer.Sound(JUMP_SFX_PATH)
        # Volume will be set from settings when playing
    else:
        JUMP_SFX = None
except Exception as e:
    print(f"Warning: Could not load jump sound: {e}")
    JUMP_SFX = None

def _load_sfx(filename):
    path = os.path.join(os.path.dirname(__file__), "..", filename)
    try:
        if os.path.exists(path):
            return pygame.mixer.Sound(path)
    except Exception:
        pass
    return None

def _play_sfx(sfx):
    if sfx is None:
        return
    try:
        settings = load_settings()
        if settings.get("sfx_on", True):
            sfx.set_volume(settings.get("sfx_volume", 0.6))
            sfx.play()
    except Exception:
        pass

COIN_SFX        = _load_sfx("coin_sfx.wav")
ENEMY_DEATH_SFX = _load_sfx("enemy_death_sfx.wav")
POWERUP_SFX     = _load_sfx("powerup_sfx.wav")
FOOTSTEP_SFX    = _load_sfx("footstep_sfx.wav")

pygame.init()
running = True
try:
    tracemalloc.start()
except Exception:
    pass

# initialization guard so we set up game objects exactly once
initialized = False
initialize_database() #initialize database

_GHOST_DIR = os.path.join(os.path.dirname(__file__), "ghost_replays")


def _auto_section_checkpoints(level_config, platforms):
    """Generate 2-4 section checkpoints for longer levels when none are configured."""
    if not platforms:
        return []
    world_w = int(level_config.get('world_width', 0) or 0)
    if world_w <= 0:
        return []

    if world_w < 3400:
        cp_count = 2
    elif world_w < 5600:
        cp_count = 3
    else:
        cp_count = 4

    checkpoints = []
    for i in range(1, cp_count + 1):
        target_x = int(world_w * (i / (cp_count + 1)))
        nearest = min(platforms, key=lambda p: abs(p.rect.centerx - target_x))
        cp_x = nearest.rect.centerx - 9
        cp_y = max(-20, nearest.rect.top - 44)
        if all(abs(cp_x - cp.rect.centerx) > 140 for cp in checkpoints):
            checkpoints.append(Checkpoint(cp_x, cp_y))
    return checkpoints


def _compute_level_medal(level_config, elapsed_time, death_count, coins_collected, total_coins):
    """Evaluate bronze/silver/gold based on time, deaths, and coin completion."""
    world_w = float(level_config.get('world_width', 3200) or 3200)
    target_time = max(28.0, world_w / 95.0)
    coin_ratio = 1.0 if total_coins <= 0 else (coins_collected / float(total_coins))

    if elapsed_time <= target_time and death_count == 0 and coin_ratio >= 0.90:
        return 'gold'
    if elapsed_time <= target_time * 1.20 and death_count <= 2 and coin_ratio >= 0.70:
        return 'silver'
    if elapsed_time <= target_time * 1.45 and death_count <= 4 and coin_ratio >= 0.45:
        return 'bronze'
    return 'none'


def _compute_style_rank(combo_peak, style_points):
    if combo_peak >= 14 or style_points >= 1300:
        return 'S'
    if combo_peak >= 10 or style_points >= 900:
        return 'A'
    if combo_peak >= 7 or style_points >= 600:
        return 'B'
    if combo_peak >= 4 or style_points >= 350:
        return 'C'
    return 'D'


def _get_style_meter_state(combo_peak, style_points):
    tiers = [
        ('D', 0, 0),
        ('C', 350, 4),
        ('B', 600, 7),
        ('A', 900, 10),
        ('S', 1300, 14),
    ]
    current_rank = _compute_style_rank(combo_peak, style_points)
    current_index = next(i for i, (rank, _, _) in enumerate(tiers) if rank == current_rank)
    if current_rank == 'S':
        return current_rank, None, 1.0, None, None

    next_rank, next_style_points, next_combo = tiers[current_index + 1]
    point_progress = style_points / float(next_style_points)
    combo_progress = combo_peak / float(next_combo)
    progress = max(point_progress, combo_progress)
    return current_rank, next_rank, max(0.0, min(1.0, progress)), next_style_points, next_combo


def _prompt_save_failed_replay(screen, player_name, level_id, elapsed_time, score_value, frames, mini_video_frames):
    if not frames:
        return
    title_font = pygame.font.SysFont("Arial", 38, bold=True)
    body_font = pygame.font.SysFont("Arial", 24)
    hint_font = pygame.font.SysFont("Arial", 20)
    clock = pygame.time.Clock()
    status = ""
    status_color = (180, 220, 255)

    while True:
        _ = clock.tick(60)
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        screen.blit(overlay, (0, 0))

        title = title_font.render("Save Failed Run Replay?", True, (245, 240, 220))
        info = body_font.render(
            f"Level {level_id}  Time {float(elapsed_time):.2f}s  Score {int(score_value)}",
            True,
            (225, 235, 250),
        )
        hint = hint_font.render("S = Save private replay   K / Esc = Skip", True, (200, 215, 235))
        screen.blit(title, (screen.get_width() // 2 - title.get_width() // 2, screen.get_height() // 2 - 90))
        screen.blit(info, (screen.get_width() // 2 - info.get_width() // 2, screen.get_height() // 2 - 42))
        screen.blit(hint, (screen.get_width() // 2 - hint.get_width() // 2, screen.get_height() // 2 + 6))
        if status:
            status_s = hint_font.render(status, True, status_color)
            screen.blit(status_s, (screen.get_width() // 2 - status_s.get_width() // 2, screen.get_height() // 2 + 38))
        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_k, pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    return
                if event.key == pygame.K_s:
                    replay_id = save_replay_timeline(
                        player_name,
                        level_id,
                        float(elapsed_time),
                        int(score_value),
                        frames,
                        is_public=False,
                        run_outcome='failed',
                        mini_video_frames=mini_video_frames,
                    )
                    if replay_id:
                        status = f"Saved private replay #{int(replay_id)}"
                        status_color = (150, 235, 175)
                    else:
                        status = "Save failed."
                        status_color = (255, 170, 150)
                    pygame.display.update()
                    pygame.time.delay(700)
                    return


def _inject_alt_paths_and_secret_room(level_config, platform_specs, wall_specs, coin_specs, powerup_specs):
    """Inject route branches and a secret vault so every level has exploration choices."""
    world_w = int(level_config.get('world_width', 0) or 0)
    world_h = int(level_config.get('world_height', 0) or 0)
    if world_w < 2200 or world_h <= 0:
        return

    # Alternate branch routes: safe lower route and faster upper risk route.
    route_start = int(world_w * 0.36)
    safe_y = int(world_h * 0.56)
    fast_y = safe_y - 120
    safe_step = 122
    fast_step = 156
    for i in range(4):
        platform_specs.append((route_start + i * safe_step, safe_y - i * 12, 122, 24))
        platform_specs.append((route_start + 64 + i * fast_step, fast_y - i * 22, 68, 22))

    # Reward fast-risk route with extra coins.
    for i in range(4):
        coin_specs.append((route_start + 86 + i * fast_step, fast_y - i * 22 - 32))

    # Secret room (coin vault) placed slightly above the main traversal plane.
    vault_x = int(world_w * 0.80)
    vault_y = -210
    platform_specs.append((vault_x, vault_y + 140, 220, 24))
    platform_specs.append((vault_x + 8, vault_y + 30, 204, 18))
    wall_specs.append((vault_x, vault_y + 36, 20, 106))
    wall_specs.append((vault_x + 200, vault_y + 36, 20, 106))
    # Side access tunnel into the room.
    platform_specs.append((vault_x - 120, vault_y + 124, 90, 20))
    wall_specs.append((vault_x - 40, vault_y + 78, 14, 66))
    for cx in range(vault_x + 30, vault_x + 200, 28):
        coin_specs.append((cx, vault_y + 90))

    # Cosmetic-like special reward: an extra fire pickup in the vault if not already many powerups.
    if len(powerup_specs) < 6:
        powerup_specs.append({"type": "fire", "x": vault_x + 100, "y": vault_y + 98})


def _pick_dynamic_weather(level_id, challenge_seed=None):
    profiles = [
        {"key": "clear", "name": "Clear Skies", "gravity_mult": 1.0, "wind_force": 0.0, "slippery": False},
        {"key": "wind", "name": "Low-Gravity Wind", "gravity_mult": 0.88, "wind_force": 38.0, "slippery": False},
        {"key": "rain", "name": "Slip Rain", "gravity_mult": 1.03, "wind_force": 16.0, "slippery": True},
    ]
    seed = int(challenge_seed) if challenge_seed is not None else int(level_id) * 97
    rng = random.Random(seed)
    return profiles[rng.randint(0, len(profiles) - 1)]


def _world_id_for_level(level_id):
    if not isinstance(level_id, int):
        return None
    for world_id, world_cfg in WORLD_DEFS.items():
        level_pool = set(world_cfg.get('normal_levels', []) + world_cfg.get('hard_levels', []) + [world_cfg.get('normal_boss'), world_cfg.get('hard_boss')])
        if int(level_id) in level_pool:
            return int(world_id)
    return None


def _get_world_tutorial_cards(world_id, level_name=''):
    if world_id == 1:
        return [
            "World 1 Drill: Chain stomps to keep combo pressure active.",
            "World 1 Drill: Use air dash and slide jump to cross long gaps safely.",
        ]
    if world_id == 2:
        return [
            "World 2 Drill: Ranged units force movement. Burst in, then disengage.",
            "World 2 Drill: Shield enemies are weakest from above or behind.",
        ]
    if world_id == 3:
        return [
            "World 3 Drill: Siege markers flash before impact. Relocate early.",
            "World 3 Drill: Use vertical routes during strike waves to avoid crossfire.",
        ]
    if str(level_name).lower().startswith('tutorial'):
        return [
            "Tutorial Tip: Build rhythm with jump, dash, and slide before combat.",
        ]
    return []


def _pick_world_challenge_variant(world_id, challenge_seed):
    if world_id is None or challenge_seed is None:
        return None
    variant_tables = {
        1: [
            {
                'key': 'speedrun_flux',
                'label': 'Speedrun Flux',
                'description': 'Faster enemies and tighter combo windows reward clean routing.',
                'enemy_speed_mult': 1.16,
                'combo_decay_mult': 0.86,
            },
            {
                'key': 'coin_rush',
                'label': 'Coin Rush',
                'description': 'Higher coin gain but jump arcs feel slightly heavier.',
                'coin_mult': 1.22,
                'gravity_mult': 1.07,
            },
        ],
        2: [
            {
                'key': 'crossfire_zone',
                'label': 'Crossfire Zone',
                'description': 'Ranged volleys accelerate and pressure movement lanes.',
                'bullet_speed_mult': 1.22,
                'enemy_speed_mult': 1.08,
            },
            {
                'key': 'fortified_squads',
                'label': 'Fortified Squads',
                'description': 'Frontline enemies gain durability; value stagger and spacing.',
                'enemy_health_mult': 1.18,
            },
        ],
        3: [
            {
                'key': 'siege_storm',
                'label': 'Siege Storm',
                'description': 'Siege strikes cycle faster and force faster repositioning.',
                'siege_cooldown_mult': 0.8,
                'enemy_speed_mult': 1.06,
            },
            {
                'key': 'last_stand',
                'label': 'Last Stand',
                'description': 'Harder pressure but richer coin payoffs for clean clears.',
                'enemy_health_mult': 1.1,
                'coin_mult': 1.16,
            },
        ],
    }
    pool = variant_tables.get(int(world_id), [])
    if not pool:
        return None
    idx = int(challenge_seed) % len(pool)
    return dict(pool[idx])


def _is_siege_world(level_config, level_id=None):
    if str(level_config.get('world_trait', '')).lower() == 'siege':
        return True
    if 'siege_strikes' in level_config:
        return True
    if isinstance(level_id, int) and 29 <= int(level_id) <= 40:
        return True
    return str(level_config.get('name', '')).lower().startswith('world 3')


def _build_siege_wave(level_config, player_rect, enemy_groups, world_width, rng):
    cfg = level_config.get('siege_strikes') or {}
    burst_count = max(1, int(cfg.get('burst_count', 2) or 2))
    column_width = max(50, int(cfg.get('column_width', 80) or 80))
    clamp_max = max(column_width, int(world_width or 0) - column_width)
    alive_enemies = []
    for group in enemy_groups:
        alive_enemies.extend([enemy for enemy in group if getattr(enemy, 'alive', False)])
    alive_enemies.sort(key=lambda enemy: abs(enemy.rect.centerx - player_rect.centerx))

    anchors = [player_rect.centerx]
    for enemy in alive_enemies[:2]:
        anchors.append(enemy.rect.centerx)

    strikes = []
    attempts = 0
    while len(strikes) < burst_count and attempts < 12:
        base_x = anchors[len(strikes) % len(anchors)] if anchors else rng.randint(column_width, clamp_max)
        strike_x = max(column_width, min(clamp_max, int(base_x + rng.randint(-70, 70))))
        if all(abs(strike_x - existing) >= int(column_width * 0.75) for existing in strikes):
            strikes.append(strike_x)
        attempts += 1
    if not strikes:
        strikes.append(max(column_width, min(clamp_max, int(player_rect.centerx))))
    return strikes


WEEKLY_BOSS_MODIFIERS = [
    {
        'key': 'relentless',
        'label': 'Relentless Assault',
        'description': 'The boss presses faster and recovers quicker between swings.',
        'move_speed_mult': 1.10,
        'attack_cooldown_mult': 0.84,
        'windup_mult': 0.88,
    },
    {
        'key': 'colossus',
        'label': 'Colossus Guard',
        'description': 'The boss is heavier, tougher, and hits harder than usual.',
        'health_mult': 1.18,
        'damage_mult': 1.15,
        'move_speed_mult': 0.93,
    },
    {
        'key': 'ring_of_fire',
        'label': 'Ring of Fire',
        'description': 'A rotating firewall patrols the arena as a weekly hazard layer.',
        'attack_cooldown_mult': 0.94,
        'hazard': 'fire_ring',
    },
    {
        'key': 'executioner',
        'label': 'Executioner Reach',
        'description': 'Longer axe arcs make every committed swing more dangerous.',
        'damage_mult': 1.10,
        'windup_mult': 0.90,
        'axe_scale_mult': 1.22,
    },
]


def _boss_world_for_level(level_id):
    if not isinstance(level_id, int):
        return None
    for world_id, world_cfg in WORLD_DEFS.items():
        if int(level_id) in (int(world_cfg['normal_boss']), int(world_cfg['hard_boss'])):
            return int(world_id)
    return None


def _get_weekly_boss_modifier(level_id):
    world_id = _boss_world_for_level(level_id)
    if world_id is None:
        return None
    week_seed = date.today().isocalendar().week + world_id * 3
    modifier = WEEKLY_BOSS_MODIFIERS[week_seed % len(WEEKLY_BOSS_MODIFIERS)]
    return dict(modifier)


def _apply_weekly_boss_modifier(boss, modifier, rotating_firewalls, level_config, level_id=None):
    if boss is None or not modifier:
        return
    attack_cooldown_mult = float(modifier.get('attack_cooldown_mult', 1.0) or 1.0)
    move_speed_mult = float(modifier.get('move_speed_mult', 1.0) or 1.0)
    damage_mult = float(modifier.get('damage_mult', 1.0) or 1.0)
    windup_mult = float(modifier.get('windup_mult', 1.0) or 1.0)
    health_mult = float(modifier.get('health_mult', 1.0) or 1.0)
    axe_scale_mult = float(modifier.get('axe_scale_mult', 1.0) or 1.0)

    for row in boss.phase_table:
        row['move_speed'] = max(40, int(float(row['move_speed']) * move_speed_mult))
        row['attack_cooldown'] = max(0.55, float(row['attack_cooldown']) * attack_cooldown_mult)
        row['attack_damage'] = max(10, int(float(row['attack_damage']) * damage_mult))
        row['windup'] = max(0.18, float(row['windup']) * windup_mult)

    boss.max_health = max(1, int(float(boss.max_health) * health_mult))
    boss.health = min(boss.max_health, max(1, int(float(boss.health) * health_mult)))
    boss.axe_scale = max(0.9, axe_scale_mult)
    boss.weekly_modifier_label = str(modifier.get('label', 'Weekly Modifier'))
    boss.weekly_modifier_description = str(modifier.get('description', ''))
    boss._apply_phase_tuning(force=True)

    if modifier.get('hazard') == 'fire_ring' and rotating_firewalls is not None:
        arena_center_x = int((boss.min_x + boss.max_x) / 2)
        arena_center_y = int(boss.rect.centery + 10)
        firewall_folder = level_config.get('firewall_animation_folder', 'images/hazards/firewall/')
        rotating_firewalls.append(
            RotatingFirewall(
                arena_center_x,
                arena_center_y,
                blade_width=92,
                blade_height=22,
                rotation_speed=245,
                animation_folder=firewall_folder,
            )
        )

def load_level_from_config(level_config, ng_plus=False, challenge_seed=None):
    """
    Convert a level config dict into actual game objects.
    Returns a dict with all initialized game objects.
    """
    _plat_img = level_config.get('platform_image', 'platform.png')
    platform_specs = list(level_config['platforms'])
    wall_specs = list(level_config.get('walls', []))
    coin_specs = list(level_config.get('coins', []))
    powerup_specs = [dict(pu) for pu in level_config.get('power_ups', [])]

    if level_config.get('auto_route_content', True):
        _inject_alt_paths_and_secret_room(level_config, platform_specs, wall_specs, coin_specs, powerup_specs)

    platforms = [Platform(_plat_img, x, y, w, h) for x, y, w, h in platform_specs] #creates a list of platform objects

    def snap_to_platform_top(x, current_y, entity_h, x_margin=10):
        # Snap entities to nearest platform under their X to avoid floating/embedded spawns.
        candidates = []
        for px, py, pw, _ in platform_specs:
            if px - x_margin <= x <= px + pw + x_margin:
                candidates.append(py)
        if not candidates:
            return current_y
        current_bottom = current_y + entity_h
        target_top = min(candidates, key=lambda top: abs(current_bottom - top))
        return target_top - entity_h

    aligned_melee = []
    for enemy in level_config.get('melee_enemies', []):
        ey = enemy['y']
        if level_config.get('name', '').startswith('Hard Level'):
            ey = snap_to_platform_top(enemy['x'], ey, 40)
        aligned_melee.append({'x': enemy['x'], 'y': ey})

    aligned_ranged = []
    for enemy in level_config.get('ranged_enemies', []):
        ey = enemy['y']
        if level_config.get('name', '').startswith('Hard Level'):
            ey = snap_to_platform_top(enemy['x'], ey, 40)
        aligned_ranged.append({'x': enemy['x'], 'y': ey})

    aligned_chargers = []
    for enemy in level_config.get('charger_enemies', []):
        ey = enemy['y']
        if level_config.get('name', '').startswith('Hard Level'):
            ey = snap_to_platform_top(enemy['x'], ey, 42)
        aligned_chargers.append({'x': enemy['x'], 'y': ey})

    aligned_shields = []
    for enemy in level_config.get('shield_enemies', []):
        ey = enemy['y']
        if level_config.get('name', '').startswith('Hard Level'):
            ey = snap_to_platform_top(enemy['x'], ey, 42)
        aligned_shields.append({'x': enemy['x'], 'y': ey})

    aligned_healers = []
    for enemy in level_config.get('healer_enemies', []):
        ey = enemy['y']
        if level_config.get('name', '').startswith('Hard Level'):
            ey = snap_to_platform_top(enemy['x'], ey, 42)
        aligned_healers.append({'x': enemy['x'], 'y': ey})

    aligned_summoners = []
    for enemy in level_config.get('summoner_enemies', []):
        ey = enemy['y']
        if level_config.get('name', '').startswith('Hard Level'):
            ey = snap_to_platform_top(enemy['x'], ey, 42)
        aligned_summoners.append({'x': enemy['x'], 'y': ey})

    aligned_teleports = []
    for enemy in level_config.get('teleport_enemies', []):
        ey = enemy['y']
        if level_config.get('name', '').startswith('Hard Level'):
            ey = snap_to_platform_top(enemy['x'], ey, 42)
        aligned_teleports.append({'x': enemy['x'], 'y': ey})

    if ng_plus or challenge_seed is not None:
        # Deterministic remix so each level keeps a predictable NG+ layout.
        cfg_world_width = level_config.get('world_width')
        if challenge_seed is not None:
            seed = int(challenge_seed)
        else:
            seed = int(level_config.get('world_width', 0)) + int(level_config.get('world_height', 0)) + len(aligned_melee) * 7 + len(aligned_ranged) * 11 + len(aligned_chargers) * 13 + len(aligned_shields) * 17
        rng = random.Random(seed)

        def remix_enemy(entry, h):
            nx = entry['x'] + rng.randint(-150, 150)
            ny = entry['y']
            if cfg_world_width:
                nx = max(10, min(int(cfg_world_width) - 40, nx))
            ny = snap_to_platform_top(nx, ny, h, x_margin=16)
            return {'x': nx, 'y': ny}

        aligned_melee = [remix_enemy(e, 40) for e in aligned_melee]
        aligned_ranged = [remix_enemy(e, 40) for e in aligned_ranged]
        aligned_chargers = [remix_enemy(e, 42) for e in aligned_chargers]
        aligned_shields = [remix_enemy(e, 42) for e in aligned_shields]
        aligned_healers = [remix_enemy(e, 42) for e in aligned_healers]
        aligned_summoners = [remix_enemy(e, 42) for e in aligned_summoners]
        aligned_teleports = [remix_enemy(e, 42) for e in aligned_teleports]

    aligned_powerups = []
    for pu in powerup_specs:
        py = pu['y']
        if level_config.get('name', '').startswith('Hard Level'):
            py = snap_to_platform_top(pu['x'], py, 30)
        aligned_powerups.append({'type': pu['type'], 'x': pu['x'], 'y': py})

    aligned_coins = []
    for cx, cy in coin_specs:
        new_y = cy
        if level_config.get('name', '').startswith('Hard Level'):
            new_y = snap_to_platform_top(cx, cy, 20)
        aligned_coins.append((cx, new_y))
    # Mark any platforms configured to decay when stepped on
    for idx in level_config.get('decaying_platforms', []): #    creates a list of platforms that decay when stepped on
        if 0 <= idx < len(platforms):
            platforms[idx].decay_on_step = True
    # Mark any platforms configured to bounce the player when stepped on
    for idx in level_config.get('bounce_platforms', []): #creates a list of platforms that bounce the player when stepped on
        if 0 <= idx < len(platforms):
            platforms[idx].bounce_on_step = True
    # Mark any platforms configured to grant a temporary movement speed boost
    for idx in level_config.get('speed_boost_platforms', []):
        if 0 <= idx < len(platforms):
            platforms[idx].speed_boost_on_step = True
    for plat in platforms:
        plat.refresh_visual_style()
    walls = [Wall('wall.png', x, y, w, h) for x, y, w, h in wall_specs] #creates a list of wall objects
    
    # Load rotating firewalls from config
    rotating_firewalls = []
    for fw_config in level_config.get('rotating_firewalls', []):
        fw = RotatingFirewall(
            fw_config['cx'],
            fw_config['cy'],
            fw_config.get('blade_width', 80),
            fw_config.get('blade_height', 20),
            fw_config.get('rotation_speed', 180),
            fw_config.get('animation_folder', level_config.get('firewall_animation_folder', 'images/hazards/firewall/'))
        )
        rotating_firewalls.append(fw)
    
    coins = [Coin('coin.png', x, y) for x, y in aligned_coins] #creates a list of coin objects
    _melee_img = level_config.get('melee_enemy_image', 'melee enemy.png')
    _enemy_idle_folder = level_config.get('enemy_idle_folder')
    _enemy_run_folder = level_config.get('enemy_run_folder')
    melee_enemies = [
        Melee_Enemy(_melee_img, e['x'], e['y'], idle_folder=_enemy_idle_folder, run_folder=_enemy_run_folder)
        for e in aligned_melee
    ]
     # creates a list for enemies
    # Assign each melee enemy to the platform it stands on so the patrol AI knows the boundaries
    for enemy in melee_enemies:
        best_plat = None
        best_dist = float('inf')
        for plat in platforms:
            if plat.rect.left <= enemy.rect.centerx <= plat.rect.right:
                dist = abs(enemy.rect.bottom - plat.rect.top)
                if dist < best_dist:
                    best_dist = dist
                    best_plat = plat
        enemy.platform = best_plat
        # Clamp the platform width to 120–180 px so patrol stays manageable
        if best_plat is not None:
            clamped_w = max(120, min(180, best_plat.rect.width))
            if clamped_w != best_plat.rect.width:
                best_plat.rect.width = clamped_w
                best_plat.image = pygame.transform.scale(
                    best_plat.image, (clamped_w, best_plat.rect.height)
                )
    _ranged_img = level_config.get('ranged_enemy_image', 'ranged enemy.png')
    _ranged_idle_folder = level_config.get('ranged_enemy_idle_folder')
    _ranged_run_folder = level_config.get('ranged_enemy_run_folder')
    ranged_enemies = [
        Ranged_Enemy(_ranged_img, e['x'], e['y'], idle_folder=_ranged_idle_folder, run_folder=_ranged_run_folder)
        for e in aligned_ranged
    ]
     # creates a list for ranged enemies
    charger_enemies = [Charger_Enemy(_melee_img, e['x'], e['y'], idle_folder=_enemy_idle_folder, run_folder=_enemy_run_folder) for e in aligned_chargers]
    shield_enemies = [Shield_Enemy(_melee_img, e['x'], e['y'], idle_folder=_enemy_idle_folder, run_folder=_enemy_run_folder) for e in aligned_shields]
    healer_enemies = [Healer_Enemy(_melee_img, e['x'], e['y'], idle_folder=_enemy_idle_folder, run_folder=_enemy_run_folder) for e in aligned_healers]
    summoner_enemies = [Summoner_Enemy(_melee_img, e['x'], e['y'], idle_folder=_enemy_idle_folder, run_folder=_enemy_run_folder) for e in aligned_summoners]
    teleport_enemies = [Teleport_Enemy(_melee_img, e['x'], e['y'], idle_folder=_enemy_idle_folder, run_folder=_enemy_run_folder) for e in aligned_teleports]
    for enemy in charger_enemies + shield_enemies + healer_enemies + summoner_enemies + teleport_enemies:
        best_plat = None
        best_dist = float('inf')
        for plat in platforms:
            if plat.rect.left <= enemy.rect.centerx <= plat.rect.right:
                dist = abs(enemy.rect.bottom - plat.rect.top)
                if dist < best_dist:
                    best_dist = dist
                    best_plat = plat
        enemy.platform = best_plat

    melee_enemies.extend(healer_enemies)
    melee_enemies.extend(summoner_enemies)
    melee_enemies.extend(teleport_enemies)
    _finish_img = level_config.get('finish_image', 'finish line.png')
    finish = Finish(_finish_img, level_config['finish_line']['x'], level_config['finish_line']['y'], 
                    level_config['finish_line']['w'], level_config['finish_line']['h']) # creates the finish line object
    boss = None
    boss_cfg = level_config.get('boss')
    if boss_cfg:
        boss = Boss(
            boss_cfg.get('image', 'melee enemy.png'),
            boss_cfg.get('x', 0),
            boss_cfg.get('y', 0),
            health=boss_cfg.get('health', 100),
            w=boss_cfg.get('w', 90),
            h=boss_cfg.get('h', 120),
            min_x=boss_cfg.get('min_x'),
            max_x=boss_cfg.get('max_x'),
            speed=boss_cfg.get('speed', 90),
            animation_folder=boss_cfg.get('animation_folder'),
            arm_color=tuple(boss_cfg.get('arm_color', (180, 115, 65))),
            wrist_color=tuple(boss_cfg.get('wrist_color', (195, 130, 75))),
            shoulder_color=tuple(boss_cfg.get('shoulder_color', (200, 140, 85))),
            axe_handle_color=tuple(boss_cfg.get('axe_handle_color', (120, 80, 50))),
            axe_head_color=tuple(boss_cfg.get('axe_head_color', (200, 200, 215))),
        )
    world_width = level_config.get('world_width')
    world_height = level_config.get('world_height')
    
    # Create guns for ranged enemies
    guns = [Gun('gun.png', e.rect.x, e.rect.y + 20, owner=e) for e in ranged_enemies] # creates guns for each ranged enemy
    
    # Load power-ups based on config
    float_powers = []
    invincibility_powers = []
    fire_powers = []
    
    for pu in aligned_powerups:
        if pu['type'] == 'float':
            float_powers.append(Float_Power('float_power.png', pu['x'], pu['y']))
             # creates float powerup objects
        elif pu['type'] == 'invincibility':
            invincibility_powers.append(Invincibility_Power('invincibility.png', pu['x'], pu['y']))
             # creates invincibility powerup objects
        elif pu['type'] == 'fire':
            fire_powers.append(Fire_Power('fire_flower.png', pu['x'], pu['y']))
             # creates fire powerup objects
    
    return {
        'world_width': world_width,
        'world_height': world_height,
        'platforms': platforms,
        'walls': walls,
        'rotating_firewalls': rotating_firewalls,
        'coins': coins,
        'melee_enemies': melee_enemies,
        'ranged_enemies': ranged_enemies,
        'charger_enemies': charger_enemies,
        'shield_enemies': shield_enemies,
        'healer_enemies': healer_enemies,
        'summoner_enemies': summoner_enemies,
        'teleport_enemies': teleport_enemies,
        'boss': boss,
        'finish_line': finish,
        'guns': guns,
        'float_powers': float_powers,
        'invincibility_powers': invincibility_powers,
        'fire_powers': fire_powers,
        'bullets': BulletManager(),
    } #return all created objects

def get_player_name():
    #Display a screen where the player can input their name
    info = pygame.display.Info()
    name_screen = pygame.display.set_mode((info.current_w, info.current_h))
    pygame.display.set_caption("Lost Horizon - Enter Your Name")
    
    # scale fonts based on screen height
    sy = name_screen.get_height() / 600.0
    sx = name_screen.get_width() / 1000.0
    font_title = pygame.font.SysFont("Arial", max(24, int(48 * sy)))
    font_text = pygame.font.SysFont("Arial", max(18, int(36 * sy)))
    
    player_name = ""
    input_active = True
    
    while input_active and running:
        name_screen.fill((0, 0, 0))  # black background
        
        # Draw title (centered)
        title = font_title.render("Enter Your Name", True, (255, 255, 255))
        title_x = (name_screen.get_width() - title.get_width()) // 2
        title_y = int(name_screen.get_height() * 0.25)
        name_screen.blit(title, (title_x, title_y))
        
        # Draw input box and text (centered)
        box_w = int(name_screen.get_width() * 0.60)
        box_h = int(name_screen.get_height() * 0.08)
        box_x = (name_screen.get_width() - box_w) // 2
        box_y = int(name_screen.get_height() * 0.45)
        pygame.draw.rect(name_screen, (255, 255, 255), (box_x, box_y, box_w, box_h), 2)
        name_text = font_text.render(player_name + ("|" if len(player_name) < 20 else ""), True, (255, 255, 255))
        text_x = box_x + int(box_w * 0.02)
        text_y = box_y + int((box_h - name_text.get_height()) // 2)
        name_screen.blit(name_text, (text_x, text_y))
        
        # Draw instruction (centered)
        instruction = font_text.render("Press ENTER to continue", True, (200, 200, 200))
        instr_x = (name_screen.get_width() - instruction.get_width()) // 2
        instr_y = int(name_screen.get_height() * 0.65)
        name_screen.blit(instruction, (instr_x, instr_y))
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None  # user quit
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and len(player_name) > 0:
                    input_active = False
                elif event.key == pygame.K_BACKSPACE:
                    player_name = player_name[:-1] #remove last character
                elif len(player_name) < 20 and event.unicode.isprintable(): #limit name length to 20 characters
                    player_name += event.unicode #add typed character to name
        
        pygame.display.update()
    
    return player_name if player_name else "Player" #default name if none entered

def level(level_id, player_name, challenge_code=None, level_config_override=None, custom_level_id=None, leaderboard_hooks=None, race_replay=None):
    global initialized, running

    is_custom_level = level_config_override is not None
    if (not is_custom_level) and level_id not in LEVELS:
        print(f"Level ID {level_id} not found.")
        return True  # return to play menu

    level_config = level_config_override if is_custom_level else LEVELS[level_id]
    level_name = level_config.get("name", f"Level {level_id}")
    stats_level_id = level_id if (not is_custom_level and isinstance(level_id, int)) else None

    initialized = False  # reset so we can play tutorial again

    # Get player name at start
    if player_name is None:
        return True  # user quit
    
    local_clock = pygame.time.Clock()  # create a local clock for the tutorial
    conn = create_connection("scores_and_times.db")
    
    # Initialize all variables that will be used throughout the game loop
    player = None
    background = None
    platforms = None
    coins = None
    melee_enemies = None
    ranged_enemies = None
    charger_enemies = None
    shield_enemies = None
    healer_enemies = None
    summoner_enemies = None
    teleport_enemies = None
    boss = None
    finish_line = None
    camera = None
    bullets = None
    timer = None
    score = None
    guns = None
    font = None
    controls_text = None
    lives = None
    jumping = False
    coins_collected = 0
    fire_powers = None
    boss_intro_played = False
    MELEE_CONTACT_DAMAGE = 25
    BULLET_DAMAGE = 20
    BOSS_STOMP_DAMAGE = 20
    BOSS_INVINCIBILITY_RAM_DAMAGE = 10
    boss_contact_damage_cooldown = 0.0
    respawn_lock_timer = 0.0
    damage_numbers = []
    death_particles = []
    footstep_timer = 0.0
    shake_timer = 0.0
    shake_intensity = 0
    fade_in_timer = 0.0
    last_kill_time = 0
    kill_streak = 0
    checkpoints = []
    active_checkpoint = None
    hud_best_score = None
    player_skin_tint = None
    warn_font = None
    bar_label_font = None
    hud_life_img = None
    hud_coin_img = None
    ng_plus_active = False
    seasonal_event = None
    seasonal_coin_mult = 1.0
    seasonal_gravity_mult = 1.0
    dynamic_weather = None
    dynamic_weather_key = 'clear'
    weather_wind_force = 0.0
    weather_particles = []
    weather_spawn_timer = 0.0
    ghost_enabled = not is_custom_level
    ghost_payload = None
    ghost_frames = []
    ghost_time = None
    ghost_cursor = 0
    ghost_record_frames = []
    ghost_record_timer = 0.0
    replay_video_frames = []
    replay_video_timer = 0.0
    replay_video_interval = 0.20
    replay_video_max_frames = 180
    ghost_owner_name = None
    ghost_replay_id = None
    total_level_coins = 0
    level_deaths = 0
    coyote_timer = 0.0
    coyote_time_window = 0.10
    jump_buffer_timer = 0.0
    jump_buffer_window = 0.10
    challenge_info = parse_challenge_code(challenge_code) if (challenge_code and not is_custom_level) else None
    challenge_seed = None
    challenge_mods = {}
    challenge_variant = None
    world_tutorial_cards = []
    tutorial_card_index = 0
    tutorial_card_timer = 0.0
    tutorial_card_duration = 6.0
    training_target_time = None
    training_medal_times = {}
    siege_enabled = _is_siege_world(level_config, level_id if isinstance(level_id, int) else None)
    siege_cfg = dict(level_config.get('siege_strikes') or {}) if siege_enabled else {}
    siege_strikes = []
    siege_rng = random.Random((int(level_id) if isinstance(level_id, int) else 0) * 173 + len(level_name))
    siege_timer = float(siege_cfg.get('cooldown', 5.2) or 5.2)
    boss_weekly_modifier = _get_weekly_boss_modifier(level_id if isinstance(level_id, int) else None)
    if challenge_info is not None and challenge_info.get('level_id') == level_id:
        challenge_seed = challenge_info.get('seed')
        challenge_mods = challenge_info.get('modifiers') or {}
    resolved_world_id = _world_id_for_level(stats_level_id if stats_level_id is not None else (level_id if isinstance(level_id, int) else None))
    world_tutorial_cards = _get_world_tutorial_cards(resolved_world_id, level_name=level_name)
    if challenge_seed is not None:
        challenge_variant = _pick_world_challenge_variant(resolved_world_id, challenge_seed)
    if is_custom_level:
        try:
            if level_config.get('training_target_time') is not None:
                training_target_time = float(level_config.get('training_target_time'))
        except Exception:
            training_target_time = None
        trial_times = level_config.get('training_medal_times') or {}
        if isinstance(trial_times, dict):
            training_medal_times = dict(trial_times)

    settings_blob = load_settings()
    keybinds = get_keybind_keycodes(settings_blob)
    keybind_names = settings_blob.get('keybinds', {}) if isinstance(settings_blob.get('keybinds'), dict) else {}
    debug_keys = keybind_names.get('debug_overlay', ['f3'])
    debug_label = '/'.join(str(k).upper() for k in debug_keys[:2]) if debug_keys else 'F3'
    power_select_1_label = '/'.join(str(k).upper() for k in keybind_names.get('select_power_1', ['1'])[:2])
    power_select_2_label = '/'.join(str(k).upper() for k in keybind_names.get('select_power_2', ['2'])[:2])
    power_select_3_label = '/'.join(str(k).upper() for k in keybind_names.get('select_power_3', ['3'])[:2])
    power_activate_label = '/'.join(str(k).upper() for k in keybind_names.get('activate_power', ['e'])[:2])
    accessibility = get_accessibility_settings(settings_blob)
    hud_simplified = bool(accessibility.get('hud_simplified', False))
    colorblind_safe = bool(accessibility.get('colorblind_safe_palette', False))
    always_show_perf = bool(accessibility.get('performance_overlay', False))
    high_contrast_hud = bool(accessibility.get('high_contrast_hud', False))
    easy_mode = bool(settings_blob.get('easy_mode', False))
    if is_custom_level and custom_level_id is None:
        run_mode_label = 'training'
    elif is_custom_level and custom_level_id is not None:
        run_mode_label = 'sandbox'
    elif challenge_info is not None:
        run_mode_label = 'challenge'
    elif easy_mode:
        run_mode_label = 'easy'
    else:
        run_mode_label = 'standard'
    if accessibility.get('extended_jump_buffer', False):
        jump_buffer_window = 0.16
        coyote_time_window = 0.14

    def _get_hook(name):
        if leaderboard_hooks is None:
            return None
        fn = leaderboard_hooks.get(name)
        return fn if callable(fn) else None

    get_best_score_hook = _get_hook('get_player_best_score')
    get_best_time_hook = _get_hook('get_player_best_time')
    save_run_hook = _get_hook('save_run')
    get_top_scores_hook = _get_hook('get_top_scores')
    get_top_times_hook = _get_hook('get_top_times')
    on_complete_hook = _get_hook('on_complete')
    debug_overlay = False
    recent_frame_ms = []
    perf_frame_counter = 0
    perf_elapsed = 0.0
    perf_spike_cooldown = 0.0
    perf_spike_count = 0
    perf_peak_frame_ms = 0.0
    selected_power_slot = 1

    def _activate_selected_power(slot):
        if slot == 1:
            if getattr(player, 'float_power_collected', False) and not getattr(player, 'float_power_active', False):
                player.float_power_collected = False
                player.float_power_active = True
                player.float_time_remaining = 5.0
                conn = create_connection("scores_and_times.db")
                if conn:
                    if get_powerup_count(conn, player_name, 'float') > 0:
                        remove_powerup(conn, player_name, 'float')
                    conn.close()
                return True
            return False

        if slot == 2:
            if getattr(player, 'invincibility_collected', False) and not getattr(player, 'invincibility_active', False):
                player.invincibility_collected = False
                player.invincibility_active = True
                player.invincibility_time_remaining = 4.0
                conn = create_connection("scores_and_times.db")
                if conn:
                    if get_powerup_count(conn, player_name, 'invincibility') > 0:
                        remove_powerup(conn, player_name, 'invincibility')
                    conn.close()
                return True
            return False

        if slot == 3:
            if player.fire_power_collected and not player.fire_power_active:
                player.fire_power_collected = False
                player.fire_power_active = True
                player.fire_power_time_remaining = 12.0
                conn = create_connection("scores_and_times.db")
                if conn:
                    if get_powerup_count(conn, player_name, 'fire') > 0:
                        remove_powerup(conn, player_name, 'fire')
                    conn.close()
                return True
            return False

        return False

    def _get_perf_snapshot():
        if recent_frame_ms:
            avg_ms_local = sum(recent_frame_ms) / len(recent_frame_ms)
            p95_ms_local = sorted(recent_frame_ms)[int((len(recent_frame_ms) - 1) * 0.95)]
        else:
            avg_ms_local = 0.0
            p95_ms_local = 0.0
        fps_avg_local = 0.0 if avg_ms_local <= 0 else (1000.0 / avg_ms_local)
        mem_current_mb_local = 0.0
        mem_peak_mb_local = 0.0
        try:
            mem_current, mem_peak = tracemalloc.get_traced_memory()
            mem_current_mb_local = float(mem_current) / (1024.0 * 1024.0)
            mem_peak_mb_local = float(mem_peak) / (1024.0 * 1024.0)
        except Exception:
            pass
        return avg_ms_local, p95_ms_local, fps_avg_local, mem_current_mb_local, mem_peak_mb_local
    analytics_area_time = {}
    analytics_tick = 0.0
    hitstop_timer = 0.0
    combo_decay_timer = 0.0
    combo_decay_window = 3.0
    combo_max_streak = 0
    style_points = 0
    style_breakdown = {
        'kills': 0,
        'movement': 0,
        'finishers': 0,
        'penalties': 0,
    }
    style_recent_actions = []
    style_recent_window_ms = 7000
    style_last_gain_ms = pygame.time.get_ticks()
    style_last_variation_ms = 0
    style_variation_cooldown_ms = 1400
    style_decay_grace_ms = 5200
    style_decay_rate = 18.0
    movement_style_cooldowns = {
        'air_dash': 0.0,
        'slide': 0.0,
        'slide_jump': 0.0,
        'wall_jump': 0.0,
    }
    player_dash_timer = 0.0
    player_dash_velocity = 0.0
    player_dash_cooldown = 0.0
    player_dash_used_air = False
    player_slide_timer = 0.0
    wall_jump_cooldown = 0.0
    player_wall_sliding = False
    base_player_speed = 150
    meta_upgrades = {'mobility': 0, 'survivability': 0, 'economy': 0}

    def damage_player(amount, source_x=None, heavy=False):
        nonlocal lives, jumping, respawn_lock_timer, shake_timer, shake_intensity, kill_streak, hitstop_timer, style_points, style_breakdown, level_deaths, coyote_timer, jump_buffer_timer
        shake_scale = 0.35 if accessibility.get('reduced_screen_shake', False) else 1.0
        shake_timer = 0.4 * shake_scale
        shake_intensity = max(1, int(6 * shake_scale))
        if player is None:
            return
        if getattr(player, 'damage_cooldown', 0.0) > 0:
            return
        player.health = max(0, player.health - amount)
        player.damage_cooldown = 0.6
        # Directional knockback for clearer hit readability.
        if source_x is not None:
            player.x_velocity = 220 if player.rect.centerx < source_x else -220
        if heavy:
            hitstop_timer = max(hitstop_timer, 0.06)
            shake_intensity = max(shake_intensity, int(9 * shake_scale))
            shake_timer = max(shake_timer, 0.45 * shake_scale)
        damage_numbers.append(DamageNumber(f"-{amount}", player.rect.centerx, player.rect.top, (255, 60, 60)))
        if player.health <= 0:
            # Respawn at checkpoint if one is active, otherwise at start platform
            if active_checkpoint is not None:
                spawn_x = active_checkpoint.rect.centerx - player.rect.width // 2
                spawn_bottom = active_checkpoint.rect.top - 1
            else:
                spawn_x = start_plat.rect.left + 5
                spawn_bottom = start_plat.rect.top - 1
            player.rect.x = spawn_x
            player.rect.bottom = spawn_bottom
            player.x_velocity = 0
            player.y_velocity = 0.0
            jumping = False
            coyote_timer = coyote_time_window
            jump_buffer_timer = 0.0
            respawn_lock_timer = 0.5
            player.damage_cooldown = max(player.damage_cooldown, 0.5)
            player.health = player.max_health
            lives -= 1
            level_deaths += 1
            kill_streak = 0
            style_points = max(0, style_points - 120)
            style_breakdown['penalties'] += 120
            try:
                log_analytics_event(player_name, 'death', level_id=stats_level_id, x=player.rect.centerx, y=player.rect.centery)
            except Exception:
                pass
            try:
                if stats_level_id is not None:
                    increment_level_death(player_name, stats_level_id)
            except Exception:
                pass
            conn_dmg = create_connection("scores_and_times.db")
            if conn_dmg and lives >= 3:
                subtract_life(conn_dmg, player_name)
            if conn_dmg:
                conn_dmg.close()
            if hasattr(player, 'update_position'):
                player.update_position()
            for plat in platforms:
                plat.active = True

    def spawn_death_particles(cx, cy, color=(255, 100, 30)):
        for _ in range(7):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(70, 200)
            death_particles.append(DeathParticle(cx, cy, math.cos(angle) * speed, math.sin(angle) * speed, color))

    def _style_gain_with_variation(action_tag, base_amount):
        nonlocal style_recent_actions, style_last_gain_ms, style_last_variation_ms
        now = pygame.time.get_ticks()
        style_recent_actions = [pair for pair in style_recent_actions if (now - int(pair[0])) <= style_recent_window_ms]
        repeats = sum(1 for _, tag in style_recent_actions if tag == action_tag)
        unique_types = len({tag for _, tag in style_recent_actions})

        repeat_mult = max(0.45, 1.0 - 0.16 * repeats)
        scaled = max(1, int(round(float(base_amount) * repeat_mult)))

        variation_bonus = 0
        if unique_types >= 3 and repeats == 0 and (now - style_last_variation_ms) >= style_variation_cooldown_ms:
            variation_bonus = 14 + min(20, unique_types * 2)
            style_last_variation_ms = now

        style_recent_actions.append((now, str(action_tag)))
        style_last_gain_ms = now
        return scaled, variation_bonus

    def _register_kill(cx, cy, action_tag='kill'):
        nonlocal last_kill_time, kill_streak, combo_decay_timer, combo_max_streak, style_points, style_breakdown, hitstop_timer
        now = pygame.time.get_ticks()
        if now - last_kill_time < 2000:
            kill_streak += 1
        else:
            kill_streak = 1
        last_kill_time = now
        combo_decay_timer = combo_decay_window
        combo_max_streak = max(combo_max_streak, kill_streak)
        gained, variety_bonus = _style_gain_with_variation(str(action_tag), 20 * kill_streak)
        total_gain = gained + variety_bonus
        style_points += total_gain
        style_breakdown['kills'] += total_gain
        hitstop_timer = max(hitstop_timer, 0.03)
        if kill_streak >= 2:
            bonus = 50 * kill_streak
            score.add_bonus(bonus)
            damage_numbers.append(DamageNumber(
                f"x{kill_streak} COMBO! +{bonus}", cx, cy - 20, (255, 160, 50)))
        if variety_bonus > 0:
            damage_numbers.append(DamageNumber(
                f"VARIETY +{variety_bonus}", cx, cy - 36, (185, 245, 170)))
        if kill_streak > 0 and kill_streak % 5 == 0:
            finisher = 250 + 50 * (kill_streak // 5)
            score.add_bonus(finisher)
            finisher_style, finisher_variety = _style_gain_with_variation('finisher', 100)
            finisher_gain = finisher_style + finisher_variety
            style_points += finisher_gain
            style_breakdown['finishers'] += finisher_gain
            damage_numbers.append(DamageNumber(
                f"FINISHER +{finisher}", cx, cy - 44, (255, 90, 210)))
            if finisher_variety > 0:
                damage_numbers.append(DamageNumber(
                    f"CHAIN VARIETY +{finisher_variety}", cx, cy - 64, (185, 245, 170)))

    def _award_movement_style(action_key, amount, label, cx, cy, refresh_combo=False):
        nonlocal style_points, style_breakdown, combo_decay_timer
        if movement_style_cooldowns[action_key] > 0:
            return
        movement_style_cooldowns[action_key] = 0.8 if action_key == 'slide' else 1.2
        gained, variety_bonus = _style_gain_with_variation(str(action_key), amount)
        total_gain = gained + variety_bonus
        style_points += total_gain
        style_breakdown['movement'] += total_gain
        if refresh_combo:
            combo_decay_timer = max(combo_decay_timer, combo_decay_window * 0.5)
        msg = f"{label} +{gained}"
        if variety_bonus > 0:
            msg += f" (+{variety_bonus} VAR)"
        damage_numbers.append(DamageNumber(msg, cx, cy - 16, (120, 240, 255)))

    def _resolve_siege_enemy_hit(enemy, damage, color=(255, 180, 90), remove_ranged_support=False):
        nonlocal enemies_killed
        if enemy is None or not getattr(enemy, 'alive', False):
            return
        enemy_died = enemy.take_damage(int(damage)) if hasattr(enemy, 'take_damage') else True
        if not enemy_died:
            return
        enemies_killed += 1
        spawn_death_particles(enemy.rect.centerx, enemy.rect.centery, color)
        _register_kill(enemy.rect.centerx, enemy.rect.centery)
        if remove_ranged_support:
            for g in guns[:]:
                if getattr(g, 'owner', None) is enemy:
                    try:
                        guns.remove(g)
                    except ValueError:
                        pass
            for b in bullets.all()[:]:
                if getattr(b, 'owner', None) is enemy:
                    try:
                        if b in bullets.bullets:
                            bullets.bullets.remove(b)
                    except ValueError:
                        pass

    def play_boss_intro_cutscene(screen, boss_obj, player_obj, modifier_info=None):
        intro_clock = pygame.time.Clock()
        intro_duration = 3.2
        elapsed = 0.0
        intro_player_img = pygame.transform.scale(player_obj.get_image(), (60, 90))
        intro_boss_img = pygame.transform.scale(boss_obj.get_image(), (160, 220))

        while elapsed < intro_duration:
            dt_intro = intro_clock.tick(60) / 1000.0
            elapsed += dt_intro

            for evt in pygame.event.get():
                if evt.type == pygame.QUIT:
                    return False

            screen.fill((8, 8, 12))
            stage_rect = pygame.Rect(0, int(screen.get_height() * 0.68), screen.get_width(), int(screen.get_height() * 0.32))
            pygame.draw.rect(screen, (30, 24, 24), stage_rect)

            if elapsed < 0.9:
                fade_in_alpha = max(0, min(255, int(255 * (1.0 - (elapsed / 0.9)))))
            else:
                fade_in_alpha = 0

            if elapsed > intro_duration - 0.9:
                fade_out_alpha = max(0, min(255, int(255 * ((elapsed - (intro_duration - 0.9)) / 0.9))))
            else:
                fade_out_alpha = 0

            p_x = int(screen.get_width() * 0.26)
            p_y = stage_rect.top - intro_player_img.get_height() + 6
            b_x = int(screen.get_width() * 0.62)
            b_y = stage_rect.top - intro_boss_img.get_height() + 6

            screen.blit(intro_player_img, (p_x, p_y))
            screen.blit(intro_boss_img, (b_x, b_y))

            swing = (elapsed * 7.5) % 1.0
            if swing > 0.5:
                swing = 1.0 - swing
            swing *= 2.0
            axe_base = pygame.Surface((56, 84), pygame.SRCALPHA)
            pygame.draw.rect(axe_base, (120, 80, 45), (24, 14, 6, 66))
            pygame.draw.polygon(axe_base, (200, 200, 210), [(30, 14), (54, 18), (48, 30), (30, 26)])
            swing_angle = -40 + (120 * swing)
            axe_img = pygame.transform.rotate(axe_base, -swing_angle)
            axe_rect = axe_img.get_rect(center=(b_x + 34, b_y + 54))
            screen.blit(axe_img, axe_rect)

            title_font = pygame.font.SysFont("Arial", 44, bold=True)
            sub_font = pygame.font.SysFont("Arial", 28)
            mod_font = pygame.font.SysFont("Arial", 22, bold=True)
            title = title_font.render("Boss Encounter", True, (255, 120, 120))
            subtitle = sub_font.render("The boss enters with a heavy axe...", True, (240, 240, 240))
            screen.blit(title, ((screen.get_width() - title.get_width()) // 2, 90))
            screen.blit(subtitle, ((screen.get_width() - subtitle.get_width()) // 2, 145))
            if modifier_info:
                mod_label = mod_font.render(f"Weekly Modifier: {modifier_info.get('label', 'Unknown')}", True, (255, 220, 140))
                mod_desc = sub_font.render(str(modifier_info.get('description', '')), True, (220, 225, 235))
                screen.blit(mod_label, ((screen.get_width() - mod_label.get_width()) // 2, 186))
                screen.blit(mod_desc, ((screen.get_width() - mod_desc.get_width()) // 2, 216))

            overlay_alpha = max(fade_in_alpha, fade_out_alpha)
            if overlay_alpha > 0:
                overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, overlay_alpha))
                screen.blit(overlay, (0, 0))

            pygame.display.update()

        return True
    
    pygame.display.set_caption("Lost Horizon") #sets the title of the game to "Lost Horizon"
    while running:
        dt = local_clock.tick(60) / 1000 # dt is delta time (seconds per frame)
        frame_ms = dt * 1000.0
        recent_frame_ms.append(frame_ms)
        if len(recent_frame_ms) > 180:
            recent_frame_ms.pop(0)
        perf_frame_counter += 1
        perf_elapsed += dt
        perf_spike_cooldown = max(0.0, perf_spike_cooldown - dt)
        perf_peak_frame_ms = max(perf_peak_frame_ms, frame_ms)
        fps_live_for_event = 0.0 if dt <= 0 else (1.0 / max(0.0001, dt))
        if (
            player_name
            and frame_ms >= 34.0
            and perf_spike_cooldown <= 0.0
            and perf_spike_count < 40
        ):
            try:
                spike_meta = json.dumps(
                    {
                        'frame_ms': round(frame_ms, 3),
                        'fps': round(fps_live_for_event, 2),
                        'frame_sample': int(perf_frame_counter),
                    },
                    separators=(",", ":"),
                )
                log_analytics_event(
                    player_name,
                    'perf_spike',
                    level_id=stats_level_id,
                    x=int(round(frame_ms * 100.0)),
                    y=int(round(fps_live_for_event * 10.0)),
                    meta=spike_meta,
                )
                perf_spike_count += 1
                perf_spike_cooldown = 1.5
            except Exception:
                pass
        if hitstop_timer > 0:
            dt *= 0.2

        # This ensures there is a screen display
        # get_surface() will return it from the main program, otherwise it creates a default one.
        screen = pygame.display.get_surface()
        if screen is None:
            info = pygame.display.Info()
            screen = pygame.display.set_mode((info.current_w, info.current_h))
            pygame.display.set_caption(f'Lost Horizon - {level_name}')

        # run one-time initialization when a screen is available
        if not initialized:

            seasonal_event = get_active_event()
            seasonal_coin_mult = (seasonal_event or {}).get("coin_mult", 1.0)
            seasonal_gravity_mult = (seasonal_event or {}).get("gravity_mult", 1.0)

            try:
                ng_plus_active = is_ng_plus_enabled(player_name)
            except Exception:
                ng_plus_active = False

            if stats_level_id is not None and isinstance(race_replay, dict):
                rr_frames = list(race_replay.get("frames", []) or [])
                if rr_frames and int(race_replay.get("level_id", -1)) == int(level_id):
                    ghost_payload = race_replay
                else:
                    ghost_payload = None
            elif stats_level_id is not None:
                ghost_payload = get_best_replay_for_level(level_id, exclude_player_name=player_name)
            else:
                ghost_payload = None
            if ghost_payload:
                ghost_frames = ghost_payload.get("frames", [])
                ghost_time = ghost_payload.get("completion_time")
                ghost_owner_name = ghost_payload.get("player_name")
                ghost_replay_id = ghost_payload.get("replay_id")
                ghost_cursor = 0
            else:
                ghost_frames = []
                ghost_time = None
                ghost_owner_name = None
                ghost_replay_id = None
                ghost_cursor = 0
            ghost_record_frames = []
            ghost_record_timer = 0.0
            replay_video_frames = []
            replay_video_timer = 0.0

            level_objects = load_level_from_config(level_config, ng_plus=ng_plus_active, challenge_seed=challenge_seed)
            

            platforms = level_objects['platforms'] #creates a list of platform objects
            walls = level_objects['walls'] #creates a list of wall objects
            rotating_firewalls = level_objects['rotating_firewalls'] #creates a list of rotating firewall objects
            coins = level_objects['coins'] #creates a list of coin objects
            total_level_coins = len(coins)
            melee_enemies = level_objects['melee_enemies'] # creates a list for enemies
            ranged_enemies = level_objects['ranged_enemies'] # creates a list for ranged enemies
            charger_enemies = level_objects['charger_enemies']
            shield_enemies = level_objects['shield_enemies']
            healer_enemies = level_objects.get('healer_enemies', [])
            summoner_enemies = level_objects.get('summoner_enemies', [])
            teleport_enemies = level_objects.get('teleport_enemies', [])
            boss = level_objects['boss']
            finish_line = level_objects['finish_line'] # creates the finish line object
            guns = level_objects['guns']
            float_powers = level_objects['float_powers']
            invincibility_powers = level_objects['invincibility_powers']
            fire_powers = level_objects['fire_powers']
            bullets = level_objects['bullets']
            world_width = level_objects['world_width']
            world_height = level_objects['world_height']

            font = pygame.font.Font(None, 36)
            player = Player('player sprite.png', 0, 330, orientation='right') # creates a player object at thde coordinates specified
            player.max_health = 50
            player.health = player.max_health
            player.damage_cooldown = 0.0
            respawn_lock_timer = 0.0
            background = Background(level_config.get('background_image', 'background.png'))
            controls_text = Text('Controls: A/D to move, SPACE to jump, P to pause', 50, 50, pygame.font.SysFont("Arial", 24))   
            player.y_velocity = 0.0  # initialize vertical velocity
            player.x_velocity = 0.0  # initialize horizontal velocity
            jumping = False  # initialize jumping state
            camera = Camera_Movement(0, 0, screen.get_width(), screen.get_height())
            camera.speed = 5.0 # initialize camera speed
            timer = Timer()
            timer.pause_timer()  # start paused until first unpause
            timer_started = False
            score = Score(timer.get_elapsed_time(), coins_collected=0)
            coins_collected = 0
            initialized = True
            if world_tutorial_cards:
                tutorial_card_index = 0
                tutorial_card_timer = tutorial_card_duration
            enemies_killed = 0
            damage_numbers = []
            death_particles = []
            footstep_timer = 0.0
            shake_timer = 0.0
            fade_in_timer = 0.5
            last_kill_time = 0
            kill_streak = 0
            checkpoints = []
            active_checkpoint = None
            cp_cfgs = level_config.get('checkpoints', [])
            if cp_cfgs:
                for cp_cfg in cp_cfgs:
                    checkpoints.append(Checkpoint(cp_cfg['x'], cp_cfg['y']))
            else:
                checkpoints = _auto_section_checkpoints(level_config, platforms)
            hud_life_img = pygame.transform.scale(
                pygame.image.load('life.png').convert_alpha(), (22, 22))
            hud_coin_img = pygame.transform.scale(
                pygame.image.load('coin.png').convert_alpha(), (22, 22))

            warn_font = pygame.font.SysFont("Arial", 18, bold=True)
            bar_label_font = pygame.font.SysFont("Arial", 16)
            # Query personal best score for HUD
            try:
                if get_best_score_hook is not None and custom_level_id is not None:
                    hud_best_score = get_best_score_hook(player_name, custom_level_id)
                elif stats_level_id is not None:
                    hud_best_score = get_player_best_score(player_name, stats_level_id)
                else:
                    hud_best_score = None
            except Exception:
                hud_best_score = None

            try:
                meta_upgrades = get_meta_upgrades(player_name)
            except Exception:
                meta_upgrades = {'mobility': 0, 'survivability': 0, 'economy': 0}

            mobility_lvl = int(meta_upgrades.get('mobility', 0))
            survivability_lvl = int(meta_upgrades.get('survivability', 0))
            economy_lvl = int(meta_upgrades.get('economy', 0))

            base_player_speed = int(150 * (1.0 + 0.04 * max(0, min(10, mobility_lvl))))
            bonus_hp = int(5 * max(0, min(10, survivability_lvl)))
            player.max_health = 50 + bonus_hp
            player.health = player.max_health
            seasonal_coin_mult *= (1.0 + 0.06 * max(0, min(10, economy_lvl)))

            # Adaptive difficulty: ease enemies if the player has struggled here
            try:
                if stats_level_id is not None:
                    death_count = get_player_death_count(player_name, stats_level_id)
                    if death_count >= 5:
                        for e in melee_enemies + charger_enemies + shield_enemies:
                            e.patrol_speed = max(40, int(e.patrol_speed * 0.82))
                            e.chase_speed  = max(70, int(e.chase_speed  * 0.82))
                        for e in ranged_enemies:
                            e.cooldown = e.cooldown * 1.35
            except Exception:
                pass
            # NG+ stronger AI and enemies
            if ng_plus_active:
                for e in melee_enemies + charger_enemies + shield_enemies:
                    e.patrol_speed = int(e.patrol_speed * 1.28)
                    e.chase_speed = int(e.chase_speed * 1.3)
                    if hasattr(e, 'max_health'):
                        e.max_health = int(e.max_health * 1.35)
                        e.health = e.max_health
                for e in ranged_enemies:
                    e.cooldown = max(0.45, e.cooldown * 0.74)
                    e.bullet_speed = int(e.bullet_speed * 1.22)
                    e.max_health = int(e.max_health * 1.35)
                    e.health = e.max_health
                if boss:
                    boss.max_health = int(boss.max_health * 1.45)
                    boss.health = boss.max_health
                    boss.attack_damage = int(boss.attack_damage * 1.2)
            if seasonal_event is not None:
                esm = max(0.6, float(seasonal_event.get("enemy_speed_mult", 1.0)))
                for e in melee_enemies + charger_enemies + shield_enemies:
                    e.patrol_speed = int(e.patrol_speed * esm)
                    e.chase_speed = int(e.chase_speed * esm)
                for e in ranged_enemies:
                    e.cooldown = max(0.35, e.cooldown / esm)
                    e.bullet_speed = int(e.bullet_speed * esm)
                if boss:
                    boss.speed = int(boss.speed * esm)
            if challenge_mods:
                em = float(challenge_mods.get('enemy_mult', 1.0))
                gm = float(challenge_mods.get('gravity_mult', 1.0))
                cm = float(challenge_mods.get('coin_mult', 1.0))
                seasonal_gravity_mult *= max(0.6, min(1.7, gm))
                seasonal_coin_mult *= max(0.5, min(2.0, cm))
                for e in melee_enemies + charger_enemies + shield_enemies:
                    e.patrol_speed = int(e.patrol_speed * max(0.7, min(1.8, em)))
                    e.chase_speed = int(e.chase_speed * max(0.7, min(1.8, em)))
                for e in ranged_enemies:
                    e.cooldown = max(0.3, e.cooldown / max(0.7, min(1.8, em)))
                    e.bullet_speed = int(e.bullet_speed * max(0.7, min(1.8, em)))

                if challenge_variant:
                    variant_enemy_speed = float(challenge_variant.get('enemy_speed_mult', 1.0) or 1.0)
                    variant_enemy_health = float(challenge_variant.get('enemy_health_mult', 1.0) or 1.0)
                    variant_bullet_speed = float(challenge_variant.get('bullet_speed_mult', 1.0) or 1.0)
                    variant_gravity = float(challenge_variant.get('gravity_mult', 1.0) or 1.0)
                    variant_coin = float(challenge_variant.get('coin_mult', 1.0) or 1.0)
                    variant_combo_decay = float(challenge_variant.get('combo_decay_mult', 1.0) or 1.0)
                    variant_siege_cd = float(challenge_variant.get('siege_cooldown_mult', 1.0) or 1.0)

                    seasonal_gravity_mult *= max(0.7, min(1.3, variant_gravity))
                    seasonal_coin_mult *= max(0.7, min(1.6, variant_coin))
                    combo_decay_window = max(1.8, min(4.6, combo_decay_window * max(0.6, min(1.4, variant_combo_decay))))

                    for e in melee_enemies + charger_enemies + shield_enemies:
                        e.patrol_speed = int(e.patrol_speed * max(0.75, min(1.35, variant_enemy_speed)))
                        e.chase_speed = int(e.chase_speed * max(0.75, min(1.35, variant_enemy_speed)))
                        if hasattr(e, 'max_health'):
                            e.max_health = max(1, int(e.max_health * max(0.75, min(1.45, variant_enemy_health))))
                            e.health = min(e.max_health, max(1, int(getattr(e, 'health', e.max_health))))
                    for e in ranged_enemies:
                        e.cooldown = max(0.26, e.cooldown / max(0.75, min(1.35, variant_enemy_speed)))
                        e.bullet_speed = int(e.bullet_speed * max(0.7, min(1.5, variant_bullet_speed)))
                        e.max_health = max(1, int(e.max_health * max(0.75, min(1.45, variant_enemy_health))))
                        e.health = min(e.max_health, max(1, int(getattr(e, 'health', e.max_health))))
                    if siege_enabled:
                        siege_timer = max(2.0, float(siege_timer) * max(0.65, min(1.4, variant_siege_cd)))

            if boss and boss_weekly_modifier:
                _apply_weekly_boss_modifier(boss, boss_weekly_modifier, rotating_firewalls, level_config, level_id=stats_level_id)

            if easy_mode:
                # Training-ground assist: keep enemies mostly static and reduce ranged pressure.
                for e in melee_enemies + charger_enemies + shield_enemies:
                    e.patrol_speed = 0
                    e.chase_speed = 0
                    if hasattr(e, 'charge_speed'):
                        e.charge_speed = 0
                    if hasattr(e, 'bash_speed'):
                        e.bash_speed = 0
                for e in ranged_enemies:
                    e.cooldown = e.cooldown * 2.4
                    if hasattr(e, 'bullet_speed'):
                        e.bullet_speed = max(120, int(e.bullet_speed * 0.55))
                if boss:
                    boss.MOVE_SPEED = 0
                    boss.attack_cooldown = max(2.4, boss.attack_cooldown * 1.45)

            weather_pick_id = stats_level_id if stats_level_id is not None else (abs(hash(level_name)) % 100000)
            dynamic_weather = _pick_dynamic_weather(weather_pick_id, challenge_seed=challenge_seed)
            if dynamic_weather is not None:
                dynamic_weather_key = dynamic_weather.get('key', 'clear')
                weather_wind_force = float(dynamic_weather.get('wind_force', 0.0))
            # Player skin tint loaded from DB
            try:
                skin_key = get_player_skin(player_name)
                _skin_colors = {'gold': (130, 95, 20), 'shadow': (20, 20, 110), 'neon': (20, 170, 150)}
                player_skin_tint = _skin_colors.get(skin_key)
            except Exception:
                player_skin_tint = None
            if seasonal_event is not None:
                evt_tint = seasonal_event.get("player_tint")
                if evt_tint is not None:
                    if player_skin_tint is None:
                        player_skin_tint = evt_tint
                    else:
                        player_skin_tint = (
                            min(255, player_skin_tint[0] + evt_tint[0] // 2),
                            min(255, player_skin_tint[1] + evt_tint[1] // 2),
                            min(255, player_skin_tint[2] + evt_tint[2] // 2),
                        )
            lives = get_player_lives(conn, player_name)
            if get_powerup_count(conn, player_name, 'float') > 0:
                player.float_power_collected = True
            if get_powerup_count(conn, player_name, 'fire') > 0:
                player.fire_power_collected = True
                if fire_powers:
                    fire_powers[0].collected = True  # mark as collected in level
            if get_powerup_count(conn, player_name, 'invincibility') > 0:
                player.invincibility_collected = True

            if boss and not boss_intro_played:
                keep_running = play_boss_intro_cutscene(screen, boss, player, modifier_info=boss_weekly_modifier)
                if not keep_running:
                    return False
                boss_intro_played = True

            conn.close()

            
        start_plat = platforms[0]

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                elapsed_now = timer.get_elapsed_time() if timer is not None else 0.0
                if score is not None and timer is not None:
                    score.calculate_score(elapsed_now, coins_collected, enemies_killed, level_deaths)
                _prompt_save_failed_replay(
                    screen,
                    player_name,
                    stats_level_id if stats_level_id is not None else level_id,
                    elapsed_now,
                    score.total_score if score is not None else 0,
                    ghost_record_frames,
                    replay_video_frames,
                )
                return False

            if action_down(event, keybinds, 'pause'):
            # block until the user resumes or quits
                timer.pause_timer()  # pause the timer
                keep_running = pause_game(stats={
                    'time': timer.get_elapsed_time(),
                    'coins': coins_collected,
                    'kills': enemies_killed,
                })
                timer.resume_timer()  # resume the timer
                # reset the local clock to avoid a large dt after pausing
                local_clock.tick()
                if not keep_running:
                    elapsed_now = timer.get_elapsed_time() if timer is not None else 0.0
                    if score is not None and timer is not None:
                        score.calculate_score(elapsed_now, coins_collected, enemies_killed, level_deaths)
                    _prompt_save_failed_replay(
                        screen,
                        player_name,
                        stats_level_id if stats_level_id is not None else level_id,
                        elapsed_now,
                        score.total_score if score is not None else 0,
                        ghost_record_frames,
                        replay_video_frames,
                    )
                    return True  # return to play menu
            if action_down(event, keybinds, 'ghost_toggle'):
                ghost_enabled = not ghost_enabled
            if action_down(event, keybinds, 'debug_overlay'):
                debug_overlay = not debug_overlay
            if action_down(event, keybinds, 'jump'):
                jump_buffer_timer = jump_buffer_window
            if action_down(event, keybinds, 'dash'):
                if jumping and not player_dash_used_air and player_dash_cooldown <= 0:
                    dash_dir = 1 if player.orientation == 'right' else -1
                    player_dash_velocity = 520 * dash_dir
                    player.x_velocity = player_dash_velocity
                    player_dash_timer = 0.16
                    player_dash_cooldown = 0.45
                    player_dash_used_air = True
                    _award_movement_style('air_dash', 35, 'AIR DASH', player.rect.centerx, player.rect.top, refresh_combo=True)
            if action_down(event, keybinds, 'slide'):
                if not jumping and abs(player.x_velocity) > 20:
                    player_slide_timer = 0.34
                    _award_movement_style('slide', 15, 'SLIDE', player.rect.centerx, player.rect.bottom)
            if action_down(event, keybinds, 'select_power_1'):
                selected_power_slot = 1
            if action_down(event, keybinds, 'select_power_2'):
                selected_power_slot = 2
            if action_down(event, keybinds, 'select_power_3'):
                selected_power_slot = 3
            if action_down(event, keybinds, 'activate_power'):
                _activate_selected_power(selected_power_slot)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # left click
                if player.fire_power_active:
                    # Spawn projectile
                    proj_x = player.rect.centerx
                    proj_y = player.rect.centery
                    
                    # Better direction control (can be improved later)
                    direction = 1 if player.orientation == 'right' else -1
                    vx = 480 * direction
                    vy = -180  # slight arc
                    
                    projectile = FireProjectile(proj_x, proj_y, vx, vy)
                    player.fire_projectiles.append(projectile)
                        
            
        keys = pygame.key.get_pressed()

        if hasattr(player, 'damage_cooldown') and player.damage_cooldown > 0:
            player.damage_cooldown = max(0.0, player.damage_cooldown - dt)
        if hitstop_timer > 0:
            hitstop_timer = max(0.0, hitstop_timer - dt)
        if respawn_lock_timer > 0:
            respawn_lock_timer = max(0.0, respawn_lock_timer - dt)
        if boss_contact_damage_cooldown > 0:
            boss_contact_damage_cooldown = max(0.0, boss_contact_damage_cooldown - dt)
        if player_dash_cooldown > 0:
            player_dash_cooldown = max(0.0, player_dash_cooldown - dt)
        if wall_jump_cooldown > 0:
            wall_jump_cooldown = max(0.0, wall_jump_cooldown - dt)
        for action_key in movement_style_cooldowns:
            if movement_style_cooldowns[action_key] > 0:
                movement_style_cooldowns[action_key] = max(0.0, movement_style_cooldowns[action_key] - dt)
        now_ticks = pygame.time.get_ticks()
        style_recent_actions = [pair for pair in style_recent_actions if (now_ticks - int(pair[0])) <= style_recent_window_ms]
        if combo_decay_timer > 0:
            combo_decay_timer = max(0.0, combo_decay_timer - dt)
        elif kill_streak > 0:
            kill_streak = max(0, kill_streak - 1)
        if style_points > 0:
            combat_active = combo_decay_timer > 0 or (now_ticks - last_kill_time) <= 2600
            if (not combat_active) and (now_ticks - style_last_gain_ms) > style_decay_grace_ms:
                style_decay = max(1, int(style_decay_rate * dt))
                applied_decay = min(style_points, style_decay)
                style_points -= applied_decay
                style_breakdown['penalties'] += applied_decay

        if not timer_started and (
            action_pressed(keys, keybinds, 'move_left') or
            action_pressed(keys, keybinds, 'move_right') or
            action_pressed(keys, keybinds, 'jump')):
            timer_started = True
            timer.resume_timer()

        if tutorial_card_timer > 0:
            tutorial_card_timer = max(0.0, tutorial_card_timer - dt)
        elif world_tutorial_cards and tutorial_card_index < len(world_tutorial_cards) - 1:
            tutorial_card_index += 1
            tutorial_card_timer = tutorial_card_duration

        if not hasattr(player, 'speed_boost_timer'):
            player.speed_boost_timer = 0.0
        if not hasattr(player, 'speed_boost_multiplier'):
            player.speed_boost_multiplier = 1.25

        if player.speed_boost_timer > 0:
            player.speed_boost_timer = max(0.0, player.speed_boost_timer - dt)
            platform_speed_mult = player.speed_boost_multiplier
        else:
            platform_speed_mult = 1.0
        invincibility_speed_mult = 2.0 if getattr(player, 'invincibility_active', False) else 1.0
        speed = int(base_player_speed * platform_speed_mult * invincibility_speed_mult)
        if player_slide_timer > 0:
            speed = int(speed * 1.38)
            player_slide_timer = max(0.0, player_slide_timer - dt)
        jump_power = 350 #initial jump velocity
        gravity = 750 * seasonal_gravity_mult #pixels per second squared
        prev_rect = player.rect.copy()

        # ensure player power state fields exist
        if not hasattr(player, 'float_power_collected'):
            player.float_power_collected = False
        if not hasattr(player, 'float_power_active'):
            player.float_power_active = False
            player.float_time_remaining = 0.0
        if not hasattr(player, 'invincibility_collected'):
            player.invincibility_collected = False
        # Backward compatibility for older attribute name.
        if hasattr(player, 'invincibility_power_collected') and player.invincibility_power_collected:
            player.invincibility_collected = True
        if not hasattr(player, 'invincibility_active'):
            player.invincibility_active = False
            player.invincibility_time_remaining = 0.0
        if not hasattr(player, 'fire_power_collected'):
            player.fire_power_collected = False
        if not hasattr(player, 'fire_power_active'):
            player.fire_power_active = False
            player.fire_power_time_remaining = 0.0
        if not hasattr(player, 'fire_projectiles'):
            player.fire_projectiles = []  # list of active FireProjectile objects

        if not hasattr(player, 'y_velocity'): #initialize y_velocity attribute
            player.y_velocity = 0

        if jump_buffer_timer > 0 and respawn_lock_timer <= 0 and ((jumping == False) or coyote_timer > 0):
            # if float power active, increase jump power
            effective_jump = jump_power
            slide_jump = player_slide_timer > 0
            if player.float_power_active:
                effective_jump = int(jump_power * 1.2)
            if slide_jump:
                effective_jump = int(effective_jump * 1.3)
            player.y_velocity = -effective_jump #applies an initial upward velocity to the player when jumping 
            jumping = True
            coyote_timer = 0.0
            jump_buffer_timer = 0.0
            if slide_jump:
                _award_movement_style('slide_jump', 45, 'SLIDE JUMP', player.rect.centerx, player.rect.top, refresh_combo=True)
            try:
                if JUMP_SFX:
                    settings = load_settings()
                    if settings.get("sfx_on", True):
                        sfx_volume = settings.get("sfx_volume", 0.6)
                        JUMP_SFX.set_volume(sfx_volume)
                        JUMP_SFX.play()
            except Exception:
                pass

        # Decay jump windows after evaluating jump this frame; avoids dropped input on high-dt frames.
        if coyote_timer > 0:
            coyote_timer = max(0.0, coyote_timer - dt)
        if jump_buffer_timer > 0:
            jump_buffer_timer = max(0.0, jump_buffer_timer - dt)

        if respawn_lock_timer > 0:
            player.x_velocity = 0
            movement_intent = False
        elif player_dash_timer > 0:
            player.x_velocity = player_dash_velocity
            movement_intent = False
        else:
            desired_x = 0.0
            moving_left = action_pressed(keys, keybinds, 'move_left')
            moving_right = action_pressed(keys, keybinds, 'move_right')
            movement_intent = moving_left ^ moving_right
            if moving_left and not moving_right:
                desired_x = -float(speed)
                player.orientation = 'left'
            elif moving_right and not moving_left:
                desired_x = float(speed)
                player.orientation = 'right'
            player.x_velocity = desired_x

        # Apply horizontal movement
        if player_dash_timer > 0:
            player_dash_timer = max(0.0, player_dash_timer - dt)
            if player_dash_timer == 0:
                player_dash_velocity = 0.0
        player.rect.x += player.x_velocity * dt

        is_moving = movement_intent and abs(player.x_velocity) > 12

        # update rect for drawing/collision
        player.update_position()
        # Apply gravity
        prev_rect_y = player.rect.copy()
        was_grounded = not jumping
        on_ground_this_frame = False

        prev_y_velocity = player.y_velocity
        max_fall_speed = 1000
        # apply gravity, reduce gravity while float is active to create a gliding effect
        if getattr(player, 'float_power_active', False):
            glide_factor = 0.35
            player.y_velocity += gravity * glide_factor * dt
            # cap falling speed to a gentler terminal velocity while gliding
            glide_terminal = 200
            if player.y_velocity > glide_terminal:
                player.y_velocity = glide_terminal
        else:
            player.y_velocity += gravity * dt
            if player.y_velocity > max_fall_speed:
                player.y_velocity = max_fall_speed

        player.rect.y += player.y_velocity * dt

        # update rect for drawing/collision
        player.update_position()

        # Single-pass collision resolution using previous rects to determine collision side.
        # Land on top when previous bottom was above platform top and now overlapping.
        # Hit head when previous top was below platform bottom and now overlapping.
        # Otherwise treat as a side collision: revert horizontal movement and start a fall.
        for plat in platforms:
            if plat.active and player.rect.colliderect(plat.rect):
                if prev_rect.bottom <= plat.rect.top and player.rect.bottom >= plat.rect.top:
                    player.rect.bottom = plat.rect.top
                    player.y_velocity = 0.0
                    jumping = False
                    on_ground_this_frame = True
                    coyote_timer = coyote_time_window
                    player_dash_used_air = False
                    # Landing dust if landing with enough downward speed
                    if prev_y_velocity > 80:
                        n = min(5, max(2, int(prev_y_velocity / 120)))
                        for _ in range(n):
                            ang = random.uniform(math.pi * 0.85, math.pi * 2.15)
                            spd = random.uniform(25, 80)
                            death_particles.append(DeathParticle(
                                player.rect.centerx + random.randint(-8, 8),
                                player.rect.bottom,
                                math.cos(ang) * spd, math.sin(ang) * spd * 0.25,
                                (195, 180, 155)))
                    if getattr(plat, 'decay_on_step', False):
                        # start decay when player lands on this configured decaying platform
                        plat.start_decay()
                    if getattr(plat, 'bounce_on_step', False):
                        player.y_velocity = -jump_power * 2  # stronger bounce
                        jumping = True
                    if getattr(plat, 'speed_boost_on_step', False):
                        plat.apply_speed_boost(player)
                # hit head on bottom of platform
                elif prev_rect.top >= plat.rect.bottom and player.rect.top <= plat.rect.bottom:
                    player.rect.top = plat.rect.bottom
                    player.y_velocity = 0.0
                else:
                    # side collision: revert horizontal move and make player start falling
                    player.rect.x = prev_rect.x
                    player.x_velocity = 0
                    # if player was previously standing on top, nudge them downward to initiate fall
                    if prev_rect.bottom <= plat.rect.top:
                        jumping = True
                        # give a small downward nudge so gravity takes over cleanly
                        player.y_velocity = max(player.y_velocity, 50.0)
                    else:
                        # collided in air from the side — ensure we are in falling state
                        jumping = True
                # update rect for drawing/collision

        # Allow speed boost platforms to trigger again after player leaves them.
        for plat in platforms:
            if getattr(plat, 'speed_boost_on_step', False) and not player.rect.colliderect(plat.rect):
                plat.reset_speed_boost_trigger()
        
        player_wall_sliding = False
        for wall in walls:
            if player.rect.colliderect(wall.rect):
                if (prev_rect.right <= wall.rect.left and player.rect.right >= wall.rect.left) or (prev_rect.left >= wall.rect.right and player.rect.left <= wall.rect.right):
                    # simple resolution: revert to previous position
                    player.rect.x = prev_rect.x
                    player.x_velocity = 0
                    jumping = True  # ensure we are in falling state
                    player_wall_sliding = True  # trigger wall-slide animation
                    # Wall jump tech: jump away from wall while airborne.
                    if action_pressed(keys, keybinds, 'jump') and wall_jump_cooldown <= 0:
                        player_wall_sliding = False  # leave wall_slide anim on jump
                        jump_dir = -1 if prev_rect.centerx < wall.rect.centerx else 1
                        player.y_velocity = -jump_power * 0.95
                        player.x_velocity = 260 * jump_dir
                        wall_jump_cooldown = 0.22
                        player_wall_sliding = False
                        _award_movement_style('wall_jump', 40, 'WALL JUMP', player.rect.centerx, player.rect.top, refresh_combo=True)
                elif (prev_rect.bottom <= wall.rect.top and player.rect.bottom >= wall.rect.top):
                    player.rect.bottom = wall.rect.top
                    player.y_velocity = 0.0
                    jumping = False
                    on_ground_this_frame = True
                    coyote_timer = coyote_time_window
                    player_dash_used_air = False
                elif player.rect.top <= wall.rect.bottom and prev_rect.top >= wall.rect.bottom:
                    player.rect.top = wall.rect.bottom
                    player.y_velocity = 0.0

        # If the player walks off a ledge, start coyote time and mark airborne.
        if not on_ground_this_frame:
            if was_grounded and player.y_velocity >= 0:
                coyote_timer = max(coyote_timer, coyote_time_window)
            jumping = True

        # Use post-collision movement state so run/jump does not flicker on landings.
        grounded_for_anim = on_ground_this_frame or (coyote_timer > 0 and player.y_velocity >= 0 and abs(player.y_velocity) < 45)
        animation_jumping = (not grounded_for_anim) and abs(getattr(player, 'y_velocity', 0.0)) > 18
        player.update_animation(
            dt,
            is_moving,
            animation_jumping,
            sliding=player_slide_timer > 0,
            wall_sliding=player_wall_sliding,
            dashing=player_dash_timer > 0,
        )

        # Footstep sounds should also follow post-collision grounded state.
        if is_moving and grounded_for_anim and player_slide_timer <= 0 and player_dash_timer <= 0:
            footstep_timer -= dt
            if footstep_timer <= 0:
                _play_sfx(FOOTSTEP_SFX)
                footstep_timer = 0.32
        else:
            footstep_timer = min(footstep_timer, 0.08)
        
        # Update and check collision with rotating firewalls
        for fw in rotating_firewalls:
            fw.update(dt)
            # Check if player collides with firewall - player dies if not invincible
            if fw.check_collision(player):
                if respawn_lock_timer > 0:
                    continue
                if not getattr(player, 'invincibility_active', False):
                    # Player hit firewall and dies
                    try:
                        log_analytics_event(player_name, 'firewall_death', level_id=stats_level_id, x=player.rect.centerx, y=player.rect.centery)
                    except Exception:
                        pass
                    spawn_x = start_plat.rect.left + 5
                    player.rect.x = spawn_x
                    player.y_velocity = 0.0
                    player.x_velocity = 0.0
                    jumping = False
                    coyote_timer = coyote_time_window
                    jump_buffer_timer = 0.0
                    prev_rect = player.rect.copy()
                    lives -= 1
                    level_deaths += 1

        if siege_enabled and world_width:
            siege_timer -= dt
            if siege_timer <= 0:
                strike_xs = _build_siege_wave(
                    level_config,
                    player.rect,
                    [melee_enemies, charger_enemies, shield_enemies, ranged_enemies],
                    world_width,
                    siege_rng,
                )
                for strike_x in strike_xs:
                    siege_strikes.append({
                        'x': int(strike_x),
                        'width': int(siege_cfg.get('column_width', 86) or 86),
                        'phase': 'warning',
                        'timer': float(siege_cfg.get('warning_time', 1.0) or 1.0),
                        'applied': False,
                    })
                damage_numbers.append(DamageNumber("SIEGE", player.rect.centerx, player.rect.top - 28, (255, 210, 120)))
                siege_timer = float(siege_cfg.get('cooldown', 5.2) or 5.2) + siege_rng.uniform(0.0, float(siege_cfg.get('cooldown_jitter', 1.4) or 1.4))

            for strike in siege_strikes[:]:
                strike['timer'] -= dt
                if strike['phase'] == 'warning' and strike['timer'] <= 0:
                    strike['phase'] = 'impact'
                    strike['timer'] = float(siege_cfg.get('impact_duration', 0.2) or 0.2)

                if strike['phase'] == 'impact' and not strike['applied']:
                    strike['applied'] = True
                    hit_rect = pygame.Rect(
                        int(strike['x'] - strike['width'] // 2),
                        -200,
                        int(strike['width']),
                        int((world_height or screen.get_height()) + 400),
                    )
                    player_hb = player.hitbox if hasattr(player, 'hitbox') else player.rect
                    if player_hb.colliderect(hit_rect) and respawn_lock_timer <= 0:
                        damage_player(int(siege_cfg.get('damage', 28) or 28), source_x=int(strike['x']), heavy=True)
                    for enemy in melee_enemies:
                        if enemy.rect.colliderect(hit_rect):
                            _resolve_siege_enemy_hit(enemy, siege_cfg.get('enemy_damage', 9999), color=(255, 150, 110))
                    for enemy in charger_enemies:
                        if enemy.rect.colliderect(hit_rect):
                            _resolve_siege_enemy_hit(enemy, siege_cfg.get('enemy_damage', 9999), color=(255, 160, 120))
                    for enemy in shield_enemies:
                        if enemy.rect.colliderect(hit_rect):
                            _resolve_siege_enemy_hit(enemy, siege_cfg.get('enemy_damage', 9999), color=(255, 185, 120))
                    for enemy in ranged_enemies:
                        if enemy.rect.colliderect(hit_rect):
                            _resolve_siege_enemy_hit(enemy, siege_cfg.get('enemy_damage', 9999), color=(255, 175, 140), remove_ranged_support=True)
                    if boss and boss.alive and boss.hitbox.colliderect(hit_rect):
                        boss.take_damage(int(siege_cfg.get('boss_damage', 34) or 34))
                        damage_numbers.append(DamageNumber("BREACH", boss.rect.centerx, boss.rect.top - 12, (255, 150, 120)))

                if strike['phase'] == 'impact' and strike['timer'] <= 0:
                    siege_strikes.remove(strike)

        if boss and boss.alive:
            boss.update(dt, player)
            # Only the swinging axe can damage the player
            if boss.axe_swing_active:
                player_hb = player.hitbox if hasattr(player, 'hitbox') else player.rect
                if boss.axe_world_rect.colliderect(player_hb):
                    damage_player(boss.attack_damage, source_x=boss.rect.centerx, heavy=True)

            # Additional ways for player to damage the boss:
            # 1) Stomp from above, 2) invincibility body ram.
            player_hb = player.hitbox if hasattr(player, 'hitbox') else player.rect
            if player_hb.colliderect(boss.hitbox):
                stomped_boss = (
                    prev_rect.bottom <= boss.hitbox.top
                    and player.rect.bottom >= boss.hitbox.top
                    and player.y_velocity >= 0
                )
                if stomped_boss:
                    boss.take_damage(BOSS_STOMP_DAMAGE)
                    player.y_velocity = -320
                    jumping = True
                    boss_contact_damage_cooldown = 0.2
                elif getattr(player, 'invincibility_active', False) and boss_contact_damage_cooldown <= 0:
                    boss.take_damage(BOSS_INVINCIBILITY_RAM_DAMAGE)
                    boss_contact_damage_cooldown = 0.35

        if healer_enemies:
            healable = [e for e in (melee_enemies + charger_enemies + shield_enemies + ranged_enemies) if getattr(e, 'alive', False)]
            for healer in healer_enemies:
                if getattr(healer, 'alive', False):
                    healed_count = healer.try_heal(healable)
                    if healed_count > 0:
                        damage_numbers.append(DamageNumber("Heal Pulse", healer.rect.centerx, healer.rect.top - 10, (95, 245, 145)))

        if teleport_enemies and (not easy_mode):
            for tele in teleport_enemies:
                if getattr(tele, 'alive', False):
                    teleported = tele.try_teleport(player)
                    if teleported:
                        damage_numbers.append(DamageNumber("Blink", tele.rect.centerx, tele.rect.top - 8, (150, 200, 255)))

        if summoner_enemies and (not easy_mode):
            active_summoned = sum(1 for e in melee_enemies if getattr(e, 'spawned_by_summoner', False) and getattr(e, 'alive', False))
            for summoner in summoner_enemies:
                if not getattr(summoner, 'alive', False):
                    continue
                req = summoner.consume_summon_request(active_summoned)
                if req <= 0:
                    continue
                for _ in range(req):
                    sx = summoner.rect.centerx + random.randint(-70, 70)
                    sy = summoner.rect.y
                    spawned = Melee_Enemy(level_config.get('melee_enemy_image', 'melee enemy.png'), sx, sy)
                    spawned.spawned_by_summoner = True
                    best_plat = None
                    best_dist = float('inf')
                    for plat in platforms:
                        if plat.rect.left <= spawned.rect.centerx <= plat.rect.right:
                            dist = abs(spawned.rect.bottom - plat.rect.top)
                            if dist < best_dist:
                                best_dist = dist
                                best_plat = plat
                    spawned.platform = best_plat
                    melee_enemies.append(spawned)
                    active_summoned += 1
                damage_numbers.append(DamageNumber("Summon", summoner.rect.centerx, summoner.rect.top - 8, (255, 180, 120)))
        
        for enemy in melee_enemies:
            if hasattr(enemy, 'stagger_timer') and enemy.stagger_timer > 0:
                enemy.stagger_timer = max(0.0, enemy.stagger_timer - dt)
            # Run patrol / chase AI movement
            if enemy.alive:
                enemy.update_ai(player, dt)

            # Apply gravity so enemies fall off ledges they walk off
            if enemy.alive:
                prev_bottom = enemy.rect.bottom
                enemy.y_velocity += gravity * dt
                if enemy.y_velocity > 1000:
                    enemy.y_velocity = 1000
                enemy.rect.y += int(enemy.y_velocity * dt)
                enemy.on_ground = False
                for plat in platforms:
                    if not plat.active:
                        continue
                    x_overlap = enemy.rect.right > plat.rect.left and enemy.rect.left < plat.rect.right
                    crossed_top = prev_bottom <= plat.rect.top and enemy.rect.bottom >= plat.rect.top
                    overlapping = enemy.rect.colliderect(plat.rect)
                    if x_overlap and enemy.y_velocity >= 0 and (crossed_top or overlapping):
                            enemy.rect.bottom = plat.rect.top
                            enemy.y_velocity = 0.0
                            enemy.on_ground = True
                            # keep platform assignment current so patrol boundaries stay correct
                            enemy.platform = plat
                            break
                # Kill enemy if it falls out of the world
                if world_height is not None and enemy.rect.top > world_height:
                    enemy.alive = False

            # keep enemy hitbox synced (if enemy moves in future)
            if hasattr(enemy, 'update_position'): # keep hitbox synced with enemy's world rect
                enemy.update_position()
            
            # Check collision direction
            collision_direction = enemy.check_collision_direction(player, prev_rect)
            
            if collision_direction == 'top':
                # Player jumped on enemy's head - enemy dies
                enemy.alive = False
                enemies_killed += 1
                _play_sfx(ENEMY_DEATH_SFX)
                damage_numbers.append(DamageNumber("Stomp!", enemy.rect.centerx, enemy.rect.top, (255, 230, 50)))
                spawn_death_particles(enemy.rect.centerx, enemy.rect.centery)
                _register_kill(enemy.rect.centerx, enemy.rect.centery)
                # Bounce player upward
                player.y_velocity = -300
                jumping = True
            elif collision_direction == 'side':
                # If invincibility is active, enemy dies on side collision instead
                if getattr(player, 'invincibility_active', False):
                    enemy.alive = False
                    enemies_killed += 1
                    spawn_death_particles(enemy.rect.centerx, enemy.rect.centery)
                    _register_kill(enemy.rect.centerx, enemy.rect.centery)
                else:
                    # Player takes contact damage from melee enemies.
                    damage_player(MELEE_CONTACT_DAMAGE, source_x=enemy.rect.centerx)

        for enemy in charger_enemies:
            if hasattr(enemy, 'stagger_timer') and enemy.stagger_timer > 0:
                enemy.stagger_timer = max(0.0, enemy.stagger_timer - dt)
            if enemy.alive:
                enemy.update_ai(player, dt)
                prev_bottom = enemy.rect.bottom
                enemy.y_velocity += gravity * dt
                if enemy.y_velocity > 1000:
                    enemy.y_velocity = 1000
                enemy.rect.y += int(enemy.y_velocity * dt)
                for plat in platforms:
                    if not plat.active:
                        continue
                    x_overlap = enemy.rect.right > plat.rect.left and enemy.rect.left < plat.rect.right
                    crossed_top = prev_bottom <= plat.rect.top and enemy.rect.bottom >= plat.rect.top
                    overlapping = enemy.rect.colliderect(plat.rect)
                    if x_overlap and enemy.y_velocity >= 0 and (crossed_top or overlapping):
                            enemy.rect.bottom = plat.rect.top
                            enemy.y_velocity = 0.0
                            enemy.platform = plat
                            break
            if hasattr(enemy, 'update_position'):
                enemy.update_position()

            collision_direction = enemy.check_collision_direction(player, prev_rect)
            if collision_direction == 'top':
                enemy.alive = False
                enemies_killed += 1
                _play_sfx(ENEMY_DEATH_SFX)
                damage_numbers.append(DamageNumber("Stomp!", enemy.rect.centerx, enemy.rect.top, (255, 230, 50)))
                spawn_death_particles(enemy.rect.centerx, enemy.rect.centery)
                _register_kill(enemy.rect.centerx, enemy.rect.centery)
                player.y_velocity = -300
                jumping = True
            elif collision_direction == 'side':
                if getattr(player, 'invincibility_active', False):
                    enemy.alive = False
                    enemies_killed += 1
                    spawn_death_particles(enemy.rect.centerx, enemy.rect.centery)
                    _register_kill(enemy.rect.centerx, enemy.rect.centery)
                else:
                    heavy_hit = getattr(enemy, 'ai_state', '') == 'charge'
                    contact_damage = getattr(enemy, 'charge_contact_damage', MELEE_CONTACT_DAMAGE)
                    damage_player(contact_damage if heavy_hit else MELEE_CONTACT_DAMAGE, source_x=enemy.rect.centerx, heavy=heavy_hit)

        for enemy in shield_enemies:
            if hasattr(enemy, 'stagger_timer') and enemy.stagger_timer > 0:
                enemy.stagger_timer = max(0.0, enemy.stagger_timer - dt)
            if enemy.alive:
                enemy.update_ai(player, dt)
                prev_bottom = enemy.rect.bottom
                enemy.y_velocity += gravity * dt
                if enemy.y_velocity > 1000:
                    enemy.y_velocity = 1000
                enemy.rect.y += int(enemy.y_velocity * dt)
                for plat in platforms:
                    if not plat.active:
                        continue
                    x_overlap = enemy.rect.right > plat.rect.left and enemy.rect.left < plat.rect.right
                    crossed_top = prev_bottom <= plat.rect.top and enemy.rect.bottom >= plat.rect.top
                    overlapping = enemy.rect.colliderect(plat.rect)
                    if x_overlap and enemy.y_velocity >= 0 and (crossed_top or overlapping):
                            enemy.rect.bottom = plat.rect.top
                            enemy.y_velocity = 0.0
                            enemy.platform = plat
                            break
            if hasattr(enemy, 'update_position'):
                enemy.update_position()

            collision_direction = enemy.check_collision_direction(player, prev_rect)
            if collision_direction == 'top':
                enemy.alive = False
                enemies_killed += 1
                _play_sfx(ENEMY_DEATH_SFX)
                damage_numbers.append(DamageNumber("Stomp!", enemy.rect.centerx, enemy.rect.top, (255, 230, 50)))
                spawn_death_particles(enemy.rect.centerx, enemy.rect.centery)
                _register_kill(enemy.rect.centerx, enemy.rect.centery)
                player.y_velocity = -300
                jumping = True
            elif collision_direction == 'side':
                if getattr(player, 'invincibility_active', False):
                    enemy.alive = False
                    enemies_killed += 1
                    spawn_death_particles(enemy.rect.centerx, enemy.rect.centery)
                    _register_kill(enemy.rect.centerx, enemy.rect.centery)
                elif enemy.blocks_from_front(player):
                    damage_player(getattr(enemy, 'bash_contact_damage', MELEE_CONTACT_DAMAGE), source_x=enemy.rect.centerx, heavy=(getattr(enemy, 'ai_state', '') == 'bash'))
                else:
                    enemy.alive = False
                    enemies_killed += 1
                    damage_numbers.append(DamageNumber("Backstab!", enemy.rect.centerx, enemy.rect.top, (120, 240, 120)))
                    spawn_death_particles(enemy.rect.centerx, enemy.rect.centery)
                    _register_kill(enemy.rect.centerx, enemy.rect.centery)
        
        for enemy in ranged_enemies:
            if hasattr(enemy, 'stagger_timer') and enemy.stagger_timer > 0:
                enemy.stagger_timer = max(0.0, enemy.stagger_timer - dt)
            # keep enemy hitbox synced (if enemy moves in future)
            if hasattr(enemy, 'update_position'): # keep hitbox synced with enemy's world rect
                enemy.update_position()
            enemy_active = enemy.alive and player.rect.x > enemy.rect.x - 400 and player.rect.x < enemy.rect.x + 400
            enemy.update_animation(dt, enemy.alive)
            # shoot bullets (use dt and the bullet_manager)
            if enemy_active:
                enemy.shoot(dt, bullets, player)
            
            # Check collision direction
            collision_direction = enemy.check_collision_direction(player, prev_rect)
            
            if collision_direction == 'top' or (collision_direction == 'side' and getattr(player, 'invincibility_active', False)):
                # Player jumped on enemy's head OR invincible player collided from side -> enemy dies
                enemy.alive = False
                enemies_killed += 1
                _play_sfx(ENEMY_DEATH_SFX)
                damage_numbers.append(DamageNumber("Stomp!", enemy.rect.centerx, enemy.rect.top, (255, 230, 50)))
                spawn_death_particles(enemy.rect.centerx, enemy.rect.centery)
                _register_kill(enemy.rect.centerx, enemy.rect.centery)
                # remove associated gun(s)
                for g in guns[:]:
                    if getattr(g, 'owner', None) is enemy:
                        try:
                            guns.remove(g)
                        except ValueError:
                            pass
                # remove bullets fired by this enemy
                for b in bullets.all()[:]:
                    if getattr(b, 'owner', None) is enemy:
                        try:
                            if b in bullets.bullets:
                                bullets.bullets.remove(b)
                        except ValueError:
                            pass
                # Bounce player upward only for top stomps
                if collision_direction == 'top':
                    player.y_velocity = -300
                    jumping = True

                    # remove associated gun(s)
                    for g in guns[:]:
                        if getattr(g, 'owner', None) is enemy:
                            try:
                                guns.remove(g)
                            except ValueError:
                                pass
                    # remove bullets fired by this enemy
                    for b in bullets.all()[:]:
                        if getattr(b, 'owner', None) is enemy:
                            try:
                                if b in bullets.bullets:
                                    bullets.bullets.remove(b)
                            except ValueError:
                                pass
            # Note: side collisions with ranged enemies do nothing to the player unless invincibility active

                # Update fire projectiles
        for proj in player.fire_projectiles[:]:
            proj.update(dt, platforms, world_width, world_height) #world bounds
            
            # Check collision with enemies
            for enemy in melee_enemies:
                if enemy.alive and proj.check_enemy_collision(enemy):
                    enemy_died = enemy.take_damage(proj.damage) if hasattr(enemy, 'take_damage') else True
                    if enemy_died:
                        enemies_killed += 1
                        spawn_death_particles(enemy.rect.centerx, enemy.rect.centery, (255, 160, 40))
                        _register_kill(enemy.rect.centerx, enemy.rect.centery)
                    proj.alive = False
                    break
            for enemy in charger_enemies:
                if enemy.alive and proj.check_enemy_collision(enemy):
                    enemy_died = enemy.take_damage(proj.damage) if hasattr(enemy, 'take_damage') else True
                    if enemy_died:
                        enemies_killed += 1
                        spawn_death_particles(enemy.rect.centerx, enemy.rect.centery, (255, 160, 40))
                        _register_kill(enemy.rect.centerx, enemy.rect.centery)
                    proj.alive = False
                    break
            for enemy in shield_enemies:
                if enemy.alive and proj.check_enemy_collision(enemy):
                    if enemy.is_front_hit(proj.rect.centerx):
                        damage_numbers.append(DamageNumber("Blocked!", enemy.rect.centerx, enemy.rect.top, (150, 200, 255)))
                        proj.alive = False
                        break
                    enemy_died = enemy.take_damage(proj.damage) if hasattr(enemy, 'take_damage') else True
                    if enemy_died:
                        enemies_killed += 1
                        spawn_death_particles(enemy.rect.centerx, enemy.rect.centery, (255, 160, 40))
                        _register_kill(enemy.rect.centerx, enemy.rect.centery)
                    proj.alive = False
                    break
            for enemy in ranged_enemies:
                if enemy.alive and proj.check_enemy_collision(enemy):
                    enemy_died = enemy.take_damage(proj.damage) if hasattr(enemy, 'take_damage') else True
                    if enemy_died:
                        enemies_killed += 1
                        spawn_death_particles(enemy.rect.centerx, enemy.rect.centery, (255, 160, 40))
                        _register_kill(enemy.rect.centerx, enemy.rect.centery)
                        # Remove gun and bullets when ranged enemy dies
                        for g in guns[:]:
                            if getattr(g, 'owner', None) is enemy:
                                guns.remove(g)
                        for b in bullets.all()[:]:
                            if getattr(b, 'owner', None) is enemy:
                                if b in bullets.bullets:
                                    bullets.bullets.remove(b)
                    proj.alive = False
                    break

            if boss and boss.alive and proj.alive and proj.check_enemy_collision(boss):
                boss.take_damage(proj.damage)
                proj.alive = False
            
            # Remove dead projectiles
            if not proj.alive:
                player.fire_projectiles.remove(proj)

        # Draw fire projectiles
        for proj in player.fire_projectiles:
            proj.draw(screen, camera)

        # handle float power pickup
        for p in float_powers:
            if not p.collected and p.collect(player):
                p.collected = True
                # mark collected (shows prompt) but do not auto-activate
                player.float_power_collected = True
                _play_sfx(POWERUP_SFX)
                damage_numbers.append(DamageNumber("Float!", p.rect.centerx, p.rect.top, (100, 200, 255)))
            # handle invincibility pickup
        for ip in invincibility_powers:
            if not ip.collected and ip.collect(player):
                ip.collected = True
                player.invincibility_collected = True
                _play_sfx(POWERUP_SFX)
                damage_numbers.append(DamageNumber("Invincible!", ip.rect.centerx, ip.rect.top, (255, 255, 100)))
        for fp in fire_powers:
            if not fp.collected and fp.collect(player):
                fp.collected = True
                player.fire_power_collected = True
                _play_sfx(POWERUP_SFX)
                damage_numbers.append(DamageNumber("Fire!", fp.rect.centerx, fp.rect.top, (255, 140, 0)))


        # update float power active timer
        if getattr(player, 'float_power_active', False):
            player.float_time_remaining -= dt
            if player.float_time_remaining <= 0:
                player.float_power_active = False
                player.float_time_remaining = 0.0

        # update invincibility timer
        if getattr(player, 'invincibility_active', False):
            player.invincibility_time_remaining -= dt
            if player.invincibility_time_remaining <= 0:
                player.invincibility_active = False
                player.invincibility_time_remaining = 0.0
        
        # update fire power timer
        if player.fire_power_active:
            player.fire_power_time_remaining -= dt
            if player.fire_power_time_remaining <= 0:
                player.fire_power_active = False

        


        for b in bullets.all()[:]:
            # move bullet in world space
            b.rect.x += b.velocity * dt
            # keep bullet hitbox synced
            if hasattr(b, 'hitbox'):
                b.hitbox.topleft = b.rect.topleft
        
            # check collision with player (use hitbox if available)
            bullet_hits = False
            if hasattr(b, 'hitbox') and hasattr(player, 'hitbox'):
                bullet_hits = b.hitbox.colliderect(player.hitbox)
            else:
                bullet_hits = b.rect.colliderect(player.rect)
            
            if bullet_hits and not getattr(player, 'invincibility_active', False):
                damage_player(BULLET_DAMAGE, source_x=b.rect.centerx)
                if b in bullets.bullets:
                    bullets.bullets.remove(b)
            # remove bullet if off-screen (beyond world bounds)
            elif b.rect.right < 0 or b.rect.left > world_width:
                if b in bullets.bullets:
                    bullets.bullets.remove(b)
                


        if player.rect.left <= 0: #if the player moves past the left side of the screen then they stay at the left side
            player.rect.left = 0

        if player.rect.top <= -world_height: #if the player jumps past the top of the screen then they stay at the top
            player.rect.top = -world_height
            player.y_velocity = max(player.y_velocity, 0.0)
        else:
            # if not colliding with platform and falling past bottom of screen, stop at bottom
            if player.rect.bottom >= world_height:
                # respawn on top of start platform (use player's height to avoid overlap)
                try:
                    log_analytics_event(player_name, 'dropoff', level_id=stats_level_id, x=player.rect.centerx, y=player.rect.centery)
                except Exception:
                    pass
                spawn_x = start_plat.rect.left + 5
                player.rect.x = spawn_x
                # place player just above the platform to avoid overlap
                player.rect.bottom = start_plat.rect.top - 1
                player.x_velocity = 0
                player.y_velocity = 0.0
                jumping = False
                coyote_timer = coyote_time_window
                jump_buffer_timer = 0.0
                if easy_mode:
                    damage_numbers.append(DamageNumber("Safety Warp", player.rect.centerx, player.rect.top - 8, (150, 235, 180)))
                    style_points = max(0, style_points - 30)
                    style_breakdown['penalties'] += 30
                else:
                    lives -= 1
                    level_deaths += 1
                    conn = create_connection("scores_and_times.db")
                    if lives >= 3:
                        subtract_life(conn, player_name)
                    conn.close()
                if hasattr(player, 'update_position'):
                    player.update_position()
                # ensure no overlap after respawn (safety correction)
                while any(plat.rect.colliderect(player.rect) for plat in platforms):
                    player.rect.y -= 1
                    player.update_position()
                for plat in platforms:
                    plat.active = True  # reset any decayed platforms

        analytics_tick += dt
        if analytics_tick >= 0.4:
            analytics_tick = 0.0
            cell_x = int(player.rect.centerx // 180)
            cell_y = int(player.rect.centery // 140)
            key = (cell_x, cell_y)
            analytics_area_time[key] = analytics_area_time.get(key, 0.0) + 0.4
            
        if player.rect.colliderect(finish_line.rect):
            if boss and boss.alive:
                # Boss must be defeated before level completion.
                pass
            else:
            # stop timer and compute final score
                timer.pause_timer()
                score.calculate_score(timer.get_elapsed_time(), coins_collected, enemies_killed, level_deaths)
                # Mark current level complete and unlock follow-ups from world rules.
                if stats_level_id is not None:
                    conn_unlock = create_connection()
                    if conn_unlock:
                        unlock_level(conn_unlock, player_name, stats_level_id)
                        hard_boss_ids = {w['hard_boss'] for w in WORLD_DEFS.values()}
                        if stats_level_id in hard_boss_ids:
                            unlock_ng_plus(conn_unlock, player_name)
                        unlocked_now = get_unlocked_levels(player_name)
                        challenge_completed = (challenge_info is not None and challenge_info.get('level_id') == stats_level_id)
                        next_levels = compute_unlocks_after_completion(stats_level_id, unlocked_now, challenge_completed=challenge_completed)
                        for next_level in next_levels:
                            unlock_level(conn_unlock, player_name, next_level)
                        conn_unlock.close()

                    save_replay_timeline(
                        player_name,
                        stats_level_id,
                        timer.get_elapsed_time(),
                        score.total_score,
                        ghost_record_frames,
                        is_public=True,
                        run_outcome='completed',
                        mini_video_frames=replay_video_frames,
                    )

                # Save score and time to database
                conn1 = create_connection("scores_and_times.db")
                medal_awarded = _compute_level_medal(
                    level_config,
                    timer.get_elapsed_time(),
                    level_deaths,
                    coins_collected,
                    total_level_coins,
                )

                # Query previous bests BEFORE saving so we can detect a new record
                if get_best_score_hook is not None and custom_level_id is not None:
                    prev_best_score = get_best_score_hook(player_name, custom_level_id)
                elif stats_level_id is not None:
                    prev_best_score = get_player_best_score(player_name, stats_level_id)
                else:
                    prev_best_score = None

                if get_best_time_hook is not None and custom_level_id is not None:
                    prev_best_time = get_best_time_hook(player_name, custom_level_id)
                elif stats_level_id is not None:
                    prev_best_time = get_player_best_time(player_name, stats_level_id)
                else:
                    prev_best_time = None

                if conn1 is not None:
                    print(f"Debug: Saving for level {level_id}, player {player_name}")  # Debug
                    if save_run_hook is not None and custom_level_id is not None:
                        success_score = save_run_hook(
                            player_name,
                            custom_level_id,
                            score.total_score,
                            timer.get_elapsed_time(),
                            coins_collected,
                        )
                        success_time = success_score
                    elif stats_level_id is not None:
                        # include collected coins when saving so leaderboard shows coins
                        success_score = save_score(
                            conn1,
                            player_name,
                            score.total_score,
                            coins_collected=coins_collected,
                            level_id=stats_level_id,
                            run_mode=run_mode_label,
                        )
                        success_time = save_time(
                            conn1,
                            player_name,
                            timer.get_elapsed_time(),
                            coins_collected=coins_collected,
                            level_id=stats_level_id,
                            run_mode=run_mode_label,
                        )
                        save_level_medal(
                            conn1,
                            player_name,
                            stats_level_id,
                            medal_awarded,
                            timer.get_elapsed_time(),
                            level_deaths,
                            coins_collected,
                            total_level_coins,
                        )
                    else:
                        success_score = False
                        success_time = False
                    print(f"Debug: Save results - score: {success_score}, time: {success_time}")  # Debug
                    add_total_coins(conn1, player_name, coins_collected)
                    conn1.close()
                else:
                    print("Debug: Failed to create database connection")  # Debug
                    if conn1:
                        conn1.close()

                is_new_score_best = (prev_best_score is None or score.total_score > prev_best_score)
                is_new_time_best  = (prev_best_time  is None or timer.get_elapsed_time() < prev_best_time)

                style_rank = _compute_style_rank(combo_max_streak, style_points)

                try:
                    for (ax, ay), spent in analytics_area_time.items():
                        if spent >= 0.8:
                            log_analytics_event(
                                player_name,
                                'area_time',
                                level_id=stats_level_id,
                                x=ax,
                                y=ay,
                                meta=f"seconds={round(spent, 2)}"
                            )
                except Exception:
                    pass

                try:
                    avg_ms, p95_ms, fps_avg, mem_current_mb, mem_peak_mb = _get_perf_snapshot()
                    perf_meta = json.dumps(
                        {
                            'outcome': 'completed',
                            'fps_avg': round(fps_avg, 3),
                            'mem_current_mb': round(mem_current_mb, 3),
                            'mem_peak_mb': round(mem_peak_mb, 3),
                            'frames': int(perf_frame_counter),
                            'duration_s': round(perf_elapsed, 3),
                            'spikes_logged': int(perf_spike_count),
                            'peak_frame_ms': round(perf_peak_frame_ms, 3),
                        },
                        separators=(",", ":"),
                    )
                    log_analytics_event(
                        player_name,
                        'perf_summary',
                        level_id=stats_level_id,
                        x=int(round(avg_ms * 100.0)),
                        y=int(round(p95_ms * 100.0)),
                        meta=perf_meta,
                    )
                except Exception:
                    pass

                # Quest + prestige progression hooks.
                try:
                    add_quest_progress(player_name, 'daily_clear_run', 1, period='daily')
                    add_quest_progress(player_name, 'weekly_clear_master', 1, period='weekly')
                    add_quest_progress(player_name, 'daily_coin_hunter', int(coins_collected), period='daily')
                    if combo_max_streak >= 5:
                        add_quest_progress(player_name, 'daily_combo_chain', 1, period='daily')
                    if style_rank in ('S', 'A'):
                        add_quest_progress(player_name, 'weekly_style_rank', 1, period='weekly')
                except Exception:
                    pass
                try:
                    prestige_gain = max(10, int(score.total_score // 50) + int(combo_max_streak * 2))
                    add_prestige_points(player_name, prestige_gain)
                except Exception:
                    pass

                if on_complete_hook is not None:
                    try:
                        on_complete_hook({
                            'level_id': stats_level_id,
                            'score': int(score.total_score),
                            'completion_time': float(timer.get_elapsed_time()),
                            'coins_collected': int(coins_collected),
                            'total_coins': int(total_level_coins),
                            'death_count': int(level_deaths),
                        })
                    except Exception:
                        pass

                # get top fastest times to display on the win screen
                if get_top_times_hook is not None and custom_level_id is not None:
                    top_times = get_top_times_hook(custom_level_id, 5)
                elif stats_level_id is not None:
                    top_times = get_fastest_times(stats_level_id, 5)
                else:
                    top_times = []

                if get_top_scores_hook is not None and custom_level_id is not None:
                    top_scores = get_top_scores_hook(custom_level_id, 5)
                elif stats_level_id is not None:
                    top_scores = get_high_scores(stats_level_id, 5)
                else:
                    top_scores = []
                print(f"Debug: level_id={level_id}, top_scores={top_scores}, top_times={top_times}")  # Debug print
                # show win screen and pass score + leaderboard
                from win_screen import win_screen
                keep_running = win_screen(
                    player_score=score.total_score, 
                    top_times=top_times, 
                    top_scores=top_scores,
                    is_new_score_best=is_new_score_best,
                    is_new_time_best=is_new_time_best,
                    style_rank=style_rank,
                    combo_max=combo_max_streak,
                    medal_awarded=medal_awarded,
                    death_count=level_deaths,
                    coins_collected=coins_collected,
                    total_coins=total_level_coins,
                    run_mode_label=run_mode_label,
                    style_breakdown=style_breakdown,
                )
                if not keep_running:
                    return False  # exit to play menu
                else:
                    return True  # restart tutorial
        
        if lives <= 0:
            overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA) #create semi-transparent overlay
            overlay.fill((0, 0, 0, 100))
            screen.blit(overlay, (0, 0)) #draw overlay on screen
            game_over_font = pygame.font.SysFont("Arial", 80)
            game_over_text = Text('Game Over', 400,200, game_over_font) #create game over text
            game_over_text.draw_text() #draw game over text
            elapsed_now = timer.get_elapsed_time()
            score.calculate_score(elapsed_now, coins_collected, enemies_killed, level_deaths)
            _prompt_save_failed_replay(
                screen,
                player_name,
                stats_level_id if stats_level_id is not None else level_id,
                elapsed_now,
                score.total_score,
                ghost_record_frames,
                replay_video_frames,
            )
            try:
                avg_ms, p95_ms, fps_avg, mem_current_mb, mem_peak_mb = _get_perf_snapshot()
                perf_meta = json.dumps(
                    {
                        'outcome': 'failed',
                        'fps_avg': round(fps_avg, 3),
                        'mem_current_mb': round(mem_current_mb, 3),
                        'mem_peak_mb': round(mem_peak_mb, 3),
                        'frames': int(perf_frame_counter),
                        'duration_s': round(perf_elapsed, 3),
                        'spikes_logged': int(perf_spike_count),
                        'peak_frame_ms': round(perf_peak_frame_ms, 3),
                    },
                    separators=(",", ":"),
                )
                log_analytics_event(
                    player_name,
                    'perf_summary',
                    level_id=stats_level_id,
                    x=int(round(avg_ms * 100.0)),
                    y=int(round(p95_ms * 100.0)),
                    meta=perf_meta,
                )
            except Exception:
                pass
            timer.reset()
            pygame.display.update()
            pygame.time.delay(1500)
            return True  # return to play menu

        for coin in coins:
            if player.rect.colliderect(coin.rect):
                gain = int(round(5 * seasonal_coin_mult))
                coins_collected += max(1, gain)
                _play_sfx(COIN_SFX)
                damage_numbers.append(DamageNumber(f"+{max(1, gain)}", coin.rect.centerx, coin.rect.top, (255, 215, 0)))
                coins.remove(coin) #removes the coin from the list when the player collides with it
                

        # Checkpoint activation
        for cp in checkpoints:
            if cp.check_activate(player):
                active_checkpoint = cp
                damage_numbers.append(DamageNumber(
                    "Checkpoint!", cp.rect.centerx, cp.rect.top - 10, (50, 220, 100)))

        if timer_started:
            ghost_record_timer += dt
            if ghost_record_timer >= 0.05:
                ghost_record_timer = 0.0
                ghost_record_frames.append({
                    "t": round(timer.get_elapsed_time(), 3),
                    "x": int(player.rect.x),
                    "y": int(player.rect.y),
                    "vx": int(getattr(player, 'x_velocity', 0)),
                    "vy": float(getattr(player, 'y_velocity', 0.0)),
                    "hp": int(getattr(player, 'health', 0)),
                    "ori": getattr(player, 'orientation', 'right'),
                })

        camera.follow(player.rect, dt, target_vx=player.x_velocity, target_vy=player.y_velocity) #update camera position based on player position and delta time
        camera.clamp_to_world(world_width, world_height * 2) #clamp camera position within world boundaries
        screen = pygame.display.get_surface()
        background.draw_background(screen, camera.x)

        # Weather VFX overlay: rain streaks and wind motes for clearer feedback.
        if dynamic_weather_key in ('rain', 'wind'):
            sw, sh = screen.get_width(), screen.get_height()
            spawn_interval = 0.014 if dynamic_weather_key == 'rain' else 0.032
            max_particles = 140 if dynamic_weather_key == 'rain' else 70
            weather_spawn_timer += dt
            while weather_spawn_timer >= spawn_interval and len(weather_particles) < max_particles:
                weather_spawn_timer -= spawn_interval
                if dynamic_weather_key == 'rain':
                    weather_particles.append({
                        'kind': 'rain',
                        'x': random.uniform(-20, sw + 20),
                        'y': random.uniform(-30, 0),
                        'vx': random.uniform(-18, 18) - weather_wind_force * 0.10,
                        'vy': random.uniform(460, 640),
                        'life': random.uniform(0.7, 1.1),
                        'length': random.randint(8, 14),
                    })
                else:
                    from_left = weather_wind_force >= 0
                    x0 = -20 if from_left else sw + 20
                    weather_particles.append({
                        'kind': 'wind',
                        'x': x0,
                        'y': random.uniform(10, sh - 10),
                        'vx': random.uniform(120, 200) * (1 if from_left else -1),
                        'vy': random.uniform(-26, 26),
                        'life': random.uniform(0.8, 1.4),
                        'length': random.randint(4, 8),
                    })

            vfx_layer = pygame.Surface((sw, sh), pygame.SRCALPHA)
            for p in weather_particles[:]:
                p['x'] += p['vx'] * dt
                p['y'] += p['vy'] * dt
                p['life'] -= dt
                if p['life'] <= 0 or p['x'] < -50 or p['x'] > sw + 50 or p['y'] < -50 or p['y'] > sh + 50:
                    weather_particles.remove(p)
                    continue

                if p['kind'] == 'rain':
                    ex = int(p['x'] + p['vx'] * 0.018)
                    ey = int(p['y'] + p['length'])
                    pygame.draw.line(vfx_layer, (170, 200, 255, 115), (int(p['x']), int(p['y'])), (ex, ey), 1)
                else:
                    pygame.draw.circle(vfx_layer, (205, 235, 210, 105), (int(p['x']), int(p['y'])), p['length'] // 2)

            # Subtle atmosphere tint by weather type.
            if dynamic_weather_key == 'rain':
                vfx_layer.fill((70, 95, 135, 22), special_flags=pygame.BLEND_RGBA_ADD)
            else:
                vfx_layer.fill((120, 150, 110, 16), special_flags=pygame.BLEND_RGBA_ADD)
            screen.blit(vfx_layer, (0, 0))

        if controls_text is not None:
            controls_text.draw_text()
        if dynamic_weather is not None and dynamic_weather.get('key') != 'clear':
            weather_txt = font.render(f"Weather: {dynamic_weather.get('name', 'Dynamic')}", True, (180, 220, 255))
            screen.blit(weather_txt, (10, 86))
        if challenge_variant is not None and challenge_info is not None:
            var_col = (255, 210, 140)
            if colorblind_safe:
                var_col = (200, 225, 255)
            variant_txt = font.render(f"Variant: {challenge_variant.get('label', 'Challenge Variant')}", True, var_col)
            screen.blit(variant_txt, (10, 114))

        if world_tutorial_cards and tutorial_card_timer > 0:
            tutorial_msg = str(world_tutorial_cards[min(tutorial_card_index, len(world_tutorial_cards) - 1)])
            tip_font = pygame.font.SysFont("Arial", 22, bold=True)
            tip_text = tip_font.render(tutorial_msg, True, (235, 245, 255))
            tip_w = min(screen.get_width() - 40, tip_text.get_width() + 26)
            tip_h = tip_text.get_height() + 16
            tip_x = (screen.get_width() - tip_w) // 2
            tip_y = 18
            tip_panel = pygame.Surface((tip_w, tip_h), pygame.SRCALPHA)
            tip_panel.fill((16, 26, 42, 188))
            screen.blit(tip_panel, (tip_x, tip_y))
            pygame.draw.rect(screen, (145, 195, 255), (tip_x, tip_y, tip_w, tip_h), 2, border_radius=8)
            screen.blit(tip_text, (tip_x + (tip_w - tip_text.get_width()) // 2, tip_y + 7))
        # Lives display with heart icons
        display_lives = min(max(0, lives), 8)
        for i in range(display_lives):
            screen.blit(hud_life_img, (10 + i * 26, 10))
        if lives > 8:
            extra_text = font.render(f"+{lives - 8}", True, (255, 255, 255))
            screen.blit(extra_text, (10 + 8 * 26, 12))
        # Health text
        hp_color = (255, 235, 90) if high_contrast_hud else (255, 120, 120)
        health_text = font.render(f"HP: {int(getattr(player, 'health', 0))}/{int(getattr(player, 'max_health', 50))}", True, hp_color)
        screen.blit(health_text, (10, 38))
        # Coin counter on HUD
        screen.blit(hud_coin_img, (10, 62))
        coin_col = (255, 255, 120) if high_contrast_hud else (255, 215, 0)
        coin_hud_text = font.render(f"x {coins_collected}", True, coin_col)
        screen.blit(coin_hud_text, (36, 64))
        # Active powerup timer bars
        bar_w = 110
        bar_h = 9
        bar_x = 10
        hud_bar_y = 90
        float_cols = ((25, 65, 140), (95, 195, 235), (220, 240, 255), (95, 195, 235))
        shield_cols = ((95, 80, 20), (235, 195, 60), (255, 245, 175), (235, 195, 60))
        fire_cols = ((115, 45, 0), (255, 125, 35), (255, 190, 120), (255, 125, 35))
        if colorblind_safe:
            float_cols = ((20, 70, 120), (70, 190, 210), (210, 240, 250), (70, 190, 210))
            shield_cols = ((65, 45, 90), (175, 110, 230), (225, 195, 250), (175, 110, 230))
            fire_cols = ((45, 80, 15), (120, 220, 90), (200, 245, 170), (120, 220, 90))
        if getattr(player, 'float_power_active', False):
            ratio = max(0.0, player.float_time_remaining / 5.0)
            pygame.draw.rect(screen, float_cols[0], (bar_x, hud_bar_y, bar_w, bar_h))
            pygame.draw.rect(screen, float_cols[1], (bar_x, hud_bar_y, int(bar_w * ratio), bar_h))
            pygame.draw.rect(screen, float_cols[2], (bar_x, hud_bar_y, bar_w, bar_h), 1)
            lbl = bar_label_font.render("Float", True, float_cols[3])
            screen.blit(lbl, (bar_x + bar_w + 4, hud_bar_y - 1))
            hud_bar_y += 14
        if getattr(player, 'invincibility_active', False):
            ratio = max(0.0, player.invincibility_time_remaining / 4.0)
            pygame.draw.rect(screen, shield_cols[0], (bar_x, hud_bar_y, bar_w, bar_h))
            pygame.draw.rect(screen, shield_cols[1], (bar_x, hud_bar_y, int(bar_w * ratio), bar_h))
            pygame.draw.rect(screen, shield_cols[2], (bar_x, hud_bar_y, bar_w, bar_h), 1)
            lbl = bar_label_font.render("Shield", True, shield_cols[3])
            screen.blit(lbl, (bar_x + bar_w + 4, hud_bar_y - 1))
            hud_bar_y += 14
        if getattr(player, 'fire_power_active', False):
            ratio = max(0.0, player.fire_power_time_remaining / 12.0)
            pygame.draw.rect(screen, fire_cols[0], (bar_x, hud_bar_y, bar_w, bar_h))
            pygame.draw.rect(screen, fire_cols[1], (bar_x, hud_bar_y, int(bar_w * ratio), bar_h))
            pygame.draw.rect(screen, fire_cols[2], (bar_x, hud_bar_y, bar_w, bar_h), 1)
            lbl = bar_label_font.render("Fire", True, fire_cols[3])
            screen.blit(lbl, (bar_x + bar_w + 4, hud_bar_y - 1))
        timer.get_elapsed_time()
        timer.draw_timer(screen, font)
        if training_target_time is not None:
            elapsed_now = timer.get_elapsed_time()
            delta = elapsed_now - training_target_time
            target_col = (140, 245, 170) if delta <= 0 else (255, 180, 150)
            target_txt = font.render(f"Ghost Target: {training_target_time:.2f}s", True, (165, 220, 255))
            delta_txt = font.render(f"Delta: {delta:+.2f}s", True, target_col)
            screen.blit(target_txt, (10, 68))
            screen.blit(delta_txt, (10, 96))
            if training_medal_times:
                gold_t = training_medal_times.get('gold')
                silver_t = training_medal_times.get('silver')
                bronze_t = training_medal_times.get('bronze')
                medal_line = f"Trial Medals  G:{gold_t}s  S:{silver_t}s  B:{bronze_t}s"
                medal_txt = bar_label_font.render(medal_line, True, (220, 220, 235))
                screen.blit(medal_txt, (10, 122))
        if hud_best_score is not None:
            best_txt = font.render(f"Best: {hud_best_score}", True, (205, 205, 205))
            screen.blit(best_txt, (screen.get_width() - best_txt.get_width() - 12, 10))
        if ng_plus_active:
            ng_txt = font.render("NG+", True, (255, 175, 90))
            screen.blit(ng_txt, (screen.get_width() - ng_txt.get_width() - 12, 40))
        if seasonal_event is not None:
            evt_color = seasonal_event.get("hud_color", (200, 230, 255))
            evt_txt = font.render(seasonal_event.get("name", "Seasonal Event"), True, evt_color)
            screen.blit(evt_txt, (screen.get_width() - evt_txt.get_width() - 12, 68))
        if not hud_simplified:
            ghost_hint = font.render(f"Ghost: {'ON' if ghost_enabled else 'OFF'} (G)", True, (180, 210, 240))
            screen.blit(ghost_hint, (10, screen.get_height() - 32))
        if not hud_simplified and ghost_enabled and ghost_frames and ghost_owner_name:
            race_meta = f"Race Ghost: {ghost_owner_name}"
            if ghost_time is not None:
                race_meta += f" {float(ghost_time):.2f}s"
            if ghost_replay_id is not None:
                race_meta += f"  #{int(ghost_replay_id)}"
            race_txt = font.render(race_meta, True, (140, 225, 255))
            screen.blit(race_txt, (10, screen.get_height() - 58))
        combo_ratio = max(0.0, min(1.0, combo_decay_timer / max(0.001, combo_decay_window)))
        combo_w = 180
        combo_x = screen.get_width() - combo_w - 12
        combo_y = 98
        combo_fill = (255, 120, 80)
        combo_txt_col = (255, 205, 160)
        if colorblind_safe:
            combo_fill = (95, 210, 135)
            combo_txt_col = (185, 240, 205)
        pygame.draw.rect(screen, (45, 45, 55), (combo_x, combo_y, combo_w, 12), border_radius=6)
        pygame.draw.rect(screen, combo_fill, (combo_x, combo_y, int(combo_w * combo_ratio), 12), border_radius=6)
        pygame.draw.rect(screen, (210, 210, 220), (combo_x, combo_y, combo_w, 12), 1, border_radius=6)
        combo_txt = font.render(f"Combo x{kill_streak}", True, combo_txt_col)
        screen.blit(combo_txt, (combo_x, combo_y - 24))

        style_combo_peak = max(combo_max_streak, kill_streak)
        live_style_rank, next_style_rank, style_ratio, next_style_points, next_style_combo = _get_style_meter_state(
            style_combo_peak,
            style_points,
        )
        style_colors = {
            'D': (175, 175, 185),
            'C': (120, 210, 255),
            'B': (120, 255, 175),
            'A': (255, 215, 90),
            'S': (255, 120, 210),
        }
        if colorblind_safe:
            style_colors = {
                'D': (190, 190, 200),
                'C': (120, 180, 255),
                'B': (90, 220, 150),
                'A': (245, 165, 80),
                'S': (210, 120, 240),
            }
        style_color = style_colors.get(live_style_rank, (220, 220, 220))
        style_y = combo_y + 34
        style_title = font.render(f"Style {live_style_rank}", True, style_color)
        screen.blit(style_title, (combo_x, style_y))
        style_stat = bar_label_font.render(f"{int(style_points)} SP   Best x{combo_max_streak}", True, (230, 235, 245) if high_contrast_hud else (215, 220, 235))
        screen.blit(style_stat, (combo_x + combo_w - style_stat.get_width(), style_y + 4))
        style_bar_y = style_y + 24
        pygame.draw.rect(screen, (38, 40, 58), (combo_x, style_bar_y, combo_w, 12), border_radius=6)
        pygame.draw.rect(screen, style_color, (combo_x, style_bar_y, int(combo_w * style_ratio), 12), border_radius=6)
        pygame.draw.rect(screen, (210, 210, 220), (combo_x, style_bar_y, combo_w, 12), 1, border_radius=6)
        if next_style_rank is None:
            next_style_txt = bar_label_font.render("Max rank reached", True, style_color)
        else:
            next_style_txt = bar_label_font.render(
                f"Next {next_style_rank}: {next_style_points} SP or x{next_style_combo}",
                True,
                (205, 210, 225),
            )
        screen.blit(next_style_txt, (combo_x, style_bar_y + 16))

        # Apply screen-shake offset to camera for all world draws
        shake_ox, shake_oy = 0, 0
        if shake_timer > 0:
            shake_timer = max(0.0, shake_timer - dt)
            cur_int = max(1, int(shake_intensity * (shake_timer / 0.4)))
            shake_ox = random.randint(-cur_int, cur_int)
            shake_oy = random.randint(-(cur_int // 2), cur_int // 2)
            camera.x += shake_ox
            camera.y += shake_oy

        finish_line_offset = camera.apply(finish_line.rect)
        screen.blit(finish_line.image, finish_line_offset) #draws the finish line at its rectangular position adjusted for camera

        if boss and boss.alive:
            boss.draw(screen, camera)
            # Boss health bar HUD
            bar_w = 320
            bar_h = 18
            bar_x = (screen.get_width() - bar_w) // 2
            bar_y = 12
            pygame.draw.rect(screen, (40, 40, 40), (bar_x, bar_y, bar_w, bar_h), border_radius=6)
            ratio = boss.health / boss.max_health if boss.max_health > 0 else 0
            fill_w = int((bar_w - 4) * max(0.0, min(1.0, ratio)))
            if ratio >= 0.5:
                t = (ratio - 0.5) * 2
                hp_color = (int(255 - 205 * t), 200, 50)
            else:
                t = ratio * 2
                hp_color = (255, int(50 + 150 * t), 50)
            pygame.draw.rect(screen, hp_color, (bar_x + 2, bar_y + 2, fill_w, bar_h - 4), border_radius=5)
            pygame.draw.rect(screen, (220, 220, 220), (bar_x, bar_y, bar_w, bar_h), 2, border_radius=6)
            boss_font = pygame.font.SysFont("Arial", 18)
            boss_text = boss_font.render(f"Boss HP: {boss.health}/{boss.max_health}", True, (255, 255, 255))
            screen.blit(boss_text, (bar_x + (bar_w - boss_text.get_width()) // 2, bar_y - 20))
            if boss_weekly_modifier:
                mod_text = boss_font.render(f"Weekly: {boss_weekly_modifier['label']}", True, (255, 225, 150))
                screen.blit(mod_text, (bar_x + (bar_w - mod_text.get_width()) // 2, bar_y + bar_h + 4))

        # Draw prompt when float power is collected but not active
        if getattr(player, 'float_power_collected', False) and not getattr(player, 'float_power_active', False):
            prompt_font = pygame.font.SysFont("Arial", 24)
            prompt = prompt_font.render(f"{power_select_1_label}: Select Float | {power_activate_label}: Activate", True, (255,255,255))
            screen.blit(prompt, (player.rect.x - camera.x, player.rect.y - 40 - camera.y))

        # Draw prompt when fire power collected
        if player.fire_power_collected and not player.fire_power_active:
            prompt_font = pygame.font.SysFont("Arial", 24)
            prompt = prompt_font.render(f"{power_select_3_label}: Select Fire | {power_activate_label}: Activate", True, (255, 220, 80))
            screen.blit(prompt, (player.rect.x - camera.x, player.rect.y - 80 - camera.y))

        if getattr(player, 'invincibility_collected', False) and not getattr(player, 'invincibility_active', False):
            prompt_font = pygame.font.SysFont("Arial", 24)
            prompt = prompt_font.render(f"{power_select_2_label}: Select Invincibility | {power_activate_label}: Activate", True, (255,255,255))
            screen.blit(prompt, (player.rect.x - camera.x, player.rect.y - 60 - camera.y))


        for enemy in melee_enemies:
            if enemy.alive:  # only draw enemy if it's alive
                # Update animation: run when moving, idle when stationary
                is_moving = enemy.ai_state in ('patrol', 'chase')
                enemy.update_animation(dt, is_moving)
                offset_rect = camera.apply(enemy.rect) #adjust enemy position based on camera
                enemy_image = enemy.get_image()  # flipped based on facing_direction
                screen.blit(enemy_image, offset_rect) #draws the enemy image at its rectangular position adjusted for camera
                if getattr(enemy, 'aura_active', False):
                    pygame.draw.circle(screen, (110, 245, 150), (enemy.rect.centerx - int(camera.x), enemy.rect.centery - int(camera.y)), 28, 2)
                if getattr(enemy, 'warn_active', False):
                    warn_s = warn_font.render("!", True, (255, 170, 90))
                    wx = enemy.rect.centerx - int(camera.x) - warn_s.get_width() // 2
                    wy = enemy.rect.top - int(camera.y) - warn_s.get_height() - 5
                    screen.blit(warn_s, (wx, wy))
        for enemy in charger_enemies:
            if enemy.alive:
                is_moving = enemy.ai_state in ('patrol', 'chase', 'charge')
                enemy.update_animation(dt, is_moving)
                offset_rect = camera.apply(enemy.rect)
                enemy_image = enemy.get_image()
                if enemy.ai_state == 'telegraph':
                    enemy_image = enemy_image.copy()
                    flash = pygame.Surface(enemy_image.get_size())
                    flash.fill((255, 90, 70))
                    enemy_image.blit(flash, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
                screen.blit(enemy_image, offset_rect)
                if enemy.warn_active:
                    warn_s = warn_font.render("!", True, (255, 90, 70))
                    wx = enemy.rect.centerx - int(camera.x) - warn_s.get_width() // 2
                    wy = enemy.rect.top - int(camera.y) - warn_s.get_height() - 5
                    screen.blit(warn_s, (wx, wy))
        for enemy in shield_enemies:
            if enemy.alive:
                is_moving = enemy.ai_state in ('patrol', 'chase', 'bash')
                enemy.update_animation(dt, is_moving)
                offset_rect = camera.apply(enemy.rect)
                enemy_image = enemy.get_image()
                screen.blit(enemy_image, offset_rect)
                # Draw directional shield plate in front for clear readability.
                sx = enemy.rect.right - int(camera.x) if enemy.facing_direction >= 0 else enemy.rect.left - int(camera.x) - 5
                sy = enemy.rect.centery - int(camera.y) - 10
                shield_color = (120, 185, 255) if not enemy.warn_active else (255, 190, 90)
                pygame.draw.rect(screen, shield_color, (sx, sy, 5, 20), border_radius=2)
                if enemy.warn_active:
                    warn_s = warn_font.render("!", True, (255, 200, 90))
                    wx = enemy.rect.centerx - int(camera.x) - warn_s.get_width() // 2
                    wy = enemy.rect.top - int(camera.y) - warn_s.get_height() - 5
                    screen.blit(warn_s, (wx, wy))
        for enemy in ranged_enemies:
            if enemy.alive:  # only draw enemy if it's alive
                offset_rect = camera.apply(enemy.rect) #adjust enemy position based on camera
                enemy_image = enemy.get_image(player)  # get flipped image based on orientation
                screen.blit(enemy_image, offset_rect) #draws the enemy image at its rectangular position adjusted for camera
                if enemy.warn_active:
                    warn_s = warn_font.render("!", True, (255, 80, 60))
                    wx = enemy.rect.centerx - int(camera.x) - warn_s.get_width() // 2
                    wy = enemy.rect.top - int(camera.y) - warn_s.get_height() - 5
                    screen.blit(warn_s, (wx, wy))
        for gun in guns:
            offset_rect = camera.apply(gun.rect) #adjust gun position based on camera
            gun_image = gun.get_image(player)  # get flipped image based on orientation
            screen.blit(gun_image, offset_rect) #draws the gun image at its rectangular position adjusted for camera 
        for coin in coins:
            coin.update(dt)
            offset_rect = camera.apply(coin.rect) #adjust coin position based on camera
            screen.blit(coin.image, offset_rect) #draws the coin image at its rectangular position adjusted for camera

        for strike in siege_strikes:
            beam_w = max(20, int(strike.get('width', 80) or 80))
            beam_x = int(strike['x'] - beam_w // 2 - camera.x)
            beam_surface = pygame.Surface((beam_w, screen.get_height()), pygame.SRCALPHA)
            if strike['phase'] == 'warning':
                beam_surface.fill((255, 210, 120, 58))
                edge_color = (255, 225, 170)
                marker_color = (255, 215, 120)
            else:
                beam_surface.fill((255, 120, 80, 110))
                edge_color = (255, 180, 110)
                marker_color = (255, 150, 90)
            screen.blit(beam_surface, (beam_x, 0))
            pygame.draw.rect(screen, edge_color, (beam_x, 0, beam_w, screen.get_height()), 2, border_radius=10)
            pygame.draw.circle(screen, marker_color, (beam_x + beam_w // 2, 32), max(8, beam_w // 7), 3)

        # draw float power pickup if not yet collected
        for p in float_powers:
            if not getattr(p, 'collected', False):
                offset_rect = camera.apply(p.rect)
                screen.blit(p.image, offset_rect)
        
        for i in invincibility_powers:
            if not getattr(i, 'collected', False):
                offset_rect = camera.apply(i.rect)
                screen.blit(i.image, offset_rect)

        # Near the other powerup drawing code, after float & invincibility
        for fp in fire_powers:
            if not fp.collected:
                offset_rect = camera.apply(fp.rect)
                screen.blit(fp.image, offset_rect)

        for cp in checkpoints:
            cp.draw(screen, camera)

        for platform in platforms:
            if not platform.active:
                continue  # skip inactive platforms
            offset_rect = camera.apply(platform.rect) #adjust platform position based on camera
            screen.blit(platform.image, offset_rect) #draws the platform image at its rectangular position adjusted for camera

        # Optional challenge ghost replay.
        if ghost_enabled and ghost_frames:
            t_now = timer.get_elapsed_time()
            while ghost_cursor + 1 < len(ghost_frames) and ghost_frames[ghost_cursor + 1]["t"] <= t_now:
                ghost_cursor += 1
            gf = ghost_frames[min(ghost_cursor, len(ghost_frames) - 1)]
            g_rect = pygame.Rect(int(gf["x"]), int(gf["y"]), player.rect.width, player.rect.height)
            g_off = camera.apply(g_rect)
            g_img = player.image.copy()
            if str(gf.get("ori", "right")) == 'left':
                g_img = pygame.transform.flip(g_img, True, False)
            g_img = pygame.transform.scale(g_img, (g_rect.width, g_rect.height))
            g_img.set_alpha(110)
            tint = pygame.Surface(g_img.get_size())
            tint.fill((90, 175, 255))
            g_img.blit(tint, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
            screen.blit(g_img, g_off)
        
        offset_rect = camera.apply(player.rect)
        player_image = player.get_image()  # get flipped image based on orientation
        if getattr(player, 'invincibility_active', False):
            flash_palette = (
                (255, 90, 90),
                (90, 255, 140),
                (90, 180, 255),
                (255, 235, 90),
                (225, 120, 255),
            )
            color_idx = (pygame.time.get_ticks() // 90) % len(flash_palette)
            tint_r, tint_g, tint_b = flash_palette[color_idx]
            player_image = player_image.copy()
            # BLEND_RGB_ADD only touches RGB — alpha is unchanged, so transparent
            # pixels stay transparent and the tint matches the sprite shape exactly
            tint_surface = pygame.Surface(player_image.get_size())
            tint_surface.fill((tint_r // 3, tint_g // 3, tint_b // 3))
            player_image.blit(tint_surface, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        elif player_skin_tint is not None:
            player_image = player_image.copy()
            tint_surface = pygame.Surface(player_image.get_size())
            tint_surface.fill(player_skin_tint)
            player_image.blit(tint_surface, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
            # Second pass makes premium skins much more visible in motion.
            tint_surface.fill((player_skin_tint[0] // 2, player_skin_tint[1] // 2, player_skin_tint[2] // 2))
            player_image.blit(tint_surface, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        # Dash afterimage: draw 3 semi-transparent ghost copies trailing behind the player
        if player_dash_timer > 0:
            dash_dir = 1 if player.orientation == 'right' else -1
            for _i in range(1, 4):
                ghost_rect = pygame.Rect(
                    player.rect.x - dash_dir * _i * 8,
                    player.rect.y,
                    player.rect.width, player.rect.height)
                ghost_off = camera.apply(ghost_rect)
                ghost_surf = player_image.copy()
                ghost_surf.set_alpha(max(0, 85 - _i * 25))
                screen.blit(ghost_surf, ghost_off)
        screen.blit(player_image, offset_rect)  #draws the player image at its rectangular position adjusted for camera

        # draw bullets with camera offsets
        for b in bullets.all():
            offset_rect = camera.apply(b.rect)
            screen.blit(b.image, offset_rect)  # draw at camera-offset position

        for fp in player.fire_projectiles:
            offset_rect = camera.apply(fp.rect)
            screen.blit(fp.image, offset_rect)  # draw at camera-offset position

        for w in walls:
            wall_offset = camera.apply(w.rect)
            screen.blit(w.image, wall_offset)  # draw wall at camera-offset position
        
        # Draw rotating firewalls
        for fw in rotating_firewalls:
            fw.draw(screen, camera)

        perf_overlay_visible = debug_overlay or always_show_perf
        if perf_overlay_visible:
            if recent_frame_ms:
                avg_ms = sum(recent_frame_ms) / len(recent_frame_ms)
                p95_ms = sorted(recent_frame_ms)[int((len(recent_frame_ms) - 1) * 0.95)]
            else:
                avg_ms = frame_ms
                p95_ms = frame_ms
            fps_live = 0.0 if dt <= 0 else (1.0 / max(0.0001, dt))
            fps_avg = 0.0 if avg_ms <= 0 else (1000.0 / avg_ms)
            mem_current_mb = 0.0
            mem_peak_mb = 0.0
            try:
                mem_current, mem_peak = tracemalloc.get_traced_memory()
                mem_current_mb = float(mem_current) / (1024.0 * 1024.0)
                mem_peak_mb = float(mem_peak) / (1024.0 * 1024.0)
            except Exception:
                pass
            perf_label = bar_label_font.render(
                f"Perf FPS {fps_live:4.1f} avg {fps_avg:4.1f}  frame {avg_ms:4.1f}ms p95 {p95_ms:4.1f}ms  mem {mem_current_mb:5.1f}/{mem_peak_mb:5.1f}MB",
                True,
                (220, 245, 220),
            )
            screen.blit(perf_label, (10, screen.get_height() - 82 if debug_overlay else screen.get_height() - 30))

        if debug_overlay:
            player_dbg = camera.apply(player.hitbox if hasattr(player, 'hitbox') else player.rect)
            pygame.draw.rect(screen, (80, 200, 255), player_dbg, 2)
            player_center = (player_dbg.centerx, player_dbg.centery)
            for enemy in melee_enemies:
                if enemy.alive:
                    hb = enemy.hitbox if hasattr(enemy, 'hitbox') else enemy.rect
                    eb = camera.apply(hb)
                    pygame.draw.rect(screen, (255, 120, 120), eb, 2)
                    state_s = font.render(f"{enemy.ai_state} stg:{getattr(enemy, 'stagger_timer', 0):.2f}", True, (255, 180, 180))
                    screen.blit(state_s, (eb.x - 8, eb.y - 18))
                    if enemy.ai_state == 'chase':
                        pygame.draw.line(screen, (255, 120, 120), (eb.centerx, eb.centery), player_center, 1)
            for enemy in charger_enemies + shield_enemies:
                if enemy.alive:
                    hb = enemy.hitbox if hasattr(enemy, 'hitbox') else enemy.rect
                    eb = camera.apply(hb)
                    pygame.draw.rect(screen, (255, 180, 90), eb, 2)
                    state_s = font.render(f"{enemy.ai_state} wrn:{getattr(enemy, 'warn_active', False)}", True, (255, 210, 160))
                    screen.blit(state_s, (eb.x - 8, eb.y - 18))
                    pygame.draw.line(screen, (255, 180, 90), (eb.centerx, eb.centery), player_center, 1)
            for enemy in ranged_enemies:
                if enemy.alive:
                    hb = enemy.hitbox if hasattr(enemy, 'hitbox') else enemy.rect
                    eb = camera.apply(hb)
                    pygame.draw.rect(screen, (220, 130, 255), eb, 2)
                    state_s = font.render(f"cd:{enemy.cooldown:.2f} stg:{getattr(enemy, 'stagger_timer', 0):.2f}", True, (230, 170, 255))
                    screen.blit(state_s, (eb.x - 8, eb.y - 18))
                    pygame.draw.line(screen, (220, 130, 255), (eb.centerx, eb.centery), player_center, 1)
            for wall in walls:
                pygame.draw.rect(screen, (120, 120, 210), camera.apply(wall.rect), 1)
            dbg_s = font.render(f"DEBUG OVERLAY ({debug_label})", True, (180, 255, 180))
            screen.blit(dbg_s, (10, screen.get_height() - 62))

        # Restore camera after shake so HUD-relative positions stay correct
        camera.x -= shake_ox
        camera.y -= shake_oy

        # Update and draw floating damage/pickup numbers
        for dn in damage_numbers[:]:
            dn.update(dt)
            dn.draw(screen, camera)
            if not dn.alive:
                damage_numbers.remove(dn)

        # Update and draw death particles
        for dp in death_particles[:]:
            dp.update(dt)
            dp.draw(screen, camera)
            if not dp.alive:
                death_particles.remove(dp)

        # Low-health vignette: red pulsing edges when HP < 35%
        if player and getattr(player, 'health', 50) / max(1, getattr(player, 'max_health', 50)) < 0.35:
            pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.004)
            a = int(160 * pulse)
            vg = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            w_s, h_s = screen.get_size()
            t = int(h_s * 0.18)
            pygame.draw.rect(vg, (210, 0, 0, a), (0, 0, w_s, t))
            pygame.draw.rect(vg, (210, 0, 0, a), (0, h_s - t, w_s, t))
            pygame.draw.rect(vg, (210, 0, 0, a), (0, 0, t, h_s))
            pygame.draw.rect(vg, (210, 0, 0, a), (w_s - t, 0, t, h_s))
            screen.blit(vg, (0, 0))

        # Level fade-in: black overlay that dissolves over the first 0.5 s
        if fade_in_timer > 0:
            fade_in_timer = max(0.0, fade_in_timer - dt)
            fade_alpha = int(255 * (fade_in_timer / 0.5))
            fade_surf = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            fade_surf.fill((0, 0, 0, fade_alpha))
            screen.blit(fade_surf, (0, 0))

        if timer_started and len(replay_video_frames) < replay_video_max_frames:
            replay_video_timer += dt
            if replay_video_timer >= replay_video_interval:
                replay_video_timer = 0.0
                try:
                    mini = pygame.transform.smoothscale(screen, (96, 54))
                    raw = pygame.image.tostring(mini, "RGB")
                    replay_video_frames.append({
                        "t": round(timer.get_elapsed_time(), 3),
                        "w": 96,
                        "h": 54,
                        "rgb": base64.b64encode(raw).decode("ascii"),
                    })
                except Exception:
                    pass

        pygame.display.update()

        for plat in platforms:
            plat.update(dt)  # update platform state (e.g., decay)
        

            
    pygame.quit()


if __name__ == "__main__":
    level()