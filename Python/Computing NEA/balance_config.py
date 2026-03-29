BALANCE_PRESETS = {
    "easy": {
        "enemy_move_mult": 0.0,
        "enemy_fire_cooldown_mult": 2.4,
        "enemy_projectile_speed_mult": 0.55,
        "boss_move_mult": 0.0,
        "boss_attack_cooldown_mult": 1.45,
        "fall_penalty_life_loss": False,
    },
    "normal": {
        "enemy_move_mult": 1.0,
        "enemy_fire_cooldown_mult": 1.0,
        "enemy_projectile_speed_mult": 1.0,
        "boss_move_mult": 1.0,
        "boss_attack_cooldown_mult": 1.0,
        "fall_penalty_life_loss": True,
    },
    "hard": {
        "enemy_move_mult": 1.18,
        "enemy_fire_cooldown_mult": 0.86,
        "enemy_projectile_speed_mult": 1.14,
        "boss_move_mult": 1.10,
        "boss_attack_cooldown_mult": 0.90,
        "fall_penalty_life_loss": True,
    },
    "ng_plus": {
        "enemy_move_mult": 1.28,
        "enemy_fire_cooldown_mult": 0.74,
        "enemy_projectile_speed_mult": 1.22,
        "boss_move_mult": 1.16,
        "boss_attack_cooldown_mult": 0.82,
        "fall_penalty_life_loss": True,
    },
}


def get_balance_preset(mode_name):
    return dict(BALANCE_PRESETS.get(mode_name, BALANCE_PRESETS["normal"]))
