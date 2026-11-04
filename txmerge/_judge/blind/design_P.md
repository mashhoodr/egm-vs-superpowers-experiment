# txmerge: merge overlapping bank exports into one ledger

*   **Author:** [redacted] ([redacted] arm), for Mashhood Rastgar
*   **Status:** Approved
*   **Date:** 2026-11-02

--------------------------------------------------------------------------------

## Overview

`txmerge` is a command-line tool, written in Python with only the standard library, that turns several overlapping bank CSV exports into one ledger CSV. It removes the duplicate rows that overlapping exports create, links money moved between the user's own accounts, and puts every other row into a category using a rules file. The command line, input formats, rules header and output header are a fixed contract in [BRIEF.md](../../BRIEF.md); this document keeps that contract and accepts a superset of the stated input formats (D5, D6). Answers from the stakeholder are recorded in [stakeholder_log.md](../../stakeholder_log.md), and the ideation that led here is in [concepts_brief.md](../../concepts_brief.md).

## The Problem

The user downloads exports from a current account (Format A) and a credit card (Format B) every few weeks. Three problems prevent the raw files from serving as a ledger:

1.  Export date ranges overlap, so the same transaction appears in more than one file. Dropping identical rows can lose real transactions, because two identical coffees on the same day are two real purchases.
2.  Paying the card from the current account appears as spending in one account and income in the other, which double-counts money that stayed within the user's own accounts.
3.  Rows have no categories.

The solution is a single command that reads every export, removes duplicates by max count, pairs transfers, applies rules, and writes a sorted ledger that is byte-identical every time it is run with the same arguments, the same input files and the same Python version (see G4).

## Goals

