# tsinvoice: merge overlapping timesheet exports into invoice-ready sessions

*   **Author:** design agent (for Mashhood Rastgar)
*   **Status:** Approved
*   **Date:** 2026-11-03

--------------------------------------------------------------------------------

## Overview

`tsinvoice` is a command-line tool for one freelancer. It reads CSV
exports from two time-tracking apps (a desktop app and a phone app), removes
entries that appear twice because export date ranges overlap, joins entries
that continue each other into one session, rounds and prices each session from
a rates file, and writes one sorted CSV of sessions ready to invoice.

It is a Python 3.11+ package that uses only the standard library at run time.
The command line, the input formats, the rates header, and the output header
are a fixed contract defined in [BRIEF.md](../../BRIEF.md). Every behaviour rule
below comes from the owner's answers in [stakeholder_log.md](../../stakeholder_log.md)
(cited as R1.n, R2.n, R3.n, R4.n for round and answer number) or from a decision made
during design where the owner said "your call" (cited as **[D]**, see the
Decisions Log).

## The Problem

The owner exports CSVs from both apps every couple of weeks. The date ranges
overlap, so the same entry appears in more than one export of the same app. The
owner also sometimes stops a timer in one app and carries on in the other (or
restarts it in the same app), so one piece of work is split into two entries
back to back. Today the owner has to clean this up by hand before invoicing.
Mistakes either drop real worked time or bill the same time twice.

The tool solves this with fixed, exact rules: an entry is a
duplicate only when it matches (after normalising client and description) an
entry in another export of the same tracker, with the same start and end; and
two entries are joined only when the second starts 0 to 2 minutes after the
first ends with the same client and description. Bad rows are skipped with a
warning; unrated sessions are kept at `0.00` with a warning; overlapping
sessions for one client are kept with a warning.

## Goals

*   **G0. Primary user and success (R1.12, [D]).** The user is one
    freelancer who runs the tool every couple of weeks before invoicing.
    Success means: every CUJ and worked example below passes as an automated
    test; reruns are byte-identical; every case in G6 appears on stderr; the
    owner can send the CSV without hand edits.
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
    same order produce a byte-identical output file and identical stderr. (On
    exit 2, the operating-system reason text inside an error message may vary
    by platform and locale.)
*   **G6. Warn on data problems.** Each of these produces one stderr
    warning: every bad row (R1.11); every unrated session (R1.4, R3.9); and
    every pair of overlapping sessions for one client, except exact repeats
    (Stage 8, [D]). Blank records, duplicate removals and joins are silent by
    design: they are the tool's normal work, not problems.

## Non-Goals

*   Time zones, offsets and daylight saving: times are local wall-clock (R1.6).
*   Splitting sessions at midnight (R1.7).
*   Fuzzy or near-duplicate matching, or reconciling an entry that was edited
    between exports (R1.2). Edited entries are both kept; Stage 8 warns only
    when the two versions keep the same client and overlap in time.
*   Deduplicating across different trackers (R1.1).
*   Invoice documents, per-client totals, currencies, tax.
*   Configurable rounding step or join gap; state kept between runs; any input
    format other than A and B.
*   A summary or progress line on stdout or stderr.

## Open Questions

None. Every behaviour question is decided either by the owner (cited inline as
R1.n, R2.n, R3.n, R4.n) or by the designer (marked **[D]**, with its reason in the
Decisions Log at the end of the Technical Plan).

## Glossary

*   **Tracker**: one time-tracking app, named by the NAME in
    `--tracker NAME=PATH`. NAME is compared as an exact, case-sensitive string.
*   **Export**: one `--tracker NAME=PATH` argument. Several exports may share a
    NAME. The same PATH given twice counts as two exports **[D]**.
*   **Entry**: one valid data row from an export, with a client, a description,
    a start and an end.
*   **Blank**: empty after trimming whitespace. Used for cells and values
    throughout.
*   **Normalised text** **[D]**: Unicode NFC, then trimming, collapsing every
    run of whitespace to one space, case-folding (so "ß" matches "ss"), and NFC
    again. Used for comparing client,
    description and rate patterns; never printed. (Headers, NAMEs and PATHs
    have their own comparison rules, stated where they are used.)
*   **Blank record** **[D]**: a CSV record with no cells, or whose cells are
    all blank (for example an empty line or `,,,`). Blank records are
    skipped anywhere in a file, including before the header: the header is
    the first non-blank record.
*   **Unrated session**: a session that no rate rule matches. It is written
    with amount `0.00` and one warning.
*   **Input order**: the order (argument position of the export, line number
    of the row). Argument position counts each `--tracker` argument on its own;
    exports are not grouped by NAME.
*   **Line number**: the 1-based physical line in the file where a record
    starts. The file's first line is line 1, so the header is line 1 only
    when no blank lines come before it.
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
    export 1's two copies and the first copy from export 2. Because the
    copies are exact repeats, Stage 8 prints no overlap warning for them.

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
    unchanged.

### CUJ 6: Rerun

*   **Given**: the same inputs and arguments as an earlier run.
*   **When**: the merge runs again.
*   **Then**: `out.csv` is byte-identical to the earlier output.

## Technical Plan (Architecture)

The tool runs in two phases. **Phase 1** reads and validates every input file
completely. A command-line problem, a problem with a whole file (missing,
unreadable, malformed CSV, unrecognised header) or any invalid rates row stops
the run with exit 2 before anything is written. A bad row in an export does not
stop the run: it is skipped with a warning. **Phase 2** is a pure function from
the list of valid entries and the rate rules to the output rows and warnings.
The output is then written to a temporary file and moved into place, so a
failed run never leaves a truncated `--out`.

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
     write temp file ─► os.replace(--out) ─► emit warnings to stderr (fixed order) ─► exit 0
