# stockmerge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A stdlib-only Python CLI, `python -m stockmerge merge`, that merges overlapping stock-take scanner exports into one de-duplicated, move-linked, categorised inventory CSV.

**Architecture:** A pipeline of small pure modules over a frozen `Scan` dataclass: readers → dedupe → moves → writer, with rules used by the writer for categories. The CLI wires them together and turns `FatalError` into exit code 2. Warnings are passed in as a callable so every module is testable without capturing stderr.

**Tech Stack:** Python 3.11+ standard library (`csv`, `argparse`, `datetime`, `dataclasses`, `tempfile`); pytest for tests.

**Spec:** `docs/superpowers/specs/2026-11-03-stockmerge-design.md` (answers behind it: `stakeholder_log.md`). Read both before starting any task.

## Global Constraints

- Python 3.11+, standard library only at runtime. `pytest` allowed for tests.
- Package lives in `stockmerge/` at the repo root; runs as `python -m stockmerge merge --location NAME=PATH [--location NAME=PATH ...] --rules RULES.csv --out INVENTORY.csv`.
- Format A header `Scanned At,SKU,Qty,Unit`; `Scanned At` is `DD/MM/YYYY HH:MM`; `Unit` is `each` (1) or `case` (12); `Qty` signed whole number.
- Format B header `timestamp,barcode,count,note`; ISO 8601 timestamp; `count` signed whole number of single items; `note` ignored.
- Rules file header `pattern,category`; pattern is a case-insensitive substring; first match wins; no match → `Uncategorised`.
- Output header exactly `location,sku,qty_each,category,move_id`; one row per kept scan; `move_id` blank unless part of a move.
- Exit code 0 on success (including when bad rows were skipped); 2 on fatal errors, with no output file written.
- Same inputs in the same order → byte-identical output.
- Timestamps compared to the minute everywhere; seconds dropped, never rounded.

## Review Focus

1. Files saved from a spreadsheet on Windows (CRLF line endings, UTF-8 BOM) must parse exactly like plain files — pinned in Task 2 (`test_crlf_and_bom`).
2. A trailing comma on data rows (an empty extra column) must not turn every row into a bad row — pinned in Task 2 (`test_trailing_empty_field_is_tolerated`).
3. A Format B `note` containing a quoted comma must not shift columns — pinned in Task 2 (`test_quoted_note_with_comma`).
4. A file that is not valid UTF-8, or an `--out` path whose directory does not exist, must give exit 2 and a one-line message, not a traceback — pinned in Task 2 (`test_non_utf8_file_is_fatal`) and Task 7 (`test_missing_output_directory_exits_2`).
5. Trailing spaces on a location name (`"shop floor "=...`) must not split one location in two — pinned in Task 7 (`test_location_name_is_trimmed`).

---

## File Structure

| File | Responsibility |
|---|---|
| `pyproject.toml` | pytest config (`pythonpath`, `testpaths`) |
| `stockmerge/__init__.py` | package marker |
| `stockmerge/model.py` | `Scan`, `FatalError`, `sku_key()`, `CASE_SIZE` |
| `stockmerge/readers.py` | read one export file into `Scan`s |
| `stockmerge/rules.py` | load rules, categorise |
| `stockmerge/dedupe.py` | per-location max-count de-duplication |
| `stockmerge/moves.py` | greedy move pairing |
| `stockmerge/writer.py` | sort, render CSV, atomic write |
| `stockmerge/cli.py` | argparse, orchestration, exit codes |
| `stockmerge/__main__.py` | `python -m stockmerge` entry |
| `tests/factories.py` | `make_scan()` helper for unit tests |
| `tests/test_*.py` | one test file per module + `test_cli.py` end to end |

---

### Task 1: Project scaffold and model

**Files:**
- Create: `pyproject.toml`, `stockmerge/__init__.py`, `stockmerge/model.py`, `tests/__init__.py`, `tests/factories.py`
- Test: `tests/test_model.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `CASE_SIZE: int = 12`
  - `class FatalError(Exception)` — stops the run, exit 2.
  - `sku_key(text: str) -> str` — trim, casefold, strip leading zeros; an all-zero SKU becomes `"0"`; blank stays `""`.
  - `@dataclass(frozen=True) class Scan` with fields `location: str, export_index: int, line: int, sku_text: str, sku_key: str, minute: datetime, qty_each: int` and property `input_order -> tuple[int, int]` returning `(export_index, line)`.
  - `tests/factories.make_scan(**overrides) -> Scan`.

- [ ] **Step 1: Write the scaffold files**

`pyproject.toml`:
```toml
[project]
name = "stockmerge"
version = "0.1.0"
requires-python = ">=3.11"

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

`stockmerge/__init__.py`:
```python
"""Merge overlapping stock-take scanner exports into one inventory."""
```

`tests/__init__.py`: empty file.

- [ ] **Step 2: Write the failing test** — `tests/test_model.py`

