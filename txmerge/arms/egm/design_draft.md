# txmerge: merge overlapping bank exports into one ledger

*   **Author:** Elephant (EGM arm), for Mashhood Rastgar
*   **Status:** Draft
*   **Date:** 2026-11-02

--------------------------------------------------------------------------------

## Overview

`txmerge` is a command-line tool, written in Python with only the standard library, that turns a pile of overlapping bank CSV exports into one ledger CSV. It removes the duplicate rows that overlapping exports create, links money moved between the user's own accounts, and puts every other row into a category using a rules file. The command line, input formats, rules header and output header are a fixed contract in [BRIEF.md](./BRIEF.md); this document does not change any of it. Answers from the stakeholder are recorded in [stakeholder_log.md](./stakeholder_log.md), and the ideation that led here is in [concepts_brief.md](./concepts_brief.md).

## The Problem

The user downloads exports from a current account (Format A) and a credit card (Format B) every few weeks. Three things make the raw files unusable as a ledger:

1.  Export date ranges overlap, so the same transaction appears in more than one file. Simply dropping identical rows is wrong, because two identical coffees on the same day are two real purchases.
2.  Paying the card from the current account appears as spending in one account and income in the other, which double-counts money that never left the user's hands.
3.  Rows have no categories.

The solution is a single command that reads every export, removes duplicates by count, pairs transfers, applies rules, and writes a sorted ledger that is identical every time it is run on the same inputs.

## Goals

*   **G1. No duplicate rows from overlapping exports, and no lost rows.** For every account and every duplicate key (defined below), the ledger contains exactly as many rows as the largest count of that key in any single export of that account.
*   **G2. Transfers linked.** Every outflow that has a matching inflow in a different account (same absolute amount, at most 3 days apart) is paired with it; both rows get category `Transfer` and the same non-empty `transfer_id`.
*   **G3. Everything else categorised.** Each non-transfer row gets the category of the first rule whose pattern appears in its description (ignoring case), or `Uncategorised`.
*   **G4. Repeatable.** Two runs with the same arguments and the same input files produce byte-identical output files.
*   **G5. Clear failure.** A bad row is skipped with a warning naming the file and line, and the run still exits 0. A bad file, bad rules file or bad argument exits 2 with a message, and leaves any existing output file unchanged.

## Non-Goals

*   Fuzzy, truncated or partial description matching for duplicates.
*   Regex or wildcard rule patterns.
*   Using the Balance column to detect missing rows.
*   Currency symbols, currency conversion, or encodings other than UTF-8.
*   Incremental updates. Every run rebuilds the whole ledger from all inputs.
*   Stable `transfer_id`s across runs with different inputs. IDs are stable only for identical inputs.
*   Any command-line flag beyond the brief's contract (no `--verbose`, no `--quiet`).

## Open Questions

