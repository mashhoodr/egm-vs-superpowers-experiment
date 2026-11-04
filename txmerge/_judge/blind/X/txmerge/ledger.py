"""Ledger output and the --out overlap check."""

from __future__ import annotations

import csv
import os
from decimal import Decimal

from txmerge.model import OUTPUT_HEADER, TxmergeError, os_reason


def format_amount(amount: Decimal) -> str:
    return f"{amount:.2f}"


def write_ledger(path: str, records) -> None:
    temp = f"{path}.{os.getpid()}.txmerge-tmp"
    try:
        f = open(temp, "x", encoding="utf-8", newline="")
    except OSError as e:
        raise TxmergeError(f"cannot write {path}: {os_reason(e)}") from e
    try:
        with f:
            writer = csv.writer(f, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
            writer.writerow(OUTPUT_HEADER)
            for r in records:
                writer.writerow(
                    (
                        r.date.isoformat(),
                        r.account,
                        r.description,
                        format_amount(r.amount),
                        r.category,
                        r.transfer_id,
                    )
                )
        os.replace(temp, path)
    except BaseException as e:
        try:
            if os.path.lexists(temp):
                os.remove(temp)
        except OSError:
            pass
        if isinstance(e, OSError):
            raise TxmergeError(f"cannot write {path}: {os_reason(e)}") from e
        raise


def check_not_input(out: str, inputs: list[str]) -> None:
    if not os.path.exists(out):
        return
    for p in inputs:
        if not os.path.exists(p):
            continue
        try:
            same = os.path.samefile(out, p)
        except OSError as e:
            raise TxmergeError(f"cannot read {p}: {os_reason(e)}") from e
        if same:
            raise TxmergeError(f"--out {out} is also an input file")
