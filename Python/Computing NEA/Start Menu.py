import pygame
from Classes import *
from play_menu import play_menu
from shop import shop_menu
from settings import settings_menu
from leaderboard import leaderboard_screen
from profile_cards import profile_card_screen
from controls_screen import controls_screen
from sandbox_mode import sandbox_mode
from replay_viewer import replay_viewer_screen
from training_playground import launch_training_playground
from progression_hub import progression_hub_screen
from casino import casino_screen
from auth import authenticate_player_screen
import os
from game_settings import load_settings, MUSIC_PATH

pygame.init() #This intiializes all of the pygame modules

try:
    pygame.mixer.init()
except Exception:
    pass

_settings = load_settings()
music_on = _settings.get("music_on", True)
music_volume = _settings.get("music_volume", 0.5)
if music_on and os.path.exists(MUSIC_PATH):
    try:
        pygame.mixer.music.load(MUSIC_PATH)
        pygame.mixer.music.set_volume(music_volume)
        pygame.mixer.music.play(-1)
    except Exception:
        pass

info = pygame.display.Info()
screen_width, screen_height = info.current_w, info.current_h

def start_menu():
    player_name = authenticate_player_screen()
    if player_name is None:
        return False

    start_screen = pygame.display.set_mode((screen_width, screen_height)) #creates a 1000x600 pixel window
    pygame.display.set_caption("Lost Horizon") #sets the title of the game to "Lost Horizon"
    
    ground_surface = pygame.image.load('groound 3.jpg').convert_alpha() #loads the background image
    ground_surface = pygame.transform.scale(ground_surface, (screen_width, screen_height))

    # compute button sizes relative to screen and scale images
    play_w = max(48, int(screen_width * 0.20))
    play_h = max(24, int(screen_height * 0.1667))
    main_btn_title_font = pygame.font.SysFont("Arial", max(18, int(34 * (screen_height / 600.0))), bold=True)
    main_btn_sub_font = pygame.font.SysFont("Arial", max(10, int(18 * (screen_height / 600.0))))

    def make_main_button_surface(title, subtitle, fill_color, border_color, title_color=(255, 245, 220), subtitle_color=(255, 220, 170)):
        surface = pygame.Surface((play_w, play_h), pygame.SRCALPHA)
        surface.fill(fill_color)
        pygame.draw.rect(surface, border_color, surface.get_rect(), 4, border_radius=12)
        title_s = main_btn_title_font.render(title, True, title_color)
        subtitle_s = main_btn_sub_font.render(subtitle, True, subtitle_color)
        surface.blit(title_s, ((play_w - title_s.get_width()) // 2, max(14, play_h // 2 - title_s.get_height())))
        surface.blit(subtitle_s, ((play_w - subtitle_s.get_width()) // 2, min(play_h - subtitle_s.get_height() - 14, play_h // 2 + 8)))
        return surface

    play_surface = make_main_button_surface("PLAY", "start adventure", (35, 72, 88), (150, 220, 255))
    play_hover_surface = make_main_button_surface("PLAY", "start adventure", (46, 90, 110), (175, 235, 255))
    shop_surface = make_main_button_surface("SHOP", "power and supplies", (44, 84, 56), (160, 235, 170))
    shop_hover_surface = make_main_button_surface("SHOP", "power and supplies", (56, 102, 68), (180, 245, 190))
    casino_surface = make_main_button_surface("CASINO", "chips and tables", (72, 30, 86), (255, 205, 120))
    casino_hover_surface = make_main_button_surface("CASINO", "chips and tables", (95, 40, 112), (255, 225, 145))
    exit_surface = make_main_button_surface("EXIT", "quit game", (96, 34, 40), (255, 150, 150))
    exit_hover_surface = make_main_button_surface("EXIT", "quit game", (118, 44, 52), (255, 175, 175))

    settings_image = pygame.image.load("settings button.jpeg").convert_alpha()
    settings_size = max(24, int(screen_width * 0.04))
    settings_image = pygame.transform.scale(settings_image, (settings_size, settings_size))

    logout_w = max(80, int(screen_width * 0.13))
    logout_h = max(30, int(screen_height * 0.075))
    logout_surface = pygame.Surface((logout_w, logout_h), pygame.SRCALPHA)
    logout_surface.fill((40, 60, 100))
    pygame.draw.rect(logout_surface, (100, 180, 255), logout_surface.get_rect(), 3, border_radius=8)
    logout_font = pygame.font.SysFont("Arial", max(12, int(22 * (screen_height / 600.0))))
    logout_label = logout_font.render("Logout", True, (255, 255, 255))
    logout_surface.blit(
        logout_label,
        ((logout_w - logout_label.get_width()) // 2, (logout_h - logout_label.get_height()) // 2),
    )

    leaderboard_w = max(100, int(screen_width * 0.15))
    leaderboard_h = max(34, int(screen_height * 0.075))
    leaderboard_surface = pygame.Surface((leaderboard_w, leaderboard_h), pygame.SRCALPHA)
    leaderboard_surface.fill((95, 70, 25))
    pygame.draw.rect(leaderboard_surface, (240, 205, 120), leaderboard_surface.get_rect(), 3, border_radius=8)
    leaderboard_font = pygame.font.SysFont("Arial", max(11, int(20 * (screen_height / 600.0))))
    leaderboard_label = leaderboard_font.render("Leaderboard", True, (255, 255, 255))
    leaderboard_surface.blit(
        leaderboard_label,
        ((leaderboard_w - leaderboard_label.get_width()) // 2, (leaderboard_h - leaderboard_label.get_height()) // 2),
    )

    meta_w = leaderboard_w
    meta_h = leaderboard_h
    meta_surface = pygame.Surface((meta_w, meta_h), pygame.SRCALPHA)
    meta_surface.fill((66, 78, 40))
    pygame.draw.rect(meta_surface, (222, 225, 120), meta_surface.get_rect(), 3, border_radius=8)
    meta_label = leaderboard_font.render("Progress", True, (255, 255, 255))
    meta_surface.blit(
        meta_label,
        ((meta_w - meta_label.get_width()) // 2, (meta_h - meta_label.get_height()) // 2),
    )

    profile_w = leaderboard_w
    profile_h = leaderboard_h
    profile_surface = pygame.Surface((profile_w, profile_h), pygame.SRCALPHA)
    profile_surface.fill((30, 75, 95))
    pygame.draw.rect(profile_surface, (130, 220, 245), profile_surface.get_rect(), 3, border_radius=8)
    profile_label = leaderboard_font.render("Profile", True, (255, 255, 255))
    profile_surface.blit(
        profile_label,
        ((profile_w - profile_label.get_width()) // 2, (profile_h - profile_label.get_height()) // 2),
    )

    controls_w = leaderboard_w
    controls_h = leaderboard_h
    controls_surface = pygame.Surface((controls_w, controls_h), pygame.SRCALPHA)
    controls_surface.fill((35, 70, 40))
    pygame.draw.rect(controls_surface, (120, 225, 130), controls_surface.get_rect(), 3, border_radius=8)
    controls_label = leaderboard_font.render("Controls", True, (255, 255, 255))
    controls_surface.blit(
        controls_label,
        ((controls_w - controls_label.get_width()) // 2, (controls_h - controls_label.get_height()) // 2),
    )

    sandbox_w = leaderboard_w
    sandbox_h = leaderboard_h
    sandbox_surface = pygame.Surface((sandbox_w, sandbox_h), pygame.SRCALPHA)
    sandbox_surface.fill((70, 42, 78))
    pygame.draw.rect(sandbox_surface, (220, 155, 240), sandbox_surface.get_rect(), 3, border_radius=8)
    sandbox_label = leaderboard_font.render("Sandbox", True, (255, 255, 255))
    sandbox_surface.blit(
        sandbox_label,
        ((sandbox_w - sandbox_label.get_width()) // 2, (sandbox_h - sandbox_label.get_height()) // 2),
    )

    replay_w = leaderboard_w
    replay_h = leaderboard_h
    replay_surface = pygame.Surface((replay_w, replay_h), pygame.SRCALPHA)
    replay_surface.fill((50, 66, 96))
    pygame.draw.rect(replay_surface, (145, 195, 255), replay_surface.get_rect(), 3, border_radius=8)
    replay_label = leaderboard_font.render("Replays", True, (255, 255, 255))
    replay_surface.blit(
        replay_label,
        ((replay_w - replay_label.get_width()) // 2, (replay_h - replay_label.get_height()) // 2),
    )

    training_w = leaderboard_w
    training_h = leaderboard_h
    training_surface = pygame.Surface((training_w, training_h), pygame.SRCALPHA)
    training_surface.fill((56, 88, 62))
    pygame.draw.rect(training_surface, (140, 235, 160), training_surface.get_rect(), 3, border_radius=8)
    training_label = leaderboard_font.render("Training", True, (255, 255, 255))
    training_surface.blit(
        training_label,
        ((training_w - training_label.get_width()) // 2, (training_h - training_label.get_height()) // 2),
    )

    # Centered layout with responsive utility grid to avoid vertical overflow.
    center_x = screen_width // 2 - play_w // 2
    title_area = int(screen_height * 0.15)
    utility_gap_x = max(10, int(screen_width * 0.012))
    utility_gap_y = max(8, int(screen_height * 0.012))
    utility_w = min(leaderboard_w, max(96, (screen_width - 60 - utility_gap_x * 3) // 4))
    utility_h = leaderboard_h
    utility_grid_w = utility_w * 4 + utility_gap_x * 3
    utility_x0 = (screen_width - utility_grid_w) // 2
    utility_y0 = title_area + int(screen_height * 0.02)
    utility_positions = [
        (utility_x0 + col * (utility_w + utility_gap_x), utility_y0 + row * (utility_h + utility_gap_y))
        for row in range(2)
        for col in range(4)
    ]

    utility_bottom = utility_y0 + 2 * utility_h + utility_gap_y
    buttons_area_start = utility_bottom + int(screen_height * 0.04)
    buttons_area_height = screen_height - buttons_area_start - int(screen_height * 0.1)
    button_spacing = max(play_h + 10, buttons_area_height / 4)

    play_y = int(buttons_area_start + button_spacing * 0.15)
    shop_y = int(buttons_area_start + button_spacing * 1.05)
    casino_y = int(buttons_area_start + button_spacing * 1.95)
    exit_y = int(buttons_area_start + button_spacing * 2.85)

    # Settings stays top-right; remaining utility buttons live in the centered grid.
    settings_x = screen_width - settings_size - 15
    settings_y = 15
    leaderboard_x, leaderboard_y = utility_positions[0]
    meta_x, meta_y = utility_positions[1]
    profile_x, profile_y = utility_positions[2]
    controls_x, controls_y = utility_positions[3]
    sandbox_x, sandbox_y = utility_positions[4]
    replay_x, replay_y = utility_positions[5]
    training_x, training_y = utility_positions[6]
    logout_x, logout_y = utility_positions[7]

    play_button = Button(center_x, play_y, play_surface)
    shop_button = Button(center_x, shop_y, shop_surface)
    casino_button = Button(center_x, casino_y, casino_surface)
    settings_button = Button(settings_x, settings_y, settings_image)
    logout_button = Button(logout_x, logout_y, logout_surface)
    meta_button = Button(meta_x, meta_y, meta_surface)
    leaderboard_button = Button(leaderboard_x, leaderboard_y, leaderboard_surface)
    profile_button = Button(profile_x, profile_y, profile_surface)
    controls_button = Button(controls_x, controls_y, controls_surface)
    sandbox_button = Button(sandbox_x, sandbox_y, sandbox_surface)
    replay_button = Button(replay_x, replay_y, replay_surface)
    training_button = Button(training_x, training_y, training_surface)
    exit_button = Button(center_x, exit_y, exit_surface)

    title_font = pygame.font.SysFont("Arial", max(60, int(80 * (screen_height / 600.0))), bold=True)
    subtitle_font = pygame.font.SysFont("Arial", max(20, int(28 * (screen_height / 600.0))))
    
    mouse_pos = (0, 0)
    hand_cursor = pygame.cursors.Cursor(pygame.SYSTEM_CURSOR_HAND)
    arrow_cursor = pygame.cursors.Cursor(pygame.SYSTEM_CURSOR_ARROW)

    def draw_main_card_button(button, normal_surface, hover_surface):
        hovered = button.rect.collidepoint(mouse_pos)
        shadow_offset = button_hover_dist if hovered else 2
        shadow_rect = pygame.Rect(button.rect.x + shadow_offset, button.rect.y + shadow_offset, button.rect.w, button.rect.h)
        pygame.draw.rect(start_screen, (0, 0, 0), shadow_rect, border_radius=10)
        start_screen.blit(hover_surface if hovered else normal_surface, button.rect.topleft)
    
    running = True
    while running:# starts a while loop that will run the program
        mouse_pos = pygame.mouse.get_pos()
        
        # Determine if hovering over a button
        hovering_button = (play_button.rect.collidepoint(mouse_pos) or 
                          shop_button.rect.collidepoint(mouse_pos) or 
                          casino_button.rect.collidepoint(mouse_pos) or 
                          settings_button.rect.collidepoint(mouse_pos) or 
                          logout_button.rect.collidepoint(mouse_pos) or 
                          meta_button.rect.collidepoint(mouse_pos) or 
                          leaderboard_button.rect.collidepoint(mouse_pos) or 
                          profile_button.rect.collidepoint(mouse_pos) or 
                          controls_button.rect.collidepoint(mouse_pos) or 
                          sandbox_button.rect.collidepoint(mouse_pos) or 
                          replay_button.rect.collidepoint(mouse_pos) or 
                          training_button.rect.collidepoint(mouse_pos) or 
                          exit_button.rect.collidepoint(mouse_pos))
        
        # Change cursor based on hover
        if hovering_button:
            pygame.mouse.set_cursor(hand_cursor)
        else:
            pygame.mouse.set_cursor(arrow_cursor)
        
        start_screen.blit(ground_surface, (0,0)) #draws the background image at the top left corner
        
        # Draw semi-transparent overlay for better text visibility
        overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
        overlay.fill((10, 10, 20, 60))
        start_screen.blit(overlay, (0, 0))
        
        # Draw title with shadow effect
        title_text = title_font.render("Lost Horizon", True, (150, 200, 255))
        title_shadow = title_font.render("Lost Horizon", True, (0, 0, 0))
        title_x = screen_width // 2 - title_text.get_width() // 2
        title_y = int(screen_height * 0.02)
        start_screen.blit(title_shadow, (title_x + 3, title_y + 3))
        start_screen.blit(title_text, (title_x, title_y))
        
        # Draw decorative line under title
        pygame.draw.line(start_screen, (100, 180, 255), (title_x - 20, title_y + title_text.get_height() + 10), 
                        (title_x + title_text.get_width() + 20, title_y + title_text.get_height() + 10), 3)
        
        # Draw player name with styling
        account_font = pygame.font.SysFont("Arial", max(16, int(24 * (screen_height / 600.0))))
        account_text = Text(f"Welcome, {player_name}", 20, screen_height - 40, account_font)
        account_text.draw_text()
        
        # Draw buttons with hover effects
        button_hover_dist = 8
        
        draw_main_card_button(play_button, play_surface, play_hover_surface)
        draw_main_card_button(shop_button, shop_surface, shop_hover_surface)
        draw_main_card_button(exit_button, exit_surface, exit_hover_surface)
        
        # Settings button with hover effect
        if settings_button.rect.collidepoint(mouse_pos):
            settings_bg = pygame.Surface((settings_size + 12, settings_size + 12), pygame.SRCALPHA)
            pygame.draw.circle(settings_bg, (100, 100, 255, 80), (settings_size // 2 + 6, settings_size // 2 + 6), settings_size // 2 + 6)
            start_screen.blit(settings_bg, (settings_button.rect.x - 6, settings_button.rect.y - 6))
        
        settings_button.draw()
        
        # Logout button with improved styling
        if logout_button.rect.collidepoint(mouse_pos):
            logout_surface_hover = pygame.Surface((logout_w, logout_h), pygame.SRCALPHA)
            logout_surface_hover.fill((50, 100, 150))
            pygame.draw.rect(logout_surface_hover, (150, 220, 255), logout_surface_hover.get_rect(), 3, border_radius=8)
            logout_label_hover = logout_font.render("Logout", True, (255, 255, 255))
            logout_surface_hover.blit(
                logout_label_hover,
                ((logout_w - logout_label_hover.get_width()) // 2, (logout_h - logout_label_hover.get_height()) // 2),
            )
            start_screen.blit(logout_surface_hover, (logout_x, logout_y))
            # Draw shadow
            shadow_logout = pygame.draw.rect(start_screen, (0, 0, 0), (logout_x + 2, logout_y + 2, logout_w, logout_h), border_radius=8)
        else:
            start_screen.blit(logout_surface, (logout_x, logout_y))

        draw_main_card_button(casino_button, casino_surface, casino_hover_surface)

        if meta_button.rect.collidepoint(mouse_pos):
            mt_hover = pygame.Surface((meta_w, meta_h), pygame.SRCALPHA)
            mt_hover.fill((82, 95, 52))
            pygame.draw.rect(mt_hover, (240, 245, 145), mt_hover.get_rect(), 3, border_radius=8)
            mt_label = leaderboard_font.render("Progress", True, (255, 255, 255))
            mt_hover.blit(mt_label, ((meta_w - mt_label.get_width()) // 2, (meta_h - mt_label.get_height()) // 2))
            start_screen.blit(mt_hover, (meta_x, meta_y))
        else:
            start_screen.blit(meta_surface, (meta_x, meta_y))

        # Leaderboard button styling
        if leaderboard_button.rect.collidepoint(mouse_pos):
            lb_hover = pygame.Surface((leaderboard_w, leaderboard_h), pygame.SRCALPHA)
            lb_hover.fill((120, 90, 35))
            pygame.draw.rect(lb_hover, (255, 220, 130), lb_hover.get_rect(), 3, border_radius=8)
            lb_label = leaderboard_font.render("Leaderboard", True, (255, 255, 255))
            lb_hover.blit(lb_label, ((leaderboard_w - lb_label.get_width()) // 2, (leaderboard_h - lb_label.get_height()) // 2))
            start_screen.blit(lb_hover, (leaderboard_x, leaderboard_y))
        else:
            start_screen.blit(leaderboard_surface, (leaderboard_x, leaderboard_y))

        if profile_button.rect.collidepoint(mouse_pos):
            pr_hover = pygame.Surface((profile_w, profile_h), pygame.SRCALPHA)
            pr_hover.fill((45, 95, 120))
            pygame.draw.rect(pr_hover, (165, 235, 255), pr_hover.get_rect(), 3, border_radius=8)
            pr_label = leaderboard_font.render("Profile", True, (255, 255, 255))
            pr_hover.blit(pr_label, ((profile_w - pr_label.get_width()) // 2, (profile_h - pr_label.get_height()) // 2))
            start_screen.blit(pr_hover, (profile_x, profile_y))
        else:
            start_screen.blit(profile_surface, (profile_x, profile_y))

        if controls_button.rect.collidepoint(mouse_pos):
            ct_hover = pygame.Surface((controls_w, controls_h), pygame.SRCALPHA)
            ct_hover.fill((50, 95, 55))
            pygame.draw.rect(ct_hover, (160, 255, 165), ct_hover.get_rect(), 3, border_radius=8)
            ct_label = leaderboard_font.render("Controls", True, (255, 255, 255))
            ct_hover.blit(ct_label, ((controls_w - ct_label.get_width()) // 2, (controls_h - ct_label.get_height()) // 2))
            start_screen.blit(ct_hover, (controls_x, controls_y))
        else:
            start_screen.blit(controls_surface, (controls_x, controls_y))

        if sandbox_button.rect.collidepoint(mouse_pos):
            sb_hover = pygame.Surface((sandbox_w, sandbox_h), pygame.SRCALPHA)
            sb_hover.fill((88, 52, 98))
            pygame.draw.rect(sb_hover, (235, 180, 255), sb_hover.get_rect(), 3, border_radius=8)
            sb_label = leaderboard_font.render("Sandbox", True, (255, 255, 255))
            sb_hover.blit(sb_label, ((sandbox_w - sb_label.get_width()) // 2, (sandbox_h - sb_label.get_height()) // 2))
            start_screen.blit(sb_hover, (sandbox_x, sandbox_y))
        else:
            start_screen.blit(sandbox_surface, (sandbox_x, sandbox_y))

        if replay_button.rect.collidepoint(mouse_pos):
            rp_hover = pygame.Surface((replay_w, replay_h), pygame.SRCALPHA)
            rp_hover.fill((66, 82, 112))
            pygame.draw.rect(rp_hover, (175, 215, 255), rp_hover.get_rect(), 3, border_radius=8)
            rp_label = leaderboard_font.render("Replays", True, (255, 255, 255))
            rp_hover.blit(rp_label, ((replay_w - rp_label.get_width()) // 2, (replay_h - rp_label.get_height()) // 2))
            start_screen.blit(rp_hover, (replay_x, replay_y))
        else:
            start_screen.blit(replay_surface, (replay_x, replay_y))

        if training_button.rect.collidepoint(mouse_pos):
            tr_hover = pygame.Surface((training_w, training_h), pygame.SRCALPHA)
            tr_hover.fill((70, 102, 78))
            pygame.draw.rect(tr_hover, (178, 250, 195), tr_hover.get_rect(), 3, border_radius=8)
            tr_label = leaderboard_font.render("Training", True, (255, 255, 255))
            tr_hover.blit(tr_label, ((training_w - tr_label.get_width()) // 2, (training_h - tr_label.get_height()) // 2))
            start_screen.blit(tr_hover, (training_x, training_y))
        else:
            start_screen.blit(training_surface, (training_x, training_y))
        
        for event in pygame.event.get(): 
            if event.type == pygame.QUIT:
                running = False
                return False
                
            if play_button.handle_event(event):
                keep_running = play_menu(player_name)  # open play menu and wait for it to return
                if not keep_running:
                    return False
            if shop_button.handle_event(event):
                keep_running = shop_menu(player_name)  # open shop menu and wait for it to return
                if not keep_running:
                    return False
            if casino_button.handle_event(event):
                keep_running = casino_screen(player_name)
                if not keep_running:
                    return False
            if settings_button.handle_event(event):
                keep_running = settings_menu(player_name=player_name)  # open settings menu and wait for it to return
                if not keep_running:
                    return False
            if leaderboard_button.handle_event(event):
                keep_running = leaderboard_screen(player_name)
                if not keep_running:
                    return False
            if meta_button.handle_event(event):
                keep_running = progression_hub_screen(player_name)
                if not keep_running:
                    return False
            if profile_button.handle_event(event):
                keep_running = profile_card_screen(player_name)
                if not keep_running:
                    return False
            if controls_button.handle_event(event):
                keep_running = controls_screen(player_name)
                if not keep_running:
                    return False
            if sandbox_button.handle_event(event):
                keep_running = sandbox_mode(player_name)
                if not keep_running:
                    return False
            if replay_button.handle_event(event):
                keep_running = replay_viewer_screen(player_name)
                if not keep_running:
                    return False
            if training_button.handle_event(event):
                keep_running = launch_training_playground(player_name)
                if not keep_running:
                    return False
            if logout_button.handle_event(event):
                new_player = authenticate_player_screen()
                if new_player is None:
                    return False
                player_name = new_player
            if exit_button.handle_event(event):
                running = False
                return False
        
        pygame.display.update()
    
    return True


if __name__ == "__main__":
    start_menu()
    pygame.display.update()

try:
    pygame.mixer.music.stop()
except Exception:
    pass

pygame.quit()