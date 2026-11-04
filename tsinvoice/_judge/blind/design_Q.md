# tsinvoice — design spec

Date: 2026-11-03. Source: `BRIEF.md` (fixed contract) + stakeholder answers in
`stakeholder_log.md` (Q1–Q10). Decisions marked **(ours)** were left to us.

## Goal

One CLI, `python -m tsinvoice merge`, that reads time-tracker CSV exports,
removes duplicate entries caused by overlapping exports, joins continued
entries into sessions, prices each session, and writes one deterministic CSV.
Python 3.11+, standard library only at runtime; `pytest` for tests.

## CLI

```
python -m tsinvoice merge --tracker NAME=PATH [--tracker NAME=PATH ...] \
    --rates RATES.csv --out SESSIONS.csv
```

- `--tracker` repeats; one NAME may appear with several PATHs. Each argument
  has an index (0, 1, 2, …) in command-line order: its **arg index**.
- Exit 0 on success (warnings allowed). Exit 2 on any fatal error, with a
  message on stderr and **no output file written** (an existing `--out` file is
  left untouched).

## Entry model

Every parsed row becomes an `Entry`:

| field | meaning |
|---|---|
| `tracker` | NAME from `--tracker` (exact string) |
| `arg_index`, `line` | input position: arg index, then the CSV line number (header is line 1) |
| `client`, `description` | original text, trimmed at both ends |
| `start`, `end` | naive `datetime` (wall clock as written) |
| `minutes` | whole number of minutes, `end - start` |

**Normalised text** (used for every comparison): trim ends, collapse each run of
whitespace to one space, `casefold()`.

**Input order** of an entry: `(arg_index, line)`.

## Parsing (`tsinvoice/parse.py`)

Files are read as `utf-8-sig` (BOM tolerated) with the `csv` module. If a file is
not valid UTF-8 the whole file is re-read as Windows-1252 with the warning
`warning: <path>: not valid UTF-8, read as Windows-1252`; if that also fails the
run is fatal, exit 2 **(ours)**. The same rule applies to the rates file; both
share `tsinvoice/csvio.py`. The header
row's cells are stripped of surrounding spaces **(ours)**, then compared exactly:

- Format A: `Client,Description,Start,End`. Start/End use `%d/%m/%Y %H:%M`.
  `minutes = (end - start)` in whole minutes.
- Format B: `client,task,start_iso,duration_minutes`. `start_iso` is parsed with
  `datetime.fromisoformat`; any offset or `Z` is **dropped, not converted**
  (keep the clock time as written). Seconds are kept **(ours)**. A date-only
  value such as `2026-03-02` (no time part) is a bad row, `start_iso ... has no
  time` **(ours)**.
  `duration_minutes` must parse as a number with no fractional part and be > 0;
  `"30.0"` is accepted as 30 **(ours)**. `end = start + duration`.
- Any other header (or an empty file): fatal, exit 2.

Bad rows are skipped with a stderr warning `warning: <path>:<line>: <reason>`,
and the run continues. A row is bad when: the field count is not 4 **(ours)**;
the client is empty after trimming **(ours)**; a date/time does not parse;
format A End is not after Start; format B `start_iso` has no time; format B
duration is not a whole number > 0 or is absurdly large (10^10 minutes or more) **(ours)**.
Completely blank lines are skipped silently **(ours)**.

## Deduplication (`tsinvoice/dedupe.py`)

Duplicates exist only **within one tracker NAME**. Identity key:
`(tracker, start, end, norm(client), norm(description))`.

- Within one export file, identical entries are all real (kept).
- Across exports of the same tracker, count by **max**, not sum: if export 1
  holds a key 2 times and export 2 holds it 3 times, keep 3.
- Entries from different trackers never deduplicate against each other, and
  overlapping (non-identical) entries are never merged.

Algorithm: walk entries in input order. For each key keep a counter `kept[key]`
and, per file (arg index), `seen[key, arg_index]`. On each entry increment
`seen`; keep the entry iff `seen > kept`, then set `kept = max(kept, seen)`.
This keeps the earliest copies in input order.

## Joining (`tsinvoice/join.py`)

Runs on the deduplicated entries. Q **continues** P when
`norm(client)` and `norm(description)` match and
`0 <= Q.start - P.end <= 2 minutes` (inclusive, measured in seconds: 0–120 s).
Overlapping entries (Q starts before P ends) never join. Tracker does not matter.

Each entry has at most one predecessor and one successor. Greedy, deterministic:

1. Sort entries by `(start, arg_index, line)`.
2. For each P in that order, among entries Q that continue P and have no
   predecessor yet (Q ≠ P), pick the smallest gap, then earliest input order.
   Link P → Q.
3. Sessions are the resulting chains, starting at entries with no predecessor.
   Chains of any length are allowed.

A **session**: `client`/`description` = first entry's trimmed original text;
`date` = first entry's start date (no split at midnight);
`raw_minutes` = sum of entry minutes (gaps are not billed);
`minutes` = `raw_minutes` rounded **up** to the next multiple of 6, once per
session (a lone entry is a session too).

## Pricing (`tsinvoice/rates.py`)

Rates file header `pattern,hourly_rate` (stripped, BOM tolerated). Rows are kept
in file order. A pattern matches a session when `norm(pattern)` is a substring
of `norm(client)` or `norm(description)` — the first entry's text **(ours)**.
The **first** matching row wins.

- No match: amount `0.00`, row still written, warning
  `warning: no rate for client '<client>' description '<description>'`.
- Empty pattern rows are ignored with a warning **(ours)**.
- Fatal (exit 2) **(ours)**: rates file missing/unreadable, wrong header,
  `hourly_rate` not a number or negative.

`amount = Decimal(minutes) / 60 * rate`, quantised to `0.01` with
`ROUND_HALF_UP`. All money arithmetic uses `Decimal`.

## Session id (`tsinvoice/session_id.py`)

Blank for a single-entry session. For a joined session **(ours)**:
`s-` + first 12 hex of SHA-256 over the member entries (in chain order) encoded
as `tracker|start ISO|end ISO|norm(client)|norm(description)` lines. Content-only,
so stable across re-runs. A given chain's id does not depend on `--tracker`
argument order, but reordering can change tie-breaks and therefore which entries
join into a chain **(ours)**. If two sessions
get the same id, the second and later in output order get `-2`, `-3`, ….

## Output (`tsinvoice/output.py`)

Header exactly `date,client,description,minutes,amount,session_id`; `\n` line
endings **(ours)**. Sort sessions by `(norm(client), start, arg_index, line)` of
their first entry. Same inputs in the same order → byte-identical output.
Written only after all inputs are read and processed successfully.