None. Every behavioural question was answered by the stakeholder or recorded as a decision with its reason in [Decision Log](#decision-log).

## Definitions

These terms are used with exactly these meanings throughout the document.

*   **Export**: one `--account NAME=PATH` argument. The same path given twice is two exports.
*   **Account**: the NAME part of `--account`, used exactly as typed (case-sensitive, not trimmed). Two exports with the same NAME belong to one account, even if their formats differ.
*   **Input position**: the pair (export index, line). Export index is the 0-based position of the `--account` argument among all `--account` arguments. Line is the 1-based physical line in the file where the record starts (the header is line 1 when it is the first line).
*   **Record**: one parsed transaction, independent of format: account, date, amount, description, input position.
*   **Description**: the original description cell with leading and trailing whitespace removed. Inner whitespace and case are kept. This is what the ledger shows and what rules match against.
*   **Normalised description**: the description with every run of whitespace collapsed to one space and then case-folded: `" ".join(text.split()).casefold()`. Used only for duplicate detection.
*   **Duplicate key**: (account, date, amount, normalised description).
*   **Outflow / inflow**: a record with amount below zero / above zero. A zero amount is neither.
*   **Output order**: records sorted by (date, account, export index, line). Account names compare as plain Python strings (code-point order).

## Critical User Journeys (CUJs)

### CUJ 1: Merge overlapping exports of two accounts

*   **Given**: two current-account exports (Format A) covering 1–31 March and 15 March–15 April, one card export (Format B), and a rules file.
*   **When**: the user runs `python -m txmerge merge --account Current=mar.csv --account Current=apr.csv --account Card=card.csv --rules rules.csv --out ledger.csv`.
*   **Then**: `ledger.csv` holds each real transaction once (repeated purchases kept), the card payment appears on both accounts with category `Transfer` and the same `transfer_id`, every other row has a category or `Uncategorised`, the process exits 0, and stderr shows one summary line.

### CUJ 2: Rerun gives the same file

*   **Given**: the run from CUJ 1 has produced `ledger.csv`.
*   **When**: the user runs the same command again.
*   **Then**: the new `ledger.csv` is byte-identical to the old one.

### CUJ 3: A messy row does not stop the run

*   **Given**: one export contains a row with date `31/02/2026`.
*   **When**: the user runs the merge.
*   **Then**: stderr shows `txmerge: warning: PATH:LINE: invalid date '31/02/2026'`, the row is not in the ledger, all other rows are, and the exit code is 0.

### CUJ 4: A wrong file does not damage the ledger

*   **Given**: `ledger.csv` exists from an earlier run, and the user passes a file whose header matches neither format.
*   **When**: the user runs the merge.
*   **Then**: stderr shows an error naming the file, the header found and the two accepted headers; the exit code is 2; `ledger.csv` is byte-for-byte unchanged.

## Technical Plan (Architecture)

The tool is one in-memory pipeline. Each stage takes a list and returns a list; no stage reads files except the first, and no stage writes files except the last. Nothing touches `--out` until every input and the rules file have been read and validated.

```text
 argv
  │
  ▼
[1] CLI: parse arguments ──────────────── usage error → exit 2
  │  exports: [(name, path)], rules path, out path
  ▼
[2] Read exports (in argument order) ──── unreadable / unrecognised header → exit 2
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
[7] Categorise non-transfer rows (first matching rule, else Uncategorised)
  ▼
[8] Write ledger: temp file in the --out directory, then rename ── OS error → exit 2
  │
  ▼
 summary line on stderr, exit 0
```

### Stage 2: reading exports

A shared CSV reader opens each file with encoding `utf-8-sig` (which removes a byte-order mark if present) and `newline=""`, and reads it with `csv.reader`. It skips rows whose cells are all empty after trimming, silently. The first row that is not skipped is the header. Each header cell is trimmed, and the trimmed header must equal one format's column list exactly: same names, same case, same order, same count.

| Format | Header | Date column (pattern) | Description column | Amount |
| --- | --- | --- | --- | --- |
| A | `Date,Description,Debit,Credit,Balance` | `Date`, day/month/year `D/M/YYYY` | `Description` | exactly one of Debit / Credit filled; Debit → negative, Credit → positive. Balance ignored. |
| B | `Transaction Date,Posting Date,Details,Amount` | `Transaction Date`, `YYYY-M-D` | `Details` | `Amount` as signed. Posting Date ignored and never validated. |

Formats are held in one table of entries (header tuple, row-parsing function). Detection picks the entry whose header matches. A third format is one new entry; dedup, transfers, rules and output do not change.

Field rules, all applied to the cell after trimming:

*   **Date**: one or two digits for day and month, four digits for year, and it must be a real calendar date. Otherwise the row is malformed.
*   **Unsigned amount (Format A Debit/Credit)**: digits, optionally grouped in threes with commas (`1,250.00` or `1250.00`), with an optional decimal point followed by one or two digits. No sign, no currency symbol, no exponent. Otherwise malformed.
*   **Signed amount (Format B)**: the same, with one optional leading `-` or `+`.
*   **Filled**: a cell is filled when it is non-empty after trimming. A Format A row with both or neither of Debit and Credit filled is malformed.
*   **Field count**: a row whose number of cells differs from the header's is malformed.
*   Amounts are converted to `Decimal` after removing commas, then quantised to two places. A zero result is stored as positive zero (`0.00`), so `-0.00` never appears.

### Stage 4: dedup

Dedup runs per account, over all its exports, whatever their format. For each duplicate key, N is the largest number of records with that key in any one export. The stage keeps the first N records with that key in input-position order and drops the rest. Each kept record keeps its own description and input position.

Example: export 0 has `Coffee` twice on 3 March for −3.50; export 1 (same account) has `COFFEE ` three times on the same day for the same amount. N = 3. Kept: both rows from export 0 and the first matching row in export 1, which shows `COFFEE` (trimmed) in the ledger.

### Stage 6: transfers

Walk the sorted records in order. For each outflow not yet paired, the candidates are inflows that are not yet paired, are in a different account, have amount equal to the outflow's absolute amount, and are dated at most 3 days before or after it (3 counts). Choose the candidate with the smallest absolute day difference; on a tie, the one that comes first in output order. If there is a candidate, both records get category `Transfer` and `transfer_id` `T` followed by the pair number padded to at least four digits (`T0001`, `T0002`, …, `T10000`), counting pairs in the order they are made. The walk is greedy: an early outflow can take an inflow that a later outflow would also have matched. This is the stakeholder's rule.

### Stage 7: rules

Rules are read in file order. A pattern matches a record when `pattern.casefold()` is a substring of `description.casefold()`. The first matching rule gives the category. With no match the category is `Uncategorised`. Transfer records are skipped.

### Stage 8: output

The ledger is written with `csv.writer` using `lineterminator="\n"` and `QUOTE_MINIMAL`, encoded UTF-8 without a byte-order mark. The header row is always written, even with zero records. Fields: `date` as `YYYY-MM-DD`; `account` as typed; `description`; `amount` with exactly two decimals, no thousands separator, `-` only for negatives; `category`; `transfer_id` or empty. The file is written to a temporary file in the same directory as `--out` and then moved over `--out` with `os.replace`, so a failed run never leaves a partial or emptied ledger.

### Errors, warnings and exit codes

| Condition | Outcome | Exit | Message (stderr) |
| --- | --- | --- | --- |
| Bad arguments (missing option, `--account` without `=`, empty NAME or PATH, no subcommand) | stop | 2 | argparse usage message |
| Input file missing or unreadable | stop | 2 | `txmerge: error: cannot read PATH: REASON` |
| Input file not valid UTF-8, or the CSV reader raises an error | stop | 2 | `txmerge: error: cannot read PATH: REASON` |
| Input file has no header (empty) or a header matching neither format | stop | 2 | `txmerge: error: PATH: unrecognised header [FOUND]; expected "Date,Description,Debit,Credit,Balance" or "Transaction Date,Posting Date,Details,Amount"` |
| Rules file missing, unreadable, not UTF-8, empty, or header not `pattern,category` | stop | 2 | `txmerge: error: cannot read PATH: REASON` or `txmerge: error: PATH: rules header must be "pattern,category"` |
| Output cannot be written (missing directory, permission) | stop | 2 | `txmerge: error: cannot write OUT: REASON` |
| Malformed data row | skip row | — | `txmerge: warning: PATH:LINE: REASON` |
| Rules row with blank pattern, blank category or wrong field count | skip rule | — | `txmerge: warning: PATH:LINE: REASON` |
| Success | write ledger | 0 | `txmerge: wrote W rows to OUT (read R, skipped M malformed, removed D duplicates, linked T transfer pairs, U uncategorised)` |

Files are read in argument order, then the rules file; the first fatal error stops the run. Warnings appear in that same reading order. Nothing is ever printed to stdout. An unexpected internal error is not caught and exits 1 with a traceback, so a defect is distinguishable from a user error.

## Alternatives Considered

### Alternative A: Sum counts across exports

*   **Pros**: Trivial to implement.
*   **Cons**: Doubles every row in an overlap.
*   **Reason for Rejection**: The stakeholder requires the maximum count, not the sum.

### Alternative B: Treat identical rows as one (set semantics)

*   **Pros**: Simplest possible dedup.
*   **Cons**: Two identical coffees on the same day collapse into one, losing a real transaction.
*   **Reason for Rejection**: Breaks G1 ("never lose a real transaction").

### Alternative C: Fuzzy description matching

*   **Pros**: Would catch truncated descriptions.
*   **Cons**: Non-obvious, could merge distinct transactions, hard to make deterministic.
*   **Reason for Rejection**: The stakeholder put fuzzy matching out of scope.

### Alternative D: Posting Date for Format B

*   **Pros**: Closer to when money moved on the card statement.
*   **Cons**: Differs from what the user sees as the purchase date.
*   **Reason for Rejection**: The stakeholder chose Transaction Date.

### Alternative E: Regex rules, or rules matched on the normalised description

*   **Pros**: More expressive; whitespace-insensitive.
*   **Cons**: Regex adds escaping errors for a non-technical rules file.
*   **Reason for Rejection**: The stakeholder specified a plain case-insensitive substring against the description as written (trimmed only).

### Alternative F: Globally optimal transfer matching

*   **Pros**: Could pair more rows when amounts repeat.
*   **Cons**: More code; results harder to explain.
*   **Reason for Rejection**: The stakeholder specified the greedy walk with closest-date choice.

### Alternative G: Every surviving duplicate copy takes the first export's text

*   **Pros**: Uniform text for a repeated purchase.
*   **Cons**: Hides what the later export actually said; leaves the copy's sort position undefined.
*   **Reason for Rejection**: The stakeholder said each copy keeps its own text.

### Alternative H: Round amounts with more than two decimals

*   **Pros**: Accepts more input.
*   **Cons**: Silently changes money; needs a rounding policy.
*   **Reason for Rejection**: Such rows are treated as malformed and reported instead.

### Alternative I: Fall back to another encoding (cp1252) when UTF-8 fails

*   **Pros**: Accepts more bank files.
*   **Cons**: Output would depend on a guess.
*   **Reason for Rejection**: Exit 2 with a clear message instead.

### Alternative J: Format plug-in classes or registry

*   **Pros**: Formal extension point.
*   **Cons**: Speculative for two formats.
*   **Reason for Rejection**: A table of (header, parse function) entries already makes a new format one entry.

### Alternative K: Write directly to `--out`

*   **Pros**: Simpler.
*   **Cons**: A failure while writing leaves a partial or emptied ledger.
*   **Reason for Rejection**: Breaks G5; temp file plus rename instead.

--------------------------------------------------------------------------------

## Non-Functional Requirements

*   **Determinism**: no iteration over sets or dicts where order reaches the output unless the dict is insertion-ordered from an ordered source; no timestamps, random values or locale-dependent sorting.
*   **Performance**: inputs are personal exports (thousands of rows). Transfer candidates are looked up by absolute amount, so pairing does not compare every outflow with every inflow.
*   **Rollback**: the tool keeps no state; an older version can be run on the same inputs.

--------------------------------------------------------------------------------

### Decision Log

Source tags: [B] brief, [S] stakeholder answer, [E] decision by the design author where the stakeholder said "your call".

| # | Decision | Source | Reason (for [E]) |
| --- | --- | --- | --- |
| D1 | Pipeline order as in the Technical Plan | S/E | Transfer pairing depends on output order, which needs dedup and sort first |
| D2 | Same path given twice = two exports, no warning | E | Max-count dedup absorbs it |
| D3 | Same file under two account names: allowed, no warning | S/E | Stakeholder: different accounts never dedup; a warning was not asked for |
| D4 | Balance column ignored | E | Not needed for any goal |
| D5 | Amount grammar strict; >2 decimals, signs in Format A, currency symbols are malformed; `+` allowed in Format B | E | Never change money silently; a `+` is a valid sign |
| D6 | Dates accept one- or two-digit day and month | E | Avoid losing real transactions on harmless formatting |
| D7 | Zero-amount rows kept; never part of a transfer | E | They are real rows; a zero has no direction |
| D8 | Rules: blank pattern or blank category or wrong field count → warn and skip | E | A blank pattern would match everything |
| D9 | Rules file missing / wrong header → exit 2 | E | Categorising with no rules is almost certainly a mistake |
| D10 | Missing or unreadable input → exit 2 | E | Same class as an unrecognised header |
| D11 | Input quirks: BOM, blank lines, padded header cells, quoted fields handled | E | Common in bank exports |
| D12 | `transfer_id` = `T` + pair number, at least 4 digits | E | Readable, deterministic |
| D13 | One summary line on stderr, nothing on stdout | E | Shows skipped rows so loss is visible |
| D14 | Output bytes: UTF-8 no BOM, `\n`, `QUOTE_MINIMAL` | E | Byte-identical output needs fixed bytes |
| D15 | Temp file then rename for output | E | An existing ledger survives any failure |
| D16 | Unexpected errors exit 1 with traceback | E | Separates defects from user errors |

### Known Limitations

*   Greedy pairing can link two unrelated equal amounts in different accounts within 3 days (for example a £50 card purchase and an unrelated £50 credit). This follows the stakeholder's rule.
*   Rules do not see inner-whitespace differences: `coffee shop` does not match `COFFEE  SHOP`.

### Future Improvements

*   **Third bank format**: add one entry to the format table with its tests.

--------------------------------------------------------------------------------

## Detailed Implementation Plan

### Target Files to Create/Modify

All paths are relative to the repository root. No file outside the repository is touched.

#### 1. `txmerge/__init__.py` (Create)

*   **Type / Scope**: Python package marker.
*   **Proposed Changes**: Empty apart from a one-line module docstring. No imports, so `python -m txmerge` stays fast.

#### 2. `txmerge/__main__.py` (Create)

*   **Type / Scope**: Module entry point.
*   **Proposed Changes**: Calls `sys.exit(main())` with `main` from `txmerge.cli`. Contains nothing else.

#### 3. `txmerge/model.py` (Create)

*   **Type / Scope**: Shared types and constants.
*   **Proposed Changes**:
    *   Constants: `TRANSFER_CATEGORY = "Transfer"`, `UNCATEGORISED = "Uncategorised"`, `TRANSFER_WINDOW_DAYS = 3`, `OUTPUT_HEADER = ("date", "account", "description", "amount", "category", "transfer_id")`, `EXIT_OK = 0`, `EXIT_ERROR = 2`.
    *   `class TxmergeError(Exception)`: a fatal user-facing error; its message is the text after `txmerge: error: `.
    *   `class MalformedRow(Exception)`: raised by row parsers; its message is the warning reason.
    *   `@dataclass class Record`: fields `account: str`, `date: datetime.date`, `amount: decimal.Decimal`, `description: str`, `export_index: int`, `line: int`, `category: str = ""`, `transfer_id: str = ""`. Method `dedup_key() -> tuple` returning `(account, date, amount, normalise(description))`. Method `sort_key() -> tuple` returning `(date, account, export_index, line)`.
    *   `def normalise(text: str) -> str`: returns `" ".join(text.split()).casefold()`.

#### 4. `txmerge/csvio.py` (Create)

*   **Type / Scope**: Shared CSV reading for exports and the rules file.
*   **Proposed Changes**:
    *   `def read_rows(path: str) -> tuple[list[str] | None, int, list[tuple[int, list[str]]]]`: opens `path` with `encoding="utf-8-sig"`, `newline=""`; reads every row with `csv.reader`, recording each row's start line as (the reader's `line_num` before reading the row) + 1. Skips rows whose cells are all empty after `strip()`. Returns (header cells trimmed, or `None` if no non-empty row; header line; list of (line, raw cells) for the remaining rows). Converts `OSError`, `UnicodeDecodeError` and `csv.Error` into `TxmergeError(f"cannot read {path}: {reason}")`. The whole file is read before returning.

