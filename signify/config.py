"""App configuration and fixed-credential auth (no database)."""

import hashlib

APP_NAME = "Signify"
APP_TAGLINE = "Real-time Sign Language Recognition"

# ---- Fixed credentials (no database) --------------------------------------
# Change these if you like. Password is compared via a salted hash so the
# plaintext isn't sitting in memory as a bare string comparison target.
_ADMIN_USER = "admin"
_ADMIN_PW_HASH = hashlib.sha256(b"signify:admin123").hexdigest()


def check_credentials(username: str, password: str) -> bool:
    if username != _ADMIN_USER:
        return False
    return hashlib.sha256(f"signify:{password}".encode()).hexdigest() == _ADMIN_PW_HASH


# ---- Theme -----------------------------------------------------------------
COLORS = {
    "bg":        "#0f1117",
    "surface":   "#171a23",
    "surface_2": "#1f2330",
    "primary":   "#6c5ce7",
    "primary_h": "#5a4bd1",
    "accent":    "#00d2a8",
    "text":      "#e8eaf0",
    "muted":     "#8b90a0",
    "danger":    "#ff5c7c",
}

# Recognizer / builder tuning
NUM_HANDS = 2
STABILITY_FRAMES = 10
MIN_CONFIDENCE = 0.45
