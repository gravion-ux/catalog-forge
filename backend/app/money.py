"""Money helpers.

Prices are stored and transmitted as strings with two decimals. Arithmetic
happens in :class:`decimal.Decimal` so a price never becomes a float.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

TWO_PLACES = Decimal("0.01")
ZERO = Decimal("0.00")


def to_decimal(value: object) -> Decimal:
    """Parse a price-like value into a Decimal, treating junk as zero."""
    if isinstance(value, Decimal):
        return value
    if value is None:
        return ZERO
    text = str(value).strip().replace(",", "").replace(" ", "")
    if text.startswith("$"):
        text = text[1:]
    if not text:
        return ZERO
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return ZERO


def format_money(value: object) -> str:
    """Format a value as a two-decimal price string."""
    return str(to_decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP))


def add(*values: object) -> str:
    total = ZERO
    for value in values:
        total += to_decimal(value)
    return format_money(total)


def multiply(price: object, factor: object) -> str:
    """Multiply a price by a factor and round to two decimals."""
    return format_money(to_decimal(price) * to_decimal(factor))
