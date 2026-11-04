# stockmerge: merge overlapping stock-take scans into one inventory

*   **Author:** EGM Elephant
*   **Status:** Draft
*   **Date:** 2026-11-03

--------------------------------------------------------------------------------

## Overview

A shop counts stock per location ("shop floor", "back room") with two barcode
scanners. Each scanner exports a CSV in its own format. The same location is
often exported more than once, so the same scan can appear in several files.
Stock that moves between locations shows up as a negative scan at one location
and a positive scan at another.

`stockmerge` is a command line tool, written in Python 3.11 with the standard
library only. It reads every export, removes copies of a scan that came from
overlapping exports of one location, links each stock-out to its matching
stock-in at another location as a move, puts every other row in a category from
the owner's rules file, and writes one CSV with one row per kept scan. The same
inputs always give the same output, byte for byte.

## The Problem

Today the owner has several overlapping CSV files in two formats and no single
count. Adding the files together counts overlapping scans twice. Treating each
location on its own makes every move look like a loss at one place and a gain
at another. The tool must remove the overlap without ever removing a real
second scan of the same item, and must recognise moves under a fixed,
explainable rule.

The fixed contract in `BRIEF.md` (command line, input headers, rules header,
output header, exit 0 on success) cannot change. Everything below works inside
it.

## Goals

*   **G1 Dedup without loss.** Copies of a scan across exports of one location
    are removed. Repeated identical rows inside one export are all kept.
*   **G2 Moves.** A stock-out and its matching stock-in at another location are
    linked with one shared `move_id` and the category `Move`.
*   **G3 Categories.** Every row that is not part of a move gets a category from
    the rules file, or `Uncategorised`.
*   **G4 Determinism.** The same arguments and the same input bytes give a
    byte-identical output file.
*   **G5 Every row is accounted for.** Each data row is either written, removed
    as a counted duplicate, or skipped with a warning that names the file and
    line. The tool never ends with an uncaught exception.
*   **G6 Failed runs change nothing.** When the tool exits 2, the `--out` file is
    not created and an existing one is not changed.

## Non-Goals

*   Totals per SKU per location. The output is one row per kept scan. (Owner
    confirmed one row per scan; totals were left to the builder, who left them
    out.)
*   Time zones or daylight saving. All times are shop local time from one clock.
*   Comparing times more precisely than the minute.
*   Dedup or SKU matching across different location names.
*   Fuzzy matching of SKUs beyond trimming, case and leading zeros. Fuzzy
    matching of location names.
*   Case sizes other than 12, or per-SKU case sizes.
*   Reading the Format B `note` for any purpose.
*   Partial moves, split moves, or moves with more than two rows.
*   Globally optimal move matching. Matching is greedy, by a fixed order.
*   Input formats other than A and B, other delimiters, other encodings than
    UTF-8.
*   Regular-expression or wildcard rules.
*   `move_id` values that stay the same when the set of inputs changes.
*   Any runtime dependency, config file, or subcommand other than `merge`.

## Open Questions

None are open. Every behaviour question was answered by the owner or recorded
as a builder's call in `concepts_brief.md` and `stakeholder_log.md`. The
builder's calls are marked **[builder]** in the rules below so the owner can
overrule them.

## Glossary

*   **Export**: one `--location NAME=PATH` argument and the file it names.
*   **Argument index**: the position of an export among the `--location`
    arguments, starting at 0.
*   **Record number**: the position of a data row within its file, starting at
    0, counting only rows that were read as records (blank lines excluded).
*   **Input order**: sort by (argument index, record number).
*   **Minute time**: a scan's timestamp with seconds and fractions dropped (not
    rounded). Every time comparison uses minute time.
*   **Normalised SKU**: the SKU text with outer spaces removed, lower-cased,
    and leading `0` characters removed. If nothing is left, it is `0`. So
    `00123`, `123` and ` 123 ` are the same SKU, and `000` is `0`.
*   **Scan key**: (location name, minute time, `qty_each`, normalised SKU).
*   **Scan order**: sort by (minute time, location name, input order).

## Critical User Journeys (CUJs)

### CUJ 1: Two overlapping exports of one location

*   **Given**: `shop.csv` (Format A) and `shop2.csv` (Format B) are both exports
    of "shop floor". Both contain the scan "SKU `00123`, 1 case, 05/03/2026
    14:30". `shop.csv` contains it twice (two shelves). `shop2.csv` has
    `2026-03-05T14:30:41,123,12,` three times.
