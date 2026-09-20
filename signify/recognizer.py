"""
Sign recognition engine — wraps the pretrained MediaPipe gesture model.

Keeps all MediaPipe/OpenCV concerns out of the UI. The UI just calls
`SignRecognizer.process(frame_bgr)` and gets back an annotated frame plus a
list of (label, score) predictions.
"""

import time
from pathlib import Path

import cv2
import mediapipe as mp

from .custom_signs import encode_landmarks
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "sign_language_recognizer.task"

# MediaPipe hand-connection pairs for drawing the skeleton.
_HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),          # thumb
    (0, 5), (5, 6), (6, 7), (7, 8),          # index
    (5, 9), (9, 10), (10, 11), (11, 12),     # middle
    (9, 13), (13, 14), (14, 15), (15, 16),   # ring
    (13, 17), (17, 18), (18, 19), (19, 20),  # pinky
    (0, 17),                                  # palm base
]


class SignRecognizer:
    """Thin wrapper around the MediaPipe GestureRecognizer (VIDEO mode)."""

    def __init__(self, model_path: Path = MODEL_PATH, num_hands: int = 2):
        if not Path(model_path).exists():
            raise FileNotFoundError(f"Model not found: {model_path}")
        options = vision.GestureRecognizerOptions(
            base_options=python.BaseOptions(model_asset_path=str(model_path)),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=num_hands,
        )
        self._recognizer = vision.GestureRecognizer.create_from_options(options)
        self._start = time.time()

    def process(self, frame_bgr):
        """Run recognition on a BGR frame.

        Returns (annotated_bgr, predictions) where predictions is a list of
        (label, score) sorted by score desc — one entry per detected hand.
        """
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        ts_ms = int((time.time() - self._start) * 1000)
        result = self._recognizer.recognize_for_video(mp_image, ts_ms)

        annotated = frame_bgr.copy()
        h, w = annotated.shape[:2]

        # Draw hand skeletons
        if result.hand_landmarks:
            for landmarks in result.hand_landmarks:
                pts = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]
                for a, b in _HAND_CONNECTIONS:
                    cv2.line(annotated, pts[a], pts[b], (0, 200, 255), 2)
                for p in pts:
                    cv2.circle(annotated, p, 4, (0, 90, 255), -1)

        predictions = []
        if result.gestures:
            for g in result.gestures:
                top = g[0]
                predictions.append((top.category_name, float(top.score)))
            predictions.sort(key=lambda x: x[1], reverse=True)

        hand_vec = None
        if result.hand_landmarks:
            hand_vec = encode_landmarks(result.hand_landmarks[0])

        return annotated, predictions, hand_vec

    def close(self):
        try:
            self._recognizer.close()
        except Exception:
            pass
