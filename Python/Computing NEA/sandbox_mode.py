import pygame

from levels import level
from database import (
    create_connection,
    save_custom_level,
    list_my_custom_levels,
    list_public_custom_levels,
    get_custom_level,
    save_custom_level_run,
    get_custom_level_top_scores,
    get_custom_level_top_times,
    get_custom_level_player_best_score,
    get_custom_level_player_best_time,
    validate_custom_level_config,
    get_custom_level_metrics,
    get_creator_profile_metrics,
    like_custom_level,
    unlike_custom_level,
)


THEMES = {
    "world1": {
        "label": "World 1",
        "platform_image": "platform.png",
        "finish_image": "finish line.png",
        "melee_enemy_image": "melee enemy.png",
        "background_image": "background.png",
    },
    "world2": {
        "label": "World 2",
        "platform_image": "underworld platform.png",
        "finish_image": "underworld finish.png",
        "melee_enemy_image": "w2_melee_enemy.png",
        "background_image": "underworld background.png",
    },
    "world3": {
        "label": "World 3 Medieval",
        "platform_image": "medieval platform.png",
        "finish_image": "medieval finish.png",
        "melee_enemy_image": "medieval enemy.png",
        "background_image": "medieval background.png",
    },
}

PALETTE = [
    ("platform", "Platform", (120, 210, 130)),
    ("wall", "Wall", (170, 170, 190)),
    ("coin", "Coin", (255, 215, 90)),
    ("melee", "Melee Enemy", (255, 120, 120)),
    ("ranged", "Ranged Enemy", (120, 190, 255)),
    ("charger", "Charger Enemy", (255, 145, 80)),
    ("shield", "Shield Enemy", (145, 120, 255)),
    ("float", "Float Power", (140, 245, 255)),
    ("invincibility", "Invincibility", (255, 255, 120)),
    ("fire", "Fire Power", (255, 140, 60)),
    ("checkpoint", "Checkpoint", (90, 220, 120)),
    ("firewall", "Rotating Firewall", (255, 80, 80)),
    ("boss", "Boss", (210, 70, 70)),
    ("finish", "Finish Line", (255, 255, 255)),
    ("toggle_decay", "Toggle Decay Platform", (200, 140, 90)),
    ("toggle_bounce", "Toggle Bounce Platform", (120, 255, 200)),
    ("toggle_speed", "Toggle Speed Platform", (120, 160, 255)),
]

PREFABS = [
    {
        "name": "Stair Route",
        "platforms": [(0, 0, 130, 24), (140, -40, 130, 24), (280, -80, 130, 24)],
        "coins": [(65, -26), (205, -66), (345, -106)],
    },
    {
        "name": "Combat Pocket",
        "platforms": [(0, 0, 260, 28), (70, -74, 120, 22)],
        "melee": [(44, -46)],
        "ranged": [(188, -46)],
    },
    {
        "name": "Speed Tunnel",
        "platforms": [(0, 0, 380, 26)],
        "speed_idx": [0],
        "coins": [(30, -28), (90, -28), (150, -28), (210, -28), (270, -28), (330, -28)],
    },
]


