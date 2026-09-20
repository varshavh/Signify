"""Render color emoji as CTkImage (Windows CTkButton text emoji is B/W)."""

from __future__ import annotations

import sys
from pathlib import Path

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont

_CACHE: dict[tuple[str, int, int], ctk.CTkImage] = {}


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


def emoji_ctk(char: str, size: int = 18, tile: int = 28) -> ctk.CTkImage:
    """Square color emoji tile, glyph centered for button overlays."""
    key = (char, size, tile)
    if key in _CACHE:
        return _CACHE[key]

    img = Image.new("RGBA", (tile, tile), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = _emoji_font(size)
    if font is not None:
        try:
            bbox = draw.textbbox((0, 0), char, font=font, embedded_color=True)
        except TypeError:
            bbox = draw.textbbox((0, 0), char, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        x = (tile - tw) // 2 - bbox[0]
        y = (tile - th) // 2 - bbox[1]
        try:
            draw.text((x, y), char, font=font, embedded_color=True)
        except TypeError:
            draw.text((x, y), char, font=font, fill=(220, 220, 220))
    else:
        draw.text((tile // 2 - 4, tile // 2 - 6), "?", fill=(180, 180, 180))

    out = ctk.CTkImage(light_image=img, dark_image=img, size=(tile, tile))
    _CACHE[key] = out
    return out
