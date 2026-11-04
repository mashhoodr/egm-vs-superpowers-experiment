# tsinvoice: merge overlapping timesheet exports into invoice-ready sessions

*   **Author:** EGM Elephant (for Mashhood Rastgar)
*   **Status:** Draft
*   **Date:** 2026-11-03

--------------------------------------------------------------------------------

## Overview

`tsinvoice` is a small command-line tool for one freelancer. It reads CSV
exports from two time-tracking apps (a desktop app and a phone app), removes
entries that appear twice because export date ranges overlap, joins entries
that continue each other into one session, rounds and prices each session from
a rates file, and writes one sorted CSV of sessions ready to invoice.

It is a Python 3.11 package that uses only the standard library at run time.
The command line, the input formats, the rates header, and the output header
are a fixed contract defined in [BRIEF.md](./BRIEF.md). Every behaviour rule
below comes from the owner's answers in [stakeholder_log.md](./stakeholder_log.md)
(cited as R1.n, R2.n, R3.n for round and answer number) or from a decision made
during design where the owner said "your call" (cited as **[D]**, see the
Decisions Log).

## The Problem

The owner exports CSVs from both apps every couple of weeks. The date ranges
overlap, so the same entry appears in more than one export of the same app. The
owner also sometimes stops a timer in one app and carries on in the other (or
restarts it in the same app), so one piece of work is split into two entries
back to back. Today the owner has to clean this up by hand before invoicing.
Mistakes either drop real worked time or bill the same time twice.

The tool solves this with fixed, exact rules, not guesswork: an entry is a
duplicate only when it is identical to one in another export of the same app,
and two entries are joined only when the second starts 0 to 2 minutes after the
first ends with the same client and description. Anything the rules cannot
decide safely is kept and reported as a warning on stderr.

## Goals

*   **G1. Fixed contract.** Accept exactly the CLI, input formats and rates
    header in BRIEF.md, and write exactly the output header
    `date,client,description,minutes,amount,session_id`. Exit 0 on success.
*   **G2. Remove duplicates without losing time.** Duplicates are removed only
    inside one tracker, only on an exact match, and the larger per-export count
    is kept (R1.1, R1.2, R3.2).
*   **G3. Join continuations.** Entries with the same client and description,
    where the next starts 0 to 2 minutes after the previous ends, become one
    session, in either app (R1.3, R2.2, R3.3, R3.4).
*   **G4. Price everything.** Each session's minutes are rounded up to a
    multiple of 6 and priced by the first matching rate rule, half-up to 2
    decimals (R1.4, R1.5, R2.1, R2.9).
*   **G5. Deterministic.** The same files given with the same arguments in the
    same order produce a byte-identical output file and identical stderr.
*   **G6. Nothing silent.** Every skipped row, unpriced session and
    time-overlapping pair of sessions for one client is reported on stderr.

## Non-Goals

*   Time zones, offsets and daylight saving: times are local wall-clock (R1.6).
*   Splitting sessions at midnight (R1.7).
*   Fuzzy or near-duplicate matching, or reconciling an entry that was edited
    between exports (R1.2). Edited entries are both kept; G6 warns about them.
*   Deduplicating across different trackers (R1.1).
*   Invoice documents, per-client totals, currencies, tax.
*   Configurable rounding step or join gap; state kept between runs; any input
    format other than A and B.
*   A summary or progress line on stdout or stderr.

## Open Questions

None. All questions raised during brainstorming are closed in
[concepts_brief.md](./concepts_brief.md) section 5 and copied into the
Decisions Log below.

## Glossary

*   **Tracker**: one time-tracking app, named by the NAME in
    `--tracker NAME=PATH`. NAME is compared as an exact, case-sensitive string.
*   **Export**: one `--tracker NAME=PATH` argument. Several exports may share a
    NAME. The same PATH given twice counts as two exports.
*   **Entry**: one valid data row from an export, with a client, a description,
    a start and an end.
*   **Normalised text**: text after Unicode NFC, trimming, collapsing every run
    of whitespace to one space, and case-folding. Used for all comparisons;
    never printed.
*   **Input order**: the order (argument position of the export, line number
    of the row). Argument position counts each `--tracker` argument on its own;
    exports are not grouped by NAME.
*   **Line number**: the physical line in the file where a record starts,
    counting the header as line 1.
*   **Gap**: next entry's start minus previous entry's end. Can be negative.
*   **Session**: a chain of one or more joined entries; one output row.
*   **First entry**: the earliest entry of a session's chain.
*   **Worked minutes**: the sum of the session's entry durations (gaps are not
    counted).
