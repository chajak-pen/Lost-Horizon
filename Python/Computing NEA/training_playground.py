import pygame

from database import get_training_trial_progress, save_training_trial_result
from levels import level


def _base_trial_config():
    return {
        "world_width": 3200,
        "world_height": 1500,
        "boss": None,
        "auto_route_content": False,
        "platform_image": "platform.png",
        "finish_image": "finish line.png",
        "melee_enemy_image": "melee enemy.png",
        "background_image": "background.png",
    }


TRIALS = {
    "dash_gap": {
        "title": "Dash Gap Sprint",
        "desc": "Chain dashes and slides to clear long gaps quickly.",
        "ghost_target": 28.0,
        "medal_times": {"gold": 26.0, "silver": 32.0, "bronze": 40.0},
        "medal_deaths": {"gold": 0, "silver": 1, "bronze": 2},
        "config": {
            "name": "Training Trial: Dash Gap Sprint",
            "platforms": [
                (0, 560, 360, 34),
                (470, 525, 180, 26),
                (760, 500, 160, 24),
                (1040, 460, 170, 24),
                (1330, 430, 160, 24),
                (1620, 460, 180, 24),
                (1950, 500, 210, 28),
                (2330, 470, 210, 28),
                (2710, 500, 230, 32),
            ],
            "walls": [(670, 380, 18, 190)],
            "coins": [(520, 490), (1110, 420), (1690, 425), (2390, 430)],
            "melee_enemies": [{"x": 2010, "y": 455}],
            "ranged_enemies": [{"x": 2480, "y": 360}],
            "charger_enemies": [],
            "shield_enemies": [],
            "checkpoints": [{"x": 1240, "y": 388}, {"x": 2240, "y": 438}],
            "finish_line": {"x": 3010, "y": 352, "w": 60, "h": 180},
            "power_ups": [{"type": "float", "x": 880, "y": 460}],
        },
    },
    "wall_climb": {
        "title": "Wall Climb Relay",
        "desc": "Use wall jumps to climb vertical shafts and preserve momentum.",
        "ghost_target": 35.0,
        "medal_times": {"gold": 32.0, "silver": 39.0, "bronze": 48.0},
        "medal_deaths": {"gold": 0, "silver": 2, "bronze": 3},
        "config": {
            "name": "Training Trial: Wall Climb Relay",
            "platforms": [
                (0, 560, 380, 34),
                (420, 520, 190, 28),
                (700, 480, 190, 26),
                (980, 430, 180, 24),
                (1240, 380, 170, 24),
                (1540, 420, 190, 24),
                (1820, 360, 180, 22),
                (2130, 300, 170, 22),
                (2440, 360, 190, 24),
                (2730, 430, 220, 28),
            ],
            "walls": [(620, 320, 18, 260), (1160, 270, 18, 270), (2060, 220, 18, 250)],
            "coins": [(760, 450), (1010, 390), (1600, 380), (2190, 270), (2810, 390)],
            "melee_enemies": [],
            "ranged_enemies": [{"x": 2490, "y": 260}],
            "charger_enemies": [{"x": 2860, "y": 385}],
            "shield_enemies": [],
            "checkpoints": [{"x": 1420, "y": 330}, {"x": 2360, "y": 312}],
            "finish_line": {"x": 3040, "y": 320, "w": 60, "h": 200},
            "power_ups": [{"type": "float", "x": 1340, "y": 340}],
        },
    },
    "combat_flow": {
        "title": "Combat Flow Circuit",
        "desc": "Blend movement tech with enemy clears to keep pace under pressure.",
        "ghost_target": 42.0,
        "medal_times": {"gold": 38.0, "silver": 46.0, "bronze": 56.0},
        "medal_deaths": {"gold": 1, "silver": 2, "bronze": 4},
        "config": {
            "name": "Training Trial: Combat Flow Circuit",
            "platforms": [
                (0, 560, 420, 34),
                (500, 520, 220, 34),
                (820, 470, 160, 26),
                (1040, 420, 150, 24),
                (1290, 360, 180, 24),
                (1550, 410, 220, 26),
                (1860, 500, 260, 30),
                (2250, 460, 200, 30),
                (2520, 390, 140, 24),
                (2790, 540, 240, 34),
            ],
            "walls": [(740, 380, 18, 170), (1740, 300, 18, 260)],
            "coins": [(600, 480), (1110, 380), (1380, 320), (2330, 430), (2860, 510)],
            "melee_enemies": [{"x": 1910, "y": 450}],
            "ranged_enemies": [{"x": 2600, "y": 340}],
            "charger_enemies": [{"x": 2100, "y": 450}],
            "shield_enemies": [],
            "checkpoints": [{"x": 1240, "y": 318}, {"x": 2430, "y": 420}],
            "finish_line": {"x": 3060, "y": 388, "w": 60, "h": 160},
            "power_ups": [
                {"type": "float", "x": 930, "y": 430},
                {"type": "invincibility", "x": 1960, "y": 470},
                {"type": "fire", "x": 2720, "y": 350},
            ],
        },
    },
}


def _compute_trial_medal(trial, completion_time, death_count):
    times = trial["medal_times"]
    caps = trial["medal_deaths"]
    if completion_time <= float(times["gold"]) and int(death_count) <= int(caps["gold"]):
        return "gold"
    if completion_time <= float(times["silver"]) and int(death_count) <= int(caps["silver"]):
        return "silver"
    if completion_time <= float(times["bronze"]) and int(death_count) <= int(caps["bronze"]):
        return "bronze"
    return "none"


