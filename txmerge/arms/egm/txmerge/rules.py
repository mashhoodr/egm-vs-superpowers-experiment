"""Rules loading and categorisation."""

from __future__ import annotations

from typing import Callable

from txmerge.csvio import read_rows
from txmerge.model import UNCATEGORISED, Record, TxmergeError


def load_rules(path: str, warn: Callable[[str], None]) -> list[tuple[str, str]]:
    header, rows = read_rows(path)
    if header is None or header != ["pattern", "category"]:
        raise TxmergeError(f'{path}: rules header must be "pattern,category"')
    rules: list[tuple[str, str]] = []
    for line, cells in rows:
        if len(cells) != 2:
            warn(f"{path}:{line}: expected 2 fields, found {len(cells)}")
            continue
        pattern, category = cells[0].strip(), cells[1].strip()
        if not pattern:
            warn(f"{path}:{line}: blank pattern")
            continue
        if not category:
            warn(f"{path}:{line}: blank category")
            continue
        rules.append((pattern.casefold(), category))
    return rules


def categorise(records: list[Record], rules: list[tuple[str, str]]) -> None:
    for record in records:
        if record.transfer_id:
            continue
        text = record.description.casefold()
        record.category = next(
            (category for pattern, category in rules if pattern in text), UNCATEGORISED
        )