*   **Billed minutes**: worked minutes rounded up to the next multiple of 6.

## Critical User Journeys (CUJs)

### CUJ 1: Overlapping exports of one app

*   **Given**: two desktop exports `d1.csv` (1–15 Oct) and `d2.csv` (8–22 Oct).
    Entry "Acme, Design, 08/10/2026 09:00–10:00" appears once in each.
*   **When**: `python -m tsinvoice merge --tracker desk=d1.csv --tracker desk=d2.csv --rates rates.csv --out out.csv`
*   **Then**: the entry appears once in `out.csv`, 60 minutes, priced, blank
    session_id. Exit 0.

### CUJ 2: Work continued in the other app

*   **Given**: desktop entry "Acme, Design, 09:00–09:07" and phone entry
    "acme, design , start 09:07, 7 minutes".
*   **When**: both are passed as different trackers.
*   **Then**: one row: client "Acme", description "Design" (from the first
    entry), minutes 18 (14 worked, rounded up), amount priced on 18 minutes,
    session_id `S1`. Exit 0.

### CUJ 3: Real repeats inside one export are kept

*   **Given**: export 1 holds the same entry twice; export 2 of the same tracker
    holds it three times.
*   **When**: both exports are merged.
*   **Then**: three copies survive (the larger count, not the sum and not one):
    export 1's two copies and the first copy from export 2.

### CUJ 4: Bad data does not stop the invoice

*   **Given**: one desktop row has a blank End; one phone row has duration
    "29.5"; one session matches no rate rule.
*   **When**: the merge runs.
*   **Then**: the two bad rows are skipped with
    `tsinvoice: warning: <path>:<line>: <reason>` on stderr; the unrated session
    is written with amount `0.00` and a warning naming its client and
    description. Exit 0.

### CUJ 5: Wrong file passed

*   **Given**: one `--tracker` path points to a CSV whose header matches neither
    format, and `out.csv` already exists from an earlier run.
*   **When**: the merge runs.
*   **Then**: `tsinvoice: error: ...` on stderr, exit 2, and `out.csv` is left
    unchanged (or not created).

### CUJ 6: Rerun

*   **Given**: the same inputs and arguments as an earlier run.
*   **When**: the merge runs again.
*   **Then**: `out.csv` is byte-identical to the earlier output.

## Technical Plan (Architecture)

The tool runs in two phases. **Phase 1** reads and validates every input file
completely. Any problem with a whole file or with the command line stops the
run with exit 2 before anything is written. **Phase 2** is a pure function from
the list of valid entries and the rate rules to the output rows and warnings.
The output is then written to a temporary file and moved into place, so a
failed run never leaves a half-written or truncated `--out`.

```text
 argv ──► parse args ──► read rates ──► read each export ──► entries + row warnings
            │ exit 2        │ exit 2        │ exit 2 (file-level)
            ▼               ▼               ▼
         ─────────────────── Phase 2 (pure) ───────────────────
         dedupe (per tracker) ─► join (per client+description)
           ─► build sessions ─► round ─► price ─► sort ─► assign session_id
           ─► overlap check
         ─────────────────────────────────────────────────────
                         │
                         ▼
     emit warnings to stderr (fixed order) ─► write temp file ─► os.replace(--out) ─► exit 0
```

Nothing after Phase 1 knows which input format an entry came from: both
formats are turned into the same entry record.

### Stage 1: Command line

*   `merge` is the only sub-command. `--tracker` (repeatable), `--rates` and
    `--out` are all required.
*   Each `--tracker` value is split on its **first** `=`. A value with no `=`,
    an empty NAME or an empty PATH is a usage error: exit 2 **[D]**.
*   If the same PATH string appears under two different NAMEs, warn
    `tsinvoice: warning: <path> is given for trackers <name1> and <name2>; its entries may be billed twice`
    (once per extra NAME, in argument order) and continue **[D]**. The same
    PATH twice under one NAME needs no warning: the max-count rule keeps it
    harmless.
*   Argument errors use the standard `argparse` message and exit code 2.

### Stage 2: Read the rates file

*   Opened as UTF-8 with BOM removal (`utf-8-sig`). Missing, unreadable or
    undecodable file: exit 2 **[D]**.
*   Header: each cell trimmed and compared case-insensitively to
    `pattern,hourly_rate`; trailing empty header cells are ignored. Anything
    else: exit 2. A zero-byte file (no header): exit 2.
