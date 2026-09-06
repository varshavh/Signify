"""Tiny bar-chart helper drawn on a Tk canvas — no matplotlib."""

from .config import COLORS


def format_duration(seconds: int) -> str:
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds / 60
    if minutes < 60:
        rounded = round(minutes)
        if abs(minutes - rounded) < 0.05:
            return f"{int(rounded)} min"
        return f"{minutes:.1f} min"
    hours = minutes / 60
    return f"{hours:.1f} h"


def draw_bars(canvas, series, color=None, bar_fill=None):
    """series: list of (label, numeric_value). Values are typically seconds."""
    color = color or COLORS["info"]
    canvas.delete("all")
    canvas.update_idletasks()
    w = max(canvas.winfo_width(), 220)
    h = max(canvas.winfo_height(), 120)
    pad_l, pad_r, pad_t, pad_b = 8, 8, 10, 22
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b
    if not series:
        canvas.create_text(w / 2, h / 2, text="No data yet", fill=COLORS["muted"],
                           font=("Arial", 12))
        return

    values = [max(0, float(v)) for _, v in series]
    peak = max(values) or 1.0
    n = len(series)
    gap = 6
    bar_w = max(8, (inner_w - gap * (n + 1)) / n)

    for i, ((label, _), val) in enumerate(zip(series, values)):
        x0 = pad_l + gap + i * (bar_w + gap)
        x1 = x0 + bar_w
        bh = (val / peak) * (inner_h - 4)
        y1 = pad_t + inner_h
        y0 = y1 - bh
        canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="",
                                width=0)
        canvas.create_text((x0 + x1) / 2, h - 10, text=str(label)[:6],
                           fill=COLORS["muted"], font=("Arial", 9))
    if bar_fill:
        pass
