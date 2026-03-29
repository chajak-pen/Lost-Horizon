import pygame
from ui_helpers import fit_text, draw_wrapped_text

from database import (
    CRAFTING_RECIPES,
    attempt_prestige,
    get_casino_profile,
    get_casino_vip_status,
    get_custom_level_metrics,
    get_friends,
    get_player_performance_summary,
    list_public_custom_levels,
    claim_quest_reward,
    craft_cosmetic,
    get_player_cosmetics,
    get_player_quests,
    get_prestige_profile,
)


def _build_featured_playlist(limit=3):
    candidates = list_public_custom_levels(limit=32)
    ranked = []
    for row in candidates:
        metrics = get_custom_level_metrics(row.get('custom_level_id', 0))
        likes = int(metrics.get('likes', 0))
        clears = int(metrics.get('clears', 0))
        plays = int(metrics.get('plays', 0))
        score = likes * 3 + clears * 2 + min(plays, 240) // 12
        ranked.append({
            'level_id': int(row.get('custom_level_id', 0)),
            'name': str(row.get('level_name') or 'Untitled Run'),
            'owner': str(row.get('owner_name') or 'Unknown'),
            'theme': str(row.get('theme') or 'world1'),
            'likes': likes,
            'clears': clears,
            'plays': plays,
            'score': score,
            'updated': str(row.get('updated_date') or ''),
        })

    ranked.sort(key=lambda r: (r['score'], r['likes'], r['updated']), reverse=True)
    return ranked[:max(0, int(limit))]


def _build_hub_npc_dialogue(player_name, quest_rows, prestige, vip_status, friends, featured_levels):
    completed_unclaimed = sum(1 for q in quest_rows if q.get('completed') and not q.get('claimed'))
    prestige_level = int(prestige.get('prestige_level', 0))
    vip_label = str(vip_status.get('tier_label') or 'Bronze Lobby')
    rep_to_next = int(vip_status.get('reputation_to_next') or 0)
    best_feature = featured_levels[0]['name'] if featured_levels else 'no featured map yet'

    steward_line = (
        f"{completed_unclaimed} quest reward(s) are waiting. Cash them in for fresh supplies."
        if completed_unclaimed > 0
        else "No claims pending. Keep your streak alive and the quartermaster will cut better deals."
    )
    archivist_line = (
        f"Prestige Lv {prestige_level} looks strong. Our featured board highlights '{best_feature}'."
        if prestige_level > 0
        else "Build your first prestige cycle. Featured creator runs help you learn cleaner routing."
    )
    host_line = (
        f"Casino standing: {vip_label}. Next lounge unlock in {rep_to_next} reputation."
        if rep_to_next > 0
        else f"Casino standing: {vip_label}. You have full VIP access right now."
    )
    social_line = (
        f"{len(friends)} friend(s) are linked. Weekly social races are now available from the playlist board."
        if friends
        else "Add a rival to your friends list for faster social challenge rotation."
    )

    return [
        {'name': 'Steward Rook', 'role': 'Hub Quartermaster', 'line': steward_line, 'tone': (255, 220, 145)},
        {'name': 'Archivist Vale', 'role': 'Playlist Curator', 'line': archivist_line, 'tone': (170, 235, 200)},
        {'name': 'Host Mirra', 'role': 'Social Concierge', 'line': host_line, 'tone': (165, 205, 255)},
        {'name': 'Courier Nox', 'role': 'Friend Link Relay', 'line': social_line, 'tone': (225, 190, 255)},
    ]