*   Fully blank lines are skipped. Every other row must be valid or the run
    stops with exit 2, naming the file and line **[D]**: wrong cell count
    (extra cells allowed only if empty), a pattern that is empty after
    normalising, a rate that is not a finite decimal number, or a negative
    rate. Zero is allowed. Reason: skipping a broken rule could let a broader
    later rule price a session wrongly with no signal.
*   Rules keep file order. Each rule stores its normalised pattern and its rate
    as a `Decimal`. A header-only rates file is valid: every session is then
    unrated and warned.

### Stage 3: Read each export

*   Same opening rules as the rates file; missing, unreadable or undecodable
    files exit 2. Each export is detected on its own, so one NAME may mix
    formats **[D]**.
*   **Header detection** **[D]**: cells trimmed, compared case-insensitively,
    exact names in exact order, trailing empty cells ignored.
    *   `client,description,start,end` → Format A (desktop).
    *   `client,task,start_iso,duration_minutes` → Format B (phone).
    *   Anything else, or no header at all: `tsinvoice: error: <path>: unrecognised header`, exit 2, nothing written.
*   Fully blank lines are skipped silently. Every other row that fails a check
    below is a **bad row**: it is skipped with
    `tsinvoice: warning: <path>:<line>: <reason>` and the run continues (R1.11).
*   **Checks on every row:** the cell count equals the header's (extra cells
    allowed only if empty); the client is not blank after trimming **[D]**. A
    blank description is allowed **[D]**: it is still real time.
*   **Format A row:** Start and End are trimmed and parsed as
    `DD/MM/YYYY HH:MM` (Python `%d/%m/%Y %H:%M`, so single-digit day, month or
    hour are accepted **[D]**). End blank, unparseable, or not after Start is a
    bad row (R1.11).
*   **Format B row:** `start_iso` is trimmed and must begin with
    `YYYY-MM-DD`, then `T` or a space, then `HH:MM` **[D]**; it is parsed with
    `datetime.fromisoformat`, and any offset or `Z` is dropped without
    converting (R1.6). A date-only value is a bad row. Seconds are kept
    **[D]**. `duration_minutes` is trimmed and must be ASCII digits, optionally
    followed by `.` and only zeros (so `30` and `30.0` are accepted, `29.5`,
    `0`, `-5`, `+5`, `1e2`, `3_0` are not), with a value above zero (R2.4,
    **[D]**). End = start + duration.
*   Each valid row becomes an **entry**: tracker NAME, input order
    (argument position, line number), source path and line, client text and
    description text (outer spaces trimmed, case kept), their normalised keys,
    start, end, and worked minutes (`(end - start)` in whole minutes; both
    formats always give whole minutes because desktop times have no seconds and
    phone durations are whole numbers).

Bad-row reasons (fixed text, used in tests):

| Reason text | When |
| --- | --- |
| `expected N fields, got M` | wrong non-empty cell count |
| `blank client` | client empty after trimming |
| `blank end` | Format A, End empty |
| `invalid start` / `invalid end` | Format A, unparseable |
| `end is not after start` | Format A, End ≤ Start |
| `invalid start_iso` | Format B, unparseable or no time part |
| `invalid duration_minutes` | Format B, not a whole number above zero |

### Stage 4: Remove duplicates (per tracker)

*   **Duplicate key**: (tracker NAME, normalised client, normalised
    description, start, end) (R1.1).
*   For each key, count its copies in each export separately. **N** = the
    largest of those counts (R1.1: two in one export and three in another give
    three).
*   Walk all entries of the tracker in input order and keep each entry while
    fewer than N copies of its key have been kept (R3.2). The kept copies
    supply the printed text and input order.
*   Different trackers are never compared (R1.1). Entries whose times overlap
    without matching exactly are not duplicates (R1.1, R1.2).

### Stage 5: Join continuations

*   Group the surviving entries of **all** trackers by (normalised client,
    normalised description) (R1.3).
*   Inside a group, sort by (start, input order) (R3.4).
*   Walk the group in that order. For each entry P, its candidates are the
    entries Q that have no predecessor yet and whose gap
    `Q.start − P.end` is between 0 and 120 seconds inclusive (R1.3, R2.2).
    P takes the candidate with the smallest gap, ties broken by input order;
    Q is then marked as having a predecessor (R2.3, R3.3). If no candidate is
    free, P has no successor (R3.3).
*   An entry that was taken as a successor still picks its own successor when
    its turn comes, so chains of any length form (R1.3, R3.3). A chain cannot
    loop, because every entry has a positive duration, so starts strictly
    increase along a chain.
*   Every entry with no predecessor starts a session; following successors
    gives the chain.

