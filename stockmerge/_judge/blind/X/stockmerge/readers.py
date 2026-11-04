"""Read one scanner export (Format A or B) into Scan records."""
from __future__ import annotations

import csv
import re
from datetime import datetime
from typing import Callable

from stockmerge.model import CASE_SIZE, FatalError, Scan, sku_key

Warn = Callable[[str], None]

HEADER_A = ["scanned at", "sku", "qty", "unit"]
HEADER_B = ["timestamp", "barcode", "count", "note"]
WHOLE_NUMBER = re.compile(r"[+-]?[0-9]+")
UNITS = {"each": 1, "case": CASE_SIZE}


class BadRow(ValueError):
    """A data row that is skipped with a warning."""


def read_text(path: str) -> str:
    try:
        with open(path, encoding="utf-8-sig", newline="") as handle:
            return handle.read()
    except UnicodeDecodeError:
        raise FatalError(f"{path}: not valid UTF-8 text") from None
    except OSError as exc:
        raise FatalError(f"cannot read {path}: {exc.strerror}") from None


def strip_empty_tail(fields: list[str], width: int) -> list[str]:
    while len(fields) > width and not fields[-1].strip():
        fields = fields[:-1]
    return fields


def _whole(text: str) -> int:
    if not WHOLE_NUMBER.fullmatch(text):
        raise BadRow(f"quantity {text!r} is not a whole number")
    try:
        return int(text)
    except ValueError:
        raise BadRow("quantity is too long") from None


def _sku(text: str) -> str:
    if not text:
        raise BadRow("blank SKU")
    return text


def _parse_a(fields: list[str]) -> tuple[str, datetime, int]:
    stamp, sku, qty, unit = fields
    try:
        minute = datetime.strptime(stamp, "%d/%m/%Y %H:%M")
    except ValueError:
        raise BadRow(f"timestamp {stamp!r} is not DD/MM/YYYY HH:MM") from None
    sku = _sku(sku)
    quantity = _whole(qty)
    multiplier = UNITS.get(unit.casefold())
    if multiplier is None:
        raise BadRow(f"unknown unit {unit!r}")
    return sku, minute, quantity * multiplier


def _parse_b(fields: list[str]) -> tuple[str, datetime, int]:
    stamp, sku, count, _note = fields
    try:
        if "T" not in stamp:
            raise ValueError
        moment = datetime.fromisoformat(stamp)
    except ValueError:
        raise BadRow(f"timestamp {stamp!r} is not ISO 8601 date and time") from None
    minute = moment.replace(tzinfo=None, second=0, microsecond=0)
    return _sku(sku), minute, _whole(count)


def split_lines(text: str) -> list[str]:
    """Split on CR, LF or CRLF only, so U+2028, form feeds etc. stay inside a field."""
    lines = re.split(r"\r\n|\r|\n", text)
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def split_line(text: str) -> list[str]:
    """Parse one physical line as its own CSV record, so a stray quote stays on its line.

    Raises csv.Error when the line cannot be parsed (e.g. a field over the size limit).
    """
    return next(csv.reader([text]), [])


def read_export(path: str, location: str, export_index: int, warn: Warn) -> list[Scan]:
    lines = list(enumerate(split_lines(read_text(path)), start=1))
    header = None
    start = len(lines)
    for position, (_, text) in enumerate(lines):
        try:
            fields = split_line(text)
        except csv.Error:
            break
        if any(f.strip() for f in fields):
            header = [f.strip().casefold() for f in strip_empty_tail(fields, 4)]
            start = position + 1
            break
    if header == HEADER_A:
        parse = _parse_a
    elif header == HEADER_B:
        parse = _parse_b
    else:
        raise FatalError(f"{path}: header matches neither scanner format")

    scans: list[Scan] = []
    for line, text in lines[start:]:
        try:
            fields = split_line(text)
            if not any(f.strip() for f in fields):
                continue
            fields = [f.strip() for f in strip_empty_tail(fields, 4)]
            if len(fields) != 4:
                raise BadRow(f"expected 4 fields, got {len(fields)}")
            sku, minute, qty = parse(fields)
        except csv.Error as exc:
            warn(f"warning: {path}:{line}: unreadable row ({exc})")
            continue
        except BadRow as exc:
            warn(f"warning: {path}:{line}: {exc}")
            continue
        scans.append(Scan(location=location, export_index=export_index, line=line,
                          sku_text=sku, sku_key=sku_key(sku), minute=minute, qty_each=qty))
    return scans
