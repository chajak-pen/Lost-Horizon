import pygame
from Classes import Button, resolve_asset_path
from level_data import LEVELS
from ui_helpers import fit_text, draw_wrapped_text
from database import (
    get_high_scores,
    get_fastest_times,
    get_survival_high_scores,
    get_high_scores_global,
    get_high_scores_friends,
    get_fastest_times_global,
    get_fastest_times_friends,
    get_survival_high_scores_friends,
)


pygame.init()


def leaderboard_screen(player_name=None):
    """Leaderboard browser for scores and times. Returns True to go back, False to quit."""
    screen = pygame.display.get_surface()
    created_here = False
    if screen is None:
        screen = pygame.display.set_mode((1000, 600))
        pygame.display.set_caption("Lost Horizon - Leaderboard")
        created_here = True

    sw, sh = screen.get_width(), screen.get_height()
    sx, sy = sw / 1000.0, sh / 600.0

    title_font = pygame.font.SysFont("Arial", max(24, int(44 * sy)), bold=True)
    heading_font = pygame.font.SysFont("Arial", max(14, int(24 * sy)), bold=True)
    row_font = pygame.font.SysFont("Arial", max(12, int(20 * sy)))
    hint_font = pygame.font.SysFont("Arial", max(11, int(18 * sy)))

    back_size = max(24, int(sw * 0.04))
    try:
        back_img = pygame.image.load(resolve_asset_path("back button.jpg")).convert_alpha()
        back_img = pygame.transform.scale(back_img, (back_size, back_size))
        back_button = Button(10, 10, back_img)
    except Exception:
        back_surface = pygame.Surface((back_size, back_size), pygame.SRCALPHA)
        back_surface.fill((70, 70, 70))
        pygame.draw.rect(back_surface, (210, 210, 210), back_surface.get_rect(), 2)
        back_button = Button(10, 10, back_surface)

    level_ids = sorted(LEVELS.keys())
    per_page = max(3, min(6, int((sh - 180) / 92)))
    total_pages = max(1, (len(level_ids) + per_page - 1) // per_page)
    page = 0
    metric = "score"  # score | time | survival
    scope = "per-level"  # per-level | global | friends | weekly

    prev_rect = pygame.Rect(20, sh - 52, 120, 34)
    next_rect = pygame.Rect(sw - 140, sh - 52, 120, 34)

    clock = pygame.time.Clock()
    running = True
    while running:
        clock.tick(60)

        screen.fill((18, 24, 36))

        title = title_font.render("Leaderboard", True, (240, 225, 170))
        screen.blit(title, ((sw - title.get_width()) // 2, 10))

        sub_text = "TAB metric, 1-4 scope, arrows page"
        if player_name:
            sub_text = f"Player: {player_name}"
        draw_wrapped_text(screen, hint_font, sub_text, (190, 200, 215), pygame.Rect(120, 50, sw - 240, 36), align="center", max_lines=2)

        mode_lbl = row_font.render(f"Metric: {metric.title()}   Scope: {scope}", True, (210, 220, 240))
        screen.blit(mode_lbl, (sw // 2 - mode_lbl.get_width() // 2, 74))

        if metric in ("score", "time") and scope == "per-level":
            start = page * per_page
            end = min(len(level_ids), start + per_page)
            visible = level_ids[start:end]

            panel_top = 102
            panel_h = max(84, int((sh - 184) / per_page))

            for idx, level_id in enumerate(visible):
                y = panel_top + idx * panel_h
                panel = pygame.Rect(26, y, sw - 52, panel_h - 8)
                pygame.draw.rect(screen, (28, 38, 56), panel, border_radius=8)
                pygame.draw.rect(screen, (90, 120, 170), panel, 2, border_radius=8)

                level_name = LEVELS.get(level_id, {}).get("name", f"Level {level_id}")
                head = heading_font.render(fit_text(heading_font, f"{level_id}. {level_name}", panel.width - 24), True, (255, 255, 255))
                screen.blit(head, (panel.x + 12, panel.y + 8))

                if metric == "score":
                    highs = get_high_scores(level_id, 1)
                    if highs:
                        hs_name, hs_score, hs_mode = highs[0]
                        tag = f" [{str(hs_mode).upper()}]" if hs_mode else ""
                        txt = f"Top Score: {hs_score} ({hs_name}){tag}"
                    else:
                        txt = "Top Score: --"
                    surf = row_font.render(txt, True, (255, 225, 130))
                else:
                    fastest = get_fastest_times(level_id, 1)
                    if fastest:
                        ft_name, ft_time, _, ft_mode = fastest[0]
                        tag = f" [{str(ft_mode).upper()}]" if ft_mode else ""
                        txt = f"Fastest Time: {ft_time:.2f}s ({ft_name}){tag}"
                    else:
                        txt = "Fastest Time: --"
                    surf = row_font.render(txt, True, (170, 225, 255))
                summary = fit_text(row_font, txt, panel.width - 28)
                screen.blit(row_font.render(summary, True, surf.get_at((0, 0))[:3]), (panel.x + 16, panel.y + 46))
        else:
            panel = pygame.Rect(26, 100, sw - 52, sh - 178)
            pygame.draw.rect(screen, (28, 38, 56), panel, border_radius=8)
            pygame.draw.rect(screen, (140, 120, 180), panel, 2, border_radius=8)

            if metric == "survival":
                if scope == "friends" and player_name:
                    rows = get_survival_high_scores_friends(player_name, 10, weekly=False)
                    head_text = "Survival Friends"
                elif scope == "weekly":
                    rows = get_survival_high_scores_friends(player_name, 10, weekly=True) if player_name else []
                    head_text = "Survival Weekly"
                else:
                    rows = get_survival_high_scores(10)
                    head_text = "Survival Global"
            elif metric == "score":
                if scope == "friends" and player_name:
                    rows = get_high_scores_friends(player_name, level_id=None, limit=10, weekly=False)
                    head_text = "Score Friends"
                elif scope == "weekly":
                    rows = get_high_scores_global(limit=10, weekly=True)
                    head_text = "Score Weekly"
                else:
                    rows = get_high_scores_global(limit=10, weekly=False)
                    head_text = "Score Global"
            else:
                if scope == "friends" and player_name:
                    rows = get_fastest_times_friends(player_name, level_id=None, limit=10, weekly=False)
                    head_text = "Time Friends"
                elif scope == "weekly":
                    rows = get_fastest_times_global(limit=10, weekly=True)
                    head_text = "Time Weekly"
                else:
                    rows = get_fastest_times_global(limit=10, weekly=False)
                    head_text = "Time Global"

            head = heading_font.render(head_text, True, (255, 255, 255))
            screen.blit(head, (panel.x + 14, panel.y + 10))

            y = panel.y + 44
            if not rows:
                empty = row_font.render("No results yet.", True, (210, 210, 210))
                screen.blit(empty, (panel.x + 16, y))
            else:
                line_h = max(24, int(28 * sy))
                max_rows = max(3, (panel.height - 58) // line_h)
                for idx, row in enumerate(rows[:max_rows], start=1):
                    if metric == "survival":
                        pname, pscore, waves = row
                        txt = f"{idx:>2}. {pname:<16}  Score: {pscore:<6}  Waves: {waves}"
                        col = (230, 220, 255)
                    elif metric == "score":
                        pname, pscore = row
                        txt = f"{idx:>2}. {pname:<16}  Best Score: {pscore}"
                        col = (255, 230, 150)
                    else:
                        pname, ptime = row
                        txt = f"{idx:>2}. {pname:<16}  Best Time: {ptime:.2f}s"
                        col = (175, 225, 255)
                    clipped = fit_text(row_font, txt, panel.width - 28)
                    txt_surf = row_font.render(clipped, True, col)
                    screen.blit(txt_surf, (panel.x + 16, y))
                    y += line_h

                hidden_rows = len(rows) - max_rows
                if hidden_rows > 0:
                    more = row_font.render(f"... and {hidden_rows} more entries", True, (185, 195, 210))
                    screen.blit(more, (panel.x + 16, min(panel.bottom - 28, y + 4)))

        # Page controls
        use_pages = metric in ("score", "time") and scope == "per-level"
        prev_active = use_pages and page > 0
        next_active = use_pages and page < total_pages - 1

        pygame.draw.rect(screen, (40, 80, 120) if prev_active else (65, 65, 65), prev_rect, border_radius=8)
        pygame.draw.rect(screen, (120, 190, 255) if prev_active else (110, 110, 110), prev_rect, 2, border_radius=8)
        prev_lbl = row_font.render("Prev", True, (255, 255, 255))
        screen.blit(prev_lbl, (prev_rect.centerx - prev_lbl.get_width() // 2, prev_rect.centery - prev_lbl.get_height() // 2))

        pygame.draw.rect(screen, (40, 80, 120) if next_active else (65, 65, 65), next_rect, border_radius=8)
        pygame.draw.rect(screen, (120, 190, 255) if next_active else (110, 110, 110), next_rect, 2, border_radius=8)
        next_lbl = row_font.render("Next", True, (255, 255, 255))
        screen.blit(next_lbl, (next_rect.centerx - next_lbl.get_width() // 2, next_rect.centery - next_lbl.get_height() // 2))

        page_text = f"Page {page + 1}/{total_pages}" if use_pages else "Scopes: 1 per-level | 2 global | 3 friends | 4 weekly"
        page_lbl = row_font.render(page_text, True, (220, 220, 220))
        screen.blit(page_lbl, (sw // 2 - page_lbl.get_width() // 2, sh - 45))

        back_button.draw()
        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    return True
                if event.key == pygame.K_TAB:
                    metric = "time" if metric == "score" else "survival" if metric == "time" else "score"
                if event.key == pygame.K_1:
                    scope = "per-level"
                if event.key == pygame.K_2:
                    scope = "global"
                if event.key == pygame.K_3:
                    scope = "friends"
                if event.key == pygame.K_4:
                    scope = "weekly"
                if event.key == pygame.K_LEFT and page > 0:
                    page -= 1
                if event.key == pygame.K_RIGHT and page < total_pages - 1:
                    page += 1

            if back_button.handle_event(event):
                return True

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if prev_rect.collidepoint(event.pos) and page > 0:
                    page -= 1
                if next_rect.collidepoint(event.pos) and page < total_pages - 1:
                    page += 1

    if created_here:
        pygame.display.quit()

    return True
