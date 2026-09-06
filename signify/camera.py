"""Open the default webcam in a way that works on macOS and Windows."""

from __future__ import annotations

import sys

import cv2


def open_webcam(index: int = 0):
    """Return an opened VideoCapture, or one that failed `.isOpened()`."""
    if sys.platform == "win32":
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if cap.isOpened():
            return cap
        cap.release()
    return cv2.VideoCapture(index)