*   **When**: the owner runs
    `python -m stockmerge merge --location "shop floor=shop.csv" --location "shop floor=shop2.csv" --rules rules.csv --out inv.csv`.
*   **Then**: `inv.csv` has three rows for that scan (the highest count in one
    export): two with `sku` `00123` from `shop.csv`, and one with `sku` `123`
    from `shop2.csv`. Each has `qty_each` 12. Exit code 0.

### CUJ 2: Stock moved from the back room to the shop floor

*   **Given**: "back room" has `-6` of SKU `ABC` at 10:05. "shop floor" has `6`
    of `abc` at 11:40.
*   **When**: the owner runs a merge with both locations.
*   **Then**: both rows are in the output with category `Move` and the same
    `move_id` (for example `M0001`). Neither row is categorised by the rules.

### CUJ 3: A file with a few bad rows

*   **Given**: one export has a row with date `31/02/2026 10:00` and one with
    quantity `2.5`.
*   **When**: the owner runs a merge.
*   **Then**: those two rows are skipped. stderr shows
    `stockmerge: warning: PATH:LINE: reason` for each, and a final summary line.
    The other rows are written. Exit code 0.

### CUJ 4: A wrong file is passed

*   **Given**: one `--location` points at a file whose header is neither Format
    A nor Format B, and an `inv.csv` from yesterday exists.
*   **When**: the owner runs a merge.
*   **Then**: stderr shows `stockmerge: error: PATH: unrecognised header ...`.
    Exit code 2. Yesterday's `inv.csv` is unchanged.

### CUJ 5: Running twice

*   **Given**: any valid set of inputs.
*   **When**: the owner runs the same command twice.
*   **Then**: the two output files are byte-identical.

## Technical Plan (Architecture)

The tool is a straight pipeline of pure functions over one record type. Only
the command line layer touches the filesystem, stderr and the exit code.

```text
argv
  │
  ▼
[1 parse args] ──usage error──► exit 2
  │ exports: [(arg_index, name, path)], rules path, out path
  ▼
[2 validate paths] ──missing/unreadable/--out is an input──► exit 2
  │
  ▼
[3 load rules] ──bad header / undecodable──► exit 2
  │ rules: [(pattern_lower, category)]      bad row ──► warning
  ▼
[4 read exports] ──unknown header / undecodable / empty file──► exit 2
  │ scans: [Scan] in input order             bad row ──► warning
  ▼
[5 dedup]  per location: keep first N copies of each scan key,
  │        N = highest count of that key in any one export
  ▼
[6 link moves]  greedy, negatives in scan order
  │
  ▼
[7 categorise]  non-move rows: first matching rule, else Uncategorised
  │
  ▼
[8 sort]  (location, normalised SKU, minute time, input order)
  │
  ▼
[9 write]  temp file in --out's folder, then os.replace ──► exit 0
```

All input is read and checked (steps 1 to 4) before anything is written. That
is how G6 holds: every exit-2 condition is found before step 9 starts, and step
9 writes to a temporary file that only replaces `--out` once it is complete.

### The record type

One frozen dataclass, `Scan`, carries a row from step 4 to step 9:

| Field | Meaning |
| --- | --- |
| `location` | location name, outer spaces trimmed |
| `arg_index` | argument index of the export |
| `record_no` | record number within the file |
| `path`, `line` | file path as given, and the first physical line of the row (for warnings) |
| `minute` | naive `datetime` with seconds and microseconds set to 0 |
| `sku` | SKU text, outer spaces trimmed, case and zeros kept (written to output) |
| `sku_norm` | normalised SKU |
| `qty_each` | signed whole number of single items |

Steps 6 and 7 do not change `Scan`. Step 6 returns a mapping from a scan's
identity `(arg_index, record_no)` to a `move_id`. Step 7 returns a category per
scan. Step 8 builds output rows `(location, sku, qty_each, category, move_id)`.

### Rules, by pipeline step

Rule IDs are used by the tests. **[owner]** means the owner decided it;
**[builder]** means the owner left it to the builder.

**Step 1. Command line**

*   R1.1 [contract] `merge` is the only subcommand and is required.
    `--location` may repeat and is required at least once; `--rules` and
    `--out` are required. Abbreviated options are not accepted.
