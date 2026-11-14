from __future__ import annotations

import time

from app.security import (
    RateLimiter,
    create_session_token,
    csrf_token,
    check_csrf,
    hash_password,
    verify_password,
    verify_session_token,
)

SECRET = "a-test-secret"


def test_password_round_trip() -> None:
    stored_hash, salt = hash_password("correct horse battery staple")

    assert verify_password("correct horse battery staple", stored_hash, salt) is True
    assert verify_password("wrong password", stored_hash, salt) is False


def test_hash_uses_a_random_salt_each_time() -> None:
    first_hash, first_salt = hash_password("same-password")
    second_hash, second_salt = hash_password("same-password")

    assert first_salt != second_salt
    assert first_hash != second_hash
    assert verify_password("same-password", first_hash, first_salt) is True
    assert verify_password("same-password", second_hash, second_salt) is True


def test_verify_password_rejects_a_tampered_hash() -> None:
    stored_hash, salt = hash_password("secret")

    assert verify_password("secret", stored_hash[:-4] + "AAAA", salt) is False


def test_session_token_round_trip() -> None:
    token = create_session_token("owner", SECRET, expires_at=2_000_000_000)

    assert verify_session_token(token, SECRET) == "owner"


def test_session_token_is_rejected_when_tampered() -> None:
    token = create_session_token("owner", SECRET, expires_at=2_000_000_000)
    payload, _, signature = token.partition(".")
    tampered = f"{payload}.{signature[:-2]}XY"

    assert verify_session_token(tampered, SECRET) is None


def test_session_token_is_rejected_with_the_wrong_secret() -> None:
    token = create_session_token("owner", SECRET, expires_at=2_000_000_000)

    assert verify_session_token(token, "another-secret") is None


def test_expired_session_token_is_rejected() -> None:
    token = create_session_token("owner", SECRET, expires_at=1_000)
    now = int(time.time())

    assert verify_session_token(token, SECRET, now=now) is None


def test_csrf_token_matches_only_its_own_session() -> None:
    first = create_session_token("owner", SECRET, expires_at=2_000_000_000)
    second = create_session_token("owner", SECRET, expires_at=2_000_000_000)

    token = csrf_token(first, SECRET)

    assert check_csrf(first, token, SECRET) is True
    assert check_csrf(second, token, SECRET) is False
    assert check_csrf(first, "not-the-token", SECRET) is False


def test_rate_limiter_blocks_after_the_limit() -> None:
    limiter = RateLimiter(limit=3, window_seconds=60)

    assert limiter.allow("1.2.3.4") is True
    assert limiter.allow("1.2.3.4") is True
    assert limiter.allow("1.2.3.4") is True
    assert limiter.allow("1.2.3.4") is False


def test_rate_limiter_is_per_key() -> None:
    limiter = RateLimiter(limit=1, window_seconds=60)

    assert limiter.allow("1.2.3.4") is True
    assert limiter.allow("1.2.3.4") is False
    assert limiter.allow("5.6.7.8") is True


def test_rate_limiter_reports_a_retry_after() -> None:
    limiter = RateLimiter(limit=1, window_seconds=60)

    limiter.allow("1.2.3.4")

    assert 0 < limiter.retry_after("1.2.3.4") <= 60


def test_rate_limiter_forgets_old_attempts() -> None:
    limiter = RateLimiter(limit=1, window_seconds=1)

    assert limiter.allow("1.2.3.4") is True
    assert limiter.allow("1.2.3.4") is False

    time.sleep(1.1)

    assert limiter.allow("1.2.3.4") is True