```

Nothing after Phase 1 knows which input format an entry came from: both
formats are turned into the same entry record.

### Stage 1: Command line

*   `merge` is the only sub-command. `--tracker` (repeatable), `--rates` and
    `--out` are all required.
*   Each `--tracker` value is split on its **first** `=`. A value with no `=`,
    an empty NAME or an empty PATH is a usage error: exit 2 **[D]**.
*   The same PATH may be given more than once. Under one NAME it adds no
    rows (max-count rule). Under two NAMEs its entries are billed twice; the
    Stage 8 overlap warning reports each such pair, so no separate check
    exists **[D]**.
*   Argument errors use the standard `argparse` message and exit code 2.

### Reading any CSV file (used by Stages 2 and 3)

*   **Reading [D].** Every input file (the rates file and each export) is
    read whole into memory with
    `open(path, encoding="utf-8-sig", newline="").read()` (BOM removed, line
    endings kept as they are) and parsed with
    `csv.reader(io.StringIO(text, newline=""))`: the standard default dialect
    (comma, `"` quoting, doubled `""` inside quotes) in its default,
    non-strict mode. A quoting quirk inside one row (for example
    `"Design" review`) is read the way the `csv` module reads it and then
    validated like any other row, so at worst it becomes a bad row (R1.11).
*   **Physical lines.** A physical line is text ended by `\n`, `\r\n` or
    `\r` (or the end of the file), the same line breaks the `csv` module
    recognises. Other Unicode line separators (for example U+2028) are
    ordinary characters.
*   Missing, unreadable or undecodable file: exit 2 **[D]**.
*   **Field size limit [D].** Before reading, the csv field size limit is
    raised to `min(sys.maxsize, 2**31 - 1)` (the larger value overflows on
    Windows), so a long field, including one swallowed by an unterminated
    quote, does not hit the default limit of 131072 characters.
*   **Unterminated quote (R4.1).** If the file ends while a quoted field is
    still open, the record that starts at that line and runs to the end of
    the file is one bad row with reason `unterminated quoted field`, reported
    at its start line; the run continues and exits 0. The rows swallowed into
    it are lost, and that single warning is the signal (owner's choice). In
    the rates file the same record is a bad rates row, so it is fatal like
    any other (Stage 2).
*   **Detection [D].** The non-strict reader does not report this case (it
    returns the partial record silently). So the parser reads
    `text + "\n" + SENTINEL`, where `SENTINEL = "__TSINVOICE_EOF__"`. If
    the last record is exactly `[SENTINEL]`, no quote was left open and that
    record is discarded. Otherwise the sentinel was swallowed into an open
    quoted field: the last record is the unterminated one (the sentinel and
    the `\n` before it are removed from its last cell). An unterminated
    record is never treated as a blank record, and check (0) "unterminated"
    runs before every other check.
*   **Unterminated header.** If the unterminated record is the header (no
    other record before it), the file has no usable header: exit 2 with
    `unrecognised header` (export) or `unrecognised rates header` (rates).
*   Any `csv.Error` (not expected with these settings) is fatal:
    `<path>: cannot read: <str(error)>`, exit 2 **[D]**.
*   A record may span several physical lines only inside a quoted field.

### Stage 2: Read the rates file

*   Opened and read as described in "Reading any CSV file".
*   Header **[D]**: each cell trimmed and compared case-insensitively to
    `pattern,hourly_rate`; trailing blank header cells are ignored. Anything
    else: exit 2. A zero-byte file (no header): exit 2.
*   Blank records (see Glossary) are skipped. Every other row must be valid or
    the run stops with exit 2, naming the file and line **[D]**: wrong cell
    count (extra cells allowed only if blank), a pattern that is blank after
    normalising, or a rate that, after trimming, does not match
    `^[0-9]+(\.[0-9]+)?$` with `re.fullmatch` (ASCII digits, optional decimal part; no sign,
    exponent, underscore or thousands separator). Negative rates are
    rejected; `-0` cannot occur. A zero rate is allowed **[D]** (for example
    unpaid work for a client) and, unlike an unrated session, prints no
    warning. See the Decisions Log for why bad rates rows are fatal. Rates
    row checks run in this order and the first failure is reported:
    unterminated quoted field, cell count, pattern, rate.
*   Rules keep file order. Each rule stores its normalised pattern and its rate
    as a `Decimal`. A header-only rates file is valid: every session is then
    an unrated session and is warned.

### Stage 3: Read each export

*   Opened and read as described in "Reading any CSV file". Each export is detected on its own, so one NAME may mix
    formats **[D]**.
*   **Header detection** **[D]**: cells trimmed, compared case-insensitively,
    exact names in exact order, trailing blank cells ignored.
    *   `client,description,start,end` → Format A (desktop).
    *   `client,task,start_iso,duration_minutes` → Format B (phone).
    *   Anything else, or no header at all: `tsinvoice: error: <path>: unrecognised header`, exit 2, nothing written.
*   Blank records (see Glossary) are skipped silently. Every other row that
    fails a check below is a **bad row**: it is skipped with
    `tsinvoice: warning: <path>:<line>: <reason>` and the run continues (R1.11).
*   **Check order.** Checks run in this order and the first failure gives
    the reason: (0) unterminated quoted field, (1) cell count, (2) client, (3) Format A Start, then End
    (blank, unparseable, not after Start) / Format B `start_iso`, then
    `duration_minutes`.
*   **Checks on every row:** the cell count equals the header's (extra cells
    allowed only if blank **[D]**); in `expected N fields, got M`, N is the header's
    field count after trailing blank header cells are dropped (4 for both
    formats) and M is the record's raw cell count. The client must not be
    blank after trimming **[D]**. A blank description is allowed **[D]**: it
    is still real time.