def _button(surface, rect, text, font, fill=(50, 70, 95), border=(120, 175, 235), text_color=(255, 255, 255)):
    pygame.draw.rect(surface, fill, rect, border_radius=10)
    pygame.draw.rect(surface, border, rect, 2, border_radius=10)
    label = font.render(text, True, text_color)
    surface.blit(label, (rect.centerx - label.get_width() // 2, rect.centery - label.get_height() // 2))


def _default_builder_data(level_name, theme_key):
    t = THEMES.get(theme_key, THEMES["world1"])
    return {
        "name": level_name,
        "theme": theme_key,
        "world_width": 4200,
        "world_height": 1500,
        "platforms": [(0, 560, 280, 34), (360, 540, 160, 34)],
        "walls": [],
        "decaying_platforms": [],
        "bounce_platforms": [],
        "speed_boost_platforms": [],
        "rotating_firewalls": [],
        "coins": [],
        "melee_enemies": [],
        "ranged_enemies": [],
        "charger_enemies": [],
        "shield_enemies": [],
        "checkpoints": [],
        "finish_line": {"x": 1120, "y": 420, "w": 60, "h": 160},
        "power_ups": [],
        "boss": None,
        "auto_route_content": False,
        "platform_image": t["platform_image"],
        "finish_image": t["finish_image"],
        "melee_enemy_image": t["melee_enemy_image"],
        "background_image": t["background_image"],
    }


def _normalize_builder_data(data):
    theme_key = data.get("theme", "world1")
    if theme_key not in THEMES:
        theme_key = "world1"
    theme = THEMES[theme_key]

    cfg = {
        "name": (data.get("name") or "Sandbox Level")[:64],
        "theme": theme_key,
        "world_width": max(1600, int(data.get("world_width", 4200))),
        "world_height": 1500,
        "platforms": list(data.get("platforms", [])),
        "walls": list(data.get("walls", [])),
        "decaying_platforms": sorted(set(int(i) for i in data.get("decaying_platforms", []))),
        "bounce_platforms": sorted(set(int(i) for i in data.get("bounce_platforms", []))),
        "speed_boost_platforms": sorted(set(int(i) for i in data.get("speed_boost_platforms", []))),
        "rotating_firewalls": list(data.get("rotating_firewalls", [])),
        "coins": list(data.get("coins", [])),
        "melee_enemies": list(data.get("melee_enemies", [])),
        "ranged_enemies": list(data.get("ranged_enemies", [])),
        "charger_enemies": list(data.get("charger_enemies", [])),
        "shield_enemies": list(data.get("shield_enemies", [])),
        "checkpoints": list(data.get("checkpoints", [])),
        "finish_line": dict(data.get("finish_line") or {"x": 1120, "y": 420, "w": 60, "h": 160}),
        "power_ups": list(data.get("power_ups", [])),
        "auto_route_content": False,
        "platform_image": theme["platform_image"],
        "finish_image": theme["finish_image"],
        "melee_enemy_image": theme["melee_enemy_image"],
        "background_image": theme["background_image"],
    }

    boss_cfg = data.get("boss")
    if isinstance(boss_cfg, dict):
        cfg["boss"] = dict(boss_cfg)

    # Keep index lists valid for current platform count.
    p_count = len(cfg["platforms"])
    cfg["decaying_platforms"] = [i for i in cfg["decaying_platforms"] if 0 <= i < p_count]
    cfg["bounce_platforms"] = [i for i in cfg["bounce_platforms"] if 0 <= i < p_count]
    cfg["speed_boost_platforms"] = [i for i in cfg["speed_boost_platforms"] if 0 <= i < p_count]

    if not cfg["platforms"]:
        cfg["platforms"] = [(0, 560, 280, 34)]
    return cfg


def _text_input(screen, title, initial="", max_len=48):
    clock = pygame.time.Clock()
    text = initial
    font_title = pygame.font.SysFont("Arial", 42, bold=True)
    font_body = pygame.font.SysFont("Arial", 28)
    while True:
        dt = clock.tick(60)
        _ = dt
        screen.fill((14, 20, 30))
        t = font_title.render(title, True, (235, 240, 255))
        screen.blit(t, ((screen.get_width() - t.get_width()) // 2, 90))
        box = pygame.Rect(screen.get_width() // 2 - 330, 220, 660, 58)
        pygame.draw.rect(screen, (35, 50, 74), box, border_radius=8)
        pygame.draw.rect(screen, (110, 170, 240), box, 2, border_radius=8)
        msg = font_body.render(text + "|", True, (255, 255, 255))
        screen.blit(msg, (box.x + 14, box.y + 12))
        hint = font_body.render("Enter confirm, Esc cancel", True, (180, 200, 225))
        screen.blit(hint, ((screen.get_width() - hint.get_width()) // 2, 310))
        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                if event.key == pygame.K_RETURN:
                    return text.strip() or None
                if event.key == pygame.K_BACKSPACE:
                    text = text[:-1]
                elif event.unicode.isprintable() and len(text) < max_len:
                    text += event.unicode


def _number_input(screen, title, initial_value, min_value=1, max_value=100000):
    initial = str(int(initial_value)) if initial_value is not None else ""
    raw = _text_input(screen, title, initial=initial, max_len=8)
    if raw is None:
        return None
    try:
        val = int(raw)
    except ValueError:
        return None
    return max(min_value, min(max_value, val))


def _show_custom_leaderboard(screen, level_row):
    clock = pygame.time.Clock()
    lvl_id = level_row["custom_level_id"]
    title = f"{level_row['level_name']} Leaderboards"
    scores = get_custom_level_top_scores(lvl_id, 10)
    times = get_custom_level_top_times(lvl_id, 10)
    h1 = pygame.font.SysFont("Arial", 42, bold=True)
    h2 = pygame.font.SysFont("Arial", 28, bold=True)
    row_font = pygame.font.SysFont("Arial", 24)

    while True:
        _ = clock.tick(60)
        screen.fill((10, 18, 30))
        t = h1.render(title, True, (235, 235, 255))
        screen.blit(t, (screen.get_width() // 2 - t.get_width() // 2, 22))

        left = pygame.Rect(80, 110, (screen.get_width() // 2) - 110, screen.get_height() - 170)
        right = pygame.Rect(screen.get_width() // 2 + 30, 110, (screen.get_width() // 2) - 110, screen.get_height() - 170)
        for panel in (left, right):
            pygame.draw.rect(screen, (26, 36, 56), panel, border_radius=10)
            pygame.draw.rect(screen, (90, 130, 185), panel, 2, border_radius=10)

        left_t = h2.render("Top Scores", True, (255, 230, 145))
        right_t = h2.render("Fastest Times", True, (170, 225, 255))
        screen.blit(left_t, (left.x + 12, left.y + 10))
        screen.blit(right_t, (right.x + 12, right.y + 10))

        y = left.y + 56
        if not scores:
            screen.blit(row_font.render("No runs yet.", True, (210, 210, 220)), (left.x + 12, y))
        else:
            for i, row in enumerate(scores[:10], start=1):
                txt = row_font.render(f"{i:>2}. {row[0]}  {row[1]}", True, (245, 240, 200))
                screen.blit(txt, (left.x + 12, y))
                y += 30

        y = right.y + 56
        if not times:
            screen.blit(row_font.render("No runs yet.", True, (210, 210, 220)), (right.x + 12, y))
        else:
            for i, row in enumerate(times[:10], start=1):
                txt = row_font.render(f"{i:>2}. {row[0]}  {row[1]:.2f}s", True, (185, 235, 255))
                screen.blit(txt, (right.x + 12, y))
                y += 30

        hint = row_font.render("Esc or Backspace to return", True, (185, 195, 210))
        screen.blit(hint, (screen.get_width() // 2 - hint.get_width() // 2, screen.get_height() - 44))
        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                return True


def _run_custom_level(player_name, level_row):
    lvl_id = level_row["custom_level_id"]
    cfg = _normalize_builder_data(level_row["config"])
    hooks = {
        "save_run": save_custom_level_run,
        "get_player_best_score": get_custom_level_player_best_score,
        "get_player_best_time": get_custom_level_player_best_time,
        "get_top_scores": get_custom_level_top_scores,
        "get_top_times": get_custom_level_top_times,
    }
    return level(-1, player_name, level_config_override=cfg, custom_level_id=lvl_id, leaderboard_hooks=hooks)


def _nearest_platform_index(data, x, y):
    best_idx = None
    best_d = 10 ** 9
    for idx, p in enumerate(data["platforms"]):
        px, py, pw, ph = p
        cx = px + pw // 2
        cy = py + ph // 2
        d = (cx - x) * (cx - x) + (cy - y) * (cy - y)
        if d < best_d:
            best_d = d
            best_idx = idx
    return best_idx


def _toggle_index(lst, idx):
    if idx is None:
        return
    if idx in lst:
        lst.remove(idx)
    else:
        lst.append(idx)


def _remove_near_point(data, mode, x, y):
    if mode == "platform":
        idx = _nearest_platform_index(data, x, y)
        if idx is not None and len(data["platforms"]) > 1:
            data["platforms"].pop(idx)
            for key in ("decaying_platforms", "bounce_platforms", "speed_boost_platforms"):
                fixed = []
                for v in data[key]:
                    if v == idx:
                        continue
                    fixed.append(v - 1 if v > idx else v)
                data[key] = fixed
    elif mode == "wall" and data["walls"]:
        data["walls"].pop()
    elif mode == "coin" and data["coins"]:
        data["coins"].pop()
    elif mode == "melee" and data["melee_enemies"]:
        data["melee_enemies"].pop()
    elif mode == "ranged" and data["ranged_enemies"]:
        data["ranged_enemies"].pop()
    elif mode == "charger" and data["charger_enemies"]:
        data["charger_enemies"].pop()
    elif mode == "shield" and data["shield_enemies"]:
        data["shield_enemies"].pop()
    elif mode in ("float", "invincibility", "fire"):
        if data["power_ups"]:
            for i in range(len(data["power_ups"]) - 1, -1, -1):
                if data["power_ups"][i].get("type") == mode:
                    data["power_ups"].pop(i)
                    break
    elif mode == "checkpoint" and data["checkpoints"]:
        data["checkpoints"].pop()
    elif mode == "firewall" and data["rotating_firewalls"]:
        data["rotating_firewalls"].pop()
    elif mode == "boss":
        data["boss"] = None


def _editor(player_name, initial_data, custom_level_id=None, is_finished=False, is_public=False):
    screen = pygame.display.get_surface()
    if screen is None:
        info = pygame.display.Info()
        screen = pygame.display.set_mode((info.current_w, info.current_h))

    data = _normalize_builder_data(initial_data)
    cam_x = 0
    cam_y = 0
    grid = 20
    mode_idx = 0
    platform_w = 140
    platform_h = 34
    wall_h = 120
    status = "Editor ready"
    selected_prefab = 0
    drag_panning = False
    drag_last = (0, 0)

    title_font = pygame.font.SysFont("Arial", 28, bold=True)
    small_font = pygame.font.SysFont("Arial", 20)
    tiny_font = pygame.font.SysFont("Arial", 17)
    clock = pygame.time.Clock()

    while True:
        dt = clock.tick(60) / 1000.0
        keys = pygame.key.get_pressed()
        pan_speed = int((1200 if (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) else 720) * dt)
        if keys[pygame.K_LEFT]:
            cam_x = max(0, cam_x - pan_speed)
        if keys[pygame.K_RIGHT]:
            cam_x = min(max(0, data["world_width"] - screen.get_width()), cam_x + pan_speed)
        if keys[pygame.K_UP]:
            cam_y = max(-900, cam_y - pan_speed)
        if keys[pygame.K_DOWN]:
            cam_y = min(900, cam_y + pan_speed)
        if keys[pygame.K_a]:
            cam_x = max(0, cam_x - pan_speed)
        if keys[pygame.K_d]:
            cam_x = min(max(0, data["world_width"] - screen.get_width()), cam_x + pan_speed)
        if keys[pygame.K_w]:
            cam_y = max(-900, cam_y - pan_speed)
        if keys[pygame.K_s]:
            cam_y = min(900, cam_y + pan_speed)

        screen.fill((13, 19, 30))
        grid_color = (25, 33, 48)
        for x in range(-cam_x % grid, screen.get_width(), grid):
            pygame.draw.line(screen, grid_color, (x, 0), (x, screen.get_height()))
        for y in range(-cam_y % grid, screen.get_height(), grid):
            pygame.draw.line(screen, grid_color, (0, y), (screen.get_width(), y))

        preview_cfg = _normalize_builder_data(data)
        publish_valid, publish_issues = validate_custom_level_config(preview_cfg)

        # Draw world bounds
        world_rect = pygame.Rect(-cam_x, -cam_y, data["world_width"], data["world_height"])
        pygame.draw.rect(screen, (40, 55, 80), world_rect, 2)

        # Draw objects
        for idx, (x, y, w, h) in enumerate(data["platforms"]):
            r = pygame.Rect(int(x - cam_x), int(y - cam_y), int(w), int(h))
            color = (110, 180, 110)
            if idx in data["decaying_platforms"]:
                color = (180, 120, 80)
            if idx in data["bounce_platforms"]:
                color = (80, 210, 190)
            if idx in data["speed_boost_platforms"]:
                color = (105, 140, 235)
            pygame.draw.rect(screen, color, r, border_radius=4)
            pygame.draw.rect(screen, (10, 10, 10), r, 2, border_radius=4)

        for x, y, w, h in data["walls"]:
            pygame.draw.rect(screen, (155, 155, 185), (int(x - cam_x), int(y - cam_y), int(w), int(h)))
        for x, y in data["coins"]:
            pygame.draw.circle(screen, (245, 205, 90), (int(x - cam_x), int(y - cam_y)), 8)
        for e in data["melee_enemies"]:
            pygame.draw.rect(screen, (230, 110, 110), (int(e["x"] - cam_x), int(e["y"] - cam_y), 24, 24))
        for e in data["ranged_enemies"]:
            pygame.draw.rect(screen, (120, 185, 245), (int(e["x"] - cam_x), int(e["y"] - cam_y), 24, 24))
        for e in data["charger_enemies"]:
            pygame.draw.rect(screen, (245, 155, 95), (int(e["x"] - cam_x), int(e["y"] - cam_y), 24, 24))
        for e in data["shield_enemies"]:
            pygame.draw.rect(screen, (155, 120, 245), (int(e["x"] - cam_x), int(e["y"] - cam_y), 24, 24))

        for p in data["power_ups"]:
            p_col = (140, 245, 255) if p["type"] == "float" else (255, 255, 120) if p["type"] == "invincibility" else (255, 140, 60)
            pygame.draw.circle(screen, p_col, (int(p["x"] - cam_x), int(p["y"] - cam_y)), 10)

        for cp in data["checkpoints"]:
            pygame.draw.rect(screen, (80, 220, 120), (int(cp["x"] - cam_x), int(cp["y"] - cam_y), 18, 42), 2)

        for fw in data["rotating_firewalls"]:
            pygame.draw.circle(screen, (245, 90, 90), (int(fw["cx"] - cam_x), int(fw["cy"] - cam_y)), 14, 2)

        if isinstance(data.get("boss"), dict):
            b = data["boss"]
            pygame.draw.rect(screen, (210, 70, 70), (int(b["x"] - cam_x), int(b["y"] - cam_y), int(b.get("w", 100)), int(b.get("h", 140))), 2)

        finish = data["finish_line"]
        pygame.draw.rect(screen, (255, 255, 255), (int(finish["x"] - cam_x), int(finish["y"] - cam_y), int(finish["w"]), int(finish["h"]),), 2)

        mode_key, mode_label, mode_color = PALETTE[mode_idx]
        panel = pygame.Rect(10, 10, screen.get_width() - 20, 142)
        pygame.draw.rect(screen, (6, 12, 24, 220), panel, border_radius=10)
        pygame.draw.rect(screen, (72, 120, 190), panel, 2, border_radius=10)

        hdr = title_font.render(f"Sandbox Builder | {data['name']} | Theme: {THEMES[data['theme']]['label']}", True, (230, 240, 255))
        screen.blit(hdr, (20, 20))
        mode_text = small_font.render(f"Tool [{mode_idx + 1}/{len(PALETTE)}]: {mode_label}", True, mode_color)
        screen.blit(mode_text, (20, 56))
        meta = small_font.render(f"Finished: {'Yes' if is_finished else 'No'}  Public: {'Yes' if is_public else 'No'}  WorldWidth: {data['world_width']}", True, (220, 220, 220))
        screen.blit(meta, (20, 82))
        hint = tiny_font.render("L click place, R click remove, wheel / [ ] / 1-9 tools, B cycle prefab, Y place prefab, MMB drag or arrows/WASD pan, F finished, V public, T width, G save, P play, Esc back", True, (180, 198, 220))
        screen.blit(hint, (20, 108))
        pf = tiny_font.render(f"Prefab: {PREFABS[selected_prefab]['name']}", True, (170, 220, 255))
        screen.blit(pf, (20, 126))

        # Clickable tool strip for quicker switching.
        strip_x = 12
        strip_y = panel.bottom + 10
        strip_w = 260
        strip_h = min(screen.get_height() - strip_y - 52, 32 * len(PALETTE) + 8)
        strip_rect = pygame.Rect(strip_x, strip_y, strip_w, strip_h)
        pygame.draw.rect(screen, (10, 20, 34), strip_rect, border_radius=8)
        pygame.draw.rect(screen, (65, 95, 140), strip_rect, 2, border_radius=8)
        tool_row_rects = []
        row_h = 28
        max_rows = max(1, (strip_h - 8) // row_h)
        scroll_start = max(0, min(mode_idx - max_rows // 2, len(PALETTE) - max_rows))
        visible = PALETTE[scroll_start:scroll_start + max_rows]
        for i, (_, lbl, col) in enumerate(visible):
            idx = scroll_start + i
            rr = pygame.Rect(strip_x + 6, strip_y + 4 + i * row_h, strip_w - 12, row_h - 2)
            active = idx == mode_idx
            fill = (40, 62, 95) if active else (20, 32, 52)
            pygame.draw.rect(screen, fill, rr, border_radius=5)
            pygame.draw.rect(screen, col if active else (70, 90, 120), rr, 1, border_radius=5)
            label = tiny_font.render(f"{idx + 1:02d} {lbl}", True, (245, 245, 245))
            screen.blit(label, (rr.x + 6, rr.y + 5))
            tool_row_rects.append((idx, rr))

        checklist_x = strip_rect.right + 14
        checklist_w = min(460, screen.get_width() - checklist_x - 12)
        checklist_h = 164
        checklist_rect = pygame.Rect(checklist_x, strip_y, checklist_w, checklist_h)
        pygame.draw.rect(screen, (10, 20, 34), checklist_rect, border_radius=8)
        pygame.draw.rect(screen, (65, 95, 140), checklist_rect, 2, border_radius=8)

        checklist_title = small_font.render("Publish Checklist", True, (225, 235, 250))
        screen.blit(checklist_title, (checklist_rect.x + 10, checklist_rect.y + 8))

        finish = preview_cfg.get("finish_line") or {}
        start_near = any(int(p[0]) <= 280 for p in preview_cfg.get("platforms", []))
        finish_near = any(abs(int(p[0]) - int(finish.get("x", -9999))) <= 420 for p in preview_cfg.get("platforms", [])) if finish else False
        checks = [
            ("Marked finished", bool(is_finished)),
            ("Marked public", bool(is_public)),
            ("Has start platform", bool(start_near)),
            ("Has finish route", bool(finish_near)),
            ("Validation clean", bool(publish_valid)),
        ]
        line_y = checklist_rect.y + 40
        for label, ok in checks:
            icon = "PASS" if ok else "FAIL"
            color = (130, 230, 150) if ok else (245, 140, 140)
            row = tiny_font.render(f"{icon}: {label}", True, color)
            screen.blit(row, (checklist_rect.x + 12, line_y))
            line_y += 22

        issue_head = tiny_font.render("Validation notes:", True, (200, 214, 236))
        screen.blit(issue_head, (checklist_rect.x + 12, line_y + 2))
        issue_y = line_y + 22
        issue_rows = publish_issues[:2] if publish_issues else ["No blocking issues detected."]
        for issue in issue_rows:
            issue_surf = tiny_font.render(f"- {issue}", True, (240, 220, 175) if publish_issues else (165, 220, 170))
            screen.blit(issue_surf, (checklist_rect.x + 12, issue_y))
            issue_y += 20

        status_text = tiny_font.render(status, True, (220, 210, 170))
        screen.blit(status_text, (20, screen.get_height() - 30))

        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return True
                if event.key == pygame.K_LEFTBRACKET:
                    mode_idx = (mode_idx - 1) % len(PALETTE)
                if event.key == pygame.K_RIGHTBRACKET:
                    mode_idx = (mode_idx + 1) % len(PALETTE)
                if pygame.K_1 <= event.key <= pygame.K_9:
                    candidate = event.key - pygame.K_1
                    if candidate < len(PALETTE):
                        mode_idx = candidate
                if event.key == pygame.K_0 and len(PALETTE) >= 10:
                    mode_idx = 9
                if event.key == pygame.K_MINUS:
                    platform_w = max(40, platform_w - 20)
                if event.key == pygame.K_EQUALS:
                    platform_w = min(400, platform_w + 20)
                if event.key == pygame.K_t:
                    picked = _number_input(
                        screen,
                        "Set world width (1800-12000)",
                        data["world_width"],
                        min_value=1800,
                        max_value=12000,
                    )
                    if picked is not None:
                        data["world_width"] = picked
                        cam_x = min(cam_x, max(0, data["world_width"] - screen.get_width()))
                        status = f"World width set to {data['world_width']}"
                if event.key == pygame.K_f:
                    is_finished = not is_finished
                    status = f"Finished set to {'Yes' if is_finished else 'No'}"
                if event.key == pygame.K_v:
                    is_public = not is_public
                    status = f"Public set to {'Yes' if is_public else 'No'}"
                if event.key == pygame.K_n:
                    new_name = _text_input(screen, "Sandbox level name", data["name"], 64)
                    if new_name:
                        data["name"] = new_name
                        status = "Name updated"
                if event.key == pygame.K_b:
                    selected_prefab = (selected_prefab + 1) % len(PREFABS)
                    status = f"Prefab selected: {PREFABS[selected_prefab]['name']}"
                if event.key == pygame.K_y:
                    pf = PREFABS[selected_prefab]
                    anchor_x = int((cam_x + screen.get_width() * 0.45) // grid * grid)
                    anchor_y = int((cam_y + screen.get_height() * 0.55) // grid * grid)
                    base_platform_idx = len(data["platforms"])
                    for px, py, pw, ph in pf.get("platforms", []):
                        data["platforms"].append((anchor_x + px, anchor_y + py, pw, ph))
                    for cx, cy in pf.get("coins", []):
                        data["coins"].append((anchor_x + cx, anchor_y + cy))
                    for ex, ey in pf.get("melee", []):
                        data["melee_enemies"].append({"x": anchor_x + ex, "y": anchor_y + ey})
                    for ex, ey in pf.get("ranged", []):
                        data["ranged_enemies"].append({"x": anchor_x + ex, "y": anchor_y + ey})
                    for rel_idx in pf.get("speed_idx", []):
                        data["speed_boost_platforms"].append(base_platform_idx + int(rel_idx))
                    status = f"Placed prefab: {pf['name']}"
                if event.key == pygame.K_g:
                    cfg = _normalize_builder_data(data)
                    valid_cfg, issues = publish_valid, publish_issues
                    if is_finished and is_public and not valid_cfg:
                        status = "Publish blocked: " + (issues[0] if issues else "Validation failed")
                        continue
                    conn = create_connection()
                    if conn is None:
                        status = "Could not connect to database"
                    else:
                        new_id = save_custom_level(
                            conn,
                            player_name,
                            cfg["name"],
                            cfg.get("theme", "world1"),
                            cfg,
                            is_finished=is_finished,
                            is_public=is_public,
                            custom_level_id=custom_level_id,
                        )
                        conn.close()
                        if new_id is not None:
                            custom_level_id = new_id
                            status = f"Saved custom level #{custom_level_id}"
                        else:
                            status = "Save failed"
                if event.key == pygame.K_p:
                    if not is_finished:
                        status = "Mark level as finished before playing"
                    elif custom_level_id is None:
                        status = "Save before playing"
                    else:
                        row = get_custom_level(custom_level_id, requester_name=player_name)
                        if row is None:
                            status = "Could not load saved level"
                        else:
                            keep_running = _run_custom_level(player_name, row)
                            if not keep_running:
                                return False
                            status = "Returned from playtest"

            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                wx = ((mx + cam_x) // grid) * grid
                wy = ((my + cam_y) // grid) * grid
                mode = PALETTE[mode_idx][0]

                if event.button == 2:
                    drag_panning = True
                    drag_last = event.pos
                    continue

                if event.button == 4:
                    mode_idx = (mode_idx - 1) % len(PALETTE)
                    continue
                if event.button == 5:
                    mode_idx = (mode_idx + 1) % len(PALETTE)
                    continue

                if strip_rect.collidepoint(event.pos):
                    for idx, rr in tool_row_rects:
                        if rr.collidepoint(event.pos):
                            mode_idx = idx
                            break
                    continue

                if event.button == 1:
                    if mode == "platform":
                        data["platforms"].append((int(wx), int(wy), platform_w, platform_h))
                    elif mode == "wall":
                        data["walls"].append((int(wx), int(wy), 24, wall_h))
                    elif mode == "coin":
                        data["coins"].append((int(wx + 10), int(wy + 10)))
                    elif mode == "melee":
                        data["melee_enemies"].append({"x": int(wx), "y": int(wy)})
                    elif mode == "ranged":
                        data["ranged_enemies"].append({"x": int(wx), "y": int(wy)})
                    elif mode == "charger":
                        data["charger_enemies"].append({"x": int(wx), "y": int(wy)})
                    elif mode == "shield":
                        data["shield_enemies"].append({"x": int(wx), "y": int(wy)})
                    elif mode in ("float", "invincibility", "fire"):
                        data["power_ups"].append({"type": mode, "x": int(wx), "y": int(wy)})
                    elif mode == "checkpoint":
                        data["checkpoints"].append({"x": int(wx), "y": int(wy)})
                    elif mode == "firewall":
                        data["rotating_firewalls"].append({
                            "cx": int(wx),
                            "cy": int(wy),
                            "blade_width": 86,
                            "blade_height": 22,
                            "rotation_speed": 220,
                        })
                    elif mode == "boss":
                        data["boss"] = {
                            "x": int(wx),
                            "y": int(wy),
                            "w": 110,
                            "h": 140,
                            "health": 950,
                            "speed": 100,
                        }
                    elif mode == "finish":
                        data["finish_line"] = {"x": int(wx), "y": int(wy), "w": 60, "h": 160}
                    elif mode == "toggle_decay":
                        _toggle_index(data["decaying_platforms"], _nearest_platform_index(data, wx, wy))
                    elif mode == "toggle_bounce":
                        _toggle_index(data["bounce_platforms"], _nearest_platform_index(data, wx, wy))
                    elif mode == "toggle_speed":
                        _toggle_index(data["speed_boost_platforms"], _nearest_platform_index(data, wx, wy))

                if event.button == 3:
                    _remove_near_point(data, mode, wx, wy)

            if event.type == pygame.MOUSEBUTTONUP and event.button == 2:
                drag_panning = False

            if event.type == pygame.MOUSEMOTION and drag_panning:
                dx = event.pos[0] - drag_last[0]
                dy = event.pos[1] - drag_last[1]
                drag_last = event.pos
                cam_x = max(0, min(max(0, data["world_width"] - screen.get_width()), cam_x - dx))
                cam_y = max(-900, min(900, cam_y - dy))


def _choose_theme(screen):
    clock = pygame.time.Clock()
    title_font = pygame.font.SysFont("Arial", 44, bold=True)
    body_font = pygame.font.SysFont("Arial", 30)
    button_width = 280
    gap = 28
    total_width = button_width * 3 + gap * 2
    start_x = (screen.get_width() - total_width) // 2
    world1_rect = pygame.Rect(start_x, 220, button_width, 120)
    world2_rect = pygame.Rect(start_x + button_width + gap, 220, button_width, 120)
    world3_rect = pygame.Rect(start_x + (button_width + gap) * 2, 220, button_width, 120)
    while True:
        _ = clock.tick(60)
        screen.fill((14, 20, 30))
        title = title_font.render("Choose Theme", True, (235, 240, 255))
        screen.blit(title, ((screen.get_width() - title.get_width()) // 2, 96))
        _button(screen, world1_rect, "World 1 Theme", body_font, fill=(36, 64, 46), border=(105, 205, 125))
        _button(screen, world2_rect, "World 2 Theme", body_font, fill=(66, 38, 30), border=(230, 150, 120))
        _button(screen, world3_rect, "World 3 Medieval", body_font, fill=(58, 58, 70), border=(214, 194, 142))
        hint = body_font.render("Esc to cancel", True, (190, 205, 225))
        screen.blit(hint, (screen.get_width() // 2 - hint.get_width() // 2, 380))
        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return None
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if world1_rect.collidepoint(event.pos):
                    return "world1"
                if world2_rect.collidepoint(event.pos):
                    return "world2"
                if world3_rect.collidepoint(event.pos):
                    return "world3"


def _my_or_public_browser(player_name, public=False):
    screen = pygame.display.get_surface()
    if screen is None:
        info = pygame.display.Info()
        screen = pygame.display.set_mode((info.current_w, info.current_h))

    title_font = pygame.font.SysFont("Arial", 40, bold=True)
    row_font = pygame.font.SysFont("Arial", 24)
    hint_font = pygame.font.SysFont("Arial", 20)
    clock = pygame.time.Clock()
    selected = 0

    while True:
        rows = list_public_custom_levels(150) if public else list_my_custom_levels(player_name)
        if selected >= len(rows):
            selected = max(0, len(rows) - 1)

        _ = clock.tick(60)
        screen.fill((11, 18, 30))
        head = "Public Sandbox Levels" if public else "My Sandbox Levels"
        title = title_font.render(head, True, (235, 242, 255))
        screen.blit(title, ((screen.get_width() - title.get_width()) // 2, 16))

        if not rows:
            empty = row_font.render("No levels found.", True, (205, 215, 230))
            screen.blit(empty, ((screen.get_width() - empty.get_width()) // 2, 140))
        else:
            y = 92
            for idx, row in enumerate(rows[:14]):
                rect = pygame.Rect(40, y, screen.get_width() - 80, 42)
                active = idx == selected
                fill = (28, 44, 70) if active else (20, 30, 48)
                border = (130, 200, 255) if active else (70, 105, 155)
                pygame.draw.rect(screen, fill, rect, border_radius=8)
                pygame.draw.rect(screen, border, rect, 2, border_radius=8)
                tag = "PUBLIC" if row["is_public"] else "PRIVATE"
                fin = "FINISHED" if row["is_finished"] else "DRAFT"
                metrics = get_custom_level_metrics(row["custom_level_id"])
                txt = (
                    f"#{row['custom_level_id']}  {row['level_name']}  |  {THEMES.get(row['theme'], THEMES['world1'])['label']}"
                    f"  |  {fin}  |  {tag}  |  P{metrics['plays']} C{metrics['clears']} L{metrics['likes']}  |  by {row['owner_name']}"
                )
                label = row_font.render(txt, True, (235, 240, 250))
                screen.blit(label, (rect.x + 10, rect.y + 9))
                y += 50

        if public:
            hint_txt = "Arrows move, Enter play, L leaderboard, K like, U unlike, Esc back"
        else:
            hint_txt = "Arrows move, Enter edit, P play, L leaderboard, Esc back"
        hint = hint_font.render(hint_txt, True, (185, 205, 230))
        screen.blit(hint, (screen.get_width() // 2 - hint.get_width() // 2, screen.get_height() - 34))

        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return True
                if event.key == pygame.K_UP and selected > 0:
                    selected -= 1
                if event.key == pygame.K_DOWN and selected < len(rows) - 1:
                    selected += 1
                if event.key == pygame.K_l and rows:
                    keep_running = _show_custom_leaderboard(screen, rows[selected])
                    if not keep_running:
                        return False
                if public and event.key == pygame.K_k and rows:
                    like_custom_level(player_name, rows[selected]["custom_level_id"])
                if public and event.key == pygame.K_u and rows:
                    unlike_custom_level(player_name, rows[selected]["custom_level_id"])
                if event.key == pygame.K_RETURN and rows:
                    row = rows[selected]
                    if public:
                        keep_running = _run_custom_level(player_name, row)
                        if not keep_running:
                            return False
                    else:
                        _editor(
                            player_name,
                            row["config"],
                            custom_level_id=row["custom_level_id"],
                            is_finished=row["is_finished"],
                            is_public=row["is_public"],
                        )
                if (not public) and event.key == pygame.K_p and rows:
                    row = rows[selected]
                    if not row["is_finished"]:
                        continue
                    keep_running = _run_custom_level(player_name, row)
                    if not keep_running:
                        return False


def sandbox_mode(player_name):
    screen = pygame.display.get_surface()
    if screen is None:
        info = pygame.display.Info()
        screen = pygame.display.set_mode((info.current_w, info.current_h))

    conn = create_connection()
    if conn is not None:
        conn.close()

    title_font = pygame.font.SysFont("Arial", 56, bold=True)
    button_font = pygame.font.SysFont("Arial", 30)
    hint_font = pygame.font.SysFont("Arial", 22)
    clock = pygame.time.Clock()

    btn_w = 420
    btn_h = 78
    cx = screen.get_width() // 2 - btn_w // 2
    create_btn = pygame.Rect(cx, 180, btn_w, btn_h)
    mine_btn = pygame.Rect(cx, 280, btn_w, btn_h)
    public_btn = pygame.Rect(cx, 380, btn_w, btn_h)
    back_btn = pygame.Rect(cx, 480, btn_w, btn_h)

    while True:
        _ = clock.tick(60)
        screen.fill((10, 17, 28))
        title = title_font.render("Sandbox Mode", True, (235, 242, 255))
        screen.blit(title, (screen.get_width() // 2 - title.get_width() // 2, 70))

        creator = get_creator_profile_metrics(player_name)
        creator_text = hint_font.render(
            f"Creator Stats: Levels {creator['levels']}  Plays {creator['plays']}  Clears {creator['clears']}  Likes {creator['likes']}",
            True,
            (210, 225, 245),
        )
        screen.blit(creator_text, (screen.get_width() // 2 - creator_text.get_width() // 2, 136))

        _button(screen, create_btn, "Create New Sandbox Level", button_font, fill=(34, 72, 54), border=(120, 220, 165))
        _button(screen, mine_btn, "My Sandbox Levels", button_font, fill=(34, 58, 84), border=(125, 190, 245))
        _button(screen, public_btn, "Browse Public Levels", button_font, fill=(72, 52, 40), border=(232, 170, 118))
        _button(screen, back_btn, "Back", button_font, fill=(52, 52, 60), border=(180, 180, 190))

        hint = hint_font.render("Create, save as draft/finished, set private/public, then play with custom leaderboards", True, (185, 205, 230))
        screen.blit(hint, (screen.get_width() // 2 - hint.get_width() // 2, screen.get_height() - 46))
        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return True
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if create_btn.collidepoint(event.pos):
                    theme = _choose_theme(screen)
                    if not theme:
                        continue
                    level_name = _text_input(screen, "Name your sandbox level", "Sandbox Level", 64)
                    if not level_name:
                        continue
                    initial = _default_builder_data(level_name, theme)
                    initial_width = _number_input(
                        screen,
                        "Choose world width (1800-12000)",
                        initial.get("world_width", 4200),
                        min_value=1800,
                        max_value=12000,
                    )
                    if initial_width is not None:
                        initial["world_width"] = initial_width
                    keep_running = _editor(player_name, initial, custom_level_id=None, is_finished=False, is_public=False)
                    if not keep_running:
                        return False
                elif mine_btn.collidepoint(event.pos):
                    keep_running = _my_or_public_browser(player_name, public=False)
                    if not keep_running:
                        return False
                elif public_btn.collidepoint(event.pos):
                    keep_running = _my_or_public_browser(player_name, public=True)
                    if not keep_running:
                        return False
                elif back_btn.collidepoint(event.pos):
                    return True
