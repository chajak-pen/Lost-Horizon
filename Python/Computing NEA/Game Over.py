import pygame
from Classes import Text, AnimatedText, Button, resolve_asset_path

pygame.init()

info = pygame.display.Info()
screen_width, screen_height = info.current_w, info.current_h

def game_over_screen(player_score=None, level=None):
    """Show the game over screen. Optionally display player_score and level info"""
    game_over_screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Lost Horizon - Game Over")

    background = pygame.image.load(resolve_asset_path("background.jpg")).convert_alpha()
    background = pygame.transform.scale(background, (screen_width, screen_height))
    
    # scale UI
    sx = screen_width / 1000.0
    sy = screen_height / 600.0
    back_size = max(24, int(screen_width * 0.04))
    back_button = Button(10, 10, "back button.jpg")
    back_button.image = pygame.transform.scale(back_button.image, (back_size, back_size))
    
    # Create retry and quit buttons
    button_w = max(48, int(screen_width * 0.20))
    button_h = max(24, int(screen_height * 0.1667))
    
    retry_image = pygame.image.load(resolve_asset_path("play button.png")).convert_alpha()
    retry_image = pygame.transform.scale(retry_image, (button_w, button_h))
    
    quit_image = pygame.image.load(resolve_asset_path("exit game.png")).convert_alpha()
    quit_image = pygame.transform.scale(quit_image, (button_w, button_h))
    
    # Center buttons horizontally
    center_x = screen_width // 2 - button_w // 2
    retry_button = Button(center_x, int(screen_height * 0.4167), retry_image)
    quit_button = Button(center_x, int(screen_height * 0.5833), quit_image)
    
    # Fonts
    font = pygame.font.SysFont("Arial", max(12, int(40 * sy)))
    small_font = pygame.font.SysFont("Arial", max(12, int(26 * sy)))
    
    # Create animated title
    title_text = AnimatedText("GAME OVER", 0, int(screen_height * 0.1), font, centered=True, fade_in_duration=1.5)
    
    clock = pygame.time.Clock()
    running = True
    
    while running:
        dt = clock.tick(60) / 1000.0  # Delta time in seconds
        
        game_over_screen.blit(background, (0, 0))
        back_button.draw()
        retry_button.draw()
        quit_button.draw()
        
        # Update and draw animated title
        title_text.update(dt)
        title_text.draw_text()
        
        # Draw player's score if provided
        if player_score is not None:
            score_text = Text(f'Final Score: {player_score}', 0, int(screen_height * 0.25), small_font, centered=True)
            score_text.draw_text()
        
        # Draw level info if provided
        if level is not None:
            level_text = Text(f'Level Reached: {level}', 0, int(screen_height * 0.32), small_font, centered=True)
            level_text.draw_text()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                return False
            
            if back_button.handle_event(event):
                return True  # Return to start menu
            
            if retry_button.handle_event(event):
                return "retry"  # Retry the level
            
            if quit_button.handle_event(event):
                return False  # Quit the game
        
        pygame.display.update()
    
    return True
