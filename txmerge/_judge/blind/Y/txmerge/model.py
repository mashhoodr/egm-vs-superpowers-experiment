"""Core data types shared by every pipeline stage."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


class InputError(Exception):
    """A fatal input problem: the run stops with exit code 2 and writes nothing."""


@dataclass(frozen=True)
class Transaction:
    account: str
    date: date
    amount: Decimal          # signed: outflow negative
    description: str         # outer whitespace trimmed, case preserved
    source: tuple[int, int]  # (index of --account argument, line number in file)


@dataclass(frozen=True)
class LedgerEntry:
    txn: Transaction
    category: str
    transfer_id: str
