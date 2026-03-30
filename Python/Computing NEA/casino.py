import os
import random
from datetime import date

import pygame

from Classes import Button, resolve_asset_path
from database import (
    CASINO_REWARD_SHOP,
    CASINO_BUY_IN_CHIP_GAIN,
    CASINO_BUY_IN_COIN_COST,
    CASINO_DAILY_CHIP_BONUS,
    add_total_chips,
    claim_casino_daily_bonus,
    create_connection,
    get_casino_profile,
    get_casino_vip_status,
    get_player_cosmetics,
    get_player_quests,
    get_total_chips,
    get_total_coins,
    purchase_casino_reward,
    record_casino_play,
    subtract_total_coins,
    subtract_total_chips,
)
from shop import blackjack_screen, roulette_screen, slot_machine_screen
from ui_helpers import draw_wrapped_text, fit_text


pygame.init()


CASINO_STAFF = {
    'host': {
        'name': 'Pit Boss Vale',
        'line': 'Tables are live tonight. Read the room, watch the tells, and do not chase cold luck.',
    },
    'cashier': {
        'name': 'Cashier Mira',
        'line': 'Coins become chips here, and chips stay in the district. Clean trades only.',
    },
    'prize': {
        'name': 'Curator Orin',
        'line': 'The prize counter rotates stock every week. Reputation decides what I put on the shelf.',
    },
    'blackjack': {
        'dealer': 'Dealer Sable',
        'line': 'Blackjack pays disciplined hands. Greed is how the house gets you.',
    },
    'roulette': {
        'dealer': 'Croupier Rook',
        'line': 'Roulette is momentum and nerve. Pick your color, then live with the wheel.',
    },
    'slots': {
        'dealer': 'Attendant Nyx',
        'line': 'Slots are quick and loud. Keep your stake controlled and cash the good runs.',
    },
    'skillshot': {
        'dealer': 'Safecracker Cinder',
        'line': 'Safecracker is all timing. Breathe, center the cursor, and stop forcing the third tumbler.',
    },
}


def _load_background(size):
    sw, sh = size
    for path in ("casino_background.png", "shop_background.png", "background.jpg"):
        resolved_path = resolve_asset_path(path)
        if os.path.exists(resolved_path):
            try:
                img = pygame.image.load(resolved_path).convert_alpha()
                return pygame.transform.scale(img, (sw, sh))
            except Exception:
                continue
    surface = pygame.Surface((sw, sh))
    surface.fill((16, 12, 22))
    return surface


def _rotating_rewards():
    keys = list(CASINO_REWARD_SHOP.keys())
    if not keys:
        return []
    week_seed = date.today().isocalendar().week % len(keys)
    return keys[week_seed:] + keys[:week_seed]


