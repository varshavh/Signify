"""Local SQLite database for accounts and per-user app data."""

from __future__ import annotations

import sqlite3
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "signify.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    salt TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    location TEXT NOT NULL DEFAULT '',
    bio TEXT NOT NULL DEFAULT '',
    min_confidence REAL NOT NULL DEFAULT 0.45,
    tts_rate INTEGER NOT NULL DEFAULT 160,
    auto_speak INTEGER NOT NULL DEFAULT 0,
    autocorrect INTEGER NOT NULL DEFAULT 1,
    translate_lang TEXT NOT NULL DEFAULT 'Hindi',
    dual_subs INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS usage_days (
    username TEXT NOT NULL,
    day TEXT NOT NULL,
    seconds INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (username, day)
);

CREATE TABLE IF NOT EXISTS detections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    ts TEXT NOT NULL,
    label TEXT NOT NULL,
    score REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS sentences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    ts TEXT NOT NULL,
    text TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS practice (
    username TEXT PRIMARY KEY,
    correct INTEGER NOT NULL DEFAULT 0,
    attempts INTEGER NOT NULL DEFAULT 0,
    best_streak INTEGER NOT NULL DEFAULT 0,
    streak INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS custom_signs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    label TEXT NOT NULL,
    landmarks TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def connect(path: Path | None = None) -> sqlite3.Connection:
    db_path = Path(path) if path else DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(_SCHEMA)
    _migrate(conn)
    return conn


def _migrate(conn: sqlite3.Connection):
    cols = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
    if "translate_lang" not in cols:
        conn.execute(
            "ALTER TABLE users ADD COLUMN translate_lang TEXT NOT NULL DEFAULT 'Hindi'"
        )
        conn.commit()
    if "dual_subs" not in cols:
        conn.execute(
            "ALTER TABLE users ADD COLUMN dual_subs INTEGER NOT NULL DEFAULT 1"
        )
        conn.commit()
