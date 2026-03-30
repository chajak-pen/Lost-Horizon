import os
import math
import random
from datetime import datetime
from collections import deque
import pygame

from Classes import Button, Player, resolve_asset_path
from levels import level
from shop import shop_menu
from survival_mode import survival_mode
from challenge_codes import make_challenge_code, parse_challenge_code, make_daily_challenge
from game_settings import load_settings, save_settings
from debug_logger import debug_log
from ui_helpers import draw_wrapped_text, fit_text
from database import (
    create_connection,
    is_level_locked,
    get_unlocked_levels,
    is_hard_mode_unlocked,
    is_hard_mode_enabled,
    is_ng_plus_unlocked,
    is_ng_plus_enabled,
    set_ng_plus_enabled,
    save_daily_challenge_run,
    get_daily_challenge_top_scores,
    get_daily_challenge_top_times,
    get_meta_upgrades,
    purchase_meta_upgrade,
    list_level_replay_runs,
    get_replay_timeline,
)
from world_progression import (
    WORLD_DEFS,
    WORLD_ORDER,
    world_name,
    is_world_unlocked,
    is_world_hard_unlocked,
    highest_unlocked_normal_in_world,
)

pygame.init()

info = pygame.display.Info()
screen_width, screen_height = info.current_w, info.current_h


def _lock_message(level_num):
    if level_num <= 6:
        prev_level_num = level_num - 1
        prev_name = "Tutorial" if prev_level_num == 1 else f"Level {prev_level_num - 1}"
        return f"Complete {prev_name} first!"
    if level_num == 12:
        return "Complete Level 5 first!"
    if 7 <= level_num <= 11:
        return "Complete previous hard level first!"
    if level_num == 13:
        return "Complete Hard Level 5 first!"
    if level_num in (15, 16):
        return "Complete previous optional level first!"
    return "This level is locked."


def _load_hub_background():
    candidates = [
        "play_menu_background.png",
        os.path.join("..", "play_menu_background.png"),
        "play_background.jpg",
        os.path.join("..", "play_background.jpg"),
        "play_menu.JPEG",
        "play_menu.jpg",
        "play_menu.jpeg",
        os.path.join("..", "play_menu.JPEG"),
        os.path.join("..", "play_menu.jpg"),
        os.path.join("..", "play_menu.jpeg"),
        "background.jpg",
        "background.png",
    ]
    for path in candidates:
        try:
            return pygame.image.load(resolve_asset_path(path)).convert()
        except Exception:
            continue
    fallback = pygame.Surface((screen_width, screen_height))
    fallback.fill((18, 26, 30))
    return fallback


def _fade(screen, duration=260):
    fade_surface = pygame.Surface((screen.get_width(), screen.get_height()))
    fade_surface.fill((0, 0, 0))
    clock = pygame.time.Clock()
    elapsed = 0.0
    while elapsed < duration:
        dt = clock.tick(60)
        elapsed += dt
        alpha = int(255 * (elapsed / duration))
        if alpha > 255:
            alpha = 255
        fade_surface.set_alpha(alpha)
        screen.blit(fade_surface, (0, 0))
        pygame.display.update()