#### 5. `txmerge/formats.py` (Create)

*   **Type / Scope**: Header detection and row parsing per format.
*   **Proposed Changes**:
    *   `@dataclass(frozen=True) class Format`: `name: str`, `header: tuple[str, ...]`, `parse: Callable[[list[str]], tuple[date, str, Decimal]]`.
    *   `FORMATS: tuple[Format, ...]` with entries A and B as in the Technical Plan table.
    *   `def detect(header: list[str] | None, path: str) -> Format`: returns the entry whose `header` equals `tuple(header)`; otherwise raises `TxmergeError` with the unrecognised-header message from the errors table (`FOUND` = the trimmed header joined by commas, or `empty file` when `None`).
    *   `def parse_date_dmy(text) -> date` and `def parse_date_ymd(text) -> date`: trimmed text must match `^(\d{1,2})/(\d{1,2})/(\d{4})$` or `^(\d{4})-(\d{1,2})-(\d{1,2})$`; build `datetime.date`; any mismatch or `ValueError` raises `MalformedRow(f"invalid date '{text}'")`.
    *   `def parse_amount(text, signed: bool) -> Decimal`: trimmed text must match `^(\d{1,3}(,\d{3})+|\d+)(\.\d{1,2})?$`, with an optional leading `[+-]` when `signed`. Remove commas, convert with `Decimal`, `quantize(Decimal("0.01"))`; if the result equals zero return `Decimal("0.00")`. Mismatch raises `MalformedRow(f"invalid amount '{text}'")`.
    *   `parse_a(cells)`: date from cell 0; description `cells[1].strip()`; debit cell 2, credit cell 3 (trimmed). Both filled → `MalformedRow("both Debit and Credit are filled")`; neither → `MalformedRow("neither Debit nor Credit is filled")`. Debit → `-parse_amount(debit, signed=False)` then normalise zero; Credit → `parse_amount(credit, signed=False)`. Cell 4 (Balance) is not read.
    *   `parse_b(cells)`: date from cell 0 (`parse_date_ymd`); cell 1 ignored; description `cells[2].strip()`; amount `parse_amount(cells[3], signed=True)`.
    *   `def read_export(export_index: int, name: str, path: str, warn: Callable[[str], None]) -> list[Record]`: calls `read_rows`, `detect`, then for each (line, cells): if `len(cells) != len(fmt.header)` warn `f"{path}:{line}: expected {n} fields, found {m}"` and skip; otherwise call `fmt.parse`, catching `MalformedRow` to warn `f"{path}:{line}: {reason}"` and skip. Returns records in line order.

