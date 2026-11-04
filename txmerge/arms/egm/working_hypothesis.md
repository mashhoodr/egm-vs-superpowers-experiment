# Working hypothesis: `txmerge`

Anchored after two rounds of stakeholder questions (see `stakeholder_log.md`). The fixed CLI and file contract is in `BRIEF.md`.

## Summary

A standard-library Python command-line tool reads several bank CSV exports per named account, removes duplicate rows that come from overlapping exports, links transfers between the user's own accounts, categorises the rest with an ordered substring rules file, and writes one sorted ledger CSV. The same inputs always give a byte-identical output.

## Behaviour agreed with the stakeholder

1. **Parsing.** Format is chosen from the header row. Format A: Debit -> negative amount, Credit -> positive. Format B: use Transaction Date, ignore Posting Date; Amount is already signed.
2. **Malformed rows** (bad date, bad amount, Format A with both or neither of Debit/Credit) are skipped with a stderr warning naming file and line; the run still exits 0.
3. **Unrecognised header** -> exit 2 with a message; no output file written.
4. **Duplicates.** Only within one account NAME. Match key = (date, amount, normalised description), where normalised = trimmed, inner whitespace collapsed, case-folded. Identical rows inside one export are real. Across exports, keep the maximum count per key, not the sum. The surviving row is the first occurrence by `--account` argument order; its description is the original text, trimmed only.
5. **Transfers.** An outflow in one account and an inflow of exactly the same absolute amount in a different account, dates at most 3 days apart either way (3 counts). Each row is in at most one transfer. Walk outflows in output order; pick the candidate inflow closest in date; tie -> the one first in output order. Both rows get category `Transfer` and the same non-empty `transfer_id`; rules are not applied to them.
6. **Rules.** Pattern is a case-insensitive plain substring of the description. First matching rule in file order wins. No match -> `Uncategorised`.
7. **Output order.** Date, then account name, then input order.

## Elephant's proposed answers to "your call" items

- `transfer_id` = `T0001`, `T0002`, ... assigned in the order pairs are made (outflow walk in output order).
- Missing or unreadable input file, missing rules file, or rules file with wrong header -> exit 2, message on stderr, no output file.
- Balance column is ignored.
- Format B amounts: thousands separators stripped as in Format A; currency symbols are not accepted (row is malformed).
- Zero-amount rows are kept, categorised by rules, never part of a transfer.
- Rules match against the trimmed original description. Rule rows with a blank pattern are skipped with a warning.
- Same path given twice: allowed, no warning (max-count dedup absorbs it).
- Input quirks handled: UTF-8 BOM, blank lines, whitespace around header cells, quoted fields (Python `csv` module).
- Amounts held as `Decimal`, never float.
- On success: one summary line on stderr; nothing on stdout.
- "Input order" is defined as (`--account` argument position, line number in that file).
