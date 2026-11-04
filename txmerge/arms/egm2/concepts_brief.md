# txmerge: merge overlapping bank exports into one ledger

* **Author:** Mashhood Rastgar (Elephant: Claude)
* **Date:** 2026-11-02

## Overview

`txmerge` is a small command-line tool for one person who downloads CSV exports
from their bank accounts every few weeks. The exports overlap in time, so one
transaction can appear in several files. The person also moves money between
their own accounts, which looks like spending in one account and income in the
other. `txmerge` reads all the exports, removes the copies that overlap, links
the two sides of each transfer, labels every other row using the person's
rules, and writes one CSV ledger. Running it again on the same inputs gives a
byte-identical file.

It is Python 3.11+, standard library only, run as
`python -m txmerge merge --account NAME=PATH ... --rules RULES.csv --out LEDGER.csv`.
The input formats, rules file and output columns are fixed by `BRIEF.md`.

## Analysis

Six Goldfish reviewers (design, codebase details, zoom out, comprehension,
implementation readiness, structure) reviewed the anchored hypothesis in
BRAINSTORM mode through the synthesizer. After merging duplicates they raised
3 Blockers, 16 Majors and 9 Nits. Full text: `brainstorm_synthesis.md`.

**What is wrong or missing (Blockers):**

* **Which copies survive dedup was undefined.** When a later export has more
  copies of a transaction than an earlier one, the extra copy's position sets
  the sort order, which drives greedy pairing and transfer-id numbers, so
  "byte-identical" depends on it. Resolved: a fixed algorithm (walk exports in
  argument order; keep a row while fewer than the target count are kept) with a
  worked example; all kept copies of a key use the earliest occurrence's text
  (stakeholder round 3).
* **Amount grammar and number type.** `float`, or an unchecked `Decimal()`
  that accepts `NaN` and `1e3`, breaks exact dedup and transfer matching.
  Resolved: strict regex, then `Decimal`, `-0.00` printed as `0.00`.
* **"Byte-identical" was not defined down to bytes.** `csv.writer` writes
  `\r\n` by default. Resolved: UTF-8 without BOM, `\n`, minimal quoting.

**Main risks (Majors), and how the brief now handles them:**

* Banks that write `0.00` in the unused Debit/Credit column would have every
  row skipped as "both filled" while the run exits 0, losing a whole account
  silently. Stakeholder left it to the designer: a Debit or Credit that
  parses to zero counts as blank (decision 23).
* A cp1252 export (`£` as byte 0xA3) would crash with a traceback (exit 1).
  Now a file-level error: exit 2 naming the file.
* A blank rule pattern matches everything. Now skipped with a warning.
* Pipeline order needed to be explicit so "output order" is defined before
  pairing: parse, dedup, sort, pair, categorise, write.
* Atomic write: validate all inputs first, write a temp file in the output
  directory, `os.replace`. The temp file is created with mode 0600; this is
  kept (it is private bank data) and documented. No `fsync` (not needed for a
  personal tool).
* Header, blank-line, wrong-cell-count and date strictness rules each needed
  one sentence: per-cell trim, case-sensitive, blank lines skipped, wrong count
  skipped with warning, zero-padded dates only, header-only file is valid,
  empty file is exit 2.
* Account-name sort is plain Python string order (codepoint, case-sensitive).

**Consequences of settled rulings that the design must state so testers do not
"fix" them:** greedy pairing can leave an outflow unpaired when a full matching
existed; a card refund can pair with an unrelated outflow; two names pointing
at the same file are two accounts and can pair that file's rows with each
other.

**Strongest counter-argument to the whole approach:** the max-count rule
cannot tell a real third coffee in export 2 from a copy, if export 1 was cut
off part-way through that day. The stakeholder chose max-count knowing this;
any rule that does better needs data the exports do not carry.

## Goals vs. Non-Goals

* **In-Scope Goals:**
  * Read Format A (current account) and Format B (credit card) files, chosen by
    the header row.
  * Remove copies of a transaction that appear in more than one export of the
    same account, without ever dropping a real repeated transaction.
  * Find transfers between two different accounts, give both rows the category
    `Transfer` and a shared `transfer_id`.
  * Label all other rows with the first matching rule, or `Uncategorised`.
  * Same inputs in the same order give a byte-identical ledger.
  * Clear errors: bad files stop the run with exit code 2 and no output; bad
    single rows are skipped with a warning on stderr.
* **Out-of-Scope Non-Goals:**
  * Fuzzy description matching (truncated or reworded text is a different
    transaction).
  * Updating an existing ledger in place; every run rebuilds from the inputs.
  * Using the Balance column (ignored).
  * Stopping a card refund from pairing with an unrelated same-amount outflow
    (stakeholder accepted this).
  * Regex or whole-word rules; currencies; formats other than A and B.

## Alternatives Weighed

* **Dedup by summing counts across exports, or by keeping one row per key.**
  Summing double-counts every overlap. One row per key loses the second of two
  identical coffees on the same day. Rejected for "keep the maximum count seen
  in any single export".
