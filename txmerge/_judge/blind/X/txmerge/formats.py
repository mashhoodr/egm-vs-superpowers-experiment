"""Header detection and row parsing per input format."""

from __future__ import annotations

import decimal
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Callable

from txmerge.csvio import read_rows
from txmerge.model import MalformedRow, Record, TxmergeError

EXPECTED = (
    'expected "Date,Description,Debit,Credit,Balance" or '
    '"Transaction Date,Posting Date,Details,Amount"'
)

_DMY = re.compile(r"([0-9]{1,2})/([0-9]{1,2})/([0-9]{4})")
_YMD = re.compile(r"([0-9]{4})-([0-9]{1,2})-([0-9]{1,2})")
_UNSIGNED = r"([0-9]{1,3}(,[0-9]{3})+|[0-9]+)(\.[0-9]{1,2})?"
_AMOUNT = re.compile(_UNSIGNED)
_SIGNED_AMOUNT = re.compile(r"[+-]?" + _UNSIGNED)
_CENT = Decimal("0.01")


def parse_date_dmy(text: str) -> date:
    t = text.strip()
    m = _DMY.fullmatch(t)
    try:
        if not m:
            raise ValueError
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        raise MalformedRow(f"invalid date '{t}'") from None


def parse_date_ymd(text: str) -> date:
    t = text.strip()
    m = _YMD.fullmatch(t)
    try:
        if not m:
            raise ValueError
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        raise MalformedRow(f"invalid date '{t}'") from None


def parse_amount(text: str, signed: bool) -> Decimal:
    t = text.strip()
    pattern = _SIGNED_AMOUNT if signed else _AMOUNT
    if not pattern.fullmatch(t):
        raise MalformedRow(f"invalid amount '{t}'")
    try:
        value = Decimal(t.replace(",", "")).quantize(_CENT)
    except decimal.InvalidOperation:
        raise MalformedRow(f"invalid amount '{t}'") from None
    if value == 0:
        return Decimal("0.00")
    return value


def parse_a(cells: list[str]) -> tuple[date, str, Decimal]:
    d = parse_date_dmy(cells[0])
    debit, credit = cells[2].strip(), cells[3].strip()
    if debit and credit:
        raise MalformedRow("both Debit and Credit are filled")
    if not debit and not credit:
        raise MalformedRow("neither Debit nor Credit is filled")
    if debit:
        amount = -parse_amount(debit, signed=False)
    else:
        amount = parse_amount(credit, signed=False)
    return d, cells[1].strip(), amount


def parse_b(cells: list[str]) -> tuple[date, str, Decimal]:
    d = parse_date_ymd(cells[0])
    amount = parse_amount(cells[3], signed=True)
    return d, cells[2].strip(), amount


@dataclass(frozen=True)
class Format:
    name: str
    header: tuple[str, ...]
    parse: Callable[[list[str]], tuple[date, str, Decimal]]


FORMATS: tuple[Format, ...] = (
    Format("A", ("Date", "Description", "Debit", "Credit", "Balance"), parse_a),
    Format("B", ("Transaction Date", "Posting Date", "Details", "Amount"), parse_b),
)


def detect(header: list[str] | None, path: str) -> Format:
    if header is None:
        raise TxmergeError(f"{path}: unrecognised header (empty file); {EXPECTED}")
    for fmt in FORMATS:
        if fmt.header == tuple(header):
            return fmt
    found = ",".join(header)
    raise TxmergeError(f'{path}: unrecognised header "{found}"; {EXPECTED}')


def read_export(
    export_index: int, name: str, path: str, warn: Callable[[str], None]
) -> tuple[list[Record], int]:
    header, rows = read_rows(path)
    fmt = detect(header, path)
    records: list[Record] = []
    malformed = 0
    for line, cells in rows:
        if len(cells) != len(fmt.header):
            warn(f"{path}:{line}: expected {len(fmt.header)} fields, found {len(cells)}")
            malformed += 1
            continue
        try:
            d, desc, amount = fmt.parse(cells)
        except MalformedRow as e:
            warn(f"{path}:{line}: {e}")
            malformed += 1
            continue
        records.append(
            Record(
                account=name,
                date=d,
                amount=amount,
                description=desc,
                export_index=export_index,
                line=line,
            )
        )
    return records, malformed
