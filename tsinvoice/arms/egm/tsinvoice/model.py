"""Shared records and the normalise helper. No I/O."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

_WS = re.compile(r"\s+")


class FatalError(Exception):
    """A fatal (exit 2) problem; the message is one Fatal error messages row."""


def normalise(text: str) -> str:
    """NFC, trim, collapse whitespace, case-fold, NFC again."""
    text = unicodedata.normalize("NFC", text)
    text = _WS.sub(" ", text.strip())
    return unicodedata.normalize("NFC", text.casefold())


@dataclass(frozen=True)
class Entry:
    tracker: str
    order: tuple[int, int]
    path: str
    line: int
    client: str
    description: str
    client_key: str
    desc_key: str
    start: datetime
    end: datetime
    minutes: int

    @property
    def dup_key(self) -> tuple:
        return (self.tracker, self.client_key, self.desc_key, self.start, self.end)


@dataclass(frozen=True)
class Rule:
    pattern_key: str
    rate: Decimal


@dataclass
class Session:
    entries: list[Entry]

    @property
    def first(self) -> Entry:
        return self.entries[0]

    @property
    def start(self) -> datetime:
        return self.entries[0].start

    @property
    def end(self) -> datetime:
        return self.entries[-1].end

    @property
    def worked_minutes(self) -> int:
        return sum(e.minutes for e in self.entries)

    @property
    def billed_minutes(self) -> int:
        return -(-self.worked_minutes // 6) * 6


@dataclass(frozen=True)
class OutputRow:
    date: str
    client: str
    description: str
    minutes: int
    amount: str
    session_id: str
    session: Session
