"""Core data types shared by every stage of the pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

CASE_SIZE = 12


class FatalError(Exception):
    """An error that stops the run with exit code 2 and writes no output."""


def sku_key(text: str) -> str:
    """Normalise a SKU for comparison: trim, casefold, drop leading zeros."""
    trimmed = text.strip().casefold()
    if not trimmed:
        return ""
    return trimmed.lstrip("0") or "0"


@dataclass(frozen=True)
class Scan:
    location: str
    export_index: int
    line: int
    sku_text: str
    sku_key: str
    minute: datetime
    qty_each: int

    @property
    def input_order(self) -> tuple[int, int]:
        return (self.export_index, self.line)
