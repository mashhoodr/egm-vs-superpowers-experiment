# stockmerge: merge overlapping stock-take scans into one inventory

*   **Author:** EGM Elephant
*   **Status:** Approved
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
at another. The tool must remove the overlap without collapsing repeated
scans inside one export (the one case it cannot tell apart is listed under
Risks & Limits), and must recognise moves under a fixed,
deterministic rule (R6.1, R6.2).

The two scanners do not write SKUs the same way. The owner reports that
scanner B drops leading zeros (`00123` from scanner 1 is `123` from scanner 2),
and SKU case and outer spaces can differ. So two rows can be the same scan,
or the two halves of a move, even when their SKU text differs. The tool
compares a normalised SKU (see Glossary) and writes the original text.

The fixed contract in `BRIEF.md` (command line, input headers, rules header,
output header, exit 0 on success) cannot change. Everything below works inside
it.

## Goals

*   **G1 Dedup without loss.** Copies of a scan across exports of one location
    are removed: the output keeps as many rows of a scan as the highest count
    of it in any one export, so repeated identical rows inside one export are
    never collapsed.
*   **G2 Moves.** A stock-out and its matching stock-in at another location are
    linked with one shared `move_id` and the category `Move`.
*   **G3 Categories.** Every row that is not part of a move gets a category from
    the rules file, or `Uncategorised`.
*   **G4 Determinism.** The same arguments and the same input bytes give a
    byte-identical output file.
*   **G5 Every row is accounted for.** Each data row is either written, removed
    as a counted duplicate, or skipped with a warning that names the file and
    line. No input file, argument or file system error ends in a traceback:
    each one is either a skipped row (exit 0) or an error message (exit 2).
    A traceback for any other reason is a bug in the tool.
*   **G6 Failed runs change nothing.** When the tool exits 2, the `--out` file is
    not created and an existing one is not changed.

## Non-Goals

*   Totals per SKU per location. The brief's "inventory, per SKU per
    location" is met by each row carrying its location and SKU; the fixed
    output contract is one row per kept scan, and the owner confirmed that.
    Adding a totals report is out of scope (a builder's call).
*   Time zones or daylight saving. All times are shop local time from one clock.
*   Clean handling of Ctrl-C. An interrupt may print a traceback and leave a
    temporary file next to `--out`; `--out` itself is never half-written.
*   Comparing times more precisely than the minute.
*   Dedup across different location names: exports of two different
    locations are never compared for copies. (Move linking does compare SKUs
    across locations; that is G2, not dedup.)
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

None are open. Every behaviour question was answered by the owner or
recorded as a builder's call in [`concepts_brief.md`](../../concepts_brief.md)
and [`stakeholder_log.md`](../../stakeholder_log.md) at the repo root.

## Glossary

*   **Owner**: the shop owner who wrote `BRIEF.md` and answered the questions
    in `stakeholder_log.md`.
*   **Builder**: whoever designs and writes the tool.
*   **Decision tags**: each rule below carries one or more tags saying who
    decided it. **[contract]**: fixed by `BRIEF.md`. **[owner]**: the owner
    decided it when asked. **[builder]**: the owner left it to the builder,
    so the owner can overrule it. A tag covers the text after it, up to the
    next tag or the end of the bullet.

*   **Export**: one `--location NAME=PATH` argument and the file it names.
*   **Argument index**: the position of an export among the `--location`
    arguments, starting at 0.
*   **Record number**: the position of a data row within its file, starting at
    0, counting every non-blank row after the header, including rows later
    skipped with a warning. Blank lines do not get a number.
*   **Input order**: sort by (argument index, record number).
*   **Trim**: remove leading and trailing whitespace with `str.strip()`.
    Wherever this document says "trimmed" or "outer spaces", it means this.
*   **Minute time**: a scan's timestamp with seconds and fractions dropped (not
    rounded). Every time comparison uses minute time.
*   **Normalised SKU**: the SKU text with outer whitespace removed
    (`str.strip()`), lower-cased,
    and leading `0` characters removed. If nothing is left, it is `0`. So
    `00123`, `123` and ` 123 ` are the same SKU, and `000` is `0`.
*   **Scan key**: (location name, minute time, `qty_each`, normalised SKU).
*   **Copy / duplicate / dedup**: rows with equal scan keys in different
    exports of one location are copies (also called duplicates) of one scan.
    Dedup is step 5, which removes the extra copies.
*   **Scan order**: sort by (minute time, location name, input order).

## Critical User Journeys (CUJs)

### CUJ 1: Two overlapping exports of one location

*   **Given**: `shop.csv` (Format A) and `shop2.csv` (Format B) are both exports
    of "shop floor". Both contain the same scan, written differently:
    `shop.csv` has `05/03/2026 14:30,00123,1,case` twice (two shelves), and
    `shop2.csv` has `2026-03-05T14:30:41,123,12,` three times.
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

The tool is a straight pipeline over one record type. Steps 3, 4 and 9 open
files; steps 5 to 8 are pure functions over in-memory lists. Warnings go to
stderr as they are found. Only the command line layer chooses the exit code.