## Fatal errors (exit 2, no output) — `tsinvoice/cli.py`

Unknown/empty header in a tracker file; `--tracker` not `NAME=PATH` or empty
NAME/PATH **(ours)**; tracker file missing/unreadable **(ours)**; rates errors
above. argparse usage errors already exit 2.

## Module layout

```
tsinvoice/__init__.py, __main__.py, cli.py, model.py (Entry, Session, norm),
parse.py, dedupe.py, join.py, rates.py, session_id.py, output.py
tests/  (one test module per source module + end-to-end CLI tests)
```

## Testing

TDD per module with pytest. Unit tests cover every rule above (normalisation,
both formats, every bad-row reason, max-count dedupe, cross-tracker keep,
join gap 0/2/3 minutes and overlap, tie-breaks, chains, rounding to 6, pricing
order/no-match/half-up, id stability and collision suffix, sort order).
End-to-end tests run `python -m tsinvoice merge` via `subprocess` on temp files:
success path, re-run byte-identical, unknown header exit 2 with no output file.

## Out of scope

Time zones, splitting at midnight, currency, invoice documents, merging
overlapping entries.


---

# tsinvoice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use [redacted]:[redacted] (recommended) or [redacted]:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A stdlib-only CLI `python -m tsinvoice merge` that dedupes overlapping timesheet exports, joins continued entries into sessions, prices them, and writes one deterministic CSV.

**Architecture:** A pipeline of small pure modules — parse → dedupe → join → price → ids/output — each with one rule set and its own tests, glued by a thin `cli.py`. Warnings go through a `warn(msg)` callable; unrecoverable problems raise `FatalError`, which the CLI turns into exit 2 with no output file.

**Tech Stack:** Python 3.11+ standard library (`csv`, `datetime`, `decimal`, `hashlib`, `argparse`, `re`); `pytest` for tests.

**Spec:** `docs/[redacted]/specs/2026-11-03-tsinvoice-design.md` (read it with this plan).

## Global Constraints

- Python 3.11+, standard library only at runtime. `pytest` allowed for tests.
- Package lives in `tsinvoice/` at the repo root; runs as `python -m tsinvoice merge --tracker NAME=PATH [--tracker NAME=PATH ...] --rates RATES.csv --out SESSIONS.csv`.
- Format A header `Client,Description,Start,End`, times `DD/MM/YYYY HH:MM`. Format B header `client,task,start_iso,duration_minutes`.
- Rates header `pattern,hourly_rate`.
- Output header exactly `date,client,description,minutes,amount,session_id`; `date` ISO `YYYY-MM-DD`; `minutes` whole number; `amount` 2 decimals; `session_id` blank unless joined.
- Exit 0 on success; exit 2 on fatal errors with no output file written.
- Same inputs in the same order → byte-identical output.
- Normalised text = trim ends, collapse whitespace runs to one space, `casefold()`.
- Warnings go to stderr, one line each, starting `warning: `.

## Review Focus

1. **The same export passed twice for one tracker** (`--tracker d=a.csv --tracker d=a.csv`) — user expects no doubled time. Test: Task 7 `test_same_file_twice_does_not_double`.
2. **Descriptions containing commas, quotes or non-ASCII** — user expects them to round-trip intact in the output CSV. Test: Task 6 `test_write_csv_quotes_commas_and_quotes`.
3. **Case differences beyond ASCII** (`CAFÉ` vs `café`, `STRASSE` vs `straße`) — user expects them treated as the same text. Test: Task 1 `test_norm_unicode_casefold`.
4. **A session that runs across midnight** (23:50–00:00 continued 00:01–00:10) — user expects one session dated on the start day. Test: Task 4 `test_join_across_midnight_keeps_start_date`.
5. **A failed run when `--out` already exists** — user expects the old file left untouched. Test: Task 7 `test_fatal_error_leaves_existing_output_untouched`.

---

### Task 1: Project scaffold and core model

**Files:**
- Create: `pyproject.toml`, `tsinvoice/__init__.py`, `tsinvoice/model.py`, `tests/__init__.py`, `tests/factories.py`
- Test: `tests/test_model.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `norm(text: str) -> str`
  - `class FatalError(Exception)`
  - `@dataclass(frozen=True) class Entry(tracker: str, arg_index: int, line: int, client: str, description: str, start: datetime, end: datetime, minutes: int)` with property `order -> tuple[int, int]` = `(arg_index, line)`
  - `@dataclass class Session(entries: list[Entry], session_id: str = "")` with properties `first: Entry`, `client: str`, `description: str`, `start: datetime`, `date: date`, `raw_minutes: int`, `minutes: int` (raw rounded up to a multiple of 6)
  - `tests/factories.py`: `entry(start: str, minutes: int, client="Acme", description="Design", tracker="desktop", arg_index=0, line=2) -> Entry`

- [ ] **Step 1: Create scaffold files**

`pyproject.toml`:
```toml
[project]
name = "tsinvoice"
version = "0.1.0"
requires-python = ">=3.11"

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

`tsinvoice/__init__.py`:
```python
"""Merge overlapping timesheet exports into invoice-ready sessions."""
```

`tests/__init__.py`: empty file.

`tests/factories.py`:
```python
from datetime import datetime, timedelta

from tsinvoice.model import Entry


def entry(start, minutes, client="Acme", description="Design",
          tracker="desktop", arg_index=0, line=2):
    st = datetime.fromisoformat(start)
    return Entry(tracker=tracker, arg_index=arg_index, line=line,
                 client=client, description=description,
                 start=st, end=st + timedelta(minutes=minutes),
                 minutes=minutes)
```

- [ ] **Step 2: Write the failing tests** — `tests/test_model.py`:
```python
from datetime import date

from tests.factories import entry
from tsinvoice.model import Session, norm


def test_norm_trims_collapses_and_ignores_case():
    assert norm("  Acme   Corp\t Ltd ") == "acme corp ltd"


def test_norm_unicode_casefold():
    assert norm("CAFÉ") == norm("café")
    assert norm("STRASSE") == norm("straße")


def test_entry_order_is_arg_index_then_line():
    assert entry("2026-03-02T09:00", 30, arg_index=1, line=7).order == (1, 7)


def test_session_uses_first_entry_text_and_start():
    s = Session([entry("2026-03-02T09:00", 7, client="Acme ", description="Design"),
                 entry("2026-03-02T09:07", 7, client="ACME", description="design")])
    assert s.client == "Acme "  # Session does not trim; the parser already trims
    assert s.description == "Design"
    assert s.date == date(2026, 3, 2)
    assert s.raw_minutes == 14


def test_session_minutes_round_up_to_multiple_of_six():
    assert Session([entry("2026-03-02T09:00", 14)]).minutes == 18
    assert Session([entry("2026-03-02T09:00", 12)]).minutes == 12
    assert Session([entry("2026-03-02T09:00", 1)]).minutes == 6


def test_session_id_defaults_blank():
    assert Session([entry("2026-03-02T09:00", 30)]).session_id == ""
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_model.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tsinvoice.model'`

