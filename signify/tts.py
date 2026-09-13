"""Text-to-speech. English uses the local voice; other languages use Google TTS.

No extra pip package. Translation speech needs the same internet as Translate.
Windows often has no Hindi/Kannada SAPI voice, so local TTS stays silent —
Google TTS is what actually plays those languages.
"""

from __future__ import annotations

import os
import ssl
import subprocess
import sys
import tempfile
import threading
import urllib.parse
import urllib.request

# Prefer locale tags so we do not match "hi" inside "Whisper".
_VOICE_NEEDLES = {
    "en": ["en-us", "en_us", "en-gb", "en-in", "english", "samantha", "zira", "david"],
    "hi": ["hi-in", "hi_in", "hindi", "lekha", "heera", "kalpana"],
    "kn": ["kn-in", "kn_in", "kannada", "alpana", "soumya"],
    "ta": ["ta-in", "ta_in", "tamil", "vani"],
    "te": ["te-in", "te_in", "telugu", "geeta"],
    "ml": ["ml-in", "ml_in", "malayalam"],
    "es": ["es-es", "es-mx", "spanish", "monica", "helena"],
    "fr": ["fr-fr", "fr-ca", "french", "thomas", "amelie"],
    "de": ["de-de", "german", "anna", "hedda"],
    "ar": ["ar-", "arabic", "maged", "hoda"],
    "ja": ["ja-jp", "japanese", "kyoko", "haruka"],
}

_MAC_SAY = {
    "en": "Samantha",
    "hi": "Lekha",
    "kn": "Soumya",
    "ta": "Vani",
    "te": "Geeta",
    "es": "Monica",
    "fr": "Thomas",
    "de": "Anna",
    "ar": "Majed",
    "ja": "Kyoko",
}

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://translate.google.com/",
}

_last_status = ""
_lock = threading.Lock()


def speak(text: str, rate: int = 160, language: str | None = None):
    """Speak `text` only when called (never automatic)."""
    text = (text or "").strip()
    if not text:
        return
    threading.Thread(target=_worker, args=(text, rate, language), daemon=True).start()


def pop_status() -> str:
    global _last_status
    with _lock:
        msg = _last_status
        _last_status = ""
        return msg


def _set_status(msg: str):
    global _last_status
    with _lock:
        _last_status = msg
    print("[speak]", msg)


def _lang_code(language: str | None) -> str:
    if not language:
        return "en"
    from .translate import lang_code
    return lang_code(language)


def _worker(text: str, rate: int, language: str | None):
    code = _lang_code(language)
    errors = []
    # Translated speech: Google first (works without a Hindi/Kannada system voice).
    if code != "en":
        try:
            _speak_google(text, code)
            return
        except Exception as exc:
            errors.append(f"google:{exc}")
        try:
            _speak_local(text, rate, code)
            return
        except Exception as exc:
            errors.append(f"local:{exc}")
        _set_status("Could not speak translation. Check internet (same as Translate).")
        print("[speak] error:", "; ".join(errors))
        return
    try:
        _speak_local(text, rate, code)
        return
    except Exception as exc:
        errors.append(f"local:{exc}")
    try:
        _speak_google(text, "en")
        return
    except Exception as exc:
        errors.append(f"google:{exc}")
    _set_status("Could not speak. Check speakers and internet.")
    print("[speak] error:", "; ".join(errors))


def _speak_local(text: str, rate: int, code: str):
    if sys.platform == "darwin":
        voice = _MAC_SAY.get(code)
        cmd = ["say"]
        if voice:
            cmd += ["-v", voice]
        # say rate: 160 pyttsx3 ~ 175 default say; map roughly
        wrds = max(120, min(280, int(rate) + 20))
        cmd += ["-r", str(wrds), text]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            return
        # Voice missing (typical on Windows-like setups; on Mac if language pack absent).
        raise RuntimeError(r.stderr.strip() or "say failed")
    import pyttsx3
    driver = "sapi5" if sys.platform == "win32" else None
    engine = pyttsx3.init(driver) if driver else pyttsx3.init()
    engine.setProperty("rate", int(rate))
    _pick_voice(engine, code)
    engine.say(text)
    engine.runAndWait()
    engine.stop()


def _pick_voice(engine, code: str):
    needles = _VOICE_NEEDLES.get(code) or _VOICE_NEEDLES["en"]
    try:
        voices = engine.getProperty("voices") or []
    except Exception:
        return
    for voice in voices:
        blob = " ".join(
            str(part) for part in (
                getattr(voice, "name", "") or "",
                getattr(voice, "id", "") or "",
            )
        ).lower()
        if any(n in blob for n in needles):
            engine.setProperty("voice", voice.id)
            return


def _chunks(text: str, n: int = 180):
    text = text.strip()
    while text:
        if len(text) <= n:
            yield text
            return
        cut = text.rfind(" ", 0, n)
        if cut < 20:
            cut = n
        yield text[:cut].strip()
        text = text[cut:].strip()


def _speak_google(text: str, tl: str):
    pieces = list(_chunks(text))
    if not pieces:
        return
    ctx = ssl.create_default_context()
    audio = b""
    for piece in pieces:
        q = urllib.parse.urlencode(
            {"ie": "UTF-8", "client": "tw-ob", "tl": tl, "q": piece}
        )
        url = "https://translate.google.com/translate_tts?" + q
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            data = resp.read()
        if len(data) < 500:
            raise RuntimeError("empty audio")
        audio += data
    _play_mp3(audio)


def _play_mp3(data: bytes):
    fd, path = tempfile.mkstemp(suffix=".mp3")
    try:
        os.write(fd, data)
        os.close(fd)
        fd = -1
        if sys.platform == "darwin":
            r = subprocess.run(["afplay", path], capture_output=True)
            if r.returncode != 0:
                raise RuntimeError("afplay failed")
            return
        if sys.platform == "win32":
            _play_mp3_windows(path)
            return
        for cmd in (
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path],
            ["mpg123", "-q", path],
        ):
            try:
                r = subprocess.run(cmd, capture_output=True)
            except FileNotFoundError:
                continue
            if r.returncode == 0:
                return
        raise RuntimeError("no mp3 player")
    finally:
        if fd >= 0:
            os.close(fd)
        try:
            os.remove(path)
        except OSError:
            pass


def _play_mp3_windows(path: str):
    import ctypes
    path = os.path.abspath(path)
    mci = ctypes.windll.winmm.mciSendStringW
    alias = "signifytts"
    buf = ctypes.create_unicode_buffer(256)

    def cmd(s: str):
        err = mci(s, buf, 255, None)
        if err:
            ctypes.windll.winmm.mciGetErrorStringW(err, buf, 255)
            raise RuntimeError(buf.value or f"mci {err}")

    cmd(f'open "{path}" type mpegvideo alias {alias}')
    try:
        cmd(f"play {alias} wait")
    finally:
        mci(f"close {alias}", None, 0, None)