def progression_hub_screen(player_name):
    screen = pygame.display.get_surface()
    if screen is None:
        info = pygame.display.Info()
        screen = pygame.display.set_mode((info.current_w, info.current_h))

    title_font = pygame.font.SysFont("Arial", 42, bold=True)
    head_font = pygame.font.SysFont("Arial", 24, bold=True)
    body_font = pygame.font.SysFont("Arial", 21)
    hint_font = pygame.font.SysFont("Arial", 18)
    clock = pygame.time.Clock()
    status = "Progression hub ready"
    refresh_timer = 0.0

    daily = []
    weekly = []
    prestige = {'prestige_level': 0, 'prestige_points': 0}
    cosmetics = {}
    casino_profile = {'reputation': 0}
    vip_status = {'tier_label': 'Bronze Lobby', 'reputation_to_next': 0}
    friends = []
    featured = []
    npc_cards = []
    perf_summary = {'runs_sampled': 0, 'avg_fps': None, 'avg_frame_ms': None, 'p95_frame_ms': None, 'perf_spikes': 0}

    while True:
        dt = clock.tick(60) / 1000.0
        refresh_timer -= dt
        if refresh_timer <= 0.0:
            daily = get_player_quests(player_name, period='daily')
            weekly = get_player_quests(player_name, period='weekly')
            prestige = get_prestige_profile(player_name)
            cosmetics = get_player_cosmetics(player_name)
            casino_profile = get_casino_profile(player_name)
            vip_status = get_casino_vip_status(reputation=casino_profile.get('reputation', 0))
            friends = get_friends(player_name)
            featured = _build_featured_playlist(limit=3)
            npc_cards = _build_hub_npc_dialogue(player_name, daily + weekly, prestige, vip_status, friends, featured)
            perf_summary = get_player_performance_summary(player_name, sample_limit=24)
            refresh_timer = 0.7

        screen.fill((12, 20, 34))
        title = title_font.render("Progression Hub", True, (235, 242, 255))
        screen.blit(title, (screen.get_width() // 2 - title.get_width() // 2, 18))

        top_h = max(240, int(screen.get_height() * 0.54))
        left = pygame.Rect(24, 90, screen.get_width() // 2 - 36, top_h)
        right = pygame.Rect(screen.get_width() // 2 + 12, 90, screen.get_width() // 2 - 36, top_h)
        bottom_y = left.bottom + 10
        bottom_h = max(110, screen.get_height() - bottom_y - 70)
        social = pygame.Rect(24, bottom_y, screen.get_width() // 2 - 36, bottom_h)
        npc = pygame.Rect(screen.get_width() // 2 + 12, bottom_y, screen.get_width() // 2 - 36, bottom_h)

        for panel in (left, right, social, npc):
            pygame.draw.rect(screen, (24, 38, 62), panel, border_radius=10)
            pygame.draw.rect(screen, (92, 140, 202), panel, 2, border_radius=10)

        daily_head = head_font.render("Daily / Weekly Quests", True, (255, 220, 140))
        screen.blit(daily_head, (left.x + 12, left.y + 10))
        y = left.y + 44
        quest_line_h = max(24, body_font.get_height() + 6)
        quest_max = max(4, (left.height - 70) // quest_line_h)
        quest_rows = daily + weekly
        for row in quest_rows[:quest_max]:
            pct = f"{row['progress']}/{row['target']}"
            flag = "CLAIMED" if row['claimed'] else "DONE" if row['completed'] else "ACTIVE"
            label = str(row.get('label') or row['quest_key'])
            category = str(row.get('category') or 'core').upper()
            period_tag = 'D' if row.get('period') == 'daily' else 'W'
            quest_text = fit_text(body_font, f"{period_tag}/{category[:3]}  {label}  {pct}  +{row['reward']}  [{flag}]", left.width - 24)
            line = body_font.render(quest_text, True, (232, 236, 245))
            screen.blit(line, (left.x + 12, y))
            y += quest_line_h
        if len(quest_rows) > quest_max:
            more_q = body_font.render(f"... and {len(quest_rows) - quest_max} more quests", True, (175, 195, 220))
            screen.blit(more_q, (left.x + 12, min(left.bottom - 30, y + 4)))

        right_head = head_font.render("Crafting + Prestige", True, (160, 230, 190))
        screen.blit(right_head, (right.x + 12, right.y + 10))
        y2 = right.y + 44
        recipe_line_h = max(24, body_font.get_height() + 6)
        recipe_max = max(3, (right.height - 165) // recipe_line_h)
        recipe_items = list(CRAFTING_RECIPES.items())
        for idx, (recipe_key, recipe) in enumerate(recipe_items[:recipe_max], start=1):
            line = body_font.render(
                fit_text(body_font, f"{idx}. {recipe_key} -> {recipe['yield']} ({recipe['cost']} coins)", right.width - 24),
                True,
                (230, 240, 230),
            )
            screen.blit(line, (right.x + 12, y2))
            y2 += recipe_line_h

        if len(recipe_items) > recipe_max:
            more_r = body_font.render(f"... and {len(recipe_items) - recipe_max} more recipes", True, (175, 205, 180))
            screen.blit(more_r, (right.x + 12, y2))
            y2 += recipe_line_h

        y2 += 8
        prestige_txt = body_font.render(
            f"Prestige Lv {prestige['prestige_level']}  Points {prestige['prestige_points']}",
            True,
            (255, 210, 130),
        )
        screen.blit(prestige_txt, (right.x + 12, y2))
        y2 += 30

        owned = ", ".join(f"{k}x{v}" for k, v in sorted(cosmetics.items()) if v > 0) or "None"
        draw_wrapped_text(screen, body_font, f"Crafted: {owned}", (185, 225, 255), pygame.Rect(right.x + 12, y2, right.width - 24, right.height - 40), line_gap=3, max_lines=4)

        social_head = head_font.render("Weekly Featured Playlist", True, (255, 215, 145))
        screen.blit(social_head, (social.x + 12, social.y + 10))
        social_meta = body_font.render(
            fit_text(body_font, f"Friends linked: {len(friends)}   VIP: {vip_status.get('tier_label', 'Bronze Lobby')}", social.width - 24),
            True,
            (220, 230, 240),
        )
        screen.blit(social_meta, (social.x + 12, social.y + 44))

        avg_fps = perf_summary.get('avg_fps')
        avg_ms = perf_summary.get('avg_frame_ms')
        p95_ms = perf_summary.get('p95_frame_ms')
        sampled = int(perf_summary.get('runs_sampled') or 0)
        spikes = int(perf_summary.get('perf_spikes') or 0)
        if sampled > 0 and avg_fps is not None and avg_ms is not None and p95_ms is not None:
            perf_line = f"Perf snapshot ({sampled} runs): {avg_fps:.1f} FPS, {avg_ms:.1f}ms avg, {p95_ms:.1f}ms p95, spikes {spikes}"
        else:
            perf_line = "Perf snapshot: gather data by finishing a few runs (debug/perf overlay can stay on)."
        perf_txt = body_font.render(fit_text(body_font, perf_line, social.width - 24), True, (190, 220, 255))
        screen.blit(perf_txt, (social.x + 12, social.y + 72))

        sy = social.y + 102
        if featured:
            for idx, row in enumerate(featured, start=1):
                line_txt = f"{idx}. {row['name']} by {row['owner']}  [L{row['likes']} C{row['clears']}]"
                line = body_font.render(fit_text(body_font, line_txt, social.width - 24), True, (235, 238, 246))
                screen.blit(line, (social.x + 12, sy))
                sy += max(24, body_font.get_height() + 4)
        else:
            none_txt = body_font.render("No public levels are featured yet.", True, (185, 195, 215))
            screen.blit(none_txt, (social.x + 12, sy))

        npc_head = head_font.render("Hub NPC Briefings", True, (195, 225, 255))
        screen.blit(npc_head, (npc.x + 12, npc.y + 10))
        ny = npc.y + 44
        row_h = max(44, int((npc.height - 52) / max(1, len(npc_cards))))
        for card in npc_cards:
            name_line = body_font.render(
                fit_text(body_font, f"{card['name']} - {card['role']}", npc.width - 24),
                True,
                card['tone'],
            )
            screen.blit(name_line, (npc.x + 12, ny))
            draw_wrapped_text(
                screen,
                hint_font,
                str(card.get('line') or ''),
                (220, 226, 236),
                pygame.Rect(npc.x + 12, ny + 22, npc.width - 24, row_h - 20),
                line_gap=2,
                max_lines=2,
            )
            ny += row_h

        draw_wrapped_text(screen, hint_font, "C claim first completed quest  1/2/3 craft  P prestige  R refresh board  Esc back", (180, 205, 235), pygame.Rect(40, screen.get_height() - 64, screen.get_width() - 80, 32), align="center", max_lines=2)
        status_txt = hint_font.render(status, True, (230, 220, 170))
        screen.blit(status_txt, (screen.get_width() // 2 - status_txt.get_width() // 2, screen.get_height() - 28))

        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return True
                if event.key == pygame.K_c:
                    pool = [q for q in (daily + weekly) if q['completed'] and not q['claimed']]
                    if pool:
                        ok, msg = claim_quest_reward(player_name, pool[0]['quest_key'], period=pool[0]['period'])
                        status = msg if ok else msg
                        refresh_timer = 0.0
                    else:
                        status = "No claimable quests right now"
                if event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    recipe_keys = list(CRAFTING_RECIPES.keys())
                    idx = event.key - pygame.K_1
                    if idx < len(recipe_keys):
                        ok, msg = craft_cosmetic(player_name, recipe_keys[idx])
                        status = msg if ok else msg
                        refresh_timer = 0.0
                if event.key == pygame.K_p:
                    ok, msg = attempt_prestige(player_name)
                    status = msg if ok else msg
                    refresh_timer = 0.0
                if event.key == pygame.K_r:
                    refresh_timer = 0.0
                    status = "Hub boards refreshed"
