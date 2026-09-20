"""Render color emoji as CTkImage (Windows CTkButton text emoji is B/W)."""

from __future__ import annotations

import sys
from pathlib import Path

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont

_CACHE: dict[tuple[str, int], ctk.CTkImage] = {}


def _emoji_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont | None:
    candidates: list[Path] = []
    if sys.platform == "win32":
        candidates = [
            Path(r"C:\Windows\Fonts\seguiemj.ttf"),
            Path(r"C:\Windows\Fonts\SegoeUIEmoji.ttf"),
        ]
    elif sys.platform == "darwin":
        candidates = [
            Path("/System/Library/Fonts/Apple Color Emoji.ttc"),
        ]
    else:
        candidates = [
            Path("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"),
            Path("/usr/share/fonts/google-noto-emoji/NotoColorEmoji.ttf"),
        ]
    for path in candidates:
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                continue
    return None


def emoji_ctk(char: str, size: int = 22) -> ctk.CTkImage:
    """Color emoji tile for buttons. Falls back to a plain label character."""
    key = (char, size)
    if key in _CACHE:
        return _CACHE[key]

    pad = 6
    canvas = size + pad * 2
    img = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = _emoji_font(size)
    if font is not None:
        try:
            draw.text((pad, pad - 2), char, font=font, embedded_color=True)
        except TypeError:
            draw.text((pad, pad - 2), char, font=font, fill=(220, 220, 220))
    else:
        draw.text((pad, pad), char, fill=(180, 180, 180))

    out = ctk.CTkImage(light_image=img, dark_image=img, size=(canvas, canvas))
    _CACHE[key] = out
    return out