- [ ] **Step 4: Implement** — `tsinvoice/model.py`:
```python
"""Core data types shared by every stage of the pipeline."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime

_WHITESPACE = re.compile(r"\s+")


def norm(text: str) -> str:
    """Comparison form: trim ends, collapse whitespace runs, ignore case."""
    return _WHITESPACE.sub(" ", text.strip()).casefold()


class FatalError(Exception):
    """Unrecoverable input problem: the CLI exits 2 and writes no output."""


@dataclass(frozen=True)
class Entry:
    tracker: str
    arg_index: int
    line: int
    client: str
    description: str
    start: datetime
    end: datetime
    minutes: int

    @property
    def order(self) -> tuple[int, int]:
        return (self.arg_index, self.line)


@dataclass
class Session:
    entries: list[Entry]
    session_id: str = ""

    @property
    def first(self) -> Entry:
        return self.entries[0]

    @property
    def client(self) -> str:
        return self.first.client

    @property
    def description(self) -> str:
        return self.first.description

    @property
    def start(self) -> datetime:
        return self.first.start

    @property
    def date(self) -> date:
        return self.first.start.date()

    @property
    def raw_minutes(self) -> int:
        return sum(e.minutes for e in self.entries)

    @property
    def minutes(self) -> int:
        return -(-self.raw_minutes // 6) * 6
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_model.py -v`
Expected: 6 passed

- [ ] **Step 6: Commit**
```bash
git add pyproject.toml tsinvoice tests
git commit -m "feat: project scaffold and core model"
```

---

### Task 2: Parse tracker exports (formats A and B)

**Files:**
- Create: `tsinvoice/parse.py`
- Test: `tests/test_parse.py`

**Interfaces:**
- Consumes: `Entry`, `FatalError` from `tsinvoice.model`.
- Produces: `read_tracker(path: str, tracker: str, arg_index: int, warn: Callable[[str], None]) -> list[Entry]`. Raises `FatalError` for unreadable file, empty file, or unknown header. Bad rows call `warn("warning: <path>:<line>: <reason>")` and are skipped.

- [ ] **Step 1: Write the failing tests** — `tests/test_parse.py`:
```python
from datetime import datetime

import pytest

from tsinvoice.model import FatalError
from tsinvoice.parse import read_tracker


def write(tmp_path, text, name="t.csv", encoding="utf-8"):
    p = tmp_path / name
    p.write_text(text, encoding=encoding)
    return str(p)


def read(path):
    warnings = []
    return read_tracker(path, "desk", 3, warnings.append), warnings


def test_format_a_row(tmp_path):
    p = write(tmp_path, "Client,Description,Start,End\n"
                        " Acme , Design  work ,02/03/2026 09:00,02/03/2026 10:30\n")
    entries, warnings = read(p)
    assert warnings == []
    (e,) = entries
    assert (e.tracker, e.arg_index, e.line) == ("desk", 3, 2)
    assert (e.client, e.description) == ("Acme", "Design  work")
    assert e.start == datetime(2026, 3, 2, 9, 0)
    assert e.end == datetime(2026, 3, 2, 10, 30)
    assert e.minutes == 90


def test_format_b_row_drops_offset_and_keeps_clock_time(tmp_path):
    p = write(tmp_path, "client,task,start_iso,duration_minutes\n"
                        "Acme,Design,2026-03-02T09:00:00Z,30\n"
                        "Acme,Design,2026-03-02T09:00:00+05:00,30.0\n"
                        "Acme,Design,2026-03-02T09:00:30,15\n")
    entries, warnings = read(p)
    assert warnings == []
    assert [e.start for e in entries] == [datetime(2026, 3, 2, 9, 0),
                                          datetime(2026, 3, 2, 9, 0),
                                          datetime(2026, 3, 2, 9, 0, 30)]
    assert all(e.start.tzinfo is None for e in entries)
    assert [e.minutes for e in entries] == [30, 30, 15]
    assert entries[2].end == datetime(2026, 3, 2, 9, 15, 30)


@pytest.mark.parametrize("duration", ["12.5", "0", "-5", "abc", "", "NaN", "inf"])
def test_format_b_bad_duration_is_skipped_with_warning(tmp_path, duration):
    p = write(tmp_path, "client,task,start_iso,duration_minutes\n"
                        f"Acme,Design,2026-03-02T09:00,{duration}\n"
                        "Acme,Design,2026-03-02T10:00,5\n")
    entries, warnings = read(p)
    assert len(entries) == 1
    assert len(warnings) == 1
    assert warnings[0].startswith(f"warning: {p}:2: ")


@pytest.mark.parametrize("row", [
    "Acme,Design,02/03/2026 10:00,02/03/2026 09:00",   # end before start
    "Acme,Design,02/03/2026 10:00,02/03/2026 10:00",   # end equals start
    "Acme,Design,2026-03-02 10:00,02/03/2026 11:00",   # wrong date format
    "Acme,Design,02/03/2026 10:00,",                   # blank end
    "Acme,Design,02/03/2026 10:00",                    # missing field
    "Acme,Design,02/03/2026 10:00,02/03/2026 11:00,x", # extra field
    " ,Design,02/03/2026 10:00,02/03/2026 11:00",      # empty client
])
def test_format_a_bad_rows_are_skipped_with_warning(tmp_path, row):
    p = write(tmp_path, "Client,Description,Start,End\n" + row + "\n")
    entries, warnings = read(p)
    assert entries == []
    assert len(warnings) == 1
    assert warnings[0].startswith(f"warning: {p}:2: ")


def test_format_b_bad_start_is_skipped(tmp_path):
    p = write(tmp_path, "client,task,start_iso,duration_minutes\nAcme,Design,yesterday,30\n")
    entries, warnings = read(p)
    assert entries == [] and len(warnings) == 1


def test_blank_lines_skipped_silently_and_line_numbers_kept(tmp_path):
    p = write(tmp_path, "Client,Description,Start,End\n\n"
                        "Acme,Design,02/03/2026 09:00,02/03/2026 10:00\n")
    entries, warnings = read(p)
    assert warnings == []
    assert entries[0].line == 3


def test_empty_description_is_allowed(tmp_path):
    p = write(tmp_path, "Client,Description,Start,End\nAcme,,02/03/2026 09:00,02/03/2026 10:00\n")
    entries, _ = read(p)
    assert entries[0].description == ""


def test_bom_and_spaced_header_tolerated(tmp_path):
    p = write(tmp_path, " client , task ,start_iso, duration_minutes\nAcme,Design,2026-03-02T09:00,30\n",
              encoding="utf-8-sig")
    entries, warnings = read(p)
    assert len(entries) == 1 and warnings == []


def test_header_only_file_gives_no_entries(tmp_path):
    p = write(tmp_path, "Client,Description,Start,End\n")
    assert read(p) == ([], [])


def test_unknown_header_is_fatal(tmp_path):
    p = write(tmp_path, "who,what,when\nAcme,Design,now\n")
    with pytest.raises(FatalError, match="header"):
        read(p)


def test_empty_file_is_fatal(tmp_path):
    p = write(tmp_path, "")
    with pytest.raises(FatalError):
        read(p)


def test_missing_file_is_fatal(tmp_path):
    with pytest.raises(FatalError, match="cannot read"):
        read(str(tmp_path / "nope.csv"))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_parse.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tsinvoice.parse'`

