"""Reading files and parsing exports (R4.1 to R4.12)."""

from __future__ import annotations

import csv
import re
from datetime import datetime
from typing import TextIO

from stockmerge.model import (
    CASE_SIZE,
    Scan,
    StockmergeError,
    Warnings,
    normalise_sku,
)

FORMAT_A_HEADER = ("Scanned At", "SKU", "Qty", "Unit")
FORMAT_B_HEADER = ("timestamp", "barcode", "count", "note")

ISO_RE = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?"
)
WHOLE_RE = re.compile(r"[+-]?[0-9]{1,9}")

csv.field_size_limit(2**31 - 1)


class RowError(Exception):
    """A row-level problem; its message is the warning reason."""


def open_text(path: str) -> TextIO:
    try:
        return open(path, encoding="utf-8-sig", errors="surrogateescape", newline="")
    except OSError as exc:
        raise StockmergeError(f"{path}: cannot read file: {exc.strerror}") from exc


def _is_blank(fields: list[str]) -> bool:
    return not fields or all(not f.strip() for f in fields)


def iter_records(path: str) -> tuple[list[str], list[tuple[int, list[str]]]]:
    header: list[str] | None = None
    records: list[tuple[int, list[str]]] = []
    f = open_text(path)
    try:
        with f:
            for line_no, line in enumerate(f, start=1):
                fields = next(csv.reader([line]), [])
                if _is_blank(fields):
                    continue
                if header is None:
                    header = [c.strip() for c in fields]
                else:
                    records.append((line_no, fields))
    except OSError as exc:
        raise StockmergeError(f"{path}: cannot read file: {exc.strerror or exc}") from exc
    if header is None:
        raise StockmergeError(f"{path}: no header row")
    return header, records


def has_bad_bytes(fields: list[str]) -> bool:
    return any("\udc80" <= ch <= "\udcff" for field in fields for ch in field)


def to_minute(dt: datetime) -> datetime:
    return dt.replace(second=0, microsecond=0)


def parse_whole(text: str) -> int:
    value = text.strip()
    if not WHOLE_RE.fullmatch(value):
        raise RowError(f"quantity is not a whole number: {text}")
    return int(value)


def parse_iso_naive(text: str) -> datetime:
    value = text.strip()
    if not ISO_RE.fullmatch(value):
        raise RowError(f"bad date: {text}")
    try:
        return datetime.strptime(value[:19], "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        raise RowError(f"bad date: {text}") from None


def parse_a_row(fields: list[str]) -> tuple[datetime, str, int]:
    if len(fields) != 4:
        raise RowError(f"expected 4 fields, found {len(fields)}")
    if has_bad_bytes(fields):
        raise RowError("not valid UTF-8")
    sku = fields[1].strip()
    if not sku:
        raise RowError("blank SKU")
    try:
        when = datetime.strptime(fields[0].strip(), "%d/%m/%Y %H:%M")
    except ValueError:
        raise RowError(f"bad date: {fields[0]}") from None
    qty = parse_whole(fields[2])
    unit = fields[3].strip().lower()
    if unit not in ("each", "case"):
        raise RowError(f"bad unit: {fields[3]}")
    if unit == "case":
        qty *= CASE_SIZE
    return to_minute(when), sku, qty


def parse_b_row(fields: list[str]) -> tuple[datetime, str, int]:
    if len(fields) != 4:
        raise RowError(f"expected 4 fields, found {len(fields)}")
    if has_bad_bytes(fields[:3]):
        raise RowError("not valid UTF-8")
    sku = fields[1].strip()
    if not sku:
        raise RowError("blank SKU")
    when = parse_iso_naive(fields[0])
    qty = parse_whole(fields[2])
    return to_minute(when), sku, qty


PARSERS = {FORMAT_A_HEADER: parse_a_row, FORMAT_B_HEADER: parse_b_row}


def read_export(
    arg_index: int, location: str, path: str, warnings: Warnings
) -> tuple[list[Scan], int, int]:
    header, records = iter_records(path)
    parser = PARSERS.get(tuple(header))
    if parser is None:
        raise StockmergeError(f"{path}: unrecognised header: {','.join(header)}")
    scans: list[Scan] = []
    skipped = 0
    for record_no, (line_no, fields) in enumerate(records):
        try:
            minute, sku, qty = parser(fields)
        except RowError as exc:
            warnings.add(path, line_no, str(exc))
            skipped += 1
            continue
        scans.append(
            Scan(
                location=location,
                arg_index=arg_index,
                record_no=record_no,
                path=path,
                line=line_no,
                minute=minute,
                sku=sku,
                sku_norm=normalise_sku(sku),
                qty_each=qty,
            )
        )
    if not scans:
        warnings.add(path, None, "no valid rows")
    return scans, len(records), skipped
