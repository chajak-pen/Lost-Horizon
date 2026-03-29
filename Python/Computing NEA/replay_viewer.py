import pygame
import base64

from database import get_replay_timeline, list_replay_runs
from ui_helpers import fit_text, draw_wrapped_text


def replay_viewer_screen(player_name):
    screen = pygame.display.get_surface()
    if screen is None:
        info = pygame.display.Info()
        screen = pygame.display.set_mode((info.current_w, info.current_h))

    title_font = pygame.font.SysFont("Arial", 40, bold=True)
    row_font = pygame.font.SysFont("Arial", 22)
    hud_font = pygame.font.SysFont("Arial", 20)
    clock = pygame.time.Clock()

    selected = 0
    show_mine_only = False
    rows = list_replay_runs(None, limit=120)
    active = None
    active_frames = []
    playback_t = 0.0
    paused = False
    speed_steps = [0.5, 1.0, 1.5, 2.0, 3.0]
    speed_idx = 1
    show_path = True
    show_marker = True
    show_health = True
    video_frame_cache = {}

    while True:
        dt = clock.tick(60) / 1000.0
        rows = list_replay_runs(player_name if show_mine_only else None, limit=120, include_private=show_mine_only)
        if selected >= len(rows):
            selected = max(0, len(rows) - 1)

        if active and not paused:
            playback_t += dt * speed_steps[speed_idx]
            if active_frames:
                playback_t = min(playback_t, float(active_frames[-1].get("t", 0.0)))

        screen.fill((10, 16, 30))
        scope_label = "My Replays" if show_mine_only else "Global Replays"
        title = title_font.render(f"Replay Viewer ({scope_label})", True, (228, 238, 255))
        screen.blit(title, (screen.get_width() // 2 - title.get_width() // 2, 14))

        left_w = min(max(300, int(screen.get_width() * 0.36)), max(300, screen.get_width() - 320))
        left = pygame.Rect(18, 78, left_w, screen.get_height() - 130)
        right = pygame.Rect(left.right + 14, 78, screen.get_width() - left.width - 50, screen.get_height() - 130)
        pygame.draw.rect(screen, (22, 34, 56), left, border_radius=10)
        pygame.draw.rect(screen, (80, 120, 170), left, 2, border_radius=10)
        pygame.draw.rect(screen, (18, 28, 46), right, border_radius=10)
        pygame.draw.rect(screen, (80, 120, 170), right, 2, border_radius=10)

        if not rows:
            empty = row_font.render("No replay runs recorded yet.", True, (210, 220, 235))
            screen.blit(empty, (left.x + 12, left.y + 14))
        else:
            y = left.y + 10
            max_rows = max(5, (left.height - 20) // 34)
            for i, row in enumerate(rows[:max_rows]):
                rr = pygame.Rect(left.x + 8, y, left.width - 16, 30)
                active_row = i == selected
                pygame.draw.rect(screen, (55, 84, 125) if active_row else (28, 45, 70), rr, border_radius=6)
                pygame.draw.rect(screen, (140, 195, 255) if active_row else (75, 115, 165), rr, 1, border_radius=6)
                txt = f"#{row['replay_id']}  L{row['level_id']}  {row['completion_time']:.2f}s  {row['score']}"
                label = row_font.render(fit_text(row_font, txt, rr.width - 16), True, (240, 244, 252))
                screen.blit(label, (rr.x + 8, rr.y + 5))
                y += 34

            if len(rows) > max_rows:
                more = hud_font.render(f"Showing {max_rows}/{len(rows)} replays", True, (170, 190, 220))
                screen.blit(more, (left.x + 10, left.bottom - 26))

        pygame.draw.rect(screen, (22, 30, 48), right.inflate(-18, -18), border_radius=8)
        viewport = right.inflate(-40, -80)
        pygame.draw.rect(screen, (42, 62, 86), viewport, 1, border_radius=6)

        if active and active_frames:
            max_x = max(1, max(int(f.get("x", 0)) for f in active_frames) + 120)
            max_y = max(1, max(int(f.get("y", 0)) for f in active_frames) + 120)
            scale = min((viewport.width - 20) / max_x, (viewport.height - 20) / max_y)
            ox = viewport.x + 12
            oy = viewport.y + 12

            mini_video_frames = list((active or {}).get("mini_video_frames", []) or [])
            idx = 0
            while idx + 1 < len(active_frames) and float(active_frames[idx + 1].get("t", 0.0)) <= playback_t:
                idx += 1
            fr = active_frames[idx]

            if mini_video_frames:
                vid_idx = 0
                while vid_idx + 1 < len(mini_video_frames) and float(mini_video_frames[vid_idx + 1].get("t", 0.0)) <= playback_t:
                    vid_idx += 1
                vf = mini_video_frames[vid_idx]
                if vid_idx not in video_frame_cache:
                    try:
                        raw = base64.b64decode(vf.get("rgb", ""))
                        w = int(vf.get("w", 240))
                        h = int(vf.get("h", 135))
                        surf = pygame.image.fromstring(raw, (w, h), "RGB")
                        video_frame_cache[vid_idx] = surf
                    except Exception:
                        video_frame_cache[vid_idx] = None
                frame_surf = video_frame_cache.get(vid_idx)
                if frame_surf is not None:
                    scaled = pygame.transform.smoothscale(frame_surf, (viewport.width - 20, viewport.height - 20))
                    screen.blit(scaled, (viewport.x + 10, viewport.y + 10))
                    badge = hud_font.render("Mini Replay Video", True, (210, 236, 255))
                    screen.blit(badge, (viewport.x + 12, viewport.y + 12))
            else:
                # Draw trajectory path.
                if show_path:
                    prev = None
                    for pf in active_frames:
                        px = ox + int(float(pf.get("x", 0)) * scale)
                        py = oy + int(float(pf.get("y", 0)) * scale)
                        if prev is not None:
                            pygame.draw.line(screen, (90, 145, 205), prev, (px, py), 2)
                        prev = (px, py)

            mx = ox + int(float(fr.get("x", 0)) * scale)
            my = oy + int(float(fr.get("y", 0)) * scale)
            if show_marker and not mini_video_frames:
                pygame.draw.circle(screen, (255, 185, 90), (mx, my), 6)
                pygame.draw.circle(screen, (255, 235, 185), (mx, my), 10, 2)

            total_t = float(active_frames[-1].get("t", 0.0))
            meta = (
                f"Replay #{active['replay_id']}  L{active['level_id']}  "
                f"Time {active['completion_time']:.2f}s  Score {active['score']}"
            )
            hud = hud_font.render(fit_text(hud_font, meta, right.width - 32), True, (235, 242, 255))
            screen.blit(hud, (right.x + 16, right.y + 12))
            mode_tag = f"Outcome: {(active.get('run_outcome') or 'completed')}  {'Public' if active.get('is_public', True) else 'Private'}"
            mode_s = hud_font.render(fit_text(hud_font, mode_tag, right.width - 32), True, (175, 215, 255))
            screen.blit(mode_s, (right.x + 16, right.y + 34))

            state = "Paused" if paused else "Playing"
            progress = hud_font.render(
                f"{state}  t={playback_t:.2f}/{total_t:.2f}  speed x{speed_steps[speed_idx]:.1f}",
                True,
                (190, 220, 255),
            )
            screen.blit(progress, (right.x + 16, right.bottom - 58))

            if show_health:
                hp = fr.get("hp")
                if hp is not None:
                    hp_s = hud_font.render(f"HP snapshot: {int(hp)}", True, (170, 240, 185))
                    screen.blit(hp_s, (right.x + 16, right.bottom - 84))

            bar = pygame.Rect(right.x + 16, right.bottom - 30, right.width - 32, 10)
            pygame.draw.rect(screen, (54, 74, 98), bar, border_radius=4)
            fill = int(bar.width * (0.0 if total_t <= 0 else min(1.0, playback_t / total_t)))
            pygame.draw.rect(screen, (110, 190, 255), (bar.x, bar.y, fill, bar.height), border_radius=4)
            pygame.draw.rect(screen, (175, 205, 235), bar, 1, border_radius=4)
        else:
            tip = row_font.render("Select a replay and press Enter to load.", True, (210, 220, 235))
            screen.blit(tip, (right.x + 16, right.y + 14))

        hint = "Up/Down select  Enter load  F toggle global/my  Space pause  [ ] scrub  ,/. step  -/+ speed  O/M/H overlays  Esc back"
        draw_wrapped_text(screen, hud_font, hint, (180, 200, 230), pygame.Rect(20, screen.get_height() - 52, screen.get_width() - 40, 40), align="center", max_lines=2)
        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return True
                if event.key == pygame.K_UP and selected > 0:
                    selected -= 1
                if event.key == pygame.K_DOWN and selected < len(rows) - 1:
                    selected += 1
                if event.key == pygame.K_RETURN and rows:
                    active = get_replay_timeline(rows[selected]["replay_id"])
                    active_frames = list((active or {}).get("frames", []))
                    video_frame_cache = {}
                    safe_frames = []
                    for f in active_frames:
                        try:
                            _ = float(f.get("t", 0.0))
                            safe_frames.append(f)
                        except Exception:
                            continue
                    active_frames = safe_frames
                    active_frames.sort(key=lambda f: float(f.get("t", 0.0)))
                    playback_t = 0.0
                    paused = False
                if event.key == pygame.K_f:
                    show_mine_only = not show_mine_only
                    selected = 0
                if event.key == pygame.K_SPACE and active:
                    paused = not paused
                if event.key == pygame.K_LEFTBRACKET and active:
                    playback_t = max(0.0, playback_t - 1.0)
                if event.key == pygame.K_RIGHTBRACKET and active and active_frames:
                    playback_t = min(float(active_frames[-1].get("t", 0.0)), playback_t + 1.0)
                if event.key == pygame.K_COMMA and active and active_frames:
                    idx = 0
                    while idx + 1 < len(active_frames) and float(active_frames[idx + 1].get("t", 0.0)) < playback_t:
                        idx += 1
                    idx = max(0, idx - 1)
                    playback_t = float(active_frames[idx].get("t", 0.0))
                if event.key == pygame.K_PERIOD and active and active_frames:
                    idx = 0
                    while idx + 1 < len(active_frames) and float(active_frames[idx + 1].get("t", 0.0)) <= playback_t:
                        idx += 1
                    idx = min(len(active_frames) - 1, idx + 1)
                    playback_t = float(active_frames[idx].get("t", 0.0))
                if event.key in (pygame.K_MINUS, pygame.K_KP_MINUS) and speed_idx > 0:
                    speed_idx -= 1
                if event.key in (pygame.K_EQUALS, pygame.K_KP_PLUS) and speed_idx < len(speed_steps) - 1:
                    speed_idx += 1
                if event.key == pygame.K_o:
                    show_path = not show_path
                if event.key == pygame.K_m:
                    show_marker = not show_marker
                if event.key == pygame.K_h:
                    show_health = not show_health