```python
from datetime import datetime

from stockmerge.model import CASE_SIZE, Scan, sku_key


def test_case_size_is_twelve():
    assert CASE_SIZE == 12


def test_sku_key_trims_casefolds_and_strips_leading_zeros():
    assert sku_key("  00123 ") == "123"
    assert sku_key("AbC-9") == "abc-9"
    assert sku_key("A00") == "a00"


def test_sku_key_all_zeros_is_zero():
    assert sku_key("000") == "0"
    assert sku_key("0") == "0"


def test_sku_key_blank_stays_blank():
    assert sku_key("   ") == ""


def test_scan_input_order():
    s = Scan(location="shop", export_index=2, line=7, sku_text="X",
             sku_key="x", minute=datetime(2026, 3, 5, 14, 30), qty_each=1)
    assert s.input_order == (2, 7)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_model.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'stockmerge.model'`

- [ ] **Step 4: Write minimal implementation** — `stockmerge/model.py`

```python
"""Core data types shared by every stage of the pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

CASE_SIZE = 12


class FatalError(Exception):
    """An error that stops the run with exit code 2 and writes no output."""


def sku_key(text: str) -> str:
    """Normalise a SKU for comparison: trim, casefold, drop leading zeros."""
    trimmed = text.strip().casefold()
    if not trimmed:
        return ""
    return trimmed.lstrip("0") or "0"


@dataclass(frozen=True)
class Scan:
    location: str
    export_index: int
    line: int
    sku_text: str
    sku_key: str
    minute: datetime
    qty_each: int

    @property
    def input_order(self) -> tuple[int, int]:
        return (self.export_index, self.line)
```

`tests/factories.py`:
```python
from datetime import datetime

from stockmerge.model import Scan, sku_key


def make_scan(**overrides) -> Scan:
    fields = dict(location="shop", export_index=0, line=2, sku_text="A1",
                  minute=datetime(2026, 3, 5, 14, 30), qty_each=1)
    fields.update(overrides)
    fields.setdefault("sku_key", sku_key(fields["sku_text"]))
    return Scan(**fields)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_model.py -v`
Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml stockmerge tests
git commit -m "feat: project scaffold and Scan model"
```

---

### Task 2: Readers (Format A and B)

**Files:**
- Create: `stockmerge/readers.py`
- Test: `tests/test_readers.py`

**Interfaces:**
- Consumes: `Scan`, `FatalError`, `sku_key`, `CASE_SIZE` from `stockmerge.model`.
- Produces: `read_export(path: str, location: str, export_index: int, warn: Callable[[str], None]) -> list[Scan]` — scans in file order; `line` is the 1-based physical line of the row (header is line 1). Bad rows are skipped and reported as `warn(f"warning: {path}:{line}: {reason}")`. Raises `FatalError` for an unreadable file, non-UTF-8 content, or a header matching neither format (including an empty file). Also produces `read_text(path: str) -> str` (used by `rules.py`).

- [ ] **Step 1: Write the failing tests** — `tests/test_readers.py`

```python
from datetime import datetime

import pytest

from stockmerge.model import FatalError
from stockmerge.readers import read_export

A_HEADER = "Scanned At,SKU,Qty,Unit\n"
B_HEADER = "timestamp,barcode,count,note\n"


def write(tmp_path, text, name="in.csv", encoding="utf-8"):
    p = tmp_path / name
    p.write_bytes(text.encode(encoding))
    return str(p)


def read(path, warnings=None):
    sink = [] if warnings is None else warnings
    return read_export(path, "shop", 0, sink.append)


def test_format_a_each_and_case(tmp_path):
    path = write(tmp_path, A_HEADER
                 + "05/03/2026 14:30,00123,2,case\n"
                 + "05/03/2026 14:31,ABC,-3,each\n"
                 + "05/03/2026 14:32,ABC,-1,case\n")
    scans = read(path)
    assert [(s.sku_text, s.sku_key, s.qty_each, s.line) for s in scans] == [
        ("00123", "123", 24, 2), ("ABC", "abc", -3, 3), ("ABC", "abc", -12, 4)]
    assert scans[0].minute == datetime(2026, 3, 5, 14, 30)
    assert scans[0].location == "shop" and scans[0].export_index == 0


def test_format_a_unit_case_insensitive_and_trimmed(tmp_path):
    path = write(tmp_path, A_HEADER + "05/03/2026 14:30,X, 2 , CASE \n"
                 + "05/03/2026 14:30,X,1,Each\n")
    assert [s.qty_each for s in read(path)] == [24, 1]


def test_format_b_drops_seconds_and_ignores_note(tmp_path):
    path = write(tmp_path, B_HEADER + "2026-03-05T14:30:59,123,-3,1 case\n")
    [s] = read(path)
    assert s.minute == datetime(2026, 3, 5, 14, 30)
    assert s.qty_each == -3 and s.sku_text == "123"


def test_format_b_fraction_and_offset_accepted(tmp_path):
    path = write(tmp_path, B_HEADER + "2026-03-05T14:30:12.5,A,1,\n"
                 + "2026-03-05T14:30:12+05:00,A,1,\n")
    scans = read(path)
    assert [s.minute for s in scans] == [datetime(2026, 3, 5, 14, 30)] * 2
    assert all(s.minute.tzinfo is None for s in scans)


def test_format_b_date_without_time_is_bad_row(tmp_path):
    warnings = []
    path = write(tmp_path, B_HEADER + "2026-03-05,A,1,\n")
    assert read(path, warnings) == []
    assert len(warnings) == 1