### Stage 6: Build, round and price sessions

*   **Printed client and description** come from the session's first entry,
    as kept in Stage 4 (outer spaces trimmed, case kept) (R1.8, R3.1).
*   **date** = the first entry's start date, `YYYY-MM-DD` (R1.6, R1.7).
*   **Worked minutes** = sum of the entries' minutes. **Billed minutes** =
    worked minutes rounded up to the next multiple of 6: `ceil(m / 6) * 6`, so
    12 stays 12 and 13 becomes 18 (R1.5, R2.1, R2.9). The `minutes` column is
    the billed number.
*   **Rate**: go through the rules in file order; the first rule whose
    normalised pattern is a substring of the normalised client **or** the
    normalised description of the first entry wins (R1.4).
*   **amount** = billed minutes × rate ÷ 60, computed in `Decimal` and rounded
    to 2 places with `ROUND_HALF_UP` (R1.5, R2.1). Example: 6 minutes at 10.05
    is 1.005, printed `1.01`. Floats are never used for money.
*   No matching rule: amount `0.00`, the row is still written, and one warning
    per row: `tsinvoice: warning: no rate for client '<client>' description '<description>' on <date>` (R1.4, R3.9).
*   A session's **span** is from its first entry's start to its last entry's
    end (used only for the overlap check).

### Stage 7: Sort and assign session IDs

*   Sort sessions by (normalised client, first entry start, first entry input
    order) (R1.9).
*   Walk the sorted rows; each session made of two or more entries gets
    `S1`, `S2`, ... in that order. Single-entry rows get a blank session_id
    (BRIEF, R3.6, **[D]**). The IDs are unique and the same for identical
    inputs; they may change when the inputs change, which the owner accepted
    (R3.6).

### Stage 8: Overlap check (warning only)

*   For every pair of output rows with the same normalised client whose spans
    overlap (each starts before the other ends; touching end-to-start is not an
    overlap), warn
    `tsinvoice: warning: overlapping sessions for client '<client>': row <i> and row <j>`,
    where i and j are 1-based data row numbers in the output, i < j, pairs in
    order of (i, j) **[D]**.
*   This does not change the output. It makes the two cases where the rules
    bill the same time twice visible: an entry edited between exports, and
    the same work timed in both apps.

### Stage 9: Warnings and output

*   **stderr order** (deterministic, G5): (1) duplicate-PATH warnings in
    argument order; (2) bad-row warnings in input order; (3) no-rate warnings
    in output row order; (4) overlap warnings in (i, j) order. Fatal errors
    are a single `tsinvoice: error: <message>` line. Nothing is printed on
    stdout **[D]**.
*   **Output file** **[D]**: UTF-8 without BOM, `\n` line endings, minimal
    quoting (fields with commas, quotes or newlines are quoted). Header exactly
    `date,client,description,minutes,amount,session_id`. `minutes` is a bare
    integer; `amount` always has two decimals (`0.00`, `12.50`, `1234.00`).
*   With no valid entries, a header-only file is written and the exit code is 0
    **[D]**.
*   The file is first written to a temporary file in the same directory as
    `--out`, then moved over `--out` with `os.replace`. An existing `--out` is
    overwritten. On exit 2 it is never touched. `--out` may equal an input
    path, because all inputs are fully read first **[D]**. If the output
    directory does not exist or is not writable: exit 2.

### Exit codes

| Exit | Cause |
| --- | --- |
| 0 | Success, including runs with skipped rows, unrated sessions, overlap warnings, or no valid entries |
| 2 | Usage error (missing option, bad `--tracker`); missing, unreadable or undecodable file; unrecognised or missing header in an export or the rates file; any bad rates row; output cannot be written |

### Worked examples

| Case | Input | Output |
| --- | --- | --- |
| Join and round | 09:00–09:07 then 09:07–09:14, same client/description | one row, minutes 18, session_id S1 |
| Gap limit | P ends 10:00; Q starts 10:02 / 10:02:01 | joined / not joined |
| Overlap is not a join | P 09:00–10:00; Q 09:59–10:30 | two rows; overlap warning |
| Claimed successor | A 09:00–10:00, B 09:30–10:01, C starts 10:01 (same group) | A is first in start order and takes C (gap 1 min); B has no free candidate; rows A+C (S1) and B; overlap warning |
| Max count | export 1 has X twice, export 2 has X three times | X three times |
| Half-up | 6 minutes at rate 10.05 | amount 1.01 |
| Exact multiple | 12 worked minutes | minutes 12 |
| No rate | no rule matches | amount 0.00, row kept, warning |
| Case of client | "Acme" session, later "ACME" session | printed "Acme" and "ACME" (each from its own first entry); sorted together |

