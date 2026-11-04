"""Shared CSV reading: UTF-8 first, Windows-1252 fallback."""
from __future__ import annotations

import csv
from typing import Callable

from tsinvoice.model import FatalError


def _read(path: str, encoding: str) -> list[tuple[int, list[str]]]:
    with open(path, newline="", encoding=encoding) as fh:
        reader = csv.reader(fh)
        return [(reader.line_num, row) for row in reader]


def read_csv_rows(path: str, kind: str, warn: Callable[[str], None]) -> list[tuple[int, list[str]]]:
    """Return (line number, cells) per record. Fatal if unreadable."""
    try:
        try:
            return _read(path, "utf-8-sig")
        except UnicodeDecodeError:
            rows = _read(path, "cp1252")
            warn(f"warning: {path}: not valid UTF-8, read as Windows-1252")
            return rows
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise FatalError(f"cannot read {kind} file {path}: {exc}") from exc
