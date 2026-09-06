"""Translate English sentences. Google first, MyMemory as fallback."""

from __future__ import annotations

import json
import ssl
import urllib.parse
import urllib.request

LANGS = [
    ("English", "en"),
    ("Hindi", "hi"),
    ("Kannada", "kn"),
    ("Tamil", "ta"),
    ("Telugu", "te"),
    ("Malayalam", "ml"),
    ("Spanish", "es"),
    ("French", "fr"),
    ("German", "de"),
    ("Arabic", "ar"),
    ("Japanese", "ja"),
]

LANG_NAMES = [name for name, _ in LANGS]

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
}

_CACHE: dict[tuple[str, str, str], str] = {}


def lang_code(name: str) -> str:
    for n, c in LANGS:
        if n == name:
            return c
    return "en"


def _open(url: str, timeout: float = 10):
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers=_HEADERS)
    return urllib.request.urlopen(req, timeout=timeout, context=ctx)


def _google_clients5(text: str, src: str, dst: str) -> str:
    q = urllib.parse.urlencode({"client": "dict-chrome-ex", "sl": src, "tl": dst, "q": text})
    url = "https://clients5.google.com/translate_a/t?" + q
    with _open(url) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if isinstance(payload, list) and payload:
        first = payload[0]
        if isinstance(first, str) and first.strip():
            return first.strip()
        if isinstance(first, list) and first and isinstance(first[0], str):
            return first[0].strip()
    raise RuntimeError("empty clients5 result")


def _google_gtx(text: str, src: str, dst: str) -> str:
    q = urllib.parse.urlencode({"client": "gtx", "sl": src, "tl": dst, "dt": "t", "q": text})
    url = "https://translate.googleapis.com/translate_a/single?" + q
    with _open(url) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    chunks = payload[0] if payload else []
    out = "".join(part[0] for part in chunks if part and part[0])
    if not out.strip():
        raise RuntimeError("empty gtx result")
    return out.strip()


def _mymemory(text: str, src: str, dst: str) -> str:
    q = urllib.parse.urlencode({"q": text[:500], "langpair": f"{src}|{dst}"})
    url = "https://api.mymemory.translated.net/get?" + q
    with _open(url) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    translated = (payload.get("responseData") or {}).get("translatedText") or ""
    if not translated.strip():
        raise RuntimeError("empty mymemory result")
    if translated.lower().startswith("mymemory warning"):
        raise RuntimeError("mymemory quota")
    return translated.strip()


def translate_text(text: str, source: str = "English", target: str = "Hindi") -> str:
    """Return translated text, or raise RuntimeError with a short reason."""
    text = (text or "").strip()
    if not text:
        raise RuntimeError("Nothing to translate.")
    src, dst = lang_code(source), lang_code(target)
    if src == dst:
        return text
    cached = _CACHE.get((text, src, dst))
    if cached:
        return cached
    errors = []
    for fn in (_google_clients5, _google_gtx, _mymemory):
        try:
            out = fn(text, src, dst)
            _CACHE[(text, src, dst)] = out
            return out
        except Exception as exc:
            errors.append(f"{fn.__name__}: {exc.__class__.__name__}")
    raise RuntimeError("Could not translate (" + "; ".join(errors) + "). Check the network.")
