"""Core logic: parse exports, deduplicate, link moves, categorise."""
from __future__ import annotations

import csv
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta

CASE_SIZE = 12
MOVE_WINDOW = timedelta(hours=2)
UNCATEGORISED = "Uncategorised"
OUTPUT_HEADER = ["location", "sku", "qty_each", "category", "move_id"]

HEADER_A = ["scanned at", "sku", "qty", "unit"]
HEADER_B = ["timestamp", "barcode", "count", "note"]
RULES_HEADER = ["pattern", "category"]

_INT_RE = re.compile(r"^[+-]?\d+$")


class InputError(Exception):
    """Fatal input problem (bad header, missing file). Exit code 2."""


@dataclass
class Scan:
    location: str
    sku: str  # as scanned, outer spaces trimmed
    norm_sku: str
    ts: datetime  # truncated to the minute
    qty_each: int
    file_index: int  # position of the --location argument
    line: int
    category: str = UNCATEGORISED
    move_id: str = ""

    @property
    def seq(self) -> tuple[int, int]:
        return (self.file_index, self.line)

    @property
    def scan_order(self) -> tuple:
        return (self.ts, self.location, self.seq)


def normalise_sku(raw: str) -> str:
    """Trim, upper-case, strip leading zeros. All-zero SKUs become '0'."""
    s = raw.strip().upper()
    stripped = s.lstrip("0")
    if not stripped and s:
        return "0"
    return stripped


def _warn(path: str, line: int, msg: str) -> None:
    print(f"warning: {path}:{line}: {msg}", file=sys.stderr)


def _norm_header(row: list[str]) -> list[str]:
    return [c.strip().lower() for c in row]


def _parse_int(text: str) -> int:
    t = text.strip()
    if not _INT_RE.match(t):
        raise ValueError(f"not a whole number: {text!r}")
    return int(t)


def _parse_a(row: list[str]) -> tuple[str, datetime, int]:
    ts_text, sku, qty_text, unit = row
    ts = datetime.strptime(ts_text.strip(), "%d/%m/%Y %H:%M")
    qty = _parse_int(qty_text)
    u = unit.strip().lower()
    if u == "each":
        mult = 1
    elif u == "case":
        mult = CASE_SIZE
    else:
        raise ValueError(f"unknown unit: {unit!r}")
    return sku, ts, qty * mult


def _parse_b(row: list[str]) -> tuple[str, datetime, int]:
    ts_text, sku, count_text, _note = row
    ts = datetime.fromisoformat(ts_text.strip())
    ts = ts.replace(tzinfo=None, second=0, microsecond=0)
    return sku, ts, _parse_int(count_text)


def read_export(location: str, path: str, file_index: int) -> list[Scan]:
    try:
        fh = open(path, newline="", encoding="utf-8-sig")
    except OSError as exc:
        raise InputError(f"cannot read {path}: {exc}") from exc
    with fh:
        reader = csv.reader(fh)
        header = next(reader, None)
        if header is None:
            raise InputError(f"{path}: empty file, no header row")
        h = _norm_header(header)
        if h == HEADER_A:
            parse = _parse_a
        elif h == HEADER_B:
            parse = _parse_b
        else:
            raise InputError(f"{path}: unrecognised header {header!r}")
        scans: list[Scan] = []
        for row in reader:
            line = reader.line_num
            if not row or all(not c.strip() for c in row):
                _warn(path, line, "empty line skipped")
                continue
            if parse is _parse_b and len(row) > 4:
                # unquoted commas in the free-text note; the note is ignored
                row = row[:3] + [",".join(row[3:])]
            if len(row) != 4:
                _warn(path, line, f"expected 4 fields, got {len(row)}; skipped")
                continue
            try:
                sku, ts, qty = parse(row)
            except ValueError as exc:
                _warn(path, line, f"{exc}; skipped")
                continue
            sku = sku.strip()
            if not sku:
                _warn(path, line, "blank SKU; skipped")
                continue
            scans.append(Scan(location, sku, normalise_sku(sku), ts, qty, file_index, line))
        return scans


