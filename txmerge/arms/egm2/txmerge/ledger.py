"""Ordering and output (D12, D17, D21, D23)."""

from __future__ import annotations

import csv
import os
import shutil
import tempfile
from decimal import Decimal

from .model import Row, TxmergeError

HEADER = ["date", "account", "description", "amount", "category", "transfer_id"]


def sort_rows(rows: list[Row]) -> list[Row]:
    return sorted(rows, key=lambda r: (r.date, r.account, r.arg_index, r.line_no))


def format_amount(amount: Decimal) -> str:
    if amount == 0:
        return "0.00"
    return format(amount, ".2f")


def write_ledger(
    path: str, rows: list[Row], categories: list[str], transfer_ids: list[str]
) -> None:
    tmp = None
    try:
        fd, tmp = tempfile.mkstemp(
            dir=os.path.dirname(os.path.abspath(path)), prefix=".txmerge-", suffix=".tmp"
        )
        with open(fd, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, lineterminator="\n")
            writer.writerow(HEADER)
            for row, category, tid in zip(rows, categories, transfer_ids):
                writer.writerow(
                    [
                        row.date.isoformat(),
                        row.account,
                        row.description,
                        format_amount(row.amount),
                        category,
                        tid,
                    ]
                )
        if os.path.exists(path):
            shutil.copymode(path, tmp)
        os.replace(tmp, path)
        tmp = None
    except OSError as exc:
        raise TxmergeError(f"cannot write {path}: {exc}") from exc
    finally:
        if tmp is not None and os.path.exists(tmp):
            os.remove(tmp)
