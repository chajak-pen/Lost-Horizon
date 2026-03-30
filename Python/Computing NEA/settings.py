import os
import pygame
from Classes import Text, Button, resolve_asset_path
from game_settings import load_settings, save_settings, MUSIC_PATH, DEFAULT_KEYBINDS
from database import is_hard_mode_unlocked, is_hard_mode_enabled, set_hard_mode, create_connection
from ui_helpers import draw_tab_button, draw_card_panel, draw_wrapped_text, load_system_cursor, apply_hover_cursor

pygame.init()

info = pygame.display.Info()
screen_width, screen_height = info.current_w, info.current_h

CONTROL_LAYOUTS = {
    "hybrid": {
        "label": "Hybrid (WASD + Arrows)",
        "keybinds": {
            "move_left": ["a", "left"],
            "move_right": ["d", "right"],
            "jump": ["space", "w", "up"],
            "pause": ["p"],
            "ghost_toggle": ["g"],
            "debug_overlay": ["f3"],
            "dash": ["lshift", "rshift"],
            "slide": ["s", "down"],
            "select_power_1": ["1"],
            "select_power_2": ["2"],
            "select_power_3": ["3"],
            "activate_power": ["e"],
        },
    },
    "arrow": {
        "label": "Arrow Focused",
        "keybinds": {
            "move_left": ["left"],
            "move_right": ["right"],
            "jump": ["up", "space"],
            "pause": ["p"],
            "ghost_toggle": ["g"],
            "debug_overlay": ["f3"],
            "dash": ["rshift"],
            "slide": ["down"],
            "select_power_1": ["1"],
            "select_power_2": ["2"],
            "select_power_3": ["3"],
            "activate_power": ["e"],
        },
    },
    "legacy": {
        "label": "Legacy Classic",
        "keybinds": {
            "move_left": ["a"],
            "move_right": ["d"],
            "jump": ["space"],
            "pause": ["p"],
            "ghost_toggle": ["g"],
            "debug_overlay": ["f3"],
            "dash": ["lshift"],
            "slide": ["s"],
            "select_power_1": ["1"],
            "select_power_2": ["2"],
            "select_power_3": ["3"],
            "activate_power": ["e"],
        },
    },
}


def _next_control_layout(layout_name):
    keys = list(CONTROL_LAYOUTS.keys())
    if layout_name not in keys:
        return keys[0]
    idx = keys.index(layout_name)
    return keys[(idx + 1) % len(keys)]


ACTION_LABELS = {
    "move_left": "Move Left",
    "move_right": "Move Right",
    "jump": "Jump",
    "pause": "Pause",
    "ghost_toggle": "Ghost Replay Toggle",
    "debug_overlay": "Debug Overlay",
    "dash": "Dash",
    "slide": "Slide",
    "select_power_1": "Select Power Slot 1 (Float)",
    "select_power_2": "Select Power Slot 2 (Invincibility)",
    "select_power_3": "Select Power Slot 3 (Fire)",
    "activate_power": "Activate Selected Power",
}


def _normalize_keybinds(raw_keybinds):
    keybinds = {}
    source = raw_keybinds if isinstance(raw_keybinds, dict) else {}
    for action, fallback in DEFAULT_KEYBINDS.items():
        candidate = source.get(action)
        if isinstance(candidate, list):
            cleaned = [str(k).lower() for k in candidate if str(k).strip()]
            keybinds[action] = cleaned if cleaned else list(fallback)
        else:
            keybinds[action] = list(fallback)
    return keybinds


def _format_key_name(name):
    txt = str(name or "").strip().lower()
    if not txt:
        return ""
    aliases = {
        "left": "Left Arrow",
        "right": "Right Arrow",
        "up": "Up Arrow",
        "down": "Down Arrow",
        "space": "Space",
        "lshift": "Left Shift",
        "rshift": "Right Shift",
        "return": "Enter",
        "esc": "Escape",
    }
    if txt in aliases:
        return aliases[txt]
    return txt.replace("_", " ").title()


def _control_layout_label(layout_name):
    if layout_name in CONTROL_LAYOUTS:
        return CONTROL_LAYOUTS[layout_name]["label"]
    return "Custom"