*   R1.2 [builder] `--location` splits on the first `=`. The name and the path
    are each trimmed of outer spaces. A missing `=`, an empty name or an empty
    path is a usage error: exit 2.
*   R1.3 [builder] The same NAME may appear with several PATHs. The same PATH
    may appear twice for one NAME; it is read twice as two exports, and dedup
    makes the second copy add nothing.
*   R1.4 [builder] Location names are compared exactly as written after
    trimming, so `Shop Floor` and `shop floor` are two locations. If two names
    differ only by case or inner spaces, print a warning, because this usually
    means a typo that turns off dedup and can create false moves.
*   R1.5 [builder] If the same PATH appears under two different names, print a
    warning.

**Step 2. Paths**

*   R2.1 [builder] Every input path and the rules path must exist and be a
    readable file; otherwise exit 2 with a message naming the path.
*   R2.2 [builder] `--out` must not resolve to the same file as any input or
    the rules file (compared with `os.path.realpath`); otherwise exit 2. The
    folder of `--out` must exist; otherwise exit 2.

**Step 3. Rules file**

*   R3.1 [contract] The header, after removing a UTF-8 BOM and trimming each
    cell, must be exactly `pattern,category`. Otherwise exit 2.
*   R3.2 [builder] Each data row must have exactly 2 fields. Both are trimmed.
    A row with the wrong field count, a blank pattern or a blank category is
    skipped with a warning. Blank lines are ignored without a warning.
*   R3.3 [owner] A pattern matches when it is a substring of the SKU, ignoring
    case. Rules are tried in file order; the first match wins.
*   R3.4 [builder] The pattern is lower-cased and compared with the normalised
    SKU, so a SKU gets the same category whichever scanner read it. A pattern
    that starts with `0` cannot match the leading zeros of a SKU, so the tool
    prints a warning for it.
*   R3.5 [builder] A rule whose category is `Move` or `Uncategorised` is
    allowed but prints a warning, because the output could then not tell a real
    move from a rule.

**Step 4. Reading exports**

*   R4.1 [builder] Files are read as UTF-8 with an optional BOM (`utf-8-sig`)
    and with `newline=""` so CRLF and LF both work. A file that cannot be
    decoded as UTF-8 is exit 2 naming the file.
*   R4.2 [contract] The format is chosen from the header row. Each header cell
    is trimmed; the list must equal `["Scanned At","SKU","Qty","Unit"]`
    (Format A) or `["timestamp","barcode","count","note"]` (Format B) exactly,
    case included. Anything else, including a zero-byte file, is exit 2 with
    the path and the header that was found. A file with a header and no data
    rows is valid and gives no scans (with a warning that it is empty).
*   R4.3 [builder] Rows are read with `csv.reader`. A row with no fields, or
    only empty fields, is a blank line and is ignored. Every other row must have
    exactly 4 fields, or it is skipped as malformed with a warning. [owner] This
    includes a Format B row whose note has an unquoted comma.
*   R4.4 [owner] The SKU (Format A `SKU`, Format B `barcode`) is trimmed. A
    blank SKU skips the row with a warning.
*   R4.5 [owner] Format A time: trimmed, then parsed with
    `datetime.strptime(value, "%d/%m/%Y %H:%M")`. [builder] This also accepts
    unpadded values such as `5/3/2026 9:05`. A value that does not parse, such
    as `31/02/2026 10:00`, skips the row with a warning.
*   R4.6 [owner] Format B time: trimmed, then it must match
    `YYYY-MM-DDTHH:MM:SS` with an optional fraction of 1 to 6 digits (regular
    expression `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?$`) and form a
    real date and time. [builder] Anything else, including a time zone offset or
    `Z`, skips the row with a warning. This keeps every time naive, so times can
    always be compared.
*   R4.7 [owner] Seconds and fractions are dropped, not rounded:
    `14:30:59` becomes `14:30`.
*   R4.8 [owner] Quantity (Format A `Qty`, Format B `count`) is trimmed and
    must match `^[+-]?[0-9]+$`. [builder] So `+5` is accepted and `5.0`, `2.5`
    and blank are skipped with a warning.
*   R4.9 [owner] Format A `Unit` is trimmed and lower-cased; it must be `each`
    or `case`, or the row is skipped with a warning. `qty_each` is `Qty` for
    `each` and `Qty * 12` for `case` (constant `CASE_SIZE = 12`).
