"""Shared types and helpers (design: Row record, D1, Messages)."""

from __future__ import annotations

import datetime
import sys
from dataclasses import dataclass
from decimal import Decimal


class TxmergeError(Exception):
    """A file-level failure (D13). The message is the Messages-table MESSAGE."""


@dataclass(frozen=True)
class Row:
    account: str
    date: datetime.date
    description: str
    amount: Decimal
    arg_index: int
    line_no: int


def normalise(description: str) -> str:
    """D1: trim, collapse inner whitespace runs to one space, casefold."""
    return " ".join(description.split()).casefold()


def row_key(row: Row) -> tuple:
    """D1 same-transaction key."""
    return (row.account, row.date, row.amount, normalise(row.description))


def warn(path: str, line: int, reason: str, what: str = "row") -> None:
    """Print a skipped data row / rule row warning to stderr."""
    print(f"txmerge: warning: {path}:{line}: {reason}; {what} skipped", file=sys.stderr)