#### 6. `txmerge/rules.py` (Create)

*   **Type / Scope**: Rules loading and categorisation.
*   **Proposed Changes**:
    *   `def load_rules(path: str, warn) -> list[tuple[str, str]]`: uses `read_rows`. Header `None` or not equal to `["pattern", "category"]` raises `TxmergeError(f'{path}: rules header must be "pattern,category"')`. For each row: wrong field count, blank pattern or blank category (after `strip()`) → warn `f"{path}:{line}: REASON"` and skip. Returns (trimmed pattern casefolded, trimmed category) in file order.
    *   `def categorise(records, rules) -> None`: for each record with empty `transfer_id`, sets `category` to the first rule whose pattern is in `record.description.casefold()`, else `UNCATEGORISED`.

#### 7. `txmerge/dedup.py` (Create)

*   **Type / Scope**: Duplicate removal.
*   **Proposed Changes**:
    *   `def dedup(records: list[Record]) -> list[Record]`: input is in input-position order. Pass 1: count records per `(export_index, dedup_key())`; for each key, `limit[key]` = the maximum count over exports. Pass 2: walk records in input-position order, keep a record while `kept[key] < limit[key]`, incrementing `kept[key]`. Returns the kept records in input-position order. Because the key includes the account, accounts never dedup against each other.

