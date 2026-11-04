"""Shared types, constants and pure helpers."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime

CASE_SIZE = 12
MOVE_WINDOW_MINUTES = 120
MOVE_CATEGORY = "Move"
UNCATEGORISED = "Uncategorised"
OUTPUT_HEADER = ["location", "sku", "qty_each", "category", "move_id"]


@dataclass(frozen=True)
class Scan:
    location: str
    arg_index: int
    record_no: int
    path: str
    line: int
    minute: datetime
    sku: str
    sku_norm: str
    qty_each: int

    @property
    def ident(self) -> tuple[int, int]:
        return (self.arg_index, self.record_no)


def normalise_sku(text: str) -> str:
    return text.strip().lower().lstrip("0") or "0"


def scan_key(s: Scan) -> tuple:
    return (s.location, s.minute, s.qty_each, s.sku_norm)


def input_order(s: Scan) -> tuple[int, int]:
    return (s.arg_index, s.record_no)


def scan_order(s: Scan) -> tuple:
    return (s.minute, s.location, s.arg_index, s.record_no)


def output_order(s: Scan) -> tuple:
    return (s.location, s.sku_norm, s.minute, s.arg_index, s.record_no)


class StockmergeError(Exception):
    """A fatal error; the CLI prints it and exits 2."""


class Warnings:
    """The only code that prints warnings."""

    def __init__(self, stream=None):
        self._stream = stream
        self.messages: list[str] = []

    def add(self, path: str | None, line: int | None, reason: str) -> None:
        if path is None:
            text = reason
        elif line is None:
            text = f"{path}: {reason}"
        else:
            text = f"{path}:{line}: {reason}"
        stream = self._stream if self._stream is not None else sys.stderr
        stream.write(f"stockmerge: warning: {text}\n")
        stream.flush()
        self.messages.append(text)