* **Dedup across different account names that point at the same file.**
  Rejected by the stakeholder: different names are different accounts.
* **Fuzzy matching of descriptions (edit distance, prefix match).** Rejected:
  the stakeholder wants exact matching after trimming, whitespace collapse and
  case folding; fuzzy matching risks losing real transactions.
* **Optimal (global) transfer matching, e.g. minimum total date gap.** Rejected
  for the stakeholder's greedy rule: outflows in output order, nearest inflow,
  ties to the first in output order. Simpler and easy to predict.
* **Using descriptions as transfer hints.** Rejected by the stakeholder;
  amount, account and date gap only.
* **Hash-based transfer ids.** Rejected for sequential `T0001`-style ids in
  pairing order: readable and still deterministic.
* **Using Posting Date for Format B.** Rejected by the stakeholder; Transaction
  Date is used.
* **Float arithmetic.** Rejected for `decimal.Decimal` so equal amounts compare
  equal and output is exact.

## Key Decisions & Staging for Next Steps

Decided with the stakeholder (see `stakeholder_log.md`):

1. **Same transaction** = same account name, same ledger date, same amount,
   same normalised description (outer spaces trimmed, runs of whitespace
   collapsed to one space, case folded). Nothing fuzzier.
2. **Count rule.** Repeats inside one export are real. Across the exports of
   one account, each key appears in the ledger as many times as the largest
   count in any single export. The kept text comes from the first occurrence by
   `--account` argument order, outer spaces trimmed, case kept.
3. **Format B date** = Transaction Date. Posting Date is ignored.
4. **Transfer** = an outflow in one account and an inflow of exactly the same
   absolute amount in a different account, ledger dates at most 3 calendar days
   apart (inclusive). Descriptions play no part. Card payments count.
5. **Pairing.** Each row is in at most one transfer. Walk outflows in output
   order; pair each with the unpaired inflow closest in date; ties go to the
   inflow that comes first in output order.
6. **Transfer rows** get category `Transfer`; rules are not applied to them.
7. **Rules**: case-insensitive substring, first match in file order wins, no
   match gives `Uncategorised`.
8. **Order**: date, then account name, then input order.
9. **Errors**: unrecognised header gives exit 2, a message, and no output file.
   A Format A row with both Debit and Credit blank, or malformed, is skipped
   with a stderr warning naming file and line; the run still exits 0.
10. **Always rebuild**; never read an existing ledger.
11. Two account names are always two accounts, even for the same file. The
    same file given twice for one account is handled by the count rule.

Decided by the Elephant where the stakeholder said "your call":

12. `transfer_id` = `T` + 4-digit zero-padded sequence (`T0001`), numbered in
    pairing order; grows past 4 digits if needed.
13. Missing or unreadable input or rules file, malformed `--account` value,
    or rules file without the `pattern,category` header: exit 2, message on
    stderr, no output file.
14. Format A row with both Debit and Credit filled: malformed, skip and warn.
15. Amounts: `decimal.Decimal`; thousands separators allowed in both formats;
    an optional leading sign in Format B; anything else (currency symbols,
    brackets, more than 2 decimals) makes the row malformed. Format B bad rows
    are skipped and warned like Format A.
16. Zero amounts: kept in the ledger and categorised; never part of a
    transfer. `-0.00` is written as `0.00`.
17. Headers: a UTF-8 byte-order mark and spaces around each header cell are
    ignored; names are otherwise exact (case-sensitive). Blank lines are
    skipped silently.
18. Rules rows with a blank pattern or blank category are skipped with a
    warning (a blank pattern would match everything). `Transfer` is allowed as
    an ordinary category label with no special meaning.
19. Balance column is ignored.
20. The same account name may receive files in both formats; they are one
    account for dedup and transfers.
21. On success, one summary line goes to stderr (rows read, duplicates
    removed, transfers, rows skipped); stdout stays empty.
22. Output: UTF-8 without BOM, `\n` line endings, minimal quoting, written to
    a temporary file and renamed so a failed run leaves no partial file.

Added after the Goldfish brainstorm review (stakeholder round 3 and designer):

23. A Debit or Credit cell that parses to zero (`0.00`, `0`) counts as blank
    for the "both blank / both filled" test. (E)
24. Rules match against the kept description (outer spaces trimmed), not the
    whitespace-collapsed key; case-insensitive (`casefold`). (S)
25. All kept copies of a duplicate key use the trimmed text of the
    first-ever occurrence (earliest argument, earliest line). (S)
26. Two names pointing at one file are two accounts; their rows may pair
    with each other as transfers. Accepted and documented. (E)
27. Header-only file is valid (zero rows). Empty file, non-UTF-8 file, or a
    header with an extra (even empty) column is a file-level error, exit 2. (E)
28. Output file is created with mode 0600 (temp file then rename); no fsync. (E)
29. Two parse functions, no format registry or class hierarchy. (E)

Next step: `/egm-draft` ingests this brief.