*   **Field mapping.** Format A: `Client` → client, `Description` →
    description, `Start`/`End` → start/end. Format B: `client` → client,
    `task` → description, `start_iso` → start, start + `duration_minutes` →
    end.
*   **Format A row:** Start and End are trimmed and parsed as
    `DD/MM/YYYY HH:MM` (Python `%d/%m/%Y %H:%M`, so single-digit day, month or
    hour are accepted **[D]**). End blank, unparseable, or not after Start is a
    bad row (R1.11).
*   **Format B row:** `start_iso` is trimmed and must begin with
    `YYYY-MM-DD`, then `T` or a space, then `HH:MM` **[D]**; it is parsed with
    `datetime.fromisoformat`, and any offset or `Z` is dropped without
    converting (R1.6). A date-only value is a bad row. Seconds and
    fractions of a second are dropped (truncated to the minute) **[D]**, so
    every time in the tool is a whole minute, the same precision as Format A. `duration_minutes` is trimmed and must be ASCII digits, optionally
    followed by `.` and one or more zeros: `re.fullmatch(r"[0-9]+(\.0+)?", value)`
    (so `30` and `30.0` are accepted; `30.`, `29.5`, `0`, `-5`, `+5`, `1e2`,
    `3_0` are not), with a value above zero (R2.4,
    **[D]**). End = start + duration. If computing the end overflows Python's
    date range (for example `99999999999` minutes), the row is a bad row with
    `invalid duration_minutes` **[D]**.
*   Each valid row becomes an **entry**: tracker NAME, input order
    (argument position, line number), source path and line, client text and
    description text (outer spaces trimmed, case kept), their normalised keys,
    start, end, and worked minutes (`(end - start)` in whole minutes; both
    formats always give whole minutes because desktop times have no seconds,
    phone seconds are dropped, and phone durations are whole numbers).

Bad-row reasons (fixed text, used in tests):

| Reason text | When |
| --- | --- |
| `expected N fields, got M` | wrong cell count (M = raw cell count; extra cells allowed only if blank) |
| `blank client` | client blank |
| `blank end` | Format A, End blank |
| `invalid start` / `invalid end` | Format A, Start blank or unparseable / End unparseable |
| `end is not after start` | Format A, End ≤ Start |
| `invalid start_iso` | Format B, blank, unparseable or no time part |
| `unterminated quoted field` | the file ends inside a quoted field that starts on this line |
| `invalid duration_minutes` | Format B, blank, not a whole number above zero, or end out of date range |

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
    `Q.start − P.end` is between 0 and 2 minutes inclusive (R1.3, R2.2).
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
*   **Unrated session** (no matching rule): amount `0.00`, the row is still
    written, and one warning per row: `tsinvoice: warning: no rate for client '<client>' description '<description>' on <date>` (R1.4, R3.9).
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
    overlap **[D]**), warn
    `tsinvoice: warning: overlapping sessions for client '<client>': row <i> and row <j>`
    (`<client>` is the printed client of row i),
    where i and j are 1-based data row numbers in the output, i < j, pairs in
    order of (i, j) **[D]**.
*   **Exact repeats are not warned [D]**: a pair is skipped when both rows
    are single-entry sessions whose entries share the same Stage 4 duplicate
    key (same tracker, normalised client and description, start and end).
    The owner says such repeats are real separate work (R1.1), so warning
    on them would teach the user to ignore the warning.
*   This does not change the output. It makes visible the cases where the
    rules bill the same time twice: an entry edited between exports (when
    both versions overlap), the same work timed in both apps, and the same
    PATH given under two NAMEs.

### Stage 9: Warnings and output

*   **stderr order** (deterministic, G5): (1) bad-row warnings in input
    order; (2) unrated-session warnings in output row order; (3) overlap
    warnings in (i, j) order. Warnings are
    printed only after the output file is in place. A fatal error (including
    a failed write) prints a single `tsinvoice: error: <message>` line and no
    warnings. Usage errors are the exception: they print argparse's own
    usage and error lines. Nothing is printed on stdout **[D]**, except
    argparse's `--help` output (exit 0), which is left as argparse prints it.
*   **Output file** **[D]**: UTF-8 without BOM, written with
    `csv.writer(..., lineterminator="\n", quoting=csv.QUOTE_MINIMAL)` (fields
    with commas, quotes or line breaks are quoted; line breaks inside a field
    are kept as they are). Header exactly
    `date,client,description,minutes,amount,session_id`. `minutes` is a bare
    integer; `amount` is a plain decimal with exactly two places and never
    exponent notation (`0.00`, `12.50`, `1234.00`). Decimal arithmetic uses
    a local context with precision 50, enough for any realistic rate.
*   With no valid entries, a header-only file is written and the exit code is 0
    **[D]**.
*   The file is first written to a temporary file (`.tsinvoice-*` in the
    same directory as `--out`, permissions set to `0o644`), then moved over
    `--out` with `os.replace`. If writing fails, the temporary file is
    removed. If `--out` is a symlink, the link itself is replaced by a
    regular file. An existing `--out` is
    overwritten. On exit 2 it is never touched. `--out` may equal an input
    path, because all inputs are fully read first **[D]**. If the output
    directory does not exist or is not writable: exit 2.

