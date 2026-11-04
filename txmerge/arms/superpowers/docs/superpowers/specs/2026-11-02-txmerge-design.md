# txmerge — design spec

Date: 2026-11-02. Source: `BRIEF.md` + stakeholder answers in `stakeholder_log.md`.

## Understanding (intent)
- **Use:** monthly spending review over one clean ledger built from overlapping bank CSV exports. *(assumed — stakeholder left it to us)*
- **Worst failure:** losing a real transaction, or counting money twice (duplicate or transfer counted as spend).
- **Success:** duplicates collapsed, transfers linked and labelled, everything else categorised, byte-identical output on re-run.

## Fixed contract (from brief, unchanged)
- Python 3.11+, stdlib only at runtime; pytest for tests. Package `txmerge/` at repo root.
- `python -m txmerge merge --account NAME=PATH [...] --rules RULES.csv --out LEDGER.csv`.
  `--account` repeats; one NAME may have several PATHs.
- Format A header `Date,Description,Debit,Credit,Balance`, date `DD/MM/YYYY`, debit/credit positive or blank, may have thousands separators.
- Format B header `Transaction Date,Posting Date,Details,Amount`, dates `YYYY-MM-DD`, signed amount (negative = spend).
- Rules CSV header `pattern,category`.
- Output header exactly `date,account,description,amount,category,transfer_id`; ISO date; signed amount, 2 decimals; `transfer_id` blank unless in a transfer. Exit 0 on success.

## Approaches considered
1. **Pipeline of pure stages (chosen).** read → dedupe → order → pair transfers → categorise → write. Each stage a small module with plain data in/out; easy to unit test and reason about determinism.
2. Single streaming pass. Fewer allocations, but transfer pairing and "max count across files" both need the full set, so it ends up buffering anyway with tangled logic.
3. In-memory `sqlite3` with SQL for dedupe/pairing. Stdlib-legal, but the greedy pairing rule is awkward in SQL and harder to test; overkill for personal-scale files.

## Behaviour

### Parsing
- Files read as UTF-8 with optional BOM (`utf-8-sig`) via `csv`. Header cells are stripped before comparison; format chosen by exact header match.
- Header matching neither format → **exit 2**, message on stderr, no output file.
- Missing/unreadable input file or rules file → **exit 2**, message, no output file. *(our choice: silently skipping an export could lose transactions)*
- Fully blank lines are ignored silently.
- Rows are parsed one physical line at a time with a strict `csv` reader, so a malformed quote (e.g. an unclosed `"`) or an over-long field spoils only its own line: warning `WARNING: <file>:<line>: malformed CSV (<reason>)`, row skipped, later lines unaffected. Quoted fields therefore cannot span lines. A malformed header line → unrecognised header, exit 2.
- Format A: amount = credit − debit. Thousands separators (`,`) removed. A column holding zero (e.g. `0.00`) counts as blank. Exactly one non-zero column → that amount (debit negative, credit positive); both blank → **skip row**; both non-zero → **skip row**; both present but zero (at least one literally `0.00`) → keep the row with amount `0.00`; negative values are a bad row. Skips, warning to stderr naming file and line number. Balance ignored.
- Format B: date = **Transaction Date**; Posting Date ignored everywhere. Amount used as-is.
- An amount must be plain decimal digits after trimming and removing commas (`[+-]?(\d+(\.\d*)?|\.\d+)`); exponents (`1e5`), NaN, etc. are unparseable.
- Unparseable date or amount → skip row with the same warning. Skipped rows never fail the run (exit 0).
- Amounts are `decimal.Decimal`, never float.
- Each parsed row records: account, date, amount, raw description (outer whitespace trimmed), and its *source position* = (index of the `--account` argument, line number in file).