*   R4.10 [owner] Format B `qty_each` is `count`. The note is never read.
*   R4.11 [owner] A quantity of 0 is kept as a real scan. [builder] It is
    categorised by the rules and is never part of a move.

**Step 5. Dedup**

*   R5.1 [owner] Two rows are copies of one scan when their scan keys are equal.
    The scanner format does not matter: `1,case` in Format A equals `12` in
    Format B.
*   R5.2 [owner] Dedup only compares exports with the same location name.
*   R5.3 [owner] Identical rows inside one export are separate real scans.
*   R5.4 [owner] For each scan key, let N be the highest number of rows with
    that key in any single export. The output keeps exactly N rows for that
    key: the first N in input order. Example: export 1 has the key twice and
    export 2 has it three times, so N is 3 and the kept rows are both rows of
    export 1 and the first such row of export 2.
*   R5.5 [owner] Each kept row keeps its own `sku` text. Spellings are not
    unified across rows.
*   R5.6 [builder] Dedup runs before move matching, so a scan that appears in
    two exports can only be part of one move.

**Step 6. Moves**

*   R6.1 [owner] A move is one row with `qty_each < 0` and one row with
    `qty_each` equal to its exact opposite, the same normalised SKU, a different
    location name, and minute times at most 120 minutes apart (120 counts).
    Either row may come first in time. Notes are ignored. Constant
    `MOVE_WINDOW_MINUTES = 120`.
*   R6.2 [owner] Negative rows are taken one at a time in scan order. For each,
    the partner is chosen from the positive rows not yet in a move: the one with
    the smallest absolute minute difference; on a tie, the one first in scan
    order. If there is no partner, the negative row is not a move.
*   R6.3 [owner] Each row is in at most one move. Both rows get category `Move`
    and the same `move_id`; the rules are not applied to them.
*   R6.4 [builder] `move_id` is `M` followed by the move's number padded to 4
    digits (`M0001`, `M0002`, ...), numbered in the order the moves are formed in
    R6.2. Past 9999 the number simply gets longer (`M10000`).
*   R6.5 [builder] Greedy matching can leave a pair unmatched that a different
    order would have matched. This is accepted: the rule is fixed, simple to
    explain and deterministic.

**Step 7. Categories**

*   R7.1 [owner] A row that is not part of a move gets the category of the
    first matching rule (R3.3, R3.4), or `Uncategorised` if none matches. Its
    `move_id` is blank.

**Step 8. Order**

*   R8.1 [owner] Output rows are sorted by location name, then normalised SKU,
    then minute time, then input order. [builder] Strings are compared by
    plain Python `str` order (code points), so the order does not depend on the
    machine's locale.

**Step 9. Output**

*   R9.1 [contract] Header `location,sku,qty_each,category,move_id`, always
    written, even with no rows.
*   R9.2 [builder] UTF-8 without a BOM, `\n` line endings, `csv` minimal
    quoting. `qty_each` is written as a plain integer (`-12`, `0`, `24`).
*   R9.3 [builder] The file is written to a temporary file in the folder of
    `--out` and moved into place with `os.replace`. If writing fails, the
    temporary file is removed and the tool exits 2.

### Messages and exit codes

| Situation | Exit | Output file |
| --- | --- | --- |
| Success, with or without skipped rows | 0 | written |
| Usage error (R1.1, R1.2) | 2 | not touched |
| Missing or unreadable input or rules file (R2.1) | 2 | not touched |
| `--out` is an input, or its folder is missing (R2.2) | 2 | not touched |
| Rules header wrong (R3.1) | 2 | not touched |
| Export header unknown, or zero-byte export (R4.2) | 2 | not touched |
| A file is not valid UTF-8 (R4.1) | 2 | not touched |
| Writing the output fails (R9.3) | 2 | not touched |

*   Warnings go to stderr as `stockmerge: warning: PATH:LINE: reason`. LINE is
    the first physical line of the row in the file (1 is the header). Warnings
    not tied to a row omit `:LINE`.
*   Errors go to stderr as `stockmerge: error: message`.
*   On success the tool prints one summary line to stderr:
    `stockmerge: read R rows, removed D duplicates, skipped S rows, linked M moves, wrote W rows`.
*   Nothing is printed to stdout.

### Worked example (dedup, moves, order)

Inputs (`--location` order: `back=b.csv`, `shop=s1.csv`, `shop=s2.csv`):

