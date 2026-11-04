"""Export parsing (D5, D13-D19)."""

from __future__ import annotations

import csv
import datetime
import re
from decimal import Decimal, InvalidOperation

from .model import Row, TxmergeError, warn

FORMAT_A = ["Date", "Description", "Debit", "Credit", "Balance"]
FORMAT_B = ["Transaction Date", "Posting Date", "Details", "Amount"]

DATE_A = "%d/%m/%Y"
DATE_B = "%Y-%m-%d"

_UNSIGNED = r"(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]{1,2})?"
_UNSIGNED_RE = re.compile(_UNSIGNED)
_SIGNED_RE = re.compile(r"[-+]?" + _UNSIGNED)
_CENT = Decimal("0.01")


def parse_date(text: str, fmt: str) -> datetime.date:
    return datetime.datetime.strptime(text.strip(), fmt).date()


def parse_amount(text: str, signed: bool) -> Decimal:
    """D15 amount grammar; raises ValueError on anything it rejects."""
    text = text.strip()
    pattern = _SIGNED_RE if signed else _UNSIGNED_RE
    if not pattern.fullmatch(text):
        raise ValueError(text)
    negative = text.startswith("-")
    digits = text.lstrip("+-").replace(",", "")
    try:
        value = Decimal(digits)
        if negative:
            value = -value
        return value.quantize(_CENT)
    except InvalidOperation as exc:
        raise ValueError(text) from exc


def read_csv(path: str) -> list[tuple[int, list[str]]]:
    """Return (physical line number, cells) for every non-blank row (D16)."""
    result: list[tuple[int, list[str]]] = []
    try:
        with open(path, encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            for cells in reader:
                if all(not c.strip() for c in cells):
                    continue
                result.append((reader.line_num, cells))
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise TxmergeError(f"cannot read {path}: {exc}") from exc
    if not result:
        raise TxmergeError(f"{path}: file is empty")
    return result


def _parse_a(cells: list[str]) -> tuple[datetime.date, str, Decimal]:
    date_text, desc, debit_text, credit_text, _balance = cells
    try:
        date = parse_date(date_text, DATE_A)
    except ValueError:
        raise _RowError(f"bad date '{date_text}'")
    debit = credit = None
    for text, slot in ((debit_text, "debit"), (credit_text, "credit")):
        if text:
            try:
                value = parse_amount(text, signed=False)
            except ValueError:
                raise _RowError(f"bad amount '{text}'")
            if slot == "debit":
                debit = value
            else:
                credit = value
    debit_filled = debit is not None and debit != 0
    credit_filled = credit is not None and credit != 0
    if not debit_filled and not credit_filled:
        raise _RowError("Debit and Credit both blank")
    if debit_filled and credit_filled:
        raise _RowError("Debit and Credit both filled")
    amount = -debit if debit_filled else credit
    return date, desc, amount


def _parse_b(cells: list[str]) -> tuple[datetime.date, str, Decimal]:
    date_text, _posting, desc, amount_text = cells
    try:
        date = parse_date(date_text, DATE_B)
    except ValueError:
        raise _RowError(f"bad date '{date_text}'")
    try:
        amount = parse_amount(amount_text, signed=True)
    except ValueError:
        raise _RowError(f"bad amount '{amount_text}'")
    return date, desc, amount


class _RowError(Exception):
    """Internal: carries the REASON for a skipped row."""


def read_export(path: str, account: str, arg_index: int) -> tuple[list[Row], int]:
    """Parse one export; return (rows in input order, skipped count)."""
    lines = read_csv(path)
    header = [c.strip() for c in lines[0][1]]
    if header == FORMAT_A:
        parse = _parse_a
    elif header == FORMAT_B:
        parse = _parse_b
    else:
        raise TxmergeError(f"{path}: unrecognised header: {','.join(header)}")

    rows: list[Row] = []
    skipped = 0
    for line_no, raw in lines[1:]:
        cells = [c.strip() for c in raw]
        try:
            if len(cells) != len(header):
                raise _RowError(f"expected {len(header)} cells, got {len(cells)}")
            date, desc, amount = parse(cells)
        except _RowError as exc:
            warn(path, line_no, str(exc))
            skipped += 1
            continue
        rows.append(Row(account, date, desc, amount, arg_index, line_no))
    return rows, skipped