#### 8. `txmerge/transfers.py` (Create)

*   **Type / Scope**: Transfer pairing.
*   **Proposed Changes**:
    *   `def pair_transfers(records: list[Record]) -> int`: `records` is in output order. Build an index from amount to the list of positions of inflows with that amount, in output order. Walk positions in order; for each outflow with empty `transfer_id`, look up inflows with amount `-outflow.amount`; filter to those with empty `transfer_id`, a different `account`, and `abs((inflow.date - outflow.date).days) <= TRANSFER_WINDOW_DAYS`; choose the minimum by `(abs day difference, position)`. On a match increment the pair counter, set both `transfer_id = f"T{counter:04d}"` and both `category = TRANSFER_CATEGORY`. Returns the number of pairs.

#### 9. `txmerge/ledger.py` (Create)

*   **Type / Scope**: Output writing.
*   **Proposed Changes**:
    *   `def format_amount(amount: Decimal) -> str`: `f"{amount:.2f}"` (amounts are already quantised and zero is already positive).
    *   `def write_ledger(path: str, records) -> None`: creates a temp file with `tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=<directory of path, or "." if none>, prefix=".txmerge-", suffix=".tmp", delete=False)`; writes `OUTPUT_HEADER` then one row per record (`date.isoformat()`, account, description, `format_amount`, category, transfer_id) with `csv.writer(f, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)`; closes it and calls `os.replace(temp, path)`. On `OSError` (including a missing directory when creating the temp file) removes the temp file if it exists and raises `TxmergeError(f"cannot write {path}: {reason}")`.

