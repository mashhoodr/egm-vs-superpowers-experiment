# stockmerge

Merge overlapping stock-take scans from two barcode scanners into one inventory
CSV: copies across exports of one location are removed, moves between
locations are linked, and every other row is categorised by your rules.
Python 3.11+, standard library only. Design: `docs/designs/stockmerge.md`.

## Usage

```
python -m stockmerge merge \
  --location NAME=PATH [--location NAME=PATH ...] \
  --rules RULES.csv \
  --out INVENTORY.csv
```

The same NAME may be given with several PATHs (several exports of one location).

## Inputs

- **Format A**: header `Scanned At,SKU,Qty,Unit`; time `DD/MM/YYYY HH:MM`;
  `Unit` is `each` or `case` (a case is 12).
- **Format B**: header `timestamp,barcode,count,note`; time
  `YYYY-MM-DDTHH:MM:SS[.ffffff]` (no time zone); the note is ignored.
- **Rules**: header `pattern,category`. A pattern matches when it is a
  substring of the SKU, ignoring case and leading zeros. First match wins.

## Output

Header `location,sku,qty_each,category,move_id`, one row per kept scan, sorted
by location, normalised SKU, minute, input order. Move rows have category
`Move` and a shared `move_id` (`M0001`, ...).

## Exit codes and messages

- `0` success (bad rows are skipped with `stockmerge: warning: PATH:LINE: reason`).
- `2` usage error, unreadable or unrecognised file, `--out` naming an input,
  or a failed write. `--out` is never touched on exit 2.
- On success stderr ends with
  `stockmerge: read R rows, removed D duplicates, skipped S rows, linked M moves, wrote W rows`.

## Builder decisions (owner may overrule)

R1.1 (no abbreviated options), R1.2, R1.3, R1.4, R1.5, R2.1, R2.2, R3.1, R3.2,
R3.4, R3.5, R4.1, R4.2, R4.3, R4.5, R4.6, R4.8, R4.9, R4.10, R4.11, R4.12,
R5.6, R6.4, R8.1 (code-point order), R9.2, R9.3. See the design doc for each.

## Worked example

```
python -m stockmerge merge --location back=b.csv --location shop=s1.csv \
  --location shop=s2.csv --rules rules.csv --out inv.csv
```

```
location,sku,qty_each,category,move_id
back,ABC,-6,Move,M0001
shop,0042,-1,Spares,
shop,abc,6,Move,M0001
shop,abc,6,Uncategorised,
```

## Tests

`python -m pytest`