```text
argv
  │
  ▼
[1 parse args] ──usage error──► exit 2
  │ exports: [(arg_index, name, path)], rules path, out path
  ▼
[2 check --out]   ──--out is an input or the rules file──► exit 2
  │
  ▼
[3 load rules] ──bad or missing header──► exit 2
  │ rules: [(pattern_lower, category)]      bad row ──► warning
  ▼
[4 read exports] ──unknown or missing header──► exit 2
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
is how G6 holds: every input-related exit-2 condition is found before step 9
starts, and step 9 writes to a temporary file that only replaces `--out` once
it is complete, so a failure inside step 9 also leaves `--out` untouched.

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

Rule IDs are used by the tests. Tags are defined in the Glossary.

#### Step 1. Command line

*   R1.1 [contract] `merge` is the only subcommand and is required.
    `--location` may repeat and is required at least once; `--rules` and
    `--out` are required. [builder] Abbreviated options are not accepted.
    Usage errors use the standard argparse format
    (`usage: stockmerge merge ...` then `stockmerge merge: error: ...`) with
    exit 2. `--help` prints to stdout and exits 0; it is the only case that
    writes to stdout.
*   R1.2 [builder] `--location` splits on the first `=`. The name and the path
    are each trimmed of outer spaces. A missing `=`, an empty name, an empty
    path, or a name that cannot be written as UTF-8 (a command line argument
    with invalid bytes) is a usage error: exit 2. This keeps step 9 from
    failing on an unencodable location name.
*   R1.3 [builder] The same NAME may appear with several PATHs. The same PATH
    may appear twice for one NAME; it is read twice as two exports, and dedup
    makes the second copy add nothing.
*   R1.4 [builder] Location names are compared exactly as written after
    trimming, so `Shop Floor` and `shop floor` are two locations. If two names
    are equal after lower-casing and collapsing each run of spaces to one
    space (so `Shop  Floor` and `shop floor`), print a warning naming both,
    because this can be a typo that turns off dedup and creates false
    moves.
*   R1.5 [builder] If the same file (compared as in R2.2) appears under two
    different names, print a warning.

#### Step 2. Output path check

*   R2.1 [builder] There is no separate existence check. A missing,
    unreadable or non-file input or rules path is found when step 3 or 4 opens
    it: the `OSError` is turned into exit 2 with a message naming the path.
*   R2.2 [builder] `--out` must not be the same file as any input or the
    rules file; otherwise exit 2.
    *   Two paths are the same file when they resolve to the same path after
        following links, or, when both exist, when the operating system
        reports them as the same file (this catches hard links and letter
        case on a case-insensitive disk). If that check itself fails, the
        paths count as different.
    *   This is the only check made before reading: reading would not catch
        it, and writing would destroy an input.
    *   A missing `--out` folder is found when step 9 creates its temporary
        file, which is still exit 2 with `--out` untouched.

#### Step 3. Rules file

*   R3.1 [contract] The header is `pattern,category`. [builder] A UTF-8 BOM
    and spaces around each cell are ignored; anything else is exit 2.
*   R3.2 [builder] The rules file is read with the same encoding, blank-line,
    header-row and line handling as an export (R4.1, R4.3, R4.12).
    A file with no header row is exit 2. A header with no rules is valid;
    every row is then `Uncategorised`. Each data row must have exactly 2
    fields (not 4). Both
    are trimmed. A row with the wrong field count, a blank pattern or a blank
    category is skipped with a warning.
*   R3.3 [owner] A pattern matches when it is a substring of the SKU, ignoring
    case. Rules are tried in file order; the first match wins.
*   R3.4 [builder] The pattern is lower-cased and compared with the normalised
    SKU, so a SKU gets the same category whichever scanner read it. A pattern
    that starts with `0` cannot match the leading zeros of a SKU, so the tool
    prints a warning for it.
*   R3.5 [builder] A rule whose category is `Move` or `Uncategorised` is
    allowed but prints a warning, because the output could not then tell a real
    move apart from a rule match.

#### Step 4. Reading exports

*   R4.1 [builder] Files are read as UTF-8 with an optional BOM, and both CRLF and LF line endings work. Bytes that are not valid UTF-8 do
    not stop the run. A data row with such a byte in a field the
    tool reads (all four Format A fields; Format B `timestamp`, `barcode`
    and `count`) is skipped with the warning `PATH:LINE: not valid UTF-8`.
    Such a byte in the Format B `note` does not matter, because the note is
    never read. A header row with
    such a byte does not match either format, so it is exit 2 (R4.2).
*   R4.2 [contract] The format is chosen from the header row. [builder] Each
    header cell is trimmed; the list must equal `["Scanned At","SKU","Qty","Unit"]`
    (Format A) or `["timestamp","barcode","count","note"]` (Format B) exactly,
    case included. Anything else is exit 2 with the path and the header that
    was found. A file with no header row at all (zero bytes, or only blank
    lines) is exit 2. A file with a header row is valid even if it gives no
    scans (no data rows, or every row skipped); it then gets the warning
    `PATH: no valid rows`.
*   R4.3 [builder] Rows are read with `csv.reader`. A row with no fields, or
    whose fields are all empty after trimming spaces, is a blank line and is
    ignored. Blank lines before the header row are skipped too; the first
    non-blank row is the header. Every other row must have
    exactly 4 fields, or it is skipped as malformed with a warning. [owner] This
    includes a Format B row whose note has an unquoted comma.
*   R4.4 [owner] The SKU (Format A `SKU`, Format B `barcode`) is trimmed. A
    blank SKU skips the row with a warning.
*   R4.5 [contract] Format A time is `DD/MM/YYYY HH:MM`. [builder] It is
    trimmed first, and unpadded values such as `5/3/2026 9:05` are also
    accepted. A value that does not parse, such
    as `31/02/2026 10:00`, skips the row with a warning.
*   R4.6 [contract] Format B time is ISO 8601. [builder] It is trimmed, then
    the whole value must match `YYYY-MM-DDTHH:MM:SS` with an optional fraction
    of 1 to 6 digits, using ASCII digits only, and form a real date and
    time. [builder] Anything else, including a time zone offset or
    `Z`, skips the row with a warning. This keeps every time naive, so times can
    always be compared.
*   R4.7 [owner] Seconds and fractions are dropped, not rounded:
    `14:30:59` becomes `14:30`.
*   R4.8 [owner] A quantity (Format A `Qty`, Format B `count`) that is not a
    whole number skips the row with a warning. [builder] After trimming it
    must be an optional `+` or `-` followed by 1 to 9 ASCII digits. So `+5`
    is accepted, and `5.0`, `2.5`, blank and values of more than 9 digits
    are skipped. (The digit limit also stops very long values from raising
    an error inside Python's integer conversion.)
*   R4.9 [owner] Format A `Unit` must be `each` or `case`, or the row is
    skipped with a warning. [builder] It is trimmed and lower-cased first. `qty_each` is `Qty` for
    `each` and `Qty * 12` for `case` (constant `CASE_SIZE = 12`).
*   R4.10 [owner] Format B `qty_each` is `count`. Notes are ignored for
    moves. [builder] The note is never read for any purpose.
*   R4.11 [builder] A quantity of 0 is kept as a real scan. It is
    categorised by the rules and is never part of a move.
*   R4.12 [builder] Each physical line is one record. A quoted field cannot
    continue onto the next line. This matters because an unclosed `"` in a
    free-text note would otherwise join every following line into one
    record and hide real scans. With this rule, the line with the unclosed
    quote still gives 4 fields (its note runs to the end of that line), and
    every later line is read normally. A note that really contains a line
    break is split; its continuation lines are skipped as malformed, each
    with a warning. Very long lines are accepted (no field size limit).

#### Step 5. Dedup

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

#### Step 6. Moves

*   R6.1 [owner] A move is one row with `qty_each < 0` and one row with
    `qty_each` equal to its exact opposite, the same normalised SKU, a different
    location name, and minute times at most 120 minutes apart (120 counts).
    Either row may come first in time. Notes are ignored.
