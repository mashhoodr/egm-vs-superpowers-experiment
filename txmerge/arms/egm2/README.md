# txmerge

Merge overlapping bank CSV exports into one deduplicated, categorised ledger.

```
python -m txmerge merge \
  --account current=cur_jan.csv --account current=cur_feb.csv \
  --account card=card.csv \
  --rules rules.csv --out ledger.csv
```

Exit codes: `0` success (bad rows are skipped with a warning on stderr);
`2` a file-level or command-line error (no ledger is written, an existing one
is left unchanged).

Run the tests with `python -m pytest`.

The full behaviour (dedup, transfer pairing, rules, messages) is defined in
[docs/designs/txmerge.md](docs/designs/txmerge.md).
