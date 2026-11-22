"""Exact decimal-money helpers.

Amounts are quantized to cents (two decimal places) and stored as integer cents
so sums never pick up binary-float drift.
"""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

CENTS = Decimal("0.01")
CENTS_PER_UNIT = Decimal(100)


class MoneyError(ValueError):
    """Invalid monetary amount."""


def parse_amount(value: str) -> Decimal:
    """Parse a positive amount with at most two decimal places."""
    try:
        amount = Decimal(str(value).strip())
    except InvalidOperation as exc:
        raise MoneyError("Amount must be a valid number") from exc
    if amount.is_nan() or amount.is_infinite():
        raise MoneyError("Amount must be a valid number")
    if amount <= 0:
        raise MoneyError("Amount must be greater than 0")
    quantized = amount.quantize(CENTS, rounding=ROUND_HALF_UP)
    if quantized != amount:
        raise MoneyError("Amount must have at most 2 decimal places")
    return quantized


def decimal_to_cents(amount: Decimal) -> int:
    quantized = amount.quantize(CENTS, rounding=ROUND_HALF_UP)
    return int(quantized * CENTS_PER_UNIT)


def cents_to_decimal(cents: int) -> Decimal:
    return (Decimal(cents) / CENTS_PER_UNIT).quantize(CENTS)


def format_dollars(amount: Decimal) -> str:
    return f"${amount.quantize(CENTS):.2f}"
