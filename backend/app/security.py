"""Admin authentication: password hashing, signed sessions, CSRF, rate limiting.

Everything here uses the standard library. Sessions are signed tokens, not
server-side records, so the app stays stateless apart from the admin user
row in the database.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque
from typing import Deque

SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 32
SALT_BYTES = 16


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


def hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    """Return ``(password_hash, salt)``, both base64url encoded."""
    if salt is None:
        salt = secrets.token_bytes(SALT_BYTES)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_DKLEN,
    )
    return _b64encode(derived), _b64encode(salt)


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """Check a password against a stored hash, never raising on bad input."""
    try:
        derived, _ = hash_password(password, _b64decode(salt))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(derived, stored_hash)


def _sign(payload: str, secret: str) -> str:
    signature = hmac.new(
        secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
    ).digest()
    return _b64encode(signature)


def create_session_token(username: str, secret: str, expires_at: int) -> str:
    """Build a signed session token carrying the username and an expiry.

    Every call produces a different token, even for the same user and the
    same expiry, so a CSRF token is bound to exactly one session.
    """
    payload = f"{_b64encode(username.encode('utf-8'))}|{expires_at}|{secrets.token_urlsafe(16)}"
    return f"{_b64encode(payload.encode('utf-8'))}.{_sign(payload, secret)}"


def verify_session_token(
    token: str, secret: str, now: int | None = None
) -> str | None:
    """Return the username when the token is valid, otherwise ``None``."""
    if not token:
        return None
    encoded_payload, separator, signature = token.partition(".")
    if not separator:
        return None
    try:
        payload = _b64decode(encoded_payload).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None
    if not hmac.compare_digest(_sign(payload, secret), signature):
        return None
    parts = payload.split("|")
    if len(parts) < 2:
        return None
    encoded_username, expiry = parts[0], parts[1]
    if not expiry.isdigit():
        return None
    if int(expiry) <= int(time.time() if now is None else now):
        return None
    try:
        username = _b64decode(encoded_username).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None
    return username or None


def csrf_token(session_token: str, secret: str) -> str:
    """Derive the CSRF token that belongs to one session."""
    return _sign(session_token, secret)


def check_csrf(session_token: str, csrf: str, secret: str) -> bool:
    """Check a submitted CSRF token against the session it must belong to."""
    if not session_token or not csrf:
        return False
    return hmac.compare_digest(csrf_token(session_token, secret), csrf)


class RateLimiter:
    """A sliding-window limiter keyed by an arbitrary string."""

    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, Deque[float]] = defaultdict(deque)

    def _prune(self, key: str, now: float) -> Deque[float]:
        hits = self._hits[key]
        cutoff = now - self.window_seconds
        while hits and hits[0] <= cutoff:
            hits.popleft()
        return hits

    def allow(self, key: str, now: float | None = None) -> bool:
        """Record an attempt and report whether it is within the budget."""
        moment = time.time() if now is None else now
        hits = self._prune(key, moment)
        if len(hits) >= self.limit:
            return False
        hits.append(moment)
        return True

    def retry_after(self, key: str, now: float | None = None) -> int:
        """Seconds until the oldest attempt leaves the window."""
        moment = time.time() if now is None else now
        hits = self._prune(key, moment)
        if not hits:
            return 0
        return max(1, int(round(self.window_seconds - (moment - hits[0]))))