def test_crlf_and_bom(tmp_path):
    path = write(tmp_path, "﻿ Scanned At , sku,QTY,unit\r\n"
                 "05/03/2026 14:30,X,1,each\r\n")
    [s] = read(path)
    assert s.sku_text == "X" and s.qty_each == 1


def test_trailing_empty_field_is_tolerated(tmp_path):
    path = write(tmp_path, "Scanned At,SKU,Qty,Unit,\n05/03/2026 14:30,X,1,each,\n")
    assert len(read(path)) == 1


def test_quoted_note_with_comma(tmp_path):
    path = write(tmp_path, B_HEADER + '2026-03-05T14:30:12,ABC,4,"moved, from back"\n')
    [s] = read(path)
    assert s.qty_each == 4


@pytest.mark.parametrize("row, reason_part", [
    ("05/03/2026 14:30,X,1.5,each", "quantity"),
    ("05/03/2026 14:30,X,1,box", "unit"),
    ("05/03/2026 14:30,  ,1,each", "SKU"),
    ("2026-03-05 14:30,X,1,each", "timestamp"),
    ("05/03/2026 14:30,X,1", "fields"),
])
def test_bad_rows_warn_and_skip(tmp_path, row, reason_part):
    warnings = []
    path = write(tmp_path, A_HEADER + row + "\n" + "05/03/2026 14:30,OK,1,each\n")
    scans = read(path, warnings)
    assert [s.sku_text for s in scans] == ["OK"]
    assert scans[0].line == 3
    assert len(warnings) == 1
    assert warnings[0].startswith(f"warning: {path}:2: ")
    assert reason_part in warnings[0]


def test_blank_lines_skipped_silently(tmp_path):
    warnings = []
    path = write(tmp_path, A_HEADER + "\n05/03/2026 14:30,X,1,each\n\n")
    scans = read(path, warnings)
    assert len(scans) == 1 and scans[0].line == 3 and warnings == []


def test_unknown_header_is_fatal(tmp_path):
    path = write(tmp_path, "date,item,qty\n")
    with pytest.raises(FatalError, match="header"):
        read(path)


def test_empty_file_is_fatal(tmp_path):
    with pytest.raises(FatalError):
        read(write(tmp_path, ""))


def test_missing_file_is_fatal(tmp_path):
    with pytest.raises(FatalError, match="cannot read"):
        read(str(tmp_path / "nope.csv"))


def test_non_utf8_file_is_fatal(tmp_path):
    path = write(tmp_path, B_HEADER + "2026-03-05T14:30:12,A,1,caf\xe9\n",
                 encoding="latin-1")
    with pytest.raises(FatalError, match="UTF-8"):
        read(path)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_readers.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'stockmerge.readers'`

- [ ] **Step 3: Write minimal implementation** — `stockmerge/readers.py`

```python
"""Read one scanner export (Format A or B) into Scan records."""
from __future__ import annotations

import csv
import io
import re
from datetime import datetime
from typing import Callable

from stockmerge.model import CASE_SIZE, FatalError, Scan, sku_key

Warn = Callable[[str], None]

HEADER_A = ["scanned at", "sku", "qty", "unit"]
HEADER_B = ["timestamp", "barcode", "count", "note"]
WHOLE_NUMBER = re.compile(r"[+-]?\d+")
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


def _strip_empty_tail(fields: list[str], width: int) -> list[str]:
    while len(fields) > width and not fields[-1].strip():
        fields = fields[:-1]
    return fields


def _whole(text: str) -> int:
    if not WHOLE_NUMBER.fullmatch(text):
        raise BadRow(f"quantity {text!r} is not a whole number")
    return int(text)


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


def read_export(path: str, location: str, export_index: int, warn: Warn) -> list[Scan]:
    reader = csv.reader(io.StringIO(read_text(path)))
    header = None
    for fields in reader:
        if any(f.strip() for f in fields):
            header = [f.strip().casefold() for f in _strip_empty_tail(fields, 4)]
            break
    if header == HEADER_A:
        parse = _parse_a
    elif header == HEADER_B:
        parse = _parse_b
    else:
        raise FatalError(f"{path}: header matches neither scanner format")

    scans: list[Scan] = []
    for fields in reader:
        line = reader.line_num
        if not any(f.strip() for f in fields):
            continue
        fields = [f.strip() for f in _strip_empty_tail(fields, 4)]
        try:
            if len(fields) != 4:
                raise BadRow(f"expected 4 fields, got {len(fields)}")
            sku, minute, qty = parse(fields)
        except BadRow as exc:
            warn(f"warning: {path}:{line}: {exc}")
            continue
        scans.append(Scan(location=location, export_index=export_index, line=line,
                          sku_text=sku, sku_key=sku_key(sku), minute=minute, qty_each=qty))
    return scans
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_readers.py -v`
Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add stockmerge/readers.py tests/test_readers.py
git commit -m "feat: read Format A and Format B exports"
```

---

### Task 3: Rules

**Files:**
- Create: `stockmerge/rules.py`
- Test: `tests/test_rules.py`