def launch_training_playground(player_name):
    screen = pygame.display.get_surface()
    if screen is None:
        info = pygame.display.Info()
        screen = pygame.display.set_mode((info.current_w, info.current_h))

    sw, sh = screen.get_size()
    title_font = pygame.font.SysFont("Arial", max(24, int(44 * sh / 600)), bold=True)
    head_font = pygame.font.SysFont("Arial", max(16, int(24 * sh / 600)), bold=True)
    body_font = pygame.font.SysFont("Arial", max(12, int(20 * sh / 600)))
    hint_font = pygame.font.SysFont("Arial", max(11, int(17 * sh / 600)))
    clock = pygame.time.Clock()

    trial_keys = list(TRIALS.keys())
    selected_idx = 0
    status = "Choose a trial and press Enter to launch."

    while True:
        _ = clock.tick(60)
        progress = get_training_trial_progress(player_name)

        screen.fill((10, 16, 30))
        title = title_font.render("Training Trials", True, (235, 240, 255))
        screen.blit(title, (sw // 2 - title.get_width() // 2, 18))

        cols = 1 if sw < 1120 else 3
        gap = 12
        card_w = (sw - 48 - gap * (cols - 1)) // cols
        card_h = max(170, int(sh * 0.26))
        rows = (len(trial_keys) + cols - 1) // cols
        grid_h = rows * card_h + (rows - 1) * gap
        start_y = max(90, (sh - grid_h) // 2)

        card_rects = []
        for i, key in enumerate(trial_keys):
            row = i // cols
            col = i % cols
            x = 24 + col * (card_w + gap)
            y = start_y + row * (card_h + gap)
            rect = pygame.Rect(x, y, card_w, card_h)
            card_rects.append(rect)

            trial = TRIALS[key]
            best = progress.get(key, {})
            selected = (i == selected_idx)
            fill = (24, 34, 58) if not selected else (32, 48, 84)
            edge = (100, 150, 230) if not selected else (170, 220, 255)
            pygame.draw.rect(screen, fill, rect, border_radius=10)
            pygame.draw.rect(screen, edge, rect, 2, border_radius=10)

            t_s = head_font.render(trial["title"], True, (255, 230, 170))
            screen.blit(t_s, (rect.x + 12, rect.y + 10))
            d_s = body_font.render(trial["desc"], True, (215, 220, 235))
            screen.blit(d_s, (rect.x + 12, rect.y + 40))

            ghost_s = body_font.render(f"Ghost target: {float(trial['ghost_target']):.2f}s", True, (160, 230, 255))
            medals = trial["medal_times"]
            medal_s = hint_font.render(
                f"G {medals['gold']:.1f}s  S {medals['silver']:.1f}s  B {medals['bronze']:.1f}s",
                True,
                (225, 225, 220),
            )
            screen.blit(ghost_s, (rect.x + 12, rect.y + 74))
            screen.blit(medal_s, (rect.x + 12, rect.y + 98))

            best_medal = str(best.get("best_medal", "none")).title()
            best_time = best.get("best_time")
            completion_count = int(best.get("completion_count", 0) or 0)
            best_time_txt = "--" if best_time is None else f"{float(best_time):.2f}s"
            progress_s = hint_font.render(f"Best: {best_medal}   Time: {best_time_txt}   Clears: {completion_count}", True, (180, 205, 225))
            screen.blit(progress_s, (rect.x + 12, rect.bottom - 28))

        hint = hint_font.render("Up/Down or click to select  |  Enter to launch  |  Esc to return", True, (180, 205, 235))
        screen.blit(hint, (sw // 2 - hint.get_width() // 2, sh - 58))
        status_s = body_font.render(status, True, (240, 220, 165))
        screen.blit(status_s, (sw // 2 - status_s.get_width() // 2, sh - 30))

        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return True
                if event.key in (pygame.K_UP, pygame.K_LEFT):
                    selected_idx = (selected_idx - 1) % len(trial_keys)
                if event.key in (pygame.K_DOWN, pygame.K_RIGHT):
                    selected_idx = (selected_idx + 1) % len(trial_keys)
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    selected_key = trial_keys[selected_idx]
                    trial = TRIALS[selected_key]
                    run_stats = {}

                    def _on_complete(payload):
                        run_stats.update(payload)

                    cfg = _base_trial_config()
                    cfg.update(trial["config"])
                    cfg["training_target_time"] = float(trial["ghost_target"])
                    cfg["training_medal_times"] = dict(trial["medal_times"])

                    keep_running = level(
                        -1,
                        player_name,
                        level_config_override=cfg,
                        leaderboard_hooks={"on_complete": _on_complete},
                    )
                    if not keep_running:
                        return False

                    if not run_stats:
                        status = "Trial ended before completion."
                        continue

                    completion_time = float(run_stats.get("completion_time", 0.0))
                    deaths = int(run_stats.get("death_count", 0) or 0)
                    medal = _compute_trial_medal(trial, completion_time, deaths)
                    save_info = save_training_trial_result(player_name, selected_key, medal, completion_time, deaths)
                    delta = completion_time - float(trial["ghost_target"])
                    reward = int(save_info.get("reward_coins", 0) or 0)
                    token = save_info.get("reward_token")
                    if reward > 0 and token:
                        token_name = str(token).replace("training_token_", "").replace("_", " ").title()
                        status = f"{trial['title']}: {medal.title()} medal, delta {delta:+.2f}s. Rewards +{reward} coins and {token_name}."
                    elif reward > 0:
                        status = f"{trial['title']}: {medal.title()} medal, delta {delta:+.2f}s. New tier reward +{reward} coins."
                    else:
                        status = f"{trial['title']}: {medal.title()} medal, delta {delta:+.2f}s."
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for idx, rect in enumerate(card_rects):
                    if rect.collidepoint(event.pos):
                        selected_idx = idx
                        break