### Decisions Log

Owner decisions are cited inline by R-number. Items marked **[D]** were left to
the designer ("your call"); the reasons are in
[concepts_brief.md](./concepts_brief.md) section 5.2. In short: keep seconds
(no false duplicates or joins); accept `30.0`; reject date-only `start_iso`;
lenient header case and spacing but exact names and order; bad rates rows are
fatal; blank client skipped, blank description kept; duplicate PATH across
NAMEs warned; sequential `S<n>` IDs; overlap warnings; atomic write; no stdout;
`\n` line endings.

## Alternatives Considered

### Alternative A: Stream each file and write rows as they are processed

*   **Pros**: Lower memory; simpler single loop.
*   **Cons**: A bad header in the third file would be found after output had
    started, breaking "exit 2, write no output". Joining and sorting need all
    entries anyway.
*   **Reason for Rejection**: Two phases (read everything, then a pure merge)
    meet the contract and make `--out` equal to an input path safe.

### Alternative B: One module per stage, or a registry of format parsers

*   **Pros**: A third input format would be one new entry.
*   **Cons**: More files and indirection for two fixed formats; a third
    format is a non-goal.
*   **Reason for Rejection**: YAGNI. A few flat modules with one shared entry
    record already keep format knowledge out of the merge logic.

### Alternative C: Per-format entry types

*   **Pros**: Keeps the original columns of each format.
*   **Cons**: Every later stage would branch on format.
*   **Reason for Rejection**: One format-agnostic entry record; nothing after
    reading needs to know the format.

### Alternative D: Global smallest-gap or optimal matching for joins

*   **Pros**: Could join more pairs in contrived cases (in the A/B/C example,
    B+C has gap 0).
*   **Cons**: Not what the owner asked for; harder to explain and test.
*   **Reason for Rejection**: The owner specified the greedy walk in start
    order (R2.3, R3.3).

### Alternative E: Truncate seconds in `start_iso` to the minute

*   **Pros**: All time arithmetic in whole minutes.
*   **Cons**: Creates false duplicates (09:00:10 and 09:00:50 would match) and
    false joins at the 2-minute edge.
*   **Reason for Rejection**: Keeping full precision is exact and costs
    nothing.

### Alternative F: Content-hash session IDs

*   **Pros**: IDs stay stable when newer, larger exports are added.
*   **Cons**: Longer IDs, collision handling.
*   **Reason for Rejection**: The owner does not rerun against earlier
    invoices (R3.6); sequential `S<n>` is enough.

### Alternative G: Skip bad rates rows with a warning

*   **Pros**: One broken rule does not stop the invoice.
*   **Cons**: Under first-match-wins, a skipped specific rule lets a broader
    later rule price the session wrongly, with only a warning line as signal.
*   **Reason for Rejection**: The rates file is short, hand-written
    configuration; failing fast is safer than mispricing.

### Alternative H: Float arithmetic for amounts

*   **Pros**: Simpler.
*   **Cons**: Python's `round` is half-to-even on binary values: 1.005 becomes
    1.00, not 1.01.
*   **Reason for Rejection**: `Decimal` with `ROUND_HALF_UP` is exact.

### Alternative I: Change the dedupe rule to catch edited or double-timed entries

*   **Pros**: Would prevent some double billing.
*   **Cons**: Contradicts the owner's exact-match rule (R1.2) and risks losing
    real time.
*   **Reason for Rejection**: Keep the owner's rule; warn about overlaps
    instead (Stage 8).

--------------------------------------------------------------------------------

## Non-Functional Requirements

*   **Performance**: Input is a freelancer's exports (hundreds to a few
    thousand rows). Join candidate search and the overlap check are simple
    scans within one client or client+description group; quadratic behaviour
    inside a group is acceptable at this size.
*   **Determinism**: No reliance on dict/set iteration order of unordered data,
    the clock, the locale, or the environment. All orders are fixed by the sort
    keys above.
*   **Safety**: Atomic output replacement; inputs are only read.
*   **Dependencies**: standard library only at run time; `pytest` for tests.

--------------------------------------------------------------------------------

### Additional Resources

*   [BRIEF.md](./BRIEF.md): fixed contract.
*   [stakeholder_log.md](./stakeholder_log.md): owner answers, rounds 1–3.
*   [concepts_brief.md](./concepts_brief.md): brainstorm analysis and decisions.

