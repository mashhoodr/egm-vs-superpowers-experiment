# txmerge: merge overlapping bank exports into one ledger

* **Author:** Elephant (EGM arm), for Mashhood Rastgar
* **Date:** 2026-11-02

## Overview

`txmerge` is a standard-library Python command-line tool for one person who downloads CSV exports from their bank accounts every few weeks. The exports overlap in date range, and money moved between the person's own accounts looks like spending in one and income in the other. The tool reads several exports per named account, removes the duplicate rows that the overlaps create, links transfers between accounts, categorises everything else with an ordered rules file, and writes one sorted ledger CSV. Running it twice on the same inputs gives a byte-identical file.

The command line, input formats, rules header and output header are fixed by `BRIEF.md` and are not repeated here.

## Analysis

Six Goldfish lenses reviewed the working hypothesis (raw summaries in `reviews/brainstorm/`). No lens proposed a different architecture: a single in-memory pass is the right shape for files a person downloads by hand. All Blocker and Major points were about places where two implementers would write different bytes or exit codes. They group as follows.

1. **Stage order was implied, not stated (zoom-out, structural, design, readiness).** Transfer pairing walks "output order", which only exists after dedup and sort. The order is now fixed: read and validate everything, parse, dedup per account, sort, pair transfers, apply rules to non-transfer rows, write.
2. **Which copies survive dedup was undefined when the maximum count comes from a later export (all six lenses).** The stakeholder settled it in round 3: keep the first N occurrences in input order, where N is the largest count in any single export. Each kept copy keeps its own text and its own input position.
3. **Output bytes were not pinned (zoom-out, codebase, comprehension, design, readiness).** Python's `csv` writer ends lines with `\r\n` by default, and `Decimal` can print `-0.00`. These are now fixed (Key Decisions, D9).
4. **Amount and date grammar were too loose (codebase, design, readiness, comprehension).** `Decimal()` accepts `NaN`, `1e3` and `1_000`; stripping every comma accepts `1,2,3`. A strict pattern check now runs before conversion, and more than two decimals is malformed rather than silently rounded.
5. **Failure handling left an existing ledger at risk (all lenses except zoom-out's narrower point).** Everything is read and validated before the output is touched, and the output is written to a temporary file and renamed, so exit 2 never changes an existing file.
6. **Header, row-shape, encoding and CSV-reader errors could crash with a traceback (codebase, design, readiness).** Each now has a defined outcome in one error table.
7. **Structure (structural).** The design document should be laid out by pipeline stage with a Definitions section and a decision log that says where each decision came from. A format-neutral record means a third bank format is one new table entry.

Counter-arguments weighed and kept as stated:

- **Greedy transfer pairing can link unrelated movements.** A £50 card purchase and an unrelated £50 credit to the current account within 3 days will be linked. The stakeholder specified this rule; it is recorded as a known limitation, not changed.
- **Rules match the trimmed original text, so `coffee shop` does not match `COFFEE  SHOP`.** Zoom-out argued for matching the normalised text. The stakeholder chose the original text in round 3.
- **Skipping malformed rows with exit 0 risks silent loss.** The stakeholder requires exit 0. The mitigation is a warning per row and a skipped-row count in the summary line.
- **A `--verbose` flag to explain dedup and pairing (comprehension).** Out of scope: not asked for, and the summary counts are enough to notice a problem.

## Goals vs. Non-Goals

* **In-Scope Goals:**
  - Parse Format A and Format B exports, detected from the header row.
  - Remove duplicates across exports of the same account by max count, never losing a real repeated purchase.
  - Link transfers between different accounts with shared `transfer_id` and category `Transfer`.
  - Categorise every other row by first matching rule, else `Uncategorised`.
  - Byte-identical output for identical inputs.
  - Clear stderr warnings for skipped rows and exit 2 for file-level errors, leaving any existing ledger untouched.
* **Out-of-Scope Non-Goals:**
  - Fuzzy or truncated description matching.
  - Regex or wildcard rules.
  - Using the Balance column to check for gaps.
  - Currency symbols or currency conversion.
  - Encodings other than UTF-8 (with or without BOM).
  - Incremental or append-only updates; every run rebuilds the whole ledger.
  - Stable `transfer_id`s across different input sets.
  - A `--verbose` mode or any flag beyond the brief's contract.

## Alternatives Weighed

- **Sum counts across exports instead of max.** Rejected: the stakeholder said max; summing doubles every overlapping row.
- **Treat every identical row as a duplicate (set semantics).** Rejected: two coffees on the same day are two purchases.
- **Fuzzy description matching for dedup.** Rejected by the stakeholder; exact match after normalising whitespace and case only.
- **Use Posting Date for Format B.** Rejected by the stakeholder; Transaction Date is used.
- **Regex rules.** Rejected by the stakeholder; plain case-insensitive substring.
- **Match rules against the normalised description.** Rejected by the stakeholder in round 3; match the trimmed original text.
- **Globally optimal transfer matching (e.g. bipartite matching).** Rejected: the stakeholder specified a greedy walk over outflows in output order with closest-date choice; it is simpler and deterministic.
- **Every surviving duplicate copy inherits the first export's text.** Rejected by the stakeholder in round 3; each copy keeps its own text.
- **Round amounts with more than two decimals.** Rejected: rounding silently changes money and needs a rounding policy; such rows are malformed instead.
- **Fall back to cp1252 when UTF-8 decoding fails.** Rejected: the output would depend on a guess; fail with exit 2 instead.
- **Format registry with parser classes or plug-ins.** Rejected as speculative. Two formats are entries in one small table (header tuple plus a row function); a third format is one more entry.
- **Write output directly to `--out`.** Rejected: a late failure or crash would leave a partial or emptied ledger. Temp file plus rename instead.

## Key Decisions & Staging for Next Steps

Source tags: [B] = `BRIEF.md`, [S] = stakeholder answer (`stakeholder_log.md`), [E] = Elephant's call where the stakeholder said "your call", with the reason.

**Pipeline**
- D1 [S/E] Stages run in this order: read and validate every input and the rules file; parse rows into records; dedup per account; sort; pair transfers; apply rules to non-transfer rows; write. Nothing touches `--out` until every check has passed.

**Definitions**
- D2 [E] *Export* = one `--account NAME=PATH` argument. The same path given twice is two exports (max-count dedup absorbs it, so no warning is needed).
- D3 [S/E] *Input position* = (index of the `--account` argument, 0-based; line number of the record in that file).
- D4 [S] *Normalised description* = trimmed, runs of whitespace collapsed to one space, case-folded: `" ".join(s.split()).casefold()`.
- D5 [S] *Output order* = sort by (date, account NAME, input position). Account NAME compares as a plain Python string (code-point order, case-sensitive), used exactly as typed.
- D6 [S/E] *Outflow* = amount < 0; *inflow* = amount > 0. A zero amount is neither.

**Parsing**
- D7 [B/S] Format A: Debit gives a negative amount, Credit a positive one. Format B: Transaction Date and signed Amount; Posting Date is ignored and never validated. Balance is ignored [E].
- D8 [E] Amount grammar, checked on the trimmed cell before `Decimal`: digits with optional correctly grouped thousands commas (`1,250.00` or `1250.00`), at most two decimals. Format B allows one leading `-`. Anything else is malformed: more than two decimals, a sign in a Format A cell, a currency symbol, exponents, `NaN`. Amounts are quantised to 0.01 at parse time and held as `Decimal`. Zero is stored as positive zero.
- D9 [E] Dates: Format A `D/M/YYYY`, Format B `YYYY-M-D`, with one- or two-digit day and month accepted (reason: never lose a real transaction); must be a real calendar date. Otherwise malformed.
- D10 [S/E] Malformed row (bad date, bad amount, Format A with both or neither of Debit/Credit, wrong number of fields): skip, warn on stderr with file and line, exit 0. "Filled" means non-empty after trimming. A row whose cells are all empty is skipped silently.
- D11 [E] Header: first non-empty row; BOM removed; each cell trimmed; must equal the format's column list exactly (case-sensitive, same order, same count). A file with no header (empty) is an unrecognised header. A header-only file has zero rows and is fine [S].
- D12 [E] Files are read as `utf-8-sig` with the `csv` module (quoted fields, embedded commas). A decode error or `csv.Error` makes the file unreadable: exit 2.

**Dedup**
- D13 [S] Only within one account NAME, across all its exports whatever their format. Key = (date, amount, normalised description). For each key, N = the largest count in any single export; keep the first N occurrences in input-position order. Each kept row keeps its own trimmed original description and its own input position.

**Transfers**
- D14 [S] Walk outflows in output order. Candidates: unpaired inflows in a different account NAME, amount equal to the outflow's absolute amount, |date difference| ≤ 3 days (either direction). Pick the smallest |difference|; tie → the candidate first in output order. Both rows get category `Transfer` and the same `transfer_id`; rules are not applied.
- D15 [E] `transfer_id` = `T` followed by the pair number zero-padded to at least four digits (`T0001`, `T0002`, ... `T10000`), numbered in pairing order. Reason: readable and deterministic for identical inputs.

**Rules**
- D16 [S] A pattern matches when it is a case-insensitive substring of the trimmed original description. First matching rule in file order wins; no match → `Uncategorised`.
- D17 [E] Rules file: same reader as inputs; header must be exactly `pattern,category` after trimming; pattern and category cells trimmed; a row with a blank pattern, blank category or wrong field count is skipped with a warning. A missing or unreadable rules file, or a wrong header, exits 2. Case-insensitive = `casefold()`. A rule category literally named `Transfer` is allowed and has no special meaning.

**Output and messages**
- D18 [E] Output: UTF-8 without BOM, `\n` line endings, `csv.QUOTE_MINIMAL`, header always written, amount printed with exactly two decimals, no thousands separators, `-` only for negatives, never `-0.00`. Written to a temp file in the same directory, then renamed over `--out`.
- D19 [E] Exit codes: 0 success; 2 for any usage, input-file, rules-file or output-path error (matches `argparse`, which exits 2 on usage errors). On exit 2 no output is created and an existing `--out` is unchanged.
- D20 [E] `--account` value split on the first `=`; empty NAME or PATH, or no `=`, is a usage error (exit 2).
- D21 [E] Messages: `txmerge: warning: PATH:LINE: reason` and `txmerge: error: reason`. On success, one summary line on stderr with counts (rows read, malformed skipped, duplicates removed, transfer pairs, uncategorised); nothing on stdout.

**Known limitation**
- Greedy pairing can link two unrelated equal amounts within 3 days. Accepted as specified.

**Next step:** `/egm-draft` ingests this brief as its Priority 1 source.
