import os, json
import pygame

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)


def _resolve_local_path(path):
    if os.path.isabs(path):
        return path
    for root in (BASE_DIR, PARENT_DIR):
        candidate = os.path.join(root, path)
        if os.path.exists(candidate):
            return candidate
    return os.path.join(BASE_DIR, path)


SETTINGS_FILE = _resolve_local_path("settings.json")
MUSIC_PATH = _resolve_local_path("background_music.mp3")

KEY_NAME_ALIASES = {
    "lshift": "left shift",
    "rshift": "right shift",
    "lctrl": "left ctrl",
    "rctrl": "right ctrl",
    "lalt": "left alt",
    "ralt": "right alt",
    "return": "enter",
    "esc": "escape",
    "spacebar": "space",
}

DEFAULT_KEYBINDS = {
    "move_left": ["a", "left"],
    "move_right": ["d", "right"],
    "jump": ["space"],
    "pause": ["p"],
    "ghost_toggle": ["g"],
    "debug_overlay": ["f3"],
    "dash": ["lshift", "rshift"],
    "slide": ["s"],
    "select_power_1": ["1"],
    "select_power_2": ["2"],
    "select_power_3": ["3"],
    "activate_power": ["e"],
}

DEFAULT_ACCESSIBILITY = {
    "high_contrast_hud": False,
    "reduced_screen_shake": False,
    "extended_jump_buffer": False,
    "training_hints": True,
    "hud_simplified": False,
    "colorblind_safe_palette": False,
    "performance_overlay": False,
}


def _merge_defaults(raw):
    merged = dict(raw or {})
    merged.setdefault("music_on", True)
    merged.setdefault("sfx_on", True)
    merged.setdefault("music_volume", 0.5)
    merged.setdefault("sfx_volume", 0.6)
    merged.setdefault("easy_mode", False)
    merged.setdefault("debug_logging", False)
    merged.setdefault("onboarding_seen", False)

    raw_binds = merged.get("keybinds") if isinstance(merged.get("keybinds"), dict) else {}
    keybinds = {}
    for action, fallback in DEFAULT_KEYBINDS.items():
        candidate = raw_binds.get(action, fallback)
        if isinstance(candidate, list) and candidate:
            keybinds[action] = [str(v).lower() for v in candidate if str(v).strip()]
        else:
            keybinds[action] = list(fallback)
    merged["keybinds"] = keybinds

    raw_access = merged.get("accessibility") if isinstance(merged.get("accessibility"), dict) else {}
    access = {}
    for k, fallback in DEFAULT_ACCESSIBILITY.items():
        access[k] = bool(raw_access.get(k, fallback))
    merged["accessibility"] = access
    return merged

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                loaded = json.load(f)
                merged = _merge_defaults(loaded)
                if merged != loaded:
                    save_settings(merged)
                return merged
        except Exception:
            # Recover from a corrupted settings file by writing defaults.
            s = _merge_defaults({})
            save_settings(s)
            return s
    s = _merge_defaults({})
    save_settings(s)
    return s

def save_settings(s):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(_merge_defaults(s), f)


def get_keybind_keycodes(settings_dict=None):
    settings = _merge_defaults(settings_dict or load_settings())
    out = {}
    for action, names in settings["keybinds"].items():
        codes = []
        for name in names:
            key_name = KEY_NAME_ALIASES.get(str(name).lower(), str(name).lower())
            try:
                code = pygame.key.key_code(key_name)
                if code not in codes:
                    codes.append(code)
            except ValueError:
                continue
        if not codes:
            for fallback_name in DEFAULT_KEYBINDS.get(action, []):
                key_name = KEY_NAME_ALIASES.get(str(fallback_name).lower(), str(fallback_name).lower())
                try:
                    code = pygame.key.key_code(key_name)
                    if code not in codes:
                        codes.append(code)
                except ValueError:
                    continue
        out[action] = tuple(codes)
    return out


def get_accessibility_settings(settings_dict=None):
    settings = _merge_defaults(settings_dict or load_settings())
    return dict(settings["accessibility"])