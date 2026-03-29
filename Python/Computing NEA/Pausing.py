import pygame
from game_settings import load_settings
from ui_helpers import draw_wrapped_text

pygame.init()

# Use a local clock for the pause loop
clock = pygame.time.Clock()


def pause_game(stats=None): 

    # This ensures there is a screen display
    # get_surface() will return it from the main program, otherwise it creates a default one.
    screen = pygame.display.get_surface()
    created_here = False
    if screen is None:
        screen = pygame.display.set_mode((1000, 439))
        pygame.display.set_caption('Lost Horizon (pause)')
        created_here = True

    paused = True
    title_font = pygame.font.SysFont("Arial", 46, bold=True)
    subtitle_font = pygame.font.SysFont("Arial", 21)
    stats_font = pygame.font.SysFont("Arial", 24)
    btn_font = pygame.font.SysFont("Arial", 24, bold=True)
    hint_font = pygame.font.SysFont("Arial", 18)

    try:
        settings = load_settings()
        pause_keys = settings.get("keybinds", {}).get("pause", ["p"])
        pause_hint = "/".join(str(k).upper() for k in pause_keys)
    except Exception:
        pause_hint = "P"

    sw, sh = screen.get_width(), screen.get_height()
    panel_w = min(620, int(sw * 0.78))
    panel_h = min(400, int(sh * 0.82))
    panel = pygame.Rect((sw - panel_w) // 2, (sh - panel_h) // 2, panel_w, panel_h)

    btn_w = max(150, int(panel_w * 0.32))
    btn_h = 50
    btn_gap = 18
    resume_rect = pygame.Rect(panel.centerx - btn_w - btn_gap // 2, panel.bottom - btn_h - 22, btn_w, btn_h)
    quit_rect = pygame.Rect(panel.centerx + btn_gap // 2, panel.bottom - btn_h - 22, btn_w, btn_h)
    
    while paused:
        mouse_pos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # If we created the display here we leave it open 
                # and let the caller handle quitting return False to signal quit.
                return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: #when escape is pressed, the game is paused
                paused = False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if resume_rect.collidepoint(event.pos):
                    paused = False
                if quit_rect.collidepoint(event.pos):
                    return False

        # Lighter overlay so level remains visible while paused.
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((8, 12, 18, 58))
        screen.blit(overlay, (0, 0))

        # Glass panel
        panel_surface = pygame.Surface((panel.w, panel.h), pygame.SRCALPHA)
        pygame.draw.rect(panel_surface, (18, 26, 40, 178), panel_surface.get_rect(), border_radius=16)
        pygame.draw.rect(panel_surface, (165, 200, 235, 155), panel_surface.get_rect(), 2, border_radius=16)
        screen.blit(panel_surface, panel.topleft)

        title = title_font.render("Paused", True, (240, 246, 255))
        screen.blit(title, (panel.centerx - title.get_width() // 2, panel.y + 18))

        draw_wrapped_text(screen, subtitle_font, "Press ESC or Resume to continue", (184, 206, 230), pygame.Rect(panel.x + 24, panel.y + 74, panel.w - 48, 28), align="center", max_lines=2)
        kb_bottom = draw_wrapped_text(
            screen,
            hint_font,
            f"Pause keybind: {pause_hint}   |   Ghost: G   |   Debug: F3",
            (170, 196, 222),
            pygame.Rect(panel.x + 24, panel.y + 100, panel.w - 48, 44),
            align="center",
            max_lines=2,
        )

        divider_y = kb_bottom + 6
        pygame.draw.line(screen, (120, 150, 180), (panel.x + 26, divider_y), (panel.right - 26, divider_y), 1)

        if stats:
            y = divider_y + 18
            lines = [
                f"Run Time: {stats.get('time', 0):.1f}s",
                f"Coins: {int(stats.get('coins', 0))}",
                f"Kills: {int(stats.get('kills', 0))}",
            ]
            for line in lines:
                card = pygame.Rect(panel.x + 34, y - 6, panel.w - 68, 40)
                pygame.draw.rect(screen, (32, 44, 62, 170), card, border_radius=8)
                pygame.draw.rect(screen, (105, 132, 160), card, 1, border_radius=8)
                s = stats_font.render(line, True, (230, 236, 246))
                screen.blit(s, (panel.centerx - s.get_width() // 2, y + 2))
                y += 48

        # Resume button
        resume_hover = resume_rect.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (42, 120, 82) if resume_hover else (34, 96, 68), resume_rect, border_radius=10)
        pygame.draw.rect(screen, (145, 230, 186), resume_rect, 2, border_radius=10)
        resume_label = btn_font.render("Resume", True, (255, 255, 255))
        screen.blit(resume_label, (resume_rect.centerx - resume_label.get_width() // 2,
                                   resume_rect.centery - resume_label.get_height() // 2))

        # Quit button
        quit_hover = quit_rect.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (138, 54, 54) if quit_hover else (112, 46, 46), quit_rect, border_radius=10)
        pygame.draw.rect(screen, (244, 160, 160), quit_rect, 2, border_radius=10)
        quit_label = btn_font.render("Quit", True, (255, 255, 255))
        screen.blit(quit_label, (quit_rect.centerx - quit_label.get_width() // 2,
                                 quit_rect.centery - quit_label.get_height() // 2))


        pygame.display.update()
        clock.tick(60)

    # Not calling pygame.quit() as the main program may still be running
    return True