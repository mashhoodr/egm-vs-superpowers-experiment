"""Shared CSV reading for exports and the rules file."""

from __future__ import annotations

import csv

from txmerge.model import TxmergeError, os_reason


def read_rows(path: str) -> tuple[list[str] | None, list[tuple[int, list[str]]]]:
    """Return (stripped header or None, [(start_line, cells), ...])."""
    header: list[str] | None = None
    rows: list[tuple[int, list[str]]] = []
    reader = None
    try:
        with open(path, encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f, strict=True)
            while True:
                start = reader.line_num + 1
                try:
                    row = next(reader)
                except StopIteration:
                    break
                if not row or all(not cell.strip() for cell in row):
                    continue
                if header is None:
                    header = [cell.strip() for cell in row]
                else:
                    rows.append((start, row))
    except OSError as e:
        raise TxmergeError(f"cannot read {path}: {os_reason(e)}") from e
    except UnicodeDecodeError as e:
        raise TxmergeError(f"cannot read {path}: {e}") from e
    except csv.Error as e:
        raise TxmergeError(f"cannot read {path}: line {reader.line_num}: {e}") from e
    return header, rows