### Duplicate removal
- Scope: per account name only. Different account names never deduplicate against each other.
- Key: (account, date, amount, normalised description), where normalised = trim, collapse internal whitespace runs to one space, casefold. Balance is not part of the key.
- For each key, count occurrences in each file (each `--account` argument is one file). Ledger keeps **max count over files** (not the sum). Passing the same file twice therefore changes nothing.
- Which instances survive: the first *N* occurrences in source-position order (argument order, then line). Each survivor keeps its **own** source position, which is used for output sorting.
- Description written for every surviving instance of a key: the trimmed original text of the key's first occurrence in argument order (case preserved).

### Output order
Sort by (date, account name, source position). This order is the "output order" used below.

### Transfer pairing
- A pair = one outflow (amount < 0) and one inflow (amount > 0) with `abs` amounts equal, in **different accounts**, dates at most **3 days** apart (inclusive). Description irrelevant. Credit card payoffs qualify under the same rule.
- Greedy, deterministic: walk outflows in output order; for each, among unpaired qualifying inflows pick the smallest absolute date difference; ties → earliest in output order. Each row in at most one pair.
- `transfer_id`: `T0001`, `T0002`, … in the order pairs are formed (zero-padded to 4 digits, wider if > 9999). Both rows share the id. *(our choice)*
- Both rows get category `Transfer`; rules are not applied to them.
- Unmatched outflows/inflows are ordinary rows.

### Categorisation
- Rules read in file order. A rule matches when `pattern.casefold()` is a substring of the output description's `casefold()`. First match wins. Rule rows with an empty pattern or an empty category are ignored. Rules CSV that is malformed (strict `csv`) → exit 2.
- No match → `Uncategorised`.
- Same treatment for inflows and outflows. *(our choice)*

### Writing
- Output written only after all inputs parse successfully (no partial file on exit 2). Rows are formatted in memory, written to a temp file beside the target and `os.replace`d into place, so a failure never leaves a partial or truncated output. An amount too large for 2-decimal formatting → exit 2, no output.
- `csv` writer, `\n` line endings, UTF-8, header exactly as contract. Amount = `Decimal.quantize(Decimal("0.01"))`, formatted with 2 decimals (`-12.50`; input `1,250` → `1250.00`); `-0.00` rendered `0.00`.
- Same inputs → byte-identical output (no timestamps, no set/dict-order dependence).

## Pipeline order (must hold)
read → dedupe → sort → pair transfers → categorise → write. Transfer pairing always runs on **deduplicated** rows.

## Architecture
```
txmerge/
  __main__.py     # calls cli.main()
  cli.py          # argparse, exit codes, wiring
  model.py        # Transaction dataclass, InputError
  readers.py      # header detection, Format A/B row parsing, warnings
  dedupe.py       # max-count-per-file dedupe
  transfers.py    # sort key + greedy pairing
  categorise.py   # rules loading + matching
  writer.py       # CSV output formatting
tests/            # unit test per module + CLI end-to-end
```
Each module exposes plain functions over lists of `Transaction`; only `cli.py` does exits and file writes.

## Error handling summary
| Case | Result |
|------|--------|
| Unknown header | exit 2, stderr message, no output |
| Missing input or rules file | exit 2, stderr message, no output |
| Bad `--account` value (no `=`) / bad rules header / malformed rules CSV | exit 2 (argparse-style usage error) |
| Amount unformattable at 2dp (e.g. 40 digits) | exit 2, stderr message, no output |
| Bad row (malformed CSV line, date/amount unparseable incl. exponent form, A both non-zero / neither debit-credit) | skip, stderr `WARNING: <file>:<line>: <reason>`, exit 0 |

## Testing
- TDD per module with small inline CSV fixtures in `tmp_path`.
- Cases: both formats incl. thousands separators and BOM; bad rows warn+skip; dedupe within-file identical rows kept, across-file max count, whitespace/case variants, balance differences, same file twice, different accounts not merged; transfer window 3 vs 4 days, nearest-date choice, tie by output order, CC payoff, unmatched stays normal; rules first-match, case-insensitive, Uncategorised; sorting; end-to-end CLI run and byte-identical re-run.