```text
b.csv  (A)  05/03/2026 10:05, ABC, -6, each
s1.csv (A)  05/03/2026 11:40, abc,  6, each
            05/03/2026 11:40, abc,  6, each
s2.csv (B)  2026-03-05T11:40:30, abc, 6, ""
            2026-03-05T12:10:00, 0042, -1, ""
```

*   Dedup on "shop": key (shop, 11:40, 6, `abc`) has count 2 in s1 and 1 in s2,
    so N = 2: the two s1 rows are kept, the s2 row is removed.
*   Moves: the only negative with a partner is the b.csv row. Both s1 rows are
    candidates at 95 minutes; the tie goes to the first in scan order (s1
    record 0). That pair is `M0001`. The other s1 row stays a normal row. The
    s2 `-1` of `0042` has no partner and is categorised by the rules.
*   Output order: `back` rows first, then `shop` rows sorted by normalised SKU
    (`42` before `abc`).

## Alternatives Considered

### Alternative A: Keep all N survivors from the export with the highest count

*   **Pros**: survivors all come from one file.
*   **Cons**: needs a tie-break between exports with the same count; does not
    match the owner's "earlier `--location` first".
*   **Reason for Rejection**: the owner confirmed "first N in input order".

### Alternative B: One SKU spelling per normalised SKU

*   **Pros**: tidier output.
*   **Cons**: rows would show text that was never scanned for them.
*   **Reason for Rejection**: the owner said each row uses the text of the copy
    that was kept.

### Alternative C: Keep seconds for moves and sorting

*   **Pros**: finer ordering.
*   **Cons**: two time models; Format A has no seconds, so the two scanners
    would behave differently.
*   **Reason for Rejection**: the owner said all comparisons are to the minute.

### Alternative D: Lenient Format B parsing with `datetime.fromisoformat`

*   **Pros**: accepts more ISO variants.
*   **Cons**: in Python 3.11 it accepts time zone offsets, which produce aware
    times that cannot be compared with naive ones and crash move matching.
*   **Reason for Rejection**: a strict shape makes skips predictable and
    testable.

### Alternative E: Match rules against the SKU as written

*   **Pros**: a pattern with leading zeros can match.
*   **Cons**: the same SKU could get different categories depending on which
    scanner read it, since scanner B drops leading zeros.
*   **Reason for Rejection**: categories should not depend on the scanner. A
    warning covers patterns that start with `0`.

### Alternative F: Case-insensitive location names

*   **Pros**: a case typo would not split a location.
*   **Cons**: hides typos rather than reporting them, and changes the name the
    owner typed.
*   **Reason for Rejection**: exact names plus a warning keep the owner's text
    and still show the typo.

### Alternative G: Optimal (maximum) move matching

*   **Pros**: can link more pairs in rare crossing cases.
*   **Cons**: harder to explain and to test; the owner already set a greedy
    order.
*   **Reason for Rejection**: owner-settled greedy rule.

### Alternative H: Write the output directly instead of via a temporary file

*   **Pros**: a few lines less.
*   **Cons**: a failure during the write leaves a half-written file.
*   **Reason for Rejection**: G6.

### Alternative I: csv default `\r\n` line endings

*   **Pros**: matches the csv module default.
*   **Cons**: harder to compare in tests and diffs.
*   **Reason for Rejection**: `\n` is simpler to test byte for byte.

### Alternative J: A `--strict` flag that exits non-zero on skipped rows

*   **Pros**: lets scripts notice bad rows.
*   **Cons**: one more mode to test; the owner wants exit 0 with warnings.
*   **Reason for Rejection**: no stated need. Listed under Future Improvements.

--------------------------------------------------------------------------------

## Non-Functional Requirements

*   **Determinism**: every sort uses a complete key that ends in input order,
    so no two rows ever compare equal. No sets or hash order are used to decide
    output, and no clock, locale or random value is read.
*   **Performance**: stock-take files are small (thousands of rows). Move
    matching groups positives by (normalised SKU, `qty_each`) so each negative
    only looks at its own group. No other tuning.
*   **Safety**: the tool only reads the given files and writes `--out` (and its
    temporary file).

--------------------------------------------------------------------------------

### Additional Resources

*   `BRIEF.md` (fixed contract)
*   `concepts_brief.md` (brainstorm decisions)
*   `stakeholder_log.md` (owner answers)

### Future Improvements

