from datetime import datetime


def get_active_event(now=None):
    """Return current seasonal event config or None."""
    now = now or datetime.now()
    month = now.month

    if month == 10:
        return {
            "key": "harvest_havoc",
            "name": "Harvest Havoc",
            "enemy_speed_mult": 1.22,
            "gravity_mult": 1.0,
            "coin_mult": 1.3,
            "player_tint": (120, 60, 10),
            "hud_color": (255, 170, 90),
        }
    if month == 12:
        return {
            "key": "frost_festival",
            "name": "Frost Festival",
            "enemy_speed_mult": 0.94,
            "gravity_mult": 0.9,
            "coin_mult": 1.2,
            "player_tint": (70, 120, 190),
            "hud_color": (170, 220, 255),
        }
    if month in (3, 4):
        return {
            "key": "spring_bloom",
            "name": "Spring Bloom",
            "enemy_speed_mult": 1.08,
            "gravity_mult": 0.96,
            "coin_mult": 1.15,
            "player_tint": (80, 150, 90),
            "hud_color": (170, 255, 180),
        }
    return None
