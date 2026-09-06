"""Offline text-to-speech. Uses pyttsx3 (same engine as the rest of Signify)."""

import sys
import threading


def speak(text: str, rate: int = 160):
    text = (text or "").strip()
    if not text:
        return
    threading.Thread(target=_worker, args=(text, rate), daemon=True).start()


def _worker(text: str, rate: int):
    try:
        import pyttsx3
        driver = "sapi5" if sys.platform == "win32" else None
        engine = pyttsx3.init(driver) if driver else pyttsx3.init()
        engine.setProperty("rate", int(rate))
        engine.say(text)
        engine.runAndWait()
        engine.stop()
    except Exception as exc:
        print("[speak] error:", exc)