*   A `--strict` flag that exits non-zero when rows were skipped.
*   A totals report per SKU per location.

--------------------------------------------------------------------------------

## Detailed Implementation Plan

### Target Files to Create/Modify

#### 1. `stockmerge/__init__.py` (Create)

*   **Type / Scope**: Python package marker.
*   **Proposed Changes**: Package docstring and `__all__ = []`. No logic.

#### 2. `stockmerge/__main__.py` (Create)

*   **Type / Scope**: Entry point for `python -m stockmerge`.
*   **Proposed Changes**: `from stockmerge.cli import main` then
    `raise SystemExit(main())`. `main(argv: list[str] | None = None) -> int`.

#### 3. `stockmerge/model.py` (Create)

*   **Type / Scope**: Shared types, constants and pure helpers.
*   **Proposed Changes**:
    *   Constants: `CASE_SIZE = 12`, `MOVE_WINDOW_MINUTES = 120`,
        `MOVE_CATEGORY = "Move"`, `UNCATEGORISED = "Uncategorised"`,
        `OUTPUT_HEADER = ["location", "sku", "qty_each", "category", "move_id"]`.
    *   `@dataclass(frozen=True) class Scan` with the fields in the record-type
        table. Property `ident -> tuple[int, int]` returning
        `(arg_index, record_no)`.
    *   `normalise_sku(text: str) -> str`: `text.strip().lower().lstrip("0") or "0"`.
    *   `scan_key(s: Scan) -> tuple`: `(s.location, s.minute, s.qty_each, s.sku_norm)`.
    *   `input_order(s: Scan) -> tuple[int, int]`: `(s.arg_index, s.record_no)`.
    *   `scan_order(s: Scan) -> tuple`: `(s.minute, s.location, s.arg_index, s.record_no)`.
    *   `class StockmergeError(Exception)`: carries a message; the CLI turns it
        into exit 2.
    *   `class Warnings`: collects warning strings in order;
        `add(path: str, line: int | None, reason: str)` formats
        `PATH:LINE: reason` (or `PATH: reason`).

#### 4. `stockmerge/readers.py` (Create)

*   **Type / Scope**: Reading and parsing exports (rules R4.1 to R4.11).
*   **Proposed Changes**:
    *   `FORMAT_A_HEADER = ["Scanned At", "SKU", "Qty", "Unit"]`,
        `FORMAT_B_HEADER = ["timestamp", "barcode", "count", "note"]`.
    *   `read_export(arg_index: int, location: str, path: str, warnings: Warnings) -> list[Scan]`:
        opens with `encoding="utf-8-sig", newline=""`; wraps
        `UnicodeDecodeError` as `StockmergeError`. Reads the first record with
        `csv.reader` as the header; none (zero-byte or only blank) is a
        `StockmergeError`. Trims header cells and looks the list up in
        `PARSERS = {tuple(FORMAT_A_HEADER): parse_a_row, tuple(FORMAT_B_HEADER): parse_b_row}`;
        no match is `StockmergeError(f"{path}: unrecognised header: {raw}")`.
        For each later record: the start line is the reader's `line_num`
        before reading it plus 1; blank records (all fields empty after trim)
        are ignored; others get the next `record_no` and are passed to the
        parser. A parser raises `RowError(reason)`, which is caught and turned
        into a warning. If no scans result, add a warning that the file has no
        valid rows.
    *   `parse_a_row(fields: list[str]) -> tuple[datetime, str, int]` returns
        (minute time, trimmed SKU, `qty_each`). Field count must be 4; SKU must
        be non-blank; time via `strptime("%d/%m/%Y %H:%M")`; quantity via
        `parse_whole`; unit lower-cased in {`each`, `case`}.
    *   `parse_b_row(fields: list[str]) -> tuple[datetime, str, int]`: field
        count 4; barcode non-blank; time via `parse_iso_naive`; count via
        `parse_whole`; note ignored.
    *   `parse_whole(text: str) -> int`: trimmed, must match `^[+-]?[0-9]+$`,
        else `RowError("quantity is not a whole number: ...")`.
    *   `parse_iso_naive(text: str) -> datetime`: regex from R4.6, then
        `datetime.strptime` on the first 19 characters with
        `"%Y-%m-%dT%H:%M:%S"` (the fraction is dropped anyway); a `ValueError`
        becomes `RowError`.
    *   `to_minute(dt: datetime) -> datetime`: `dt.replace(second=0, microsecond=0)`.
    *   `class RowError(Exception)`.