def read_rules(path: str) -> list[tuple[str, str]]:
    try:
        fh = open(path, newline="", encoding="utf-8-sig")
    except OSError as exc:
        raise InputError(f"cannot read rules {path}: {exc}") from exc
    with fh:
        reader = csv.reader(fh)
        header = next(reader, None)
        if header is None or _norm_header(header) != RULES_HEADER:
            raise InputError(f"{path}: rules header must be 'pattern,category'")
        rules = []
        for row in reader:
            line = reader.line_num
            if not row or all(not c.strip() for c in row):
                continue
            if len(row) != 2 or not row[0].strip():
                _warn(path, line, "malformed rule skipped")
                continue
            rules.append((row[0].strip(), row[1].strip()))
        return rules


def deduplicate(files: list[list[Scan]]) -> list[Scan]:
    """Collapse overlapping exports of the same location.

    Key = (location, minute timestamp, normalised SKU, qty_each). Within one
    file, repeats are real scans. Across files of one location, the k-th copy
    in each file is the same scan, so the kept count is the max per file.
    The representative of the k-th copy is taken from the earliest file (in
    --location order) that has at least k copies.
    """
    # key -> file_index -> [scans in line order]
    groups: dict[tuple, dict[int, list[Scan]]] = defaultdict(lambda: defaultdict(list))
    for scans in files:
        for s in scans:
            groups[(s.location, s.ts, s.norm_sku, s.qty_each)][s.file_index].append(s)
    kept: list[Scan] = []
    for per_file in groups.values():
        ordered = [per_file[i] for i in sorted(per_file)]
        depth = max(len(lst) for lst in ordered)
        for k in range(depth):
            for lst in ordered:
                if len(lst) > k:
                    kept.append(lst[k])
                    break
    return kept


def link_moves(scans: list[Scan]) -> None:
    """Pair each negative scan with the best opposite positive elsewhere."""
    ordered = sorted(scans, key=lambda s: s.scan_order)
    positives: dict[tuple[str, int], list[Scan]] = defaultdict(list)
    for s in ordered:
        if s.qty_each > 0:
            positives[(s.norm_sku, s.qty_each)].append(s)
    used: set[int] = set()
    n = 0
    for neg in ordered:
        if neg.qty_each >= 0:
            continue
        best = None
        best_key = None
        for pos in positives.get((neg.norm_sku, -neg.qty_each), ()):
            if id(pos) in used or pos.location == neg.location:
                continue
            gap = abs(pos.ts - neg.ts)
            if gap > MOVE_WINDOW:
                continue
            key = (gap, pos.scan_order)
            if best_key is None or key < best_key:
                best, best_key = pos, key
        if best is not None:
            n += 1
            move_id = f"M{n:04d}"
            neg.move_id = best.move_id = move_id
            used.add(id(best))


def categorise(scans: list[Scan], rules: list[tuple[str, str]]) -> None:
    """First rule whose pattern is a case-insensitive substring of the
    normalised SKU wins; patterns are normalised the same way (trim, upper)."""
    lowered = [(p.strip().upper(), c) for p, c in rules]
    for s in scans:
        s.category = UNCATEGORISED
        for pat, cat in lowered:
            if pat in s.norm_sku:
                s.category = cat
                break


def merge(locations: list[tuple[str, str]], rules_path: str) -> list[Scan]:
    rules = read_rules(rules_path)
    files = [read_export(name, path, i) for i, (name, path) in enumerate(locations)]
    scans = deduplicate(files)
    link_moves(scans)
    categorise(scans, rules)
    scans.sort(key=lambda s: (s.location, s.norm_sku, s.ts, s.seq))
    return scans


def write_output(scans: list[Scan], out_path: str) -> None:
    import os
    import tempfile

    directory = os.path.dirname(os.path.abspath(out_path))
    fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(OUTPUT_HEADER)
            for s in scans:
                w.writerow([s.location, s.sku, s.qty_each, s.category, s.move_id])
        os.replace(tmp, out_path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
