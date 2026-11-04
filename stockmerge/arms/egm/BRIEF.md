# Brief: `stockmerge` — merge overlapping stock-take scans into one inventory

> This is the only document every arm receives. Product questions go to the
> stakeholder (see your arm instructions). Do not read anything under `_judge/`.

## The problem
My shop does stock-takes with two barcode scanners, and they export CSVs in
different formats. We count per location ("shop floor", "back room" and so
on). The same location often gets scanned twice, so the exports overlap and
the same scan shows up more than once. Stock also moves between locations,
which looks like a loss at one location and a gain at another. I want one
clean inventory, per SKU per location, with moves linked and SKUs categorised.

## Fixed contract (the acceptance tests rely on this, don't change it)

- Python 3.11+, standard library only at runtime. `pytest` allowed for tests.
- Package lives in `stockmerge/` at your repo root and runs as:

```
python -m stockmerge merge \
  --location NAME=PATH [--location NAME=PATH ...] \
  --rules RULES.csv \
  --out INVENTORY.csv
```

  `--location` may repeat, and the same NAME may appear with several PATHs
  (several exports of one location).

- **Input formats.** The format is detected from the header row.
  - **Format A (scanner 1):** header `Scanned At,SKU,Qty,Unit`.
    `Scanned At` is `DD/MM/YYYY HH:MM`. `Unit` is `each` or `case`. `Qty` is a
    whole number and may be negative (an adjustment).
  - **Format B (scanner 2):** header `timestamp,barcode,count,note`.
    `timestamp` is ISO 8601 (`2026-03-05T14:30:12`). `count` is a signed whole
    number. `note` is free text.
- **Rules file:** CSV with header `pattern,category`.
- **Output:** CSV with header exactly
  `location,sku,qty_each,category,move_id`
  - One row per scan kept. `qty_each` is a signed whole number of single
    items; `move_id` blank unless the row is part of a move.
- Exit code 0 on success.

## What I want
1. Duplicates from overlapping exports removed — but never lose a real scan.
2. Moves between locations recognised and linked, not counted as shrinkage.
3. Everything categorised by my rules.
4. Running it again on the same inputs gives the same output.

The rest is yours to design, and to ask me about.