#### 5. `stockmerge/rules.py` (Create)

*   **Type / Scope**: Rules file loading and categorisation (R3.1 to R3.5, R7.1).
*   **Proposed Changes**:
    *   `@dataclass(frozen=True) class Rule: pattern: str; category: str` where
        `pattern` is already lower-cased.
    *   `load_rules(path: str, warnings: Warnings) -> list[Rule]`: `utf-8-sig`,
        `newline=""`; header trimmed must equal `["pattern", "category"]`
        exactly, else `StockmergeError`; decode errors and an empty file are
        `StockmergeError`. Data rows per R3.2; warnings per R3.4 and R3.5.
    *   `categorise(sku_norm: str, rules: list[Rule]) -> str`: first rule with
        `rule.pattern in sku_norm`, else `UNCATEGORISED`.

#### 6. `stockmerge/dedup.py` (Create)

*   **Type / Scope**: Dedup (R5.1 to R5.4).
*   **Proposed Changes**:
    *   `dedup(scans: list[Scan]) -> tuple[list[Scan], int]` returns the kept
        scans in input order and the number removed.
    *   Algorithm: count rows per `(scan_key, arg_index)`; for each scan key,
        N = the largest of those counts (location is part of the key, so only
        exports of one location are compared). Walk scans in input order with
        a counter per scan key; keep a scan while its key's counter is below N,
        then increment.

#### 7. `stockmerge/moves.py` (Create)

*   **Type / Scope**: Move linking (R6.1 to R6.5).
*   **Proposed Changes**:
    *   `link_moves(scans: list[Scan]) -> dict[tuple[int, int], str]` maps
        `Scan.ident` to `move_id` for every row in a move.
    *   Algorithm: group positive scans by `(sku_norm, qty_each)`. Sort
        negatives by `scan_order`. For each negative, look in group
        `(sku_norm, -qty_each)` for scans not yet used whose location differs
        and whose minute difference is at most `MOVE_WINDOW_MINUTES`; choose
        the minimum by `(abs(minute difference in whole minutes), scan_order)`.
        Number moves from 1 in this loop; `move_id = f"M{n:04d}"`.

#### 8. `stockmerge/writer.py` (Create)

*   **Type / Scope**: Output (R8.1, R9.1 to R9.3).
*   **Proposed Changes**:
    *   `build_rows(scans, move_ids, rules) -> list[list[str]]`: sorts scans by
        `(location, sku_norm, minute, arg_index, record_no)`; for each, the
        category is `MOVE_CATEGORY` if its ident is in `move_ids`, else
        `categorise(...)`; `move_id` is the mapped id or `""`.
    *   `write_csv(out_path: str, rows) -> None`: `tempfile.NamedTemporaryFile`
        with `mode="w"`, `encoding="utf-8"`, `newline=""`, `dir` = folder of
        `out_path`, `delete=False`; `csv.writer(f, lineterminator="\n")`;
        header then rows; flush, close, `os.replace`. On any `OSError`,
        remove the temporary file and raise `StockmergeError`.

#### 9. `stockmerge/cli.py` (Create)

*   **Type / Scope**: Command line layer (R1.x, R2.x, messages table).
*   **Proposed Changes**:
    *   `build_parser() -> argparse.ArgumentParser` with `prog="stockmerge"`,
        `allow_abbrev=False`, required subparsers with only `merge`
        (`allow_abbrev=False`); `--location` `action="append"`, `required=True`;
        `--rules` and `--out` required. argparse already exits 2 on usage
        errors.
    *   `parse_location(value: str) -> tuple[str, str]` per R1.2; raises
        `StockmergeError`.
    *   `main(argv=None) -> int`: parse; build the export list
        `[(arg_index, name, path)]`; warnings per R1.4 and R1.5; path checks
        per R2.1 and R2.2; `load_rules`; `read_export` for each export;
        `dedup`; `link_moves`; `build_rows`; `write_csv`. Prints each warning
        as `stockmerge: warning: ...` to stderr as it is collected, then the
        summary line. Catches `StockmergeError`, prints
        `stockmerge: error: ...`, returns 2. Returns 0 on success.

#### 10. `tests/conftest.py` (Create)

