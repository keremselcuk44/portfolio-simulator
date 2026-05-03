"""Database — lightweight SQLite persistence for users, trades, sessions.

Design
------
* Pure stdlib: sqlite3 + hashlib, no extra pip installs.
* Single file DB stored at ``data/portfoliosim.db``.
* Thread-safe for single-writer (PyQt main thread only).
* Passwords stored as SHA-256 hex digests with a per-user salt.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path


# ── Data containers ───────────────────────────────────────────────────────────

@dataclass
class UserRow:
    id: int
    username: str


# ── Database ──────────────────────────────────────────────────────────────────

class Database:
    """Thin wrapper around a single SQLite connection."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None:
            db_path = Path(__file__).resolve().parents[2] / "data" / "portfoliosim.db"
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._create_tables()

    # ── Schema ────────────────────────────────────────────────────────────────

    def _create_tables(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT    UNIQUE NOT NULL,
                password_hash TEXT    NOT NULL,
                salt          TEXT    NOT NULL,
                created_at    TEXT    DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS trades (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id),
                side        TEXT    NOT NULL,
                symbol      TEXT    NOT NULL,
                quantity    REAL    NOT NULL,
                price       REAL    NOT NULL,
                total       REAL    NOT NULL,
                timestamp   TEXT    NOT NULL,
                session_id  TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id),
                session_id  TEXT    UNIQUE NOT NULL,
                started_at  TEXT    DEFAULT (datetime('now')),
                ended_at    TEXT,
                final_value REAL,
                total_pnl   REAL,
                trade_count INTEGER DEFAULT 0,
                xp_earned   INTEGER DEFAULT 0
            );
        """)
        self._conn.commit()

    # ── Auth helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()

    def register_user(self, username: str, password: str) -> UserRow | str:
        """Register a new user. Returns UserRow on success, error string on failure."""
        username = username.strip()
        if not username or not password:
            return "Kullanıcı adı ve şifre boş bırakılamaz."
        if len(username) < 3:
            return "Kullanıcı adı en az 3 karakter olmalıdır."
        if len(password) < 4:
            return "Şifre en az 4 karakter olmalıdır."

        salt = uuid.uuid4().hex
        pw_hash = self._hash_password(password, salt)
        try:
            cur = self._conn.execute(
                "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
                (username, pw_hash, salt),
            )
            self._conn.commit()
            return UserRow(id=cur.lastrowid, username=username)  # type: ignore[arg-type]
        except sqlite3.IntegrityError:
            return "Bu kullanıcı adı zaten kayıtlı."

    def verify_login(self, username: str, password: str) -> UserRow | str:
        """Verify credentials. Returns UserRow on success, error string on failure."""
        username = username.strip()
        row = self._conn.execute(
            "SELECT id, username, password_hash, salt FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if row is None:
            return "Kullanıcı bulunamadı."
        uid, uname, pw_hash, salt = row
        if self._hash_password(password, salt) != pw_hash:
            return "Şifre hatalı."
        return UserRow(id=uid, username=uname)

    # ── Trade persistence ─────────────────────────────────────────────────────

    def save_trade(
        self,
        user_id: int,
        session_id: str,
        side: str,
        symbol: str,
        quantity: float,
        price: float,
        total: float,
        timestamp: str,
    ) -> None:
        self._conn.execute(
            "INSERT INTO trades (user_id, session_id, side, symbol, quantity, price, total, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, session_id, side, symbol, quantity, price, total, timestamp),
        )
        self._conn.commit()

    # ── Session persistence ───────────────────────────────────────────────────

    def start_session(self, user_id: int, session_id: str) -> None:
        self._conn.execute(
            "INSERT INTO sessions (user_id, session_id) VALUES (?, ?)",
            (user_id, session_id),
        )
        self._conn.commit()

    def end_session(
        self,
        session_id: str,
        final_value: float,
        total_pnl: float,
        trade_count: int,
        xp_earned: int,
    ) -> None:
        self._conn.execute(
            "UPDATE sessions SET ended_at = datetime('now'), final_value = ?, "
            "total_pnl = ?, trade_count = ?, xp_earned = ? WHERE session_id = ?",
            (final_value, total_pnl, trade_count, xp_earned, session_id),
        )
        self._conn.commit()

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def close(self) -> None:
        self._conn.close()
