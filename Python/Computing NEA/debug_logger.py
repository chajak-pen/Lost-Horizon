import os
from datetime import datetime

from game_settings import load_settings

LOG_FILE = "debug_events.log"


def debug_log(event_name, message):
    try:
        settings = load_settings()
        if not settings.get("debug_logging", False):
            return
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {event_name}: {message}\n"
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        # Logging must never break gameplay.
        return
