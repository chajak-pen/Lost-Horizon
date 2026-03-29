import base64
import json
import random
from datetime import datetime


def make_challenge_code(level_id, seed=None, modifiers=None):
    seed = int(seed if seed is not None else random.randint(100000, 99999999))
    payload = {
        "lvl": int(level_id),
        "seed": seed,
        "mods": modifiers or {},
    }
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def parse_challenge_code(code):
    if not code:
        return None
    try:
        padded = code + "=" * ((4 - len(code) % 4) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
        payload = json.loads(raw.decode("utf-8"))
        return {
            "level_id": int(payload.get("lvl")),
            "seed": int(payload.get("seed")),
            "modifiers": payload.get("mods") or {},
        }
    except Exception:
        return None


def make_daily_challenge(available_levels, now=None):
    """Build deterministic daily challenge details for a list of playable levels."""
    levels = [int(lvl) for lvl in (available_levels or [])]
    if not levels:
        return None

    levels = sorted(set(levels))
    now = now or datetime.now()
    date_key = now.strftime("%Y-%m-%d")
    base_seed = int(now.strftime("%Y%m%d"))

    level_rng = random.Random(base_seed * 131 + 17)
    level_id = levels[level_rng.randint(0, len(levels) - 1)]

    mod_rng = random.Random(base_seed * 313 + int(level_id) * 7)
    modifiers = {
        "enemy_mult": round(mod_rng.uniform(1.05, 1.40), 2),
        "gravity_mult": round(mod_rng.uniform(0.90, 1.14), 2),
        "coin_mult": round(mod_rng.uniform(0.92, 1.35), 2),
    }
    challenge_seed = base_seed * 100 + int(level_id)
    code = make_challenge_code(level_id, seed=challenge_seed, modifiers=modifiers)
    return {
        "date_key": date_key,
        "level_id": int(level_id),
        "seed": int(challenge_seed),
        "modifiers": modifiers,
        "challenge_code": code,
    }
