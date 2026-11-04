"""Shared types and constants."""

from __future__ import annotations

import datetime
import decimal
from dataclasses import dataclass

TRANSFER_CATEGORY = "Transfer"
UNCATEGORISED = "Uncategorised"
TRANSFER_WINDOW_DAYS = 3
OUTPUT_HEADER = ("date", "account", "description", "amount", "category", "transfer_id")
EXIT_OK = 0
EXIT_ERROR = 2


class TxmergeError(Exception):
    """Fatal user-facing error; message follows ``txmerge: error: ``."""


class MalformedRow(Exception):
    """Raised by row parsers; message is the warning reason."""


def normalise(text: str) -> str:
    return " ".join(text.split()).casefold()


def os_reason(e: OSError) -> str:
    return e.strerror if e.strerror else str(e)


@dataclass
class Record:
    account: str
    date: datetime.date
    amount: decimal.Decimal
    description: str
    export_index: int
    line: int
    category: str = ""
    transfer_id: str = ""

    def dedup_key(self) -> tuple:
        return (self.account, self.date, self.amount, normalise(self.description))

    def sort_key(self) -> tuple:
        return (self.date, self.account, self.export_index, self.line)