### Future Improvements

*   **Stable IDs**: content-hash session IDs if invoices ever cite them across
    reruns.
*   **Summary line**: counts of rows read, skipped, deduplicated and joined.

--------------------------------------------------------------------------------

## Detailed Implementation Plan

All paths are relative to the repository root. No other files are touched.

### Target Files to Create/Modify

#### 1. `tsinvoice/__init__.py` (Create)

*   **Type / Scope**: Python package marker.
*   **Proposed Changes**: Module docstring and `__version__ = "0.1.0"`.
    Nothing else.

#### 2. `tsinvoice/__main__.py` (Create)

*   **Type / Scope**: Entry point for `python -m tsinvoice`.
*   **Proposed Changes**: `raise SystemExit(main())` where `main` comes from
    `tsinvoice.cli`.

#### 3. `tsinvoice/model.py` (Create)

*   **Type / Scope**: Shared data records and helpers. No I/O.
*   **Proposed Changes**:
    *   `class FatalError(Exception)`: carries a message; the CLI turns it into
        `tsinvoice: error: <message>` and exit 2.
    *   `def normalise(text: str) -> str`: `unicodedata.normalize("NFC", text)`,
        then `" ".join(text.split())`, then `.casefold()`.
    *   `@dataclass(frozen=True) class Entry`: `tracker: str`,
        `order: tuple[int, int]` (argument position starting at 0, line
        number), `path: str` (as given on the command line), `line: int`,
        `client: str`, `description: str` (trimmed, case kept),
        `client_key: str`, `desc_key: str`, `start: datetime`, `end: datetime`,
        `minutes: int`.
    *   `@dataclass(frozen=True) class Rule`: `pattern_key: str`,
        `rate: Decimal`.
    *   `@dataclass class Session`: `entries: list[Entry]`; properties
        `first` (entries[0]), `start` (first.start), `end` (entries[-1].end),
        `worked_minutes` (sum), `billed_minutes` (`-(-worked // 6) * 6`).
    *   `@dataclass(frozen=True) class OutputRow`: `date: str`, `client: str`,
        `description: str`, `minutes: int`, `amount: str`, `session_id: str`,
        plus `client_key: str`, `start: datetime`, `end: datetime`,
        `order: tuple[int, int]` used for sorting and the overlap check.

#### 4. `tsinvoice/readers.py` (Create)

*   **Type / Scope**: All file reading and row validation (Stages 2 and 3).
*   **Proposed Changes**:
    *   Constants `FORMAT_A = ("client", "description", "start", "end")`,
        `FORMAT_B = ("client", "task", "start_iso", "duration_minutes")`,
        `RATES_HEADER = ("pattern", "hourly_rate")`.
    *   `def _records(path) -> tuple[list[str] | None, list[tuple[int, list[str]]]]`:
        open with `encoding="utf-8-sig", newline=""`; wrap `OSError` and
        `UnicodeDecodeError` as `FatalError(f"{path}: cannot read: {reason}")`.
        Use `csv.reader`. The record start line is
        `reader.line_num` before reading the record, plus 1. Return the header
        cells (or `None` for an empty file) and the data records with their
        start line, dropping records that are empty lists or all-blank cells.
    *   `def _header_key(cells) -> tuple[str, ...]`: trim and lowercase each
        cell, drop trailing empty cells.
    *   `def _fit(cells, width) -> list[str] | None`: return the first `width`
        cells if the record has exactly `width` cells, or more cells where the
        extras are all blank; `None` otherwise.
    *   `def read_rates(path) -> list[Rule]`: header must equal
        `RATES_HEADER` else `FatalError(f"{path}: unrecognised rates header")`;
        no header: `FatalError(f"{path}: empty rates file")`. Per record:
        width 2; pattern normalised and non-empty; rate parsed with
        `Decimal(cell.strip())`, catching `InvalidOperation`; reject if
        `not rate.is_finite()` or `rate < 0`. Any failure:
        `FatalError(f"{path}:{line}: invalid rates row: <reason>")`.
    *   `def read_export(path, tracker, arg_index) -> tuple[list[Entry], list[str]]`:
        detect format from `_header_key`; else
        `FatalError(f"{path}: unrecognised header")`. For each record, build
        an `Entry` or a warning string
        `f"tsinvoice: warning: {path}:{line}: {reason}"` using the reason
        texts in Stage 3. Format A: `datetime.strptime(s.strip(), "%d/%m/%Y %H:%M")`.
        Format B: regex `^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}` (ASCII) must
        match the trimmed value, then `datetime.fromisoformat(value)` and
        `.replace(tzinfo=None)`; duration regex `^[0-9]+(\.0+)?$` and
        `int(value.split(".")[0]) > 0`; `end = start + timedelta(minutes=d)`.
        Minutes for both formats: `int((end - start).total_seconds() // 60)`.
        Catch `ValueError` and `OverflowError` from parsing as bad rows.