- [ ] **Step 3: Implement** — `tsinvoice/parse.py`:
```python
"""Read one tracker export (format A or B) into Entry objects."""
from __future__ import annotations

import csv
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Callable

from tsinvoice.model import Entry, FatalError

FORMAT_A = ["Client", "Description", "Start", "End"]
FORMAT_B = ["client", "task", "start_iso", "duration_minutes"]
_A_TIME = "%d/%m/%Y %H:%M"

Warn = Callable[[str], None]


class _BadRow(Exception):
    pass


def read_tracker(path: str, tracker: str, arg_index: int, warn: Warn) -> list[Entry]:
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.reader(fh)
            rows = [(reader.line_num, row) for row in reader]
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise FatalError(f"cannot read tracker file {path}: {exc}") from exc
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
    minutes = int(duration)
    return client, description, start, start + timedelta(minutes=minutes), minutes
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_parse.py -v`
Expected: all passed

- [ ] **Step 5: Commit**
```bash
git add tsinvoice/parse.py tests/test_parse.py
git commit -m "feat: parse format A and B tracker exports"
```

---

### Task 3: Deduplicate overlapping exports

**Files:**
- Create: `tsinvoice/dedupe.py`
- Test: `tests/test_dedupe.py`

**Interfaces:**
- Consumes: `Entry`, `norm` from `tsinvoice.model`.
- Produces: `dedupe(entries: list[Entry]) -> list[Entry]` — returns kept entries in input order (`(arg_index, line)`).

Rule (spec "Deduplication"): key = `(tracker, start, end, norm(client), norm(description))`. Within one file all copies are real. Across files of the same tracker, keep `max` copies per file, not the sum. Different trackers never dedupe.

- [ ] **Step 1: Write the failing tests** — `tests/test_dedupe.py`:
```python
from tests.factories import entry
from tsinvoice.dedupe import dedupe


def e(arg_index, line, tracker="desktop", client="Acme", description="Design",
      start="2026-03-02T09:00", minutes=30):
    return entry(start, minutes, client=client, description=description,
                 tracker=tracker, arg_index=arg_index, line=line)


def test_same_entry_twice_in_one_file_is_kept_twice():
    assert len(dedupe([e(0, 2), e(0, 3)])) == 2


def test_across_exports_of_one_tracker_keep_max_count():
    entries = [e(0, 2), e(0, 3), e(1, 2), e(1, 3), e(1, 4)]
    kept = dedupe(entries)
    assert len(kept) == 3
    assert [x.order for x in kept] == [(0, 2), (0, 3), (1, 4)]


def test_max_count_when_larger_export_comes_first():
    assert len(dedupe([e(0, 2), e(0, 3), e(0, 4), e(1, 2)])) == 3


def test_match_uses_normalised_text():
    kept = dedupe([e(0, 2, client="Acme", description="Design  work"),
                   e(1, 2, client=" ACME ", description="design work")])
    assert len(kept) == 1
    assert kept[0].order == (0, 2)


def test_different_trackers_never_dedupe():
    assert len(dedupe([e(0, 2, tracker="desktop"), e(1, 2, tracker="phone")])) == 2


def test_different_times_are_not_duplicates():
    assert len(dedupe([e(0, 2), e(1, 2, minutes=31)])) == 2
    assert len(dedupe([e(0, 2), e(1, 2, start="2026-03-02T09:01")])) == 2


def test_output_is_in_input_order_regardless_of_given_order():
    kept = dedupe([e(1, 5, start="2026-03-02T08:00"), e(0, 9, start="2026-03-02T10:00")])
    assert [x.order for x in kept] == [(0, 9), (1, 5)]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_dedupe.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tsinvoice.dedupe'`

- [ ] **Step 3: Implement** — `tsinvoice/dedupe.py`:
```python
"""Remove entries repeated across overlapping exports of the same tracker."""
from __future__ import annotations

from collections import defaultdict

from tsinvoice.model import Entry, norm


def _key(e: Entry):
    return (e.tracker, e.start, e.end, norm(e.client), norm(e.description))


def dedupe(entries: list[Entry]) -> list[Entry]:
    """Keep, per identity key, as many copies as the largest single export holds."""
    kept_count: dict = defaultdict(int)
    seen_in_file: dict = defaultdict(int)
    kept = []
    for e in sorted(entries, key=lambda x: x.order):
        key = _key(e)
        seen_in_file[key, e.arg_index] += 1
        if seen_in_file[key, e.arg_index] > kept_count[key]:
            kept_count[key] = seen_in_file[key, e.arg_index]
            kept.append(e)
    return kept
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_dedupe.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**
```bash
git add tsinvoice/dedupe.py tests/test_dedupe.py
git commit -m "feat: dedupe entries across exports by max count"
```

---

### Task 4: Join continued entries into sessions

**Files:**
- Create: `tsinvoice/join.py`
- Test: `tests/test_join.py`

**Interfaces:**
- Consumes: `Entry`, `Session`, `norm` from `tsinvoice.model`.
- Produces: `join(entries: list[Entry]) -> list[Session]` — every entry appears in exactly one session; sessions are returned in order of their first entry's `(start, arg_index, line)`.

Rule (spec "Joining"): Q continues P when normalised client and description match and `0 <= Q.start - P.end <= 2 minutes`. One predecessor/successor each. Process P in `(start, arg_index, line)` order; choose the unclaimed candidate with the smallest gap, then earliest `(arg_index, line)`.

- [ ] **Step 1: Write the failing tests** — `tests/test_join.py`:
```python
from datetime import date