*   R6.2 [owner] Negative rows are taken one at a time in scan order. For each,
    the partner is chosen from the positive rows not yet in a move: the one with
    the smallest absolute minute difference; on a tie, the one first in scan
    order. If there is no partner, the negative row is not a move.
*   R6.3 [owner] Each row is in at most one move. Both rows get category `Move`
    and the same `move_id`; the rules are not applied to them. (Owner, round
    1: "Both rows get the same move_id and the category `Move`, and the rules
    are not applied to move rows. Each row can belong to only one move.")
*   R6.4 [builder] `move_id` is `M` followed by the move's number padded to 4
    digits (`M0001`, `M0002`, ...), numbered in the order the moves are formed in
    R6.2. Past 9999 the number has more digits (`M10000`).
*   R6.5 [owner] Matching is greedy. It can leave a pair unmatched that a
    different order would have matched: when negative N1 takes positive P1,
    and P1 was the only partner of a later negative N2, N2 is left without a
    move even if N1 also had another partner P2. This is accepted: the rule
    is fixed by the owner and deterministic.

#### Step 7. Categories

*   R7.1 [owner] A row that is not part of a move gets the category of the
    first matching rule (R3.3, R3.4), or `Uncategorised` if none matches. Its
    `move_id` is blank.

#### Step 8. Order

*   R8.1 [owner] Output rows are sorted by location name, then normalised SKU,
    then minute time, then input order. [builder] Strings are compared by
    plain Python `str` order (code points), so the order does not depend on the
    machine's locale.

#### Step 9. Output

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
| Missing or unreadable input or rules file (R2.1, found on open) | 2 | not touched |
| `--out` is an input or the rules file (R2.2) | 2 | not touched |
| `--out` folder missing or not writable (R9.3) | 2 | not touched |
| Any other `OSError`, `UnicodeError` or `csv.Error` (backstop in the command line layer, G5) | 2 | not touched |
| Rules header wrong, rules file has no header row, or rules header not valid UTF-8 (R3.1, R3.2) | 2 | not touched |
| Export header unknown, or no header row (R4.2) | 2 | not touched |
| A header row is not valid UTF-8 (R4.1, R4.2) | 2 | not touched |
| Writing the output fails (R9.3) | 2 | not touched |

*   Warnings go to stderr as `stockmerge: warning: PATH:LINE: reason`. LINE is
    the first physical line of the row in the file (1 is the header). Warnings
    about a whole file omit `:LINE`. Warnings about the command line (R1.4,
    R1.5) have no PATH: `stockmerge: warning: reason`.
*   Warnings are printed to stderr as soon as they are found, so warnings
    found before an exit-2 error are still shown.
*   Errors go to stderr as `stockmerge: error: message`.
*   On success the tool prints one summary line to stderr:
    `stockmerge: read R rows, removed D duplicates, skipped S rows, linked M moves, wrote W rows`.
    The wording is fixed and always uses the plural (`linked 1
    moves`, never `linked 1 move`), so scripts can parse it. The counts
    cover export files only, not the rules file:
    *   R = data records read from all exports, excluding blank lines and
        header rows (valid and skipped alike).
    *   S = records skipped with a warning.
    *   D = valid scans removed by dedup.
    *   M = number of moves (pairs), so `2 × M` rows have category `Move`.
    *   W = rows written. Always `W = R - S - D`.
*   Nothing is printed to stdout.

### Worked example (dedup, moves, order)

Inputs, as a summary of the data rows (header rows left out; `--location`
order: `back=b.csv`, `shop=s1.csv`, `shop=s2.csv`):

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
    (`42` before `abc`), then minute time, then input order.

With a rules file containing one rule, `42,Spares`, the output is:

```text
location,sku,qty_each,category,move_id
back,ABC,-6,Move,M0001
shop,0042,-1,Spares,
shop,abc,6,Move,M0001
shop,abc,6,Uncategorised,
```

and stderr ends with
`stockmerge: read 5 rows, removed 1 duplicates, skipped 0 rows, linked 1 moves, wrote 4 rows`.

## Alternatives Considered

### Alternative A: Keep all N survivors from the export with the highest count

*   **Pros**: survivors all come from one file.
*   **Cons**: needs a tie-break between exports with the same count; does not
    match the owner's answer that the copies kept are the first ones by
    `--location` argument order (`stakeholder_log.md`, round 3, Q1).
*   **Reason for Rejection**: the owner confirmed "first N in input order".

### Alternative B: One SKU spelling per normalised SKU

*   **Pros**: each normalised SKU appears with one spelling in the output.
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

*   **Pros**: links the most pairs, including the case described in R6.5.
*   **Cons**: needs a matching algorithm whose result is harder to predict by
    hand; the owner already set a greedy order.
*   **Reason for Rejection**: owner-settled greedy rule.

### Alternative H: Write the output directly instead of via a temporary file

*   **Pros**: no temporary-file handling.
*   **Cons**: a failure during the write leaves a half-written file.
*   **Reason for Rejection**: G6.

### Alternative I: csv default `\r\n` line endings

*   **Pros**: matches the csv module default.
*   **Cons**: none that matter for correctness.
*   **Reason for Rejection**: builder preference: `\n` matches the line
    endings of the test files and of most shells and diff tools.

### Alternative J: A `--strict` flag that exits non-zero on skipped rows

*   **Pros**: lets scripts notice bad rows.
*   **Cons**: one more mode to test; the owner wants exit 0 with warnings.
*   **Reason for Rejection**: no stated need. Listed under Future Improvements.

### Alternative K: Other ways to handle a record that spans several lines

*   **Pros**: skipping the whole span with one warning is the simplest;
    `csv` strict mode (exit 2 on a bad quote) never guesses; re-reading each
    line with quoting turned off never joins lines.
*   **Cons**: skipping the span drops every real scan on the swallowed lines,
    against "never lose a real scan"; strict mode stops the whole run for one
    bad note; quoting turned off splits correctly quoted fields such as
    `"a, b"` into two fields, so those scans are skipped.
*   **Reason for Rejection**: reading each physical line as one record with
    normal quoting (R4.12) keeps every scan that fits on one line and warns
    about the rest, with no special detection step.

### Alternative L: Other ways to handle bytes that are not valid UTF-8

*   **Pros**: exiting 2 on any bad byte is the simplest rule; skipping any
    row with a bad byte anywhere is one check instead of a per-field one.
*   **Cons**: exiting 2 throws away the whole run for one bad byte; skipping
    on a bad byte in the ignored note drops a real scan.
*   **Reason for Rejection**: R4.1 skips a row only when the bad byte is in a
    field the tool reads, which is the only option that loses no real scan
    and still never writes broken text.

--------------------------------------------------------------------------------

## Risks & Limits

| Risk | Impact | Mitigation | Rule | Decided by |
| --- | --- | --- | --- | --- |
| Two real scans of the same SKU and quantity in the same minute at one location, one in each of two exports | Treated as one scan; one is removed | Accepted: this is the owner's definition of "same scan" | R5.1, R5.4 | owner |
| A real write-off is paired with an unrelated stock-in of the same SKU and opposite quantity within 2 hours | Shrinkage shown as a move | Accepted: owner's move rule; both rows are visible with category `Move` and a shared id | R6.1 | owner |
| Two different SKUs that differ only by leading zeros (`0123` and `123`) | Treated as one SKU | Accepted: owner said scanner B drops leading zeros | Glossary | owner |
| Location name typo (`Shop floor` vs `shop floor`) | Dedup turned off between them; false moves possible | Warning | R1.4 | builder |
| Unclosed quote in a note | Could join following lines into one record | Each physical line is one record | R4.12 | builder |
| Trailing empty column in a header or rows (`Scanned At,SKU,Qty,Unit,`) | Header: exit 2. Rows: skipped | Accepted: the header must list exactly the contract's columns; the error names the header found | R4.2, R4.3 | builder |
| Cell text starting with `=`, `+`, `-` or `@` opened in a spreadsheet | May be read as a formula | Accepted: the output must keep the scanned text unchanged | R5.5, R9.2 | builder |
| A very large input, or one SKU with very many scans of one quantity | Memory use grows with input; move matching slows in proportion to the size of a (SKU, quantity) group | Accepted: no size was given in the brief; an index can be added later if a real file needs it | NFR | builder |
| The input formats are known only from `BRIEF.md`; no real export was available | A real export with an extra column or another date shape is rejected or has its rows skipped | Accepted: every rejection names the file and header or line, so a mismatch is visible on the first run | R4.2 to R4.9 | builder |
| Every row of a file is skipped | The run still exits 0 | Accepted: the owner chose skip-and-warn with exit 0; the `PATH: no valid rows` warning and the summary's S count show it | R4.2 | owner |
| `--out` names an input | The input would be destroyed | Exit 2 before reading | R2.2 | builder |
| Failure while writing | Half-written output | Write to a temporary file, then move it into place | R9.3 | builder |

--------------------------------------------------------------------------------

## Non-Functional Requirements

*   **Determinism**: every sort uses a complete key that ends in input order,
    so no two rows ever compare equal. No sets or hash order are used to decide
    output, and no clock, locale or random value affects the output content
    (the temporary file's random name is not part of the output).
*   **Performance**: [builder] no size was given; a stock-take is assumed
    to fit in memory. Move matching groups positives by (normalised SKU,
    `qty_each`), and each negative checks only the positives of its own
    group, so the cost per negative is the size of that group. No other
    tuning (see Risks & Limits).
*   **Safety**: the tool only reads the given files and writes `--out` (and its
    temporary file).

--------------------------------------------------------------------------------

## Additional Resources

*   [`BRIEF.md`](../../BRIEF.md) (fixed contract)
*   [`concepts_brief.md`](../../concepts_brief.md) (brainstorm decisions)
*   [`stakeholder_log.md`](../../stakeholder_log.md) (owner answers)

## Future Improvements

*   A `--strict` flag (Alternative J).
*   A totals report per SKU per location.

--------------------------------------------------------------------------------

## Detailed Implementation Plan

### Phases

Build in this order. Each phase ends with a checkpoint that must pass before
the next phase starts.

| Phase | Files | Checkpoint |
| --- | --- | --- |
| P1 Model | `stockmerge/__init__.py`, `stockmerge/model.py`, `tests/conftest.py`, `tests/test_model.py`, `pyproject.toml`, `.gitignore` | `python -m pytest tests/test_model.py` passes |
| P2 Reading | `stockmerge/readers.py`, `tests/test_readers.py` | `python -m pytest tests/test_readers.py` passes |
| P3 Rules | `stockmerge/rules.py`, `tests/test_rules.py` | `python -m pytest tests/test_rules.py` passes |
| P4 Dedup and moves | `stockmerge/dedup.py`, `stockmerge/moves.py`, `tests/test_dedup.py`, `tests/test_moves.py` | both test files pass |
| P5 Output and CLI | `stockmerge/writer.py`, `stockmerge/cli.py`, `stockmerge/__main__.py`, `tests/test_writer.py`, `tests/test_cli.py` | `python -m pytest` passes; the worked example gives exactly the output shown in the Technical Plan |
| P6 Docs | `README.md` | `python -m pytest` still passes; the README names every [builder] rule ID and shows the worked example's command and output |

### Target Files to Create/Modify

#### 1. `stockmerge/__init__.py` (Create)

*   **Type / Scope**: Python package marker.
*   **Proposed Changes**: Package docstring and `__all__ = []`. No logic.

#### 2. `stockmerge/__main__.py` (Create)

*   **Type / Scope**: Entry point for `python -m stockmerge`.
*   **Proposed Changes**: `from stockmerge.cli import main` then
    `raise SystemExit(main())`.

#### 3. `stockmerge/model.py` (Create)

*   **Type / Scope**: Shared types, constants and pure helpers.
*   **Proposed Changes**:
    *   Constants: `CASE_SIZE = 12`, `MOVE_WINDOW_MINUTES = 120`,
        `MOVE_CATEGORY = "Move"`, `UNCATEGORISED = "Uncategorised"`,
        `OUTPUT_HEADER = ["location", "sku", "qty_each", "category", "move_id"]`.
    *   `@dataclass(frozen=True) class Scan` with fields in this order:
        `location: str`, `arg_index: int`, `record_no: int`, `path: str`,
        `line: int`, `minute: datetime`, `sku: str`, `sku_norm: str`,
        `qty_each: int`. Property `ident -> tuple[int, int]` returning
        `(arg_index, record_no)`.
    *   `normalise_sku(text: str) -> str`:
        `text.strip().lower().lstrip("0") or "0"`.
    *   `scan_key(s) -> tuple`: `(s.location, s.minute, s.qty_each, s.sku_norm)`.
    *   `input_order(s) -> tuple[int, int]`: `(s.arg_index, s.record_no)`.
    *   `scan_order(s) -> tuple`: `(s.minute, s.location, s.arg_index, s.record_no)`.
    *   `output_order(s) -> tuple`:
        `(s.location, s.sku_norm, s.minute, s.arg_index, s.record_no)`.
    *   `class StockmergeError(Exception)`: carries a message; the CLI prints
        `stockmerge: error: <message>` and returns 2.
    *   `class Warnings`: the only code that prints warnings.
        `__init__(self, stream=None)`; when `stream` is `None`, each `add`
        writes to the current `sys.stderr` (looked up at write time, so
        pytest's `capsys` sees it).
        `add(path: str | None, line: int | None, reason: str) -> None` builds
        `PATH:LINE: reason`, `PATH: reason` or `reason` (parts that are
        `None` are left out), writes `stockmerge: warning: <text>\n` to the
        stream at once, and appends the text to `self.messages` (a list,
        used by unit tests only). It does not count skipped rows; the S
        count comes from `read_export` (see file 4).

#### 4. `stockmerge/readers.py` (Create)

*   **Type / Scope**: Reading files and parsing exports (R4.1 to R4.12).
*   **Proposed Changes**:
    *   `FORMAT_A_HEADER = ("Scanned At", "SKU", "Qty", "Unit")`,
        `FORMAT_B_HEADER = ("timestamp", "barcode", "count", "note")`.
    *   `ISO_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?")`,
        always used with `ISO_RE.fullmatch(text)`.
        `WHOLE_RE = re.compile(r"[+-]?[0-9]{1,9}")`, used with `fullmatch`.
        Explicit `[0-9]` (not `\d`) so only ASCII digits match.
    *   `class RowError(Exception)`: a row-level problem; its message is the
        warning reason.
    *   At import, the module calls `csv.field_size_limit(2**31 - 1)` (R4.12),
        so the limit is raised for unit tests as well as the CLI.
    *   `open_text(path: str) -> TextIO`: `open(path, encoding="utf-8-sig",
        errors="surrogateescape", newline="")`; an `OSError` becomes
        `StockmergeError(f"{path}: cannot read file: {exc.strerror}")`.
    *   `iter_records(path: str) -> tuple[list[str], list[tuple[int, list[str]]]]`:
        the one shared reader, used by `read_export` and `load_rules`. It
        reads the whole file before returning (stock-take files are small)
        and closes it. Opens with `open_text`, goes through the physical
        lines (`for line_no, line in enumerate(f, start=1)`), splits each with
        `next(csv.reader([line]), [])` (R4.12), and skips blank records (no
        fields, or all fields empty after `strip()`). The first non-blank
        record is the header; its cells are trimmed and returned as the
        first value. If there is none, raise
        `StockmergeError(f"{path}: no header row")`. The second value is the
        list of `(line_no, fields)` for each later non-blank record.
    *   `has_bad_bytes(fields: list[str]) -> bool`: true if any character is
        in the range `"\udc80"` to `"\udcff"` (left by `surrogateescape`).
    *   `read_export(arg_index: int, location: str, path: str, warnings: Warnings) -> tuple[list[Scan], int, int]`:
        returns (scans, records read, records skipped).
        1. `header, records = iter_records(path)`.
        2. Look up `tuple(header)` in
           `PARSERS = {FORMAT_A_HEADER: parse_a_row, FORMAT_B_HEADER: parse_b_row}`.
           No match: `StockmergeError(f"{path}: unrecognised header: {','.join(header)}")`.
        3. For each `(line_no, fields)`, `record_no` counts from 0. Call the
           parser; on `RowError(reason)` call
           `warnings.add(path, line_no, reason)` and count it as skipped.
           Otherwise build the `Scan` with `sku_norm = normalise_sku(sku)`.
        4. If no scans were built, `warnings.add(path, None, "no valid rows")`.
    *   `parse_a_row(fields) -> tuple[datetime, str, int]` returns (minute
        time, trimmed SKU, `qty_each`). Checks, in this order, each raising
        `RowError` with the quoted reason:
        1. `len(fields) != 4` → `"expected 4 fields, found N"`.
        2. `has_bad_bytes(fields)` → `"not valid UTF-8"`.
        3. blank SKU → `"blank SKU"`.
        4. `datetime.strptime(fields[0].strip(), "%d/%m/%Y %H:%M")` fails →
           `"bad date: <value>"`.
        5. quantity via `parse_whole(fields[2])`.
        6. unit `fields[3].strip().lower()` not in {`each`, `case`} →
           `"bad unit: <value>"`. `case` multiplies by `CASE_SIZE`.
    *   `parse_b_row(fields) -> tuple[datetime, str, int]`: same order:
        field count 4; `has_bad_bytes(fields[:3])` (the note is not checked);
        blank barcode; time via `parse_iso_naive(fields[0])`; count via
        `parse_whole(fields[2])`. The note is not read.
    *   `parse_whole(text) -> int`: `text.strip()` must `WHOLE_RE.fullmatch`,
        else `RowError(f"quantity is not a whole number: {text}")`; returns
        `int(...)`.
    *   `parse_iso_naive(text) -> datetime`: `text.strip()` must
        `ISO_RE.fullmatch`, then `datetime.strptime(value[:19],
        "%Y-%m-%dT%H:%M:%S")`; a non-match or `ValueError` raises
        `RowError(f"bad date: {text}")`.
    *   `to_minute(dt) -> datetime`: `dt.replace(second=0, microsecond=0)`;
        both row parsers call it before returning.

#### 5. `stockmerge/rules.py` (Create)

*   **Type / Scope**: Rules file loading and categorisation (R3.1 to R3.5, R7.1).
*   **Proposed Changes**:
    *   `@dataclass(frozen=True) class Rule: pattern: str; category: str`;
        `pattern` is stored lower-cased.
    *   `load_rules(path: str, warnings: Warnings) -> list[Rule]`:
        `header, records = iter_records(path)`; `tuple(header)` must equal
        `("pattern", "category")`, else
        `StockmergeError(f"{path}: rules header must be pattern,category, found: {','.join(header)}")`.
        For each `(line_no, fields)`, first trim every field (`strip()`),
        then skip with `warnings.add(path, line_no, reason)`
        when: `len(fields) != 2` (`"expected 2 fields, found N"`), bad bytes
        (`"not valid UTF-8"`), blank pattern (`"blank pattern"`), blank
        category (`"blank category"`). Otherwise keep it, and also warn
        (keeping the rule) when the pattern starts with `0`
        (`"pattern starts with 0 and cannot match leading zeros of a SKU"`)
        or the category is `Move` or `Uncategorised`
        (`"category <c> is also used by stockmerge itself"`).
    *   `categorise(sku_norm: str, rules: list[Rule]) -> str`: first rule with
        `rule.pattern in sku_norm`, else `UNCATEGORISED`.

#### 6. `stockmerge/dedup.py` (Create)

*   **Type / Scope**: Dedup (R5.1 to R5.6).
*   **Proposed Changes**:
    *   `dedup(scans: list[Scan]) -> tuple[list[Scan], int]` returns the kept
        scans in input order and the number removed.
    *   Algorithm: count rows per `(scan_key, arg_index)`; for each scan key,
        N = the largest of those counts. Walk scans in input order with a
        counter per scan key; keep a scan while its key's counter is below N,
        then increment.

#### 7. `stockmerge/moves.py` (Create)

*   **Type / Scope**: Move linking (R6.1 to R6.5).
*   **Proposed Changes**:
    *   `link_moves(scans: list[Scan]) -> dict[tuple[int, int], str]` maps
        `Scan.ident` to `move_id` for every row in a move.
    *   `minutes_between(a, b) -> int`:
        `abs(int((a.minute - b.minute).total_seconds()) // 60)`.
    *   Algorithm: group positive scans by `(sku_norm, qty_each)`, each group
        in `scan_order`. Sort negatives by `scan_order`. For each negative,
        filter group `(sku_norm, -qty_each)` to positives not yet used, at a
        different location, and with `minutes_between <= MOVE_WINDOW_MINUTES`;
        choose the minimum by `(minutes_between, scan_order)`. Number moves
        from 1 in this loop; `move_id = f"M{n:04d}"`.

#### 8. `stockmerge/writer.py` (Create)

*   **Type / Scope**: Output (R8.1, R9.1 to R9.3).
*   **Proposed Changes**:
    *   `build_rows(scans, move_ids, rules) -> list[list[str]]`: sorts by
        `output_order`; category is `MOVE_CATEGORY` if the scan's ident is in
        `move_ids`, else `categorise(scan.sku_norm, rules)`; row is
        `[location, sku, str(qty_each), category, move_id or ""]`.
    *   `write_csv(out_path: str, rows) -> None`:
        `tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="",
        dir=os.path.dirname(os.path.abspath(out_path)), prefix=".stockmerge-",
        suffix=".tmp", delete=False)`; `csv.writer(f, lineterminator="\n")`;
        write `OUTPUT_HEADER` then rows; close; `os.replace(tmp, out_path)`.
        Before the replace, set the temporary file's permissions: if
        `out_path` already exists, copy its mode (`shutil.copymode`);
        otherwise use `0o666` minus the process umask (read with
        `os.umask(0)` and restored at once). If `out_path` is a symlink, the
        link itself is replaced by a regular file (accepted; not followed).
        On `OSError` or `UnicodeError` (including failure to create the
        temporary file), remove the temporary file if it exists and raise
        `StockmergeError(f"{out_path}: cannot write output: {exc}")`.

#### 9. `stockmerge/cli.py` (Create)

*   **Type / Scope**: Command line layer (R1.x, R2.x, messages table).
*   **Proposed Changes**:
    *   `location_arg(value: str) -> tuple[str, str]`: the argparse `type=`
        for `--location`. Splits on the first `=`, trims both parts. Raises
        `argparse.ArgumentTypeError` (so argparse prints its usage format and
        exits 2, as R1.1 and R1.2 require) for: no `=`
        (`"expected NAME=PATH, got: <value>"`), empty name
        (`"empty location name in: <value>"`), empty path
        (`"empty path in: <value>"`), or a name for which
        `name.encode("utf-8")` fails (`"location name is not valid UTF-8"`).
    *   `build_parser() -> argparse.ArgumentParser`: `prog="stockmerge"`,
        `allow_abbrev=False`; subparsers `dest="command", required=True`;
        one subparser `merge` (`allow_abbrev=False`) with
        `--location` (`action="append"`, `type=location_arg`,
        `required=True`, `metavar="NAME=PATH"`), `--rules` (required),
        `--out` (required).
    *   `same_file(a: str, b: str) -> bool` (R2.2): true if
        `os.path.realpath(a) == os.path.realpath(b)`; otherwise, if both
        exist, `os.path.samefile(a, b)`, with an `OSError` treated as false.
    *   `fold_name(name: str) -> str` (R1.4):
        `re.sub(r" +", " ", name.lower())`.
    *   Imports: `cli.py` imports functions by name
        (`from stockmerge.dedup import dedup`,
        `from stockmerge.moves import link_moves`, and so on), so a test can
        replace one with `monkeypatch.setattr("stockmerge.cli.dedup", ...)`.
        `writer.py` uses `import os` and calls `os.replace(...)`, so a test
        can replace it with `monkeypatch.setattr("stockmerge.writer.os.replace", ...)`.
    *   `main(argv: list[str] | None = None) -> int`:
        1. (The csv field size limit is already raised by `readers.py`.)
        2. `args = build_parser().parse_args(argv)` (argparse exits 2 on
           usage errors and 0 on `--help`).
        3. `exports = [(i, name, path) for i, (name, path) in enumerate(args.location)]`.
        4. `warnings = Warnings()`. R1.4: for each pair of distinct names
           with equal `fold_name`, in first-seen order,
           `warnings.add(None, None, f"location names '{a}' and '{b}' differ only by case or spaces")`.
           R1.5: for each pair of exports with different names whose paths
           are `same_file`,
           `warnings.add(None, None, f"{path} is given for both '{a}' and '{b}'")`.
        5. R2.2: if `same_file(args.out, p)` for any input path or the rules
           path, raise `StockmergeError(f"--out {args.out} is also an input file")`.
        6. `rules = load_rules(args.rules, warnings)`.
        7. For each export: `read_export(...)`; collect scans and add up R
           (read) and S (skipped).
        8. `kept, d = dedup(scans)`; `move_ids = link_moves(kept)`;
           `rows = build_rows(kept, move_ids, rules)`; `write_csv(args.out, rows)`.
        9. Print to stderr
           `stockmerge: read {R} rows, removed {d} duplicates, skipped {S} rows, linked {len(move_ids)//2} moves, wrote {len(rows)} rows`
           and return 0.
        *   `StockmergeError` → print `stockmerge: error: {exc}` to stderr,
            return 2.
        *   Backstop: `OSError`, `UnicodeError`, `csv.Error` → print
            `stockmerge: error: {where}: {detail}` and return 2. `where` is
            `getattr(exc, "filename", None) or current_path`, where
            `current_path` is a local set before each file step (rules,
            each export, `--out`) and starts as `"stockmerge"`. `detail` is
            `exc.strerror` for an `OSError` that has one (so the path is not
            printed twice), else `str(exc)`.
        *   Any other exception is not caught.
        *   `main` prints nothing to stdout.

#### 10. `tests/conftest.py` (Create)

*   **Type / Scope**: Test helpers.
*   **Proposed Changes**:
    *   `REPO_ROOT = Path(__file__).resolve().parent.parent`.
    *   Fixture `write_file(tmp_path)` returning a function
        `(name, content: str | bytes) -> str` that writes the file under
        `tmp_path` (text as UTF-8 with `newline=""`, bytes as-is) and
        returns its path as `str`.
    *   Fixture `run_cli()` returning a function `(*args) -> (returncode,
        stdout, stderr)` that runs
        `subprocess.run([sys.executable, "-m", "stockmerge", *args],
        cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8")`.
    *   Helper `make_scan(**overrides) -> Scan` (a plain function in
        `tests/conftest.py`, also exposed as fixture `scan_factory`) with
        defaults `location="shop"`, `arg_index=0`, `record_no=0`,
        `path="t.csv"`, `line=2`, `minute=datetime(2026, 3, 5, 10, 0)`,
        `sku="ABC"`, `qty_each=1`; `sku_norm` is computed from `sku` unless
        given. `minute` is used as given (not truncated), so tests pass
        whole-minute times; truncation is tested through the readers and the
        CLI. Used by `test_dedup.py` and `test_moves.py`.
    *   Fixture `read_out()` returning a function `(path) -> list[dict]`
        (`csv.DictReader` over the file, `encoding="utf-8", newline=""`).
    *   Unit tests import from `stockmerge` directly; `pyproject.toml` sets
        `pythonpath = ["."]` so this works from the repo root.

#### 11. `tests/test_model.py` (Create)

*   **Type / Scope**: Unit tests for the Glossary helpers.
*   **Proposed Changes**: `normalise_sku`: `" 00ABC "` → `"abc"`, `"000"` →
    `"0"`, `"123"` → `"123"`; `Warnings.add` formats with and without path
    and line.

#### 12. `tests/test_readers.py` (Create)

*   **Type / Scope**: Unit tests for R4.x (see the rule-to-test map).

#### 13. `tests/test_rules.py` (Create)

*   **Type / Scope**: Unit tests for R3.x and R7.1 (see the map).

#### 14. `tests/test_dedup.py` (Create)

*   **Type / Scope**: Unit tests for R5.x (see the map).

#### 15. `tests/test_moves.py` (Create)

*   **Type / Scope**: Unit tests for R6.x (see the map).

#### 16. `tests/test_cli.py` (Create)

*   **Type / Scope**: End-to-end tests through `python -m stockmerge`
    (R1.x, R2.x, R8.1, R9.x, CUJs, worked example).

#### 17. `tests/test_writer.py` (Create)

*   **Type / Scope**: Unit tests for `write_csv` (R9.2, R9.3; see the map).

#### 17a. `pyproject.toml` (Create)

*   **Type / Scope**: Project metadata and pytest config.
*   **Proposed Changes**: `[project]` name `stockmerge`,
    `requires-python = ">=3.11"`, no dependencies;
    `[tool.pytest.ini_options] testpaths = ["tests"]`, `pythonpath = ["."]`.

#### 18. `README.md` (Create)

*   **Type / Scope**: User documentation.
*   **Proposed Changes**: what the tool does, the command line, the two input
    formats, the rules file, the output columns, exit codes and warning
    format, and the list of [builder] rules.

#### 19. `.gitignore` (Create)

*   **Type / Scope**: Repo hygiene.
*   **Proposed Changes**: `__pycache__/`, `.pytest_cache/`, `*.pyc`.

### Rule-to-test map

Each case (separated by `;` in the third column) is one test function or
one parametrised case, with its input and expected result. The coverage
gate counts cases, not rows.

| Rule | Test file | Case: input → expected |
| --- | --- | --- |
| R1.1 | test_cli | no `--rules` → exit 2, stderr starts `usage: stockmerge`; `merge --help` → exit 0, stdout non-empty; `--loc` abbreviation → exit 2 |
| R1.2 | test_cli | `--location shop` → exit 2, stderr contains `expected NAME=PATH`; `--location =a.csv` and `--location shop=` → exit 2; `" shop = a.csv "` → location `shop` in output |
| R1.3 | test_cli | same `shop=a.csv` twice → output equals the single-file output |
| R1.4 | test_cli | names `Shop  Floor` and `shop floor` → exit 0, stderr has `differ only by case or spaces` |
| R1.5 | test_cli | `a=x.csv` and `b=x.csv` → warning `is given for both` |
| R2.1 | test_cli | missing input, missing rules, input that is a folder → exit 2, no output file |
| R2.2 | test_cli | `--out` equal to an input → exit 2, input unchanged; `--out` in a missing folder → exit 2 |
| R3.1 | test_rules | header `pat,cat` → `StockmergeError`; header with BOM and spaces → accepted |
| R3.2 | test_rules | blank pattern, blank category, 3 fields → skipped with warning; header only → `[]`; empty file → error |
| R3.3 | test_rules | rules `ab,X` then `abc,Y`, SKU `abc` → `X`; pattern `AB` matches SKU `xaby` |
| R3.4 | test_rules | pattern `abc`, SKU `00ABC` → match; pattern `0ab` → warning |
| R3.5 | test_rules | category `Move` → warning, rule kept |
| R4.1 | test_readers | BOM file read; CRLF file read; row with byte `\xff` in SKU → skipped `not valid UTF-8`, next row read; `\xff` in Format B note → row kept |
| R4.2 | test_readers | Format A and B headers detected; ` SKU ` cell trimmed; unknown header → error naming header; zero bytes / only blank lines → `no header row`; header only → no scans and `no valid rows` warning |
| R4.3 | test_readers | blank and whitespace-only lines ignored without warning; blank lines before header skipped; 5 fields → skipped; Format B note `a,b` unquoted → skipped |
| R4.4 | test_readers | SKU `"  "` → skipped `blank SKU`; ` 00123 ` → `sku` `00123` |
| R4.5 | test_readers | `05/03/2026 14:30` ok; `5/3/2026 9:05` ok; `31/02/2026 10:00` → skipped |
| R4.6 | test_readers | `2026-03-05T14:30:12` ok; `.123456` fraction ok; `Z`, `+01:00`, `2026-03-05`, Arabic-Indic digits → skipped |
| R4.7 | test_readers | `14:30:59` → minute 14:30 |
| R4.8 | test_readers | `+5` → 5; `-3` → -3; `5.0`, `2.5`, blank, `1234567890` → skipped |
| R4.9 | test_readers | `2,case` → 24; `-1,case` → -12; ` Case ` → 12; `box` → skipped |
| R4.10 | test_readers | Format B count `7` → 7 regardless of note text |
| R4.11 | test_moves | scans `shop` `X` 0 at 10:00 and `back` `X` 0 at 10:05 → `link_moves` returns `{}` |
| R4.11 | test_cli | Format A row `05/03/2026 10:00,ABC,0,each` with rule `ab,Food` → output row `shop,ABC,0,Food,` |
| R4.12 | test_readers | note `"oops` unclosed, then 2 valid rows → 3 scans; quoted `"a, b"` note → kept; 200,000-character note → no error |
| R5.1–R5.3 | test_dedup | `1,case` (A) equals `12` (B) (built as `qty_each=12` scans); `00123` equals `123`; different locations never deduped; 2 identical rows in one export → 2 kept |
| R5.1 + R4.7 | test_cli | `shop=a.csv` (B) with `2026-03-05T14:30:05,X,1,` and `shop=b.csv` (B) with `2026-03-05T14:30:59,X,1,` → 1 output row, summary `removed 1 duplicates` |
| R5.4 | test_dedup | counts 2 and 1 → 2 kept, removed 1; counts 2 and 3 → both export-1 rows plus first export-2 row |
| R5.5 | test_dedup | kept rows keep their own `sku` text |
| R5.6 | test_cli | a negative scan present in two exports of `back` and one positive at `shop` → one move, the other copy removed (D = 1, M = 1) |
| R6.1 | test_moves | basic pair; positive first; 120 min links; 121 min does not; same location never; different quantity never |
| R6.1 + R4.7 | test_cli | `back=b.csv` (B) `2026-03-05T10:00:59,X,-1,` and `shop=s.csv` (B) `2026-03-05T12:00:30,X,1,` → both rows `Move`, same `move_id` (120 minutes on minute times; 119.5 on raw times) |
| R6.2 | test_moves | `back` -5 `X` 10:00 with `shop` +5 at 10:30 and `store` +5 at 10:10 → pairs with `store`; `back` -5 at 10:00 with `shop` +5 at 09:50 and `store` +5 at 10:10 (both 10 min) → pairs with `shop` (earlier minute); `back` -5 at 10:00 and `store` -5 at 10:30 with one `shop` +5 at 10:20 → `back` (first in scan order) takes it, `store` unmatched |
| R6.3 | test_moves, test_cli | each row in one move; both rows category `Move`, same id |
| R6.4 | test_moves | two moves → `M0001`, `M0002` in order formed |
| R6.5 | test_moves | SKU `X`, qty 5: `shop` +5 at 08:01 (P2), `back` -5 at 10:00 (N1), `shop` +5 at 10:05 (P1), `store` -5 at 10:10 (N2) → N1 pairs with P1 (5 min beats 119); N2's only in-window partner was P1, so N2 is unmatched; P2 unmatched |
| R7.1 | test_cli | non-move row with no rule match → `Uncategorised`, blank `move_id` |
| R8.1 | test_cli | worked example rows in the order shown |
| R9.1 | test_cli | no data rows → file is exactly the header line |
| R9.2 | test_cli | output bytes have no BOM, no `\r`; `-12` written as `-12` |
| R9.3 | test_cli, test_writer | existing `--out` unchanged after an exit-2 run (CLI); `write_csv` with `os.replace` monkeypatched to raise `OSError` → `StockmergeError`, no `.stockmerge-*.tmp` left, existing `--out` unchanged (unit); new output file mode is `0o666 & ~umask`; existing `--out` mode kept |
| Summary | test_cli | worked example stderr ends with the summary line shown in the Technical Plan |
| G4 | test_cli | two runs on the same inputs → byte-identical files |
| G5 backstop | test_cli (in-process) | monkeypatch `stockmerge.cli.dedup` to raise `OSError("boom")`; `main([...])` returns 2 and stderr starts `stockmerge: error:` |
| Warning format | test_readers | bad row on physical line 4 (after a blank line 3) → message `PATH:4: ...` |
| R4.1 header / rules | test_readers, test_rules | header with `\xff` → unrecognised header error; rules row with `\xff` → skipped with warning |
| R2.2 variants | test_cli | `--out` is a hard link to an input → exit 2; `--out` equal to the rules file → exit 2 |
| CUJ 1 | test_cli | files and rows exactly as CUJ 1 → 3 rows: two `00123`, one `123`, each `qty_each` 12 |
| CUJ 3 | test_cli | one valid row, `31/02/2026 10:00` row, `2.5` row → exit 0, 1 output row, 2 warnings with line numbers, summary `skipped 2 rows` |
| CUJ 4 | test_cli | unknown header with an existing `--out` → exit 2, stderr contains `unrecognised header`, `--out` bytes unchanged |
| Worked example | test_cli | files below and `rules.csv` = `pattern,category\n42,Spares\n`; run with `--location back=b.csv --location shop=s1.csv --location shop=s2.csv` → output file is exactly the 5 lines shown in the Technical Plan, plus a final `\n` |

Worked-example file contents (each line ends with `\n`):

```text
b.csv:   Scanned At,SKU,Qty,Unit
         05/03/2026 10:05,ABC,-6,each
s1.csv:  Scanned At,SKU,Qty,Unit
         05/03/2026 11:40,abc,6,each
         05/03/2026 11:40,abc,6,each
s2.csv:  timestamp,barcode,count,note
         2026-03-05T11:40:30,abc,6,
         2026-03-05T12:10:00,0042,-1,
```

### Verification Plan

*   **Compilation/Build**: none; `python -m stockmerge merge --help` exits 0.
*   **Unit Tests**: `python -m pytest` from the repo root passes.
*   **Static Analysis & Linting**: none required (standard library only).
*   **Test Coverage Requirement**: every case in the rule-to-test map
    (each `;`-separated item) has its own test function or parametrised
    case.
*   **E2E/Integration**: `tests/test_cli.py` runs the real module in a
    subprocess.

--------------------------------------------------------------------------------

*Drafted with EGM*
