"""Money helpers.

Prices are stored and transmitted as strings with two decimals. Arithmetic
happens in :class:`decimal.Decimal` so a price never becomes a float.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

TWO_PLACES = Decimal("0.01")
ZERO = Decimal("0.00")

#: A price with more integer digits than this is junk, not a price. It also
#: keeps every value inside the decimal context precision, so quantize can
#: never raise on a value that came from a request body.
MAX_MONEY_INTEGER_DIGITS = 24


def _integer_digits(number: Decimal) -> int:
    """How many digits the integer part of a value has."""
    _, digits, exponent = number.as_tuple()
    if not isinstance(exponent, int):
        return MAX_MONEY_INTEGER_DIGITS + 1
    return max(1, len(digits) + exponent)


def to_decimal(value: object) -> Decimal:
    """Parse a price-like value into a Decimal, treating junk as zero."""
    if isinstance(value, Decimal):
        return value if _is_money(value) else ZERO
    if value is None:
        return ZERO
    text = str(value).strip().replace(",", "").replace(" ", "")
    if text.startswith("$"):
        text = text[1:]
    if not text:
        return ZERO
    try:
        parsed = Decimal(text)
    except (InvalidOperation, ValueError):
        return ZERO
    return parsed if _is_money(parsed) else ZERO


def _is_money(number: Decimal) -> bool:
    """True when a Decimal can be written as a price.

    ``Decimal("NaN")``, ``Decimal("Infinity")`` and ``Decimal("sNaN")`` are
    valid Decimals but they are not prices: the first quantizes to the literal
    string "NaN" and the others raise on quantize.
    """
    if not number.is_finite():
        return False
    return _integer_digits(number) <= MAX_MONEY_INTEGER_DIGITS


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