from tests.factories import entry
from tsinvoice.join import join


def orders(sessions):
    return [[x.order for x in s.entries] for s in sessions]


def test_back_to_back_entries_join_across_trackers():
    a = entry("2026-03-02T09:00", 7, tracker="desktop", arg_index=0, line=2)
    b = entry("2026-03-02T09:07", 7, tracker="phone", arg_index=1, line=2)
    (s,) = join([a, b])
    assert s.entries == [a, b]
    assert s.raw_minutes == 14 and s.minutes == 18


def test_gap_of_two_minutes_joins_three_does_not():
    a = entry("2026-03-02T09:00", 30, line=2)
    b = entry("2026-03-02T09:32", 30, line=3)   # gap 2 -> joins
    c = entry("2026-03-02T10:05", 30, line=4)   # gap 3 -> separate
    assert orders(join([a, b, c])) == [[(0, 2), (0, 3)], [(0, 4)]]


def test_gap_measured_in_seconds():
    a = entry("2026-03-02T09:00:00", 30, line=2)
    b = entry("2026-03-02T09:32:01", 30, line=3)  # gap 2m01s -> separate
    assert len(join([a, b])) == 2


def test_overlap_never_joins():
    a = entry("2026-03-02T09:00", 60, line=2)
    b = entry("2026-03-02T09:59", 30, line=3)
    assert len(join([a, b])) == 2


def test_client_and_description_must_match_normalised():
    a = entry("2026-03-02T09:00", 30, client="Acme", description="Design", line=2)
    b = entry("2026-03-02T09:30", 30, client=" ACME", description="design", line=3)
    c = entry("2026-03-02T10:00", 30, client="Acme", description="Review", line=4)
    assert orders(join([a, b, c])) == [[(0, 2), (0, 3)], [(0, 4)]]


def test_long_chain_is_one_session():
    es = [entry(f"2026-03-02T{9 + i:02d}:00", 60, line=2 + i) for i in range(4)]
    (s,) = join(list(reversed(es)))
    assert s.entries == es
    assert s.minutes == 240


def test_smallest_gap_wins_then_input_order():
    p = entry("2026-03-02T09:00", 60, arg_index=0, line=2)
    far = entry("2026-03-02T10:02", 10, arg_index=0, line=3)
    near_late = entry("2026-03-02T10:01", 10, arg_index=1, line=2)
    near_early = entry("2026-03-02T10:01", 10, arg_index=0, line=4)
    sessions = join([p, far, near_late, near_early])
    assert sessions[0].entries == [p, near_early]
    # the losers stay separate sessions
    assert sorted(len(s.entries) for s in sessions) == [1, 1, 2]


def test_earlier_session_gets_first_pick():
    p1 = entry("2026-03-02T08:00", 120, arg_index=0, line=2)  # ends 10:00
    p2 = entry("2026-03-02T09:00", 60, arg_index=1, line=2)   # ends 10:00
    q = entry("2026-03-02T10:00", 30, arg_index=0, line=3)
    sessions = join([q, p2, p1])
    assert sessions[0].entries == [p1, q]
    assert sessions[1].entries == [p2]


def test_same_start_tie_broken_by_input_order():
    p1 = entry("2026-03-02T09:00", 60, arg_index=1, line=2)
    p2 = entry("2026-03-02T09:00", 60, arg_index=0, line=5)
    q = entry("2026-03-02T10:00", 30, arg_index=0, line=9)
    sessions = join([p1, p2, q])
    assert sessions[0].entries == [p2, q]


def test_join_across_midnight_keeps_start_date():
    a = entry("2026-03-02T23:50", 10, line=2)
    b = entry("2026-03-03T00:01", 9, line=3)
    (s,) = join([a, b])
    assert s.date == date(2026, 3, 2)
    assert s.minutes == 24  # 19 rounded up to 24


def test_empty_input():
    assert join([]) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_join.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tsinvoice.join'`

- [ ] **Step 3: Implement** — `tsinvoice/join.py`:
```python
"""Link entries that continue one another into sessions."""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from tsinvoice.model import Entry, Session, norm

MAX_GAP = timedelta(minutes=2)
_ZERO = timedelta(0)


def _join_key(e: Entry):
    return (norm(e.client), norm(e.description))


def join(entries: list[Entry]) -> list[Session]:
    ordered = sorted(entries, key=lambda e: (e.start, e.arg_index, e.line))
    successor: list[int | None] = [None] * len(ordered)
    has_predecessor = [False] * len(ordered)
    by_key: dict = defaultdict(list)
    for i, e in enumerate(ordered):
        by_key[_join_key(e)].append(i)

    for i, p in enumerate(ordered):
        best, best_rank = None, None
        for j in by_key[_join_key(p)]:
            if j == i or has_predecessor[j]:
                continue
            q = ordered[j]
            gap = q.start - p.end
            if _ZERO <= gap <= MAX_GAP:
                rank = (gap, q.arg_index, q.line)
                if best_rank is None or rank < best_rank:
                    best, best_rank = j, rank
        if best is not None:
            successor[i] = best
            has_predecessor[best] = True

    sessions = []
    for i in range(len(ordered)):
        if has_predecessor[i]:
            continue
        chain, k = [], i
        while k is not None:
            chain.append(ordered[k])
            k = successor[k]
        sessions.append(Session(chain))
    return sessions
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_join.py -v`
Expected: all passed

- [ ] **Step 5: Commit**
```bash
git add tsinvoice/join.py tests/test_join.py
git commit -m "feat: join continued entries into sessions"
```

---

### Task 5: Rates file and pricing

**Files:**
- Create: `tsinvoice/rates.py`
- Test: `tests/test_rates.py`

**Interfaces:**
- Consumes: `FatalError`, `norm` from `tsinvoice.model`.
- Produces:
  - `@dataclass(frozen=True) class Rate(pattern: str, hourly_rate: Decimal)`
  - `load_rates(path: str, warn: Callable[[str], None]) -> list[Rate]` — raises `FatalError` for unreadable file, wrong header, wrong field count, non-numeric or negative rate; warns and skips empty patterns.
  - `find_rate(client: str, description: str, rates: list[Rate]) -> Decimal | None`
  - `price(minutes: int, hourly_rate: Decimal) -> Decimal` — quantised to `0.01`, `ROUND_HALF_UP`.