### Fatal error messages

Every exit-2 path (except argparse usage errors) prints exactly one line
`tsinvoice: error: <message>`. These texts are normative:

| Message | When |
| --- | --- |
| `<path>: cannot read: <reason>` (reason is `str(exception)`) | tracker or rates file missing, unreadable, not valid UTF-8, or another `csv.Error` |
| `<path>: unrecognised header` | export header matches neither format, or the export has no non-blank record |
| `<path>: unrecognised rates header` | rates header is not `pattern,hourly_rate`, or the rates file has no non-blank record |
| `<path>:<line>: invalid rates row: expected 2 fields, got M` | rates row with wrong cell count |
| `<path>:<line>: invalid rates row: unterminated quoted field` | rates file ends inside a quoted field starting on this line |
| `<path>:<line>: invalid rates row: empty pattern` | pattern blank after normalising |
| `<path>:<line>: invalid rates row: invalid hourly_rate` | rate fails `^[0-9]+(\.[0-9]+)?$` |
| `<out path>: cannot write: <OS reason>` | temp file or replace fails |

### Exit codes

| Exit | Cause |
| --- | --- |
| 0 | Success, including runs with skipped rows, unrated sessions, overlap warnings, or no valid entries |
| 2 | Usage error (missing option, bad `--tracker`); missing, unreadable or undecodable file; a `csv.Error` other than an unterminated quote; unrecognised or missing header in an export or the rates file; any bad rates row; output cannot be written |

### Worked examples

| Case | Input | Output |
| --- | --- | --- |
| Join and round | 09:00–09:07 then 09:07–09:14, same client/description | one row, minutes 18, session_id S1 |
| Gap limit | P ends 10:00; Q starts 10:02 / 10:03 | joined / not joined |
| App handoff with seconds | phone `start_iso` 09:00:30, 7 min (09:00–09:07 after truncation); desktop 09:07–09:14 | joined: one row, minutes 18 |
| Overlap is not a join | P 09:00–10:00; Q 09:59–10:30 | two rows; overlap warning |
| Claimed successor | A 09:00–10:00, B 09:30–10:01, C starts 10:01 (same group) | A is first in start order and takes C (gap 1 min); B has no free candidate; rows A+C (S1) and B; overlap warning |
| Max count | export 1 has X twice, export 2 has X three times | X three times |
| Half-up | 6 minutes at rate 10.05 | amount 1.01 |
| Exact multiple | 12 worked minutes | minutes 12 |
| Unrated | no rule matches | amount 0.00, row kept, warning |
| Case of client | "Acme" session, later "ACME" session | printed "Acme" and "ACME" (each from its own first entry); sorted together |

### Decisions Log

Owner decisions are cited inline by R-number. Each item below was left to the
designer ("your call"); this list is the authoritative record of them.

| [D] decision | Reason |
| --- | --- |
| Truncate `start_iso` seconds to the minute | Desktop times have minute precision. Keeping phone seconds would make an ordinary handoff (phone 09:00:30 + 7 min, desktop starting 09:07) a 30-second overlap: no join, two rounded sessions (24 billed minutes instead of 18) and a false overlap warning. The cost is that two phone entries differing only in seconds become duplicates, which needs two exports holding near-identical entries and is far rarer |
| Accept `30.0` as a duration; reject `29.5`, signs, exponents | `30.0` is a whole number written by some apps; the owner requires a whole number above zero (R2.4) |
| Reject date-only or hour-only `start_iso` | Python would silently read a date-only value as midnight and invent a start time |
| Desktop dates via `%d/%m/%Y %H:%M` (single digits accepted) | Standard parser behaviour; rejecting `5/1/2026 9:00` would drop real time |
| Export and rates headers: trimmed, case-insensitive, exact names and order, trailing blank cells ignored, BOM removed | Tolerates spreadsheet re-saves without guessing at renamed or reordered columns |
| One NAME may mix formats | Detection is per file; nothing else depends on the format |
| Missing/unreadable/undecodable file, zero-byte file: exit 2 | The input set is wrong as a whole; a partial invoice would silently lose time |
| `--tracker` split on first `=`; empty side is a usage error | Paths may contain `=`; an empty NAME or PATH is always a typo |
| Any bad rates row is fatal (exit 2) | Under first-match-wins, a skipped specific rule lets a broader later rule misprice silently |
| Blank client is a bad row; blank description is kept | Sessions are grouped and priced by client, so a blank client cannot be billed; a blank description is still billable real time |
| Same PATH under two NAMEs: no separate warning | It bills every entry twice, but every resulting pair already gets a Stage 8 overlap warning; a second warning for one mistake adds noise |
| Line numbers are 1-based physical file lines of the record's start | Matches what the user sees in an editor |
| Warning and error texts fixed; stderr order fixed | Deterministic stderr (G5) and testable messages |
| Header-only output when no valid entries; exit 0 | A run with only bad rows is still a successful run; the warnings say why it is empty |
| Atomic write via temp file + `os.replace`; `--out` may equal an input | Guarantees "exit 2 writes nothing" and never leaves a truncated file |
| Nothing on stdout; no summary line | Not requested; warnings already report everything skipped or suspect |
| UTF-8 without BOM, `\n` line endings, minimal quoting | Byte-stable output across platforms (G5) |
| Sequential `S1, S2, ...` session IDs on joined rows in output order; blank on single-entry rows | The owner needs unique and stable-for-identical-inputs only (R3.6). The owner's "non-empty" (R1.8) is read as applying to joined sessions, because BRIEF.md fixes `session_id` as blank unless the row was joined, and the contract wins |
| Overlap warning for same-client sessions | Makes the double billing the owner's rules allow visible without changing output (G6) |
| Unicode NFC around case-folding in `normalise()` | The two apps may encode "é" differently; without NFC the same client would not match. It adds NFC as a step around the owner's trim/collapse/ignore-case rule (R1.1) |
| Primary user and success (R1.12) | See Goal G0 |
| Same PATH twice counts as two exports | Simple, and the max-count rule makes it harmless |
| Blank records skipped anywhere, including before the header | Spreadsheet saves add blank lines; they carry no data |
| Extra cells allowed only if blank | Trailing commas from spreadsheets are common; non-blank extra data means the row is not what we think it is |
| Zero rate allowed, no warning | Lets the owner mark unpaid work deliberately; an unrated session is different and is warned |
| Touching sessions (one ends exactly when the next starts) are not an overlap | No time is counted twice |
| Non-strict CSV reading; a `csv.Error` other than an unterminated quote is fatal | Keeps R1.11 (skip bad rows) for row-level quirks; an unterminated quote is a bad row by owner decision (R4.1) |
| Duration overflow is a bad row | Prevents a crash on huge values and fits the owner's bad-row rule (R1.11). Implausibly long entries are not warned: the owner reviews the `minutes` column before invoicing |
| Temp file `0o644`, removed on failure; a symlinked `--out` is replaced | Normal file permissions for an invoice; no leftovers after a failed write |