def _show_daily_leaderboard(screen, daily_info):
    date_key = daily_info.get('date_key')
    rows_score = get_daily_challenge_top_scores(date_key, 10)
    rows_time = get_daily_challenge_top_times(date_key, 10)

    title_font = pygame.font.SysFont("Arial", max(22, int(screen.get_height() * 0.05)), bold=True)
    head_font = pygame.font.SysFont("Arial", max(14, int(screen.get_height() * 0.03)), bold=True)
    row_font = pygame.font.SysFont("Arial", max(12, int(screen.get_height() * 0.024)))
    clock = pygame.time.Clock()

    while True:
        _ = clock.tick(60)
        sw, sh = screen.get_width(), screen.get_height()
        screen.fill((14, 20, 33))

        title = title_font.render(f"Daily Challenge - {date_key}", True, (230, 240, 255))
        subtitle = row_font.render(f"Level {daily_info.get('level_id')} | Seed {daily_info.get('seed')}", True, (190, 210, 240))
        screen.blit(title, (sw // 2 - title.get_width() // 2, 18))
        screen.blit(subtitle, (sw // 2 - subtitle.get_width() // 2, 58))

        left = pygame.Rect(30, 96, sw // 2 - 45, sh - 146)
        right = pygame.Rect(sw // 2 + 15, 96, sw // 2 - 45, sh - 146)
        for panel in (left, right):
            pygame.draw.rect(screen, (26, 36, 56), panel, border_radius=8)
            pygame.draw.rect(screen, (105, 145, 205), panel, 2, border_radius=8)

        l_head = head_font.render("Top Scores", True, (255, 230, 140))
        r_head = head_font.render("Fastest Times", True, (180, 230, 255))
        screen.blit(l_head, (left.x + 12, left.y + 10))
        screen.blit(r_head, (right.x + 12, right.y + 10))

        y = left.y + 42
        if rows_score:
            for idx, row in enumerate(rows_score, start=1):
                txt = row_font.render(f"{idx:>2}. {row[0]}  {row[1]}", True, (245, 240, 195))
                screen.blit(txt, (left.x + 12, y))
                y += 26
        else:
            screen.blit(row_font.render("No runs yet.", True, (220, 220, 220)), (left.x + 12, y))

        y = right.y + 42
        if rows_time:
            for idx, row in enumerate(rows_time, start=1):
                txt = row_font.render(f"{idx:>2}. {row[0]}  {row[1]:.2f}s", True, (190, 235, 255))
                screen.blit(txt, (right.x + 12, y))
                y += 26
        else:
            screen.blit(row_font.render("No runs yet.", True, (220, 220, 220)), (right.x + 12, y))

        hint = row_font.render("Esc / Backspace to return", True, (185, 200, 225))
        screen.blit(hint, (sw // 2 - hint.get_width() // 2, sh - 34))
        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                return True


def _choose_replay_for_level(screen, level_num, player_name):
    title_font = pygame.font.SysFont("Arial", max(22, int(screen.get_height() * 0.05)), bold=True)
    row_font = pygame.font.SysFont("Arial", max(12, int(screen.get_height() * 0.025)))
    hud_font = pygame.font.SysFont("Arial", max(12, int(screen.get_height() * 0.022)))
    clock = pygame.time.Clock()

    rows = list_level_replay_runs(level_num, limit=80, viewer_player_name=player_name)
    selected = 0

    while True:
        _ = clock.tick(60)
        rows = list_level_replay_runs(level_num, limit=80, viewer_player_name=player_name)
        if selected >= len(rows):
            selected = max(0, len(rows) - 1)

        sw, sh = screen.get_width(), screen.get_height()
        screen.fill((14, 20, 32))
        panel = pygame.Rect(40, 80, sw - 80, sh - 150)
        pygame.draw.rect(screen, (24, 36, 58), panel, border_radius=10)
        pygame.draw.rect(screen, (105, 150, 215), panel, 2, border_radius=10)

        title = title_font.render(f"Race Replay Selector - Level {level_num}", True, (235, 242, 255))
        screen.blit(title, (sw // 2 - title.get_width() // 2, 20))

        y = panel.y + 12
        if not rows:
            txt = row_font.render("No global replays found for this level.", True, (215, 225, 240))
            screen.blit(txt, (panel.x + 12, y))
        else:
            max_rows = max(5, (panel.height - 32) // 34)
            for i, row in enumerate(rows[:max_rows]):
                rr = pygame.Rect(panel.x + 10, y, panel.width - 20, 30)
                active = i == selected
                pygame.draw.rect(screen, (58, 88, 130) if active else (30, 46, 72), rr, border_radius=6)
                pygame.draw.rect(screen, (140, 200, 255) if active else (80, 120, 170), rr, 1, border_radius=6)
                mine_tag = " (YOU)" if row.get('player_name') == player_name else ""
                privacy = "PUBLIC" if row.get('is_public', True) else "PRIVATE"
                outcome = (row.get('run_outcome') or 'completed').upper()
                txt = f"#{row['replay_id']}  {row['player_name']}{mine_tag}  {row['completion_time']:.2f}s  score {row['score']}  {outcome}/{privacy}"
                label = row_font.render(fit_text(row_font, txt, rr.width - 14), True, (240, 245, 255))
                screen.blit(label, (rr.x + 8, rr.y + 5))
                y += 34

            if len(rows) > max_rows:
                more = hud_font.render(f"Showing {max_rows}/{len(rows)}", True, (175, 200, 230))
                screen.blit(more, (panel.x + 10, panel.bottom - 24))

        hint = "Up/Down select | Enter choose | Delete clear race replay | Esc cancel"
        draw_wrapped_text(screen, hud_font, hint, (190, 208, 235), pygame.Rect(20, sh - 60, sw - 40, 40), align="center", max_lines=2)
        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False, None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None, None
                if event.key == pygame.K_UP and selected > 0:
                    selected -= 1
                if event.key == pygame.K_DOWN and selected < len(rows) - 1:
                    selected += 1
                if event.key in (pygame.K_DELETE, pygame.K_BACKSPACE):
                    return True, None
                if event.key == pygame.K_RETURN and rows:
                    payload = get_replay_timeline(rows[selected]['replay_id'])
                    if payload and payload.get('frames'):
                        return True, payload


def _draw_player_pointer(screen, player_pos, target_pos, color, double=False):
    px, py = player_pos
    tx, ty = target_pos
    dx = tx - px
    dy = ty - py
    dist = math.hypot(dx, dy)
    if dist < 1:
        return
    ux = dx / dist
    uy = dy / dist
    perp_x = -uy
    perp_y = ux

    # Pointer starts near player and points toward target.
    shaft_start = (px + ux * 24, py + uy * 24)
    shaft_end = (px + ux * 66, py + uy * 66)
    tip = (px + ux * 82, py + uy * 82)
    base_left = (tip[0] - ux * 14 + perp_x * 8, tip[1] - uy * 14 + perp_y * 8)
    base_right = (tip[0] - ux * 14 - perp_x * 8, tip[1] - uy * 14 - perp_y * 8)

    pygame.draw.line(screen, color, shaft_start, shaft_end, 4)
    pygame.draw.line(screen, (35, 35, 35), shaft_start, shaft_end, 1)
    pygame.draw.polygon(screen, color, [tip, base_left, base_right])
    pygame.draw.polygon(screen, (35, 35, 35), [tip, base_left, base_right], 2)

    if double:
        off = 10
        s2 = (shaft_start[0] + perp_x * off, shaft_start[1] + perp_y * off)
        e2 = (shaft_end[0] + perp_x * off, shaft_end[1] + perp_y * off)
        t2 = (tip[0] + perp_x * off, tip[1] + perp_y * off)
        bl2 = (base_left[0] + perp_x * off, base_left[1] + perp_y * off)
        br2 = (base_right[0] + perp_x * off, base_right[1] + perp_y * off)
        pygame.draw.line(screen, color, s2, e2, 4)
        pygame.draw.line(screen, (35, 35, 35), s2, e2, 1)
        pygame.draw.polygon(screen, color, [t2, bl2, br2])
        pygame.draw.polygon(screen, (35, 35, 35), [t2, bl2, br2], 2)


def _highest_unlocked_normal_level(player_name, world_id):
    unlocked = set(get_unlocked_levels(player_name))
    return highest_unlocked_normal_in_world(unlocked, world_id)


class HubDoor:
    def __init__(self, x, y, w, h, label, target_type, target_value, accent=(170, 130, 60)):
        self.rect = pygame.Rect(x, y, w, h)
        self.label = label
        self.target_type = target_type  # "level" | "page" | "shop"
        self.target_value = target_value
        self.accent = accent

    def center(self):
        return self.rect.center

    def draw(self, screen, camera, title_font, label_font, locked=False, active=False):
        draw_rect = self.rect.move(-int(camera[0]), -int(camera[1]))

        # Small blended door style so it sits in the background naturally.
        frame_col = (165, 145, 110) if active else (112, 98, 76)
        panel_col = (55, 44, 30)
        accent_col = self.accent
        if locked:
            frame_col = (108, 108, 108)
            panel_col = (62, 62, 62)
            accent_col = (92, 92, 92)

        door_surf = pygame.Surface((draw_rect.w, draw_rect.h), pygame.SRCALPHA)
        door_surf.fill((0, 0, 0, 0))

        # Arch body
        pygame.draw.rect(door_surf, (*panel_col, 185), (0, 10, draw_rect.w, draw_rect.h - 10), border_radius=7)
        pygame.draw.rect(door_surf, (*frame_col, 210), (0, 10, draw_rect.w, draw_rect.h - 10), 2, border_radius=7)

        # Sign plate
        plate = pygame.Rect(4, 6, draw_rect.w - 8, 18)
        pygame.draw.rect(door_surf, (*accent_col, 210), plate, border_radius=5)

        screen.blit(door_surf, draw_rect.topleft)

        sign = title_font.render(self.label, True, (245, 245, 245))
        screen.blit(sign, (draw_rect.centerx - sign.get_width() // 2, draw_rect.y + 7))

        if self.target_type == "page":
            tag_text = "Portal"
        elif self.target_type == "shop":
            tag_text = "Shop"
        elif self.target_type == "survival":
            tag_text = "Survival"
        else:
            tag_text = "Level"
        if locked:
            tag_text = "Locked"

        tag = label_font.render(tag_text, True, (230, 230, 230))
        screen.blit(tag, (draw_rect.centerx - tag.get_width() // 2, draw_rect.bottom + 4))


def _add_edge(edges, a, b):
    edges.setdefault(a, set()).add(b)
    edges.setdefault(b, set()).add(a)


def _build_hub_graph(page_name, active_world, doors):
    node_positions = {}
    node_radii = {}
    edges = {}
    segments = []
    plaza_world = (0, 0)

    def add_node(node_id, pos, radius=34):
        node_positions[node_id] = pos
        node_radii[node_id] = radius

    def connect(a, b):
        _add_edge(edges, a, b)
        segments.append((node_positions[a], node_positions[b]))

    if page_name == "main":
        plaza_world = (2200, 940)
        points = {
            "center": plaza_world,
            "west": (1910, 940),
            "east": (2490, 940),
            "north": (2200, 770),
            "south": (2200, 1110),
            "west_top": (1680, 820),
            "west_low": (1680, 1035),
            "east_top": (2710, 840),
            "east_low": (2710, 1030),
        }
        connections = [
            ("center", "west"),
            ("center", "east"),
            ("center", "north"),
            ("center", "south"),
            ("west", "west_top"),
            ("west", "west_low"),
            ("east", "east_top"),
            ("east", "east_low"),
        ]
        routes = {
            "Tutorial": "south",
            f"W{active_world} L1": "west_top",
            f"W{active_world} L2": "north",
            f"W{active_world} L3": "east_top",
            f"W{active_world} L4": "east_low",
            f"W{active_world} L5": "east_low",
            f"W{active_world} Boss": "west_low",
            "Hard": "west_top",
            "Optional": "east_low",
            "Shop": "west_top",
            "Survival": "south",
            "World 1": "east_top",
            "World 2": "east_top",
            "World 3": "east_top",
        }
    elif page_name == "hard":
        plaza_world = (1700, 910)
        points = {
            "center": plaza_world,
            "left": (1450, 910),
            "right": (1960, 910),
            "top": (1700, 760),
            "bottom": (1700, 1070),
            "left_top": (1320, 800),
            "left_bottom": (1320, 1030),
            "right_top": (2090, 800),
            "right_bottom": (2090, 1040),
        }
        connections = [
            ("center", "left"),
            ("center", "right"),
            ("center", "top"),
            ("center", "bottom"),
            ("left", "left_top"),
            ("left", "left_bottom"),
            ("right", "right_top"),
            ("right", "right_bottom"),
        ]
        routes = {
            f"W{active_world} H1": "left_top",
            f"W{active_world} H2": "top",
            f"W{active_world} H3": "right_top",
            f"W{active_world} H4": "right_bottom",
            f"W{active_world} H5": "bottom",
            f"W{active_world} Hard Boss": "left_bottom",
            "Main": "right",
        }
    else:
        plaza_world = (1560, 900)
        points = {
            "center": plaza_world,
            "left": (1360, 900),
            "right": (1760, 900),
            "top": (1560, 760),
            "bottom": (1560, 1045),
            "far_left": (1200, 950),
            "far_right": (1940, 940),
        }
        connections = [
            ("center", "left"),
            ("center", "right"),
            ("center", "top"),
            ("center", "bottom"),
            ("left", "far_left"),
            ("right", "far_right"),
        ]
        routes = {
            "Optional 1": "left",
            "Optional 2": "top",
            "Optional 3": "right",
            "Main": "far_right",
            "Hard": "far_left",
        }

    for node_id, pos in points.items():
        radius = 48 if node_id == "center" else 34
        add_node(node_id, pos, radius)

    for a, b in connections:
        connect(a, b)

    door_nodes = {}
    for d in doors:
        node_id = f"door::{d.label}"
        door_nodes[d.label] = node_id
        add_node(node_id, d.center(), max(26, min(48, d.rect.w // 2 + 6)))
        route_anchor = routes.get(d.label)
        if route_anchor and route_anchor in node_positions:
            connect(route_anchor, node_id)

    return {
        "positions": node_positions,
        "radii": node_radii,
        "edges": edges,
        "segments": segments,
        "door_nodes": door_nodes,
        "junction_ids": [n for n in points.keys() if n != "center"],
        "plaza": plaza_world,
    }


def _nearest_graph_node(world_pos, node_positions):
    px, py = world_pos
    best = None
    best_dist_sq = 10 ** 9
    for node_id, (nx, ny) in node_positions.items():
        dx = nx - px
        dy = ny - py
        dist_sq = dx * dx + dy * dy
        if dist_sq < best_dist_sq:
            best_dist_sq = dist_sq
            best = node_id
    return best


def _pick_clicked_node(world_pos, doors, nav_graph):
    x, y = world_pos

    for d in doors:
        if d.rect.collidepoint(x, y):
            return nav_graph["door_nodes"].get(d.label)

    best = None
    best_dist_sq = 10 ** 9
    for node_id, (nx, ny) in nav_graph["positions"].items():
        r = nav_graph["radii"].get(node_id, 34)
        dx = nx - x
        dy = ny - y
        dist_sq = dx * dx + dy * dy
        if dist_sq <= (r * r) and dist_sq < best_dist_sq:
            best_dist_sq = dist_sq
            best = node_id
    return best


def _find_node_path(edges, start, target):
    if start is None or target is None:
        return []
    if start == target:
        return [start]

    queue = deque([start])
    parent = {start: None}

    while queue:
        cur = queue.popleft()
        for nxt in edges.get(cur, ()):
            if nxt in parent:
                continue
            parent[nxt] = cur
            if nxt == target:
                queue.clear()
                break
            queue.append(nxt)

    if target not in parent:
        return []

    path = []
    cur = target
    while cur is not None:
        path.append(cur)
        cur = parent[cur]
    path.reverse()
    return path


def _build_page_layout(page_name, hard_mode_active, active_world=1):
    # Returns world_size (w, h), spawn (x, y), doors
    world_cfg = WORLD_DEFS.get(active_world, WORLD_DEFS[1])
    n = world_cfg["normal_levels"]
    h = world_cfg["hard_levels"]
    normal_boss = world_cfg["normal_boss"]
    hard_boss = world_cfg["hard_boss"]

    if page_name == "main":
        world_w, world_h = 4400, 1800
        # Main hub arranged as a cluster around the center (not linear rows).
        spawn = (2080, 930)
        doors = [
            HubDoor(2080, 980, 96, 126, "Tutorial", "level", 1, (120, 140, 210)),
            HubDoor(1740, 760, 90, 118, f"W{active_world} L1", "level", n[0], (80, 120, 200)),
            HubDoor(2080, 690, 90, 118, f"W{active_world} L2", "level", n[1], (70, 145, 90)),
            HubDoor(2440, 770, 90, 118, f"W{active_world} L3", "level", n[2], (90, 130, 80)),
            HubDoor(2610, 1030, 90, 118, f"W{active_world} L4", "level", n[3], (130, 85, 60)),
            HubDoor(2280, 1170, 90, 118, f"W{active_world} L5", "level", n[4], (115, 95, 70)),
            HubDoor(1890, 1160, 98, 130, f"W{active_world} Boss", "level", normal_boss, (165, 55, 55)),
            HubDoor(1240, 790, 98, 130, "Hard", "page", "hard", (170, 40, 40)),
            HubDoor(2830, 920, 98, 130, "Optional", "page", "optional", (50, 90, 165)),
            HubDoor(1540, 700, 92, 122, "Shop", "shop", "shop", (165, 130, 60)),
            HubDoor(1540, 1080, 102, 132, "Survival", "survival", "survival", (140, 85, 160)),
            HubDoor(3240, 760, 96, 126, "World 1", "world", 1, (110, 110, 130)),
            HubDoor(3480, 760, 96, 126, "World 2", "world", 2, (110, 110, 130)),
            HubDoor(3720, 760, 96, 126, "World 3", "world", 3, (110, 110, 130)),
        ]
        if active_world != 1:
            doors = [d for d in doors if not (d.target_type == "page" and d.target_value == "optional")]
        return (world_w, world_h), spawn, doors

    if page_name == "hard":
        world_w, world_h = 3600, 1700
        spawn = (1620, 900)
        doors = [
            HubDoor(1280, 760, 96, 124, f"W{active_world} H1", "level", h[0], (185, 70, 70)),
            HubDoor(1650, 710, 96, 124, f"W{active_world} H2", "level", h[1], (185, 70, 70)),
            HubDoor(2020, 790, 96, 124, f"W{active_world} H3", "level", h[2], (185, 70, 70)),
            HubDoor(2190, 1040, 96, 124, f"W{active_world} H4", "level", h[3], (185, 70, 70)),
            HubDoor(1840, 1170, 96, 124, f"W{active_world} H5", "level", h[4], (185, 70, 70)),
            HubDoor(1460, 1110, 104, 136, f"W{active_world} Hard Boss", "level", hard_boss, (205, 55, 55)),
            HubDoor(2500, 900, 104, 136, "Main", "page", "main", (80, 80, 90)),
        ]
        return (world_w, world_h), spawn, doors

    world_w, world_h = 3000, 1650
    spawn = (1450, 880)
    doors = [
        HubDoor(1180, 760, 100, 128, "Optional 1", "level", 14, (70, 120, 185)),
        HubDoor(1560, 720, 100, 128, "Optional 2", "level", 15, (70, 120, 185)),
        HubDoor(1940, 810, 100, 128, "Optional 3", "level", 16, (70, 120, 185)),
        HubDoor(2200, 1060, 106, 136, "Main", "page", "main", (80, 80, 90)),
    ]

    if hard_mode_active and active_world == 1:
        doors.append(HubDoor(980, 1020, 106, 136, "Hard", "page", "hard", (170, 40, 40)))

    return (world_w, world_h), spawn, doors


def _is_page_door_locked(door, hard_mode_active):
    if door.target_type != "page":
        return False
    if door.target_value == "hard":
        return not hard_mode_active
    return False


def should_lock_door(easy_mode, door, hard_mode_active, unlocked_levels_set, player_name):
    if easy_mode:
        return False
    if door.target_type == "level":
        return is_level_locked(player_name, int(door.target_value))
    if door.target_type == "world":
        return not is_world_unlocked(unlocked_levels_set, int(door.target_value))
    if door.target_type == "page":
        return _is_page_door_locked(door, hard_mode_active)
    return False


def play_menu(player_name):
    if not player_name:
        return True

    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Lost Horizon - Play Menu Hub")

    bg_base = _load_hub_background()
    bg_tile = pygame.transform.scale(bg_base, (screen_width, screen_height))

    back_size = max(24, int(screen_width * 0.04))
    back_image = pygame.image.load(resolve_asset_path("back button.jpg")).convert_alpha()
    back_image = pygame.transform.scale(back_image, (back_size, back_size))
    back_button = Button(10, 10, back_image)

    title_font = pygame.font.SysFont("Arial", max(12, int(screen_height * 0.023)), bold=True)
    label_font = pygame.font.SysFont("Arial", max(11, int(screen_height * 0.020)))
    hud_font = pygame.font.SysFont("Arial", max(12, int(screen_height * 0.026)), bold=True)
    msg_font = pygame.font.SysFont("Arial", max(14, int(screen_height * 0.034)), bold=True)

    unlocked_levels = get_unlocked_levels(player_name)
    hard_mode_unlocked = is_hard_mode_unlocked(player_name) or 7 in unlocked_levels
    hard_mode_active = hard_mode_unlocked and is_hard_mode_enabled(player_name)
    ng_plus_unlocked = is_ng_plus_unlocked(player_name)
    ng_plus_active = ng_plus_unlocked and is_ng_plus_enabled(player_name)
    settings_blob = load_settings()
    easy_mode = bool(settings_blob.get("easy_mode", False))
    onboarding_seen = bool(settings_blob.get("onboarding_seen", False))
    onboarding_steps = [
        "Welcome to the hub: click paths/doors and press E to enter.",
        "Use U for meta upgrades and C/D/J for challenge tools.",
        "Tip: Settings controls keybinds + Easy Mode training ground.",
    ]
    onboarding_idx = 0
    onboarding_timer = 7.0 if not onboarding_seen else 0.0

    current_page = "main"
    active_world = 1
    unlocked_levels_set = set(unlocked_levels)
    world_hard_unlocked = is_world_hard_unlocked(unlocked_levels_set, active_world)
    world_size, spawn_pos, doors = _build_page_layout(current_page, hard_mode_active and world_hard_unlocked, active_world)
    nav_graph = _build_hub_graph(current_page, active_world, doors)

    hub_player = Player("player sprite.png", spawn_pos[0], spawn_pos[1], w=40, h=60, orientation='right')
    hub_player.update_position()
    player_x = float(hub_player.rect.x)
    player_y = float(hub_player.rect.y)

    player_speed = 280
    camera_x = 0.0
    camera_y = 0.0
    queued_nodes = []

    message = "Click a path node or door to move. Press E near a door to enter."
    message_color = (240, 240, 230)
    message_timer = 4.0
    active_challenge_code = None
    active_daily_info = None
    selected_race_replays = {}
    upg_cache = get_meta_upgrades(player_name)
    upg_refresh_timer = 0.0
    daily_pool = []
    for wid in WORLD_ORDER:
        wdef = WORLD_DEFS.get(wid, {})
        daily_pool.extend(wdef.get('normal_levels', []))
        if wdef.get('normal_boss') is not None:
            daily_pool.append(wdef.get('normal_boss'))
        daily_pool.extend(wdef.get('optional_levels', []))

    clock = pygame.time.Clock()
    while True:
        dt = clock.tick(60) / 1000.0
        upg_refresh_timer = max(0.0, upg_refresh_timer - dt)
        if upg_refresh_timer <= 0.0:
            upg_cache = get_meta_upgrades(player_name)
            upg_refresh_timer = 1.0

        unlocked_levels = get_unlocked_levels(player_name)
        unlocked_levels_set = set(unlocked_levels)
        hard_mode_unlocked = is_hard_mode_unlocked(player_name) or 7 in unlocked_levels
        hard_mode_active = hard_mode_unlocked and is_hard_mode_enabled(player_name)
        ng_plus_unlocked = is_ng_plus_unlocked(player_name)
        ng_plus_active = ng_plus_unlocked and is_ng_plus_enabled(player_name)
        settings_blob = load_settings()
        easy_mode = bool(settings_blob.get("easy_mode", False))
        world_hard_unlocked = is_world_hard_unlocked(unlocked_levels_set, active_world)

        nearest = None
        nearest_dist_sq = 10 ** 9
        p_cx, p_cy = hub_player.rect.center
        for d in doors:
            dx = d.center()[0] - p_cx
            dy = d.center()[1] - p_cy
            dist_sq = dx * dx + dy * dy
            if dist_sq < nearest_dist_sq:
                nearest_dist_sq = dist_sq
                nearest = d

        if current_page == "hard" and (not easy_mode) and not (hard_mode_active and world_hard_unlocked):
            current_page = "main"
            world_size, spawn_pos, doors = _build_page_layout(current_page, hard_mode_active and world_hard_unlocked, active_world)
            hub_player.rect.topleft = spawn_pos
            hub_player.update_position()
            message = "Hard hub is locked for this world."
            message_color = (255, 210, 140)
            message_timer = 2.8

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if back_button.handle_event(event):
                return True

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_x, mouse_y = event.pos
                world_click = (mouse_x + int(camera_x), mouse_y + int(camera_y))
                target_node = _pick_clicked_node(world_click, doors, nav_graph)
                if target_node is not None:
                    start_node = _nearest_graph_node(hub_player.rect.center, nav_graph["positions"])
                    path = _find_node_path(nav_graph["edges"], start_node, target_node)
                    if len(path) > 1:
                        queued_nodes = path[1:]
                        message = "Moving"
                        if target_node.startswith("door::"):
                            message += f" to {target_node.split('::', 1)[1]}"
                        message_color = (210, 230, 255)
                        message_timer = 1.2
                    elif len(path) == 1:
                        queued_nodes = []
                        message = "Already at that node."
                        message_color = (220, 225, 240)
                        message_timer = 0.9

            if event.type == pygame.KEYDOWN and event.key == pygame.K_e:
                nearest = None
                nearest_dist_sq = 10 ** 9
                p_cx, p_cy = hub_player.rect.center
                for d in doors:
                    cx, cy = d.center()
                    dx, dy = cx - p_cx, cy - p_cy
                    dist_sq = dx * dx + dy * dy
                    if dist_sq < nearest_dist_sq:
                        nearest_dist_sq = dist_sq
                        nearest = d

                if nearest is not None and nearest_dist_sq <= (120 * 120):
                    if nearest.target_type == "page":
                        locked_page = (not easy_mode) and _is_page_door_locked(nearest, hard_mode_active and world_hard_unlocked)
                        if locked_page:
                            if nearest.target_value == "hard" and not world_hard_unlocked:
                                message = "Beat this world's normal + boss and previous hard boss first."
                            elif nearest.target_value == "hard" and hard_mode_unlocked and not hard_mode_active:
                                message = "Enable Hard Mode in Settings to enter this portal."
                            else:
                                message = "Unlock Hard Mode by completing normal progression first."
                            message_color = (255, 200, 120)
                            message_timer = 2.4
                        else:
                            _fade(screen, 260)
                            current_page = nearest.target_value
                            debug_log("hub_enter_page", f"player={player_name} page={current_page}")
                            world_size, spawn_pos, doors = _build_page_layout(current_page, hard_mode_active and world_hard_unlocked, active_world)
                            nav_graph = _build_hub_graph(current_page, active_world, doors)
                            hub_player.rect.topleft = spawn_pos
                            hub_player.update_position()
                            player_x = float(hub_player.rect.x)
                            player_y = float(hub_player.rect.y)
                            queued_nodes = []
                            message = f"Entered {current_page.title()} hub ({world_name(active_world)})"
                            message_color = (210, 230, 255)
                            message_timer = 1.5

                    elif nearest.target_type == "world":
                        target_world = int(nearest.target_value)
                        if (not easy_mode) and (not is_world_unlocked(unlocked_levels_set, target_world)):
                            prev_world = target_world - 1
                            prev_name = world_name(prev_world)
                            message = f"Beat {prev_name} normal boss to unlock this world."
                            message_color = (255, 200, 120)
                            message_timer = 2.5
                        else:
                            _fade(screen, 260)
                            active_world = target_world
                            debug_log("hub_enter_world", f"player={player_name} world={active_world}")
                            world_hard_unlocked = is_world_hard_unlocked(unlocked_levels_set, active_world)
                            current_page = "main"
                            world_size, spawn_pos, doors = _build_page_layout(current_page, hard_mode_active and world_hard_unlocked, active_world)
                            nav_graph = _build_hub_graph(current_page, active_world, doors)
                            hub_player.rect.topleft = spawn_pos
                            hub_player.update_position()
                            player_x = float(hub_player.rect.x)
                            player_y = float(hub_player.rect.y)
                            queued_nodes = []
                            message = f"Entered {world_name(active_world)}"
                            message_color = (210, 230, 255)
                            message_timer = 1.6

                    elif nearest.target_type == "shop":
                        _fade(screen, 220)
                        keep_running = shop_menu(player_name)
                        debug_log("hub_enter_shop", f"player={player_name}")
                        if not keep_running:
                            return False
                        world_size, spawn_pos, doors = _build_page_layout(current_page, hard_mode_active and world_hard_unlocked, active_world)
                        nav_graph = _build_hub_graph(current_page, active_world, doors)
                        hub_player.rect.x = max(0, min(hub_player.rect.x, world_size[0] - hub_player.rect.width))
                        hub_player.rect.y = max(0, min(hub_player.rect.y, world_size[1] - hub_player.rect.height))
                        hub_player.update_position()
                        player_x = float(hub_player.rect.x)
                        player_y = float(hub_player.rect.y)
                        queued_nodes = []
                        message = "Returned from shop"
                        message_color = (220, 240, 205)
                        message_timer = 1.5

                    elif nearest.target_type == "survival":
                        _fade(screen, 220)
                        keep_running = survival_mode(player_name)
                        debug_log("hub_enter_survival", f"player={player_name}")
                        if not keep_running:
                            return False
                        world_size, spawn_pos, doors = _build_page_layout(current_page, hard_mode_active and world_hard_unlocked, active_world)
                        nav_graph = _build_hub_graph(current_page, active_world, doors)
                        hub_player.rect.x = max(0, min(hub_player.rect.x, world_size[0] - hub_player.rect.width))
                        hub_player.rect.y = max(0, min(hub_player.rect.y, world_size[1] - hub_player.rect.height))
                        hub_player.update_position()
                        player_x = float(hub_player.rect.x)
                        player_y = float(hub_player.rect.y)
                        queued_nodes = []
                        message = "Returned from survival"
                        message_color = (220, 220, 255)
                        message_timer = 1.6

                    elif nearest.target_type == "level":
                        level_num = int(nearest.target_value)
                        if (not easy_mode) and is_level_locked(player_name, level_num):
                            message = _lock_message(level_num)
                            message_color = (255, 190, 120)
                            message_timer = 2.6
                        else:
                            _fade(screen, 280)
                            use_code = active_challenge_code
                            parsed = parse_challenge_code(use_code) if use_code else None
                            if parsed and parsed.get('level_id') != level_num:
                                use_code = None

                            run_hooks = None
                            daily_info = active_daily_info if active_daily_info and active_daily_info.get('level_id') == level_num else None
                            race_payload = selected_race_replays.get(level_num)
                            if daily_info is not None:
                                def _on_complete(payload):
                                    save_daily_challenge_run(
                                        player_name,
                                        daily_info.get('date_key'),
                                        daily_info.get('level_id'),
                                        daily_info.get('seed'),
                                        daily_info.get('challenge_code'),
                                        payload.get('score', 0),
                                        payload.get('completion_time', 0.0),
                                        payload.get('coins_collected', 0),
                                    )
                                run_hooks = {'on_complete': _on_complete}

                            keep_running = level(
                                level_num,
                                player_name=player_name,
                                challenge_code=use_code,
                                leaderboard_hooks=run_hooks,
                                race_replay=race_payload,
                            )
                            debug_log("hub_enter_level", f"player={player_name} level={level_num} easy={easy_mode}")
                            if not keep_running:
                                return False

                            if daily_info is not None:
                                message = f"Daily run submitted for {daily_info.get('date_key')}"
                                message_color = (190, 235, 245)
                                message_timer = 2.0

                            unlocked_levels = get_unlocked_levels(player_name)
                            unlocked_levels_set = set(unlocked_levels)
                            hard_mode_unlocked = is_hard_mode_unlocked(player_name) or 7 in unlocked_levels
                            hard_mode_active = hard_mode_unlocked and is_hard_mode_enabled(player_name)
                            world_hard_unlocked = is_world_hard_unlocked(unlocked_levels_set, active_world)
                            if current_page == "hard" and not (hard_mode_active and world_hard_unlocked):
                                current_page = "main"
                            world_size, spawn_pos, doors = _build_page_layout(current_page, hard_mode_active and world_hard_unlocked, active_world)
                            nav_graph = _build_hub_graph(current_page, active_world, doors)
                            hub_player.rect.x = max(0, min(hub_player.rect.x, world_size[0] - hub_player.rect.width))
                            hub_player.rect.y = max(0, min(hub_player.rect.y, world_size[1] - hub_player.rect.height))
                            hub_player.update_position()
                            player_x = float(hub_player.rect.x)
                            player_y = float(hub_player.rect.y)
                            queued_nodes = []
                            message = "Returned from level"
                            message_color = (200, 235, 205)
                            message_timer = 1.4
                            if not onboarding_seen:
                                settings_blob["onboarding_seen"] = True
                                save_settings(settings_blob)
                                onboarding_seen = True
                                onboarding_timer = 0.0

            if event.type == pygame.KEYDOWN and event.key == pygame.K_c:
                if nearest is not None and nearest.target_type == "level":
                    level_num = int(nearest.target_value)
                    mods = {
                        "enemy_mult": round(random.uniform(1.0, 1.45), 2),
                        "gravity_mult": round(random.uniform(0.85, 1.2), 2),
                        "coin_mult": round(random.uniform(0.9, 1.5), 2),
                    }
                    active_challenge_code = make_challenge_code(level_num, modifiers=mods)
                    message = f"Challenge code for L{level_num}: {active_challenge_code[:26]}..."
                    message_color = (200, 225, 255)
                    message_timer = 4.0
                else:
                    message = "Stand near a level door and press C to generate a race code."
                    message_color = (255, 220, 140)
                    message_timer = 2.4

            if event.type == pygame.KEYDOWN and event.key == pygame.K_d:
                daily = make_daily_challenge(daily_pool, now=datetime.now())
                if daily is None:
                    message = "No available levels for daily challenge yet."
                    message_color = (255, 220, 140)
                    message_timer = 2.6
                else:
                    active_daily_info = daily
                    active_challenge_code = daily['challenge_code']
                    _fade(screen, 260)

                    def _on_complete_daily(payload):
                        save_daily_challenge_run(
                            player_name,
                            daily.get('date_key'),
                            daily.get('level_id'),
                            daily.get('seed'),
                            daily.get('challenge_code'),
                            payload.get('score', 0),
                            payload.get('completion_time', 0.0),
                            payload.get('coins_collected', 0),
                        )

                    keep_running = level(
                        int(daily['level_id']),
                        player_name=player_name,
                        challenge_code=daily['challenge_code'],
                        leaderboard_hooks={'on_complete': _on_complete_daily},
                        race_replay=selected_race_replays.get(int(daily['level_id'])),
                    )
                    if not keep_running:
                        return False

                    world_size, spawn_pos, doors = _build_page_layout(current_page, hard_mode_active and world_hard_unlocked, active_world)
                    nav_graph = _build_hub_graph(current_page, active_world, doors)
                    hub_player.rect.x = max(0, min(hub_player.rect.x, world_size[0] - hub_player.rect.width))
                    hub_player.rect.y = max(0, min(hub_player.rect.y, world_size[1] - hub_player.rect.height))
                    hub_player.update_position()
                    player_x = float(hub_player.rect.x)
                    player_y = float(hub_player.rect.y)
                    queued_nodes = []
                    message = f"Daily challenge run complete ({daily['date_key']}). Press J for leaderboard."
                    message_color = (185, 235, 255)
                    message_timer = 3.2

            if event.type == pygame.KEYDOWN and event.key == pygame.K_j:
                if active_daily_info is None:
                    active_daily_info = make_daily_challenge(daily_pool, now=datetime.now())
                if active_daily_info is not None:
                    keep_running = _show_daily_leaderboard(screen, active_daily_info)
                    if not keep_running:
                        return False

            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                if nearest is not None and nearest.target_type == "level":
                    level_num = int(nearest.target_value)
                    ok, payload = _choose_replay_for_level(screen, level_num, player_name)
                    if ok is False:
                        return False
                    if ok is None:
                        message = "Replay selection cancelled."
                        message_color = (210, 220, 240)
                        message_timer = 1.5
                    elif payload is None:
                        selected_race_replays.pop(level_num, None)
                        message = f"Cleared replay race target for L{level_num}."
                        message_color = (220, 220, 220)
                        message_timer = 2.0
                    else:
                        selected_race_replays[level_num] = payload
                        message = f"Racing L{level_num} against {payload.get('player_name', 'Unknown')} #{payload.get('replay_id', '?')}"
                        message_color = (165, 230, 255)
                        message_timer = 2.8
                else:
                    message = "Stand near a level door and press R to pick a replay race ghost."
                    message_color = (255, 220, 140)
                    message_timer = 2.5

            if event.type == pygame.KEYDOWN and event.key == pygame.K_n:
                if not ng_plus_unlocked:
                    message = "Beat a hard boss to unlock New Game+."
                    message_color = (255, 200, 120)
                    message_timer = 2.0
                else:
                    conn = create_connection()
                    if conn:
                        set_ng_plus_enabled(conn, player_name, not ng_plus_active)
                        conn.close()
                    ng_plus_active = not ng_plus_active
                    message = f"New Game+ {'enabled' if ng_plus_active else 'disabled'}"
                    message_color = (255, 205, 140)
                    message_timer = 1.8

            if event.type == pygame.KEYDOWN and event.key == pygame.K_u:
                choices = ['mobility', 'survivability', 'economy']
                # Auto-pick the lowest level path first for a smooth starter progression.
                stat = min(choices, key=lambda k: upg_cache.get(k, 0))
                ok, msg = purchase_meta_upgrade(player_name, stat)
                message = msg
                message_color = (170, 235, 180) if ok else (255, 210, 150)
                message_timer = 2.4
                if ok:
                    upg_cache = get_meta_upgrades(player_name)
                    upg_refresh_timer = 1.0

            if event.type == pygame.KEYDOWN and event.key == pygame.K_RIGHT and not onboarding_seen:
                onboarding_idx = min(len(onboarding_steps) - 1, onboarding_idx + 1)
                onboarding_timer = 6.0 if onboarding_idx < len(onboarding_steps) - 1 else 0.0

        move_x = 0.0
        move_y = 0.0
        if queued_nodes:
            next_node = queued_nodes[0]
            target_x, target_y = nav_graph["positions"][next_node]
            player_cx, player_cy = hub_player.rect.center
            dx = target_x - player_cx
            dy = target_y - player_cy
            dist = math.hypot(dx, dy)

            if dist <= max(2.0, player_speed * dt):
                hub_player.rect.center = (int(target_x), int(target_y))
                player_x = float(hub_player.rect.x)
                player_y = float(hub_player.rect.y)
                queued_nodes.pop(0)
            elif dist > 0:
                move_x = dx / dist
                move_y = dy / dist
                if move_x < 0:
                    hub_player.orientation = 'left'
                elif move_x > 0:
                    hub_player.orientation = 'right'

                player_x += move_x * player_speed * dt
                player_y += move_y * player_speed * dt
                hub_player.rect.x = int(round(player_x))
                hub_player.rect.y = int(round(player_y))

            if not queued_nodes:
                message = "Arrived. Click another node to continue."
                message_color = (210, 240, 210)
                message_timer = 1.3

        world_w, world_h = world_size
        if hub_player.rect.left < 0:
            hub_player.rect.left = 0
        if hub_player.rect.right > world_w:
            hub_player.rect.right = world_w
        if hub_player.rect.top < 0:
            hub_player.rect.top = 0
        if hub_player.rect.bottom > world_h:
            hub_player.rect.bottom = world_h
        hub_player.update_position()

        is_moving = bool(queued_nodes) or (abs(move_x) > 1e-5 or abs(move_y) > 1e-5)
        hub_player.update_animation(dt, is_moving=is_moving, jumping=False)

        target_cam_x = hub_player.rect.centerx - screen_width // 2
        target_cam_y = hub_player.rect.centery - screen_height // 2
        cam_lerp = min(1.0, 8.0 * dt)
        camera_x += (target_cam_x - camera_x) * cam_lerp
        camera_y += (target_cam_y - camera_y) * cam_lerp
        camera_x = max(0, min(camera_x, world_w - screen_width))
        camera_y = max(0, min(camera_y, world_h - screen_height))

        tile_w, tile_h = bg_tile.get_width(), bg_tile.get_height()
        px = int(camera_x * 0.35) % tile_w
        py = int(camera_y * 0.22) % tile_h
        for gx in range(-1, 2):
            for gy in range(-1, 2):
                screen.blit(bg_tile, (gx * tile_w - px, gy * tile_h - py))

        tint = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
        tint.fill((12, 16, 22, 85))
        screen.blit(tint, (0, 0))

        # Wide dirt paths with fork/merge junctions, rendered for every hub page.

        def to_screen(pt):
            return (pt[0] - int(camera_x), pt[1] - int(camera_y))

        def draw_dirt_segment(a, b):
            sa = to_screen(a)
            sb = to_screen(b)
            pygame.draw.line(screen, (126, 96, 62), sa, sb, 76)
            pygame.draw.line(screen, (101, 77, 49), sa, sb, 56)
            pygame.draw.line(screen, (153, 124, 84), sa, sb, 4)

        def draw_junction(node):
            sn = to_screen(node)
            pygame.draw.circle(screen, (126, 96, 62), sn, 39)
            pygame.draw.circle(screen, (101, 77, 49), sn, 28)

        for a, b in nav_graph["segments"]:
            draw_dirt_segment(a, b)

        for node_id in nav_graph["junction_ids"]:
            draw_junction(nav_graph["positions"][node_id])

        plaza_screen = to_screen(nav_graph["plaza"])
        plaza_radius_outer = 122 if current_page == "main" else 116 if current_page == "hard" else 112
        plaza_radius_inner = 96 if current_page == "main" else 90 if current_page == "hard" else 86
        pygame.draw.circle(screen, (140, 108, 70), plaza_screen, plaza_radius_outer)
        pygame.draw.circle(screen, (112, 84, 54), plaza_screen, plaza_radius_inner)
        pygame.draw.circle(screen, (168, 138, 96), plaza_screen, plaza_radius_outer, 4)

        nearest = None
        nearest_dist_sq = 10 ** 9
        p_cx, p_cy = hub_player.rect.center
        for d in doors:
            dx = d.center()[0] - p_cx
            dy = d.center()[1] - p_cy
            dist_sq = dx * dx + dy * dy
            if dist_sq < nearest_dist_sq:
                nearest_dist_sq = dist_sq
                nearest = d

        # Draw doors
        for d in doors:
            door_locked = should_lock_door(easy_mode, d, hard_mode_active, unlocked_levels_set, player_name)
            active = (d is nearest and nearest_dist_sq <= (120 * 120))
            d.draw(screen, (camera_x, camera_y), title_font, label_font, locked=door_locked, active=active)

        # Direction pointers from the player toward important targets.
        if current_page == "main":
            highest = _highest_unlocked_normal_level(player_name, active_world)
            highest_door = None
            hard_door = None
            optional_door = None
            for d in doors:
                if d.target_type == "level" and int(d.target_value) == highest:
                    highest_door = d
                if d.target_type == "page" and d.target_value == "hard":
                    hard_door = d
                if d.target_type == "page" and d.target_value == "optional":
                    optional_door = d

            player_sx = hub_player.rect.centerx - int(camera_x)
            player_sy = hub_player.rect.centery - int(camera_y)

            if highest_door is not None:
                hx = highest_door.rect.centerx - int(camera_x)
                hy = highest_door.rect.centery - int(camera_y)
                _draw_player_pointer(screen, (player_sx, player_sy), (hx, hy), (255, 230, 120), double=False)

            if hard_door is not None:
                hx = hard_door.rect.centerx - int(camera_x)
                hy = hard_door.rect.centery - int(camera_y)
                c = (255, 170, 170) if (hard_mode_active and world_hard_unlocked) else (160, 130, 130)
                _draw_player_pointer(screen, (player_sx, player_sy), (hx, hy), c, double=True)

            if optional_door is not None:
                ox = optional_door.rect.centerx - int(camera_x)
                oy = optional_door.rect.centery - int(camera_y)
                _draw_player_pointer(screen, (player_sx, player_sy), (ox, oy), (165, 210, 255), double=True)

        # Draw real player character with animation
        player_draw = hub_player.rect.move(-int(camera_x), -int(camera_y))
        screen.blit(hub_player.get_image(), player_draw.topleft)

        hud_card = pygame.Rect(12, 10, min(560, screen_width - 24), max(116, int(screen_height * 0.24)))
        pygame.draw.rect(screen, (14, 22, 36, 182), hud_card, border_radius=10)
        pygame.draw.rect(screen, (95, 140, 200), hud_card, 2, border_radius=10)

        hub_title = f"{world_name(active_world)} - {current_page.title()}"
        title_s = hud_font.render(fit_text(hud_font, hub_title, hud_card.width - 24), True, (255, 230, 160))
        screen.blit(title_s, (hud_card.x + 12, hud_card.y + 10))

        hud_lines = [
            ("Move: Left click nodes/doors   Enter door: E", (230, 230, 230)),
            (f"{'NG+: ON' if ng_plus_active else ('NG+: OFF' if ng_plus_unlocked else 'NG+: LOCKED')} (toggle: N)", (255, 190, 120) if ng_plus_active else (190, 190, 190)),
            ("Challenge code: C near level door | Replay race: R near level door", (195, 215, 240)),
            ("Daily challenge: D run, J leaderboard", (195, 215, 240)),
            (f"Meta upgrades (U to buy next): Mv {upg_cache.get('mobility', 0)} | HP {upg_cache.get('survivability', 0)} | Eco {upg_cache.get('economy', 0)}", (180, 230, 170)),
        ]
        if active_daily_info is not None:
            hud_lines.append((f"Daily: L{active_daily_info['level_id']} {active_daily_info['date_key']} (use E at that door)", (165, 220, 255)))
        if easy_mode:
            hud_lines.append(("Easy Mode: ON (training unlocks all doors)", (150, 240, 170)))

        hud_y = hud_card.y + 38
        for line, color in hud_lines:
            hud_y = draw_wrapped_text(screen, label_font, line, color, pygame.Rect(hud_card.x + 12, hud_y, hud_card.width - 24, 40), line_gap=2, max_lines=2) + 3

        if nearest is not None and nearest_dist_sq <= (120 * 120):
            near_text = f"Press E to enter: {nearest.label}"
            near_col = (245, 255, 220)
            if (not easy_mode) and nearest.target_type == "level" and is_level_locked(player_name, int(nearest.target_value)):
                near_col = (255, 205, 135)
            if (not easy_mode) and nearest.target_type == "page" and _is_page_door_locked(nearest, hard_mode_active and world_hard_unlocked):
                near_col = (255, 205, 135)
            if (not easy_mode) and nearest.target_type == "world" and not is_world_unlocked(unlocked_levels_set, int(nearest.target_value)):
                near_col = (255, 205, 135)
            draw_wrapped_text(screen, msg_font, near_text, near_col, pygame.Rect(40, screen_height - 94, screen_width - 80, 44), align="center", max_lines=2)
            if nearest.target_type == "level":
                lvl = int(nearest.target_value)
                chosen = selected_race_replays.get(lvl)
                if chosen:
                    race_line = f"Race ghost: {chosen.get('player_name', 'Unknown')} #{chosen.get('replay_id', '?')} ({float(chosen.get('completion_time', 0.0)):.2f}s)"
                    draw_wrapped_text(screen, label_font, race_line, (150, 225, 255), pygame.Rect(40, screen_height - 62, screen_width - 80, 24), align="center", max_lines=1)

        if message_timer > 0:
            message_timer = max(0.0, message_timer - dt)
            msg_s = msg_font.render(message, True, message_color)
            screen.blit(msg_s, (screen_width // 2 - msg_s.get_width() // 2, 16))

        if not hard_mode_active and hard_mode_unlocked:
            hard_hint = fit_text(label_font, "Hard mode unlocked but disabled in Settings.", max(160, screen_width - hud_card.right - 32))
            hard_s = label_font.render(hard_hint, True, (255, 210, 140))
            screen.blit(hard_s, (screen_width - hard_s.get_width() - 18, 14))

        if onboarding_timer > 0 and onboarding_idx < len(onboarding_steps):
            onboarding_timer = max(0.0, onboarding_timer - dt)
            card = pygame.Rect(20, screen_height - 126, min(screen_width - 40, 760), 86)
            card.centerx = screen_width // 2
            pygame.draw.rect(screen, (20, 34, 58), card, border_radius=10)
            pygame.draw.rect(screen, (120, 180, 240), card, 2, border_radius=10)
            draw_wrapped_text(screen, label_font, onboarding_steps[onboarding_idx], (225, 238, 252), pygame.Rect(card.x + 14, card.y + 12, card.width - 28, 36), align="center", max_lines=2)
            draw_wrapped_text(screen, label_font, "Press Right Arrow to next tip", (175, 205, 235), pygame.Rect(card.x + 14, card.y + 50, card.width - 28, 22), align="center", max_lines=1)
            if onboarding_timer == 0:
                onboarding_idx = min(len(onboarding_steps) - 1, onboarding_idx + 1)
                onboarding_timer = 6.0 if onboarding_idx < len(onboarding_steps) - 1 else 0.0

        back_button.draw()
        pygame.display.update()


if __name__ == "__main__":
    play_menu(None)