**Interfaces:**
- Consumes: `FatalError` from `stockmerge.model`; `read_text` from `stockmerge.readers`.
- Produces:
  - `UNCATEGORISED = "Uncategorised"`
  - `@dataclass(frozen=True) class Rule: pattern: str; category: str` (pattern already trimmed and casefolded).
  - `load_rules(path: str, warn: Callable[[str], None]) -> list[Rule]` — raises `FatalError` on unreadable file or wrong header; skips blank-pattern, blank-category or wrong-width rows with `warn(f"warning: {path}:{line}: {reason}")`.
  - `categorise(key: str, rules: list[Rule]) -> str` — `key` is a `sku_key`; first rule whose pattern is a substring wins.

- [ ] **Step 1: Write the failing tests** — `tests/test_rules.py`

```python
import pytest

from stockmerge.model import FatalError, sku_key
from stockmerge.rules import UNCATEGORISED, Rule, categorise, load_rules


def write(tmp_path, text):
    p = tmp_path / "rules.csv"
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_load_and_first_match_wins(tmp_path):
    rules = load_rules(write(tmp_path, "pattern,category\nCOLA,Drinks\nco,Other\n"), [].append)
    assert rules == [Rule("cola", "Drinks"), Rule("co", "Other")]
    assert categorise(sku_key("DIET-cola-330"), rules) == "Drinks"
    assert categorise(sku_key("COFFEE"), rules) == "Other"


def test_no_match_is_uncategorised(tmp_path):
    rules = load_rules(write(tmp_path, "pattern,category\nTEA,Hot\n"), [].append)
    assert categorise(sku_key("COLA"), rules) == UNCATEGORISED == "Uncategorised"


def test_matches_normalised_sku(tmp_path):
    rules = load_rules(write(tmp_path, "pattern,category\n123,Cans\n"), [].append)
    assert categorise(sku_key("00123"), rules) == "Cans"


def test_header_tolerates_bom_case_and_spaces(tmp_path):
    rules = load_rules(write(tmp_path, "﻿ Pattern , CATEGORY\r\n x , Y \r\n"), [].append)
    assert rules == [Rule("x", "Y")]


def test_blank_pattern_skipped_with_warning(tmp_path):
    warnings = []
    path = write(tmp_path, "pattern,category\n,Everything\nA,Alpha\n")
    rules = load_rules(path, warnings.append)
    assert rules == [Rule("a", "Alpha")]
    assert warnings and warnings[0].startswith(f"warning: {path}:2: ")


def test_wrong_header_is_fatal(tmp_path):
    with pytest.raises(FatalError, match="header"):
        load_rules(write(tmp_path, "sku,cat\nA,B\n"), [].append)


def test_missing_rules_file_is_fatal(tmp_path):
    with pytest.raises(FatalError):
        load_rules(str(tmp_path / "none.csv"), [].append)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_rules.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'stockmerge.rules'`

- [ ] **Step 3: Write minimal implementation** — `stockmerge/rules.py`

```python
"""Load categorisation rules and apply them to SKUs."""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import Callable

from stockmerge.model import FatalError
from stockmerge.readers import read_text

UNCATEGORISED = "Uncategorised"


@dataclass(frozen=True)
class Rule:
    pattern: str
    category: str


def load_rules(path: str, warn: Callable[[str], None]) -> list[Rule]:
    reader = csv.reader(io.StringIO(read_text(path)))
    header = next(reader, [])
    if [f.strip().casefold() for f in header] != ["pattern", "category"]:
        raise FatalError(f"{path}: rules header must be pattern,category")
    rules: list[Rule] = []
    for fields in reader:
        line = reader.line_num
        if not any(f.strip() for f in fields):
            continue
        if len(fields) != 2:
            warn(f"warning: {path}:{line}: expected 2 fields, got {len(fields)}")
            continue
        pattern, category = (f.strip() for f in fields)
        if not pattern or not category:
            warn(f"warning: {path}:{line}: blank pattern or category")
            continue
        rules.append(Rule(pattern.casefold(), category))
    return rules


def categorise(key: str, rules: list[Rule]) -> str:
    for rule in rules:
        if rule.pattern in key:
            return rule.category
    return UNCATEGORISED
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_rules.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add stockmerge/rules.py tests/test_rules.py
git commit -m "feat: load rules and categorise SKUs"
```

---

### Task 4: De-duplication

**Files:**
- Create: `stockmerge/dedupe.py`
- Test: `tests/test_dedupe.py`

**Interfaces:**
- Consumes: `Scan` from `stockmerge.model`; `make_scan` from `tests.factories`.
- Produces: `dedupe(scans: list[Scan]) -> list[Scan]` — returns kept scans in input order (`input_order`). Duplicate key is `(location, minute, sku_key, qty_each)`; per key keep `max` copies over exports; the k-th kept copy is the k-th occurrence in the first export (lowest `export_index`) with at least k copies.

- [ ] **Step 1: Write the failing tests** — `tests/test_dedupe.py`