## Alternatives Considered

### Alternative A: Stream each file and write rows as they are processed

*   **Pros**: Lower memory; one loop instead of two phases.
*   **Cons**: A bad header in the third file would be found after output had
    started, breaking "exit 2, write no output". Joining and sorting need all
    entries anyway.
*   **Reason for Rejection**: Two phases (read everything, then a pure merge)
    meet the contract and make `--out` equal to an input path safe.

### Alternative B: One module per stage, or a registry of format parsers

*   **Pros**: A third input format would be one new entry.
*   **Cons**: More files and indirection for two fixed formats; a third
    format is a non-goal.
*   **Reason for Rejection**: A third format is a non-goal. A few flat
    modules with one shared entry record already keep format knowledge out of
    the merge logic.

### Alternative C: Per-format entry types

*   **Pros**: Keeps the original columns of each format.
*   **Cons**: Every later stage would branch on format.
*   **Reason for Rejection**: One format-agnostic entry record; nothing after
    reading needs to know the format.

### Alternative D: Global smallest-gap or optimal matching for joins

*   **Pros**: Could join more pairs in some cases (in the A/B/C example, B+C
    has gap 0).
*   **Cons**: Not what the owner asked for; harder to explain and test.
*   **Reason for Rejection**: The owner specified the greedy walk in start
    order (R2.3, R3.3).

### Alternative E: Keep seconds in `start_iso`

*   **Pros**: Two phone entries that differ only in seconds are never treated
    as duplicates.
*   **Cons**: A phone entry with seconds followed by a desktop entry (minute
    precision) often looks like a short overlap, so the handoff is not joined,
    is billed as two rounded sessions, and triggers an overlap warning.
*   **Reason for Rejection**: See Decisions Log (truncate seconds): it breaks
    ordinary app handoffs.

### Alternative F: Content-hash session IDs

*   **Pros**: IDs stay stable when newer, larger exports are added.
*   **Cons**: Longer IDs, collision handling.
*   **Reason for Rejection**: The owner does not rerun against earlier
    invoices (R3.6); sequential `S<n>` is enough.

### Alternative G: Skip bad rates rows with a warning

*   **Pros**: One broken rule does not stop the invoice.
*   **Cons**: Under first-match-wins, a skipped specific rule lets a broader
    later rule price the session wrongly, with only a warning line as signal.
*   **Reason for Rejection**: See Decisions Log (bad rates rows are fatal).

### Alternative H: Float arithmetic for amounts

*   **Pros**: No `Decimal` import or conversions.
*   **Cons**: Binary floats cannot represent 1.005 exactly (it is stored as
    1.00499...), so `round(1.005, 2)` gives 1.0.
*   **Reason for Rejection**: `Decimal` with `ROUND_HALF_UP` gives the decimal
    half-up result the owner specified (R1.5).

### Alternative I: Change the dedupe rule to catch edited or double-timed entries

*   **Pros**: Would prevent some double billing.
*   **Cons**: Contradicts the owner's exact-match rule (R1.2) and risks losing
    real time.
*   **Reason for Rejection**: Keep the owner's rule; warn about overlaps
    instead (Stage 8).

--------------------------------------------------------------------------------

## Risks & Mitigations