def settings_menu(player_name=None):
    settings_screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Lost Horizon - Settings Menu")

    background = None
    for bg_path in ("settings_background.png", "background.jpg", "background.png"):
        resolved_bg_path = resolve_asset_path(bg_path)
        if os.path.exists(resolved_bg_path):
            try:
                background = pygame.image.load(resolved_bg_path).convert_alpha()
                background = pygame.transform.scale(background, (screen_width, screen_height))
                break
            except Exception:
                continue
    if background is None:
        background = pygame.Surface((screen_width, screen_height))
        background.fill((15, 20, 28))
    
    # scale UI elements relative to a 1000x600 baseline
    sx = screen_width / 1000.0
    sy = screen_height / 600.0
    back_size = max(24, int(screen_width * 0.04))
    back_image = pygame.image.load(resolve_asset_path("back button.jpg")).convert_alpha()
    back_image = pygame.transform.scale(back_image, (back_size, back_size))
    back_button = Button(int(15 * sx), int(15 * sy), back_image)
    
    title_font = pygame.font.SysFont("Arial", max(24, int(52 * sy)), bold=True)
    label_font = pygame.font.SysFont("Arial", max(14, int(28 * sy)))

    # Check hard mode status (only if player_name is available)
    hard_mode_unlocked = is_hard_mode_unlocked(player_name) if player_name else False
    
    # load persisted settings
    settings = load_settings()
    music_on = settings.get("music_on", True)
    sfx_on = settings.get("sfx_on", True)
    music_volume = settings.get("music_volume", 0.5)
    sfx_volume = settings.get("sfx_volume", 0.6)
    control_layout = settings.get("control_layout", "hybrid")
    accessibility = dict(settings.get("accessibility", {}))
    accessibility.setdefault("high_contrast_hud", False)
    accessibility.setdefault("reduced_screen_shake", False)
    accessibility.setdefault("extended_jump_buffer", False)
    accessibility.setdefault("training_hints", True)
    accessibility.setdefault("hud_simplified", False)
    accessibility.setdefault("colorblind_safe_palette", False)
    accessibility.setdefault("performance_overlay", False)
    hard_mode_enabled = is_hard_mode_enabled(player_name) if hard_mode_unlocked and player_name else False
    easy_mode = bool(settings.get("easy_mode", False))
    control_keybinds = _normalize_keybinds(settings.get("keybinds", {}))
    control_actions = list(DEFAULT_KEYBINDS.keys())
    selected_action_index = 0
    awaiting_bind = None

    # Multi-page settings: less compact and grouped by behavior.
    pages = ["audio", "gameplay", "controls", "accessibility"]
    page_titles = {
        "audio": "Audio",
        "gameplay": "Gameplay",
        "controls": "Controls",
        "accessibility": "Accessibility",
    }
    current_page = "audio"

    tabs_y = int(120 * sy)
    tab_h = max(34, int(44 * sy))
    tab_gap = max(10, int(12 * sx))
    panel_x = int(70 * sx)
    panel_y = tabs_y + tab_h + max(14, int(20 * sy))
    panel_w = screen_width - int(140 * sx)
    panel_h = screen_height - panel_y - int(48 * sy)

    row_gap = max(62, int(78 * sy))
    label_x = panel_x + int(26 * sx)
    value_x = panel_x + int(panel_w * 0.62)
    control_w = max(120, int(panel_w * 0.30))
    control_h = max(30, int(40 * sy))
    slider_w = max(260, int(panel_w * 0.52))
    slider_h = max(10, int(14 * sy))

    tab_rects = {}
    tab_total_w = 0
    temp_widths = {}
    for p in pages:
        w = max(150, int(190 * sx))
        temp_widths[p] = w
        tab_total_w += w
    tab_total_w += tab_gap * (len(pages) - 1)
    tx = (screen_width - tab_total_w) // 2
    for p in pages:
        w = temp_widths[p]
        tab_rects[p] = pygame.Rect(tx, tabs_y, w, tab_h)
        tx += w + tab_gap

    def _row_y(index):
        return panel_y + int(32 * sy) + index * row_gap

    def _toggle_rect(index):
        return pygame.Rect(value_x, _row_y(index), control_w, control_h)

    def _slider_rect(index):
        return pygame.Rect(value_x, _row_y(index) + int(control_h * 0.2), slider_w, slider_h)

    def _control_rect(index):
        return pygame.Rect(value_x, _row_y(index), control_w, control_h)

    def draw_toggle(rect, enabled, hovered=False, on_col=(115, 245, 155), off_col=(220, 120, 120), bg_hover=(60, 90, 140), bg_idle=(40, 60, 110)):
        bg_col = bg_hover if hovered else bg_idle
        shadow = rect.copy()
        shadow.y += 2
        pygame.draw.rect(settings_screen, (0, 0, 0), shadow, border_radius=8)
        pygame.draw.rect(settings_screen, bg_col, rect, border_radius=8)
        pygame.draw.rect(settings_screen, (120, 175, 235), rect, 2, border_radius=8)
        knob_r = max(8, rect.h // 3)
        knob_pad = 6
        knob_x = rect.x + (rect.w - knob_pad - knob_r) if enabled else rect.x + knob_pad + knob_r
        pygame.draw.circle(settings_screen, on_col if enabled else off_col, (knob_x, rect.y + rect.h // 2), knob_r)

    def draw_slider(rect, value, hovered=False):
        shadow_rect = rect.copy()
        shadow_rect.y += 2
        pygame.draw.rect(settings_screen, (0, 0, 0), shadow_rect, border_radius=4)
        pygame.draw.rect(settings_screen, (60, 70, 90), rect, border_radius=4)
        pygame.draw.rect(settings_screen, (100, 150, 200), rect, 2, border_radius=4)
        filled_w = max(1, int(value * rect.w))
        pygame.draw.rect(settings_screen, (100, 180, 255), (rect.x, rect.y, filled_w, rect.h), border_radius=4)
        knob_x = rect.x + int(value * rect.w)
        knob_col = (150, 220, 255) if hovered else (100, 180, 255)
        pygame.draw.circle(settings_screen, knob_col, (knob_x, rect.y + rect.h // 2), max(8, int(12 * sy)))

    dragging_music_slider = False
    dragging_sfx_slider = False

    hand_cursor = load_system_cursor(pygame.SYSTEM_CURSOR_HAND)
    arrow_cursor = load_system_cursor(pygame.SYSTEM_CURSOR_ARROW)
    current_cursor = None
    mouse_pos = (0, 0)

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        
        interactive = [back_button.rect]
        interactive.extend(tab_rects.values())

        if current_page == "audio":
            interactive.extend([_toggle_rect(0), _toggle_rect(1), _slider_rect(2), _slider_rect(3)])
        elif current_page == "gameplay":
            interactive.extend([_toggle_rect(0), _toggle_rect(1)])
        elif current_page == "controls":
            interactive.extend([
                _control_rect(0),
                _control_rect(1),
                _control_rect(2),
                _control_rect(3),
                _control_rect(4),
                _control_rect(5),
            ])
        elif current_page == "accessibility":
            interactive.extend([_toggle_rect(0), _toggle_rect(1), _toggle_rect(2), _toggle_rect(3), _toggle_rect(4), _toggle_rect(5), _toggle_rect(6)])

        hovering_toggle = any(r.collidepoint(mouse_pos) for r in interactive)
        
        # Set cursor based on hover
        current_cursor = apply_hover_cursor(hovering_toggle, hand_cursor, arrow_cursor, current_cursor)
        
        settings_screen.blit(background, (0, 0))
        
        # Draw semi-transparent overlay for consistency
        overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
        overlay.fill((10, 10, 20, 40))
        settings_screen.blit(overlay, (0, 0))
        
        # Draw title with styling
        title_text = title_font.render("Settings", True, (150, 200, 255))
        title_shadow = title_font.render("Settings", True, (0, 0, 0))
        title_x = screen_width // 2 - title_text.get_width() // 2
        title_y = int(screen_height * 0.02)
        settings_screen.blit(title_shadow, (title_x + 2, title_y + 2))
        settings_screen.blit(title_text, (title_x, title_y))
        
        # Draw decorative line under title
        pygame.draw.line(settings_screen, (100, 180, 255), (title_x - 20, title_y + title_text.get_height() + 10), 
                        (title_x + title_text.get_width() + 20, title_y + title_text.get_height() + 10), 3)

        for p in pages:
            rect = tab_rects[p]
            draw_tab_button(settings_screen, rect, page_titles[p], label_font, active=(p == current_page))

        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
        draw_card_panel(settings_screen, panel_rect)

        section_title = title_font.render(page_titles[current_page], True, (180, 220, 255))
        settings_screen.blit(section_title, (panel_rect.x + 20, panel_rect.y + 10))

        if current_page == "audio":
            m_rect = _toggle_rect(0)
            s_rect = _toggle_rect(1)
            mv_rect = _slider_rect(2)
            sv_rect = _slider_rect(3)

            settings_screen.blit(label_font.render("Music", True, (170, 215, 255)), (label_x, m_rect.y + 4))
            draw_toggle(m_rect, music_on, hovered=m_rect.collidepoint(mouse_pos))

            settings_screen.blit(label_font.render("SFX", True, (170, 215, 255)), (label_x, s_rect.y + 4))
            draw_toggle(s_rect, sfx_on, hovered=s_rect.collidepoint(mouse_pos))

            settings_screen.blit(label_font.render("Music Volume", True, (170, 215, 255)), (label_x, mv_rect.y - 16))
            draw_slider(mv_rect, music_volume, hovered=mv_rect.collidepoint(mouse_pos))
            settings_screen.blit(label_font.render(f"{int(music_volume * 100)}%", True, (170, 215, 255)), (mv_rect.right + 12, mv_rect.y - 8))

            settings_screen.blit(label_font.render("SFX Volume", True, (170, 215, 255)), (label_x, sv_rect.y - 16))
            draw_slider(sv_rect, sfx_volume, hovered=sv_rect.collidepoint(mouse_pos))
            settings_screen.blit(label_font.render(f"{int(sfx_volume * 100)}%", True, (170, 215, 255)), (sv_rect.right + 12, sv_rect.y - 8))

        elif current_page == "gameplay":
            hm_rect = _toggle_rect(0)
            em_rect = _toggle_rect(1)
            if hard_mode_unlocked:
                settings_screen.blit(label_font.render("Hard Mode", True, (255, 205, 140)), (label_x, hm_rect.y + 4))
                draw_toggle(hm_rect, hard_mode_enabled, hovered=hm_rect.collidepoint(mouse_pos), on_col=(255, 180, 100), off_col=(150, 80, 80), bg_hover=(120, 80, 60), bg_idle=(100, 60, 40))
            else:
                lock_msg = "Hard Mode unlocks after normal progression milestones."
                settings_screen.blit(label_font.render(lock_msg, True, (140, 150, 175)), (label_x, hm_rect.y + 4))

            settings_screen.blit(label_font.render("Easy Mode (Training Ground)", True, (170, 215, 255)), (label_x, em_rect.y + 4))
            draw_toggle(em_rect, easy_mode, hovered=em_rect.collidepoint(mouse_pos), on_col=(135, 240, 165), off_col=(150, 95, 95), bg_hover=(74, 112, 76), bg_idle=(58, 88, 62))

            note = "No level locks, no fall-off deaths, static enemies, slower enemy fire"
            draw_wrapped_text(
                settings_screen,
                label_font,
                note,
                (165, 190, 225),
                pygame.Rect(label_x, em_rect.y + int(34 * sy), panel_rect.right - label_x - 24, int(70 * sy)),
                line_gap=2,
            )

        elif current_page == "controls":
            selected_action = control_actions[selected_action_index]
            selected_keys = control_keybinds.get(selected_action, [])

            cl_rect = _control_rect(0)
            act_rect = _control_rect(1)
            replace_rect = _control_rect(2)
            add_rect = _control_rect(3)
            clear_rect = _control_rect(4)
            reset_rect = _control_rect(5)

            settings_screen.blit(label_font.render("Control Layout Preset", True, (170, 215, 255)), (label_x, cl_rect.y + 4))
            pygame.draw.rect(settings_screen, (35, 60, 96), cl_rect, border_radius=8)
            pygame.draw.rect(settings_screen, (120, 180, 245), cl_rect, 2, border_radius=8)
            layout_txt = label_font.render(_control_layout_label(control_layout), True, (240, 245, 255))
            settings_screen.blit(layout_txt, (cl_rect.x + 10, cl_rect.y + (cl_rect.h - layout_txt.get_height()) // 2))

            settings_screen.blit(label_font.render("Editing Action", True, (170, 215, 255)), (label_x, act_rect.y + 4))
            pygame.draw.rect(settings_screen, (35, 60, 96), act_rect, border_radius=8)
            pygame.draw.rect(settings_screen, (120, 180, 245), act_rect, 2, border_radius=8)
            action_txt = label_font.render(ACTION_LABELS.get(selected_action, selected_action.replace("_", " ").title()), True, (240, 245, 255))
            settings_screen.blit(action_txt, (act_rect.x + 10, act_rect.y + (act_rect.h - action_txt.get_height()) // 2))

            settings_screen.blit(label_font.render("Replace Primary Key", True, (170, 215, 255)), (label_x, replace_rect.y + 4))
            pygame.draw.rect(settings_screen, (45, 80, 120), replace_rect, border_radius=8)
            pygame.draw.rect(settings_screen, (120, 190, 245), replace_rect, 2, border_radius=8)
            replace_txt = label_font.render("Press To Rebind", True, (240, 245, 255))
            settings_screen.blit(replace_txt, (replace_rect.x + 10, replace_rect.y + (replace_rect.h - replace_txt.get_height()) // 2))

            settings_screen.blit(label_font.render("Add Secondary Key", True, (170, 215, 255)), (label_x, add_rect.y + 4))
            pygame.draw.rect(settings_screen, (45, 80, 120), add_rect, border_radius=8)
            pygame.draw.rect(settings_screen, (120, 190, 245), add_rect, 2, border_radius=8)
            add_txt = label_font.render("Press To Add", True, (240, 245, 255))
            settings_screen.blit(add_txt, (add_rect.x + 10, add_rect.y + (add_rect.h - add_txt.get_height()) // 2))

            settings_screen.blit(label_font.render("Clear Current Action", True, (170, 215, 255)), (label_x, clear_rect.y + 4))
            pygame.draw.rect(settings_screen, (110, 55, 55), clear_rect, border_radius=8)
            pygame.draw.rect(settings_screen, (230, 130, 130), clear_rect, 2, border_radius=8)
            clear_txt = label_font.render("Reset This Action", True, (250, 235, 235))
            settings_screen.blit(clear_txt, (clear_rect.x + 10, clear_rect.y + (clear_rect.h - clear_txt.get_height()) // 2))

            settings_screen.blit(label_font.render("Reset All Keybinds", True, (170, 215, 255)), (label_x, reset_rect.y + 4))
            pygame.draw.rect(settings_screen, (90, 55, 95), reset_rect, border_radius=8)
            pygame.draw.rect(settings_screen, (210, 145, 235), reset_rect, 2, border_radius=8)
            reset_txt = label_font.render("Restore Defaults", True, (250, 240, 255))
            settings_screen.blit(reset_txt, (reset_rect.x + 10, reset_rect.y + (reset_rect.h - reset_txt.get_height()) // 2))

            current_keys_line = " / ".join(_format_key_name(k) for k in selected_keys) if selected_keys else "None"
            draw_wrapped_text(
                settings_screen,
                label_font,
                f"Current binds: {current_keys_line}",
                (190, 210, 235),
                pygame.Rect(label_x, _row_y(6), panel_rect.right - label_x - 24, int(60 * sy)),
                line_gap=2,
            )

            if awaiting_bind:
                mode_txt = "replace" if awaiting_bind == "replace" else "add"
                draw_wrapped_text(
                    settings_screen,
                    label_font,
                    f"Press any key to {mode_txt}. Press Escape to cancel.",
                    (255, 220, 160),
                    pygame.Rect(label_x, _row_y(7), panel_rect.right - label_x - 24, int(60 * sy)),
                    line_gap=2,
                )
            else:
                draw_wrapped_text(
                    settings_screen,
                    label_font,
                    "Tip: Click the action row to cycle through all actions with keybinds.",
                    (150, 180, 220),
                    pygame.Rect(label_x, _row_y(7), panel_rect.right - label_x - 24, int(60 * sy)),
                    line_gap=2,
                )

        else:  # accessibility
            rs_rect = _toggle_rect(0)
            jb_rect = _toggle_rect(1)
            th_rect = _toggle_rect(2)
            hc_rect = _toggle_rect(3)
            hs_rect = _toggle_rect(4)
            cb_rect = _toggle_rect(5)
            po_rect = _toggle_rect(6)

            settings_screen.blit(label_font.render("Reduced Screen Shake", True, (170, 215, 255)), (label_x, rs_rect.y + 4))
            draw_toggle(rs_rect, accessibility.get("reduced_screen_shake", False), hovered=rs_rect.collidepoint(mouse_pos))

            settings_screen.blit(label_font.render("Extended Jump Buffer", True, (170, 215, 255)), (label_x, jb_rect.y + 4))
            draw_toggle(jb_rect, accessibility.get("extended_jump_buffer", False), hovered=jb_rect.collidepoint(mouse_pos))

            settings_screen.blit(label_font.render("Training Hints", True, (170, 215, 255)), (label_x, th_rect.y + 4))
            draw_toggle(th_rect, accessibility.get("training_hints", True), hovered=th_rect.collidepoint(mouse_pos))

            settings_screen.blit(label_font.render("High Contrast HUD", True, (170, 215, 255)), (label_x, hc_rect.y + 4))
            draw_toggle(hc_rect, accessibility.get("high_contrast_hud", False), hovered=hc_rect.collidepoint(mouse_pos))

            settings_screen.blit(label_font.render("Simplified HUD", True, (170, 215, 255)), (label_x, hs_rect.y + 4))
            draw_toggle(hs_rect, accessibility.get("hud_simplified", False), hovered=hs_rect.collidepoint(mouse_pos))

            settings_screen.blit(label_font.render("Colorblind-Safe Cues", True, (170, 215, 255)), (label_x, cb_rect.y + 4))
            draw_toggle(cb_rect, accessibility.get("colorblind_safe_palette", False), hovered=cb_rect.collidepoint(mouse_pos))

            settings_screen.blit(label_font.render("Performance Overlay", True, (170, 215, 255)), (label_x, po_rect.y + 4))
            draw_toggle(po_rect, accessibility.get("performance_overlay", False), hovered=po_rect.collidepoint(mouse_pos))
        
        # Draw back button with improved styling
        back_button.draw()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                return False

            if back_button.handle_event(event):
                return True

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                for p, r in tab_rects.items():
                    if r.collidepoint(mx, my):
                        current_page = p

                if current_page == "audio":
                    m_rect = _toggle_rect(0)
                    s_rect = _toggle_rect(1)
                    mv_rect = _slider_rect(2)
                    sv_rect = _slider_rect(3)

                    if m_rect.collidepoint(mx, my):
                        music_on = not music_on
                        settings["music_on"] = music_on
                        save_settings(settings)
                        try:
                            if music_on:
                                pygame.mixer.music.unpause()
                                if not pygame.mixer.music.get_busy() and os.path.exists(MUSIC_PATH):
                                    pygame.mixer.music.load(MUSIC_PATH)
                                    pygame.mixer.music.set_volume(music_volume)
                                    pygame.mixer.music.play(-1)
                            else:
                                pygame.mixer.music.pause()
                        except Exception:
                            pass

                    if s_rect.collidepoint(mx, my):
                        sfx_on = not sfx_on
                        settings["sfx_on"] = sfx_on
                        save_settings(settings)

                    if mv_rect.collidepoint(mx, my):
                        dragging_music_slider = True
                    if sv_rect.collidepoint(mx, my):
                        dragging_sfx_slider = True

                elif current_page == "gameplay":
                    hm_rect = _toggle_rect(0)
                    em_rect = _toggle_rect(1)
                    if hard_mode_unlocked and hm_rect.collidepoint(mx, my):
                        hard_mode_enabled = not hard_mode_enabled
                        if player_name:
                            conn = create_connection()
                            if conn:
                                set_hard_mode(conn, player_name, hard_mode_enabled)
                                conn.close()
                    if em_rect.collidepoint(mx, my):
                        easy_mode = not easy_mode
                        settings["easy_mode"] = easy_mode
                        save_settings(settings)

                elif current_page == "controls":
                    cl_rect = _control_rect(0)
                    act_rect = _control_rect(1)
                    replace_rect = _control_rect(2)
                    add_rect = _control_rect(3)
                    clear_rect = _control_rect(4)
                    reset_rect = _control_rect(5)
                    selected_action = control_actions[selected_action_index]

                    if cl_rect.collidepoint(mx, my):
                        control_layout = _next_control_layout(control_layout)
                        settings["control_layout"] = control_layout
                        control_keybinds = _normalize_keybinds(CONTROL_LAYOUTS[control_layout]["keybinds"])
                        settings["keybinds"] = control_keybinds
                        awaiting_bind = None
                        save_settings(settings)

                    elif act_rect.collidepoint(mx, my):
                        selected_action_index = (selected_action_index + 1) % len(control_actions)

                    elif replace_rect.collidepoint(mx, my):
                        awaiting_bind = "replace"

                    elif add_rect.collidepoint(mx, my):
                        awaiting_bind = "add"

                    elif clear_rect.collidepoint(mx, my):
                        control_keybinds[selected_action] = list(DEFAULT_KEYBINDS.get(selected_action, []))
                        settings["keybinds"] = control_keybinds
                        settings["control_layout"] = "custom"
                        control_layout = "custom"
                        awaiting_bind = None
                        save_settings(settings)

                    elif reset_rect.collidepoint(mx, my):
                        control_keybinds = _normalize_keybinds(DEFAULT_KEYBINDS)
                        settings["keybinds"] = control_keybinds
                        settings["control_layout"] = "hybrid"
                        control_layout = "hybrid"
                        awaiting_bind = None
                        save_settings(settings)

                else:
                    rs_rect = _toggle_rect(0)
                    jb_rect = _toggle_rect(1)
                    th_rect = _toggle_rect(2)
                    hc_rect = _toggle_rect(3)
                    hs_rect = _toggle_rect(4)
                    cb_rect = _toggle_rect(5)
                    po_rect = _toggle_rect(6)
                    if rs_rect.collidepoint(mx, my):
                        accessibility["reduced_screen_shake"] = not accessibility.get("reduced_screen_shake", False)
                        settings["accessibility"] = accessibility
                        save_settings(settings)
                    if jb_rect.collidepoint(mx, my):
                        accessibility["extended_jump_buffer"] = not accessibility.get("extended_jump_buffer", False)
                        settings["accessibility"] = accessibility
                        save_settings(settings)
                    if th_rect.collidepoint(mx, my):
                        accessibility["training_hints"] = not accessibility.get("training_hints", True)
                        settings["accessibility"] = accessibility
                        save_settings(settings)
                    if hc_rect.collidepoint(mx, my):
                        accessibility["high_contrast_hud"] = not accessibility.get("high_contrast_hud", False)
                        settings["accessibility"] = accessibility
                        save_settings(settings)
                    if hs_rect.collidepoint(mx, my):
                        accessibility["hud_simplified"] = not accessibility.get("hud_simplified", False)
                        settings["accessibility"] = accessibility
                        save_settings(settings)
                    if cb_rect.collidepoint(mx, my):
                        accessibility["colorblind_safe_palette"] = not accessibility.get("colorblind_safe_palette", False)
                        settings["accessibility"] = accessibility
                        save_settings(settings)
                    if po_rect.collidepoint(mx, my):
                        accessibility["performance_overlay"] = not accessibility.get("performance_overlay", False)
                        settings["accessibility"] = accessibility
                        save_settings(settings)

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                dragging_music_slider = False
                dragging_sfx_slider = False

            if event.type == pygame.MOUSEMOTION:
                if dragging_music_slider and current_page == "audio":
                    mv_rect = _slider_rect(2)
                    mx = event.pos[0]
                    music_volume = max(0, min(1, (mx - mv_rect.x) / mv_rect.w))
                    settings["music_volume"] = music_volume
                    save_settings(settings)
                    try:
                        pygame.mixer.music.set_volume(music_volume)
                    except Exception:
                        pass
                
                if dragging_sfx_slider and current_page == "audio":
                    sv_rect = _slider_rect(3)
                    mx = event.pos[0]
                    sfx_volume = max(0, min(1, (mx - sv_rect.x) / sv_rect.w))
                    settings["sfx_volume"] = sfx_volume
                    save_settings(settings)

            if event.type == pygame.KEYDOWN:
                if current_page == "controls" and awaiting_bind:
                    if event.key == pygame.K_ESCAPE:
                        awaiting_bind = None
                    else:
                        selected_action = control_actions[selected_action_index]
                        key_name = pygame.key.name(event.key).lower()
                        if key_name:
                            current = list(control_keybinds.get(selected_action, []))
                            if awaiting_bind == "replace":
                                updated = [key_name]
                            else:
                                updated = current if current else []
                                if key_name not in updated:
                                    updated.append(key_name)
                                if len(updated) > 3:
                                    updated = updated[-3:]
                            control_keybinds[selected_action] = updated
                            settings["keybinds"] = control_keybinds
                            settings["control_layout"] = "custom"
                            control_layout = "custom"
                            save_settings(settings)
                        awaiting_bind = None
                    continue

                if event.key == pygame.K_LEFT:
                    idx = pages.index(current_page)
                    current_page = pages[(idx - 1) % len(pages)]
                if event.key == pygame.K_RIGHT:
                    idx = pages.index(current_page)
                    current_page = pages[(idx + 1) % len(pages)]

        pygame.display.update()