#### 10. `txmerge/cli.py` (Create)

*   **Type / Scope**: Argument parsing and pipeline orchestration.
*   **Proposed Changes**:
    *   `def account_arg(value: str) -> tuple[str, str]`: splits on the first `=`; no `=`, empty NAME or empty PATH raises `argparse.ArgumentTypeError(f"expected NAME=PATH, got '{value}'")`.
    *   `def build_parser() -> argparse.ArgumentParser`: `prog="txmerge"`; subparsers with `dest="command"`, `required=True`; subcommand `merge` with `--account` (`type=account_arg`, `action="append"`, `required=True`, `metavar="NAME=PATH"`), `--rules` (required), `--out` (required). The `merge` help text lists both accepted input headers and the rules header.
    *   `def main(argv: list[str] | None = None) -> int`: parses arguments (argparse exits 2 itself on usage errors). Defines `warn(msg)` that prints `txmerge: warning: {msg}` to stderr. Inside `try`: reads every export in argument order with `read_export`, then `load_rules`; runs `dedup`, sorts with `Record.sort_key`, `pair_transfers`, `categorise`, `write_ledger`; prints the success summary line from the errors table to stderr; returns `EXIT_OK`. `except TxmergeError as e`: prints `txmerge: error: {e}` to stderr and returns `EXIT_ERROR`. Counts for the summary: R = records parsed, M = rows skipped as malformed (count warnings from exports only), D = R − kept, T = pairs, U = rows with category `Uncategorised`, W = rows written.

