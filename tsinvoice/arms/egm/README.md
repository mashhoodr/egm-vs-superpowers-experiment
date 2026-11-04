# tsinvoice

Merge overlapping timesheet exports from two time-tracking apps into one
priced, invoice-ready CSV of sessions. Python 3.11+, standard library only.
Contract: [BRIEF.md](BRIEF.md). Design: [docs/designs/tsinvoice.md](docs/designs/tsinvoice.md).

## Usage

```
python -m tsinvoice merge \
  --tracker NAME=PATH [--tracker NAME=PATH ...] \
  --rates RATES.csv \
  --out SESSIONS.csv
```

`--tracker` repeats; one NAME may have several exports.

## Formats

- **Format A (desktop):** `Client,Description,Start,End`, times `DD/MM/YYYY HH:MM`.
- **Format B (phone):** `client,task,start_iso,duration_minutes`; ISO start
  (offsets ignored, seconds truncated), whole-number duration above zero.
- **Rates:** `pattern,hourly_rate`.
- **Output:** `date,client,description,minutes,amount,session_id`.

Headers are matched trimmed and case-insensitively. Files must be UTF-8.

## Rules

- **Duplicates.** Within one tracker, entries with the same client,
  description (ignoring case and spacing), start and end are duplicates. The
  largest count in any single export is kept, so real repeats are never lost.
  Different trackers are never deduplicated.
- **Joins.** Entries with the same client and description, where the next
  starts 0 to 2 minutes after the previous ends, become one session (any
  tracker). Joined rows get `session_id` `S1`, `S2`, ...; single entries are blank.
- **Rounding.** Worked minutes are rounded up to a multiple of 6.
- **Pricing.** The first rate rule whose pattern appears in the client or the
  description wins; amount = minutes x rate / 60, half-up to 2 decimals.
  Put specific rules before broad ones and avoid short patterns: a pattern
  like `ac` also matches a description such as "call with Acme".

## Warnings and exit codes

Warnings go to stderr: each skipped bad row (`<path>:<line>: <reason>`), each
unrated session (written with `0.00`), and each pair of overlapping sessions
for one client. Exit 0 on success; exit 2 on usage errors, unreadable or
unrecognised files, any bad rates row, or a failed write. On exit 2 `--out`
is left untouched.

## Tests

```
python -m pytest
```
