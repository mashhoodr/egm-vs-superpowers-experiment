# stockmerge — design

Status: approved (process gate decided by the agent, see `process_log.md`).
Sources: `BRIEF.md` (fixed contract) and `stakeholder_log.md` (answers).
Items marked **[our call]** were left to us by the stakeholder.

## 1. Understanding

- **Outcome:** one clean, reproducible inventory CSV per stock-take: one row per
  real scan, per SKU per location, with case quantities converted to single
  items, overlapping exports de-duplicated, moves between locations linked,
  and every row categorised.
- **Reader [our call]:** the shop owner, opening the CSV in a spreadsheet to
  reconcile counts against the stock system and to tell shrinkage from moves.
- **Success:** the acceptance tests pass against the fixed contract; no real
  scan is lost; same inputs in the same order give byte-identical output.

## 2. Command line (fixed)

```
python -m stockmerge merge --location NAME=PATH [...] --rules RULES.csv --out INVENTORY.csv
```

- `--location` repeats; split on the first `=`. Each `--location` argument is
  one **export**. The same NAME may appear with several PATHs.
- NAME is compared exactly after trimming outer spaces, case-sensitive, and
  written to output as trimmed **[our call]**. An empty NAME or PATH, or a value
  without `=`, is a usage error.
- Exit codes: `0` success; `2` for any fatal error (usage error, unreadable
  input or rules file, unrecognised header, bad rules header). On a fatal error
  a message goes to stderr and the output file is not written or touched.

## 3. Input parsing

Header detection **[our call]:** strip a UTF-8 BOM, split as CSV, trim each
field, compare case-insensitively to the two known headers (exact column
order). Neither matches (including an empty file) → fatal, exit 2.

| | Format A | Format B |
|---|---|---|
| header | `Scanned At,SKU,Qty,Unit` | `timestamp,barcode,count,note` |
| time | `DD/MM/YYYY HH:MM` | ISO 8601 `YYYY-MM-DDTHH:MM[:SS[.fff]][offset]` |
| qty | signed whole number × unit | signed whole number, always single items |
| unit | `each` = 1, `case` = 12 (case-insensitive, trimmed) | — |
| note | — | ignored entirely |

- Whole number: `^[+-]?\d+$` after trimming.
- Format B timestamps **[our call]:** accepted via `datetime.fromisoformat`; a
  time part (`T`) is required; fractional seconds and offsets are accepted and
  the offset is discarded (wall-clock, shop local time).
- All timestamps are truncated to the minute (seconds dropped, never rounded).
  Only the minute value is used anywhere downstream.
- **Bad row** (wrong column count — including an unquoted comma in a Format B note, per the stakeholder —, blank SKU, unparseable time, non-whole qty,
  unknown unit, a quantity too long to parse, a field the CSV parser rejects): skipped with `warning: <path>:<line>: <reason>` on stderr;
  the run continues and exits 0. Line numbers are 1-based physical file lines
  (header is line 1). Fully blank lines are skipped silently.

Each good row becomes a `Scan`: location, export index, row index within
export, sku_text (outer spaces trimmed, case and zeros kept), sku_key
(normalised), minute timestamp, qty_each.

**SKU key:** trim, casefold, strip leading zeros; an all-zero SKU becomes `0`
**[our call]**.

## 4. Rules

- CSV with header `pattern,category` (BOM stripped, trimmed, case-insensitive).
  Missing/unreadable file or wrong header → fatal, exit 2 **[our call]**.
- Pattern is a case-insensitive substring. It is trimmed and casefolded, then
  tested against the row's **sku_key** (normalised SKU, as the stakeholder said
  normalisation applies to matching) **and** against the row's casefolded
  sku_text; either containing the pattern is a match **[our call]**. This lets a
  pattern copied with leading zeros (`00123`) still match, without stripping
  zeros from the pattern (which would make `0012` match `5123`). Cost: two
  spellings of one SKU can, in rare cases, get different categories.
- Header and data rows are parsed one physical line at a time, with trailing
  empty fields tolerated, like the export readers.
- First matching rule in file order wins; no match → `Uncategorised`.
- A rule with a blank pattern, or a malformed row, is skipped with a warning
  **[our call]** (a blank pattern would otherwise match everything).

## 5. De-duplication (per location only)

- Duplicate key: `(location, minute, sku_key, qty_each)`. Different locations
  never de-duplicate against each other.
- Rows inside one export are always real scans. For each key, count copies per
  export; keep `max` over exports. The k-th kept copy (k = 1..max) is the k-th
  occurrence in the **first export in `--location` order** that has at least
  k copies. The kept row carries that export's sku_text and input position.
- De-duplication runs **before** move detection **[our call]**, so a duplicated
  scan can only take part in one move.

## 6. Move detection

- Candidates: a negative scan N and a positive scan P with different
  locations, same sku_key, `P.qty == -N.qty`, `|P.minute - N.minute| <= 120`
  minutes (exactly 2 h counts).
- **Scan order:** (minute, location name, input order), where input order is
  (export index, row index).
- One-pass greedy: walk negatives in scan order; each pairs with the closest
  still-unpaired candidate positive; ties go to the earliest in scan order.
  Each row is in at most one move.
- move_id **[our call]:** `M1`, `M2`, … in pairing order; both rows get it.
- Zero-quantity scans are kept as rows **[our call]** (never lose a real scan)
  and never take part in moves.

## 7. Output

- Header exactly `location,sku,qty_each,category,move_id`; `\n` line endings,
  UTF-8, written via `csv.writer`.
- One row per kept scan, sorted by (location name, sku_key, minute, input
  order). `sku` is the kept row's sku_text; `move_id` blank if none.
- Written to a temporary file in the target directory, then renamed, so a
  failed run never leaves a partial file.

## 8. Architecture

Pipeline of small pure modules over a frozen `Scan` dataclass (chosen over a
single script, which is harder to test, and an in-memory SQLite approach,
which hides the ordering rules in SQL):

| Module | Purpose |
|---|---|
| `stockmerge/model.py` | `Scan` dataclass, `sku_key()` |
| `stockmerge/readers.py` | header detection, Format A/B row parsing, warnings |
| `stockmerge/rules.py` | load rules, `categorise(sku_key)` |
| `stockmerge/dedupe.py` | per-location max-count de-duplication |
| `stockmerge/moves.py` | greedy move pairing, move_id assignment |
| `stockmerge/writer.py` | sorting and CSV output |
| `stockmerge/cli.py`, `__main__.py` | argparse, orchestration, exit codes |

Errors: readers raise `FatalError` for header problems; `cli` catches it,
prints, exits 2. Warnings go through a callable passed in (stderr in the CLI),
which keeps modules testable.

## 9. Testing

- Unit tests per module with pytest (TDD).
- End-to-end tests run `python -m stockmerge merge` in a subprocess on
  temporary CSVs: format mix, duplicates across formats, moves, bad rows,
  fatal header, byte-identical repeat runs.
