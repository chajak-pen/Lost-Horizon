import os
import pygame
from Classes import resolve_asset_path
from database import create_connection, initialize_database, register_player, authenticate_player
from ui_helpers import draw_wrapped_text, load_system_cursor, apply_hover_cursor, get_safe_display_size

pygame.init()
initialize_database()


def _draw_button(screen, rect, text, font, fill=(50, 50, 50), border=(200, 200, 200), hover=False):
    # Draw shadow for depth
    shadow_rect = rect.copy()
    shadow_rect.y += 4
    pygame.draw.rect(screen, (0, 0, 0), shadow_rect, border_radius=10)
    
    # Brighten fill color on hover for visual feedback
    if hover:
        fill = tuple(min(255, c + 40) for c in fill)
    
    pygame.draw.rect(screen, fill, rect, border_radius=10)
    pygame.draw.rect(screen, border, rect, 3 if hover else 2, border_radius=10)
    txt = font.render(text, True, (255, 255, 255))
    screen.blit(txt, (rect.x + (rect.w - txt.get_width()) // 2, rect.y + (rect.h - txt.get_height()) // 2))


def _draw_input(screen, rect, value, active, font, hidden=False):
    # Draw shadow
    shadow_rect = rect.copy()
    shadow_rect.y += 2
    pygame.draw.rect(screen, (0, 0, 0), shadow_rect, border_radius=8)
    
    # Color based on active state
    if active:
        fill_color = (30, 35, 45)
        border_color = (100, 200, 255)
        border_width = 3
    else:
        fill_color = (20, 20, 20)
        border_color = (180, 180, 180)
        border_width = 2
    
    pygame.draw.rect(screen, fill_color, rect, border_radius=8)
    pygame.draw.rect(screen, border_color, rect, border_width, border_radius=8)
    display = ("*" * len(value)) if hidden else value
    text = font.render(display, True, (255, 255, 255))
    screen.blit(text, (rect.x + 10, rect.y + (rect.h - text.get_height()) // 2))


def authenticate_player_screen():
    screen_w, screen_h = get_safe_display_size()
    screen = pygame.display.set_mode((screen_w, screen_h), pygame.RESIZABLE)
    pygame.display.set_caption("Lost Horizon - Login")

    bg = None
    for bg_path in ("login_background.png", "background.jpg", "background.png"):
        resolved_bg_path = resolve_asset_path(bg_path)
        if os.path.exists(resolved_bg_path):
            try:
                bg = pygame.image.load(resolved_bg_path).convert_alpha()
                bg = pygame.transform.scale(bg, (screen_w, screen_h))
                break
            except Exception:
                continue

    sx = screen_w / 1000.0
    sy = screen_h / 600.0

    title_font = pygame.font.SysFont("Arial", max(24, int(52 * sy)))
    body_font = pygame.font.SysFont("Arial", max(14, int(28 * sy)))
    button_font = pygame.font.SysFont("Arial", max(12, int(24 * sy)))

    panel_w = int(620 * sx)
    panel_h = int(510 * sy)
    panel_x = (screen_w - panel_w) // 2
    panel_y = (screen_h - panel_h) // 2

    login_btn = pygame.Rect(panel_x + int(40 * sx), panel_y + int(110 * sy), int(240 * sx), int(62 * sy))
    register_btn = pygame.Rect(panel_x + int(340 * sx), panel_y + int(110 * sy), int(240 * sx), int(62 * sy))
    exit_btn = pygame.Rect(panel_x + int(40 * sx), panel_y + int(188 * sy), int(540 * sx), int(50 * sy))

    name_rect = pygame.Rect(panel_x + int(40 * sx), panel_y + int(120 * sy), int(540 * sx), int(52 * sy))
    pass_rect = pygame.Rect(panel_x + int(40 * sx), panel_y + int(210 * sy), int(540 * sx), int(52 * sy))
    confirm_rect = pygame.Rect(panel_x + int(40 * sx), panel_y + int(300 * sy), int(540 * sx), int(52 * sy))

    submit_btn = pygame.Rect(panel_x + int(340 * sx), panel_y + int(384 * sy), int(240 * sx), int(52 * sy))
    back_btn = pygame.Rect(panel_x + int(40 * sx), panel_y + int(384 * sy), int(240 * sx), int(52 * sy))
    show_pass_rect = pygame.Rect(panel_x + int(460 * sx), panel_y + int(176 * sy), int(120 * sx), int(28 * sy))
    show_confirm_rect = pygame.Rect(panel_x + int(460 * sx), panel_y + int(356 * sy), int(120 * sx), int(28 * sy))

    state = "choice"  # choice/login/register
    active_field = "name"
    name = ""
    password = ""
    confirm_password = ""
    message = "Choose Login or Register"
    message_color = (220, 220, 220)
    show_password = False
    show_confirm_password = False
    failed_login_attempts = 0
    lock_until_ms = 0
    mouse_pos = (0, 0)

    def submit_current():
        nonlocal state, name, password, confirm_password
        nonlocal message, message_color, failed_login_attempts, lock_until_ms

        now_ms = pygame.time.get_ticks()
        if state == "login" and now_ms < lock_until_ms:
            wait_s = max(1, (lock_until_ms - now_ms + 999) // 1000)
            message = f"Too many failed attempts. Try again in {wait_s}s."
            message_color = (255, 180, 120)
            return None

        if state == "register" and password != confirm_password:
            message = "Passwords do not match."
            message_color = (255, 120, 120)
            return None

        conn = create_connection()
        if not conn:
            message = "Database connection failed."
            message_color = (255, 120, 120)
            return None

        if state == "login":
            ok, response = authenticate_player(conn, name, password)
        else:
            ok, response = register_player(conn, name, password)
        conn.close()

        if ok:
            failed_login_attempts = 0
            return response

        if state == "login":
            failed_login_attempts += 1
            if failed_login_attempts >= 5:
                lock_until_ms = pygame.time.get_ticks() + 10000
                failed_login_attempts = 0
                message = "Too many failed attempts. Login locked for 10 seconds."
                message_color = (255, 180, 120)
                return None

        message = response
        message_color = (255, 120, 120)
        return None

    clock = pygame.time.Clock()
    hand_cursor = load_system_cursor(pygame.SYSTEM_CURSOR_HAND)
    arrow_cursor = load_system_cursor(pygame.SYSTEM_CURSOR_ARROW)
    current_cursor = None
    
    while True:
        mouse_pos = pygame.mouse.get_pos()
        
        if bg is not None:
            screen.blit(bg, (0, 0))
        else:
            # Draw a gradient-like background with dark colors
            screen.fill((10, 10, 15))
            for y in range(screen_h):
                color_val = int(10 + (y / screen_h) * 20)
                pygame.draw.line(screen, (color_val, color_val, color_val + 5), (0, y), (screen_w, y))

        # Draw panel with shadow and gradient effect
        pygame.draw.rect(screen, (0, 0, 0), (panel_x + 4, panel_y + 4, panel_w, panel_h), border_radius=14)
        pygame.draw.rect(screen, (20, 20, 30), (panel_x, panel_y, panel_w, panel_h), border_radius=14)
        pygame.draw.rect(screen, (80, 100, 140), (panel_x, panel_y, panel_w, panel_h), 3, border_radius=14)

        # Draw decorative top bar
        pygame.draw.rect(screen, (50, 80, 140), (panel_x, panel_y, panel_w, int(8 * sy)), border_radius=14)

        title = title_font.render("Lost Horizon", True, (150, 200, 255))
        screen.blit(title, (panel_x + (panel_w - title.get_width()) // 2, panel_y + int(20 * sy)))

        draw_wrapped_text(
            screen,
            body_font,
            message,
            message_color,
            pygame.Rect(panel_x + int(40 * sx), panel_y + int(72 * sy), panel_w - int(80 * sx), int(48 * sy)),
            line_gap=2,
            max_lines=2,
        )

        if state == "choice":
            login_hover = login_btn.collidepoint(mouse_pos)
            register_hover = register_btn.collidepoint(mouse_pos)
            exit_hover = exit_btn.collidepoint(mouse_pos)
            
            # Set cursor based on hover
            current_cursor = apply_hover_cursor(
                login_hover or register_hover or exit_hover,
                hand_cursor,
                arrow_cursor,
                current_cursor,
            )
            
            _draw_button(screen, login_btn, "Login", button_font, fill=(40, 80, 130), border=(100, 180, 255), hover=login_hover)
            _draw_button(screen, register_btn, "Register", button_font, fill=(40, 130, 80), border=(100, 255, 150), hover=register_hover)
            _draw_button(screen, exit_btn, "Exit Game", button_font, fill=(130, 40, 40), border=(255, 100, 100), hover=exit_hover)
        else:
            now_ms = pygame.time.get_ticks()
            if state == "login" and now_ms < lock_until_ms:
                wait_s = max(1, (lock_until_ms - now_ms + 999) // 1000)
                draw_wrapped_text(
                    screen,
                    body_font,
                    f"Login retry delay active: {wait_s}s",
                    (255, 190, 120),
                    pygame.Rect(panel_x + int(40 * sx), panel_y + int(98 * sy), panel_w - int(80 * sx), int(30 * sy)),
                    max_lines=1,
                )

            name_lbl = body_font.render("Name", True, (150, 200, 255))
            pass_lbl = body_font.render("Password", True, (150, 200, 255))
            screen.blit(name_lbl, (name_rect.x, name_rect.y - int(26 * sy)))
            screen.blit(pass_lbl, (pass_rect.x, pass_rect.y - int(26 * sy)))

            _draw_input(screen, name_rect, name, active_field == "name", body_font, hidden=False)
            _draw_input(screen, pass_rect, password, active_field == "password", body_font, hidden=not show_password)
            
            show_pass_hover = show_pass_rect.collidepoint(mouse_pos)
            submit_hover = submit_btn.collidepoint(mouse_pos)
            back_hover = back_btn.collidepoint(mouse_pos)
            
            # Set cursor based on button hover
            hovering_control = show_pass_hover or submit_hover or back_hover
            
            _draw_button(
                screen,
                show_pass_rect,
                "Hide" if show_password else "Show",
                button_font,
                fill=(60, 60, 70),
                border=(180, 180, 200),
                hover=show_pass_hover
            )

            if state == "register":
                confirm_lbl = body_font.render("Confirm Password", True, (150, 200, 255))
                screen.blit(confirm_lbl, (confirm_rect.x, confirm_rect.y - int(26 * sy)))
                _draw_input(
                    screen,
                    confirm_rect,
                    confirm_password,
                    active_field == "confirm",
                    body_font,
                    hidden=not show_confirm_password,
                )
                
                show_confirm_hover = show_confirm_rect.collidepoint(mouse_pos)
                
                # Update cursor if show_confirm_password button is hovered
                hovering_control = hovering_control or show_confirm_hover
                
                _draw_button(
                    screen,
                    show_confirm_rect,
                    "Hide" if show_confirm_password else "Show",
                    button_font,
                    fill=(60, 60, 70),
                    border=(180, 180, 200),
                    hover=show_confirm_hover
                )

                draw_wrapped_text(
                    screen,
                    body_font,
                    "Rule: 8+ chars, upper, lower, number, symbol",
                    (150, 150, 180),
                    pygame.Rect(panel_x + int(40 * sx), panel_y + int(446 * sy), panel_w - int(80 * sx), int(42 * sy)),
                    line_gap=2,
                    max_lines=2,
                )

            current_cursor = apply_hover_cursor(
                hovering_control,
                hand_cursor,
                arrow_cursor,
                current_cursor,
            )

            _draw_button(screen, submit_btn, "Submit", button_font, fill=(30, 100, 50), border=(100, 255, 150), hover=submit_hover)
            _draw_button(screen, back_btn, "Back", button_font, fill=(50, 50, 60), border=(150, 150, 180), hover=back_hover)

        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if state == "choice":
                    if login_btn.collidepoint(event.pos):
                        state = "login"
                        active_field = "name"
                        name = ""
                        password = ""
                        confirm_password = ""
                        message = "Log in with your existing account"
                        message_color = (220, 220, 220)
                        show_password = False
                        show_confirm_password = False
                    elif register_btn.collidepoint(event.pos):
                        state = "register"
                        active_field = "name"
                        name = ""
                        password = ""
                        confirm_password = ""
                        message = "Create an account (no duplicate names)"
                        message_color = (220, 220, 220)
                        show_password = False
                        show_confirm_password = False
                    elif exit_btn.collidepoint(event.pos):
                        return None
                else:
                    if back_btn.collidepoint(event.pos):
                        state = "choice"
                        message = "Choose Login or Register"
                        message_color = (220, 220, 220)
                        continue

                    if show_pass_rect.collidepoint(event.pos):
                        show_password = not show_password
                        continue

                    if state == "register" and show_confirm_rect.collidepoint(event.pos):
                        show_confirm_password = not show_confirm_password
                        continue

                    if submit_btn.collidepoint(event.pos):
                        auth_name = submit_current()
                        if auth_name is not None:
                            return auth_name

                    if name_rect.collidepoint(event.pos):
                        active_field = "name"
                    elif pass_rect.collidepoint(event.pos):
                        active_field = "password"
                    elif state == "register" and confirm_rect.collidepoint(event.pos):
                        active_field = "confirm"

            if event.type == pygame.KEYDOWN and state != "choice":
                if event.key == pygame.K_ESCAPE:
                    state = "choice"
                    message = "Choose Login or Register"
                    message_color = (220, 220, 220)
                    continue

                if event.key == pygame.K_TAB:
                    if state == "register":
                        order = ["name", "password", "confirm"]
                    else:
                        order = ["name", "password"]
                    idx = order.index(active_field)
                    active_field = order[(idx + 1) % len(order)]
                    continue

                if event.key == pygame.K_RETURN:
                    auth_name = submit_current()
                    if auth_name is not None:
                        return auth_name
                    continue

                target = None
                if active_field == "name":
                    target = "name"
                elif active_field == "password":
                    target = "password"
                elif active_field == "confirm":
                    target = "confirm_password"

                if target is not None:
                    if event.key == pygame.K_BACKSPACE:
                        if target == "name":
                            name = name[:-1]
                        elif target == "password":
                            password = password[:-1]
                        else:
                            confirm_password = confirm_password[:-1]
                    elif event.unicode.isprintable() and len(event.unicode) == 1:
                        if target == "name" and len(name) < 20:
                            name += event.unicode
                        elif target == "password" and len(password) < 40:
                            password += event.unicode
                        elif target == "confirm_password" and len(confirm_password) < 40:
                            confirm_password += event.unicode

        clock.tick(60)