def safecracker_screen(player_name, conn, get_balance, add_balance, subtract_balance, result_logger=None):
    screen = pygame.display.get_surface()
    if screen is None:
        info = pygame.display.Info()
        screen = pygame.display.set_mode((info.current_w, info.current_h))
    sw, sh = screen.get_size()
    sx, sy = sw / 1000.0, sh / 600.0

    background = _load_background((sw, sh))
    back_size = max(24, int(sw * 0.04))
    back_img = pygame.image.load(resolve_asset_path("back button.jpg")).convert_alpha()
    back_img = pygame.transform.scale(back_img, (back_size, back_size))
    back_button = Button(10, 10, back_img)

    title_font = pygame.font.SysFont("Arial", max(22, int(40 * sy)), bold=True)
    head_font = pygame.font.SysFont("Arial", max(14, int(24 * sy)), bold=True)
    body_font = pygame.font.SysFont("Arial", max(12, int(20 * sy)))
    small_font = pygame.font.SysFont("Arial", max(11, int(16 * sy)))

    clock = pygame.time.Clock()
    bet_values = [10, 25, 50]
    selected_bet_idx = 0
    state = 'betting'
    tumbler_index = 0
    tumbler_scores = []
    cursor_pos = 0.0
    cursor_dir = 1.0
    cursor_speed = 0.82
    tumbler_targets = [0.25, 0.52, 0.74]
    current_bet = bet_values[selected_bet_idx]
    message = "Pick a chip stake, then stop each tumbler in the gold zone."
    message_color = (235, 225, 185)

    meter_rect = pygame.Rect(int(sw * 0.18), int(sh * 0.42), int(sw * 0.64), max(24, int(34 * sy)))
    lock_rects = [
        pygame.Rect(int(sw * 0.18), int(sh * 0.25) + i * max(44, int(54 * sy)), int(sw * 0.64), max(28, int(34 * sy)))
        for i in range(3)
    ]
    bet_rects = [
        pygame.Rect(int(sw * 0.24) + i * max(120, int(140 * sx)), int(sh * 0.78), max(96, int(110 * sx)), max(42, int(52 * sy)))
        for i in range(len(bet_values))
    ]
    start_rect = pygame.Rect(int(sw * 0.68), int(sh * 0.78), max(120, int(140 * sx)), max(42, int(52 * sy)))

    def reset_round():
        nonlocal tumbler_index, tumbler_scores, cursor_pos, cursor_dir, cursor_speed, tumbler_targets
        tumbler_index = 0
        tumbler_scores = []
        cursor_pos = 0.0
        cursor_dir = 1.0
        cursor_speed = random.uniform(0.76, 0.94)
        tumbler_targets = [random.uniform(0.18, 0.82) for _ in range(3)]

    def begin_round():
        nonlocal state, current_bet, message, message_color
        chips_now = get_balance(conn, player_name)
        current_bet = bet_values[selected_bet_idx]
        if chips_now < current_bet:
            message = f"Need {current_bet} chips to play."
            message_color = (255, 185, 130)
            return
        subtract_balance(conn, player_name, current_bet)
        reset_round()
        state = 'playing'
        message = "Press Space or click when the cursor is centered in the gold zone."
        message_color = (210, 235, 245)

    def resolve_stop():
        nonlocal tumbler_index, state, message, message_color
        target = tumbler_targets[tumbler_index]
        distance = abs(cursor_pos - target)
        if distance <= 0.035:
            tumbler_scores.append(2)
        elif distance <= 0.085:
            tumbler_scores.append(1)
        else:
            tumbler_scores.append(0)
        tumbler_index += 1
        if tumbler_index >= 3:
            total_score = sum(tumbler_scores)
            payout = 0
            if total_score >= 5:
                payout = current_bet * 3
                message = f"Vault cracked cleanly. +{payout} chips."
                message_color = (175, 245, 170)
            elif total_score >= 3:
                payout = current_bet * 2
                message = f"Strong crack. +{payout} chips."
                message_color = (185, 235, 180)
            elif total_score >= 2:
                payout = current_bet
                message = "Partial crack. Bet refunded."
                message_color = (230, 220, 150)
            else:
                message = "Lock jammed. The house keeps the stake."
                message_color = (255, 170, 140)
            if payout > 0:
                add_balance(conn, player_name, payout)
            if callable(result_logger):
                try:
                    result_logger('skillshot', int(current_bet), int(payout))
                except Exception:
                    pass
            state = 'betting'

    reset_round()

    while True:
        dt = clock.tick(60) / 1000.0
        if state == 'playing':
            cursor_pos += cursor_dir * cursor_speed * dt
            if cursor_pos >= 1.0:
                cursor_pos = 1.0
                cursor_dir = -1.0
            elif cursor_pos <= 0.0:
                cursor_pos = 0.0
                cursor_dir = 1.0

        screen.blit(background, (0, 0))
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((10, 16, 26, 188))
        screen.blit(overlay, (0, 0))

        title = title_font.render("Safecracker Table", True, (255, 228, 140))
        screen.blit(title, (sw // 2 - title.get_width() // 2, 20))
        subtitle = body_font.render("A timing game: hit the sweet spot on all three tumblers.", True, (215, 225, 238))
        screen.blit(subtitle, (sw // 2 - subtitle.get_width() // 2, 62))
        chips_label = head_font.render(f"Chips: {get_balance(conn, player_name)}", True, (255, 235, 120))
        screen.blit(chips_label, (sw - chips_label.get_width() - 18, 16))

        for idx, rect in enumerate(lock_rects):
            solved = idx < len(tumbler_scores)
            active = idx == tumbler_index and state == 'playing'
            pygame.draw.rect(screen, (24, 34, 48), rect, border_radius=10)
            pygame.draw.rect(screen, (110, 130, 155) if not active else (240, 205, 120), rect, 2, border_radius=10)
            target = tumbler_targets[idx]
            zone_w = max(28, int(rect.w * 0.08))
            zone_rect = pygame.Rect(rect.x + int(target * (rect.w - zone_w)), rect.y + 5, zone_w, rect.h - 10)
            zone_color = (185, 150, 70) if not solved else (95, 165, 105)
            pygame.draw.rect(screen, zone_color, zone_rect, border_radius=8)
            label = head_font.render(f"Tumbler {idx + 1}", True, (240, 240, 245))
            screen.blit(label, (rect.x + 10, rect.y - label.get_height() - 2))
            if solved:
                grade = "Perfect" if tumbler_scores[idx] == 2 else "Good" if tumbler_scores[idx] == 1 else "Miss"
                grade_s = small_font.render(grade, True, (210, 230, 210) if tumbler_scores[idx] > 0 else (255, 180, 150))
                screen.blit(grade_s, (rect.right - grade_s.get_width() - 8, rect.y - grade_s.get_height() - 2))

        pygame.draw.rect(screen, (28, 36, 58), meter_rect, border_radius=12)
        pygame.draw.rect(screen, (170, 190, 220), meter_rect, 2, border_radius=12)
        current_target = tumbler_targets[min(tumbler_index, 2)]
        sweet_w = max(40, int(meter_rect.w * 0.09))
        sweet_rect = pygame.Rect(meter_rect.x + int(current_target * (meter_rect.w - sweet_w)), meter_rect.y + 6, sweet_w, meter_rect.h - 12)
        pygame.draw.rect(screen, (236, 196, 88), sweet_rect, border_radius=8)
        cursor_x = meter_rect.x + int(cursor_pos * meter_rect.w)
        pygame.draw.line(screen, (255, 255, 255), (cursor_x, meter_rect.y - 12), (cursor_x, meter_rect.bottom + 12), 4)

        info = small_font.render("Space / Left Click: stop cursor   |   Gold zone = better payout", True, (205, 215, 230))
        screen.blit(info, (sw // 2 - info.get_width() // 2, meter_rect.bottom + 18))

        for idx, rect in enumerate(bet_rects):
            selected = idx == selected_bet_idx
            pygame.draw.rect(screen, (58, 92, 74) if selected else (46, 52, 72), rect, border_radius=9)
            pygame.draw.rect(screen, (180, 235, 185) if selected else (150, 165, 190), rect, 2, border_radius=9)
            bet_s = body_font.render(f"{bet_values[idx]} chips", True, (255, 255, 255))
            screen.blit(bet_s, (rect.centerx - bet_s.get_width() // 2, rect.centery - bet_s.get_height() // 2))

        start_active = state == 'betting'
        pygame.draw.rect(screen, (80, 118, 58) if start_active else (72, 72, 72), start_rect, border_radius=10)
        pygame.draw.rect(screen, (190, 235, 175) if start_active else (135, 135, 135), start_rect, 2, border_radius=10)
        start_label = body_font.render("Start Run", True, (255, 255, 255))
        screen.blit(start_label, (start_rect.centerx - start_label.get_width() // 2, start_rect.centery - start_label.get_height() // 2))

        msg = body_font.render(fit_text(body_font, message, sw - 50), True, message_color)
        screen.blit(msg, (sw // 2 - msg.get_width() // 2, sh - 34))
        back_button.draw()
        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if back_button.handle_event(event):
                return True
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return True
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE and state == 'playing':
                resolve_stop()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if state == 'playing':
                    resolve_stop()
                    continue
                for idx, rect in enumerate(bet_rects):
                    if rect.collidepoint(event.pos):
                        selected_bet_idx = idx
                        current_bet = bet_values[idx]
                        break
                if start_rect.collidepoint(event.pos) and state == 'betting':
                    begin_round()

    return True


def casino_screen(player_name):
    if not player_name:
        return True

    screen = pygame.display.get_surface()
    if screen is None:
        info = pygame.display.Info()
        screen = pygame.display.set_mode((info.current_w, info.current_h))
    sw, sh = screen.get_size()
    sx, sy = sw / 1000.0, sh / 600.0

    conn = create_connection()
    if conn is None:
        return True

    background = _load_background((sw, sh))
    back_size = max(24, int(sw * 0.04))
    back_img = pygame.image.load(resolve_asset_path("back button.jpg")).convert_alpha()
    back_img = pygame.transform.scale(back_img, (back_size, back_size))
    back_button = Button(10, 10, back_img)

    title_font = pygame.font.SysFont("Arial", max(24, int(42 * sy)), bold=True)
    head_font = pygame.font.SysFont("Arial", max(16, int(24 * sy)), bold=True)
    body_font = pygame.font.SysFont("Arial", max(11, int(18 * sy)))
    small_font = pygame.font.SysFont("Arial", max(10, int(15 * sy)))
    msg_font = pygame.font.SysFont("Arial", max(12, int(22 * sy)), bold=True)

    header_rect = pygame.Rect(20, 20, sw - 40, max(72, int(88 * sy)))
    games_rect = pygame.Rect(24, header_rect.bottom + 18, int(sw * 0.54), sh - header_rect.bottom - 42)
    side_rect = pygame.Rect(games_rect.right + 16, games_rect.y, sw - games_rect.right - 40, games_rect.height)
    dialogue_rect = pygame.Rect(header_rect.x + 18, header_rect.y + 54, int(sw * 0.48), max(30, int(28 * sy)))

    game_card_gap = max(12, int(16 * sx))
    game_card_h = max(90, int(110 * sy))
    game_card_w = games_rect.w - 24
    game_cards = []
    game_defs = [
        ("blackjack", "Blackjack Table", "Classic dealer table. Best for controlled chip gains.", (32, 88, 44)),
        ("roulette", "Roulette Wheel", "Higher variance bets with quick spin resolution.", (125, 34, 34)),
        ("slots", "Slot Machines", "Fast spins, power-up jackpots, and small chip refunds.", (104, 58, 126)),
        ("skillshot", "Safecracker", "Stop each tumbler in the gold window for a skill-based payout.", (138, 94, 32)),
    ]
    for idx, game_def in enumerate(game_defs):
        card = pygame.Rect(games_rect.x + 12, games_rect.y + 56 + idx * (game_card_h + game_card_gap), game_card_w, game_card_h)
        play_rect = pygame.Rect(card.right - 108, card.centery - 18, 90, 36)
        game_cards.append({
            'game_key': game_def[0],
            'title': game_def[1],
            'description': game_def[2],
            'color': game_def[3],
            'dealer': CASINO_STAFF.get(game_def[0], {}).get('dealer', 'Floor Staff'),
            'card_rect': card,
            'play_rect': play_rect,
        })

    cashier_rect = pygame.Rect(side_rect.x + 12, side_rect.y + 12, side_rect.w - 24, max(128, int(150 * sy)))
    rewards_rect = pygame.Rect(side_rect.x + 12, cashier_rect.bottom + 14, side_rect.w - 24, max(220, int(250 * sy)))
    stats_rect = pygame.Rect(side_rect.x + 12, rewards_rect.bottom + 14, side_rect.w - 24, side_rect.bottom - rewards_rect.bottom - 26)

    buyin_rect = pygame.Rect(cashier_rect.x + 14, cashier_rect.bottom - 48, cashier_rect.w - 28, 34)
    bonus_rect = pygame.Rect(cashier_rect.x + 14, cashier_rect.bottom - 90, cashier_rect.w - 28, 34)

    reward_order = _rotating_rewards()
    reward_buttons = []
    reward_card_h = max(54, int(62 * sy))
    for idx, reward_key in enumerate(reward_order[:3]):
        reward_buttons.append((reward_key, pygame.Rect(rewards_rect.x + 12, rewards_rect.y + 48 + idx * (reward_card_h + 10), rewards_rect.w - 24, reward_card_h)))

    message = "The casino trades in chips. Buy in with coins, play tables, and spend winnings on cosmetics."
    message_color = (230, 220, 170)
    message_timer = 0.0
    clock = pygame.time.Clock()

    def push_message(text, color=(230, 220, 170), duration=2.5):
        nonlocal message, message_color, message_timer
        message = text
        message_color = color
        message_timer = duration

    def logger(game_key, wager, payout):
        record_casino_play(conn, player_name, game_key, wager, payout)

    def buy_in(coin_cost=CASINO_BUY_IN_COIN_COST, chip_gain=CASINO_BUY_IN_CHIP_GAIN):
        coins = get_total_coins(conn, player_name)
        if coins < coin_cost:
            return False, f"Need {coin_cost} coins to buy in."
        subtract_total_coins(conn, player_name, coin_cost)
        add_total_chips(conn, player_name, chip_gain)
        return True, f"Cashier exchanged {coin_cost} coins for {chip_gain} chips."

    while True:
        dt = clock.tick(60) / 1000.0
        profile = get_casino_profile(player_name)
        vip_status = get_casino_vip_status(reputation=profile['reputation'])
        daily_casino_quests = [q for q in get_player_quests(player_name, period='daily') if q.get('category') == 'casino']
        weekly_casino_quests = [q for q in get_player_quests(player_name, period='weekly') if q.get('category') == 'casino']
        cosmetics = get_player_cosmetics(player_name)
        owned_casino_rewards = sorted(key for key, qty in cosmetics.items() if key.startswith("casino_") and qty > 0)
        featured_reward = reward_order[0] if reward_order else None
        mouse_pos = pygame.mouse.get_pos()
        speaker = CASINO_STAFF['host']['name']
        dialogue = CASINO_STAFF['host']['line']
        for game in game_cards:
            if game['card_rect'].collidepoint(mouse_pos):
                speaker = CASINO_STAFF.get(game['game_key'], {}).get('dealer', game['dealer'])
                dialogue = CASINO_STAFF.get(game['game_key'], {}).get('line', game['description'])
                break
        if cashier_rect.collidepoint(mouse_pos):
            speaker = CASINO_STAFF['cashier']['name']
            dialogue = CASINO_STAFF['cashier']['line']
        if rewards_rect.collidepoint(mouse_pos):
            speaker = CASINO_STAFF['prize']['name']
            dialogue = CASINO_STAFF['prize']['line']

        screen.blit(background, (0, 0))
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((8, 10, 18, 170))
        screen.blit(overlay, (0, 0))

        for panel in (header_rect, games_rect, cashier_rect, rewards_rect, stats_rect):
            pygame.draw.rect(screen, (20, 24, 40), panel, border_radius=12)
            pygame.draw.rect(screen, (110, 145, 210), panel, 2, border_radius=12)

        title = title_font.render("Casino District", True, (255, 225, 120))
        screen.blit(title, (header_rect.x + 18, header_rect.y + 12))
        subtitle = body_font.render(f"VIP tier: {vip_status['tier_label']}  |  chips, rotating rewards, and table games", True, (210, 220, 240))
        screen.blit(subtitle, (header_rect.x + 18, header_rect.y + 48))
        pygame.draw.rect(screen, (38, 28, 22), dialogue_rect, border_radius=8)
        pygame.draw.rect(screen, (210, 175, 110), dialogue_rect, 2, border_radius=8)
        speaker_s = small_font.render(speaker, True, (255, 226, 150))
        screen.blit(speaker_s, (dialogue_rect.x + 10, dialogue_rect.y + 5))
        draw_wrapped_text(screen, small_font, dialogue, (230, 228, 220), pygame.Rect(dialogue_rect.x + 10, dialogue_rect.y + 18, dialogue_rect.w - 20, dialogue_rect.h - 8), line_gap=2, max_lines=2)

        chips_text = head_font.render(f"Chips: {profile['chips']}", True, (255, 230, 120))
        rep_text = body_font.render(f"Rep: {profile['reputation']}", True, (180, 230, 255))
        coins_text = body_font.render(f"Coins: {get_total_coins(conn, player_name)}", True, (225, 225, 225))
        screen.blit(chips_text, (header_rect.right - chips_text.get_width() - 18, header_rect.y + 12))
        screen.blit(rep_text, (header_rect.right - rep_text.get_width() - 18, header_rect.y + 44))
        screen.blit(coins_text, (header_rect.right - coins_text.get_width() - 18, header_rect.y + 68))

        games_head = head_font.render("Table Floor", True, (170, 230, 190))
        screen.blit(games_head, (games_rect.x + 14, games_rect.y + 12))
        for game in game_cards:
            card = game['card_rect']
            color = game['color']
            pygame.draw.rect(screen, (28, 34, 54), card, border_radius=10)
            pygame.draw.rect(screen, color, card, 2, border_radius=10)
            title_s = head_font.render(game['title'], True, (245, 245, 250))
            screen.blit(title_s, (card.x + 14, card.y + 10))
            dealer_s = small_font.render(game['dealer'], True, (255, 220, 170))
            screen.blit(dealer_s, (card.x + 14, card.y + 30))
            draw_wrapped_text(screen, body_font, game['description'], (205, 210, 225), pygame.Rect(card.x + 14, card.y + 50, card.w - 150, card.h - 56), line_gap=2, max_lines=3)
            play_rect = game['play_rect']
            pygame.draw.rect(screen, color, play_rect, border_radius=8)
            pygame.draw.rect(screen, (220, 230, 240), play_rect, 2, border_radius=8)
            play_s = body_font.render("Play", True, (255, 255, 255))
            screen.blit(play_s, (play_rect.centerx - play_s.get_width() // 2, play_rect.centery - play_s.get_height() // 2))

        cashier_head = head_font.render("Cashier  |  Mira Vale", True, (255, 220, 140))
        screen.blit(cashier_head, (cashier_rect.x + 12, cashier_rect.y + 10))
        draw_wrapped_text(screen, body_font, "Daily bonus keeps the casino accessible. Buy-ins convert a controlled amount of progression coins into chips without letting table losses overrun the main economy.", (220, 220, 225), pygame.Rect(cashier_rect.x + 12, cashier_rect.y + 38, cashier_rect.w - 24, 60), line_gap=2, max_lines=4)
        for rect, fill, border, label in (
            (bonus_rect, (70, 82, 132), (165, 195, 255), f"Claim Daily +{CASINO_DAILY_CHIP_BONUS} Chips"),
            (buyin_rect, (74, 104, 60), (160, 225, 170), f"Buy In: {CASINO_BUY_IN_COIN_COST} Coins -> {CASINO_BUY_IN_CHIP_GAIN} Chips"),
        ):
            pygame.draw.rect(screen, fill, rect, border_radius=8)
            pygame.draw.rect(screen, border, rect, 2, border_radius=8)
            lbl = fit_text(body_font, label, rect.w - 12)
            lbl_s = body_font.render(lbl, True, (255, 255, 255))
            screen.blit(lbl_s, (rect.centerx - lbl_s.get_width() // 2, rect.centery - lbl_s.get_height() // 2))

        rewards_head = head_font.render("Prize Counter  |  Curator Orin", True, (255, 180, 210))
        screen.blit(rewards_head, (rewards_rect.x + 12, rewards_rect.y + 10))
        if featured_reward is not None:
            featured_label = CASINO_REWARD_SHOP[featured_reward]['label']
            featured_s = body_font.render(f"Weekly spotlight: {featured_label}", True, (255, 225, 160))
            screen.blit(featured_s, (rewards_rect.x + 12, rewards_rect.y + 30))
        for reward_key, rect in reward_buttons:
            reward = CASINO_REWARD_SHOP[reward_key]
            owned = cosmetics.get(reward['yield'], 0) > 0
            required_rep = int(reward.get('required_reputation', 0) or 0)
            unlocked = profile['reputation'] >= required_rep
            fill = (54, 44, 72) if not owned else (46, 70, 58)
            edge = (220, 160, 210) if not owned else (160, 225, 170)
            if not unlocked and not owned:
                fill = (44, 44, 48)
                edge = (150, 150, 155)
            pygame.draw.rect(screen, fill, rect, border_radius=8)
            pygame.draw.rect(screen, edge, rect, 2, border_radius=8)
            label = body_font.render(reward['label'], True, (245, 245, 250))
            if owned:
                cost_text = "Owned"
            elif unlocked:
                cost_text = f"{reward['cost']} chips"
            else:
                cost_text = f"Req {required_rep} rep"
            cost = body_font.render(cost_text, True, (255, 225, 140) if not owned else (165, 235, 180))
            desc = small_font.render(fit_text(small_font, reward['description'], rect.w - 150), True, (205, 210, 220))
            screen.blit(label, (rect.x + 12, rect.y + 8))
            screen.blit(desc, (rect.x + 12, rect.y + 32))
            screen.blit(cost, (rect.right - cost.get_width() - 12, rect.y + 8))

        stats_head = head_font.render("Casino Ledger + VIP  |  Pit Boss Vale", True, (160, 210, 255))
        screen.blit(stats_head, (stats_rect.x + 12, stats_rect.y + 10))
        stat_lines = [
            f"VIP tier: {vip_status['tier_label']}",
            f"Blackjack hands: {profile['blackjack_hands']}",
            f"Roulette spins: {profile['roulette_spins']}",
            f"Slot spins: {profile['slot_spins']}",
            f"Safecracker rounds: {profile['skillshot_rounds']}",
            f"Total wagered: {profile['total_wagered']} chips",
            f"Total payouts: {profile['total_paid_out']} chips",
            f"Net table result: {profile['net']} chips",
            f"Daily claims: {profile['daily_bonus_claims']}",
        ]
        stat_y = stats_rect.y + 38
        for line in stat_lines:
            stat_s = body_font.render(fit_text(body_font, line, stats_rect.w - 24), True, (220, 225, 235))
            screen.blit(stat_s, (stats_rect.x + 12, stat_y))
            stat_y += stat_s.get_height() + 6

        vip_lines = []
        if vip_status['next_tier_label']:
            vip_lines.append(f"Next unlock: {vip_status['next_tier_label']} in {vip_status['reputation_to_next']} rep")
        else:
            vip_lines.append("VIP track complete: all lounge tiers unlocked")
        vip_lines.append(vip_status['tier_perk'])
        quest_preview = []
        for quest in daily_casino_quests[:1] + weekly_casino_quests[:1]:
            quest_preview.append(f"{quest['label']}: {quest['progress']}/{quest['target']}")
        if not quest_preview:
            quest_preview.append("No casino quests available right now")
        for line in vip_lines + quest_preview:
            stat_s = small_font.render(fit_text(small_font, line, stats_rect.w - 24), True, (180, 220, 190))
            screen.blit(stat_s, (stats_rect.x + 12, stat_y))
            stat_y += stat_s.get_height() + 4

        owned_line = ", ".join(item.replace("casino_", "") for item in owned_casino_rewards) or "None yet"
        draw_wrapped_text(screen, small_font, f"Owned casino rewards: {owned_line}. Claim finished casino quests in the Progression Hub.", (180, 220, 190), pygame.Rect(stats_rect.x + 12, stats_rect.bottom - 58, stats_rect.w - 24, 48), line_gap=2, max_lines=3)

        if message_timer > 0:
            message_timer = max(0.0, message_timer - dt)
        msg_s = msg_font.render(fit_text(msg_font, message, sw - 60), True, message_color)
        screen.blit(msg_s, (sw // 2 - msg_s.get_width() // 2, sh - 30))

        back_button.draw()
        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                conn.close()
                return False
            if back_button.handle_event(event):
                conn.close()
                return True
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                conn.close()
                return True
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                if bonus_rect.collidepoint(pos):
                    ok, msg = claim_casino_daily_bonus(player_name)
                    push_message(msg, (180, 240, 190) if ok else (255, 190, 130))
                    continue
                if buyin_rect.collidepoint(pos):
                    ok, msg = buy_in()
                    push_message(msg, (180, 240, 190) if ok else (255, 190, 130))
                    continue
                clicked_game = None
                for game in game_cards:
                    if game['play_rect'].collidepoint(pos):
                        clicked_game = game['game_key']
                        break
                if clicked_game == 'blackjack':
                    keep_running = blackjack_screen(player_name, conn, get_total_chips, add_total_chips, subtract_total_chips, 'Chips', logger)
                    if not keep_running:
                        conn.close()
                        return False
                    continue
                if clicked_game == 'roulette':
                    keep_running = roulette_screen(player_name, conn, get_total_chips, add_total_chips, subtract_total_chips, 'Chips', logger)
                    if not keep_running:
                        conn.close()
                        return False
                    continue
                if clicked_game == 'slots':
                    keep_running = slot_machine_screen(player_name, conn, get_total_chips, add_total_chips, subtract_total_chips, 'Chips', logger)
                    if not keep_running:
                        conn.close()
                        return False
                    continue
                if clicked_game == 'skillshot':
                    keep_running = safecracker_screen(player_name, conn, get_total_chips, add_total_chips, subtract_total_chips, logger)
                    if not keep_running:
                        conn.close()
                        return False
                    continue
                for reward_key, rect in reward_buttons:
                    if rect.collidepoint(pos):
                        ok, msg = purchase_casino_reward(player_name, reward_key)
                        push_message(msg, (180, 240, 190) if ok else (255, 190, 130))
                        break