#### 11. `pyproject.toml` (Create)

*   **Type / Scope**: Project metadata and pytest configuration.
*   **Proposed Changes**: `[project]` name `txmerge`, `requires-python = ">=3.11"`, no runtime dependencies. `[tool.pytest.ini_options]` with `testpaths = ["tests"]`. No build backend is needed; tests run from the repository root.

#### 12. `tests/conftest.py` (Create)

*   **Type / Scope**: Test helpers.
*   **Proposed Changes**: fixture `write(tmp_path)` that returns a function writing given text (exact bytes, `newline=""`) to a named file under `tmp_path` and returning its path. Fixture `run(capsys)` that calls `txmerge.cli.main(argv)` and returns (exit code, stdout, stderr); for argparse errors it catches `SystemExit` and returns its code. Helper `read_ledger(path)` returning the output rows as lists.

#### 13. `tests/test_parsing.py` (Create)

*   **Type / Scope**: Unit tests for `formats.py`, `csvio.py`, `model.normalise`.
*   **Proposed Changes**: Format A debit → negative, credit → positive, `1,250.00` → `-1250.00`; both / neither filled → malformed; Format B signed amounts including `+`; dates `01/02/2026` and `1/2/2026` accepted, `31/02/2026`, `2026/02/01`, `02/01/26` rejected; amounts `NaN`, `1e3`, `1,2,3`, `12.345`, `£5.00`, `-5.00` in Format A rejected; zero debit gives `0.00` not `-0.00`; BOM and padded header cells detected; blank lines skipped and line numbers still physical (a blank line before a bad row shifts its reported line); quoted field with an embedded comma; header-only file gives zero records; wrong field count is malformed; normalise collapses tabs and multiple spaces and case-folds.

