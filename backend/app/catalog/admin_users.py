"""The admin user row."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from app.security import hash_password, verify_password


def find_admin_user(
    conn: sqlite3.Connection, username: str
) -> tuple[str, str] | None:
    """The stored ``(password_hash, salt)`` of an admin user."""
    row = conn.execute(
        "SELECT password_hash, salt FROM admin_users WHERE username = ?", (username,)
    ).fetchone()
    if row is None:
        return None
    return str(row["password_hash"]), str(row["salt"])


def ensure_admin_user(
    conn: sqlite3.Connection, username: str, password: str
) -> None:
    """Make sure the configured admin user exists and uses the configured password.

    The password comes from the environment, so changing it there and
    restarting is enough to change it. An empty password is never stored,
    because an account with no password is an account anybody can use.
    """
    username = (username or "").strip()
    if not username or not password:
        return

    stored = find_admin_user(conn, username)
    if stored is not None and verify_password(password, stored[0], stored[1]):
        return

    password_hash, salt = hash_password(password)
    if stored is None:
        conn.execute(
            "INSERT INTO admin_users (username, password_hash, salt, created_at)"
            " VALUES (?, ?, ?, ?)",
            (username, password_hash, salt, _now()),
        )
    else:
        conn.execute(
            "UPDATE admin_users SET password_hash = ?, salt = ? WHERE username = ?",
            (password_hash, salt, username),
        )
    conn.commit()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