```python
from datetime import datetime

from stockmerge.dedupe import dedupe
from tests.factories import make_scan


def test_identical_rows_in_one_export_are_all_kept():
    a = make_scan(line=2)
    b = make_scan(line=3)
    assert dedupe([a, b]) == [a, b]


def test_overlap_across_exports_keeps_first_export():
    first = make_scan(export_index=0, line=2, sku_text="00123")
    second = make_scan(export_index=1, line=2, sku_text="123")
    assert dedupe([first, second]) == [first]


def test_max_count_not_sum_copies_from_first_export_with_that_many():
    e1 = [make_scan(export_index=0, line=n, sku_text="00123") for n in (2, 3)]
    e2 = [make_scan(export_index=1, line=n, sku_text="123") for n in (5, 6, 7)]
    assert dedupe(e1 + e2) == [e1[0], e1[1], e2[2]]


def test_different_locations_never_dedupe():
    a = make_scan(location="shop", export_index=0)
    b = make_scan(location="back", export_index=1)
    assert dedupe([a, b]) == [a, b]


def test_different_minute_or_qty_are_different_scans():
    a = make_scan(export_index=0)
    b = make_scan(export_index=1, minute=datetime(2026, 3, 5, 14, 31))
    c = make_scan(export_index=1, line=3, qty_each=2)
    assert dedupe([a, b, c]) == [a, b, c]


def test_result_is_in_input_order_regardless_of_argument_order():
    late = make_scan(export_index=1, line=2, sku_text="B")
    early = make_scan(export_index=0, line=9, sku_text="A")
    assert dedupe([late, early]) == [early, late]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_dedupe.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'stockmerge.dedupe'`

- [ ] **Step 3: Write minimal implementation** — `stockmerge/dedupe.py`

```python
"""Remove scans duplicated by overlapping exports of the same location."""
from __future__ import annotations

from stockmerge.model import Scan


def dedupe(scans: list[Scan]) -> list[Scan]:
    groups: dict[tuple, dict[int, list[Scan]]] = {}
    for scan in sorted(scans, key=lambda s: s.input_order):
        key = (scan.location, scan.minute, scan.sku_key, scan.qty_each)
        groups.setdefault(key, {}).setdefault(scan.export_index, []).append(scan)

    kept: list[Scan] = []
    for by_export in groups.values():
        exports = sorted(by_export)
        most = max(len(copies) for copies in by_export.values())
        for k in range(most):
            source = next(e for e in exports if len(by_export[e]) > k)
            kept.append(by_export[source][k])
    return sorted(kept, key=lambda s: s.input_order)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_dedupe.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add stockmerge/dedupe.py tests/test_dedupe.py
git commit -m "feat: de-duplicate overlapping exports by max count"
```

---

### Task 5: Move detection

**Files:**
- Create: `stockmerge/moves.py`
- Test: `tests/test_moves.py`

**Interfaces:**
- Consumes: `Scan` from `stockmerge.model`; `make_scan` from `tests.factories`.
- Produces:
  - `WINDOW_MINUTES = 120`
  - `scan_order(scan: Scan) -> tuple` — `(minute, location, export_index, line)`.
  - `link_moves(scans: list[Scan]) -> dict[tuple[int, int], str]` — maps a scan's `input_order` to its move_id (`"M1"`, `"M2"`, … in pairing order). Scans not in a move are absent.

- [ ] **Step 1: Write the failing tests** — `tests/test_moves.py`

```python
from datetime import datetime, timedelta

from stockmerge.moves import link_moves
from tests.factories import make_scan

T0 = datetime(2026, 3, 5, 14, 0)


def scan(location, qty, minutes=0, export_index=0, line=2, sku="A1"):
    return make_scan(location=location, qty_each=qty, minute=T0 + timedelta(minutes=minutes),
                     export_index=export_index, line=line, sku_text=sku)


def test_simple_move_links_both_rows():
    out = scan("shop", -5, export_index=0)
    back = scan("back", 5, minutes=30, export_index=1)
    assert link_moves([out, back]) == {out.input_order: "M1", back.input_order: "M1"}


def test_exactly_two_hours_counts_and_more_does_not():
    neg = scan("shop", -5, export_index=0)
    edge = scan("back", 5, minutes=120, export_index=1)
    assert link_moves([neg, edge]) != {}
    late = scan("back", 5, minutes=121, export_index=1)
    assert link_moves([neg, late]) == {}


def test_positive_before_negative_still_links():
    neg = scan("shop", -5, minutes=60, export_index=0)
    pos = scan("back", 5, minutes=0, export_index=1)
    assert len(link_moves([neg, pos])) == 2


def test_requires_exact_opposite_and_same_sku_and_other_location():
    neg = scan("shop", -5, export_index=0)
    assert link_moves([neg, scan("back", 4, export_index=1)]) == {}
    assert link_moves([neg, scan("back", 5, export_index=1, sku="B2")]) == {}
    assert link_moves([neg, scan("shop", 5, export_index=0, line=3)]) == {}


def test_sku_compared_normalised():
    neg = scan("shop", -12, export_index=0, sku="00123")
    pos = scan("back", 12, export_index=1, sku="123")
    assert len(link_moves([neg, pos])) == 2


def test_closest_partner_wins():
    neg = scan("shop", -5, minutes=60, export_index=0)
    far = scan("back", 5, minutes=0, export_index=1, line=2)
    near = scan("store", 5, minutes=70, export_index=2, line=2)
    moves = link_moves([neg, far, near])
    assert moves == {neg.input_order: "M1", near.input_order: "M1"}


def test_tie_goes_to_earliest_in_scan_order():
    neg = scan("shop", -5, minutes=60, export_index=0)
    before = scan("back", 5, minutes=30, export_index=1)
    after = scan("store", 5, minutes=90, export_index=2)
    assert link_moves([neg, after, before]) == {neg.input_order: "M1", before.input_order: "M1"}


def test_each_row_in_at_most_one_move_and_ids_follow_scan_order():
    n1 = scan("shop", -5, minutes=0, export_index=0, line=2)
    n2 = scan("shop", -5, minutes=10, export_index=0, line=3)
    p1 = scan("back", 5, minutes=5, export_index=1, line=2)
    p2 = scan("back", 5, minutes=100, export_index=1, line=3)
    moves = link_moves([n2, p2, n1, p1])
    assert moves == {n1.input_order: "M1", p1.input_order: "M1",
                     n2.input_order: "M2", p2.input_order: "M2"}


def test_greedy_does_not_search_for_more_moves():
    # n1 (first in scan order) takes p_shared (closest); n2 then has no partner,
    # even though pairing n1 with p_other would have linked both.
    n1 = scan("shop", -5, minutes=0, export_index=0, line=2)
    n2 = scan("shop", -5, minutes=100, export_index=0, line=3)
    p_shared = scan("back", 5, minutes=50, export_index=1, line=2)
    p_other = scan("store", 5, minutes=-60, export_index=2, line=2)
    moves = link_moves([n1, n2, p_shared, p_other])
    assert moves[n1.input_order] == "M1" and moves[p_shared.input_order] == "M1"
    assert n2.input_order not in moves
    assert p_other.input_order not in moves


def test_zero_quantity_never_moves():
    assert link_moves([scan("shop", 0), scan("back", 0, export_index=1)]) == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_moves.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'stockmerge.moves'`

