"""Read one bank export (Format A or B) into Transactions."""
import csv
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Callable

from txmerge.model import InputError, Transaction

FORMAT_A = ["Date", "Description", "Debit", "Credit", "Balance"]
FORMAT_B = ["Transaction Date", "Posting Date", "Details", "Amount"]


class _BadRow(ValueError):
    pass


_PLAIN_NUMBER = re.compile(r"[+-]?(\d+(\.\d*)?|\.\d+)")


def parse_amount(text: str) -> Decimal:
    cleaned = text.strip().replace(",", "")
    if not _PLAIN_NUMBER.fullmatch(cleaned):
        raise ValueError(f"bad amount {text!r}")
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        raise ValueError(f"bad amount {text!r}") from None
    if not value.is_finite():
        raise ValueError(f"bad amount {text!r}")
    return value


def _parse_date(text: str, fmt: str) -> date:
    try:
        return datetime.strptime(text.strip(), fmt).date()
    except ValueError:
        raise _BadRow(f"bad date {text!r}") from None


def _amount(text: str) -> Decimal:
    try:
        return parse_amount(text)
    except ValueError as exc:
        raise _BadRow(str(exc)) from None


def _non_negative(text: str) -> Decimal:
    value = _amount(text)
    if value < 0:
        raise _BadRow(f"bad amount {text!r}: must be positive")
    return value


def _row_a(row: list[str]) -> tuple[date, Decimal, str]:
    when = _parse_date(row[0], "%d/%m/%Y")
    debit, credit = row[2].strip(), row[3].strip()
    if not debit and not credit:
        raise _BadRow("neither Debit nor Credit set")
    d = _non_negative(debit) if debit else None
    c = _non_negative(credit) if credit else None
    # A column holding zero counts as blank (some banks write 0.00 in the unused one).
    d_set, c_set = bool(d), bool(c)
    if d_set and c_set:
        raise _BadRow("both Debit and Credit set")
    if d_set:
        amount = -d
    elif c_set:
        amount = c
    else:
        amount = Decimal("0.00")
    return when, amount, row[1].strip()


def _row_b(row: list[str]) -> tuple[date, Decimal, str]:
    when = _parse_date(row[0], "%Y-%m-%d")
    return when, _amount(row[3]), row[2].strip()


def read_export(account: str, path: str, arg_index: int,
                warn: Callable[[str], None]) -> list[Transaction]:
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            return _read(fh, account, path, arg_index, warn)
    except OSError as exc:
        raise InputError(f"cannot read {path}: {exc.strerror or exc}") from None
    except UnicodeDecodeError:
        raise InputError(f"cannot read {path}: not UTF-8 text") from None


def _read(fh, account, path, arg_index, warn) -> list[Transaction]:
    # One physical line at a time, strict: a bad quote ruins only its own line.
    lines = enumerate(fh, start=1)
    header = None
    first = next(lines, None)
    if first is not None:
        try:
            header = next(csv.reader([first[1]], strict=True), [])
        except csv.Error as exc:
            raise InputError(f"{path}: unrecognised header ({exc})") from None
    cells = [c.strip() for c in header] if header else []
    if cells == FORMAT_A:
        parse, width = _row_a, len(FORMAT_A)
    elif cells == FORMAT_B:
        parse, width = _row_b, len(FORMAT_B)
    else:
        raise InputError(f"{path}: unrecognised header {header!r}")

    rows: list[Transaction] = []
    for line, text in lines:
        try:
            row = next(csv.reader([text], strict=True), [])
        except csv.Error as exc:
            warn(f"WARNING: {path}:{line}: malformed CSV ({exc})")
            continue
        if not any(cell.strip() for cell in row):
            continue
        try:
            if len(row) != width:
                raise _BadRow(f"expected {width} fields, got {len(row)}")
            when, amount, desc = parse(row)
        except _BadRow as exc:
            warn(f"WARNING: {path}:{line}: {exc}")
            continue
        rows.append(Transaction(account, when, amount, desc, (arg_index, line)))
    return rows
