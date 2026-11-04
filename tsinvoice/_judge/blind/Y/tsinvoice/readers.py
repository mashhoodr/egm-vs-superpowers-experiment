"""File reading and row validation (Reading any CSV file, Stages 2 and 3)."""

from __future__ import annotations

import csv
import io
import re
import sys
from datetime import datetime, timedelta
from decimal import Decimal

from tsinvoice.model import Entry, FatalError, Rule, normalise

SENTINEL = "__TSINVOICE_EOF__"
UNTERMINATED = "unterminated quoted field"

FORMAT_A = ["client", "description", "start", "end"]
FORMAT_B = ["client", "task", "start_iso", "duration_minutes"]
RATES_HEADER = ["pattern", "hourly_rate"]

_RATE_RE = re.compile(r"^[0-9]+(\.[0-9]+)?$")
_DURATION_RE = re.compile(r"[0-9]+(\.0+)?")
_START_ISO_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}")

Record = tuple[int, list[str], bool]


def _is_blank(cells: list[str]) -> bool:
    return all(not c.strip() for c in cells)


def _read_records(path: str) -> tuple[list[str] | None, list[Record]]:
    """Read a CSV file into (header_cells, data records).

    Each record is (start_line, cells, unterminated). Blank records are
    dropped unless unterminated. header_cells is None when there is no
    non-blank record or the header itself is unterminated.
    """
    csv.field_size_limit(min(sys.maxsize, 2**31 - 1))
    try:
        with open(path, encoding="utf-8-sig", newline="") as fh:
            text = fh.read()
    except (OSError, UnicodeError) as e:
        raise FatalError(f"{path}: cannot read: {e}") from e

    reader = csv.reader(io.StringIO(text + "\n" + SENTINEL, newline=""))
    raw: list[tuple[int, list[str]]] = []
    try:
        while True:
            start = reader.line_num + 1
            try:
                cells = next(reader)
            except StopIteration:
                break
            raw.append((start, cells))
    except csv.Error as e:
        raise FatalError(f"{path}: cannot read: {e}") from e

    records: list[Record] = []
    last_cells = raw[-1][1] if raw else None
    if last_cells == [SENTINEL]:
        raw.pop()
        unterminated_at = None
    else:
        # The sentinel was swallowed into an open quoted field.
        start, cells = raw[-1]
        suffix = "\n" + SENTINEL
        if cells and cells[-1].endswith(suffix):
            cells = cells[:-1] + [cells[-1][: -len(suffix)]]
        raw[-1] = (start, cells)
        unterminated_at = len(raw) - 1

    for i, (start, cells) in enumerate(raw):
        unterminated = i == unterminated_at
        if not unterminated and _is_blank(cells):
            continue
        records.append((start, cells, unterminated))

    if not records:
        return None, []
    _, header, header_unterminated = records[0]
    if header_unterminated:
        return None, []
    return header, records[1:]


def _header_key(cells: list[str]) -> list[str]:
    key = [c.strip().lower() for c in cells]
    while key and not key[-1]:
        key.pop()
    return key


def _count_error(cells: list[str], n: int) -> str | None:
    if len(cells) == n or (len(cells) > n and _is_blank(cells[n:])):
        return None
    return f"expected {n} fields, got {len(cells)}"


def read_rates(path: str) -> list[Rule]:
    """Stage 2: read the rates file; any problem is fatal."""
    header, records = _read_records(path)
    if header is None or _header_key(header) != RATES_HEADER:
        raise FatalError(f"{path}: unrecognised rates header")
    rules: list[Rule] = []
    for line, cells, unterminated in records:
        prefix = f"{path}:{line}: invalid rates row: "
        if unterminated:
            raise FatalError(prefix + UNTERMINATED)
        err = _count_error(cells, 2)
        if err:
            raise FatalError(prefix + err)
        pattern = normalise(cells[0])
        if not pattern:
            raise FatalError(prefix + "empty pattern")
        rate = cells[1].strip()
        if not _RATE_RE.fullmatch(rate):
            raise FatalError(prefix + "invalid hourly_rate")
        rules.append(Rule(pattern_key=pattern, rate=Decimal(rate)))
    return rules


def _parse_a(start_s: str, end_s: str) -> tuple[datetime, datetime] | str:
    fmt = "%d/%m/%Y %H:%M"
    start_s, end_s = start_s.strip(), end_s.strip()
    try:
        start = datetime.strptime(start_s, fmt)
    except ValueError:
        return "invalid start"
    if not end_s:
        return "blank end"
    try:
        end = datetime.strptime(end_s, fmt)
    except ValueError:
        return "invalid end"
    if end <= start:
        return "end is not after start"
    return start, end


def _parse_b(start_s: str, dur_s: str) -> tuple[datetime, datetime] | str:
    start_s, dur_s = start_s.strip(), dur_s.strip()
    if not _START_ISO_RE.match(start_s):
        return "invalid start_iso"
    try:
        start = datetime.fromisoformat(start_s)
    except ValueError:
        return "invalid start_iso"
    start = start.replace(tzinfo=None, second=0, microsecond=0)
    if not _DURATION_RE.fullmatch(dur_s):
        return "invalid duration_minutes"
    try:
        minutes = int(dur_s.split(".")[0])
        if minutes <= 0:
            return "invalid duration_minutes"
        end = start + timedelta(minutes=minutes)
    except (OverflowError, ValueError):
        return "invalid duration_minutes"
    return start, end


def read_export(
    path: str, tracker: str, arg_index: int
) -> tuple[list[Entry], list[str]]:
    """Stage 3: read one export into entries and bad-row warning lines."""
    header, records = _read_records(path)
    key = _header_key(header) if header is not None else None
    if key == FORMAT_A:
        parse = _parse_a
    elif key == FORMAT_B:
        parse = _parse_b
    else:
        raise FatalError(f"{path}: unrecognised header")

    entries: list[Entry] = []
    warnings: list[str] = []
    for line, cells, unterminated in records:
        if unterminated:
            reason = UNTERMINATED
        else:
            reason = _count_error(cells, 4)
        if reason is None:
            client = cells[0].strip()
            if not client:
                reason = "blank client"
            else:
                result = parse(cells[2], cells[3])
                if isinstance(result, str):
                    reason = result
        if reason is not None:
            warnings.append(f"tsinvoice: warning: {path}:{line}: {reason}")
            continue
        start, end = result
        description = cells[1].strip()
        entries.append(
            Entry(
                tracker=tracker,
                order=(arg_index, line),
                path=path,
                line=line,
                client=client,
                description=description,
                client_key=normalise(client),
                desc_key=normalise(description),
                start=start,
                end=end,
                minutes=int((end - start).total_seconds()) // 60,
            )
        )
    return entries, warnings