- [ ] **Step 3: Write minimal implementation** — `stockmerge/moves.py`

```python
"""Link a negative scan at one location to the matching positive scan elsewhere."""
from __future__ import annotations

from stockmerge.model import Scan

WINDOW_MINUTES = 120


def scan_order(scan: Scan) -> tuple:
    return (scan.minute, scan.location, scan.export_index, scan.line)


def link_moves(scans: list[Scan]) -> dict[tuple[int, int], str]:
    positives: dict[tuple[str, int], list[Scan]] = {}
    for scan in sorted((s for s in scans if s.qty_each > 0), key=scan_order):
        positives.setdefault((scan.sku_key, scan.qty_each), []).append(scan)

    paired: set[tuple[int, int]] = set()
    moves: dict[tuple[int, int], str] = {}
    for neg in sorted((s for s in scans if s.qty_each < 0), key=scan_order):
        best, best_gap = None, None
        for pos in positives.get((neg.sku_key, -neg.qty_each), []):
            if pos.input_order in paired or pos.location == neg.location:
                continue
            gap = abs(pos.minute - neg.minute).total_seconds() / 60
            if gap > WINDOW_MINUTES:
                continue
            if best_gap is None or gap < best_gap:
                best, best_gap = pos, gap
        if best is not None:
            move_id = f"M{len(moves) // 2 + 1}"
            paired.add(best.input_order)
            moves[neg.input_order] = move_id
            moves[best.input_order] = move_id
    return moves
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_moves.py -v`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add stockmerge/moves.py tests/test_moves.py
git commit -m "feat: link moves between locations with greedy pairing"
```

---

### Task 6: Writer

**Files:**
- Create: `stockmerge/writer.py`
- Test: `tests/test_writer.py`

**Interfaces:**
- Consumes: `Scan`, `FatalError` from `stockmerge.model`; `Rule`, `categorise` from `stockmerge.rules`; `make_scan` from `tests.factories`.
- Produces:
  - `HEADER = ["location", "sku", "qty_each", "category", "move_id"]`
  - `output_order(scan: Scan) -> tuple` — `(location, sku_key, minute, export_index, line)`.
  - `render(scans: list[Scan], rules: list[Rule], moves: dict[tuple[int, int], str]) -> str` — CSV text with `\n` line endings.
  - `write_atomic(path: str, text: str) -> None` — writes via a temp file in the same directory then `os.replace`; raises `FatalError` on `OSError`.

- [ ] **Step 1: Write the failing tests** — `tests/test_writer.py`

```python
from datetime import datetime

import pytest

from stockmerge.model import FatalError
from stockmerge.rules import Rule
from stockmerge.writer import render, write_atomic
from tests.factories import make_scan


def test_header_and_row_format():
    s = make_scan(location="shop", sku_text="00123", qty_each=-24)
    text = render([s], [Rule("123", "Cans")], {s.input_order: "M1"})
    assert text == "location,sku,qty_each,category,move_id\nshop,00123,-24,Cans,M1\n"


def test_blank_move_id_and_uncategorised():
    text = render([make_scan(sku_text="X")], [], {})
    assert text.splitlines()[1] == "shop,X,1,Uncategorised,"