#### 14. `tests/test_dedup.py` (Create)

*   **Type / Scope**: Unit tests for `dedup.py`.
*   **Proposed Changes**: two identical rows in one export kept twice; counts 2 and 3 across exports give 3, and the third is the first matching row of the second export with its own text; descriptions differing only in case or inner whitespace collapse with the first occurrence's text kept; different date, amount or truncated text stay separate; same path given twice adds no rows; same rows under two different account names both kept; Format A and Format B exports under one account name dedup against each other.

#### 15. `tests/test_transfers.py` (Create)

*   **Type / Scope**: Unit tests for `transfers.py`.
*   **Proposed Changes**: 3 days apart links, 4 days does not; inflow dated before the outflow links; closest date wins; tie on distance goes to the inflow first in output order; two equal outflows and one inflow link only the first outflow; same account never links; zero amounts never link; IDs `T0001`, `T0002` in walk order; transfer rows get category `Transfer` even when a rule would match (checked end to end).

#### 16. `tests/test_rules.py` (Create)

*   **Type / Scope**: Unit tests for `rules.py`.
*   **Proposed Changes**: case-insensitive substring; first matching rule wins; no match gives `Uncategorised`; header-only rules file gives all `Uncategorised`; blank pattern or blank category warns and is skipped; wrong header raises `TxmergeError`; pattern `coffee shop` does not match `COFFEE  SHOP`.

#### 17. `tests/test_cli.py` (Create)

*   **Type / Scope**: End-to-end tests.
*   **Proposed Changes**:
    *   A full CUJ 1 scenario with two overlapping Format A exports and one Format B export; the output file compared byte-for-byte with an expected string written in the test (header, `\n` endings, sorted order, transfer pair, categories).
    *   Determinism: run twice into two files and compare bytes.
    *   One `subprocess.run([sys.executable, "-m", "txmerge", "merge", ...], cwd=<repo root>)` test proving the module entry point works, exits 0, prints nothing to stdout and one summary line to stderr.
    *   Exit 2 cases, each asserting exit code 2, `txmerge: error:` on stderr, and that a pre-existing `--out` file is byte-for-byte unchanged (and that no new file is created when none existed): unrecognised header, empty input file, missing input file, missing rules file, wrong rules header, non-UTF-8 input (bytes `0xA3`), missing output directory, `--account` without `=`, empty NAME.
    *   Malformed row: exit 0, row absent, stderr contains `PATH:LINE`.
    *   All rows malformed: exit 0, ledger with header only.

### Verification Plan

*   **Compilation/Build**: none; `python -c "import txmerge.cli"` must succeed on Python 3.11+.
*   **Unit Tests**: `python -m pytest` from the repository root must pass.
*   **Static Analysis & Linting**: none required.
*   **Test Coverage Requirement**: every row of the errors table and every decision in the Decision Log has at least one test.
*   **E2E/Integration**: the subprocess test in `tests/test_cli.py`.

--------------------------------------------------------------------------------

*Drafted with EGM*
