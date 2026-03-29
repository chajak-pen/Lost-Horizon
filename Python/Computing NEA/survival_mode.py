import random
import pygame

from database import save_survival_score


pygame.init()


def survival_mode(player_name):
    """Arcade survival mode with wave scaling. Returns True to go back, False to quit."""
    screen = pygame.display.get_surface()
    if screen is None:
        info = pygame.display.Info()
        screen = pygame.display.set_mode((info.current_w, info.current_h))

    sw, sh = screen.get_width(), screen.get_height()
    floor_y = int(sh * 0.78)

    title_font = pygame.font.SysFont("Arial", 42, bold=True)
    hud_font = pygame.font.SysFont("Arial", 26)
    hint_font = pygame.font.SysFont("Arial", 20)

    player = pygame.Rect(sw // 2 - 18, floor_y - 52, 36, 52)
    player_vx = 0.0
    player_vy = 0.0
    player_speed = 280.0
    gravity = 900.0
    jump_power = 430.0
    on_ground = True

    hp = 100
    invuln = 0.0

    enemies = []
    projectiles = []
    wave = 0
    wave_timer = 1.0
    score = 0
    kills = 0

    running = True
    clock = pygame.time.Clock()

    def spawn_wave(idx):
        spawned = []
        melee_count = 2 + idx
        ranged_count = max(0, (idx - 1) // 2)

        for _ in range(melee_count):
            side_left = random.random() < 0.5
            x = -30 if side_left else sw + 30
            spawned.append({
                "kind": "melee",
                "rect": pygame.Rect(x, floor_y - 40, 32, 40),
                "speed": min(370, 105 + idx * 14),
                "hp": 1 + idx // 3,
                "shoot_cd": 0.0,
            })

        for _ in range(ranged_count):
            x = random.randint(80, sw - 80)
            spawned.append({
                "kind": "ranged",
                "rect": pygame.Rect(x, floor_y - 42, 32, 42),
                "speed": min(300, 85 + idx * 8),
                "hp": 2 + idx // 4,
                "shoot_cd": max(0.4, 1.8 - idx * 0.08),
            })
        return spawned

    while running:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return True
                if event.key == pygame.K_SPACE and on_ground:
                    player_vy = -jump_power
                    on_ground = False

        keys = pygame.key.get_pressed()
        player_vx = 0.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            player_vx = -player_speed
        elif keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            player_vx = player_speed

        player.x += int(player_vx * dt)
        player.x = max(0, min(sw - player.width, player.x))

        player_vy += gravity * dt
        player.y += int(player_vy * dt)
        if player.bottom >= floor_y:
            player.bottom = floor_y
            player_vy = 0.0
            on_ground = True

        # Waves
        if not enemies:
            wave_timer -= dt
            if wave_timer <= 0:
                wave += 1
                enemies.extend(spawn_wave(wave))
                wave_timer = 1.25
                score += 50 * wave

        # Enemy update
        for e in enemies[:]:
            er = e["rect"]
            if e["kind"] == "melee":
                if er.centerx < player.centerx:
                    er.x += int(e["speed"] * dt)
                else:
                    er.x -= int(e["speed"] * dt)
            else:
                # Ranged: small strafe and periodic projectile
                if abs(er.centerx - player.centerx) > 180:
                    if er.centerx < player.centerx:
                        er.x += int(e["speed"] * dt)
                    else:
                        er.x -= int(e["speed"] * dt)
                e["shoot_cd"] -= dt
                if e["shoot_cd"] <= 0:
                    vx = 260 if player.centerx > er.centerx else -260
                    projectiles.append({"rect": pygame.Rect(er.centerx, er.centery - 3, 12, 6), "vx": vx})
                    e["shoot_cd"] = max(0.35, 1.6 - wave * 0.07)

            # Stomp kills enemy
            if player.colliderect(er) and player_vy > 0 and player.bottom - er.top < 22:
                e["hp"] -= 1
                player_vy = -300
                on_ground = False
                if e["hp"] <= 0:
                    enemies.remove(e)
                    kills += 1
                    score += 30 + wave * 8
                    continue

            # Side contact damage
            if player.colliderect(er) and not (player_vy > 0 and player.bottom - er.top < 22):
                if invuln <= 0:
                    hp -= 12
                    invuln = 0.6

        # Projectiles update
        for p in projectiles[:]:
            p["rect"].x += int(p["vx"] * dt)
            if p["rect"].right < 0 or p["rect"].left > sw:
                projectiles.remove(p)
                continue
            if player.colliderect(p["rect"]):
                if invuln <= 0:
                    hp -= 10
                    invuln = 0.5
                projectiles.remove(p)

        if invuln > 0:
            invuln = max(0.0, invuln - dt)

        if hp <= 0:
            save_survival_score(player_name, score, wave)
            over_t = pygame.time.get_ticks() + 1600
            while pygame.time.get_ticks() < over_t:
                screen.fill((18, 18, 22))
                over = title_font.render("Survival Defeated", True, (255, 130, 130))
                sum_text = hud_font.render(f"Score: {score}  Waves: {wave}", True, (230, 230, 230))
                screen.blit(over, (sw // 2 - over.get_width() // 2, sh // 2 - 60))
                screen.blit(sum_text, (sw // 2 - sum_text.get_width() // 2, sh // 2))
                pygame.display.update()
            return True

        # Draw
        screen.fill((20, 26, 34))
        pygame.draw.rect(screen, (58, 68, 82), (0, floor_y, sw, sh - floor_y))

        title = title_font.render("Endless Survival", True, (255, 220, 130))
        screen.blit(title, (20, 12))

        hp_col = (220, 90, 90) if hp < 35 else (180, 230, 180)
        hud = hud_font.render(f"HP: {hp}   Wave: {wave}   Kills: {kills}   Score: {score}", True, hp_col)
        screen.blit(hud, (20, 62))

        hint = hint_font.render("A/D move, SPACE jump stomp, ESC return", True, (205, 215, 228))
        screen.blit(hint, (20, 98))

        # Player blink during invuln
        if invuln <= 0 or int(pygame.time.get_ticks() / 70) % 2 == 0:
            pygame.draw.rect(screen, (90, 180, 255), player, border_radius=5)

        for e in enemies:
            col = (220, 120, 90) if e["kind"] == "melee" else (190, 120, 235)
            pygame.draw.rect(screen, col, e["rect"], border_radius=5)

        for p in projectiles:
            pygame.draw.rect(screen, (255, 210, 120), p["rect"], border_radius=3)

        pygame.display.update()

    return True