def test_sorted_by_location_sku_key_minute_input_order():
    rows = [
        make_scan(location="shop", sku_text="B", line=2),
        make_scan(location="back", sku_text="Z", line=3),
        make_scan(location="shop", sku_text="a", line=4, minute=datetime(2026, 3, 5, 15, 0)),
        make_scan(location="shop", sku_text="A", line=5, minute=datetime(2026, 3, 5, 9, 0)),
        make_scan(location="shop", sku_text="A", line=1, minute=datetime(2026, 3, 5, 9, 0)),
    ]
    lines = render(rows, [], {}).splitlines()[1:]
    assert [line.split(",")[0:2] for line in lines] == [
        ["back", "Z"], ["shop", "A"], ["shop", "A"], ["shop", "a"], ["shop", "B"]]
    assert render(rows, [], {}) == render(list(reversed(rows)), [], {})


def test_values_with_commas_are_quoted():
    text = render([make_scan(location="shop, front")], [], {})
    assert text.splitlines()[1].startswith('"shop, front",')


def test_write_atomic(tmp_path):
    target = tmp_path / "out.csv"
    write_atomic(str(target), "a\n")
    assert target.read_bytes() == b"a\n"
    assert [p.name for p in tmp_path.iterdir()] == ["out.csv"]


def test_write_atomic_missing_directory_is_fatal(tmp_path):
    with pytest.raises(FatalError, match="cannot write"):
        write_atomic(str(tmp_path / "missing" / "out.csv"), "a\n")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_writer.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'stockmerge.writer'`

- [ ] **Step 3: Write minimal implementation** — `stockmerge/writer.py`

```python
"""Render the merged inventory and write it to disk safely."""
from __future__ import annotations

import csv
import io
import os
import tempfile

from stockmerge.model import FatalError, Scan
from stockmerge.rules import Rule, categorise

HEADER = ["location", "sku", "qty_each", "category", "move_id"]


def output_order(scan: Scan) -> tuple:
    return (scan.location, scan.sku_key, scan.minute, scan.export_index, scan.line)


