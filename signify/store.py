"""Local SQLite persistence: accounts, profiles, usage, detections, practice."""

from __future__ import annotations

import hashlib
import hmac
import os
import re
from datetime import date, datetime, timedelta

from .db import connect

USERNAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{2,31}$")
GMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@gmail\.com$", re.IGNORECASE)


def _hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return salt.hex(), digest.hex()


def _verify_password(password: str, salt_hex: str, hash_hex: str) -> bool:
    try:
        salt = bytes.fromhex(salt_hex)
    except ValueError:
        return False
    _, digest = _hash_password(password, salt)
    return hmac.compare_digest(digest, hash_hex)


class AuthError(Exception):
    pass


class LocalAuth:
    def __init__(self, db_path=None):
        self.conn = connect(db_path)

    def user_count(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()
        return int(row["n"])

    def has_user(self, username: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM users WHERE username = ?", (username.strip(),)
        ).fetchone()
        return row is not None

    def last_username(self) -> str:
        row = self.conn.execute(
            "SELECT value FROM meta WHERE key = 'last_username'"
        ).fetchone()
        return row["value"] if row else ""

    def set_last_username(self, username: str):
        self.conn.execute(
            "INSERT INTO meta(key, value) VALUES('last_username', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (username,),
        )
        self.conn.commit()

    def signup(self, username: str, password: str, confirm: str,
               name: str, email: str = "", location: str = "", bio: str = "") -> str:
        username = (username or "").strip()
        name = (name or "").strip()
        email = (email or "").strip()
        location = (location or "").strip()
        bio = (bio or "").strip()

        if not username:
            raise AuthError("Username is required.")
        if not USERNAME_RE.match(username):
            raise AuthError("Username must start with a letter and be 3–32 characters.")
        if len(password or "") < 4:
            raise AuthError("Password must be at least 4 characters.")
        if password != confirm:
            raise AuthError("Passwords do not match.")
        if len(name) < 2:
            raise AuthError("Full name is required.")
        if not email:
            raise AuthError("Email is required.")
        if not GMAIL_RE.match(email):
            raise AuthError("Email must be a valid @gmail.com address.")
        if len(bio) < 2:
            raise AuthError("Short bio is required.")
        if self.has_user(username):
            raise AuthError("That username is already taken.")

        salt, pw_hash = _hash_password(password)
        now = datetime.now().isoformat(timespec="seconds")
        self.conn.execute(
            """INSERT INTO users
               (username, salt, password_hash, name, email, location, bio, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (username, salt, pw_hash, name, email, location, bio, now),
        )
        self.conn.execute(
            "INSERT INTO practice(username) VALUES (?)", (username,)
        )
        self.conn.commit()
        self.set_last_username(username)
        return username

    def login(self, username: str, password: str) -> str:
        username = (username or "").strip()
        if not username:
            raise AuthError("Enter your username.")
        row = self.conn.execute(
            "SELECT username, salt, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if row is None:
            raise AuthError("NO_ACCOUNT")
        if not _verify_password(password or "", row["salt"], row["password_hash"]):
            raise AuthError("Wrong password.")
        self.set_last_username(row["username"])
        return row["username"]


class AppStore:
    """Per-user view of the local database. Same API the screens already use."""

    def __init__(self, username: str, db_path=None):
        self.username = username
        self.conn = connect(db_path)
        self._reload()

    def _reload(self):
        row = self.conn.execute(
            "SELECT * FROM users WHERE username = ?", (self.username,)
        ).fetchone()
        if row is None:
            raise AuthError(f"Unknown user: {self.username}")
        self._profile = {
            "name": row["name"],
            "email": row["email"],
            "location": row["location"],
            "bio": row["bio"],
            "username": row["username"],
        }
        self._settings = {
            "min_confidence": float(row["min_confidence"]),
            "tts_rate": int(row["tts_rate"]),
            "auto_speak": bool(row["auto_speak"]),
            "autocorrect": bool(row["autocorrect"]),
            "translate_lang": row["translate_lang"] or "Hindi",
            "dual_subs": bool(row["dual_subs"]) if "dual_subs" in row.keys() else True,
        }

    @property
    def profile(self) -> dict:
        return self._profile

    def update_profile(self, **fields):
        allowed = ("name", "email", "location", "bio")
        sets, vals = [], []
        for key, val in fields.items():
            if key in allowed:
                sets.append(f"{key} = ?")
                vals.append(val)
        if not sets:
            return
        vals.append(self.username)
        self.conn.execute(
            f"UPDATE users SET {', '.join(sets)} WHERE username = ?", vals
        )
        self.conn.commit()
        self._reload()

    @property
    def settings(self) -> dict:
        return self._settings

    def update_settings(self, **fields):
        allowed = {
            "min_confidence": float,
            "tts_rate": int,
            "auto_speak": lambda v: 1 if v else 0,
            "autocorrect": lambda v: 1 if v else 0,
            "translate_lang": str,
            "dual_subs": lambda v: 1 if v else 0,
        }
        sets, vals = [], []
        for key, val in fields.items():
            if key not in allowed:
                continue
            sets.append(f"{key} = ?")
            vals.append(allowed[key](val))
        if not sets:
            return
        vals.append(self.username)
        self.conn.execute(
            f"UPDATE users SET {', '.join(sets)} WHERE username = ?", vals
        )
        self.conn.commit()
        self._reload()

    def add_usage_seconds(self, seconds: int, day: str | None = None):
        if seconds <= 0:
            return
        key = day or date.today().isoformat()
        self.conn.execute(
            """INSERT INTO usage_days(username, day, seconds) VALUES (?, ?, ?)
               ON CONFLICT(username, day) DO UPDATE SET
               seconds = seconds + excluded.seconds""",
            (self.username, key, int(seconds)),
        )
        self.conn.commit()

    def _seconds_on(self, day: str) -> int:
        row = self.conn.execute(
            "SELECT seconds FROM usage_days WHERE username = ? AND day = ?",
            (self.username, day),
        ).fetchone()
        return int(row["seconds"]) if row else 0

    def seconds_in_range(self, start: date, end: date) -> int:
        total = 0
        cur = start
        while cur <= end:
            total += self._seconds_on(cur.isoformat())
            cur += timedelta(days=1)
        return total

    def today_seconds(self) -> int:
        return self._seconds_on(date.today().isoformat())

    def week_seconds(self) -> int:
        today = date.today()
        start = today - timedelta(days=today.weekday())
        return self.seconds_in_range(start, today)

    def month_seconds(self) -> int:
        today = date.today()
        return self.seconds_in_range(today.replace(day=1), today)

    def year_seconds(self) -> int:
        today = date.today()
        return self.seconds_in_range(today.replace(month=1, day=1), today)

    def last_n_days(self, n: int = 7) -> list[tuple[str, int]]:
        today = date.today()
        out = []
        for i in range(n - 1, -1, -1):
            d = today - timedelta(days=i)
            out.append((d.strftime("%a"), self._seconds_on(d.isoformat())))
        return out

    def last_n_weeks(self, n: int = 8) -> list[tuple[str, int]]:
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        out = []
        for i in range(n - 1, -1, -1):
            start = monday - timedelta(weeks=i)
            end = start + timedelta(days=6)
            out.append((start.strftime("%d %b"),
                        self.seconds_in_range(start, min(end, today))))
        return out

    def last_n_months(self, n: int = 6) -> list[tuple[str, int]]:
        today = date.today()
        y, m = today.year, today.month
        months = []
        for _ in range(n):
            months.append((y, m))
            m -= 1
            if m == 0:
                m, y = 12, y - 1
        months.reverse()
        out = []
        for y, m in months:
            start = date(y, m, 1)
            end = date(y, 12, 31) if m == 12 else date(y, m + 1, 1) - timedelta(days=1)
            out.append((start.strftime("%b"),
                        self.seconds_in_range(start, min(end, today))))
        return out

    def last_n_years(self, n: int = 4) -> list[tuple[str, int]]:
        today = date.today()
        out = []
        for i in range(n - 1, -1, -1):
            y = today.year - i
            start, end = date(y, 1, 1), date(y, 12, 31)
            out.append((str(y), self.seconds_in_range(start, min(end, today))))
        return out

    def record_detection(self, label: str, score: float):
        if not label:
            return
        self.conn.execute(
            "INSERT INTO detections(username, ts, label, score) VALUES (?, ?, ?, ?)",
            (self.username, datetime.now().isoformat(timespec="seconds"),
             label, round(float(score), 3)),
        )
        extra = self.conn.execute(
            """SELECT id FROM detections WHERE username = ?
               ORDER BY id DESC LIMIT 1 OFFSET 500""",
            (self.username,),
        ).fetchone()
        if extra:
            self.conn.execute(
                "DELETE FROM detections WHERE username = ? AND id <= ?",
                (self.username, extra["id"]),
            )
        self.conn.commit()

    def top_signs(self, n: int = 8) -> list[tuple[str, int]]:
        rows = self.conn.execute(
            """SELECT label, COUNT(*) AS c FROM detections
               WHERE username = ? GROUP BY label ORDER BY c DESC LIMIT ?""",
            (self.username, n),
        ).fetchall()
        return [(r["label"], int(r["c"])) for r in rows]

    def add_sentence(self, text: str):
        text = (text or "").strip()
        if not text:
            return
        self.conn.execute(
            "INSERT INTO sentences(username, ts, text) VALUES (?, ?, ?)",
            (self.username, datetime.now().isoformat(timespec="seconds"), text),
        )
        self.conn.commit()

    def recent_sentences(self, n: int = 8) -> list[dict]:
        rows = self.conn.execute(
            """SELECT ts, text FROM sentences WHERE username = ?
               ORDER BY id DESC LIMIT ?""",
            (self.username, n),
        ).fetchall()
        return [{"ts": r["ts"], "text": r["text"]} for r in rows]

    @property
    def practice(self) -> dict:
        row = self.conn.execute(
            "SELECT * FROM practice WHERE username = ?", (self.username,)
        ).fetchone()
        if row is None:
            self.conn.execute(
                "INSERT INTO practice(username) VALUES (?)", (self.username,)
            )
            self.conn.commit()
            return {"correct": 0, "attempts": 0, "best_streak": 0, "streak": 0}
        return {
            "correct": int(row["correct"]),
            "attempts": int(row["attempts"]),
            "best_streak": int(row["best_streak"]),
            "streak": int(row["streak"]),
        }

    def record_practice(self, correct: bool):
        p = self.practice
        attempts = p["attempts"] + 1
        if correct:
            c = p["correct"] + 1
            streak = p["streak"] + 1
            best = max(p["best_streak"], streak)
        else:
            c = p["correct"]
            streak = 0
            best = p["best_streak"]
        self.conn.execute(
            """UPDATE practice SET correct=?, attempts=?, best_streak=?, streak=?
               WHERE username=?""",
            (c, attempts, best, streak, self.username),
        )
        self.conn.commit()
