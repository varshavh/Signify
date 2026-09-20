"""Personal gestures: save hand shape from a photo, match live by landmarks.

No extra model file — we store a normalized 21-point hand vector in SQLite and
compare new frames with simple distance. Good for a few custom signs you teach.
"""

from __future__ import annotations

import json

import numpy as np

# Lower = stricter match. ~0.28 works for most taught poses.
MATCH_THRESHOLD = 0.32


def encode_landmarks(landmarks) -> list[float] | None:
    """MediaPipe hand landmarks -> flat normalized vector (63 floats)."""
    pts = np.array([[lm.x, lm.y, lm.z] for lm in landmarks], dtype=np.float32)
    wrist = pts[0]
    pts = pts - wrist
    scale = float(np.max(np.linalg.norm(pts[:, :2], axis=1)))
    if scale < 1e-5:
        return None
    return (pts / scale).reshape(-1).tolist()


def decode_landmarks(blob: str) -> list[float]:
    return json.loads(blob)


def distance(a: list[float], b: list[float]) -> float:
    va = np.asarray(a, dtype=np.float32)
    vb = np.asarray(b, dtype=np.float32)
    if va.shape != vb.shape:
        return float("inf")
    return float(np.linalg.norm(va - vb))


def best_match(query: list[float] | None, templates: list[tuple[str, list[float]]],
               threshold: float = MATCH_THRESHOLD) -> tuple[str | None, float]:
    """Return (label, confidence 0–1) for the closest template under threshold."""
    if not query or not templates:
        return None, 0.0
    best_label = None
    best_dist = float("inf")
    for label, vec in templates:
        d = distance(query, vec)
        if d < best_dist:
            best_dist = d
            best_label = label
    if best_label is None or best_dist > threshold:
        return None, 0.0
    conf = max(0.0, min(1.0, 1.0 - (best_dist / threshold)))
    return best_label, conf
