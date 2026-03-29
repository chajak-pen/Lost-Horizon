import pygame
from database import get_analytics_heatmap
from ui_helpers import draw_wrapped_text, fit_text, wrap_text


def controls_screen(player_name=None):
    """Full-screen controls reference.  Returns True to keep the game running, False to quit."""
    screen = pygame.display.get_surface()
    if screen is None:
        return True

    sw, sh = screen.get_size()

    font_title = pygame.font.SysFont("Arial", max(30, int(36 * sh / 600)), bold=True)
    font_head  = pygame.font.SysFont("Arial", max(16, int(21 * sh / 600)), bold=True)
    font_body  = pygame.font.SysFont("Arial", max(13, int(16 * sh / 600)))
    font_hint  = pygame.font.SysFont("Arial", max(11, int(13 * sh / 600)))

    # (section_heading, [(key_label, description), ...])
    SECTIONS = [
        ("MOVEMENT", [
            ("← / A",                "Move Left"),
            ("→ / D",                "Move Right"),
            ("Space",                "Jump"),
            ("Space  (near wall)",   "Wall Jump — bounce off any wall, gain height"),
            ("Shift  (while airborne)", "Air Dash — burst forward in current direction  (once per jump)"),
            ("S  (ground + moving)", "Slide — speed boost; follow with Space for extra jump height"),
        ]),
        ("POWERS  (collect first)", [
            ("E",                      "Activate Float Power — gentle glide for 5 s"),
            ("R",                      "Activate Invincibility — 4 s immunity + speed"),
            ("Q",                      "Activate Fire Power — 12 s of ranged fire"),
            ("Left Click  (fire)", "Shoot a fire projectile in facing direction"),
        ]),
        ("COMBAT", [
            ("Jump on enemy",          "Stomp — instant kill, resets air-dash"),
            ("Build kill streak",      "Combo multiplier — every 5 kills triggers a Finisher bonus"),
            ("Use movement tech",      "Air Dash, Slide, Slide Jump, and Wall Jump also add Style Rank points"),
            ("Stay active",            "Combo decay — streak drops if no kill within 3 s"),
        ]),
        ("IN-LEVEL", [
            ("P",   "Pause / Resume"),
            ("G",   "Toggle Ghost Replay — translucent replay of your personal best"),
            ("F3",  "Debug Overlay — hitboxes, enemy states, patrol paths, frame-time and memory metrics"),
        ]),
        ("HUB WORLD", [
            ("N",                     "Toggle New Game+ — remixed enemy positions"),
            ("C  (near level door)",  "Generate Challenge Code — share your run conditions with friends"),
        ]),
        ("MENUS & LEADERBOARD", [
            ("Tab  (leaderboard)",  "Cycle stat metric:  Score → Time → Survival"),
            ("1",                   "Leaderboard scope: Per-Level"),
            ("2",                   "Leaderboard scope: Global"),
            ("3",                   "Leaderboard scope: Friends"),
            ("4",                   "Leaderboard scope: Weekly"),
            ("Esc",                 "Back / Close current menu"),
        ]),
    ]

    # ---- two-column layout constants ----
    margin = max(30, int(sw * 0.04))
    col_gap = max(20, int(sw * 0.03))
    col_w   = (sw - margin * 2 - col_gap) // 2
    col_xs  = [margin, margin + col_w + col_gap]

    scroll_y   = 0
    max_scroll = 0          # calculated after first render pass

    BG         = (8, 12, 28)
    HEAD_COL   = (240, 200, 70)
    KEY_COL    = (110, 200, 255)
    DESC_COL   = (210, 210, 210)
    LINE_COL   = (60, 90, 140)
    HINT_COL   = (80, 80, 110)

    KEY_AREA_W = max(160, int(col_w * 0.40))   # fixed width reserved for key label

    clock = pygame.time.Clock()
    onboarding_note = ""
    if player_name:
        # Use recent death hotspots as lightweight onboarding guidance.
        hot = get_analytics_heatmap(player_name, 2, event_type='death', limit=1)
        if hot:
            hx, hy, _ = hot[0]
            onboarding_note = f"Analytics Tip: Most deaths around zone ({hx}, {hy}). Practice jump timing + dash there."

    while True:
        # ---- events ----
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return True
                if event.key == pygame.K_UP:
                    scroll_y = max(0, scroll_y - 40)
                if event.key == pygame.K_DOWN:
                    scroll_y = min(max_scroll, scroll_y + 40)
            if event.type == pygame.MOUSEWHEEL:
                scroll_y = max(0, min(max_scroll, scroll_y - event.y * 35))

        # ---- draw ----
        screen.fill(BG)

        # Title
        title_surf = font_title.render("Controls  Reference", True, (180, 220, 255))
        title_y    = 18 - scroll_y
        screen.blit(title_surf, (sw // 2 - title_surf.get_width() // 2, title_y))
        pygame.draw.line(screen, (80, 130, 200),
                         (margin, title_y + title_surf.get_height() + 6),
                         (sw - margin, title_y + title_surf.get_height() + 6), 2)

        # Sections — alternate between left and right columns
        col_y  = [title_y + title_surf.get_height() + 20, title_y + title_surf.get_height() + 20]
        bottom = 0

        for sec_idx, (heading, entries) in enumerate(SECTIONS):
            ci   = sec_idx % 2          # column index
            cx   = col_xs[ci]
            cy   = col_y[ci]

            # Section heading
            head_surf = font_head.render(heading, True, HEAD_COL)
            screen.blit(head_surf, (cx, cy))
            cy += head_surf.get_height() + 3
            pygame.draw.line(screen, LINE_COL, (cx, cy), (cx + col_w, cy), 1)
            cy += 7

            for key_label, desc in entries:
                key_text = fit_text(font_body, key_label, KEY_AREA_W - 8)
                kl = font_body.render(key_text, True, KEY_COL)
                screen.blit(kl, (cx, cy))
                desc_rect = pygame.Rect(cx + KEY_AREA_W, cy, col_w - KEY_AREA_W - 6, sh)
                next_y = draw_wrapped_text(screen, font_body, desc, DESC_COL, desc_rect, line_gap=3)
                cy = max(cy + kl.get_height(), next_y) + 4

            cy += 16            # gap after each section
            col_y[ci] = cy
            bottom = max(bottom, cy)

        tip_lines = [
            "Movement Tips:",
            "  •  Air Dash extends your reach across wide gaps — use it while jumping over the air-dash challenge platforms in Level 1.",
            "  •  Wall Jump: press Space the instant you touch a wall to launch off it. Chain multiple walls to climb vertical shafts.",
            "  •  Slide + Jump: press S while running, then Space immediately for a boosted jump that clears taller ledges.",
        ]

        # Movement tips box
        tip_y = max(col_y) + 10
        wrapped_tip_lines = []
        for line in tip_lines:
            wrapped_tip_lines.extend(wrap_text(font_body, line, sw - margin * 2 - 28))
        tip_box_h = len(wrapped_tip_lines) * (font_body.get_height() + 3) + 24
        tip_rect  = pygame.Rect(margin, tip_y, sw - margin * 2, tip_box_h)
        pygame.draw.rect(screen, (18, 30, 55), tip_rect, border_radius=8)
        pygame.draw.rect(screen, (60, 100, 160), tip_rect, 2, border_radius=8)

        ty = tip_y + 10
        for i, line in enumerate(tip_lines):
            col = HEAD_COL if i == 0 else DESC_COL
            ty = draw_wrapped_text(
                screen,
                font_body,
                line,
                col,
                pygame.Rect(margin + 14, ty, sw - margin * 2 - 28, tip_box_h),
                line_gap=3,
            )

        if onboarding_note:
            ty = draw_wrapped_text(
                screen,
                font_body,
                onboarding_note,
                (165, 220, 255),
                pygame.Rect(margin + 14, ty + 4, sw - margin * 2 - 28, tip_box_h),
                line_gap=3,
            )
            bottom = max(bottom, ty + 20)

        bottom = max(bottom, tip_y + tip_box_h + 10)
        max_scroll = max(0, bottom + 40 - sh)

        # Hint bar at bottom
        hint_bg = pygame.Surface((sw, 30), pygame.SRCALPHA)
        hint_bg.fill((8, 12, 28, 220))
        screen.blit(hint_bg, (0, sh - 30))
        hint_surf = font_hint.render(
            "↑ / ↓  or  scroll wheel to navigate   •   ESC to return", True, HINT_COL)
        screen.blit(hint_surf, (sw // 2 - hint_surf.get_width() // 2, sh - 24))

        pygame.display.flip()
        clock.tick(60)