#### 5. `tsinvoice/core.py` (Create)

*   **Type / Scope**: Pure merge logic (Stages 4–8). No I/O.
*   **Proposed Changes**:
    *   `def dedupe(entries: list[Entry]) -> list[Entry]`: input is all
        entries in input order. Key = `(tracker, client_key, desc_key, start, end)`.
        Count per `(key, order[0])` with `collections.Counter`; `limit[key]` =
        max over exports. Keep an entry while `kept[key] < limit[key]`.
        Return survivors in input order.
    *   `def join(entries: list[Entry]) -> list[Session]`: group by
        `(client_key, desc_key)` preserving input order; sort each group by
        `(start, order)`. Track `has_pred: set[int]` and `succ: dict[int, int]`
        over indices into the sorted group. For each index p, scan indices q
        with `q not in has_pred`, `q != p`, and
        `0 <= (g[q].start - g[p].end).total_seconds() <= 120`; choose the
        minimum by `(gap_seconds, g[q].order)`. Then build a `Session` for
        each index not in `has_pred` by following `succ`. Return sessions in
        any order (sorted later).
    *   `def find_rate(rules, client_key, desc_key) -> Decimal | None`: first
        rule with `pattern_key in client_key or pattern_key in desc_key`.
    *   `def price(minutes: int, rate: Decimal) -> str`:
        `(Decimal(minutes) * rate / Decimal(60)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)`,
        formatted with `format(value, "f")`.
    *   `def merge(entries, rules) -> tuple[list[OutputRow], list[str]]`:
        dedupe → join → build rows (date from `first.start.date().isoformat()`,
        texts from `first`, billed minutes, amount or `"0.00"`) → sort by
        `(client_key, start, order)` → assign `S1..Sn` to rows whose session
        has two or more entries → collect no-rate warnings in row order →
        overlap warnings: for each client_key, compare every pair i < j of its
        rows, overlap when `a.start < b.end and b.start < a.end`, then order
        all overlap warnings by `(i, j)` using 1-based output row numbers.
        Return rows and warnings (no-rate first, then overlap). Warning texts
        exactly as in Stages 6 and 8, using the printed client/description.

#### 6. `tsinvoice/writer.py` (Create)

*   **Type / Scope**: Output CSV (Stage 9).
*   **Proposed Changes**: `def write_rows(out_path, rows) -> None`: create a
    temporary file with `tempfile.NamedTemporaryFile("w", encoding="utf-8",
    newline="", dir=<dir of out_path or ".">, prefix=".tsinvoice-",
    delete=False)`; write with `csv.writer(f, lineterminator="\n")` the header
    and one line per row; flush, close, `os.replace(tmp, out_path)`. On any
    `OSError`, remove the temp file if it exists and raise
    `FatalError(f"{out_path}: cannot write: {reason}")`.

#### 7. `tsinvoice/cli.py` (Create)

*   **Type / Scope**: Argument parsing and orchestration.
*   **Proposed Changes**:
    *   `def build_parser() -> argparse.ArgumentParser`: program name
        `tsinvoice`; required sub-command `merge` with `--tracker`
        (`action="append"`, `required=True`, `type=parse_tracker`),
        `--rates` and `--out` (both required).
    *   `def parse_tracker(value) -> tuple[str, str]`: split on the first `=`;
        raise `argparse.ArgumentTypeError("expected NAME=PATH")` if there is
        no `=` or either side is empty (argparse then exits 2).
    *   `def main(argv: list[str] | None = None) -> int`: parse args; collect
        duplicate-PATH warnings (a PATH seen before under a different NAME);
        read rates; read every export in argument order, collecting entries
        and row warnings; call `core.merge`; print warnings to `sys.stderr`
        in the Stage 9 order; call `writer.write_rows`; return 0. Catch
        `FatalError` anywhere: print `tsinvoice: error: <message>` to stderr
        and return 2, without printing warnings collected so far and without
        writing. Rates are read before exports so that a rates error is
        reported first.

#### 8. `tests/conftest.py` (Create)

