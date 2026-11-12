"""SQLite storage for accounts, rooms and messages.

Passwords are never stored in plain text. Each one is hashed with PBKDF2-SHA256
and a random per-user salt. Messages are stored unencrypted (see README).
"""

import hashlib
import hmac
import os
import sqlite3
import threading
from contextlib import closing

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat.db")
ITERATIONS = 200_000
_write_lock = threading.Lock()


def _connect():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with closing(_connect()) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL COLLATE NOCASE,
                salt BLOB NOT NULL,
                pw_hash BLOB NOT NULL
            );
            CREATE TABLE IF NOT EXISTS rooms (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY,
                room_id INTEGER NOT NULL REFERENCES rooms(id),
                username TEXT NOT NULL,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );
            """
        )
        conn.commit()


def _hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)


def create_user(username, password):
    """Return True if the account was created, False if the name is taken."""
    salt = os.urandom(16)
    with _write_lock, closing(_connect()) as conn:
        try:
            conn.execute(
                "INSERT INTO users (username, salt, pw_hash) VALUES (?, ?, ?)",
                (username, salt, _hash(password, salt)),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def check_login(username, password):
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT salt, pw_hash FROM users WHERE username = ?", (username,)
        ).fetchone()
    if row is None:
        # Do the same work for unknown users so response time doesn't reveal which names exist.
        _hash(password, b"\0" * 16)
        return False
    return hmac.compare_digest(_hash(password, row["salt"]), row["pw_hash"])


def get_room_id(name):
    with _write_lock, closing(_connect()) as conn:
        conn.execute("INSERT OR IGNORE INTO rooms (name) VALUES (?)", (name,))
        conn.commit()
        return conn.execute("SELECT id FROM rooms WHERE name = ?", (name,)).fetchone()["id"]


def list_rooms():
    with closing(_connect()) as conn:
        return [row["name"] for row in conn.execute("SELECT name FROM rooms ORDER BY name")]


def save_message(room, username, text):
    room_id = get_room_id(room)
    with _write_lock, closing(_connect()) as conn:
        conn.execute(
            "INSERT INTO messages (room_id, username, text) VALUES (?, ?, ?)",
            (room_id, username, text),
        )
        conn.commit()


def recent_messages(room, limit=50):
    """Return the latest messages in a room, oldest first."""
    with closing(_connect()) as conn:
        rows = conn.execute(
            """
            SELECT m.username, m.text, m.created_at
            FROM messages m JOIN rooms r ON r.id = m.room_id
            WHERE r.name = ?
            ORDER BY m.id DESC
            LIMIT ?
            """,
            (room, limit),
        ).fetchall()
    return list(reversed(rows))