*   **G1. Duplicates from overlapping exports removed by max count.** For every account and every duplicate key (see [Definitions](#definitions)), the ledger contains exactly as many rows as the largest count of that key in any single export of that account.
*   **G2. Transfers linked.** Outflows are paired with matching inflows in other accounts (same absolute amount, at most 3 days apart) by the greedy walk in [Stage 6](#stage-6-transfers). Both rows of a pair get category `Transfer` and the same non-empty `transfer_id`.
*   **G3. Everything else categorised.** Each non-transfer record gets the category of the first rule whose pattern appears in its description (ignoring case), or `Uncategorised`.
*   **G4. Repeatable.** Two runs with the same arguments, the same input files and the same Python version produce byte-identical output files. (Case-folding and whitespace splitting follow the Unicode tables of the Python version in use.)
*   **G5. Failure behaviour.** A malformed data row ([Stage 2](#stage-2-reading-exports)) or invalid rule row ([Stage 3](#stage-3-rules-file)) is skipped with a warning naming the file and line, and the run still exits 0. Every fatal condition in [Errors, warnings and exit codes](#errors-warnings-and-exit-codes) exits 2 with a message and does not modify an existing output file.

## Non-Goals

*   Fuzzy, truncated or partial description matching for duplicates.
*   Regex or wildcard rule patterns.
*   Using the Balance column to detect missing rows.
*   Currency symbols, currency conversion, or encodings other than UTF-8.
*   Incremental updates. Every run rebuilds the whole ledger from all inputs.
*   Stable `transfer_id`s across runs with different inputs. IDs are stable only for identical inputs.
*   Durability of the new ledger across an OS crash or power loss (no `fsync`).
*   Any command-line flag beyond the brief's contract and `argparse`'s built-in `-h`/`--help` (no `--verbose`, no `--quiet`).

## Open Questions

None. Every behavioural question was answered by the stakeholder or recorded as a decision with its reason in [Decision Log](#decision-log).

## Definitions

*   **Export**: one `--account NAME=PATH` argument. The same path given twice is two exports.
*   **Account**: the NAME part of `--account`, used exactly as typed (case-sensitive, not trimmed). Two exports with the same NAME belong to one account, even if their formats differ.
*   **Input position**: the pair (export index, line). Export index is the 0-based position of the `--account` argument among all `--account` arguments. Line is the 1-based physical line in the file where the row starts; line numbers count every physical line, including blank lines and the header.
*   **Row**: one list of cells as returned by `csv.reader` from an input or rules file. A row may span more than one physical line when a quoted field contains a line break. Lines of the written ledger are also called rows.
*   **Record**: one parsed transaction held in memory, independent of format: account, date, amount, description, input position.
*   **Description**: the original description cell with leading and trailing whitespace removed. Inner whitespace and case are kept. This is what the ledger shows and what rules match against.
*   **Normalised description**: the description with every run of whitespace collapsed to one space and then case-folded: `" ".join(text.split()).casefold()`. Used only for duplicate detection.
*   **Duplicate key**: (account, date, amount, normalised description).
*   **Outflow / inflow**: a record with amount below zero / above zero. A zero amount is neither.
*   **Output order**: records sorted by (date, account, export index, line). Account names compare as plain Python strings (code-point order).

## Critical User Journeys (CUJs)

### CUJ 1: Merge overlapping exports of two accounts

*   **Given**: two current-account exports (Format A) covering 1–31 March and 15 March–15 April, one card export (Format B), and a rules file.
*   **When**: the user runs `python -m txmerge merge --account Current=mar.csv --account Current=apr.csv --account Card=card.csv --rules rules.csv --out ledger.csv`.
*   **Then**: for each account and duplicate key, `ledger.csv` holds as many rows as the largest count of that key in any single export, the card payment appears on both accounts with category `Transfer` and the same `transfer_id`, every other row has a category or `Uncategorised`, the process exits 0, and stderr shows one summary line.

### CUJ 2: Rerun gives the same file

*   **Given**: the run from CUJ 1 has produced `ledger.csv`.
*   **When**: the user runs the same command again.
*   **Then**: the new `ledger.csv` is byte-identical to the old one.

### CUJ 3: A malformed row is skipped

*   **Given**: one export contains a row with date `31/02/2026`.
*   **When**: the user runs the merge.
*   **Then**: stderr shows `txmerge: warning: PATH:LINE: invalid date '31/02/2026'`, the row is not in the ledger, all other rows are, and the exit code is 0.

### CUJ 4: An unrecognised header leaves the ledger unchanged

*   **Given**: `ledger.csv` exists from an earlier run, and the user passes a file whose header matches neither format.
*   **When**: the user runs the merge.
*   **Then**: stderr shows an error naming the file, the header found and the two accepted headers; the exit code is 2; `ledger.csv` is byte-identical to before.

## Technical Plan (Architecture)

The tool is one in-memory pipeline. Stages 2 and 3 read files, Stage 8 writes the only output file, and Stages 4 to 7 work on records in memory (Stages 6 and 7 fill in `category` and `transfer_id` on the records in place). Nothing is written to `--out` until every input and the rules file have been read and validated.

```text
 argv
  │
  ▼
[1] CLI: parse arguments; --out must not be an input ── usage error / overlap → exit 2
  │  exports: [(name, path)], rules path, out path
  ▼
[2] Read exports (in argument order) ──── missing / unreadable / bad CSV / unrecognised header → exit 2
  │  detect format from header; parse each row
  │  malformed row → warning, skip
  │  → records (format-neutral), in input-position order
  ▼
[3] Read rules file ───────────────────── missing / unreadable / wrong header → exit 2
  │  bad rule row → warning, skip
  │  → ordered list of (pattern, category)
  ▼
[4] Dedup per account (max count, first N by input position)
  ▼
[5] Sort into output order
  ▼
[6] Pair transfers (greedy walk over outflows in output order)
  ▼
[7] Categorise non-transfer records (first matching rule, else Uncategorised)
  ▼
[8] Write ledger: temp file, then rename ── OS error → exit 2
  │
  ▼
 summary line on stderr, exit 0
```

### Stage 1: command line

Arguments are parsed with `argparse` (see `txmerge/cli.py` in the [Detailed Implementation Plan](#detailed-implementation-plan)). Each `--account` value is split at the first `=`, so a PATH may itself contain `=`; a value with no `=`, an empty NAME or an empty PATH is a usage error. If `--rules` or `--out` is given more than once, the last value is used (`argparse` default). Usage errors exit 2 before any file is read. The tool then checks that `--out` is not the same file as any input export or the rules file (`os.path.samefile`, applied only to paths that exist); if it is, the run stops with exit 2 before any input is read.

### Stage 2: reading exports

A shared CSV reader opens each file with encoding `utf-8-sig` (which removes a byte-order mark if present) and `newline=""`. It reads the file with `csv.reader(f, strict=True)`. In strict mode a quote that is never closed, or a stray character after a closing quote, raises `csv.Error`, and the whole file fails with exit 2; without it, the reader would silently absorb every later row into one field. It skips, without a warning, rows whose cells are all empty after trimming. The first row that is not skipped is the header. Each header cell is trimmed, and the trimmed header must equal one format's column list exactly: same names, same case, same order, same count. A file with preamble lines (for example an account number) before the header therefore has an unrecognised header.

| Format | Header | Date column and pattern | Description column | Amount |
| --- | --- | --- | --- | --- |
| A | `Date,Description,Debit,Credit,Balance` | `Date`, `D/M/YYYY` (day first) | `Description` | exactly one of Debit / Credit filled; Debit → negative, Credit → positive. Balance ignored. |
| B | `Transaction Date,Posting Date,Details,Amount` | `Transaction Date`, `YYYY-M-D` | `Details` | `Amount` as signed. Posting Date ignored and never validated. |

Formats are held in one table of entries (header tuple, row-parsing function). Detection picks the entry whose header matches. A third format is one new entry; dedup, transfers, rules and output do not change.

The field rules below apply to each cell after trimming. "Digit" always means an ASCII digit `0`–`9`; other Unicode digits are rejected. The checks run in the order listed, and only the first failing reason is reported.

*   **Field count**: a row whose number of cells differs from the header's is malformed with reason `expected N fields, found M`. An amount with a thousands separator must be quoted in the file; an unquoted `1,250.00` adds a cell and fails this check.
*   **Date**: one or two digits for day and month, four digits for year, and it must be a real calendar date. Otherwise the row is malformed with reason `invalid date 'TEXT'`.
*   **Filled (Format A)**: a cell is filled when it is non-empty after trimming. A Format A row with both Debit and Credit filled is malformed with reason `both Debit and Credit are filled`; with neither, `neither Debit nor Credit is filled`.
*   **Unsigned amount (Format A Debit/Credit)**: digits, optionally grouped in threes with commas (`1,250.00` or `1250.00`), with an optional decimal point followed by one or two digits; at least one digit is required before the point, so `.50` and `1250.` are malformed. No sign, no currency symbol, no exponent, no underscore. Otherwise malformed with reason `invalid amount 'TEXT'`.
*   **Signed amount (Format B)**: the same grammar, with one optional leading `-` or `+`.
*   **Conversion**: amounts are converted to `Decimal` after removing commas, then quantised to two places. If the conversion fails (for example a number too long for `Decimal`'s default precision), the row is malformed with reason `invalid amount 'TEXT'`. A zero result is stored as positive zero (`0.00`), so `-0.00` never appears.
*   **Empty description**: accepted; the record has an empty description, dedups normally and matches no rule.

### Stage 3: rules file

The rules file is read with the same CSV reader as the exports (BOM removed, blank rows skipped, cells trimmed). Its header must be exactly `pattern,category`; anything else, an empty file, or a missing or unreadable file stops the run with exit 2. A header-only file is a valid empty rule set: every non-transfer record becomes `Uncategorised`. Each rule row must have two cells with a non-blank pattern and a non-blank category; otherwise it is skipped with a warning. Rules keep their file order.

### Stage 4: dedup

Dedup runs per account, over all its exports, whatever their format. For each duplicate key, N is the largest number of records with that key in any one export. The stage keeps the first N records with that key in input-position order and drops the rest. Each kept record keeps its own description and input position.

Example: export 0 has `Coffee` twice on 3 March for −3.50; export 1 (same account) has `COFFEE ` three times on the same day for the same amount. N = 3. Kept: both records from export 0 and the first matching record in export 1, which shows `COFFEE` (trimmed) in the ledger.

### Stage 5: sort

Records are sorted into output order as defined in [Definitions](#definitions). The sort key includes the input position, which is unique, so the order is total.

### Stage 6: transfers

Stage 6 walks the sorted records in output order. For each outflow not yet paired, the candidates are inflows that are not yet paired, are in a different account, have amount equal to the outflow's absolute amount, and are dated at most 3 days before or after it (inclusive). Choose the candidate with the smallest absolute day difference; on a tie, the one that comes first in output order. If there is a candidate, both records get category `Transfer` and `transfer_id` `T` followed by the pair number padded to at least four digits (`T0001`, `T0002`, …, `T10000`), counting pairs in the order they are made. The walk is greedy: an early outflow can take an inflow that a later outflow would also have matched.

Candidates are found through an index from amount to the inflows with that amount, kept in output order. This gives the same result as scanning every inflow; its cost is described under [Non-Functional Requirements](#non-functional-requirements).

### Stage 7: categorise

A pattern matches a record when `pattern.casefold()` is a substring of `description.casefold()`. The first matching rule in file order gives the category. With no match the category is `Uncategorised`. Transfer records are skipped. A rule may use the category name `Transfer` or `Uncategorised`. Neither has any special meaning: a record given `Transfer` by a rule has an empty `transfer_id`, and a record given `Uncategorised` by a rule is counted as uncategorised in the summary.

### Stage 8: output

The ledger is written with `csv.writer` using `lineterminator="\n"` and `QUOTE_MINIMAL`, encoded UTF-8 without a byte-order mark. The header row is always written, even with zero records. Fields: `date` as `YYYY-MM-DD`; `account` as typed; `description` exactly as defined (no escaping; a description containing `\n` or `\r` is written inside double quotes with those characters kept as they are); `amount` with exactly two decimals, no thousands separator, `-` only for negatives; `category`; `transfer_id` or empty.

The rows go to a temporary file next to `--out`, named `--out` plus `.<process id>.txmerge-tmp`, opened with `open(..., "x")` (so the user's umask sets its permissions and an existing file of that name is never overwritten). When the file is complete it is moved over `--out` with `os.replace`, which is atomic because both paths are in the same directory. If any step fails, the temp file is removed and `--out` keeps its previous contents. A symbolic link at `--out` is replaced by a regular file.

### Errors, warnings and exit codes

| Condition | Outcome | Exit | Message (stderr) |
| --- | --- | --- | --- |
| Bad arguments (missing option, `--account` without `=`, empty NAME or PATH, no subcommand) | stop | 2 | `usage: txmerge ...` followed by `txmerge: error: ...`; the wording is argparse's and is not fixed by this design |
| Input file missing or unreadable | stop | 2 | `txmerge: error: cannot read PATH: REASON` |
| Input file not valid UTF-8, or the CSV reader raises an error (for example an unclosed quote or a character after a closing quote) | stop | 2 | `txmerge: error: cannot read PATH: REASON` |
| Input file has a header matching neither format | stop | 2 | `txmerge: error: PATH: unrecognised header "FOUND"; expected "Date,Description,Debit,Credit,Balance" or "Transaction Date,Posting Date,Details,Amount"` (FOUND = trimmed header cells joined by commas) |
| Input file has no header (empty, or only blank rows) | stop | 2 | `txmerge: error: PATH: unrecognised header (empty file); expected "Date,Description,Debit,Credit,Balance" or "Transaction Date,Posting Date,Details,Amount"` |
| Rules file missing, unreadable, not UTF-8, or the CSV reader raises an error | stop | 2 | `txmerge: error: cannot read PATH: REASON` |
| Rules file empty, or header not `pattern,category` | stop | 2 | `txmerge: error: PATH: rules header must be "pattern,category"` |
| `--out` is the same file as an input export or the rules file | stop | 2 | `txmerge: error: --out OUT is also an input file` |
| Output cannot be written (missing directory, permission, disk full) | stop | 2 | `txmerge: error: cannot write OUT: REASON` |
| Malformed data row | skip row | — | `txmerge: warning: PATH:LINE: REASON`, with REASON as listed in Stage 2 |
| Rules row with wrong field count, blank pattern or blank category | skip rule | — | `txmerge: warning: PATH:LINE: expected 2 fields, found N`, `txmerge: warning: PATH:LINE: blank pattern`, or `txmerge: warning: PATH:LINE: blank category` (checked in that order; only the first is reported) |
| Success | write ledger | 0 | `txmerge: wrote W rows to OUT (parsed R, skipped M malformed, removed D duplicates, linked T transfer pairs, U uncategorised)`. R = rows parsed into records (malformed rows excluded); M = data rows skipped as malformed; D = R − W; T = pairs; U = records with category `Uncategorised` |

PATH in every message is the path exactly as typed on the command line (not resolved). Files are read in argument order, then the rules file; the first fatal error stops the run. Warnings appear in that same reading order. Only `-h`/`--help` writes to stdout (argparse help text, exit 0). An unexpected internal error is not caught and exits 1 with a traceback, so a defect is distinguishable from a user error.

## Alternatives Considered

Alternatives A to G are behaviours the stakeholder decided; they are listed so the reasons stay with the design. H to L are trade-offs chosen by the design author.

### Alternative A: Sum counts across exports

*   **Pros**: No per-export counting.
*   **Cons**: Doubles every row in an overlap.
*   **Reason for Rejection**: The stakeholder requires the maximum count, not the sum.

### Alternative B: Treat identical rows as one (set semantics)

*   **Pros**: No counting at all; one pass with a set.
*   **Cons**: Two identical coffees on the same day collapse into one, losing a real transaction.
*   **Reason for Rejection**: Breaks G1, and the brief's first requirement ("never lose a real transaction").

### Alternative C: Fuzzy description matching

*   **Pros**: Would catch truncated descriptions.
*   **Cons**: Needs a similarity threshold that can merge two distinct transactions; results change when the threshold changes.
*   **Reason for Rejection**: The stakeholder put fuzzy matching out of scope.

### Alternative D: Posting Date for Format B

*   **Pros**: Matches the date the card issuer settled the charge.
*   **Cons**: Differs from what the user sees as the purchase date.
*   **Reason for Rejection**: The stakeholder chose Transaction Date.

### Alternative E1: Regex rules

*   **Pros**: More expressive patterns.
*   **Cons**: Characters such as `.` and `(` in merchant names need escaping, and a missed escape changes what the pattern matches.
*   **Reason for Rejection**: The stakeholder specified a plain case-insensitive substring.

### Alternative E2: Match rules on the normalised description

*   **Pros**: `coffee shop` would match `COFFEE  SHOP`.
*   **Cons**: Rules would match text the user does not see in the ledger.
*   **Reason for Rejection**: The stakeholder specified matching against the description as written, trimmed only.

### Alternative F: Globally optimal transfer matching

*   **Pros**: Could pair more rows when amounts repeat.
*   **Cons**: Needs a matching algorithm; whether an outflow is paired would depend on all other candidates, not only on earlier outflows.
*   **Reason for Rejection**: The stakeholder specified the greedy walk with closest-date choice.

### Alternative G: Every surviving duplicate copy takes the first export's text

*   **Pros**: Uniform text for a repeated purchase.
*   **Cons**: Hides what the later export actually said, and it is unclear which input position the extra copy would then sort by (its own, or the first export's).
*   **Reason for Rejection**: The stakeholder said each copy keeps its own text.

### Alternative H: Round amounts with more than two decimals

*   **Pros**: Accepts more input.
*   **Cons**: Needs a rounding policy.
*   **Reason for Rejection**: Rounding would change amounts without the user knowing; a warning on a skipped row is visible.

### Alternative I: Fall back to another encoding (cp1252) when UTF-8 fails

*   **Pros**: Accepts more bank files.
*   **Cons**: The tool would have to guess the encoding.
*   **Reason for Rejection**: A wrong guess silently corrupts descriptions, which can break dedup (G1) and makes output depend on the guess.

### Alternative J: Format plug-in classes or registry

*   **Pros**: Formal extension point.
*   **Cons**: Extra code for two formats.
*   **Reason for Rejection**: A table of (header, parse function) entries already makes a new format one entry.

### Alternative K: Write directly to `--out`

*   **Pros**: No temp file or rename.
*   **Cons**: A failure while writing leaves a partial or emptied ledger.
*   **Reason for Rejection**: Breaks G5.

### Alternative L: Stream rows, or use SQLite as a working store

*   **Pros**: Lower memory for very large inputs; SQLite is in the standard library.
*   **Cons**: Streaming cannot dedup by max count or sort without holding all rows; SQLite adds a schema and query layer.
*   **Reason for Rejection**: Streaming cannot meet G1; at the size stated in Non-Functional Requirements, an in-memory list needs less code than SQLite.

## Non-Functional Requirements

*   **Determinism**: every ordering in the output comes from input order or an explicit sort. No unordered set iteration, timestamps, random values or locale-dependent comparison.
*   **Performance**: for each outflow, candidate lookup scans only the inflows with the same amount (Stage 6), not all inflows. When many records share one amount (a monthly subscription, repeated coffees), the work for that amount grows with the square of how many records share it. No target run time is set.
*   **Size**: designed for up to about 100,000 records per run (estimate: about 1 KB per record including Python object overhead, so about 100 MB; not measured). All records are held in memory and no size limit is enforced.
*   **Rollback**: the tool keeps no state; an older version can be run on the same inputs.

## Risks and Mitigations

| Risk | Type | Mitigation or acceptance |
| --- | --- | --- |
| Greedy pairing links two unrelated equal amounts in different accounts within 3 days (for example a £50 card purchase and an unrelated £50 credit) | Correctness | Accepted: this is the stakeholder's rule. Both records appear in the ledger with the same `transfer_id`. |
| A duplicate survives when a later export truncates the description or changes the date or amount (for example a pending card charge that posts with a tip), so the ledger double-counts it | Correctness | Accepted: the stakeholder put fuzzy matching out of scope. Exact matching does not merge records whose date, amount or normalised description differ. |
| Two exports of one account split a day between them, and each holds a different purchase with the same key (for example one coffee before and one after the export cut-off); max-count keeps only one | Correctness | Accepted: this is the stakeholder's max-count rule; the exports carry no information that tells the two cases apart. |
| Rules match inner whitespace exactly: `coffee shop` does not match `COFFEE  SHOP` | Correctness | Accepted: stakeholder rule; the user can add a second rule. |
| A description starting with `=`, `+`, `-` or `@` may be run as a formula when the ledger is opened in a spreadsheet | Security | Accepted: the stakeholder requires descriptions exactly as the bank gave them. Description text is merchant-controlled. |
| The same file is passed under two account names, so an outflow in one copy can pair with an equal inflow in the other and form a false transfer | Correctness | Accepted (D3): the stakeholder said different accounts never dedup; both records of each pair appear in the ledger with their `transfer_id`. |
| `--out` points at an input export or the rules file and would destroy it | Failure | Refused with exit 2 before any input is read (Stage 1). |
| The process is killed between creating and renaming the temp file, leaving a `*.txmerge-tmp` file | Failure | Accepted: the existing ledger is unchanged; the stray file can be deleted. |
| An amount with a thousands separator is not quoted, so the row has an extra cell | Failure | Accepted: which cell the extra comma belongs to cannot be known; the row is warned (`expected N fields, found M`) and counted in M. |
| Two `--account` NAMEs that differ only by case or outer spaces (`current`, `Current`) split one real account, so overlapping rows are not deduplicated | Correctness | Accepted: NAMEs are used as typed (stakeholder: dedup is per account name); both NAMEs appear in the ledger's `account` column. |
| A bank export with a trailing comma on every line (an extra empty header cell) | Failure | Accepted: the header no longer matches exactly, so the run exits 2 showing the found header; the user removes the trailing commas. |
| A bank export with preamble lines before the header | Failure | Accepted: exit 2 with the found and expected headers, so the user can remove the preamble. |
| Many records share one amount (for example years of the same subscription), so transfer lookup for that amount grows with the square of their number | Scalability | Accepted: the cost is stated in Non-Functional Requirements; no time target is set. |
| A current-account export writes `0.00` in the unused Debit or Credit cell, so every row has both filled and is skipped | Failure | Accepted: follows the brief ("positive numbers or blank") and the stakeholder's malformed-row rule; each row is warned and the summary's M count shows the loss. |
| One non-UTF-8 byte (for example a cp1252 `£`) makes the whole run exit 2 | Failure | Accepted (D24): the error REASON from `UnicodeDecodeError` names the byte and its position within the chunk being decoded, which locates it in small files. |
| Inputs beyond the size in [Non-Functional Requirements](#non-functional-requirements) | Scalability | Accepted: the tool may run slowly or run out of memory; no limit is enforced. |

## Decision Log

Source tags:

*   **S**: stakeholder answer.
*   **E**: decision by the design author where the stakeholder said "your call".
*   **S/E**: the stakeholder set the rule and the author filled in a detail it left open.

| # | Decision | Source | Reason |
| --- | --- | --- | --- |
| D1 | Pipeline order as in the Technical Plan | S/E | The stakeholder fixed dedup, output order and the outflow walk; transfer pairing needs dedup and sort first |
| D2 | Same path given twice = two exports, no warning | E | Max-count dedup absorbs it |
| D3 | Same file under two account names: allowed, no warning | S/E | The stakeholder said different accounts never dedup; the result is well defined. Its false-transfer risk is listed in Risks |
| D4 | Balance column ignored | E | Not needed for any goal |
| D5 | Amount grammar strict: ASCII digits, comma thousands separators accepted in both formats, `+` or `-` allowed only in Format B; more than 2 decimals, signs in Format A, currency symbols are malformed | E | Never change money silently; `+` is accepted because a signed column may mark refunds with it; the brief documents separators in Format A, and Format B uses the same grammar for consistency |
| D6 | Dates accept one- or two-digit day and month | E | Avoid losing real transactions over formatting that does not change the date's value |
| D7 | Zero-amount rows kept; never part of a transfer | E | They are real rows; a zero has no direction |
| D8 | Rules: blank pattern, blank category or wrong field count → warn and skip | E | A blank pattern would match everything |
| D9 | Rules file missing, unreadable or wrong header → exit 2; header-only file is valid | S/E | A missing file or wrong header means the wrong path was passed; the stakeholder said a header-only file leaves every record `Uncategorised` |
| D10 | Missing or unreadable input → exit 2 | E | Same class as an unrecognised header |
| D11 | BOM removed, blank rows skipped without warning, header cells trimmed, quoted fields read by `csv` | E | Each quirk would otherwise turn a valid export into an unrecognised header or malformed rows |
| D12 | `transfer_id` = `T` + pair number, at least 4 digits | E | Derived only from pair order, so identical inputs give identical IDs (G4); zero-padded IDs sort as text in pair order up to `T9999` |
| D13 | One summary line on stderr; nothing on stdout except `--help` | E | Reports counts of skipped, removed and uncategorised rows so loss is visible; stdout stays empty for scripted use, and stderr carries diagnostics |
| D14 | Output bytes: UTF-8 no BOM, `\n`, `QUOTE_MINIMAL` | E | Fixing encoding, line ending and quoting makes the output identical across platforms (G4) |
| D15 | Temp file per process next to `--out`, then rename; temp removed on failure | E | An existing ledger is not modified unless the new one is fully written; plain `open` keeps the user's umask |
| D16 | Unexpected errors exit 1 with traceback | E | Separates defects from user errors |
| D17 | Descriptions written as given, no formula escaping | S | The stakeholder requires descriptions exactly as the bank gave them, trimmed only |
| D18 | `--out` equal to an input or the rules file → exit 2 | E | Prevents destroying a source file |
| D19 | Rule categories `Transfer` / `Uncategorised` allowed, no warning | E | The result is well defined and a warning would fire on intended use |
| D20 | Rule pattern and category cells are trimmed | E | Spreadsheet editors can pad cells; a pattern that depends on outer spaces as a word boundary is not supported |
| D21 | A symbolic link at `--out` is replaced by a regular file (links are not followed) | E | `os.replace` does this with no extra code; following links was removed at Stage 8 review as unneeded |
| D22 | An empty description is accepted | E | An empty description is still a real transaction |
| D23 | `.50` and `1250.` are malformed | E | These are not the documented export format; accepting them widens the grammar without need |
| D24 | CSV read in strict mode; an encoding error or any `csv.Error` fails the whole file with exit 2 | E | The bad bytes cannot be tied reliably to one row; non-strict reading can silently absorb every later row into one field |
| D25 | `--account` split at the first `=`; repeated `--rules` / `--out` keep the last value; PATH printed as typed | E | A path may contain `=`; last-value is the `argparse` default; the typed path is what the user recognises |
| D26 | `casefold()` (not `lower()`) for rule matching and normalised descriptions | E | It is Python's documented caseless-matching method; it also folds characters such as `ß` to `ss`, which is accepted |
| D27 | Transfer candidates found through an amount index | E | Same result as a full scan; avoids comparing every outflow with every inflow. It does not remove the quadratic case of many records sharing one amount (see Non-Functional Requirements) |

## Future Improvements

*   **Third bank format**: add one entry to the format table with its tests.

--------------------------------------------------------------------------------

## Detailed Implementation Plan

### Target Files to Create

All paths are relative to the repository root, which is the directory that contains `BRIEF.md` (this design lives at `docs/designs/` under it). Every file below is new; no existing file is modified. No conflicts with the [Technical Plan](#technical-plan-architecture) are intended; if one is found, the Technical Plan governs.

Terms used below, as defined in [Definitions](#definitions): *input-position order* is ascending `(export_index, line)`, which is the order produced by concatenating `read_export` results in `--account` argument order; *output order* is ascending `Record.sort_key()`; an *outflow* is a record with `amount < 0` and an *inflow* one with `amount > 0`.

#### 1. `txmerge/__init__.py` (Create)

*   **Type / Scope**: Python package marker.
*   **Proposed Changes**: A one-line module docstring and nothing else.

#### 2. `txmerge/__main__.py` (Create)

*   **Type / Scope**: Module entry point.
*   **Proposed Changes**: `import sys`, `from txmerge.cli import main`, then `sys.exit(main())`. Nothing else.

#### 3. `txmerge/model.py` (Create)

*   **Type / Scope**: Shared types and constants.
*   **Proposed Changes**:
    *   Constants: `TRANSFER_CATEGORY = "Transfer"`, `UNCATEGORISED = "Uncategorised"`, `TRANSFER_WINDOW_DAYS = 3`, `OUTPUT_HEADER = ("date", "account", "description", "amount", "category", "transfer_id")`, `EXIT_OK = 0`, `EXIT_ERROR = 2`.
    *   `class TxmergeError(Exception)`: a fatal user-facing error. Its message is the text that follows `txmerge: error: `; the prefix is added only by `cli.main`.
    *   `class MalformedRow(Exception)`: raised by row parsers; its message is the warning reason.
    *   `@dataclass class Record`: fields `account: str`, `date: datetime.date`, `amount: decimal.Decimal`, `description: str`, `export_index: int`, `line: int`, `category: str = ""`, `transfer_id: str = ""`. Method `dedup_key() -> tuple` returns `(account, date, amount, normalise(description))`. Method `sort_key() -> tuple` returns `(date, account, export_index, line)`.
    *   `def normalise(text: str) -> str`: returns `" ".join(text.split()).casefold()`.
    *   `def os_reason(e: OSError) -> str`: returns `e.strerror` if it is set, else `str(e)`. Used for every `OSError`; when `strerror` is set, the message omits the file path and errno prefix.

#### 4. `txmerge/csvio.py` (Create)

*   **Type / Scope**: Shared CSV reading for exports and the rules file.
*   **Proposed Changes**: `def read_rows(path: str) -> tuple[list[str] | None, list[tuple[int, list[str]]]]`.
    *   Opens `path` with `open(path, encoding="utf-8-sig", newline="")` and reads it with `csv.reader(f, strict=True)`.
    *   Reads with an explicit loop: `start = reader.line_num + 1; row = next(reader)`, stopping on `StopIteration`. `start` is the row's start line (1-based, physical, counting blank lines); a `for row in reader` loop would give the end line of multi-line rows instead.
    *   Skips rows that are `[]` or whose cells are all empty after `strip()`.
    *   The first remaining row is the header: returned with each cell stripped, or `None` if there is no remaining row. The other rows are returned as `(start, cells)` with cells unchanged.
    *   The `csv` module's default field size limit (131072 characters) is kept; a longer field raises `csv.Error`.
    *   Error mapping, each raised as `TxmergeError(f"cannot read {path}: {reason}")` with `path` as typed: `OSError` → `reason = os_reason(e)`; `UnicodeDecodeError` → `reason = str(e)`; `csv.Error` → `reason = f"line {reader.line_num}: {e}"`. One `try` encloses the `with open(...)` block; `reader` is created immediately after `open`, so it is bound whenever `csv.Error` is caught.

#### 5. `txmerge/formats.py` (Create)

*   **Type / Scope**: Header detection and row parsing per format.
*   **Proposed Changes**:
    *   `@dataclass(frozen=True) class Format`: `name: str`, `header: tuple[str, ...]`, `parse: Callable[[list[str]], tuple[date, str, Decimal]]`.
    *   `FORMATS: tuple[Format, ...]`: entry A with header `("Date", "Description", "Debit", "Credit", "Balance")` and `parse_a`; entry B with header `("Transaction Date", "Posting Date", "Details", "Amount")` and `parse_b`.
    *   `EXPECTED = 'expected "Date,Description,Debit,Credit,Balance" or "Transaction Date,Posting Date,Details,Amount"'`.
    *   `def detect(header: list[str] | None, path: str) -> Format`: first, if `header is None`, raises `TxmergeError(f"{path}: unrecognised header (empty file); {EXPECTED}")`. Otherwise returns the `fmt` in `FORMATS` with `fmt.header == tuple(header)`, or raises `TxmergeError(f'{path}: unrecognised header "{",".join(header)}"; {EXPECTED}')`.
    *   `def parse_date_dmy(text: str) -> date`: `re.fullmatch(r"([0-9]{1,2})/([0-9]{1,2})/([0-9]{4})", t)` on the trimmed text `t`; builds `date(year, month, day)`. A mismatch or `ValueError` raises `MalformedRow(f"invalid date '{t}'")`.
    *   `def parse_date_ymd(text: str) -> date`: the same with `re.fullmatch(r"([0-9]{4})-([0-9]{1,2})-([0-9]{1,2})", t)`.
    *   `def parse_amount(text: str, signed: bool) -> Decimal`: on the trimmed text `t`, `re.fullmatch` with `([0-9]{1,3}(,[0-9]{3})+|[0-9]+)(\.[0-9]{1,2})?`, prefixed by `[+-]?` when `signed`. Removes commas, converts with `Decimal`, then `quantize(Decimal("0.01"))`. If the result equals zero, returns `Decimal("0.00")` (this turns `Decimal("-0.00")` from a Format B `-0.00` into positive zero). A mismatch, or `decimal.InvalidOperation` from the conversion or `quantize`, raises `MalformedRow(f"invalid amount '{t}'")`.
    *   `parse_a(cells)`: checks in the Technical Plan's order. Date: `parse_date_dmy(cells[0])`. Filled: `debit, credit = cells[2].strip(), cells[3].strip()`; both non-empty → `MalformedRow("both Debit and Credit are filled")`; both empty → `MalformedRow("neither Debit nor Credit is filled")`. Amount: Debit → `-parse_amount(debit, signed=False)` (negating positive zero gives positive zero under the default `decimal` context); Credit → `parse_amount(credit, signed=False)`. Description: `cells[1].strip()`. Cell 4 (Balance) is never read. Returns `(date, description, amount)`.
    *   `parse_b(cells)`: date `parse_date_ymd(cells[0])`; cell 1 (Posting Date) never read; amount `parse_amount(cells[3], signed=True)`; description `cells[2].strip()`. Returns `(date, description, amount)`.
    *   `def read_export(export_index: int, name: str, path: str, warn: Callable[[str], None]) -> tuple[list[Record], int]`: calls `read_rows` and `detect`. For each `(line, cells)`: if `len(cells) != len(fmt.header)`, warns `f"{path}:{line}: expected {len(fmt.header)} fields, found {len(cells)}"`; otherwise calls `d, desc, a = fmt.parse(cells)` and builds `Record(account=name, date=d, amount=a, description=desc, export_index=export_index, line=line)`; on `MalformedRow` warns `f"{path}:{line}: {e}"`. Each malformed row is skipped and counted. Returns (records in input-position order, number of malformed rows).

#### 6. `txmerge/rules.py` (Create)

*   **Type / Scope**: Rules loading and categorisation.
*   **Proposed Changes**:
    *   `def load_rules(path: str, warn: Callable[[str], None]) -> list[tuple[str, str]]`: calls `read_rows`. If the header is `None` or not `["pattern", "category"]`, raises `TxmergeError(f'{path}: rules header must be "pattern,category"')`. For each `(line, cells)`, in this order, only the first applying: `len(cells) != 2` → warn `f"{path}:{line}: expected 2 fields, found {len(cells)}"`; pattern blank after `strip()` → warn `f"{path}:{line}: blank pattern"`; category blank after `strip()` → warn `f"{path}:{line}: blank category"`. A warned row is skipped. Returns `(pattern.strip().casefold(), category.strip())` pairs in file order.
    *   `def categorise(records: list[Record], rules: list[tuple[str, str]]) -> None`: for each record with empty `transfer_id`, sets `category` to the category of the first rule whose pattern is a substring of `record.description.casefold()`, else `UNCATEGORISED`.

#### 7. `txmerge/dedup.py` (Create)

*   **Type / Scope**: Duplicate removal.
*   **Proposed Changes**: `def dedup(records: list[Record]) -> list[Record]`, with `records` in input-position order. Let `k = record.dedup_key()`.
    *   Pass 1: `count[(record.export_index, k)] += 1` for every record; then `limit[k] = max(count[(e, k)] over all export indexes e)`.
    *   Pass 2: walk records in input-position order; keep a record while `kept[k] < limit[k]`, incrementing `kept[k]`; drop the rest.
    *   Returns the kept records in input-position order. `k` contains the account, so accounts never dedup against each other.

#### 8. `txmerge/transfers.py` (Create)

*   **Type / Scope**: Transfer pairing.
*   **Proposed Changes**: `def pair_transfers(records: list[Record]) -> int`, with `records` in output order.
    *   Builds `index`: a dict from amount to the list of positions of inflows with that amount, in output order.
    *   Walks positions in output order. For each outflow with empty `transfer_id`, considers the candidates in `index.get(-outflow.amount, [])` that have empty `transfer_id`, `account != outflow.account`, and `abs((inflow.date - outflow.date).days) <= TRANSFER_WINDOW_DAYS`. Chooses the candidate with the smallest `(abs((inflow.date - outflow.date).days), position)`.
    *   On a match increments the pair counter and sets, on both records, `transfer_id = f"T{counter:04d}"` and `category = TRANSFER_CATEGORY`.
    *   Returns the number of pairs.

#### 9. `txmerge/ledger.py` (Create)

*   **Type / Scope**: Output writing and the `--out` overlap check.
*   **Proposed Changes**:
    *   `def format_amount(amount: Decimal) -> str`: `f"{amount:.2f}"`. Relies on `parse_amount` having quantised amounts to 0.01 and normalised zero to `0.00`.
    *   `def write_ledger(path: str, records) -> None`, in steps:
        1.  `temp = f"{path}.{os.getpid()}.txmerge-tmp"`.
        2.  `open(temp, "x", encoding="utf-8", newline="")`. If this raises `OSError` (for example `FileExistsError`, or `FileNotFoundError` for a missing directory), raise `TxmergeError(f"cannot write {path}: {os_reason(e)}")` without removing anything: this process did not create `temp`.
        3.  Only after step 2 succeeds, inside `try`: `with f:` on the file object opened in step 2 (never reopened), write `OUTPUT_HEADER` and then one row per record (`date.isoformat()`, account, description, `format_amount(amount)`, category, transfer_id) using `csv.writer(f, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)`; after the `with` block closes the file, call `os.replace(temp, path)`.
        4.  `except BaseException`: remove `temp` if it still exists, ignoring an `OSError` from the removal itself; then, if the exception is an `OSError`, raise `TxmergeError(f"cannot write {path}: {os_reason(e)}")` from it, otherwise re-raise it unchanged.
    *   `def check_not_input(out: str, inputs: list[str]) -> None`: if `os.path.exists(out)`, then for each `p` in `inputs` with `os.path.exists(p)`: if `os.path.samefile(out, p)`, raise `TxmergeError(f"--out {out} is also an input file")`. An `OSError` from `samefile` is raised as `TxmergeError(f"cannot read {p}: {os_reason(e)}")`; the message names the input path even if the failing stat was on `out` (known limitation: this occurs only if a file is removed or loses permissions between the `exists` check and `samefile`).

#### 10. `txmerge/cli.py` (Create)

*   **Type / Scope**: Argument parsing and pipeline orchestration.
*   **Proposed Changes**:
    *   `def account_arg(value: str) -> tuple[str, str]`: `name, sep, path = value.partition("=")`; if `sep` is empty, or `name` or `path` is empty, raises `argparse.ArgumentTypeError(f"expected NAME=PATH, got '{value}'")`.
    *   `def build_parser() -> argparse.ArgumentParser`: `ArgumentParser(prog="txmerge", allow_abbrev=False)`; `add_subparsers(dest="command", required=True)`; `add_parser("merge", allow_abbrev=False, description=...)` with `--account` (`type=account_arg`, `action="append"`, `required=True`, `metavar="NAME=PATH"`), `--rules` (`required=True`, `metavar="RULES.csv"`), `--out` (`required=True`, `metavar="LEDGER.csv"`). The `merge` description is `"Merge bank exports. Accepted headers: Date,Description,Debit,Credit,Balance | Transaction Date,Posting Date,Details,Amount. Rules header: pattern,category."`. Help wording is not part of the contract.
    *   `def main(argv: list[str] | None = None) -> int`, in steps:
        1.  `args = build_parser().parse_args(argv)` (argparse exits 2 on usage errors).
        2.  `warn(msg)` is defined inside `main` and calls `print(f"txmerge: warning: {msg}", file=sys.stderr)`, so `sys.stderr` is looked up at call time (so pytest's `capsys`, which replaces `sys.stderr`, captures the output). The summary and error lines are printed the same way.
        3.  Before the `try`: `M = 0`, `records = []`. Inside `try`:
            1.  `check_not_input(args.out, [path for _, path in args.account] + [args.rules])`.
            2.  For each `(index, (name, path))` in `enumerate(args.account)`: `batch, skipped = read_export(index, name, path, warn)`; `records.extend(batch)`; `M += skipped`.
            3.  `rules = load_rules(args.rules, warn)`.
            4.  `R = len(records)`; `kept = dedup(records)`; `kept.sort(key=Record.sort_key)`.
            5.  `T = pair_transfers(kept)`; `categorise(kept, rules)`.
            6.  `write_ledger(args.out, kept)`.
            7.  `W = len(kept)`, `D = R - W`, `U` = the number of kept records whose category is `UNCATEGORISED`; print `txmerge: wrote {W} rows to {args.out} (parsed {R}, skipped {M} malformed, removed {D} duplicates, linked {T} transfer pairs, {U} uncategorised)` to stderr; return `EXIT_OK`.
        4.  `except TxmergeError as e`: print `txmerge: error: {e}` to stderr; return `EXIT_ERROR`.

#### 11. `pyproject.toml` (Create)

*   **Type / Scope**: Project metadata and pytest configuration.
*   **Proposed Changes**: `[project]` with `name = "txmerge"`, `version = "0.1.0"`, `requires-python = ">=3.11"`, `dependencies = []`, and `[project.optional-dependencies] test = ["pytest>=7.0"]` (`pythonpath` needs pytest 7.0 or later). `[tool.pytest.ini_options]` with `testpaths = ["tests"]` and `pythonpath = ["."]`, so both `pytest` and `python -m pytest` import the package from the repository root. No build backend.

#### 12. `tests/conftest.py` (Create)

*   **Type / Scope**: Test helpers.
*   **Proposed Changes**:
    *   The module imports nothing from `txmerge` at top level, so it loads in Phase 1, before `txmerge.cli` exists.
    *   Fixture `write(tmp_path)`: returns `write(name, content)`. Parent directories under `tmp_path` are created first (`mkdir(parents=True, exist_ok=True)`). A `str` is written encoded as UTF-8 with no newline translation (`open(..., "w", encoding="utf-8", newline="")`); `bytes` are written as-is. Returns the path as a string.
    *   Fixture `run(capsys)`: returns a function `run(argv) -> (exit_code, stdout, stderr)`. Inside that function it imports `txmerge.cli` and calls `txmerge.cli.main(argv)`; `exit_code` is the value `main(argv)` returns, or `e.code` if argparse raises `SystemExit`; stdout and stderr come from `capsys.readouterr()`.
    *   Fixture `read_ledger()`: returns a function `read(path)` that returns the output rows as lists, read with `csv.reader` from a file opened with `encoding="utf-8", newline=""`.

#### 13. `tests/test_parsing.py` (Create)

*   **Type / Scope**: Unit tests for `formats.py`, `csvio.py` and `model.normalise`.
*   **Proposed Changes**: one test function per bullet, parametrised over the listed values (decision IDs in brackets):
    *   Format A: Debit `12.50` → `-12.50`; Credit `12.50` → `12.50`; Debit `1,250.00` (quoted cell) → `-1250.00`.
    *   Format A both filled / neither filled → the two exact reasons.
    *   Format A Balance cell `abc` or empty is ignored and the row parses [D4].
    *   Format B: `-1,250.00` → `-1250.00`; `+5.00` → `5.00`; `-0.00` → `0.00` [D5].
    *   Format A cells `+5.00` and `-5.00` rejected [D5].
    *   Dates accepted: `01/02/2026`, `1/2/2026` (Format A), `2026-01-02`, `2026-1-2` (Format B) [D6].
    *   Dates rejected in Format A: `31/02/2026`, `2026/02/01`, `02/01/26`, and `٠١/٠٢/٢٠٢٦` (Arabic-Indic digits). Rejected in Format B: `2026-02-30`, `01/02/2026`.
    *   Amounts rejected with `invalid amount 'TEXT'` (TEXT is the trimmed cell), tested by calling `parse_amount` directly: `NaN`, `1e3`, `1,2,3`, `12.345`, `£5.00`, `.50`, `1250.`, `١٢`, and a 40-digit number [D23].
    *   Zero Debit `0.00` → `0.00`, never `-0.00` [D7].
    *   Empty description accepted [D22].
    *   BOM before the header and padded header cells: format detected [D11].
    *   A file whose only rows are blank → `TxmergeError` with "unrecognised header (empty file)".
    *   Blank line before a bad row: the warning's line number counts the blank line [D11].
    *   A Format A row with date `31/02/2026` whose quoted description spans physical lines 3–4 warns exactly `PATH:3: invalid date '31/02/2026'` (its start line, not its end line); a later bad row on line 6 warns `PATH:6: ...`.
    *   Quoted field with an embedded comma parses as one cell [D11].
    *   Header-only file → zero records.
    *   Format A row with an unquoted `1,250.00` in Debit (six cells) → `expected 5 fields, found 6`.
    *   Malformed-row reason precedence: a row with a bad date and both Debit and Credit filled reports the date.
    *   `normalise`: tabs and repeated spaces collapse, case folds, and `STRASSE` and `straße` normalise equal [D26].

#### 14. `tests/test_dedup.py` (Create)

*   **Type / Scope**: Unit tests for `dedup.py`.
*   **Proposed Changes**:
    *   Two identical rows in one export are both kept.
    *   Counts 2 and 3 across two exports give 3; the third kept record is the first matching row of the second export, with its own text and input position.
    *   Descriptions differing only in case or inner whitespace have the same duplicate key; the first occurrence's text is kept.
    *   Different date, amount or truncated text stay separate.
    *   The same path given twice under one NAME adds no rows [D2].
    *   The same rows under two different NAMEs are both kept [D3].
    *   Format A and Format B exports under one NAME dedup against each other.

#### 15. `tests/test_transfers.py` (Create)

*   **Type / Scope**: Unit tests for `transfers.py`.
*   **Proposed Changes**:
    *   3 days apart links; 4 days does not.
    *   An inflow dated before its outflow links.
    *   The closest date wins; a tie on distance goes to the inflow first in output order.
    *   Two equal outflows and one inflow: only the first outflow links.
    *   The same account never links; zero amounts never link [D7].
    *   IDs are `T0001`, `T0002` in the order pairs are made [D12].
    *   Amount index matches a full scan [D27]: inflow `i` (0–49) of `10.00` on 2026-01-01 plus `i % 7` days in account `["A", "B", "C"][i % 3]`; outflow `j` (0–29) of `-10.00` on 2026-01-01 plus `j % 5` days in account `["A", "B", "C"][(j + 1) % 3]`. A reference function in the test applies the Stage 6 rule by scanning every inflow position; every record's `transfer_id` must equal the reference.

#### 16. `tests/test_rules.py` (Create)

*   **Type / Scope**: Unit tests for `rules.py`.
*   **Proposed Changes**:
    *   Case-insensitive substring match; first matching rule wins; no match gives `Uncategorised`.
    *   Header-only rules file → every record `Uncategorised` [D9].
    *   Rules rows `coffee` (one field), `,Food` and `coffee,` warn `expected 2 fields, found 1`, `blank pattern` and `blank category`, and are skipped [D8].
    *   Padded cells ` Coffee , Food ` match `COFFEE` and give category `Food` [D20].
    *   Wrong header and empty file raise `TxmergeError` [D9].
    *   Pattern `coffee shop` does not match `COFFEE  SHOP`.
    *   Pattern `straße` matches `STRASSE` [D26].
    *   A rule with category `Transfer` leaves `transfer_id` empty [D19].

#### 17. `tests/test_cli.py` (Create)

*   **Type / Scope**: End-to-end tests through `cli.main` (and one subprocess).
*   **Proposed Changes**:
    *   CUJ 1 (see [Critical User Journeys](#critical-user-journeys-cujs)); the expected ledger string is worked out by hand from the Technical Plan, never pasted from a run: two overlapping Format A exports, one Format B export, one malformed export row, one invalid rules row and a rule with category `Uncategorised`. Assert the ledger bytes equal an expected string written in the test (header, `\n` endings, sorted order, one transfer pair, categories), and assert the exact summary line, including M = 1 (the invalid rules row is not counted) and U counting the rule-assigned `Uncategorised` record [D1, D13, D19].
    *   CUJ 3: a row with date `31/02/2026` gives exactly `txmerge: warning: PATH:LINE: invalid date '31/02/2026'` (PATH as typed), the row is absent, exit 0.
    *   Descriptions containing a quoted inner LF (U+000A) and a quoted inner lone CR (U+000D) are written inside double quotes with the character kept. Verified by the design author on CPython 3.11.14 and 3.13.7: `csv.writer` with `lineterminator="\n"` and `QUOTE_MINIMAL` quotes both, so no extra code is needed.
    *   Determinism: two runs into two files give identical bytes [D14].
    *   Subprocess: one valid Format A export with two rows (`Coffee` and `Rent`) and a rules file with the single rule `coffee,Food`; `subprocess.run([sys.executable, "-m", "txmerge", "merge", ...], cwd=Path(__file__).resolve().parent.parent)` exits 0, stdout is empty, and stderr equals the following summary line plus one trailing `\n`: `txmerge: wrote 2 rows to OUT (parsed 2, skipped 0 malformed, removed 0 duplicates, linked 0 transfer pairs, 1 uncategorised)` with OUT as typed [D13].
    *   Exit 2 cases:
        *   All cases assert exit code 2. Each case that can start with a pre-existing `--out` (every case except "missing output directory" and the argument errors that pass no `--out`) is run with one and asserts it is byte-identical afterwards; each case that can start without one (every case except "`--out` equal to an input export / the rules file") is run without one and asserts no `--out` is created.
        *   Application errors: stderr starts with `txmerge: error:`; for the unrecognised-header and empty-file cases, stderr equals the exact errors-table message with PATH as typed.
        *   Argument errors: stderr starts with `usage: txmerge` and contains `error:`.
        *   The cases:
            *   unrecognised header; empty input file; missing input file [D10];
            *   missing rules file; wrong rules header [D9];
            *   non-UTF-8 input: bytes `b"Date,Description,Debit,Credit,Balance\n01/02/2026,Caf\xa3,1.00,,\n"`;
            *   unclosed quote: `Date,Description,Debit,Credit,Balance\n01/02/2026,"Open,1.00,,\n02/02/2026,Later,2.00,,\n` (no later `"` in the file) [D24];
            *   missing output directory;
            *   `--out` equal to an input export, and `--out` equal to the rules file [D18];
            *   `--account` without `=` [D25]; empty NAME; missing subcommand; abbreviated `--acc`.
    *   Write failure after the temp file exists: monkeypatch `os.replace` to raise `OSError`; assert exit 2, `cannot write OUT`, and no `*.txmerge-tmp` file left [D15].
    *   With `monkeypatch.chdir(tmp_path)` and a file written to `dir/a=b.csv`, `--account Name=dir/a=b.csv` reads it; repeating `--out` writes to the last value [D25].
    *   A symbolic link at `--out` pointing to a separate existing non-input file is replaced by a regular file holding the ledger, and the file it pointed to is unchanged [D21].
    *   Format B Posting Date `xyz` is ignored and the row parses.
    *   `merge --help` exits 0 and writes non-empty help text to stdout.
    *   All rows malformed: exit 0, ledger with header only.

### Phases

From Phase 2 on, each phase ends with `python -m pytest` passing on all tests written so far. Phase 1 has no tests and is checked by its import command only (pytest would exit 5, "no tests collected").

1.  **Skeleton**: files 1, 3, 4, 11, 12. Check: `python -c "import txmerge.model, txmerge.csvio"` succeeds.
2.  **Parsing**: file 5 and file 13.
3.  **Rules**: file 6 and file 16.
4.  **Dedup**: file 7 and file 14.
5.  **Transfers**: file 8 and file 15.
6.  **Output and CLI**: files 9, 10, 2 and 17, including the subprocess test.

### Verification Plan

*   **Build**: no build step. Import check: `python -c "import txmerge.cli"` succeeds on Python 3.11+.
*   **Unit Tests**: in each interpreter under test, install pytest with `python -m pip install "pytest>=7.0"` (the package itself is not installed; `pythonpath` and the subprocess `cwd` make it importable), then run `python -m pytest` from the repository root. It passes on Python 3.11 and on Python 3.13.
*   **Static Analysis & Linting**: none required.
*   **Test Coverage Requirement**: every row of the errors table has at least one test, and every Decision Log entry tagged E or S/E (see [Decision Log](#decision-log)) has at least one test, shown by the decision IDs in brackets above, except D16 (exit 1 on an internal error, Python's default behaviour).
*   **E2E/Integration**: the subprocess test in `tests/test_cli.py`.

--------------------------------------------------------------------------------

*Drafted with [redacted]*
