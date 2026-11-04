# stockmerge

Merge overlapping stock-take exports into one inventory. See `BRIEF.md` for the
contract and `stakeholder_log.md` for the agreed rules.

```
python -m stockmerge merge --location "shop floor=a.csv" --location "back room=b.csv" \
  --rules rules.csv --out inventory.csv
python -m pytest
```

## Rules implemented
- Format A/B detected from the header (case/whitespace-insensitive). Unknown
  header, missing file, or bad rules header: exit 2, no output written.
- Bad rows (bad date, non-integer qty, unknown unit, blank SKU, empty line,
  wrong field count) are skipped with `warning: FILE:LINE: ...` on stderr.
- `case` = 12 items. Format B `count` is always single items; `note` ignored.
- SKU identity: trim, ignore case, ignore leading zeros. Output `sku` is the
  trimmed original spelling from the first occurrence (in `--location` order).
- Duplicates: same location + minute timestamp (seconds truncated) + SKU +
  qty_each. Repeats inside one file are real; across exports of one location
  the kept count is the max per file.
- Moves: negative + exactly opposite positive, same SKU, different location,
  within 2h inclusive (either order). Negatives processed in scan order
  (timestamp, location, input order); partner = closest in time, then scan order.

## My calls (stakeholder left open)
- `move_id` is `M0001`, `M0002`, ... numbered in the order moves are linked.
- Zero-quantity rows are kept (never lose a real scan); they never form moves.
- Rule patterns match the *normalised* SKU (upper-cased, leading zeros
  stripped), so `00123` and `123` always get the same category. A pattern
  with leading zeros therefore only matches where those zeros are inside the SKU.
- An all-zero SKU (`000`) normalises to `0`.
- Format B rows whose note has unquoted commas are kept (extra fields = note).
- Output is written atomically (temp file + rename).
