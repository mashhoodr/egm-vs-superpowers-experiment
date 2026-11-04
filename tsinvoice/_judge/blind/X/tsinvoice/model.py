"""Core data types shared by every stage of the pipeline."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime

_WHITESPACE = re.compile(r"\s+")


def norm(text: str) -> str:
    """Comparison form: trim ends, collapse whitespace runs, ignore case."""
    return _WHITESPACE.sub(" ", text.strip()).casefold()


class FatalError(Exception):
    """Unrecoverable input problem: the CLI exits 2 and writes no output."""


@dataclass(frozen=True)
class Entry:
    tracker: str
    arg_index: int
    line: int
    client: str
    description: str
    start: datetime
    end: datetime
    minutes: int

    @property
    def order(self) -> tuple[int, int]:
        return (self.arg_index, self.line)


@dataclass
class Session:
    entries: list[Entry]
    session_id: str = ""

    @property
    def first(self) -> Entry:
        return self.entries[0]

    @property
    def client(self) -> str:
        return self.first.client

    @property
    def description(self) -> str:
        return self.first.description

    @property
    def start(self) -> datetime:
        return self.first.start

    @property
    def date(self) -> date:
        return self.first.start.date()

    @property
    def raw_minutes(self) -> int:
        return sum(e.minutes for e in self.entries)

    @property
    def minutes(self) -> int:
        return -(-self.raw_minutes // 6) * 6
