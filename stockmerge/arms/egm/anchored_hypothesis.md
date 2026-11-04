# Anchored feature hypothesis: `stockmerge`

A stdlib-only Python 3.11 command line tool (`python -m stockmerge merge --location NAME=PATH ... --rules RULES.csv --out INVENTORY.csv`)
that reads stock-take CSV exports from two barcode scanner formats, removes copies of the same scan that
appear in overlapping exports of one location (never dropping a real repeat scan), links a stock-out at one
location to the matching stock-in at another as a move, categorises every other row by substring rules, and
writes one deterministic CSV (`location,sku,qty_each,category,move_id`, one row per kept scan).

## Fixed contract (from the owner, cannot change)
- Format A header `Scanned At,SKU,Qty,Unit`; time `DD/MM/YYYY HH:MM`; unit `each` or `case`; signed whole Qty.
- Format B header `timestamp,barcode,count,note`; ISO 8601 time with seconds; signed whole count; free-text note.
- Format detected from header row. Rules CSV header `pattern,category`. Exit 0 on success.
- `--location` repeats; the same NAME may have several PATHs (several exports of one location).

## Behaviour settled with the owner
- A case is always 12 items (every SKU). `qty_each = Qty * 12` for case rows.
- SKU normalisation for comparison: trim, ignore case, strip leading zeros (`00123` == `123`).
- Time compared to the minute; Format B seconds truncated, not rounded. Same clock, no time zones.
- Same scan = same location name, same minute, same qty_each, same normalised SKU. Scanner does not matter.
- Identical rows inside one export are two real scans; keep both.
- Across exports of one location: per scan key, keep the highest count seen in any single export, not the total.
  Rows kept come first from earlier `--location` arguments.
- Dedup only within one location name, never across locations.
- Output `sku` = the first occurrence's text (outer spaces trimmed, case and zeros kept), first by `--location` order.
- Move = a negative row and a positive row of exactly opposite qty_each, same normalised SKU, different location,
  timestamps at most 2 hours apart (2h exactly counts). Either may come first. Notes are ignored.
  Process negatives in scan order (timestamp, location name, input order). For each, choose the unmatched
  positive partner closest in time; tie -> earliest in scan order. Each row in at most one move.
  Both move rows get category `Move` and the same non-empty move_id; rules are not applied to them.
- Non-move rows: first rule (file order) whose pattern is a case-insensitive substring of the SKU wins;
  no match -> `Uncategorised`. move_id blank.
- Output sorted by location name, normalised SKU, timestamp, input order.
- Errors: unknown header -> exit 2, message, no output file written. Malformed row, bad date, non-whole qty,
  blank SKU, Format A unit not each/case -> skip row, warn on stderr with file and line, still exit 0.

## Builder's calls (owner said "your call")
- Dedup runs before move matching.
- Rules match against the normalised SKU (so a SKU gets the same category whichever scanner read it).
- Quantity 0 rows are kept (they are real scans), categorised by rules, never part of a move.
- Location names compared and written exactly as typed after trimming outer spaces; empty name is an error.
- Rules file: wrong header -> exit 2; blank pattern or blank category row -> skip with warning.
- Same PATH given twice for one location -> treated as two exports (dedup makes it harmless).
- `--location` without `=` or a missing/unreadable file -> exit 2 with a message, no output written.
- move_id = `M0001`, `M0002`, ... in the order the moves are formed (negatives in scan order).
