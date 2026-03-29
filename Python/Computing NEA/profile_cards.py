import pygame

from Classes import Button
from ui_helpers import fit_text, draw_wrapped_text
from database import (
    create_connection,
    get_profile_card,
    get_friends,
    get_player_cosmetics,
    add_friend,
    set_profile_title,
    set_profile_badge,
)


pygame.init()


TITLES = [
    "Rookie Explorer",
    "Sky Runner",
    "Combo Hunter",
    "Boss Breaker",
    "Shadow Champion",
]

BADGES = ["none", "bronze", "silver", "gold", "neon"]


def profile_card_screen(player_name):
    screen = pygame.display.get_surface()
    if screen is None:
        info = pygame.display.Info()
        screen = pygame.display.set_mode((info.current_w, info.current_h))

    sw, sh = screen.get_width(), screen.get_height()
    title_font = pygame.font.SysFont("Arial", 40, bold=True)
    label_font = pygame.font.SysFont("Arial", 24)
    small_font = pygame.font.SysFont("Arial", 20)

    back_size = max(24, int(sw * 0.04))
    back_img = pygame.image.load("back button.jpg").convert_alpha()
    back_img = pygame.transform.scale(back_img, (back_size, back_size))
    back_button = Button(10, 10, back_img)

    panel = pygame.Rect(20, 76, min(sw - 40, 820), sh - 112)
    panel.centerx = sw // 2
    title_idx = 0
    badge_idx = 0
    friend_input = ""
    input_active = False

    message = ""
    msg_timer = 0.0

    conn = create_connection()
    if conn is None:
        return True

    clock = pygame.time.Clock()
    while True:
        dt = clock.tick(60) / 1000.0
        card = get_profile_card(player_name)
        friends = get_friends(player_name)
        cosmetics = get_player_cosmetics(player_name)
        trial_tokens = sorted(
            key for key, qty in cosmetics.items()
            if key.startswith("training_token_") and int(qty or 0) > 0
        )

        if card:
            if card.get("title") in TITLES:
                title_idx = TITLES.index(card.get("title"))
            if card.get("badge") in BADGES:
                badge_idx = BADGES.index(card.get("badge"))

        screen.fill((20, 26, 36))
        pygame.draw.rect(screen, (34, 44, 60), panel, border_radius=14)
        pygame.draw.rect(screen, (140, 170, 210), panel, 2, border_radius=14)

        title = title_font.render("Profile Card", True, (255, 230, 150))
        screen.blit(title, (panel.centerx - title.get_width() // 2, panel.y + 14))

        y = panel.y + 84
        lines = [
            f"Player: {player_name}",
            f"Title: {card.get('title', 'Rookie Explorer')}",
            f"Badge: {card.get('badge', 'none')}",
            f"Skin: {card.get('skin', 'default')}",
            f"Coins: {card.get('coins', 0)}",
            f"Best Score: {card.get('best_score', 0)}",
            f"Best Time: {card.get('best_time', '--')}",
        ]
        for ln in lines:
            s = label_font.render(fit_text(label_font, ln, panel.w - 52), True, (230, 230, 235))
            screen.blit(s, (panel.x + 26, y))
            y += 34

        # Cosmetic controls
        title_prev = pygame.Rect(panel.x + 26, y + 10, 36, 30)
        selector_w = min(320, panel.w - 120)
        title_next = pygame.Rect(panel.x + 26 + 44 + selector_w + 8, y + 10, 36, 30)
        title_row = pygame.Rect(panel.x + 70, y + 8, selector_w, 34)
        pygame.draw.rect(screen, (55, 66, 88), title_row, border_radius=7)
        pygame.draw.rect(screen, (140, 170, 220), title_row, 1, border_radius=7)
        pygame.draw.rect(screen, (70, 80, 96), title_prev, border_radius=6)
        pygame.draw.rect(screen, (70, 80, 96), title_next, border_radius=6)
        screen.blit(small_font.render("<", True, (255, 255, 255)), (title_prev.x + 12, title_prev.y + 3))
        screen.blit(small_font.render(">", True, (255, 255, 255)), (title_next.x + 11, title_next.y + 3))
        screen.blit(small_font.render(fit_text(small_font, TITLES[title_idx], title_row.w - 16), True, (220, 230, 255)), (title_row.x + 8, title_row.y + 6))

        y += 54
        badge_prev = pygame.Rect(panel.x + 26, y + 10, 36, 30)
        badge_next = pygame.Rect(panel.x + 26 + 44 + selector_w + 8, y + 10, 36, 30)
        badge_row = pygame.Rect(panel.x + 70, y + 8, selector_w, 34)
        pygame.draw.rect(screen, (55, 66, 88), badge_row, border_radius=7)
        pygame.draw.rect(screen, (140, 170, 220), badge_row, 1, border_radius=7)
        pygame.draw.rect(screen, (70, 80, 96), badge_prev, border_radius=6)
        pygame.draw.rect(screen, (70, 80, 96), badge_next, border_radius=6)
        screen.blit(small_font.render("<", True, (255, 255, 255)), (badge_prev.x + 12, badge_prev.y + 3))
        screen.blit(small_font.render(">", True, (255, 255, 255)), (badge_next.x + 11, badge_next.y + 3))
        screen.blit(small_font.render(fit_text(small_font, BADGES[badge_idx], badge_row.w - 16), True, (220, 230, 255)), (badge_row.x + 8, badge_row.y + 6))

        y += 62
        friend_lbl = small_font.render("Add Friend:", True, (220, 220, 220))
        screen.blit(friend_lbl, (panel.x + 26, y))
        friend_box_w = max(160, min(260, panel.w - 270))
        friend_box = pygame.Rect(panel.x + 130, y - 2, friend_box_w, 34)
        pygame.draw.rect(screen, (25, 32, 46), friend_box, border_radius=6)
        pygame.draw.rect(screen, (120, 145, 180), friend_box, 2 if input_active else 1, border_radius=6)
        friend_text = friend_input if friend_input else "friend name"
        friend_color = (255, 255, 255) if friend_input else (130, 130, 140)
        screen.blit(small_font.render(friend_text, True, friend_color), (friend_box.x + 8, friend_box.y + 6))

        add_btn = pygame.Rect(friend_box.right + 10, y - 2, 90, 34)
        pygame.draw.rect(screen, (44, 104, 64), add_btn, border_radius=6)
        pygame.draw.rect(screen, (140, 230, 165), add_btn, 2, border_radius=6)
        screen.blit(small_font.render("Add", True, (255, 255, 255)), (add_btn.x + 28, add_btn.y + 6))

        y += 56
        friends_title = small_font.render("Friends:", True, (220, 220, 220))
        screen.blit(friends_title, (panel.x + 26, y))
        friend_y = y + 28
        max_visible_friends = max(3, (panel.bottom - friend_y - 54) // 24)
        for i, fn in enumerate(friends[:max_visible_friends]):
            screen.blit(small_font.render(fit_text(small_font, f"- {fn}", panel.w - 66), True, (205, 215, 235)), (panel.x + 40, friend_y + i * 24))
        if len(friends) > max_visible_friends:
            more = small_font.render(f"... and {len(friends) - max_visible_friends} more", True, (165, 180, 210))
            screen.blit(more, (panel.x + 40, min(panel.bottom - 52, friend_y + max_visible_friends * 24)))

        tokens_text = "None"
        if trial_tokens:
            pretty = [t.replace("training_token_", "").replace("_", " ").title() for t in trial_tokens[:4]]
            tokens_text = ", ".join(pretty)
            if len(trial_tokens) > 4:
                tokens_text += f" (+{len(trial_tokens) - 4} more)"
        token_y = panel.bottom - 76
        token_lbl = small_font.render("Training Tokens:", True, (220, 220, 220))
        screen.blit(token_lbl, (panel.x + 26, token_y))
        token_val = small_font.render(fit_text(small_font, tokens_text, panel.w - 52), True, (190, 230, 200))
        screen.blit(token_val, (panel.x + 26, token_y + 24))

        if msg_timer > 0 and message:
            msg_timer = max(0.0, msg_timer - dt)
            draw_wrapped_text(screen, small_font, message, (255, 215, 130), pygame.Rect(panel.x + 24, panel.bottom - 46, panel.w - 48, 30), align="center", max_lines=2)

        back_button.draw()
        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                conn.close()
                return False
            if back_button.handle_event(event):
                conn.close()
                return True
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if title_prev.collidepoint(event.pos):
                    title_idx = (title_idx - 1) % len(TITLES)
                    set_profile_title(conn, player_name, TITLES[title_idx])
                elif title_next.collidepoint(event.pos):
                    title_idx = (title_idx + 1) % len(TITLES)
                    set_profile_title(conn, player_name, TITLES[title_idx])
                elif badge_prev.collidepoint(event.pos):
                    badge_idx = (badge_idx - 1) % len(BADGES)
                    set_profile_badge(conn, player_name, BADGES[badge_idx])
                elif badge_next.collidepoint(event.pos):
                    badge_idx = (badge_idx + 1) % len(BADGES)
                    set_profile_badge(conn, player_name, BADGES[badge_idx])
                elif friend_box.collidepoint(event.pos):
                    input_active = True
                elif add_btn.collidepoint(event.pos):
                    if friend_input.strip():
                        ok = add_friend(conn, player_name, friend_input.strip())
                        message = "Friend added" if ok else "Could not add friend"
                        msg_timer = 1.8
                        friend_input = ""
                else:
                    input_active = False
            if event.type == pygame.KEYDOWN and input_active:
                if event.key == pygame.K_BACKSPACE:
                    friend_input = friend_input[:-1]
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    if friend_input.strip():
                        ok = add_friend(conn, player_name, friend_input.strip())
                        message = "Friend added" if ok else "Could not add friend"
                        msg_timer = 1.8
                        friend_input = ""
                elif len(friend_input) < 20 and event.unicode.isprintable():
                    friend_input += event.unicode