*   **Type / Scope**: Test helpers.
*   **Proposed Changes**: fixture `write_file(tmp_path)` that writes text
    (or bytes) to a named file and returns its path; helper `run_cli(args)`
    that calls `subprocess.run([sys.executable, "-m", "stockmerge", ...])` with
    `cwd` set to the repo root and returns (exit code, stdout, stderr); helper
    `read_out(path)` that parses the output CSV into a list of dicts.

#### 11. `tests/test_readers.py` (Create)

*   **Type / Scope**: Unit tests for R4.x.
*   **Proposed Changes**: Format A and B detection; trimmed header cells;
    unknown header and zero-byte file raise; header-only file gives no scans
    and a warning; BOM and CRLF accepted; `case` gives ×12 and `-1,case` gives
    -12; unit `Case ` accepted; bad unit skipped; `5.0`, `2.5`, blank quantity
    skipped; `+5` accepted; `31/02/2026` skipped; `5/3/2026 9:05` accepted;
    Format B `Z`, `+01:00`, date-only skipped; fraction accepted; seconds
    truncated (`14:30:59` to 14:30); unquoted comma in note skipped; blank SKU
    skipped; blank line ignored without a warning; warning line numbers;
    invalid UTF-8 raises.

#### 12. `tests/test_rules.py` (Create)

*   **Type / Scope**: Unit tests for R3.x and R7.1.
*   **Proposed Changes**: header check; first match in file order wins;
    case-insensitive substring; matching against normalised SKU (`00ABC` with
    pattern `abc`); no match gives `Uncategorised`; blank pattern or category
    skipped with a warning; warnings for patterns starting with `0` and for
    categories `Move`/`Uncategorised`.

#### 13. `tests/test_dedup.py` (Create)

*   **Type / Scope**: Unit tests for R5.x.
*   **Proposed Changes**: identical rows in one export all kept; 2 vs 1 keeps
    2; 2 vs 3 keeps 3 with both export-1 rows plus the first export-2 row;
    Format A `1,case` equals Format B `12`; `00123` equals `123`; same minute
    with different seconds are one key; different locations are never deduped;
    removed count is correct; each kept row keeps its own `sku` text.

#### 14. `tests/test_moves.py` (Create)

*   **Type / Scope**: Unit tests for R6.x.
*   **Proposed Changes**: basic pair; positive before negative; exactly 120
    minutes links and 121 does not; 10:00:59 and 12:00:30 link (minute times);
    same location never links; different quantity never links; closest
    partner wins; tie broken by scan order; each row used once; negatives
    processed in scan order; `move_id` numbering `M0001`, `M0002`; zero
    quantity never links.

#### 15. `tests/test_cli.py` (Create)

*   **Type / Scope**: End-to-end tests through `python -m stockmerge`.
*   **Proposed Changes**: CUJ 1 to CUJ 5; header written with no rows; output
    order; `\n` line endings and no BOM in output; byte-identical output on two
    runs; exit 2 and no output file for: unknown header, missing input, missing
    rules file, wrong rules header, `--location` without `=`, empty name,
    `--out` equal to an input; an existing `--out` is unchanged after an exit-2
    run; warnings on stderr with the `stockmerge: warning:` prefix; summary
    line counts; nothing on stdout.

#### 16. `pyproject.toml` (Create)

*   **Type / Scope**: Project metadata and pytest config.
*   **Proposed Changes**: `[project]` name `stockmerge`,
    `requires-python = ">=3.11"`, no dependencies;
    `[tool.pytest.ini_options] testpaths = ["tests"]`.

#### 17. `README.md` (Create)

*   **Type / Scope**: User documentation.
*   **Proposed Changes**: what the tool does, the command line, the two input
    formats, the rules file, the output columns, the exit codes and warning
    format, and a short list of the builder's calls (R-IDs marked [builder]).

#### 18. `.gitignore` (Create)

*   **Type / Scope**: Repo hygiene.
*   **Proposed Changes**: `__pycache__/`, `.pytest_cache/`, `*.pyc`.

### Verification Plan

*   **Compilation/Build**: none; `python -m stockmerge merge --help` runs.
*   **Unit Tests**: `python -m pytest` from the repo root passes.
*   **Static Analysis & Linting**: none required (standard library only).
*   **Test Coverage Requirement**: at least one test per rule ID marked
    [owner] or [contract].
*   **E2E/Integration**: `tests/test_cli.py` runs the real module in a
    subprocess.

--------------------------------------------------------------------------------

*Drafted with EGM*
