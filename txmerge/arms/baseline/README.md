# txmerge

Merge overlapping bank exports into one categorised ledger. See `BRIEF.md` for the
contract and `stakeholder_log.md` for the product answers.

```
python -m txmerge merge --account current=a.csv --account current=b.csv \
  --account card=c.csv --rules rules.csv --out ledger.csv
python -m pytest
```

## Behaviour
- **Dedupe** (per account): key = date, amount, description (trimmed, whitespace
  collapsed, case-insensitive). Each key is kept max-count-in-any-one-export times;
  surviving rows are the earliest by `--account` argument order.
- **Transfers**: outflow + inflow of equal absolute amount in different accounts,
  dates at most 3 days apart. Outflows are processed in output order; closest date
  wins, ties go to the inflow earliest in output order. Each row joins at most one
  transfer. Both legs get category `Transfer`; rules are not applied to them.
- **Categories**: first rule whose `pattern` is a case-insensitive substring of the
  description; otherwise `Uncategorised`. Blank patterns are ignored.
- **Order**: date, account name, line number in source file (then argument order).

## Decisions made where the stakeholder left it open
- `transfer_id` is `T0001`, `T0002`, ... numbered in output order of the outflow leg,
  so reruns on the same inputs give identical ids.
- Missing/unreadable export or rules file, unknown header, or bad rules header:
  exit 2, message on stderr, no output file written (output is written atomically).
- Malformed rows (bad date/amount, Debit and Credit both filled or both blank, wrong
  field count): skipped, `warning: FILE:LINE: ...` on stderr, exit 0.
- Format A Debit/Credit are taken as magnitudes (a stray sign does not flip direction).
  Amounts are rounded half-up to 2 decimals before comparison.
- Output descriptions keep the original text (outer whitespace trimmed).
