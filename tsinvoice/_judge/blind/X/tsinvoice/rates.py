"""Load the rates file and price sessions."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Callable

from tsinvoice.csvio import read_csv_rows
from tsinvoice.model import FatalError, norm

RATES_HEADER = ["pattern", "hourly_rate"]
_CENT = Decimal("0.01")


@dataclass(frozen=True)
class Rate:
    pattern: str
    hourly_rate: Decimal


def load_rates(path: str, warn: Callable[[str], None]) -> list[Rate]:
    rows = read_csv_rows(path, "rates", warn)
    if not rows or [c.strip() for c in rows[0][1]] != RATES_HEADER:
        raise FatalError(f"{path}: rates header must be {','.join(RATES_HEADER)}")

    rates = []
    for line, row in rows[1:]:
        if not row:
            continue
        if len(row) != 2:
            raise FatalError(f"{path}:{line}: expected 2 fields, got {len(row)}")
        pattern, rate_text = row[0].strip(), row[1].strip()
        try:
            rate = Decimal(rate_text)
        except InvalidOperation:
            rate = None
        if rate is None or not rate.is_finite() or rate < 0:
            raise FatalError(f"{path}:{line}: hourly_rate {rate_text!r} is not a number >= 0")
        if not pattern:
            warn(f"warning: {path}:{line}: empty pattern ignored")
            continue
        rates.append(Rate(pattern, rate + 0))  # +0 turns -0 into 0
    return rates


def find_rate(client: str, description: str, rates: list[Rate]) -> Decimal | None:
    c, d = norm(client), norm(description)
    for r in rates:
        p = norm(r.pattern)
        if p in c or p in d:
            return r.hourly_rate
    return None


def price(minutes: int, hourly_rate: Decimal) -> Decimal:
    return (Decimal(minutes) * hourly_rate / Decimal(60)).quantize(_CENT, rounding=ROUND_HALF_UP)
