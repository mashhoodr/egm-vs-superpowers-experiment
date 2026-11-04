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
