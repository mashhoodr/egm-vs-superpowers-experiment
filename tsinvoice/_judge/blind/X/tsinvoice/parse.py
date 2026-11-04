"""Read one tracker export (format A or B) into Entry objects."""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Callable

from tsinvoice.csvio import read_csv_rows
from tsinvoice.model import Entry, FatalError

FORMAT_A = ["Client", "Description", "Start", "End"]
FORMAT_B = ["client", "task", "start_iso", "duration_minutes"]
_A_TIME = "%d/%m/%Y %H:%M"

Warn = Callable[[str], None]


class _BadRow(Exception):
    pass


def read_tracker(path: str, tracker: str, arg_index: int, warn: Warn) -> list[Entry]:
    rows = read_csv_rows(path, "tracker", warn)
    if not rows:
        raise FatalError(f"{path}: empty file, expected a header row")

    header = [cell.strip() for cell in rows[0][1]]
    if header == FORMAT_A:
        parse_row = _parse_a
    elif header == FORMAT_B:
        parse_row = _parse_b
    else:
        raise FatalError(f"{path}: unrecognised header {','.join(header)!r}")

    entries = []
    for line, row in rows[1:]:
        if not row:
            continue
        try:
            if len(row) != 4:
                raise _BadRow(f"expected 4 fields, got {len(row)}")
            client, description, start, end, minutes = parse_row([c.strip() for c in row])
            if not client:
                raise _BadRow("empty client")
        except _BadRow as exc:
            warn(f"warning: {path}:{line}: {exc}")
            continue
        entries.append(Entry(tracker, arg_index, line, client, description, start, end, minutes))
    return entries


def _parse_a(cells):
    client, description, start_text, end_text = cells
    start = _strptime(start_text, "Start")
    end = _strptime(end_text, "End")
    if end <= start:
        raise _BadRow("End is not after Start")
    return client, description, start, end, int((end - start).total_seconds() // 60)


def _strptime(text, field):
    try:
        return datetime.strptime(text, _A_TIME)
    except ValueError:
        raise _BadRow(f"cannot parse {field} {text!r}") from None


def _parse_b(cells):
    client, description, start_text, duration_text = cells
    if "T" not in start_text.upper() and " " not in start_text:
        raise _BadRow(f"start_iso {start_text!r} has no time")
    try:
        start = datetime.fromisoformat(start_text).replace(tzinfo=None)
    except ValueError:
        raise _BadRow(f"cannot parse start_iso {start_text!r}") from None
    try:
        duration = Decimal(duration_text)
    except InvalidOperation:
        duration = None
    if (duration is None or not duration.is_finite()
            or duration != duration.to_integral_value() or duration <= 0):
        raise _BadRow(f"duration_minutes {duration_text!r} is not a whole number above zero")
    if duration.adjusted() > 9:
        raise _BadRow(f"duration_minutes {duration_text!r} is out of range")
    minutes = int(duration)
    try:
        end = start + timedelta(minutes=minutes)
    except OverflowError:
        raise _BadRow(f"duration_minutes {duration_text!r} is out of range") from None
    return client, description, start, end, minutes