| Risk | Failure mode and impact | Mitigation or accepted limit |
| --- | --- | --- |
| Double billing | Edited entries, the same work timed in both apps, or one PATH under two NAMEs bill the same time twice | Owner's exact-match rule kept (R1.2); Stage 8 overlap warning makes it visible |
| Lost time | A skipped bad row drops real time | One warning per bad row with file and line (R1.11) |
| Mispricing by a broken rule | A skipped specific rule lets a later broad rule price the session | Bad rates rows are fatal (Stage 2) |
| Substring over-match | Client "Beta" with description "call with Acme" is priced by an earlier "acme" rule, because descriptions are matched too (R1.4) | Accepted (owner's rule). README advises putting specific rules first and avoiding short patterns |
| Malformed CSV | An unterminated quote swallows the rest of a file | Accepted (R4.1): the unterminated record is one bad row with its own reason `unterminated quoted field` naming file and line, so the user can see why later rows are missing |
| Implausible values | A year typo bills a year; huge durations overflow | Overflow is a bad row (Stage 3). A typo that stays in range is visible in the `minutes` column (accepted) |
| Partial output | A crash or failed write leaves a truncated invoice | Temp file + `os.replace`; temp removed on failure. A hard kill can leave a `.tsinvoice-*` file next to `--out` (accepted) |
| Encoding | cp1252 or UTF-16 exports fail | Accepted: exit 2 with `cannot read: <decode reason>`; the owner re-exports as UTF-8 |
| Scale | Join and overlap scans are quadratic inside a group | Accepted at freelancer size (thousands of rows) |

**Security.** Inputs are the owner's own local files and are trusted. The tool
reads only the given paths, writes only `--out` and its temporary file, opens
no network connections and runs no code from the inputs. Spreadsheet formula
injection (a client or description starting with `=`, `+`, `-` or `@`) is an
accepted limit: the text is written as is, because the owner's own data is
not hostile and changing it would alter the invoice text.

--------------------------------------------------------------------------------

## Non-Functional Requirements

*   **Performance**: Input is a freelancer's exports (hundreds to a few
    thousand rows). Join candidate search is a linear scan per entry within
    its client+description group, and the overlap check compares every pair
    within one client: O(n²) per group, acceptable at this size.
*   **Determinism**: No reliance on dict/set iteration order of unordered data,
    the clock, the locale, or the environment. All orders are fixed by the sort
    keys above.
*   **Safety**: see Risks & Mitigations.
*   **Dependencies**: standard library only at run time; `pytest` for tests.

--------------------------------------------------------------------------------

## Additional Resources

*   [BRIEF.md](../../BRIEF.md): fixed contract.
*   [stakeholder_log.md](../../stakeholder_log.md): owner answers, rounds 1–4.
*   [concepts_brief.md](../../concepts_brief.md): brainstorm analysis and decisions.

## Future Improvements

*   **Stable IDs**: content-hash session IDs if invoices ever cite them across
    reruns.
*   **Summary line**: counts of rows read, skipped, deduplicated and joined.

--------------------------------------------------------------------------------

## Detailed Implementation Plan

The repository root is the directory that contains `BRIEF.md` (two levels
above this document). `tsinvoice/`, `tests/`, `pyproject.toml` and
`README.md` are created there. All paths below are relative to it. No other
files are touched.

**Precedence.** Stages 1–9 are the specification. User-visible text is
defined in the bad-row reasons table, the Fatal error messages table, the
warning formats in Stages 3, 6, 8 and 9, and argparse's own usage text
(Stage 1). The plan below gives build order, module responsibilities,
public signatures and records; where it differs from the Stages,
the Stages win.

### Build phases

Each phase ends with `python -m pytest` passing before the next starts.

1.  **P1 Skeleton and model:** `pyproject.toml`, `tsinvoice/__init__.py`,
    `tsinvoice/model.py`, `tests/conftest.py`, `tests/test_model.py`.
2.  **P2 Readers:** `tsinvoice/readers.py`, `tests/test_readers.py`.
3.  **P3 Merge core:** `tsinvoice/core.py`, `tests/test_core.py`.
4.  **P4 CLI and output:** `tsinvoice/writer.py`, `tsinvoice/cli.py`,
    `tsinvoice/__main__.py`, `tests/test_cli.py`.
5.  **P5 Docs:** `README.md`.

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