def render(scans: list[Scan], rules: list[Rule], moves: dict[tuple[int, int], str]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(HEADER)
    for scan in sorted(scans, key=output_order):
        writer.writerow([scan.location, scan.sku_text, scan.qty_each,
                         categorise(scan.sku_key, rules), moves.get(scan.input_order, "")])
    return buffer.getvalue()


def write_atomic(path: str, text: str) -> None:
    directory = os.path.dirname(os.path.abspath(path))
    try:
        fd, temp = tempfile.mkstemp(dir=directory, prefix=".stockmerge-", suffix=".tmp")
    except OSError as exc:
        raise FatalError(f"cannot write {path}: {exc.strerror}") from None
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        os.replace(temp, path)
    except OSError as exc:
        if os.path.exists(temp):
            os.unlink(temp)
        raise FatalError(f"cannot write {path}: {exc.strerror}") from None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_writer.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add stockmerge/writer.py tests/test_writer.py
git commit -m "feat: render sorted inventory and write atomically"
```

---

### Task 7: CLI and end-to-end tests

**Files:**
- Create: `stockmerge/cli.py`, `stockmerge/__main__.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `FatalError`; `read_export`; `load_rules`; `dedupe`; `link_moves`; `render`, `write_atomic` (signatures as in Tasks 1–6).
- Produces:
  - `parse_location(value: str) -> tuple[str, str]` — split on first `=`, trim NAME; raises `argparse.ArgumentTypeError` if `=` is missing or NAME/PATH is empty.
  - `run_merge(locations: list[tuple[str, str]], rules_path: str, out_path: str, warn: Callable[[str], None]) -> None`.
  - `main(argv: list[str] | None = None) -> int` — 0 on success, 2 on `FatalError` (message `error: ...` on stderr). argparse usage errors exit 2 by themselves.

- [ ] **Step 1: Write the failing tests** — `tests/test_cli.py`

```python
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
A_HEADER = "Scanned At,SKU,Qty,Unit\n"
B_HEADER = "timestamp,barcode,count,note\n"
RULES = "pattern,category\ncola,Drinks\n123,Cans\n"


def run(tmp_path, locations, rules=RULES, out="out.csv"):
    (tmp_path / "rules.csv").write_text(rules, encoding="utf-8")
    args = [sys.executable, "-m", "stockmerge", "merge"]
    for name, filename, content in locations:
        path = tmp_path / filename
        if content is not None:
            path.write_text(content, encoding="utf-8")
        args += ["--location", f"{name}={path}"]
    args += ["--rules", str(tmp_path / "rules.csv"), "--out", str(tmp_path / out)]
    return subprocess.run(args, cwd=REPO, capture_output=True, text=True)


def output(tmp_path, out="out.csv"):
    return (tmp_path / out).read_text(encoding="utf-8")


def test_full_merge(tmp_path):
    shop_a = A_HEADER + ("05/03/2026 14:30,00123,1,case\n"
                         "05/03/2026 14:35,COLA-1,-6,each\n"
                         "05/03/2026 14:40,TEA,2,each\n"
                         "05/03/2026 14:40,TEA,2,each\n")
    shop_b = B_HEADER + ("2026-03-05T14:30:59,123,12,overlap\n"
                         "2026-03-05T14:40:10,TEA,2,\n")
    back_b = B_HEADER + "2026-03-05T15:10:00,cola-1,6,moved in\n"
    result = run(tmp_path, [("shop floor", "a.csv", shop_a),
                            ("shop floor", "b.csv", shop_b),
                            ("back room", "c.csv", back_b)])
    assert result.returncode == 0, result.stderr
    assert output(tmp_path) == (
        "location,sku,qty_each,category,move_id\n"
        "back room,cola-1,6,Drinks,M1\n"
        "shop floor,00123,12,Cans,\n"
        "shop floor,COLA-1,-6,Drinks,M1\n"
        "shop floor,TEA,2,Uncategorised,\n"
        "shop floor,TEA,2,Uncategorised,\n")


def test_repeat_runs_are_byte_identical(tmp_path):
    locs = [("shop", "a.csv", A_HEADER + "05/03/2026 14:30,X,-1,each\n"),
            ("back", "b.csv", B_HEADER + "2026-03-05T14:31:00,X,1,\n")]
    run(tmp_path, locs)
    first = (tmp_path / "out.csv").read_bytes()
    run(tmp_path, locs)
    assert (tmp_path / "out.csv").read_bytes() == first


def test_bad_row_warns_and_exits_0(tmp_path):
    result = run(tmp_path, [("shop", "a.csv", A_HEADER + "bad,X,1,each\n05/03/2026 14:30,Y,1,each\n")])
    assert result.returncode == 0
    assert "a.csv:2:" in result.stderr
    assert output(tmp_path).splitlines()[1:] == ["shop,Y,1,Uncategorised,"]


def test_unknown_header_exits_2_and_writes_nothing(tmp_path):
    result = run(tmp_path, [("shop", "a.csv", "what,is,this\n")])
    assert result.returncode == 2
    assert "error:" in result.stderr
    assert not (tmp_path / "out.csv").exists()


def test_missing_input_exits_2(tmp_path):
    result = run(tmp_path, [("shop", "missing.csv", None)])
    assert result.returncode == 2
    assert "Traceback" not in result.stderr


def test_bad_location_argument_exits_2(tmp_path):
    (tmp_path / "rules.csv").write_text(RULES, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "stockmerge", "merge", "--location", "nopath",
         "--rules", str(tmp_path / "rules.csv"), "--out", str(tmp_path / "o.csv")],
        cwd=REPO, capture_output=True, text=True)
    assert result.returncode == 2


def test_missing_output_directory_exits_2(tmp_path):
    result = run(tmp_path, [("shop", "a.csv", A_HEADER)], out="no/such/out.csv")
    assert result.returncode == 2
    assert "Traceback" not in result.stderr


def test_location_name_is_trimmed(tmp_path):
    result = run(tmp_path, [("shop ", "a.csv", A_HEADER + "05/03/2026 14:30,X,1,each\n"),
                            (" shop", "b.csv", A_HEADER + "05/03/2026 14:30,X,1,each\n")])
    assert result.returncode == 0
    assert output(tmp_path).splitlines()[1:] == ["shop,X,1,Uncategorised,"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_cli.py -v`
Expected: FAIL (non-zero return codes: `No module named stockmerge.__main__`)

- [ ] **Step 3: Write minimal implementation**

`stockmerge/cli.py`:
```python
"""Command-line entry point: python -m stockmerge merge ..."""
from __future__ import annotations

import argparse
import sys
from typing import Callable

from stockmerge.dedupe import dedupe
from stockmerge.model import FatalError
from stockmerge.moves import link_moves
from stockmerge.readers import read_export
from stockmerge.rules import load_rules
from stockmerge.writer import render, write_atomic


def parse_location(value: str) -> tuple[str, str]:
    name, sep, path = value.partition("=")
    name = name.strip()
    if not sep or not name or not path:
        raise argparse.ArgumentTypeError(f"expected NAME=PATH, got {value!r}")
    return name, path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stockmerge")
    commands = parser.add_subparsers(dest="command", required=True)
    merge = commands.add_parser("merge", help="merge scanner exports into one inventory")
    merge.add_argument("--location", action="append", required=True, type=parse_location,
                       metavar="NAME=PATH", help="an export of location NAME (repeatable)")
    merge.add_argument("--rules", required=True, help="CSV with header pattern,category")
    merge.add_argument("--out", required=True, help="output inventory CSV")
    return parser


def run_merge(locations: list[tuple[str, str]], rules_path: str, out_path: str,
              warn: Callable[[str], None]) -> None:
    rules = load_rules(rules_path, warn)
    scans = []
    for index, (name, path) in enumerate(locations):
        scans.extend(read_export(path, name, index, warn))
    kept = dedupe(scans)
    write_atomic(out_path, render(kept, rules, link_moves(kept)))


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        run_merge(args.location, args.rules, args.out,
                  lambda message: print(message, file=sys.stderr))
    except FatalError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0
```

`stockmerge/__main__.py`:
```python
from stockmerge.cli import main

raise SystemExit(main())
```

- [ ] **Step 4: Run all tests to verify they pass**

Run: `python -m pytest -v`
Expected: all passed (Tasks 1–7)

- [ ] **Step 5: Commit**

```bash
git add stockmerge/cli.py stockmerge/__main__.py tests/test_cli.py
git commit -m "feat: merge command wiring and end-to-end tests"
```
