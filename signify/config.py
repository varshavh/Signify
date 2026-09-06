"""App configuration and visual theme."""

APP_NAME = "Signify"
APP_TAGLINE = "Real-time Sign Language Recognition"


# ---- Theme -----------------------------------------------------------------
COLORS = {
    "bg":        "#0f1117",
    "surface":   "#171a23",
    "surface_2": "#1f2330",
    "primary":   "#6c5ce7",
    "primary_h": "#5a4bd1",
    "accent":    "#00d2a8",
    "info":      "#4ea8ff",
    "ok":        "#3dd68c",
    "text":      "#e8eaf0",
    "muted":     "#8b90a0",
    "danger":    "#ff5c7c",
}

# Signs used in Practice Studio (reliable subset of the 42-class model).
PRACTICE_SIGNS = [
    "Hello", "Bye", "Yes", "No", "Please", "Thankyou", "Ok", "Name",
    "Me", "ILoveYou", "A", "B", "C", "I", "Y", "L",
]

# Recognizer / builder tuning
NUM_HANDS = 2
STABILITY_FRAMES = 10
MIN_CONFIDENCE = 0.45
