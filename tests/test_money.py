"""Tests for the money helpers."""

from __future__ import annotations

from decimal import Decimal

from app.money import add, format_money, multiply, to_decimal


def test_a_normal_price_is_kept() -> None:
    assert format_money("12.5") == "12.50"
    assert format_money("$1,234.567") == "1234.57"
    assert format_money(Decimal("7")) == "7.00"


def test_junk_is_zero() -> None:
    assert format_money("not a price") == "0.00"
    assert format_money(None) == "0.00"
    assert format_money("") == "0.00"


def test_non_finite_values_are_not_prices() -> None:
    """NaN and Infinity are valid Decimals but they are not prices."""
    for value in ("NaN", "nan", "sNaN", "Infinity", "-Infinity", "inf"):
        assert to_decimal(value) == Decimal("0.00"), value
        assert format_money(value) == "0.00", value


def test_a_non_finite_decimal_is_not_a_price() -> None:
    assert to_decimal(Decimal("NaN")) == Decimal("0.00")
    assert to_decimal(Decimal("Infinity")) == Decimal("0.00")
    assert format_money(Decimal("NaN")) == "0.00"


def test_an_absurd_magnitude_is_junk() -> None:
    """A value that cannot be written as a price is treated as junk."""
    assert format_money("1e999") == "0.00"


def test_arithmetic_stays_exact() -> None:
    assert add("0.10", "0.20") == "0.30"
    assert multiply("19.99", "3") == "59.97"