- [ ] **Step 1: Write the failing tests** — `tests/test_rates.py`:
```python
from decimal import Decimal

import pytest

from tsinvoice.model import FatalError
from tsinvoice.rates import Rate, find_rate, load_rates, price


def write(tmp_path, text):
    p = tmp_path / "rates.csv"
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_load_rates_in_file_order(tmp_path):
    p = write(tmp_path, "pattern,hourly_rate\nAcme,100\n review ,80.50\n")
    assert load_rates(p, [].append) == [Rate("Acme", Decimal("100")),
                                        Rate("review", Decimal("80.50"))]


def test_empty_pattern_is_ignored_with_warning(tmp_path):
    p = write(tmp_path, "pattern,hourly_rate\n,100\nAcme,50\n")
    warnings = []
    assert load_rates(p, warnings.append) == [Rate("Acme", Decimal("50"))]
    assert warnings == [f"warning: {p}:2: empty pattern ignored"]


@pytest.mark.parametrize("text", [
    "pat,rate\nAcme,100\n",
    "",
    "pattern,hourly_rate\nAcme,lots\n",
    "pattern,hourly_rate\nAcme,-5\n",
    "pattern,hourly_rate\nAcme,NaN\n",
    "pattern,hourly_rate\nAcme\n",
])
def test_bad_rates_file_is_fatal(tmp_path, text):
    with pytest.raises(FatalError):
        load_rates(write(tmp_path, text), [].append)


def test_missing_rates_file_is_fatal(tmp_path):
    with pytest.raises(FatalError, match="cannot read"):
        load_rates(str(tmp_path / "nope.csv"), [].append)


def test_find_rate_substring_case_insensitive_client_or_description():
    rates = [Rate("acme", Decimal("100")), Rate("REVIEW", Decimal("80"))]
    assert find_rate("ACME Corp", "anything", rates) == Decimal("100")
    assert find_rate("Other", "code review", rates) == Decimal("80")
    assert find_rate("Other", "Design", rates) is None


def test_find_rate_first_match_wins():
    rates = [Rate("review", Decimal("80")), Rate("acme", Decimal("100"))]
    assert find_rate("Acme", "Review", rates) == Decimal("80")


def test_find_rate_normalises_whitespace():
    assert find_rate("Big   Co", "x", [Rate("big co", Decimal("1"))]) == Decimal("1")


def test_price_uses_minutes_over_sixty_half_up():
    assert price(18, Decimal("100")) == Decimal("30.00")
    assert price(6, Decimal("0.05")) == Decimal("0.01")    # 0.005 rounds up
    assert price(6, Decimal("0.15")) == Decimal("0.02")    # 0.015 rounds up, not to even
    assert str(price(6, Decimal("0"))) == "0.00"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_rates.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tsinvoice.rates'`

- [ ] **Step 3: Implement** — `tsinvoice/rates.py`:
```python
"""Load the rates file and price sessions."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Callable

from tsinvoice.model import FatalError, norm

RATES_HEADER = ["pattern", "hourly_rate"]
_CENT = Decimal("0.01")


@dataclass(frozen=True)
class Rate:
    pattern: str
    hourly_rate: Decimal


def load_rates(path: str, warn: Callable[[str], None]) -> list[Rate]:
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.reader(fh)
            rows = [(reader.line_num, row) for row in reader]
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise FatalError(f"cannot read rates file {path}: {exc}") from exc
    if not rows or [c.strip() for c in rows[0][1]] != RATES_HEADER:
        raise FatalError(f"{path}: rates header must be {','.join(RATES_HEADER)}")

    rates = []
    for line, row in rows[1:]:
        if not row:
            continue
        if len(row) != 2:
            raise FatalError(f"{path}:{line}: expected 2 fields, got {len(row)}")
        pattern, rate_text = row[0].strip(), row[1].strip()
        try:
            rate = Decimal(rate_text)
        except InvalidOperation:
            rate = None
        if rate is None or not rate.is_finite() or rate < 0:
            raise FatalError(f"{path}:{line}: hourly_rate {rate_text!r} is not a number >= 0")
        if not pattern:
            warn(f"warning: {path}:{line}: empty pattern ignored")
            continue
        rates.append(Rate(pattern, rate))
    return rates


def find_rate(client: str, description: str, rates: list[Rate]) -> Decimal | None:
    c, d = norm(client), norm(description)
    for r in rates:
        p = norm(r.pattern)
        if p in c or p in d:
            return r.hourly_rate
    return None


def price(minutes: int, hourly_rate: Decimal) -> Decimal:
    return (Decimal(minutes) * hourly_rate / Decimal(60)).quantize(_CENT, rounding=ROUND_HALF_UP)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_rates.py -v`
Expected: all passed

- [ ] **Step 5: Commit**
```bash
git add tsinvoice/rates.py tests/test_rates.py
git commit -m "feat: load rates and price sessions"
```

---

### Task 6: Session ids, ordering and CSV output

**Files:**
- Create: `tsinvoice/session_id.py`, `tsinvoice/output.py`
- Test: `tests/test_session_id.py`, `tests/test_output.py`

**Interfaces:**
- Consumes: `Entry`, `Session`, `norm` from `tsinvoice.model`.
- Produces:
  - `compute_id(entries: list[Entry]) -> str` — `"s-"` + 12 hex chars.
  - `assign_ids(sessions: list[Session]) -> None` — sets `session_id` in place; sessions must already be in output order.
  - `OUTPUT_HEADER = ["date", "client", "description", "minutes", "amount", "session_id"]`
  - `sort_sessions(sessions: list[Session]) -> list[Session]` — by `(norm(client), start, first.arg_index, first.line)`.
  - `session_row(session: Session, amount: Decimal) -> list[str]`
  - `render_csv(rows: list[list[str]]) -> str` — header + rows, `\n` line endings.

