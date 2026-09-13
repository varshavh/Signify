"""Offline text-to-speech. Uses pyttsx3 (same engine as the rest of Signify)."""

import sys
import threading

# Substrings matched against installed SAPI / macOS voice names.
_VOICE_HINTS = {
    "en": ["english", "david", "zira", "samantha", "alex", "daniel"],
    "hi": ["hindi", "heera", "kalpana", "lekha"],
    "kn": ["kannada"],
    "ta": ["tamil"],
    "te": ["telugu"],
    "ml": ["malayalam"],
    "es": ["spanish", "helena", "sabina", "jorge", "monica"],
    "fr": ["french", "hortense", "thomas", "amelie"],
    "de": ["german", "hedda", "stefan", "anna"],
    "ar": ["arabic", "hoda", "naayf"],
    "ja": ["japanese", "haruka", "kyoko", "otoya"],
}


def speak(text: str, rate: int = 160, language: str | None = None):
    """Speak `text` when called (never automatic). `language` is a name like Hindi."""
    text = (text or "").strip()
    if not text:
        return
    threading.Thread(target=_worker, args=(text, rate, language), daemon=True).start()


def _lang_code(language: str | None) -> str:
    if not language:
        return "en"
    from .translate import lang_code
    return lang_code(language)


def _pick_voice(engine, language: str | None):
    code = _lang_code(language)
    hints = _VOICE_HINTS.get(code) or _VOICE_HINTS["en"]
    try:
        voices = engine.getProperty("voices") or []
    except Exception:
        return
    for hint in hints:
        for voice in voices:
            blob = " ".join(
                str(part) for part in (
                    getattr(voice, "name", "") or "",
                    getattr(voice, "id", "") or "",
                    getattr(voice, "languages", None) or "",
                )
            ).lower()
            if hint in blob:
                engine.setProperty("voice", voice.id)
                return


def _worker(text: str, rate: int, language: str | None):
    try:
        import pyttsx3
        driver = "sapi5" if sys.platform == "win32" else None
        engine = pyttsx3.init(driver) if driver else pyttsx3.init()
        engine.setProperty("rate", int(rate))
        _pick_voice(engine, language)
        engine.say(text)
        engine.runAndWait()
        engine.stop()
    except Exception as exc:
        print("[speak] error:", exc)