*   **Type / Scope**: Shared records and the normalise helper. No I/O.
*   **Proposed Changes**:
    *   `class FatalError(Exception)`: carries the message text of one row of
        the Fatal error messages table.
    *   `def normalise(text: str) -> str`: the Glossary's "Normalised text".
    *   `@dataclass(frozen=True) class Entry`: `tracker: str`,
        `order: tuple[int, int]` (argument position from 0, line number),
        `path: str` (as given), `line: int`, `client: str`,
        `description: str` (trimmed, case kept), `client_key: str`,
        `desc_key: str`, `start: datetime`, `end: datetime`, `minutes: int`.
        A `dup_key` property returns the Stage 4 duplicate key.
    *   `@dataclass(frozen=True) class Rule`: `pattern_key: str`,
        `rate: Decimal`.
    *   `@dataclass class Session`: `entries: list[Entry]`, with properties
        `first`, `start`, `end` (last entry's end), `worked_minutes`,
        `billed_minutes` (Stage 6).
    *   `@dataclass(frozen=True) class OutputRow`: the six output columns
        `date: str`, `client: str`, `description: str`, `minutes: int`,
        `amount: str`, `session_id: str`, plus `session: Session` (used for the
        overlap check and its exact-repeat exemption).

#### 4. `tsinvoice/readers.py` (Create)

*   **Type / Scope**: All file reading and row validation ("Reading any CSV
    file", Stages 2 and 3).
*   **Proposed Changes**:
    *   `def read_rates(path: str) -> list[Rule]`: implements Stage 2; raises
        `FatalError` for every fatal case.
    *   `def read_export(path: str, tracker: str, arg_index: int) -> tuple[list[Entry], list[str]]`:
        implements Stage 3; returns valid entries in file order and the
        formatted bad-row warning lines in file order; raises `FatalError`
        for file-level problems.
    *   One private helper reads a file into
        `(header_cells: list[str] | None, records: list[tuple[int, list[str], bool]])`
        using the sentinel method in "Reading any CSV file". Each record is
        `(start_line, cells, unterminated)`; start line = the reader's
        `line_num` before the record plus 1; blank records are dropped unless
        unterminated; `header_cells` is `None` when the file has no non-blank
        record or the header itself is unterminated. Other private helpers are
        the implementer's choice.

#### 5. `tsinvoice/core.py` (Create)

*   **Type / Scope**: Pure merge logic (Stages 4–8). No I/O.
*   **Proposed Changes**:
    *   `def dedupe(entries: list[Entry]) -> list[Entry]`: Stage 4; input and
        output in input order.
    *   `def join(entries: list[Entry]) -> list[Session]`: Stage 5.
    *   `def find_rate(rules: list[Rule], entry: Entry) -> Decimal | None`:
        Stage 6 rate rule.
    *   `def price(minutes: int, rate: Decimal) -> str`: Stage 6 amount
        (`Decimal`, `ROUND_HALF_UP`, two decimals, never exponent notation).
    *   `def merge(entries: list[Entry], rules: list[Rule]) -> tuple[list[OutputRow], list[str]]`:
        Stages 4–8 in order; returns sorted rows and the unrated-session
        warnings followed by the overlap warnings.

#### 6. `tsinvoice/writer.py` (Create)

*   **Type / Scope**: Output CSV (Stage 9).
*   **Proposed Changes**: `def write_rows(out_path: str, rows: list[OutputRow]) -> None`:
    implements the Stage 9 output file rules:
    `fd, tmp = tempfile.mkstemp(prefix=".tsinvoice-", dir=os.path.dirname(out_path) or ".")`;
    `os.chmod(tmp, 0o644)`; `open(fd, "w", encoding="utf-8", newline="")`
    (so `\n` is never translated); write; close; `os.replace(tmp, out_path)`.
    On any `OSError`, unlink `tmp` if it exists and raise
    `FatalError(f"{out_path}: cannot write: {e.strerror or e}")`.

#### 7. `tsinvoice/cli.py` (Create)

*   **Type / Scope**: Argument parsing and orchestration (Stage 1, Stage 9
    order).
*   **Proposed Changes**:
    *   `def build_parser() -> argparse.ArgumentParser`: program `tsinvoice`,
        `allow_abbrev=False`; `add_subparsers(dest="command", required=True)`
        with sub-command `merge` (also `allow_abbrev=False`): repeatable
        required `--tracker` parsed by `parse_tracker`, required `--rates`
        and `--out`. `--help` keeps argparse's default (prints to stdout,
        exit 0); it is the one case where stdout is used.
    *   `def parse_tracker(value: str) -> tuple[str, str]`: Stage 1 split;
        raises `argparse.ArgumentTypeError("expected NAME=PATH")` on a bad
        value.
    *   `def main(argv: list[str] | None = None) -> int`: read rates, then
        every export in argument order; `core.merge`; `writer.write_rows`;
        then print all warnings in the Stage 9 order and return 0. On
        `FatalError` print only the error line and return 2.

#### 8. `tests/conftest.py` (Create)

*   **Type / Scope**: Test fixtures (pytest fixtures, so test modules use
    them by argument name, never by import).
*   **Proposed Changes**:
    *   Fixture `write_file(tmp_path)` returns
        `write(name: str, content: str | bytes) -> str`: writes `content`
        to `tmp_path / name` (text is written as UTF-8 with `newline=""`, so
        `\r\n` in the string is kept; bytes are written as is, for BOM,
        CRLF and non-UTF-8 cases) and returns the absolute path.
    *   Fixture `run_cli(capsys)` returns
        `run(args: list[str], out_path: str | None = None) -> tuple[int, str, str, bytes | None]`:
        imports `tsinvoice.cli` inside the fixture body (so collection works
        in phases P1-P3 before `cli.py` exists), calls `main(args)`, converts a `SystemExit` from
        argparse into its exit code, reads stdout and stderr from `capsys`,
        and returns `(code, stdout, stderr, out_bytes)` where `out_bytes` is
        the content of `out_path` if given and the file exists, else `None`.
    *   Fixture `run_module()` returns
        `run(args: list[str]) -> subprocess.CompletedProcess` using
        `subprocess.run([sys.executable, "-m", "tsinvoice", *args], cwd=<repo root>, capture_output=True)`
        where repo root is the parent of `tests/`; tests pass absolute paths.

#### 8a. `tests/test_model.py` (Create)

*   **Type / Scope**: Unit tests for `normalise` and `Session`.
*   **Proposed Changes**:
    *   composed vs decomposed "é" normalise equal; "ß" equals "ss";
        whitespace runs and tabs collapse; outer spaces trimmed.
    *   `billed_minutes`: 1→6, 6→6, 7→12, 12→12, 14→18.

#### 9. `tests/test_readers.py` (Create)

*   **Type / Scope**: Unit tests for Stages 2–3.
*   **Proposed Changes**: format detection (A, B, case/spacing/BOM in header,
    trailing empty header cell, wrong order, extra column, zero-byte file →
    `FatalError`); Format A bad rows (blank End, unparseable, End ≤ Start,
    blank client); single-digit Format A date `5/1/2026 9:00` accepted;
    blank description kept; extra blank cells accepted and extra non-blank
    cells rejected (`expected 4 fields, got 5`); unterminated quote in an
    export → `read_export` returns one bad-row warning
    `unterminated quoted field` at its start line and the entries before it;
    an unterminated quote whose swallowed text exceeds the csv module's
    default field limit (131072 characters) gives the same result (not
    fatal); unterminated record with blank content (last line `"`) still
    reported; unterminated header → `FatalError` `unrecognised header`;
    file with only blank records → `unrecognised header`; quote quirk then
    open quote (`Acme,"Design"x,...,"08/10/2026 10:00` followed by a valid
    line) → one `unterminated quoted field` row; `"A"c,"multi` + newline +
    `",...` read as one valid row (no false detection); CRLF input, bare-`\r`
    input and a U+2028 inside a field read with correct line numbers; in the rates file → `FatalError`; undecodable
    bytes (cp1252 `\xe9`) → `FatalError` `cannot read`; a mid-row quote quirk such as
    `"Design" review` read normally (not fatal); huge
    duration (`99999999999`) → `invalid duration_minutes`; Format B (offset and `Z` dropped,
    seconds truncated to the minute, date-only rejected, durations `30`, `30.0` accepted and
    `29.5`, `0`, `-5`, `+5`, `1e2`, `3_0`, blank rejected); line numbers
    (physical lines; blank lines counted, including blank lines before the
    header; a `,,,` record skipped; quoted multi-line field reports its start
    line); check order when a row fails several checks; records with too
    many or too few cells; rates
    file (valid, header-only, bad header, empty pattern, non-numeric, `NaN`,
    `1e2`, `+5`, negative → `FatalError` with the exact message from the
    Fatal error messages table; rates check order; zero rate allowed).

#### 10. `tests/test_core.py` (Create)

*   **Type / Scope**: Unit tests for Stages 4–8, using hand-built `Entry`
    lists.
*   **Proposed Changes**: dedupe (identical across exports kept once; counts 2
    and 3 give 3 and the kept copies are export 1's two plus export 2's
    first; identical copies within one export all kept; case/space
    differences dedupe; one-minute difference not deduped; different trackers
    never deduped; same path twice under one NAME); join (gaps 0, 2 min
    joined; 3 min and negative not joined; phone 09:00:30 + desktop 09:07
    handoff joined; chains of 3 across trackers;
    smallest gap wins; gap tie broken by input order; claimed-successor
    A/B/C case; same-start predecessors in input order; different
    descriptions not joined); price (6 min at 10.05 → `1.01`, half-up, zero
    rate → `0.00`, 600 min at 1000000 → `10000000.00` with no exponent
    notation); rate matching (first rule wins, description-only
    match, case-insensitive, whitespace-normalised pattern, no match →
    `0.00` and the exact Stage 6 warning text); printed text from each session's own first entry
    ("Acme" vs "ACME"); sort order with input-order tie-break; session_id only
    on joined rows, sequential and unique; overlap warnings (overlap warned,
    touching not warned, different clients not warned, exact repeats (same
    duplicate key, whether from one export or kept across exports) not
    warned, same entry in two trackers warned, exact Stage 8 text, order
    (i, j)).

#### 11. `tests/test_cli.py` (Create)

*   **Type / Scope**: End-to-end tests through `main()` and one through
    `python -m tsinvoice`.
*   **Proposed Changes**: CUJ 1–6 as tests; exact output header and bytes
    (`\n` endings, no BOM, quoting of a description with a comma);
    header-only output for no valid entries; exit 2 with existing `--out`
    unchanged for an unrecognised header, a missing tracker file, a missing
    rates file and a bad rates row; bad `--tracker` values (`desk`, `=a.csv`,
    `desk=`) exit 2; missing sub-command or missing `--rates`/`--out` exit
    2; same PATH under two NAMEs gives overlap warnings; `--out` equal to an
    input path works; `--out` in a missing directory → exit 2
    `cannot write` and no `.tsinvoice-*` file left; no `.tsinvoice-*` file
    left after success; output mode is `0o644` and a symlinked `--out` is
    replaced by a regular file (both skipped on Windows); nothing on stdout;
    byte-identical output and stderr across two runs; stderr ordering across
    the three warning kinds; one test through `run_module` (the real
    `python -m tsinvoice merge` command).

#### 12. `pyproject.toml` (Create)

*   **Type / Scope**: Project metadata and pytest configuration.
*   **Proposed Changes**: `[project]` name `tsinvoice`, version `0.1.0`,
    `requires-python = ">=3.11"`, no dependencies; `[tool.pytest.ini_options]`
    `testpaths = ["tests"]`, `pythonpath = ["."]`.

#### 13. `README.md` (Create)

*   **Type / Scope**: Short user documentation.
*   **Proposed Changes**: what the tool does, the command, input and output
    formats, the dedupe/join/rounding/pricing rules in one paragraph each,
    warnings and exit codes, and how to run tests. Advise putting specific
    rate rules before broad ones and avoiding short patterns (Risks). Link to `BRIEF.md` and the
    design document.

### Verification Plan

*   **Compilation/Build**: `python -m compileall tsinvoice`
*   **Unit Tests**: `python -m pytest` from the repository root; all tests
    pass.
*   **Static Analysis & Linting**: none required.
*   **Test Coverage Requirement**: at least one test for every bullet in
    Stages 1–9, every row of the bad-row reasons, Fatal error messages,
    exit-code and worked-examples tables, and every CUJ. Each such test's
    name or docstring cites the stage, table row or CUJ it covers.
*   **E2E/Integration**: `tests/test_cli.py` runs the real command with
    `python -m tsinvoice merge ...` on temporary files.

--------------------------------------------------------------------------------

<!-- Provenance: Indicates initial structural drafting via EGM. -->

*Drafted with EGM*