- [ ] **Step 1: Write the failing tests** — `tests/test_session_id.py`:
```python
import re

from tests.factories import entry
from tsinvoice.model import Session
from tsinvoice.session_id import assign_ids, compute_id


def chain(tracker="desktop", arg_index=0):
    return [entry("2026-03-02T09:00", 7, tracker=tracker, arg_index=arg_index, line=2),
            entry("2026-03-02T09:07", 7, tracker=tracker, arg_index=arg_index, line=3)]


def test_compute_id_shape_and_stability():
    sid = compute_id(chain())
    assert re.fullmatch(r"s-[0-9a-f]{12}", sid)
    assert compute_id(chain()) == sid


def test_compute_id_ignores_input_position():
    assert compute_id(chain(arg_index=0)) == compute_id(chain(arg_index=5))


def test_compute_id_depends_on_content():
    assert compute_id(chain("desktop")) != compute_id(chain("phone"))


def test_assign_ids_blank_for_single_entry_and_distinct_on_collision():
    single = Session([entry("2026-03-02T08:00", 30)])
    s1, s2 = Session(chain()), Session(chain(arg_index=1))
    assign_ids([single, s1, s2])
    assert single.session_id == ""
    assert s1.session_id == compute_id(s1.entries)
    assert s2.session_id == s1.session_id + "-2"
```

`tests/test_output.py`:
```python
import csv
import io
from decimal import Decimal

from tests.factories import entry
from tsinvoice.model import Session
from tsinvoice.output import OUTPUT_HEADER, render_csv, session_row, sort_sessions


def test_sort_by_normalised_client_then_start_then_input_order():
    b = Session([entry("2026-03-01T09:00", 30, client="beta")])
    a_late = Session([entry("2026-03-02T09:00", 30, client="Alpha")])
    a_early = Session([entry("2026-03-01T09:00", 30, client="ALPHA", arg_index=1)])
    a_tie = Session([entry("2026-03-01T09:00", 30, client="alpha", arg_index=0, line=9)])
    assert sort_sessions([b, a_late, a_early, a_tie]) == [a_tie, a_early, a_late, b]


def test_session_row_format():
    s = Session([entry("2026-03-02T09:00", 14, client="Acme", description="Design")],
                session_id="s-abc")
    assert session_row(s, Decimal("30.00")) == ["2026-03-02", "Acme", "Design", "18", "30.00", "s-abc"]


def test_render_csv_header_and_newlines():
    text = render_csv([["2026-03-02", "Acme", "Design", "18", "30.00", ""]])
    assert text == "date,client,description,minutes,amount,session_id\n2026-03-02,Acme,Design,18,30.00,\n"


def test_render_csv_empty_is_header_only():
    assert render_csv([]) == ",".join(OUTPUT_HEADER) + "\n"


def test_write_csv_quotes_commas_and_quotes():
    row = ["2026-03-02", "Acme, Inc.", 'Fix "login" — café', "6", "1.00", ""]
    text = render_csv([row])
    assert list(csv.reader(io.StringIO(text)))[1] == row
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_session_id.py tests/test_output.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement** — `tsinvoice/session_id.py`:
```python
"""Deterministic ids for joined sessions."""
from __future__ import annotations

import hashlib

from tsinvoice.model import Entry, Session, norm


def compute_id(entries: list[Entry]) -> str:
    lines = [f"{e.tracker}|{e.start.isoformat()}|{e.end.isoformat()}|"
             f"{norm(e.client)}|{norm(e.description)}" for e in entries]
    digest = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
    return "s-" + digest[:12]


def assign_ids(sessions: list[Session]) -> None:
    """Set ids in place; ``sessions`` must already be in output order."""
    used: dict[str, int] = {}
    for s in sessions:
        if len(s.entries) < 2:
            s.session_id = ""
            continue
        base = compute_id(s.entries)
        used[base] = used.get(base, 0) + 1
        s.session_id = base if used[base] == 1 else f"{base}-{used[base]}"
```

`tsinvoice/output.py`:
```python
"""Order sessions and render the output CSV."""
from __future__ import annotations

import csv
import io
from decimal import Decimal

from tsinvoice.model import Session, norm

OUTPUT_HEADER = ["date", "client", "description", "minutes", "amount", "session_id"]


def sort_sessions(sessions: list[Session]) -> list[Session]:
    return sorted(sessions, key=lambda s: (norm(s.client), s.start,
                                           s.first.arg_index, s.first.line))


def session_row(session: Session, amount: Decimal) -> list[str]:
    return [session.date.isoformat(), session.client, session.description,
            str(session.minutes), f"{amount:.2f}", session.session_id]


