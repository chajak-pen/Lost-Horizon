import pygame
import random
import os
from Classes import Text, Button
from seasonal_events import get_active_event
from progression_hub import progression_hub_screen
from database import (
    create_connection,
    initialize_database,
    get_total_coins,
    SHOP_PRICE_INFLATION_CAP,
    SHOP_PRICE_INFLATION_RATE,
    SHOP_PRICE_INFLATION_STEP_COINS,
    subtract_total_coins,
    add_lives,
    add_powerup,
    add_total_coins,
    get_owned_skins,
    get_player_skin,
    set_player_skin,
    buy_skin,
)

pygame.init()

initialize_database()

info = pygame.display.Info()
screen_width, screen_height = info.current_w, info.current_h


def _load_screen_background(size, primary_name):
    sw, sh = size
    for path in (primary_name, "background.jpg", "background.png"):
        if os.path.exists(path):
            try:
                img = pygame.image.load(path).convert_alpha()
                return pygame.transform.scale(img, (sw, sh))
            except Exception:
                continue
    fallback = pygame.Surface((sw, sh))
    fallback.fill((18, 22, 30))
    return fallback


def blackjack_screen(player_name, conn, get_balance=None, add_balance=None, subtract_balance=None, balance_label="Coins", result_logger=None):
    """Blackjack vs dealer AI. Returns True to go back to shop, False to quit."""

    screen = pygame.display.get_surface()
    sw, sh = screen.get_width(), screen.get_height()
    sx, sy = sw / 1000.0, sh / 600.0

    background = _load_screen_background((sw, sh), "blackjack_background.png")

    back_size = max(24, int(sw * 0.04))
    back_img  = pygame.image.load("back button.jpg").convert_alpha()
    back_img  = pygame.transform.scale(back_img, (back_size, back_size))
    back_button = Button(10, 10, back_img)

    title_font  = pygame.font.SysFont("Arial", max(20, int(40 * sy)), bold=True)
    card_font   = pygame.font.SysFont("Arial", max(14, int(26 * sy)), bold=True)
    suit_font   = pygame.font.SysFont("Arial", max(10, int(18 * sy)))
    label_font  = pygame.font.SysFont("Arial", max(12, int(22 * sy)))
    msg_font    = pygame.font.SysFont("Arial", max(14, int(28 * sy)), bold=True)
    btn_font    = pygame.font.SysFont("Arial", max(12, int(22 * sy)))

    wallet_get = get_balance or get_total_coins
    wallet_add = add_balance or add_total_coins
    wallet_subtract = subtract_balance or subtract_total_coins
    balance_word = str(balance_label)
    balance_word_lower = balance_word.lower()

    CARD_W = max(52, int(72 * sx))
    CARD_H = max(76, int(104 * sy))
    CARD_GAP = max(8, int(12 * sx))

    SUITS  = ["♥", "♦", "♠", "♣"]
    RANKS  = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
    RED_SUITS = {"♥", "♦"}

    def make_deck():
        deck = [(r, s) for s in SUITS for r in RANKS]
        random.shuffle(deck)
        return deck

    def card_value(rank):
        if rank in ("J", "Q", "K"):
            return 10
        if rank == "A":
            return 11
        return int(rank)

    def hand_total(hand):
        total = sum(card_value(r) for r, _ in hand)
        aces  = sum(1 for r, _ in hand if r == "A")
        while total > 21 and aces:
            total -= 10
            aces  -= 1
        return total

    def is_soft_17(hand):
        """True if dealer has exactly 17 with an ace counted as 11."""
        total = sum(card_value(r) for r, _ in hand)
        aces  = sum(1 for r, _ in hand if r == "A")
        while total > 21 and aces:
            total -= 10
            aces  -= 1
        return total == 17 and aces > 0

    def draw_card(surf, card, x, y, face_down=False):
        if face_down:
            pygame.draw.rect(surf, (30, 60, 160), (x, y, CARD_W, CARD_H), border_radius=6)
            pygame.draw.rect(surf, (180, 200, 255), (x, y, CARD_W, CARD_H), 2, border_radius=6)
            # Crosshatch pattern
            for i in range(0, CARD_W, 8):
                pygame.draw.line(surf, (50, 80, 180), (x + i, y), (x, y + i))
                pygame.draw.line(surf, (50, 80, 180), (x + CARD_W - i, y + CARD_H), (x + CARD_W, y + CARD_H - i))
            return
        rank, suit = card
        color = (200, 30, 30) if suit in RED_SUITS else (15, 15, 15)
        pygame.draw.rect(surf, (245, 240, 220), (x, y, CARD_W, CARD_H), border_radius=6)
        pygame.draw.rect(surf, (100, 90, 70), (x, y, CARD_W, CARD_H), 2, border_radius=6)
        # Top-left rank + suit
        rank_s = card_font.render(rank, True, color)
        suit_s = suit_font.render(suit, True, color)
        surf.blit(rank_s, (x + 4, y + 2))
        surf.blit(suit_s, (x + 4, y + 2 + rank_s.get_height()))
        # Centre suit
        big_suit = title_font.render(suit, True, color)
        surf.blit(big_suit, (x + (CARD_W - big_suit.get_width()) // 2,
                              y + (CARD_H - big_suit.get_height()) // 2))

    def draw_hand(surf, hand, start_x, y, hide_second=False):
        for i, card in enumerate(hand):
            cx = start_x + i * (CARD_W + CARD_GAP)
            face_down = hide_second and i == 1
            draw_card(surf, card, cx, y, face_down=face_down)

    def hand_start_x(hand_len):
        total_w = hand_len * CARD_W + (hand_len - 1) * CARD_GAP
        return (sw - total_w) // 2

    def draw_btn(surf, rect, text, active=True, color=(40, 100, 40)):
        border = (130, 220, 130)
        if not active:
            color  = (55, 55, 55)
            border = (90, 90, 90)
        pygame.draw.rect(surf, color, rect, border_radius=9)
        pygame.draw.rect(surf, border, rect, 2, border_radius=9)
        lbl = btn_font.render(text, True, (255, 255, 255))
        surf.blit(lbl, (rect.x + (rect.w - lbl.get_width()) // 2,
                        rect.y + (rect.h - lbl.get_height()) // 2))

    # Button geometry
    btn_h = max(38, int(52 * sy))
    btn_w = max(90, int(120 * sx))
    btn_y = int(sh * 0.87)
    btn_gap = max(10, int(16 * sx))
    total_btns_w = 3 * btn_w + 2 * btn_gap
    bx = (sw - total_btns_w) // 2
    hit_rect    = pygame.Rect(bx,                       btn_y, btn_w, btn_h)
    stand_rect  = pygame.Rect(bx + btn_w + btn_gap,     btn_y, btn_w, btn_h)
    double_rect = pygame.Rect(bx + 2*(btn_w + btn_gap), btn_y, btn_w, btn_h)

    # Bet controls
    bet_amounts = [5, 10, 20, 50]
    bet_idx = 0         # -1 means custom
    bet_w = max(60, int(80 * sx))
    bet_h = btn_h
    deal_w = max(90, int(120 * sx))
    bet_row_w = len(bet_amounts) * (bet_w + btn_gap) - btn_gap + btn_gap + deal_w
    bet_row_x = (sw - bet_row_w) // 2
    bet_rects = [pygame.Rect(bet_row_x + i * (bet_w + btn_gap), btn_y, bet_w, bet_h)
                 for i in range(len(bet_amounts))]
    deal_rect = pygame.Rect(bet_row_x + len(bet_amounts) * (bet_w + btn_gap), btn_y, deal_w, bet_h)
    new_game_rect = pygame.Rect((sw - deal_w) // 2, btn_y, deal_w, btn_h)

    # Custom bet input box (sits above the preset buttons)
    cust_box_w = max(130, int(180 * sx))
    cust_box_h = max(32, int(42 * sy))
    cust_box_y = btn_y - cust_box_h - max(6, int(8 * sy))
    cust_box_x = (sw - cust_box_w) // 2
    cust_box_rect  = pygame.Rect(cust_box_x, cust_box_y, cust_box_w, cust_box_h)
    cust_input     = ""   # raw string while typing
    cust_active    = False  # whether the custom input box has keyboard focus

    # Game state  "betting" | "playing" | "dealer" | "result"
    state       = "betting"
    deck        = make_deck()
    player_hand = []
    dealer_hand = []
    bet         = bet_amounts[bet_idx]
    message     = ""
    msg_color   = (220, 220, 220)
    last_result = ""

    # dealer animation
    dealer_delay = 0.0  # seconds until next dealer card
    DEALER_CARD_DELAY = 0.7

    def deal_new_game():
        nonlocal deck, player_hand, dealer_hand, state, message, msg_color, dealer_delay
        if len(deck) < 15:
            deck = make_deck()
        player_hand = [deck.pop(), deck.pop()]
        dealer_hand = [deck.pop(), deck.pop()]
        state = "playing"
        message = ""
        msg_color = (220, 220, 220)
        dealer_delay = 0.0
        # Check player blackjack immediately
        if hand_total(player_hand) == 21:
            state = "dealer"
            dealer_delay = DEALER_CARD_DELAY

    def resolve():
        nonlocal state, message, msg_color, last_result
        p = hand_total(player_hand)
        d = hand_total(dealer_hand)
        state = "result"
        payout = 0
        if p == 21 and len(player_hand) == 2 and not (d == 21 and len(dealer_hand) == 2):
            winnings = int(bet * 2.5)
            wallet_add(conn, player_name, winnings)
            payout = winnings
            message = f"Blackjack!  +{winnings} {balance_word_lower}"
            msg_color = (255, 220, 0)
            last_result = "blackjack"
        elif p > 21:
            message = f"Bust!  -{bet} {balance_word_lower}"
            msg_color = (210, 80, 80)
            last_result = "lose"
        elif d > 21:
            payout = bet * 2
            wallet_add(conn, player_name, payout)
            message = f"Dealer busts!  +{payout} {balance_word_lower}"
            msg_color = (130, 230, 130)
            last_result = "win"
        elif p > d:
            payout = bet * 2
            wallet_add(conn, player_name, payout)
            message = f"You win!  +{payout} {balance_word_lower}"
            msg_color = (130, 230, 130)
            last_result = "win"
        elif d > p:
            message = f"Dealer wins.  -{bet} {balance_word_lower}"
            msg_color = (210, 80, 80)
            last_result = "lose"
        else:
            payout = bet
            wallet_add(conn, player_name, bet)
            message = f"Push — bet returned"
            msg_color = (200, 200, 100)
            last_result = "push"
        if callable(result_logger):
            try:
                result_logger('blackjack', int(bet), int(payout))
            except Exception:
                pass

    clock = pygame.time.Clock()
    running = True
    while running:
        dt = clock.tick(60) / 1000.0

        # --- Dealer AI animation ---
        if state == "dealer":
            dealer_delay -= dt
            if dealer_delay <= 0:
                d_total = hand_total(dealer_hand)
                # Dealer hits on hard <=16 or soft 17
                if d_total < 17 or (d_total == 17 and is_soft_17(dealer_hand)):
                    if len(deck) == 0:
                        deck = make_deck()
                    dealer_hand.append(deck.pop())
                    dealer_delay = DEALER_CARD_DELAY
                else:
                    resolve()

        # --- Draw ---
        screen.blit(background, (0, 0))

        # semi-transparent table overlay
        table = pygame.Surface((sw, sh), pygame.SRCALPHA)
        table.fill((0, 60, 0, 120))
        screen.blit(table, (0, 0))

        # Title + coins
        title_s = title_font.render("Blackjack", True, (255, 220, 0))
        screen.blit(title_s, ((sw - title_s.get_width()) // 2, int(sh * 0.02)))
        coins_now = wallet_get(conn, player_name)
        coins_s = label_font.render(f"{balance_word}: {coins_now}", True, (255, 255, 0))
        screen.blit(coins_s, (sw - coins_s.get_width() - 18, 14))

        # Dealer area
        dealer_label = label_font.render(
            f"Dealer  ({hand_total(dealer_hand) if state not in ('playing',) else '?'})",
            True, (220, 220, 220)
        )
        screen.blit(dealer_label, ((sw - dealer_label.get_width()) // 2, int(sh * 0.10)))
        if dealer_hand:
            hide = (state == "playing")
            draw_hand(screen, dealer_hand, hand_start_x(len(dealer_hand)), int(sh * 0.155), hide_second=hide)

        # Player area
        player_total = hand_total(player_hand)
        player_label = label_font.render(f"You  ({player_total})", True, (220, 220, 220))
        screen.blit(player_label, ((sw - player_label.get_width()) // 2, int(sh * 0.50)))
        if player_hand:
            draw_hand(screen, player_hand, hand_start_x(len(player_hand)), int(sh * 0.545))

        # Message
        if message:
            msg_s = msg_font.render(message, True, msg_color)
            screen.blit(msg_s, ((sw - msg_s.get_width()) // 2, int(sh * 0.81)))

        # Buttons
        if state == "betting":
            # Custom bet input box
            box_border = (255, 220, 0) if cust_active else (160, 160, 160)
            pygame.draw.rect(screen, (20, 20, 20), cust_box_rect, border_radius=7)
            pygame.draw.rect(screen, box_border, cust_box_rect, 2, border_radius=7)
            cust_hint = cust_input if cust_input else "Custom bet..."
            cust_color = (255, 255, 255) if cust_input else (120, 120, 120)
            cust_surf = btn_font.render(cust_hint, True, cust_color)
            screen.blit(cust_surf, (cust_box_rect.x + 8,
                                     cust_box_rect.y + (cust_box_rect.h - cust_surf.get_height()) // 2))
            cust_lbl = label_font.render("or type a custom bet:", True, (200, 200, 200))
            screen.blit(cust_lbl, (cust_box_rect.x, cust_box_rect.y - int(22 * sy)))

            bet_label = label_font.render("Quick pick:", True, (220, 220, 220))
            screen.blit(bet_label, (bet_row_x, btn_y - int(26 * sy)))
            for i, b_rect in enumerate(bet_rects):
                selected = (i == bet_idx and not cust_active and not cust_input)
                draw_btn(screen, b_rect, f"{bet_amounts[i]}",
                         active=coins_now >= bet_amounts[i],
                         color=(60, 120, 60) if selected else (40, 80, 40))
            can_deal = bet > 0 and coins_now >= bet
            draw_btn(screen, deal_rect, "Deal", active=can_deal, color=(30, 80, 130))
        elif state == "playing":
            can_double = coins_now >= bet and len(player_hand) == 2
            draw_btn(screen, hit_rect,    "Hit",    active=True)
            draw_btn(screen, stand_rect,  "Stand",  active=True,  color=(120, 60, 30))
            draw_btn(screen, double_rect, "Double", active=can_double, color=(100, 50, 120))
            bet_s = label_font.render(f"Bet: {bet}", True, (255, 220, 100))
            screen.blit(bet_s, (hit_rect.x, btn_y - int(24 * sy)))
        elif state == "dealer":
            bet_s = label_font.render(f"Bet: {bet}  —  Dealer's turn...", True, (220, 200, 120))
            screen.blit(bet_s, ((sw - bet_s.get_width()) // 2, btn_y - int(24 * sy)))
        elif state == "result":
            draw_btn(screen, new_game_rect, "New Game", active=True, color=(30, 80, 130))

        back_button.draw()
        pygame.display.update()

        # --- Events ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if back_button.handle_event(event):
                return True

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos

                if state == "betting":
                    # Toggle custom input focus
                    cust_active = cust_box_rect.collidepoint(pos)
                    for i, b_rect in enumerate(bet_rects):
                        if b_rect.collidepoint(pos) and coins_now >= bet_amounts[i]:
                            bet_idx = i
                            bet = bet_amounts[bet_idx]
                            cust_input = ""
                            cust_active = False
                    if deal_rect.collidepoint(pos) and bet > 0 and coins_now >= bet:
                        wallet_subtract(conn, player_name, bet)
                        deal_new_game()

                elif state == "playing":
                    if hit_rect.collidepoint(pos):
                        if len(deck) == 0:
                            deck = make_deck()
                        player_hand.append(deck.pop())
                        if hand_total(player_hand) > 21:
                            resolve()
                        elif hand_total(player_hand) == 21:
                            state = "dealer"
                            dealer_delay = DEALER_CARD_DELAY

                    elif stand_rect.collidepoint(pos):
                        state = "dealer"
                        dealer_delay = DEALER_CARD_DELAY

                    elif double_rect.collidepoint(pos) and coins_now >= bet and len(player_hand) == 2:
                        wallet_subtract(conn, player_name, bet)
                        bet *= 2
                        if len(deck) == 0:
                            deck = make_deck()
                        player_hand.append(deck.pop())
                        if hand_total(player_hand) > 21:
                            resolve()
                        else:
                            state = "dealer"
                            dealer_delay = DEALER_CARD_DELAY

                elif state == "result":
                    if new_game_rect.collidepoint(pos):
                        cust_input = ""
                        cust_active = False
                        bet_idx = max(0, bet_idx)
                        bet = bet_amounts[bet_idx]
                        state = "betting"
                        player_hand = []
                        dealer_hand = []
                        message = ""

            if event.type == pygame.KEYDOWN and state == "betting" and cust_active:
                if event.key == pygame.K_BACKSPACE:
                    cust_input = cust_input[:-1]
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    cust_active = False
                elif event.unicode.isdigit() and len(cust_input) < 6:
                    cust_input += event.unicode
                try:
                    v = int(cust_input) if cust_input else 0
                    if v > 0:
                        bet = min(v, coins_now)
                        bet_idx = -1
                    else:
                        bet = bet_amounts[max(0, bet_idx)] if bet_idx >= 0 else 0
                except ValueError:
                    pass

    return True


def roulette_screen(player_name, conn, get_balance=None, add_balance=None, subtract_balance=None, balance_label="Coins", result_logger=None):
    """Roulette mini-game. Returns True to go back to shop, False to quit."""

    screen = pygame.display.get_surface()
    sw, sh = screen.get_width(), screen.get_height()
    sx, sy = sw / 1000.0, sh / 600.0

    background = _load_screen_background((sw, sh), "roulette_background.png")

    back_size = max(24, int(sw * 0.04))
    back_img  = pygame.image.load("back button.jpg").convert_alpha()
    back_img  = pygame.transform.scale(back_img, (back_size, back_size))
    back_button = Button(10, 10, back_img)

    title_font = pygame.font.SysFont("Arial", max(20, int(40 * sy)), bold=True)
    label_font = pygame.font.SysFont("Arial", max(12, int(22 * sy)))
    msg_font   = pygame.font.SysFont("Arial", max(14, int(26 * sy)), bold=True)
    btn_font   = pygame.font.SysFont("Arial", max(11, int(20 * sy)))
    num_font   = pygame.font.SysFont("Arial", max(9,  int(15 * sy)), bold=True)

    wallet_get = get_balance or get_total_coins
    wallet_add = add_balance or add_total_coins
    wallet_subtract = subtract_balance or subtract_total_coins
    balance_word = str(balance_label)
    balance_word_lower = balance_word.lower()

    import math

    # Roulette wheel numbers 0-36, alternating red/black (0 is green)
    WHEEL_ORDER = [0,32,15,19,4,21,2,25,17,34,6,27,13,36,11,30,8,23,10,5,24,16,33,1,20,14,31,9,22,18,29,7,28,12,35,3,26]
    RED_NUMS    = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
    def num_color(n):
        if n == 0: return (0, 140, 0)
        return (180, 20, 20) if n in RED_NUMS else (20, 20, 20)

    # Bet types
    BET_TYPES = [
        ("Red",    "Even money (×2)",  5),
        ("Black",  "Even money (×2)",  5),
        ("Odd",    "Even money (×2)",  5),
        ("Even",   "Even money (×2)",  5),
        ("1-18",   "Even money (×2)",  5),
        ("19-36",  "Even money (×2)",  5),
        ("1st 12", "2:1 payout (×3)",  5),
        ("2nd 12", "2:1 payout (×3)",  5),
        ("3rd 12", "2:1 payout (×3)",  5),
    ]

    def check_win(bet_name, result):
        if bet_name == "Red":    return result in RED_NUMS
        if bet_name == "Black":  return result not in RED_NUMS and result != 0
        if bet_name == "Odd":    return result != 0 and result % 2 == 1
        if bet_name == "Even":   return result != 0 and result % 2 == 0
        if bet_name == "1-18":   return 1 <= result <= 18
        if bet_name == "19-36":  return 19 <= result <= 36
        if bet_name == "1st 12": return 1 <= result <= 12
        if bet_name == "2nd 12": return 13 <= result <= 24
        if bet_name == "3rd 12": return 25 <= result <= 36
        return False

    def payout_multiplier(bet_name):
        return 3 if "12" in bet_name else 2

    # Layout
    WHEEL_R   = max(100, int(min(sw, sh) * 0.21))
    wheel_cx  = sw // 2
    wheel_cy  = int(sh * 0.36)

    # Bet grid below wheel
    bet_cols   = 3
    bet_rows   = (len(BET_TYPES) + bet_cols - 1) // bet_cols
    b_w        = max(80, int(110 * sx))
    b_h        = max(30, int(42 * sy))
    b_gap      = max(6,  int(10 * sx))
    grid_w     = bet_cols * b_w + (bet_cols - 1) * b_gap
    grid_x     = (sw - grid_w) // 2
    grid_y     = int(sh * 0.62)

    # Bet amount selector
    bet_amounts = [5, 10, 20]
    bet_idx     = 0

    # Custom bet input (roulette)
    cust_box_w  = max(110, int(150 * sx))
    cust_box_h  = max(30,  int(40  * sy))

    # Spin button
    spin_w = max(110, int(150 * sx))
    spin_h = max(34, int(46 * sy))
    spin_y = int(sh * 0.90)
    spin_rect  = pygame.Rect((sw - spin_w) // 2, spin_y, spin_w, spin_h)

    # Amount buttons left of spin
    amt_w    = max(44, int(60 * sx))
    amt_h    = spin_h
    amt_gap  = max(6, int(8 * sx))
    amt_total_w = len(bet_amounts) * amt_w + (len(bet_amounts) - 1) * amt_gap
    amt_x0   = spin_rect.left - amt_total_w - max(14, int(20 * sx))
    amt_rects = [pygame.Rect(amt_x0 + i * (amt_w + amt_gap), spin_y, amt_w, amt_h)
                 for i in range(len(bet_amounts))]

    # Custom bet input box (placed above the amount buttons)
    cust_box_rect = pygame.Rect(amt_x0, spin_y - cust_box_h - max(4, int(6 * sy)),
                                 amt_total_w, cust_box_h)
    cust_input = ""
    cust_active = False
    selected_bet   = None   # index into BET_TYPES
    state          = "betting"   # betting | spinning | result
    spin_angle     = 0.0
    spin_speed     = 0.0
    spin_decel     = 0.0
    result_num     = 0
    message        = "Place your bet then spin!"
    msg_color      = (220, 220, 220)
    staked_amount  = 0

    def start_spin():
        nonlocal state, spin_speed, spin_decel, spin_angle
        state       = "spinning"
        spin_speed  = random.uniform(900, 1200)   # deg/s
        spin_decel  = random.uniform(180, 240)    # deg/s²

    def draw_wheel(angle_deg):
        n = len(WHEEL_ORDER)
        slice_angle = 360.0 / n
        for i, num in enumerate(WHEEL_ORDER):
            start_a = math.radians(angle_deg + i * slice_angle - slice_angle / 2)
            end_a   = math.radians(angle_deg + i * slice_angle + slice_angle / 2)
            color   = num_color(num)
            points  = [(wheel_cx, wheel_cy)]
            steps   = max(4, int(slice_angle))
            for s in range(steps + 1):
                a = start_a + (end_a - start_a) * s / steps
                points.append((wheel_cx + math.cos(a) * WHEEL_R,
                                wheel_cy + math.sin(a) * WHEEL_R))
            if len(points) >= 3:
                pygame.draw.polygon(screen, color, points)
                pygame.draw.polygon(screen, (60, 60, 60), points, 1)
            # number label
            mid_a = (start_a + end_a) / 2
            lx = wheel_cx + math.cos(mid_a) * WHEEL_R * 0.72
            ly = wheel_cy + math.sin(mid_a) * WHEEL_R * 0.72
            ns = num_font.render(str(num), True, (255, 255, 255))
            # rotate label to align with slice
            ns_rot = pygame.transform.rotate(ns, -math.degrees((start_a + end_a) / 2))
            screen.blit(ns_rot, (lx - ns_rot.get_width() // 2, ly - ns_rot.get_height() // 2))
        # rim
        pygame.draw.circle(screen, (180, 150, 80), (wheel_cx, wheel_cy), WHEEL_R, 4)
        pygame.draw.circle(screen, (60, 40, 10),   (wheel_cx, wheel_cy), max(12, WHEEL_R // 8))
        # pointer triangle at top
        tip   = (wheel_cx, wheel_cy - WHEEL_R - 4)
        ptr_w = max(10, WHEEL_R // 8)
        pygame.draw.polygon(screen, (255, 80, 80),
                            [(tip[0], tip[1]),
                             (tip[0] - ptr_w, tip[1] - ptr_w * 2),
                             (tip[0] + ptr_w, tip[1] - ptr_w * 2)])

    def angle_to_result(angle_deg):
        # The pointer is at -90° (top). Find which slice is under the pointer.
        n = len(WHEEL_ORDER)
        slice_angle = 360.0 / n
        # normalise angle so 0° is "right"; pointer is at top = -90°
        pointer_in_wheel = (-90 - angle_deg) % 360
        # Each slice i is CENTRED at i*slice_angle, so use round() not int()
        # int() floors and picks the previous slice when the pointer is past a
        # slice's centre, causing the result to appear one slice to the left.
        idx = round(pointer_in_wheel / slice_angle) % n
        return WHEEL_ORDER[idx]

    def draw_btn_box(rect, text, active=True, selected=False,
                     fill=(40, 40, 80), sel_fill=(100, 60, 180), border=(120, 120, 200)):
        if not active:
            fill, border = (50, 50, 50), (80, 80, 80)
        elif selected:
            fill = sel_fill
        pygame.draw.rect(screen, fill, rect, border_radius=7)
        pygame.draw.rect(screen, border, rect, 2, border_radius=7)
        lbl = btn_font.render(text, True, (255, 255, 255))
        screen.blit(lbl, (rect.x + (rect.w - lbl.get_width()) // 2,
                          rect.y + (rect.h - lbl.get_height()) // 2))

    clock = pygame.time.Clock()
    running = True
    while running:
        dt = clock.tick(60) / 1000.0

        # Spin physics
        if state == "spinning":
            spin_angle += spin_speed * dt
            spin_speed  = max(0.0, spin_speed - spin_decel * dt)
            if spin_speed <= 0:
                result_num = angle_to_result(spin_angle)
                state      = "result"
                bet_name   = BET_TYPES[selected_bet][0]
                bet_cost   = staked_amount
                payout = 0
                if check_win(bet_name, result_num):
                    mult     = payout_multiplier(bet_name)
                    winnings = bet_cost * mult
                    payout = winnings
                    wallet_add(conn, player_name, winnings)
                    message   = f"Ball landed on {result_num}!  {bet_name} wins!  +{winnings} {balance_word_lower}"
                    msg_color = (130, 230, 130)
                else:
                    message   = f"Ball landed on {result_num}.  {bet_name} loses.  -{bet_cost} {balance_word_lower}"
                    msg_color = (210, 80, 80)
                if callable(result_logger):
                    try:
                        result_logger('roulette', int(bet_cost), int(payout))
                    except Exception:
                        pass

        # Draw
        screen.blit(background, (0, 0))
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 30, 0, 110))
        screen.blit(overlay, (0, 0))

        title_s = title_font.render("Roulette", True, (255, 220, 0))
        screen.blit(title_s, ((sw - title_s.get_width()) // 2, int(sh * 0.02)))

        coins_now = wallet_get(conn, player_name)
        coins_s   = label_font.render(f"{balance_word}: {coins_now}", True, (255, 255, 0))
        screen.blit(coins_s, (sw - coins_s.get_width() - 18, 14))

        draw_wheel(spin_angle)

        # Bet grid
        bet_label = label_font.render("Choose a bet:", True, (220, 220, 220))
        screen.blit(bet_label, (grid_x, grid_y - int(24 * sy)))
        for i, (bname, bdesc, _) in enumerate(BET_TYPES):
            col = i % bet_cols
            row = i // bet_cols
            r   = pygame.Rect(grid_x + col * (b_w + b_gap),
                               grid_y + row * (b_h + b_gap), b_w, b_h)
            draw_btn_box(r, bname, active=(state == "betting"),
                         selected=(i == selected_bet))

        # Amount selector + spin button
        # Custom bet input box
        cust_border = (255, 200, 0) if cust_active else (120, 120, 180)
        pygame.draw.rect(screen, (25, 25, 50), cust_box_rect, border_radius=6)
        pygame.draw.rect(screen, cust_border, cust_box_rect, 2, border_radius=6)
        cust_display = cust_input if cust_input else ("Custom amount..." if state == "betting" else "")
        cust_color   = (255, 255, 200) if cust_input else (140, 140, 140)
        cust_s = btn_font.render(cust_display, True, cust_color)
        screen.blit(cust_s, (cust_box_rect.x + 6,
                              cust_box_rect.y + (cust_box_rect.h - cust_s.get_height()) // 2))

        amt_label = label_font.render("Quick bet:", True, (220, 220, 220))
        screen.blit(amt_label, (amt_x0, spin_y - int(22 * sy)))
        for i, a_rect in enumerate(amt_rects):
            draw_btn_box(a_rect, str(bet_amounts[i]),
                         active=(state == "betting"),
                         selected=(i == bet_idx and not cust_active and not cust_input),
                         fill=(30, 60, 100), sel_fill=(60, 120, 200), border=(80, 140, 220))

        # Determine effective bet
        try:
            effective_bet = int(cust_input) if cust_input else bet_amounts[bet_idx]
        except ValueError:
            effective_bet = bet_amounts[bet_idx]

        can_spin = state == "betting" and selected_bet is not None and coins_now >= effective_bet and effective_bet > 0
        s_fill   = (30, 100, 30) if can_spin else (55, 55, 55)
        s_border = (130, 220, 130) if can_spin else (90, 90, 90)
        pygame.draw.rect(screen, s_fill,   spin_rect, border_radius=9)
        pygame.draw.rect(screen, s_border, spin_rect, 2, border_radius=9)
        spin_lbl = btn_font.render("SPIN", True, (255, 255, 255))
        screen.blit(spin_lbl, (spin_rect.x + (spin_rect.w - spin_lbl.get_width()) // 2,
                                spin_rect.y + (spin_rect.h - spin_lbl.get_height()) // 2))

        if state == "result":
            # "New Spin" button replaces hint
            ns_rect = pygame.Rect(spin_rect.right + max(10, int(14 * sx)), spin_y, spin_w, spin_h)
            draw_btn_box(ns_rect, "New Spin", fill=(30, 80, 130), border=(80, 160, 220))

        if message:
            ms = msg_font.render(message, True, msg_color)
            screen.blit(ms, ((sw - ms.get_width()) // 2, int(sh * 0.555)))

        back_button.draw()
        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if back_button.handle_event(event):
                return True

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos

                if state == "betting":
                    # Custom input box focus
                    cust_active = cust_box_rect.collidepoint(pos)
                    # Bet type selection
                    for i in range(len(BET_TYPES)):
                        col = i % bet_cols
                        row = i // bet_cols
                        r   = pygame.Rect(grid_x + col * (b_w + b_gap),
                                           grid_y + row * (b_h + b_gap), b_w, b_h)
                        if r.collidepoint(pos):
                            selected_bet = i
                    # Preset amount selection
                    for i, a_rect in enumerate(amt_rects):
                        if a_rect.collidepoint(pos) and coins_now >= bet_amounts[i]:
                            bet_idx = i
                            cust_input = ""
                            cust_active = False
                    # Spin
                    if spin_rect.collidepoint(pos) and can_spin:
                        staked_amount = effective_bet
                        wallet_subtract(conn, player_name, effective_bet)
                        start_spin()

            if event.type == pygame.KEYDOWN and state == "betting" and cust_active:
                if event.key == pygame.K_BACKSPACE:
                    cust_input = cust_input[:-1]
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    cust_active = False
                elif event.unicode.isdigit() and len(cust_input) < 6:
                    cust_input += event.unicode

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                if state == "result":
                    ns_rect = pygame.Rect(spin_rect.right + max(10, int(14 * sx)), spin_y, spin_w, spin_h)
                    if ns_rect.collidepoint(pos):
                        selected_bet = None
                        cust_input   = ""
                        cust_active  = False
                        state        = "betting"
                        message      = "Place your bet then spin!"
                        msg_color    = (220, 220, 220)

    return True


def slot_machine_screen(player_name, conn, get_balance=None, add_balance=None, subtract_balance=None, balance_label="Coins", result_logger=None):
    """Separate slot-machine screen. Returns True to go back to shop, False to quit."""
    SPIN_COST = 5

    screen = pygame.display.get_surface()
    sw, sh = screen.get_width(), screen.get_height()
    sx, sy = sw / 1000.0, sh / 600.0

    background = _load_screen_background((sw, sh), "slot_machine_background.png")

    # Reel size/placement tuned to the extracted slot background panel.
    sym_size = max(58, int(min(sw, sh) * 0.135))

    # Symbols use the existing powerup images
    raw_symbols = [
        ("float",         "float_power.png"),
        ("invincibility", "invincibility.png"),
        ("fire",          "fire_flower.png"),
        ("life",          "life.png"),
    ]
    symbols = []
    for name, path in raw_symbols:
        img = pygame.image.load(path).convert_alpha()
        img = pygame.transform.scale(img, (sym_size, sym_size))
        symbols.append((name, img))

    # Coin jackpot symbol — drawn procedurally (no image file needed)
    coin_surf = pygame.Surface((sym_size, sym_size), pygame.SRCALPHA)
    pygame.draw.circle(coin_surf, (255, 210, 0), (sym_size // 2, sym_size // 2), sym_size // 2 - 2)
    pygame.draw.circle(coin_surf, (200, 160, 0), (sym_size // 2, sym_size // 2), sym_size // 2 - 2, 3)
    _coin_font = pygame.font.SysFont("Arial", max(20, int(sym_size * 0.45)), bold=True)
    _coin_lbl = _coin_font.render("$", True, (120, 80, 0))
    coin_surf.blit(_coin_lbl, ((sym_size - _coin_lbl.get_width()) // 2, (sym_size - _coin_lbl.get_height()) // 2))
    symbols.append(("coin", coin_surf))

    title_font = pygame.font.SysFont("Arial", max(22, int(46 * sy)), bold=True)
    font      = pygame.font.SysFont("Arial", max(14, int(28 * sy)))

    wallet_get = get_balance or get_total_coins
    wallet_add = add_balance or add_total_coins
    wallet_subtract = subtract_balance or subtract_total_coins
    balance_word = str(balance_label)
    balance_word_lower = balance_word.lower()

    # Back button
    back_size = max(24, int(sw * 0.04))
    back_img = pygame.image.load("back button.jpg").convert_alpha()
    back_img = pygame.transform.scale(back_img, (back_size, back_size))
    back_button = Button(10, 10, back_img)

    # Reel layout: anchors line up with the machine window area in the background.
    REEL_COUNT = 3
    reel_spacing = max(int(sw * 0.11), int(sym_size * 1.08))
    machine_center_x = int(sw * 0.5)
    machine_center_y = int(sh * 0.49)
    reel_xs = [
        machine_center_x - reel_spacing - sym_size // 2,
        machine_center_x - sym_size // 2,
        machine_center_x + reel_spacing - sym_size // 2,
    ]
    reel_y = machine_center_y - sym_size // 2
    box_pad    = max(8, int(12 * sx))
    box_w      = sym_size + box_pad * 2
    box_h      = sym_size + box_pad * 2

    # Spin button
    spin_w = max(150, int(220 * sx))
    spin_h = max(42, int(58 * sy))
    spin_rect = pygame.Rect((sw - spin_w) // 2, int(sh * 0.89), spin_w, spin_h)

    # State
    current = [0, 0, 0]         # symbol index currently shown in each reel
    final   = [0, 0, 0]         # target result
    spinning      = False
    stopped       = [False, False, False]
    spin_start    = 0.0
    cycle_timers  = [0.0, 0.0, 0.0]
    SPIN_DUR_BASE = 1.2          # reel 0 stops after this many seconds
    REEL_DELAY    = 0.45         # each subsequent reel stops this much later
    CYCLE_SPEED   = 0.07         # seconds between symbol flips while spinning

    message       = f"Match symbols to win!  Cost: {SPIN_COST} {balance_word_lower}/spin"
    message_color = (220, 220, 220)

    def draw_reel(idx, sym_idx, highlight):
        rx = reel_xs[idx]
        bx = rx - box_pad
        by = reel_y - box_pad
        fill   = (210, 180, 30) if highlight else (30, 30, 30)
        border = (255, 220, 0)  if highlight else (140, 140, 140)
        pygame.draw.rect(screen, fill,   (bx, by, box_w, box_h), border_radius=12)
        pygame.draw.rect(screen, border, (bx, by, box_w, box_h), 3, border_radius=12)
        screen.blit(symbols[sym_idx][1], (rx, reel_y))

    def apply_result():
        nonlocal message, message_color
        names = [symbols[i][0] for i in final]
        payout = 0
        if names[0] == names[1] == names[2]:
            n = names[0]
            if n == "coin":
                payout = 50
                wallet_add(conn, player_name, payout)
                message = f"MEGA JACKPOT!  3 x Coin  — +{payout} {balance_word_lower}!"
                message_color = (255, 240, 50)
            elif n == "life":
                add_lives(conn, player_name, 2)
                message = "JACKPOT!  3 x Life  — +2 extra lives!"
                message_color = (255, 220, 0)
            else:
                add_powerup(conn, player_name, n, 2)
                message = f"JACKPOT!  3 x {n.title()}  — +2 powerups!"
                message_color = (255, 220, 0)
        elif names[0] == names[1] or names[1] == names[2] or names[0] == names[2]:
            payout = 3
            wallet_add(conn, player_name, payout)
            message = f"Two matching!  +{payout} {balance_word_lower} returned!"
            message_color = (160, 230, 140)
        else:
            message = "No match — better luck next time!"
            message_color = (210, 100, 100)
        if callable(result_logger):
            try:
                result_logger('slots', SPIN_COST, int(payout))
            except Exception:
                pass

    clock = pygame.time.Clock()
    running = True
    while running:
        dt = clock.tick(60) / 1000.0

        screen.blit(background, (0, 0))

        # Title
        title_surf = title_font.render("Slot Machine", True, (255, 220, 0))
        screen.blit(title_surf, ((sw - title_surf.get_width()) // 2, int(sh * 0.015)))

        # Coin balance
        coins_now = wallet_get(conn, player_name)
        coins_surf = font.render(f"{balance_word}: {coins_now}", True, (255, 255, 0))
        coins_box = pygame.Rect(sw - coins_surf.get_width() - 30, 12, coins_surf.get_width() + 16, coins_surf.get_height() + 10)
        pygame.draw.rect(screen, (25, 18, 12), coins_box, border_radius=8)
        pygame.draw.rect(screen, (200, 160, 60), coins_box, 2, border_radius=8)
        screen.blit(coins_surf, (coins_box.x + 8, coins_box.y + 5))

        # Animate reels
        if spinning:
            elapsed = pygame.time.get_ticks() / 1000.0 - spin_start
            all_done = True
            for i in range(REEL_COUNT):
                stop_at = SPIN_DUR_BASE + i * REEL_DELAY
                if elapsed >= stop_at and not stopped[i]:
                    stopped[i] = True
                    current[i] = final[i]
                if not stopped[i]:
                    all_done = False
                    cycle_timers[i] += dt
                    if cycle_timers[i] >= CYCLE_SPEED:
                        cycle_timers[i] = 0.0
                        current[i] = (current[i] + 1) % len(symbols)
            if all_done:
                spinning = False
                apply_result()

        # Draw reels
        jackpot = (not spinning and final[0] == final[1] == final[2])
        for i in range(REEL_COUNT):
            draw_reel(i, current[i], highlight=jackpot)

        # Compact two-row legend placed below machine, above controls.
        legend_top = int(sh * 0.73)
        legend_font = pygame.font.SysFont("Arial", max(10, int(17 * sy)))
        legend_items = [
            (0, "x3 +2 powerups"),
            (1, "x3 +2 powerups"),
            (2, "x3 +2 powerups"),
            (3, "x3 +2 lives"),
            (4, f"x3 +50 {balance_word_lower}"),
        ]
        cols = 3
        cell_w = max(180, int(sw * 0.23))
        cell_h = max(42, int(sh * 0.05))
        grid_w = min(sw - 40, cols * cell_w)
        start_x = (sw - grid_w) // 2
        mini_icon = max(20, int(sym_size * 0.32))
        for idx, (sym_idx, label_text) in enumerate(legend_items):
            row = idx // cols
            col = idx % cols
            cx = start_x + col * cell_w
            cy = legend_top + row * cell_h
            if row == 1:
                cx += cell_w // 2
            small = pygame.transform.scale(symbols[sym_idx][1], (mini_icon, mini_icon))
            screen.blit(small, (cx, cy + 2))
            lbl = legend_font.render(label_text, True, (235, 235, 235))
            screen.blit(lbl, (cx + mini_icon + 8, cy + 4))

        # Message
        msg_surf = font.render(message, True, message_color)
        msg_box = pygame.Rect((sw - msg_surf.get_width()) // 2 - 10, int(sh * 0.835), msg_surf.get_width() + 20, msg_surf.get_height() + 10)
        pygame.draw.rect(screen, (25, 18, 12), msg_box, border_radius=8)
        pygame.draw.rect(screen, (160, 130, 70), msg_box, 2, border_radius=8)
        screen.blit(msg_surf, (msg_box.x + 10, msg_box.y + 5))

        # Spin button
        can_spin = not spinning and coins_now >= SPIN_COST
        btn_fill   = (25, 90, 25)  if can_spin else (55, 55, 55)
        btn_border = (130, 220, 130) if can_spin else (90, 90, 90)
        pygame.draw.rect(screen, btn_fill,   spin_rect, border_radius=10)
        pygame.draw.rect(screen, btn_border, spin_rect, 2, border_radius=10)
        spin_txt = font.render(f"SPIN  ({SPIN_COST} {balance_word_lower})", True, (255, 255, 255))
        screen.blit(spin_txt, (
            spin_rect.x + (spin_rect.w - spin_txt.get_width()) // 2,
            spin_rect.y + (spin_rect.h - spin_txt.get_height()) // 2,
        ))

        back_button.draw()
        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if back_button.handle_event(event):
                return True
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if spin_rect.collidepoint(event.pos) and can_spin:
                    wallet_subtract(conn, player_name, SPIN_COST)
                    final      = [random.randint(0, len(symbols) - 1) for _ in range(REEL_COUNT)]
                    stopped    = [False, False, False]
                    cycle_timers = [0.0, 0.0, 0.0]
                    spinning   = True
                    spin_start = pygame.time.get_ticks() / 1000.0
                    message       = "Spinning..."
                    message_color = (220, 220, 220)
    return True


def skins_screen(player_name, conn):
    """Skin unlock/equip screen. Returns True to go back to shop, False to quit."""

    screen = pygame.display.get_surface()
    sw, sh = screen.get_width(), screen.get_height()
    sx, sy = sw / 1000.0, sh / 600.0

    background = _load_screen_background((sw, sh), "shop_background.png")

    back_size = max(24, int(sw * 0.04))
    back_img = pygame.image.load("back button.jpg").convert_alpha()
    back_img = pygame.transform.scale(back_img, (back_size, back_size))
    back_button = Button(10, 10, back_img)

    title_font = pygame.font.SysFont("Arial", max(20, int(42 * sy)), bold=True)
    label_font = pygame.font.SysFont("Arial", max(12, int(22 * sy)))
    msg_font = pygame.font.SysFont("Arial", max(12, int(24 * sy)), bold=True)
    evt_font = pygame.font.SysFont("Arial", max(10, int(18 * sy)), bold=True)
    active_event = get_active_event()

    skin_defs = [
        {"key": "gold", "name": "Gold", "cost": 250, "tint": (130, 95, 20), "card": (140, 110, 30)},
        {"key": "shadow", "name": "Shadow", "cost": 300, "tint": (20, 20, 110), "card": (55, 55, 95)},
        {"key": "neon", "name": "Neon", "cost": 400, "tint": (20, 170, 150), "card": (20, 125, 115)},
    ]

    card_w = max(180, int(230 * sx))
    card_h = max(200, int(255 * sy))
    gap = max(12, int(18 * sx))
    total_w = card_w * len(skin_defs) + gap * (len(skin_defs) - 1)
    start_x = (sw - total_w) // 2
    top_y = int(sh * 0.28)

    btn_h = max(34, int(42 * sy))
    for idx, skin in enumerate(skin_defs):
        x = start_x + idx * (card_w + gap)
        skin["card_rect"] = pygame.Rect(x, top_y, card_w, card_h)
        skin["btn_rect"] = pygame.Rect(x + 12, top_y + card_h - btn_h - 12, card_w - 24, btn_h)

    message = "Unlock a skin once, then equip it any time."
    message_color = (220, 220, 210)
    msg_timer = 3.0
    clock = pygame.time.Clock()

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        coins_now = get_total_coins(conn, player_name)
        owned = set(get_owned_skins(player_name))
        active = get_player_skin(player_name)

        screen.blit(background, (0, 0))
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((8, 12, 22, 130))
        screen.blit(overlay, (0, 0))

        title_s = title_font.render("Skins", True, (255, 230, 140))
        screen.blit(title_s, ((sw - title_s.get_width()) // 2, int(sh * 0.06)))

        coins_s = label_font.render(f"Coins: {coins_now}", True, (255, 235, 120))
        screen.blit(coins_s, (sw - coins_s.get_width() - 18, 14))

        if active_event is not None:
            evt_color = active_event.get("hud_color", (200, 220, 255))
            evt_txt = evt_font.render(f"Seasonal cosmetic active: {active_event.get('name', 'Event')}", True, evt_color)
            screen.blit(evt_txt, ((sw - evt_txt.get_width()) // 2, int(sh * 0.13)))

        for skin in skin_defs:
            card = skin["card_rect"]
            pygame.draw.rect(screen, (30, 36, 52), card, border_radius=12)
            pygame.draw.rect(screen, skin["card"], card, 3, border_radius=12)

            name_s = label_font.render(skin["name"], True, (245, 245, 245))
            screen.blit(name_s, (card.centerx - name_s.get_width() // 2, card.y + 12))

            swatch = pygame.Rect(card.centerx - 42, card.y + 46, 84, 84)
            pygame.draw.rect(screen, (18, 22, 32), swatch, border_radius=10)
            pygame.draw.rect(screen, (150, 150, 150), swatch, 2, border_radius=10)
            tint_patch = pygame.Surface((swatch.w - 10, swatch.h - 10))
            tint_patch.fill(skin["tint"])
            screen.blit(tint_patch, (swatch.x + 5, swatch.y + 5))

            owned_skin = skin["key"] in owned
            is_active = active == skin["key"]
            if owned_skin:
                status = "Active" if is_active else "Owned"
                status_color = (140, 235, 160) if is_active else (210, 210, 210)
            else:
                status = f"Cost: {skin['cost']}"
                status_color = (255, 210, 140)
            status_s = label_font.render(status, True, status_color)
            screen.blit(status_s, (card.centerx - status_s.get_width() // 2, swatch.bottom + 14))

            btn = skin["btn_rect"]
            if owned_skin and is_active:
                b_fill = (70, 70, 70)
                b_edge = (120, 120, 120)
                b_text = "Equipped"
            elif owned_skin:
                b_fill = (40, 100, 60)
                b_edge = (130, 220, 150)
                b_text = "Equip"
            else:
                affordable = coins_now >= skin["cost"]
                b_fill = (90, 70, 35) if affordable else (70, 70, 70)
                b_edge = (230, 190, 120) if affordable else (120, 120, 120)
                b_text = "Buy"
            pygame.draw.rect(screen, b_fill, btn, border_radius=8)
            pygame.draw.rect(screen, b_edge, btn, 2, border_radius=8)
            btn_s = label_font.render(b_text, True, (255, 255, 255))
            screen.blit(btn_s, (btn.centerx - btn_s.get_width() // 2, btn.centery - btn_s.get_height() // 2))

        if msg_timer > 0:
            msg_s = msg_font.render(message, True, message_color)
            screen.blit(msg_s, ((sw - msg_s.get_width()) // 2, int(sh * 0.19)))

        back_button.draw()
        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if back_button.handle_event(event):
                return True
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for skin in skin_defs:
                    if not skin["btn_rect"].collidepoint(event.pos):
                        continue
                    owned_skin = skin["key"] in owned
                    if owned_skin:
                        set_player_skin(player_name, skin["key"])
                        message = f"{skin['name']} skin equipped"
                        message_color = (180, 240, 190)
                        msg_timer = 2.0
                    else:
                        if coins_now >= skin["cost"]:
                            subtract_total_coins(conn, player_name, skin["cost"])
                            buy_skin(conn, player_name, skin["key"])
                            message = f"Unlocked {skin['name']} skin"
                            message_color = (180, 240, 190)
                            msg_timer = 2.0
                        else:
                            message = "Not enough coins"
                            message_color = (255, 185, 120)
                            msg_timer = 1.8

        if msg_timer > 0:
            msg_timer = max(0.0, msg_timer - dt)

    return True


def shop_menu(player_name=None):
    if not player_name:
        return True

    conn = create_connection()
    total_coins = get_total_coins(conn, player_name)
    shop_screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Lost Horizon - Shop Menu")

    background = _load_screen_background((screen_width, screen_height), "shop_background.png")

    sx = screen_width / 1000.0
    sy = screen_height / 600.0
    back_size = max(24, int(screen_width * 0.04))
    btn_size = max(48, int(screen_width * 0.10))

    back_img = pygame.image.load("back button.jpg").convert_alpha()
    back_img = pygame.transform.scale(back_img, (back_size, back_size))
    back_button = Button(10, 10, back_img)

    float_img = pygame.image.load("float_power.png").convert_alpha()
    float_img = pygame.transform.scale(float_img, (btn_size, btn_size))
    invincibility_img = pygame.image.load("invincibility.png").convert_alpha()
    invincibility_img = pygame.transform.scale(invincibility_img, (btn_size, btn_size))
    fire_img = pygame.image.load("fire_flower.png").convert_alpha()
    fire_img = pygame.transform.scale(fire_img, (btn_size, btn_size))
    lives_img = pygame.image.load("life.png").convert_alpha()
    lives_img = pygame.transform.scale(lives_img, (btn_size, btn_size))

    row_y = int(screen_height * 0.21)
    price_font = pygame.font.SysFont("Arial", max(12, int(22 * sy)), bold=True)
    name_font = pygame.font.SysFont("Arial", max(12, int(21 * sy)), bold=True)
    info_font = pygame.font.SysFont("Arial", max(10, int(17 * sy)))
    coins_font = pygame.font.SysFont("Arial", max(12, int(24 * sy)), bold=True)
    title_font = pygame.font.SysFont("Arial", max(16, int(40 * sy)))
    subtitle_font = pygame.font.SysFont("Arial", max(10, int(19 * sy)))
    msg_font = pygame.font.SysFont("Arial", max(12, int(22 * sy)), bold=True)

    # Card-driven horizontal layout to avoid overlap on smaller displays.
    card_w = max(180, int(205 * sx))
    card_gap = max(12, int(16 * sx))
    total_card_w = card_w * 4 + card_gap * 3
    if total_card_w > screen_width - 40:
        card_w = max(150, (screen_width - 40 - card_gap * 3) // 4)
        total_card_w = card_w * 4 + card_gap * 3
    card_x0 = (screen_width - total_card_w) // 2
    card_xs = [card_x0 + i * (card_w + card_gap) for i in range(4)]

    card_h = max(200, min(int(screen_height * 0.36), int(245 * sy)))
    icon_size = min(btn_size, max(42, card_w - 56))
    float_img = pygame.transform.scale(float_img, (icon_size, icon_size))
    invincibility_img = pygame.transform.scale(invincibility_img, (icon_size, icon_size))
    fire_img = pygame.transform.scale(fire_img, (icon_size, icon_size))
    lives_img = pygame.transform.scale(lives_img, (icon_size, icon_size))

    icon_y = row_y + max(28, int(20 * sy))
    float_button = Button(card_xs[0] + (card_w - icon_size) // 2, icon_y, float_img)
    invincibility_button = Button(card_xs[1] + (card_w - icon_size) // 2, icon_y, invincibility_img)
    fire_button = Button(card_xs[2] + (card_w - icon_size) // 2, icon_y, fire_img)
    lives_button = Button(card_xs[3] + (card_w - icon_size) // 2, icon_y, lives_img)
    item_defs = [
        {
            "key": "float",
            "name": "Float Power",
            "desc": "Longer jumps and glide control",
            "button": float_button,
            "img": float_img,
            "base": 10,
            "color": (95, 175, 255),
            "buy_label": "Buy Float",
        },
        {
            "key": "invincibility",
            "name": "Invincibility",
            "desc": "Temporary damage immunity",
            "button": invincibility_button,
            "img": invincibility_img,
            "base": 15,
            "color": (255, 205, 95),
            "buy_label": "Buy Shield",
        },
        {
            "key": "fire",
            "name": "Fire Power",
            "desc": "Shoot projectiles at enemies",
            "button": fire_button,
            "img": fire_img,
            "base": 20,
            "color": (255, 135, 95),
            "buy_label": "Buy Fire",
        },
        {
            "key": "life",
            "name": "Extra Life",
            "desc": "+1 life for your run",
            "button": lives_button,
            "img": lives_img,
            "base": 5,
            "color": (190, 120, 255),
            "buy_label": "Buy Life",
        },
    ]

    def scaled_price(base_cost, coin_count):
        # Price scales softly with stored wealth to slow hoarding without punishing normal play.
        tier = max(0, int(coin_count // max(1, SHOP_PRICE_INFLATION_STEP_COINS)))
        mult = min(SHOP_PRICE_INFLATION_CAP, 1.0 + SHOP_PRICE_INFLATION_RATE * tier)
        raw = int(round(base_cost * mult))
        snapped = int(5 * round(raw / 5.0))
        return max(base_cost, snapped)

    def refresh_prices(coin_count):
        out = {}
        for item in item_defs:
            out[item["key"]] = scaled_price(item["base"], coin_count)
        return out

    def render_fit_text(text, max_width, primary_font, fallback_font, color=(255, 255, 255)):
        surf = primary_font.render(text, True, color)
        if surf.get_width() <= max_width:
            return surf
        surf = fallback_font.render(text, True, color)
        if surf.get_width() <= max_width:
            return surf
        short = text
        while len(short) > 3:
            short = short[:-1]
            trial = fallback_font.render(short + "...", True, color)
            if trial.get_width() <= max_width:
                return trial
        return fallback_font.render("...", True, color)

    # Merchant cards split shop stock into clear categories.
    mini_btn_w = max(130, int(176 * sx))
    mini_btn_h = max(40, int(56 * sy))
    nav_top = row_y + card_h + max(18, int(18 * sy))
    vendor_defs = [
        {
            "key": "quartermaster",
            "name": "Quartermaster",
            "subtitle": "Survival stock",
            "color": (95, 165, 255),
            "items": ["life", "invincibility"],
        },
        {
            "key": "arcanist",
            "name": "Arcanist",
            "subtitle": "Power techniques",
            "color": (255, 135, 95),
            "items": ["float", "fire"],
        },
        {
            "key": "atelier",
            "name": "Atelier",
            "subtitle": "Skin boutique",
            "color": (235, 205, 115),
            "items": [],
            "action": "skins",
        },
        {
            "key": "guild",
            "name": "Guild Clerk",
            "subtitle": "Crafting and prestige",
            "color": (150, 225, 190),
            "items": [],
            "action": "progression",
        },
    ]
    vendor_gap = max(10, int(14 * sx))
    total_vendor_w = mini_btn_w * len(vendor_defs) + vendor_gap * (len(vendor_defs) - 1)
    vendor_x = (screen_width - total_vendor_w) // 2
    for idx, vendor in enumerate(vendor_defs):
        vendor["rect"] = pygame.Rect(
            vendor_x + idx * (mini_btn_w + vendor_gap),
            nav_top,
            mini_btn_w,
            mini_btn_h,
        )
    selected_vendor = "quartermaster"
    slot_font = pygame.font.SysFont("Arial", max(13, int(22 * sy)))

    message = "Prices scale softly with your coin total."
    message_color = (235, 235, 220)
    message_timer = 3.0
    loop_clock = pygame.time.Clock()

    running = True
    while running:
        dt = loop_clock.tick(60) / 1000.0
        current_prices = refresh_prices(total_coins)

        shop_screen.blit(background, (0, 0))
        overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
        overlay.fill((8, 12, 22, 105))
        shop_screen.blit(overlay, (0, 0))

        back_button.draw()

        title_x = screen_width // 2 - title_font.size("Shop Menu")[0] // 2
        title_y = int(screen_height * 0.0333)
        title_text = Text("Shop Menu", title_x, title_y, title_font)
        title_text.draw_text()

        price_mult = current_prices["float"] / max(1, item_defs[0]["base"])
        sub = subtitle_font.render(f"Current shop inflation: x{price_mult:.2f}", True, (220, 220, 200))
        shop_screen.blit(sub, (screen_width // 2 - sub.get_width() // 2, title_y + 42))

        coins_s = coins_font.render(f"Total Coins: {total_coins}", True, (255, 235, 120))
        coins_box = pygame.Rect(screen_width - coins_s.get_width() - 34, 10, coins_s.get_width() + 20, 36)
        pygame.draw.rect(shop_screen, (30, 36, 55), coins_box, border_radius=8)
        pygame.draw.rect(shop_screen, (210, 185, 110), coins_box, 2, border_radius=8)
        shop_screen.blit(coins_s, (coins_box.x + 10, coins_box.y + 7))

        selected_cfg = next((v for v in vendor_defs if v["key"] == selected_vendor), vendor_defs[0])
        active_keys = set(selected_cfg.get("items") or [])
        visible_items = [item for item in item_defs if item["key"] in active_keys]

        if selected_cfg.get("action"):
            action_name = "Skins boutique" if selected_cfg["action"] == "skins" else "Progression desk"
            action_hint = subtitle_font.render(
                f"{selected_cfg['name']} routes to {action_name}.",
                True,
                (220, 220, 200),
            )
            shop_screen.blit(action_hint, (screen_width // 2 - action_hint.get_width() // 2, row_y + 8))

        if visible_items:
            total_active_w = len(visible_items) * card_w + max(0, len(visible_items) - 1) * card_gap
            active_x0 = (screen_width - total_active_w) // 2
            active_card_xs = [active_x0 + i * (card_w + card_gap) for i in range(len(visible_items))]
        else:
            active_card_xs = []

        # Draw item cards with framed buy buttons.
        badge_font = pygame.font.SysFont("Arial", max(10, int(17 * sy)), bold=True)
        badge_font_small = pygame.font.SysFont("Arial", max(9, int(15 * sy)), bold=True)
        for idx, item in enumerate(visible_items):
            button = item["button"]
            key = item["key"]
            cost = current_prices[key]
            affordable = total_coins >= cost

            card = pygame.Rect(
                active_card_xs[idx],
                row_y,
                card_w,
                card_h,
            )
            button.rect.topleft = (card.x + (card.w - icon_size) // 2, icon_y)
            bg_col = (28, 34, 52)
            edge_col = item["color"] if affordable else (110, 110, 110)
            glow = pygame.Surface((card.w, card.h), pygame.SRCALPHA)
            glow.fill((*item["color"], 45 if affordable else 16))
            shop_screen.blit(glow, card.topleft)
            pygame.draw.rect(shop_screen, bg_col, card, border_radius=12)
            pygame.draw.rect(shop_screen, edge_col, card, 3, border_radius=12)

            # Framed icon area
            icon_frame = button.rect.inflate(14, 14)
            pygame.draw.rect(shop_screen, (18, 22, 38), icon_frame, border_radius=9)
            pygame.draw.rect(shop_screen, edge_col, icon_frame, 2, border_radius=9)
            shop_screen.blit(item["img"], button.rect.topleft)

            # Card text is rendered after icon frame so it is never hidden.
            name_s = render_fit_text(item["name"], card.w - 16, name_font, info_font, (242, 242, 242))
            shop_screen.blit(name_s, (card.centerx - name_s.get_width() // 2, card.y + 8))

            desc_y = icon_frame.bottom + 8
            desc_limit_bottom = card.bottom - max(34, int(36 * sy))
            if desc_y > desc_limit_bottom:
                desc_y = desc_limit_bottom
            desc_s = render_fit_text(item["desc"], card.w - 16, info_font, info_font, (205, 205, 215))
            shop_screen.blit(desc_s, (card.centerx - desc_s.get_width() // 2, desc_y))

            # Price badge / buy button area
            badge_w = card.w - 16
            badge_h = max(24, int(28 * sy))
            badge = pygame.Rect(card.x + 8, card.bottom - badge_h - 8, badge_w, badge_h)
            buy_fill = (42, 110, 62) if affordable else (86, 86, 86)
            buy_edge = (145, 230, 165) if affordable else (130, 130, 130)
            pygame.draw.rect(shop_screen, buy_fill, badge, border_radius=7)
            pygame.draw.rect(shop_screen, buy_edge, badge, 2, border_radius=7)
            badge_text = render_fit_text(
                f"{item['buy_label']} - {cost} coins",
                badge.w - 10,
                badge_font,
                badge_font_small,
                (255, 255, 255),
            )
            shop_screen.blit(
                badge_text,
                (badge.centerx - badge_text.get_width() // 2, badge.centery - badge_text.get_height() // 2),
            )

        for vendor in vendor_defs:
            vr = vendor["rect"]
            active = vendor["key"] == selected_vendor
            fill = tuple(min(255, c + 18) for c in vendor["color"]) if active else (42, 42, 52)
            edge = vendor["color"] if active else (120, 120, 130)
            pygame.draw.rect(shop_screen, fill, vr, border_radius=10)
            pygame.draw.rect(shop_screen, edge, vr, 2, border_radius=10)

            name_lbl = render_fit_text(vendor["name"], vr.w - 8, slot_font, info_font, (255, 255, 255))
            subtitle_lbl = render_fit_text(vendor["subtitle"], vr.w - 8, info_font, info_font, (230, 230, 230))
            shop_screen.blit(name_lbl, (vr.centerx - name_lbl.get_width() // 2, vr.y + 6))
            shop_screen.blit(subtitle_lbl, (vr.centerx - subtitle_lbl.get_width() // 2, vr.y + vr.h - subtitle_lbl.get_height() - 5))

        if message_timer > 0:
            msg = msg_font.render(message, True, message_color)
            shop_screen.blit(msg, (screen_width // 2 - msg.get_width() // 2, int(screen_height * 0.14)))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                return False

            if back_button.handle_event(event):
                return True

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for vendor in vendor_defs:
                    if vendor["rect"].collidepoint(event.pos):
                        selected_vendor = vendor["key"]
                        if vendor.get("action") == "skins":
                            result = skins_screen(player_name, conn)
                            total_coins = get_total_coins(conn, player_name)
                            if not result:
                                conn.close()
                                return False
                        elif vendor.get("action") == "progression":
                            result = progression_hub_screen(player_name)
                            total_coins = get_total_coins(conn, player_name)
                            if not result:
                                conn.close()
                                return False
                        break

            active_keys = set(next((v for v in vendor_defs if v["key"] == selected_vendor), vendor_defs[0]).get("items") or [])

            if "float" in active_keys and float_button.handle_event(event):
                cost = current_prices["float"]
                if total_coins >= cost:
                    subtract_total_coins(conn, player_name, cost)
                    total_coins = get_total_coins(conn, player_name)
                    add_powerup(conn, player_name, 'float', 1)
                    message = f"Bought Float Power for {cost} coins"
                    message_color = (180, 240, 190)
                    message_timer = 2.0
                else:
                    message = "Not enough coins for Float Power"
                    message_color = (255, 185, 120)
                    message_timer = 1.8
            if "invincibility" in active_keys and invincibility_button.handle_event(event):
                cost = current_prices["invincibility"]
                if total_coins >= cost:
                    subtract_total_coins(conn, player_name, cost)
                    total_coins = get_total_coins(conn, player_name)
                    add_powerup(conn, player_name, 'invincibility', 1)
                    message = f"Bought Invincibility for {cost} coins"
                    message_color = (180, 240, 190)
                    message_timer = 2.0
                else:
                    message = "Not enough coins for Invincibility"
                    message_color = (255, 185, 120)
                    message_timer = 1.8
            if "fire" in active_keys and fire_button.handle_event(event):
                cost = current_prices["fire"]
                if total_coins >= cost:
                    subtract_total_coins(conn, player_name, cost)
                    total_coins = get_total_coins(conn, player_name)
                    add_powerup(conn, player_name, 'fire', 1)
                    message = f"Bought Fire Power for {cost} coins"
                    message_color = (180, 240, 190)
                    message_timer = 2.0
                else:
                    message = "Not enough coins for Fire Power"
                    message_color = (255, 185, 120)
                    message_timer = 1.8
            if "life" in active_keys and lives_button.handle_event(event):
                cost = current_prices["life"]
                if total_coins >= cost:
                    subtract_total_coins(conn, player_name, cost)
                    total_coins = get_total_coins(conn, player_name)
                    add_lives(conn, player_name, 1)
                    message = f"Bought Extra Life for {cost} coins"
                    message_color = (180, 240, 190)
                    message_timer = 2.0
                else:
                    message = "Not enough coins for Extra Life"
                    message_color = (255, 185, 120)
                    message_timer = 1.8

        if message_timer > 0:
            message_timer = max(0.0, message_timer - dt)

        pygame.display.update()

    conn.close()

if __name__ == "__main__":
    shop_menu()