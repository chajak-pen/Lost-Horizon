import pygame
from Classes import Text, Button
from ui_helpers import fit_text, draw_wrapped_text

pygame.init()

info = pygame.display.Info()
screen_width, screen_height = info.current_w, info.current_h

def win_screen(player_score=None, top_times=None, top_scores=None, is_new_score_best=False, is_new_time_best=False,
               style_rank=None, combo_max=None, medal_awarded=None, death_count=None,
               coins_collected=None, total_coins=None, run_mode_label=None, style_breakdown=None):
    #Show the win screen. Optionally display player_score and a list of top_times
    win_screen = pygame.display.set_mode((screen_width, screen_height)) #creates a 1000x600 pixel window
    pygame.display.set_caption("Lost Horizon - You Win!") #sets the title of the game to "Lost Horizon - You Win!"

    background = pygame.image.load("background.jpg").convert_alpha() #loads the background image
    background = pygame.transform.scale(background, (screen_width, screen_height))
    # scale UI
    sx = screen_width / 1000.0
    sy = screen_height / 600.0
    back_size = max(24, int(screen_width * 0.04))
    back_button = Button(10, 10, "back button.jpg")
    back_button.image = pygame.transform.scale(back_button.image, (back_size, back_size))
    font = pygame.font.SysFont("Arial", max(12, int(30 * sy)))
    title_font = pygame.font.SysFont("Arial", max(20, int(48 * sy)), bold=True)
    small_font = pygame.font.SysFont("Arial", max(11, int(22 * sy)))
    running = True
    while running:# starts a while loop that will run the program
        win_screen.blit(background, (0,0)) #draws the background image at the top left corner
        back_button.draw()
        title_x = screen_width // 2 - title_font.size("You Win!")[0] // 2
        title_y = int(screen_height * 0.03)
        title_text = Text("You Win!", title_x, title_y, title_font)
        title_text.draw_text()

        top_pad = title_y + title_font.get_height() + int(18 * sy)
        summary_w = min(460, screen_width - 60)
        summary_h = max(180, int(screen_height * 0.24))
        summary = pygame.Rect((screen_width - summary_w) // 2, top_pad, summary_w, summary_h)
        pygame.draw.rect(win_screen, (14, 24, 42, 190), summary, border_radius=12)
        pygame.draw.rect(win_screen, (110, 170, 230), summary, 2, border_radius=12)

        summary_lines = []
        if player_score is not None:
            summary_lines.append(f"Score: {player_score}")
        if style_rank is not None:
            summary_lines.append(f"Style Rank: {style_rank}")
        if combo_max is not None:
            summary_lines.append(f"Max Combo: x{combo_max}")
        if medal_awarded is not None:
            summary_lines.append(f"Medal: {str(medal_awarded).title()}")
        if death_count is not None:
            summary_lines.append(f"Deaths: {int(death_count)}")
        if coins_collected is not None and total_coins is not None:
            summary_lines.append(f"Coins: {int(coins_collected)}/{int(total_coins)}")
        if run_mode_label:
            summary_lines.append(f"Run Mode: {str(run_mode_label).replace('_', ' ').title()}")

        left_col_x = summary.x + 18
        right_col_x = summary.centerx + 12
        summary_y = summary.y + 18
        split_at = (len(summary_lines) + 1) // 2
        for idx, line in enumerate(summary_lines[:split_at]):
            surf = font.render(fit_text(font, line, summary.w // 2 - 28), True, (235, 240, 248))
            win_screen.blit(surf, (left_col_x, summary_y + idx * (surf.get_height() + 8)))
        for idx, line in enumerate(summary_lines[split_at:]):
            surf = font.render(fit_text(font, line, summary.w // 2 - 28), True, (235, 240, 248))
            win_screen.blit(surf, (right_col_x, summary_y + idx * (surf.get_height() + 8)))

        breakdown_bottom = summary.bottom
        if style_breakdown:
            breakdown_h = max(74, int(90 * sy))
            breakdown = pygame.Rect(summary.x, summary.bottom + int(8 * sy), summary.w, breakdown_h)
            pygame.draw.rect(win_screen, (14, 24, 42, 190), breakdown, border_radius=12)
            pygame.draw.rect(win_screen, (145, 122, 230), breakdown, 2, border_radius=12)
            head = small_font.render("Style Breakdown", True, (220, 195, 255))
            win_screen.blit(head, (breakdown.x + 12, breakdown.y + 8))
            b_lines = [
                f"Kills +{int(style_breakdown.get('kills', 0))}",
                f"Movement +{int(style_breakdown.get('movement', 0))}",
                f"Finishers +{int(style_breakdown.get('finishers', 0))}",
                f"Penalties -{int(style_breakdown.get('penalties', 0))}",
            ]
            left_x = breakdown.x + 14
            right_x = breakdown.centerx + 8
            line_y = breakdown.y + 34
            for idx, text in enumerate(b_lines[:2]):
                surf = small_font.render(fit_text(small_font, text, breakdown.w // 2 - 24), True, (230, 234, 245))
                win_screen.blit(surf, (left_x, line_y + idx * (surf.get_height() + 6)))
            for idx, text in enumerate(b_lines[2:]):
                surf = small_font.render(fit_text(small_font, text, breakdown.w // 2 - 24), True, (230, 234, 245))
                win_screen.blit(surf, (right_x, line_y + idx * (surf.get_height() + 6)))
            breakdown_bottom = breakdown.bottom

        # New personal best banner
        if is_new_score_best or is_new_time_best:
            banner_font = pygame.font.SysFont("Arial", max(18, int(34 * sy)), bold=True)
            if is_new_score_best and is_new_time_best:
                banner_str = "*** New Personal Best Score & Time! ***"
            elif is_new_score_best:
                banner_str = "*** New Personal Best Score! ***"
            else:
                banner_str = "*** New Best Time! ***"
            banner_surf = banner_font.render(banner_str, True, (255, 215, 0))
            banner_x = (screen_width - banner_surf.get_width()) // 2
            banner_y = breakdown_bottom + int(8 * sy)
            win_screen.blit(banner_surf, (banner_x, banner_y))

        boards_top = breakdown_bottom + int(56 * sy)
        board_gap = int(20 * sx)
        board_w = (screen_width - 60 - board_gap) // 2
        board_h = screen_height - boards_top - 34
        left_board = pygame.Rect(20, boards_top, board_w, board_h)
        right_board = pygame.Rect(left_board.right + board_gap, boards_top, board_w, board_h)
        for board in (left_board, right_board):
            pygame.draw.rect(win_screen, (10, 18, 34, 180), board, border_radius=10)
            pygame.draw.rect(win_screen, (95, 145, 210), board, 2, border_radius=10)

        #draw top scores if provided
        if top_scores:
            left_x = left_board.x + 12
            y_start = left_board.y + 10
            header = Text('Top Scores:', left_x, y_start, small_font)
            header.draw_text()
            line_h = max(22, small_font.get_linesize())
            max_rows = max(3, (left_board.height - 42) // line_h)
            for i, row in enumerate(top_scores[:max_rows]):
                name = row[0]
                score = row[1]
                mode = row[2] if len(row) > 2 else None
                mode_suffix = f" [{str(mode).upper()}]" if mode else ""
                score_line = fit_text(small_font, f"{i+1}. {name} - {score}{mode_suffix}", left_board.width - 24)
                score_text = small_font.render(score_line, True, (255, 255, 255))
                win_screen.blit(score_text, (left_x, y_start + (i + 1) * line_h))

        # draw top times if provided
        if top_times:
            right_x = right_board.x + 12
            y_start = right_board.y + 10
            header = Text('Top Times:', right_x, y_start, small_font)
            header.draw_text()
            line_h = max(22, small_font.get_linesize())
            max_rows = max(3, (right_board.height - 42) // line_h)
            for i, row in enumerate(top_times[:max_rows]):
                name = row[0]
                time_taken = row[1]
                run_coins = row[2] if len(row) > 2 else 0
                mode = row[3] if len(row) > 3 else None
                mode_suffix = f" [{str(mode).upper()}]" if mode else ""
                time_text = small_font.render(
                    fit_text(small_font, f"{i+1}. {name} - {time_taken:.2f}s - Coins: {run_coins}{mode_suffix}", right_board.width - 24),
                    True,
                    (255, 255, 255),
                )
                win_screen.blit(time_text, (right_x, y_start + (i + 1) * line_h))
        for event in pygame.event.get(): 
            if event.type == pygame.QUIT:
                running = False
                return False
            
            if back_button.handle_event(event):
                return True  # return True to go back to start menu

        pygame.display.update()