def render_csv(rows: list[list[str]]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(OUTPUT_HEADER)
    writer.writerows(rows)
    return buf.getvalue()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_session_id.py tests/test_output.py -v`
Expected: all passed

- [ ] **Step 5: Commit**
```bash
git add tsinvoice/session_id.py tsinvoice/output.py tests/test_session_id.py tests/test_output.py
git commit -m "feat: session ids, ordering and CSV rendering"
```

---

### Task 7: CLI wiring and end-to-end tests

**Files:**
- Create: `tsinvoice/cli.py`, `tsinvoice/__main__.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `read_tracker` (parse), `dedupe`, `join`, `load_rates`, `find_rate`, `price` (rates), `assign_ids` (session_id), `sort_sessions`, `session_row`, `render_csv` (output), `FatalError` (model).
- Produces: `main(argv: list[str] | None = None) -> int`; `parse_tracker_arg(text: str) -> tuple[str, str]` (raises `FatalError`).

- [ ] **Step 1: Write the failing tests** — `tests/test_cli.py`:
```python
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

DESKTOP = ("Client,Description,Start,End\n"
           "Acme,Design,02/03/2026 09:00,02/03/2026 09:07\n"
           "Beta,Call,02/03/2026 11:00,02/03/2026 11:30\n")
DESKTOP_2 = ("Client,Description,Start,End\n"
             "Beta,Call,02/03/2026 11:00,02/03/2026 11:30\n"
             "Beta,Call,03/03/2026 11:00,03/03/2026 11:20\n")
PHONE = ("client,task,start_iso,duration_minutes\n"
         "acme,design,2026-03-02T09:07:00Z,7\n"
         "Gamma,Misc,2026-03-02T12:00:00,10\n"
         "Gamma,Misc,2026-03-02T13:00:00,12.5\n")
RATES = "pattern,hourly_rate\nacme,100\nbeta,60\n"


def run(tmp_path, *args):
    return subprocess.run([sys.executable, "-m", "tsinvoice", *args], cwd=REPO,
                          capture_output=True, text=True)


def setup(tmp_path):
    files = {"d1.csv": DESKTOP, "d2.csv": DESKTOP_2, "p.csv": PHONE, "rates.csv": RATES}
    for name, text in files.items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    return [f"--tracker", f"desktop={tmp_path / 'd1.csv'}",
            "--tracker", f"desktop={tmp_path / 'd2.csv'}",
            "--tracker", f"phone={tmp_path / 'p.csv'}",
            "--rates", str(tmp_path / "rates.csv")]


def test_end_to_end(tmp_path):
    out = tmp_path / "out.csv"
    result = run(tmp_path, "merge", *setup(tmp_path), "--out", str(out))
    assert result.returncode == 0, result.stderr
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "date,client,description,minutes,amount,session_id"
    acme, beta1, beta2, gamma = lines[1:]
    assert acme.startswith("2026-03-02,Acme,Design,18,30.00,s-")
    assert beta1 == "2026-03-02,Beta,Call,30,30.00,"
    assert beta2 == "2026-03-03,Beta,Call,24,24.00,"
    assert gamma == "2026-03-02,Gamma,Misc,12,0.00,"
    assert "p.csv:4" in result.stderr                     # bad duration warned
    assert "no rate for client 'Gamma' description 'Misc'" in result.stderr


def test_rerun_is_byte_identical(tmp_path):
    args = setup(tmp_path)
    out1, out2 = tmp_path / "o1.csv", tmp_path / "o2.csv"
    assert run(tmp_path, "merge", *args, "--out", str(out1)).returncode == 0
    assert run(tmp_path, "merge", *args, "--out", str(out2)).returncode == 0
    assert out1.read_bytes() == out2.read_bytes()


def test_same_file_twice_does_not_double(tmp_path):
    (tmp_path / "d.csv").write_text(DESKTOP, encoding="utf-8")
    (tmp_path / "rates.csv").write_text(RATES, encoding="utf-8")
    out = tmp_path / "out.csv"
    result = run(tmp_path, "merge", "--tracker", f"d={tmp_path / 'd.csv'}",
                 "--tracker", f"d={tmp_path / 'd.csv'}",
                 "--rates", str(tmp_path / "rates.csv"), "--out", str(out))
    assert result.returncode == 0, result.stderr
    assert len(out.read_text().splitlines()) == 3


def test_unknown_header_exits_2_without_output(tmp_path):
    (tmp_path / "bad.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    (tmp_path / "rates.csv").write_text(RATES, encoding="utf-8")
    out = tmp_path / "out.csv"
    result = run(tmp_path, "merge", "--tracker", f"x={tmp_path / 'bad.csv'}",
                 "--rates", str(tmp_path / "rates.csv"), "--out", str(out))
    assert result.returncode == 2
    assert "header" in result.stderr
    assert not out.exists()


def test_fatal_error_leaves_existing_output_untouched(tmp_path):
    (tmp_path / "rates.csv").write_text("nope\n", encoding="utf-8")
    (tmp_path / "d.csv").write_text(DESKTOP, encoding="utf-8")
    out = tmp_path / "out.csv"
    out.write_text("old\n", encoding="utf-8")
    result = run(tmp_path, "merge", "--tracker", f"d={tmp_path / 'd.csv'}",
                 "--rates", str(tmp_path / "rates.csv"), "--out", str(out))
    assert result.returncode == 2
    assert out.read_text() == "old\n"


def test_bad_tracker_argument_exits_2(tmp_path):
    (tmp_path / "rates.csv").write_text(RATES, encoding="utf-8")
    out = tmp_path / "out.csv"
    for bad in ["no-equals-sign", "=path.csv", "name="]:
        result = run(tmp_path, "merge", "--tracker", bad,
                     "--rates", str(tmp_path / "rates.csv"), "--out", str(out))
        assert result.returncode == 2, bad
        assert not out.exists()


def test_missing_tracker_file_exits_2(tmp_path):
    (tmp_path / "rates.csv").write_text(RATES, encoding="utf-8")
    out = tmp_path / "out.csv"
    result = run(tmp_path, "merge", "--tracker", f"d={tmp_path / 'missing.csv'}",
                 "--rates", str(tmp_path / "rates.csv"), "--out", str(out))
    assert result.returncode == 2
    assert not out.exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_cli.py -v`
Expected: FAIL (non-zero return codes: `No module named tsinvoice.__main__`)

- [ ] **Step 3: Implement** — `tsinvoice/cli.py`:
```python
"""Command-line entry point: python -m tsinvoice merge ..."""
from __future__ import annotations

import argparse
import sys
from decimal import Decimal

from tsinvoice.dedupe import dedupe
from tsinvoice.join import join
from tsinvoice.model import FatalError
from tsinvoice.output import render_csv, session_row, sort_sessions
from tsinvoice.parse import read_tracker
from tsinvoice.rates import find_rate, load_rates, price
from tsinvoice.session_id import assign_ids


def _warn(message: str) -> None:
    print(message, file=sys.stderr)


def parse_tracker_arg(text: str) -> tuple[str, str]:
    name, sep, path = text.partition("=")
    if not sep or not name.strip() or not path:
        raise FatalError(f"--tracker must be NAME=PATH, got {text!r}")
    return name.strip(), path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tsinvoice")
    sub = parser.add_subparsers(dest="command", required=True)
    merge = sub.add_parser("merge", help="merge tracker exports into priced sessions")
    merge.add_argument("--tracker", action="append", required=True, metavar="NAME=PATH")
    merge.add_argument("--rates", required=True)
    merge.add_argument("--out", required=True)
    return parser


def _merge(trackers: list[str], rates_path: str) -> str:
    specs = [parse_tracker_arg(t) for t in trackers]
    rates = load_rates(rates_path, _warn)
    entries = []
    for arg_index, (name, path) in enumerate(specs):
        entries.extend(read_tracker(path, name, arg_index, _warn))
    sessions = sort_sessions(join(dedupe(entries)))
    assign_ids(sessions)
    rows = []
    for s in sessions:
        rate = find_rate(s.client, s.description, rates)
        if rate is None:
            _warn(f"warning: no rate for client {s.client!r} description {s.description!r}")
            amount = price(s.minutes, Decimal(0))
        else:
            amount = price(s.minutes, rate)
        rows.append(session_row(s, amount))
    return render_csv(rows)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        text = _merge(args.tracker, args.rates)
    except FatalError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    try:
        with open(args.out, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
    except OSError as exc:
        print(f"error: cannot write {args.out}: {exc}", file=sys.stderr)
        return 2
    return 0
```

`tsinvoice/__main__.py`:
```python
from tsinvoice.cli import main

raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_cli.py -v`
Expected: all passed

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest -q`
Expected: all passed, 0 failures

- [ ] **Step 6: Commit**
```bash
git add tsinvoice/cli.py tsinvoice/__main__.py tests/test_cli.py
git commit -m "feat: merge CLI with end-to-end tests"
```