*   **Type / Scope**: Test helpers.
*   **Proposed Changes**: fixture `write_csv(tmp_path)` returning a function
    that writes given text to a named file and returns its path; helper
    `run(args) -> (exit_code, stdout, stderr, out_text)` that calls
    `tsinvoice.cli.main(args)` with `capsys`, catching `SystemExit` from
    argparse; helper `run_subprocess(args, cwd)` using
    `subprocess.run([sys.executable, "-m", "tsinvoice", ...])` for
    end-to-end checks.

#### 9. `tests/test_readers.py` (Create)

*   **Type / Scope**: Unit tests for Stages 2–3.
*   **Proposed Changes**: format detection (A, B, case/spacing/BOM in header,
    trailing empty header cell, wrong order, extra column, zero-byte file →
    `FatalError`); Format A bad rows (blank End, unparseable, End ≤ Start,
    blank client); blank description kept; Format B (offset and `Z` dropped,
    seconds kept, date-only rejected, durations `30`, `30.0` accepted and
    `29.5`, `0`, `-5`, `+5`, `1e2`, `3_0`, blank rejected); line numbers
    (header is line 1, blank lines counted, quoted multi-line field reports
    its start line); ragged rows; rates file (valid, header-only, bad header,
    empty pattern, non-numeric, `NaN`, negative → `FatalError`; zero rate
    allowed).

#### 10. `tests/test_core.py` (Create)

*   **Type / Scope**: Unit tests for Stages 4–8, using hand-built `Entry`
    lists.
*   **Proposed Changes**: dedupe (identical across exports kept once; counts 2
    and 3 give 3 and the kept copies are export 1's two plus export 2's
    first; identical copies within one export all kept; case/space
    differences dedupe; one-minute difference not deduped; different trackers
    never deduped; same path twice under one NAME); join (gaps 0, 120 s
    joined; 121 s and negative not joined; chains of 3 across trackers;
    smallest gap wins; gap tie broken by input order; claimed-successor
    A/B/C case; same-start predecessors in input order; different
    descriptions not joined); rounding (1→6, 6→6, 7→12, 12→12, 14→18); price
    (6 min at 10.05 → `1.01`, half-up, zero rate, large values with no
    exponent notation); rate matching (first rule wins, description-only
    match, case-insensitive, whitespace-normalised pattern, no match →
    `0.00` and warning); printed text from each session's own first entry
    ("Acme" vs "ACME"); sort order with input-order tie-break; session_id only
    on joined rows, sequential and unique; overlap warnings (overlap warned,
    touching not warned, different clients not warned, order (i, j)).

#### 11. `tests/test_cli.py` (Create)

*   **Type / Scope**: End-to-end tests through `main()` and one through
    `python -m tsinvoice`.
*   **Proposed Changes**: CUJ 1–6 as tests; exact output header and bytes
    (`\n` endings, no BOM, quoting of a description with a comma);
    header-only output for no valid entries; exit 2 with existing `--out`
    unchanged for an unrecognised header, a missing tracker file, a missing
    rates file and a bad rates row; bad `--tracker` values (`desk`, `=a.csv`,
    `desk=`) exit 2; duplicate PATH under two NAMEs warns; `--out` equal to an
    input path works; nothing on stdout; byte-identical output and stderr
    across two runs; stderr ordering across the four warning kinds.

#### 12. `pyproject.toml` (Create)

*   **Type / Scope**: Project metadata and pytest configuration.
*   **Proposed Changes**: `[project]` name `tsinvoice`, version `0.1.0`,
    `requires-python = ">=3.11"`, no dependencies; `[tool.pytest.ini_options]`
    `testpaths = ["tests"]`, `pythonpath = ["."]`.

#### 13. `README.md` (Create)

*   **Type / Scope**: Short user documentation.
*   **Proposed Changes**: what the tool does, the command, input and output
    formats, the dedupe/join/rounding/pricing rules in one paragraph each,
    warnings and exit codes, and how to run tests. Link to `BRIEF.md` and the
    design document.

### Verification Plan

*   **Compilation/Build**: `python -m compileall tsinvoice`
*   **Unit Tests**: `python -m pytest` from the repository root; all tests
    pass.
*   **Static Analysis & Linting**: none required (stdlib only); optional
    `python -m pyflakes` if available.
*   **Test Coverage Requirement**: every rule in Stages 1–9 and every row of
    the worked-examples and exit-code tables has at least one test.
*   **E2E/Integration**: `tests/test_cli.py` runs the real command with
    `python -m tsinvoice merge ...` on temporary files.

--------------------------------------------------------------------------------

<!-- Provenance: Indicates initial structural drafting via EGM. -->

*Drafted with EGM*
