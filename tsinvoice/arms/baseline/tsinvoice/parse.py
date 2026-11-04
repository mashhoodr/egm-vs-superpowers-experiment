"""Reading tracker exports and the rates file."""
from __future__ import annotations

import csv
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

HEADER_A = ["Client", "Description", "Start", "End"]
HEADER_B = ["client", "task", "start_iso", "duration_minutes"]


class InputError(Exception):
    """Fatal input problem: exit code 2, no output written."""


@dataclass(frozen=True)
class Entry:
    tracker: str
    client: str          # outer-trimmed original text
    description: str     # outer-trimmed original text
    start: datetime      # naive local wall-clock, truncated to the minute
    end: datetime
    order: tuple         # (tracker arg index, line number) for stable ordering

    @property
    def minutes(self) -> int:
        return int((self.end - self.start).total_seconds() // 60)


def norm(text: str) -> str:
    """Trim, collapse inner whitespace, ignore case."""
    return re.sub(r"\s+", " ", text.strip()).casefold()


def warn(msg: str) -> None:
    print(f"warning: {msg}", file=sys.stderr)


def _minute(dt: datetime) -> datetime:
    # Seconds are dropped: timestamps are truncated to the whole minute.
    return dt.replace(second=0, microsecond=0)


def _parse_a(value: str) -> datetime:
    return _minute(datetime.strptime(value.strip(), "%d/%m/%Y %H:%M"))


def _parse_iso(value: str) -> datetime:
    text = value.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1]
    dt = datetime.fromisoformat(text)
    # Offsets are dropped, not converted: start_iso is local wall-clock time.
    return _minute(dt.replace(tzinfo=None))


def _whole_minutes(value: str) -> int:
    # Integer-valued decimals such as "30.0" count as whole; "30.5" does not.
    text = value.strip()
    try:
        num = Decimal(text)
    except InvalidOperation:
        raise ValueError(f"duration_minutes {value!r} is not a number")
    if not num.is_finite() or num != num.to_integral_value():
        raise ValueError(f"duration_minutes {value!r} is not a whole number")
    n = int(num)
    if n <= 0:
        raise ValueError(f"duration_minutes {value!r} is not above zero")
    return n


def read_tracker(tracker: str, path: str, index: int) -> list[Entry]:
    try:
        fh = open(path, newline="", encoding="utf-8-sig")
    except OSError as exc:
        raise InputError(f"cannot read {path}: {exc}") from exc
    with fh:
        rows = list(csv.reader(fh))
    if not rows:
        raise InputError(f"{path}: empty file, no header row")
    header = [h.strip() for h in rows[0]]
    if header == HEADER_A:
        fmt = "A"
    elif header == HEADER_B:
        fmt = "B"
    else:
        raise InputError(f"{path}: unknown header {rows[0]!r}")

    entries = []
    for lineno, row in enumerate(rows[1:], start=2):
        if not any(cell.strip() for cell in row):
            continue
        try:
            if len(row) != 4:
                raise ValueError(f"expected 4 fields, got {len(row)}")
            client, desc = row[0].strip(), row[1].strip()
            if not client:
                raise ValueError("client is blank")
            if fmt == "A":
                start = _parse_a(row[2])
                if not row[3].strip():
                    raise ValueError("End is blank")
                end = _parse_a(row[3])
            else:
                start = _parse_iso(row[2])
                end = start + timedelta(minutes=_whole_minutes(row[3]))
            if end <= start:
                raise ValueError("end is not after start")
        except ValueError as exc:
            warn(f"{path}:{lineno}: skipped row: {exc}")
            continue
        entries.append(Entry(tracker, client, desc, start, end, (index, lineno)))
    return entries


@dataclass(frozen=True)
class Rate:
    pattern: str
    rate: Decimal


def read_rates(path: str) -> list[Rate]:
    try:
        fh = open(path, newline="", encoding="utf-8-sig")
    except OSError as exc:
        raise InputError(f"cannot read rates file {path}: {exc}") from exc
    with fh:
        rows = list(csv.reader(fh))
    if not rows or [h.strip() for h in rows[0]] != ["pattern", "hourly_rate"]:
        raise InputError(f"{path}: rates header must be 'pattern,hourly_rate'")
    rates = []
    for lineno, row in enumerate(rows[1:], start=2):
        if not any(cell.strip() for cell in row):
            continue
        try:
            if len(row) != 2:
                raise ValueError(f"expected 2 fields, got {len(row)}")
            pattern = row[0].strip()
            if not pattern:
                raise ValueError("pattern is blank")
            try:
                rate = Decimal(row[1].strip())
            except InvalidOperation:
                raise ValueError(f"hourly_rate {row[1]!r} is not a number")
            if not rate.is_finite() or rate < 0:
                raise ValueError(f"hourly_rate {row[1]!r} is not a valid rate")
        except ValueError as exc:
            warn(f"{path}:{lineno}: skipped rate: {exc}")
            continue
        rates.append(Rate(pattern, rate))
    return rates
