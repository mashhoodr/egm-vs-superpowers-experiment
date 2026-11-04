# txmerge: merge overlapping bank exports into one ledger

*   **Author:** Mashhood Rastgar (drafted by Claude, EGM Elephant)
*   **Status:** Draft
*   **Date:** 2026-11-02

--------------------------------------------------------------------------------

## Overview

`txmerge` is a command-line tool for one person who downloads CSV exports from
their bank accounts every few weeks. It reads every export, removes the rows
that appear twice because exports overlap in time, links the two sides of each
money move between the person's own accounts, labels every other row with the
person's category rules, and writes a single CSV ledger.

It is a Python 3.11+ package using only the standard library at runtime
(`pytest` for tests). It runs as:

```
python -m txmerge merge \
  --account NAME=PATH [--account NAME=PATH ...] \
  --rules RULES.csv \
  --out LEDGER.csv
```

The input formats, the rules file, the output columns and the command line are
a fixed contract defined in [`BRIEF.md`](BRIEF.md) and repeated in this
document where needed. Acceptance tests depend on that contract, so this design
does not change it.

## The Problem

The person's exports overlap: an export downloaded on 1 March and another on
15 March both contain the transactions from 1 to 10 March. Naively joining
them double-counts those transactions. Simply dropping identical rows is also
wrong, because two identical rows inside one export (two coffees of the same
price on the same day) are two real purchases.

Money the person moves between their own accounts (for example paying the
credit card from the current account) shows up as an outflow in one account
and an inflow in another. Counted naively, it looks like spending and income
that never happened.

Finally, the person wants every remaining row labelled with a category from a
rules file they maintain, and wants to re-run the tool on the same files and
get exactly the same ledger, so the output can be compared or kept under
version control.

The proposed solution is a single pass pipeline: parse each file into rows,
remove overlap copies per account using a counting rule, sort, pair transfers
with a fixed greedy rule, apply category rules to the rest, and write the
ledger atomically.

## Goals

*   **G1 – No overlap copies.** For each account, a transaction that appears in
    several exports appears in the ledger as many times as the highest count of
    it in any single export.
*   **G2 – No lost transactions.** A row is only removed as a copy when another
    export of the same account has a row with the same date, amount and
    normalised description. Repeats inside one export are always kept.
*   **G3 – Transfers linked.** An outflow and an inflow of the same absolute
    amount in two different accounts, at most 3 days apart, are labelled
    `Transfer` and share a `transfer_id`.
*   **G4 – Everything else categorised** by the first matching rule, or
    `Uncategorised`.
*   **G5 – Deterministic.** The same inputs, given in the same order, produce a
    byte-identical ledger file.
*   **G6 – Clear failures.** A file the tool cannot use stops the run with exit
    code 2, a message on stderr, and no ledger file. A single bad row is skipped
    with a warning naming the file and line, and the run still exits 0.

## Non-Goals

*   Fuzzy description matching. A truncated or reworded description is a
    different transaction.
*   Updating an existing ledger. Every run rebuilds the ledger from the inputs
    and overwrites `--out`.
*   Using the Format A `Balance` column (for example to detect missing rows).
*   Preventing a card refund from being paired with an unrelated outflow of the
    same amount within 3 days. The stakeholder accepted this behaviour.
*   Regular-expression or whole-word rules, multiple currencies, or formats
    other than A and B.
*   Any database, network access, configuration file, or third-party package.

## Open Questions

*   None. Every product question was answered by the stakeholder or decided and
    recorded in "Decisions" below.

## Decisions

These are the product rules the design implements. Rules marked (S) were set
by the stakeholder; rules marked (E) were left to the designer ("your call")
and are recorded here so the implementation has no open choices. The full
question-and-answer record is in [`stakeholder_log.md`](stakeholder_log.md).

| # | Rule | Source |
|---|------|--------|
| D1 | Two rows are the **same transaction** when account name, ledger date, amount and *normalised description* all match. Normalised description = outer whitespace trimmed, every run of inner whitespace replaced by one space, then `str.casefold()`. | S |
| D2 | **Count rule.** Identical rows inside one export are separate real transactions. Across the exports of one account, each same-transaction key appears in the ledger as many times as its highest count in any single export (max, not sum). | S |
| D3 | The kept rows are the earliest occurrences, ordered by `--account` argument position then line number. **Every** kept copy of a key gets the description of the key's first-ever occurrence (earliest argument, then earliest line), outer whitespace trimmed, case unchanged. | S |
| D4 | An "export" is one `--account NAME=PATH` argument. The same PATH given twice for one NAME is two exports, so D2 keeps the count unchanged. Two different NAMEs are two accounts and never deduplicate against each other, even for the same PATH. A consequence (accepted, E): rows of one file given under two NAMEs can pair with each other as transfers under D6. | S |
| D5 | Format B ledger date = `Transaction Date`. `Posting Date` is read only to check the row has the right number of columns. | S |
| D6 | **Transfer**: an outflow (amount < 0) in account X and an inflow (amount > 0) in account Y ≠ X with exactly the opposite amount, whose ledger dates differ by at most 3 calendar days (inclusive: the 1st and the 4th match, the 1st and the 5th do not; the inflow may be dated before the outflow). Descriptions are ignored. Card payments from the current account count. | S |
| D7 | **Pairing order.** Each row joins at most one transfer. Walk outflows in ledger order. For each unpaired outflow, choose among unpaired matching inflows the one with the smallest absolute date gap; on a tie choose the one earliest in ledger order. | S |
| D8 | Both rows of a transfer get category `Transfer` and the same `transfer_id`. Rules are not applied to them. All other rows have an empty `transfer_id`. | S |
| D9 | `transfer_id` = `T` followed by the pair number zero-padded to 4 digits (`T0001`, `T0002`, …), numbered 1, 2, 3 in the order pairs are made by D7. Past 9999 the number simply gets longer (`T10000`). | E |
| D10 | **Rules**: a rule matches when `pattern.casefold()` is a substring of `description.casefold()`, where `description` is the kept text (outer whitespace trimmed, inner whitespace **not** collapsed). The first matching rule in file order wins. No match gives `Uncategorised`. | S |
| D11 | Rules file: header must be exactly `pattern,category` (after the header clean-up in D16), otherwise exit 2. Pattern and category have outer whitespace trimmed. A row whose pattern or category is blank after trimming, or that does not have exactly 2 cells, is skipped with a warning. `Transfer` is an ordinary category label with no special meaning. | E |
| D12 | **Ledger order**: ledger date, then account name (plain Python string order), then `--account` argument position, then line number in that file. | S |
| D13 | **File-level errors** (exit code 2, message on stderr, no ledger file written, and any existing file at `--out` left untouched): a header matching neither format (including a header with an extra column, even an empty one); an input or rules file that is missing, unreadable, not valid UTF-8, or has no non-blank line; a malformed `--account` value; a missing required option. | S (header) / E (rest) |
| D14 | **Row-level errors** (row skipped, warning on stderr naming file and line, run continues, exit 0): wrong number of cells; unparseable date; unparseable amount; Format A row with both Debit and Credit blank or both filled, where a cell that parses to zero (`0`, `0.00`) counts as blank. A file with a header and no data rows is valid and contributes nothing. | S (Format A) / E (both filled, zero-as-blank, Format B) |
| D15 | **Amounts** use `decimal.Decimal`, never `float`. An amount is digits with optional comma thousands separators in groups of three (`1,250.00`) or no separators (`1250.00`), and an optional `.` followed by 1 or 2 digits. Format A Debit/Credit take no sign. Format B Amount takes an optional leading `-` or `+`. Anything else (currency symbols, brackets, spaces inside, 3+ decimals) makes the row malformed (D14). | E |
| D16 | **File clean-up**: files are read as UTF-8 with an optional byte-order mark. Header cells have outer whitespace trimmed; header names are otherwise exact and case-sensitive. Data cells have outer whitespace trimmed before parsing. Lines whose cells are all blank are skipped silently and are not counted. | E |
| D17 | **Zero amounts** (0.00) are kept and categorised by rules. They are neither outflows nor inflows, so never part of a transfer. They are written as `0.00`, never `-0.00`. | E |
| D18 | The Format A `Balance` column is ignored. | E |
| D19 | One account NAME may receive files in both formats. All its rows form one account for D1–D7. | E |
| D20 | **Always rebuild**: the tool never reads an existing ledger; `--out` is overwritten on success. | S |
| D21 | **Determinism**: the same inputs in the same order give a byte-identical ledger: UTF-8 without byte-order mark, `\n` line endings, minimal CSV quoting, amounts formatted with exactly 2 decimals. | S (goal) / E (encoding) |
| D22 | **Messages**: stdout stays empty. Warnings and the end-of-run summary go to stderr. | E |
| D23 | **Output file mode**: the ledger is created as a temporary file (mode 0600, private bank data) and renamed onto `--out`, so it ends up 0600. No `fsync`. | E |

## Critical User Journeys (CUJs)

### CUJ 1: Merge overlapping exports of two accounts

*   **Given**: `cur_jan.csv` and `cur_feb.csv` (Format A) for account `current`
    overlap on 10–15 January; `card.csv` (Format B) for account `card`; a rules
    file with `TESCO,Groceries`.
*   **When**: the person runs
    `python -m txmerge merge --account current=cur_jan.csv --account current=cur_feb.csv --account card=card.csv --rules rules.csv --out ledger.csv`.
*   **Then**: exit code 0; each 10–15 January transaction appears once (or as
    many times as it repeats inside a single export); Tesco rows are
    `Groceries`; the summary line on stderr shows how many duplicates were
    removed.

### CUJ 2: Pay the credit card from the current account

*   **Given**: `current` has `05/03/2026, CARD PAYMENT, 500.00,,` (outflow) and
    `card` has `2026-03-07,2026-03-08,PAYMENT RECEIVED,500.00` (inflow).
*   **When**: the person runs the merge.
*   **Then**: both rows have category `Transfer` and the same `transfer_id`
    (`T0001` if it is the first pair); neither is categorised by rules.

### CUJ 3: Re-run gives the same file

*   **Given**: a ledger produced from some inputs.
*   **When**: the person runs the same command again with the same files in the
    same order.
*   **Then**: the new ledger is byte-identical to the old one.

### CUJ 4: A file in an unknown format

*   **Given**: one `--account` points at a CSV whose header is neither format.
*   **When**: the person runs the merge.
*   **Then**: exit code 2, a stderr message naming that file, and no ledger file
    is created (an existing one is left unchanged).

### CUJ 5: A bad row in an otherwise good file

*   **Given**: a Format A file where line 7 has both Debit and Credit blank.
*   **When**: the person runs the merge.
*   **Then**: exit code 0, the ledger is written without that row, and stderr
    has `txmerge: warning: <path>:7: ...; row skipped`.

## Technical Plan (Architecture)

### Data flow

The tool is one process that runs a fixed pipeline over in-memory lists. Each
stage is a plain function in its own module, takes a list and returns a list,
and does not touch the filesystem except the reader and the writer.

```text
 CLI args ──► parse_args ──► list of (account, path, arg_index)
                                   │
 rules.csv ──► load_rules ─────────┼──────────────────────────────┐
                                   ▼                              │
 each export ──► read_export ──► Rows (all accounts, input order) │
   (header check: Format A / B,    │   bad rows → stderr warning  │
    else exit 2)                   ▼                              │
                             deduplicate (per account, D1–D4)     │
                                   ▼                              │
                             sort_ledger (D12)                    │
                                   ▼                              │
                             pair_transfers (D6–D9)               │
                                   ▼                              │
                             categorise (D10) ◄───────────────────┘
                                   ▼
                             write_ledger (temp file + rename, D21)
                                   ▼
                             summary line → stderr, exit 0
```

All file-level checks (every input header, the rules file header) happen
before any output is written, so a file-level error never leaves a partial or
truncated ledger.

### Row record

Every parsed row becomes one immutable record:

| Field | Type | Meaning |
|-------|------|---------|
| `account` | `str` | NAME from `--account` |
| `date` | `datetime.date` | ledger date (Format A `Date`, Format B `Transaction Date`) |
| `description` | `str` | original text, outer whitespace trimmed |
| `amount` | `Decimal` | signed, outflow negative, quantized to `0.01` |
| `arg_index` | `int` | 0-based position of the `--account` argument the row came from |
| `line_no` | `int` | 1-based physical line number in the file where the row ends (`csv.reader.line_num`) |

`category` and `transfer_id` are added at the end, producing output rows.

The **same-transaction key** is `(account, date, amount, normalise(description))`
where `normalise` = `" ".join(description.split()).casefold()`.

### Reading an export

1. Open with `encoding="utf-8-sig"`, `newline=""` and read with `csv.reader`.
2. The first row whose cells are not all blank is the header. Trim each cell.
   Exactly `Date,Description,Debit,Credit,Balance` → Format A; exactly
   `Transaction Date,Posting Date,Details,Amount` → Format B; otherwise
   file-level error (exit 2). A file with no non-blank row is also a file-level
   error.
3. For each later row: skip silently if every cell is blank; otherwise it must
   have exactly as many cells as the header, then parse:
   * Format A: `Date` with `DD/MM/YYYY`; exactly one of `Debit`/`Credit`
     non-blank, where a cell that parses to zero counts as blank (D14); amount = −Debit or +Credit (unsigned amount grammar, D15).
   * Format B: `Transaction Date` with `YYYY-MM-DD`; amount = signed `Amount`
     (D15).
   * Any failure → warning, skip, count as skipped.

Dates are parsed with `datetime.strptime` using `%d/%m/%Y` and `%Y-%m-%d`, after
checking the text against `^\d{2}/\d{2}/\d{4}$` / `^\d{4}-\d{2}-\d{2}$` so only
zero-padded dates are accepted.

### Deduplication

Within each account (rows grouped by NAME):

1. For each export (`arg_index`), count how many rows have each key.
2. `target[key]` = the largest of those counts.
3. Walk the account's rows ordered by `(arg_index, line_no)` and keep a row only
   while fewer than `target[key]` rows with that key have been kept.

4. Replace the description of every kept row with the trimmed text of its
   key's first occurrence in `(arg_index, line_no)` order.

This keeps the earliest occurrences (D3) and lets a later export contribute
extra copies only when it has more of a key than every earlier export. Removed
rows are counted for the summary.

Worked example: export 1 has key K twice, export 2 has K three times. Target is
3. Both rows from export 1 are kept, then the first K row of export 2, and the
other two K rows of export 2 are dropped. The ledger has K three times.

### Sorting

Sort all kept rows by `(date, account, arg_index, line_no)`. Every row has a
unique `(arg_index, line_no)`, so the order is total and stable.

### Transfer pairing

1. Build an index from amount to the list of ledger positions of inflows with
   that amount (amount > 0), in ledger order.
2. Walk the ledger in order. For each row with amount < 0 that is not yet
   paired, look up inflows with amount equal to `-amount`. Keep only those that
   are unpaired, in a different account, and with `abs((inflow.date -
   outflow.date).days) <= 3`. If any remain, choose the one with the smallest
   `(abs(day gap), ledger position)`.
3. Assign both rows `transfer_id = f"T{n:04d}"` for the n-th pair (n starts at
   1) and mark them paired.

Rows with amount 0 are never in the index and never looked up (D17).

Worked examples (accounts `cur` and `card`, all amounts 50.00):

| Ledger (in order) | Result | Why |
|---|---|---|
| cur 03-01 −50; card 03-04 +50 | pair | gap 3 |
| cur 03-01 −50; card 03-05 +50 | no pair | gap 4 |
| card 02-27 +50; cur 03-01 −50 | pair | inflow may come first (gap 2) |
| cur 03-01 −50; card 03-02 +50; card 03-02 +50 | first card row pairs | equal gaps, earlier ledger position wins |
| cur 03-01 −50; cur 03-03 −50; card 03-03 +50 | first cur row pairs, second stays unpaired | greedy: earlier outflow takes the only inflow even though the second outflow is closer. Expected, not a bug. |
| cur 03-01 −50; cur 03-02 +50 | no pair | same account |

### Categorisation

Rules are loaded once into a list of `(pattern.casefold(), category)` in file
order. Matching uses the kept description (trimmed, inner spaces as written),
not the dedup key (D10). For each ledger row without a `transfer_id`, the category is the first
rule whose folded pattern is in `description.casefold()`, else `Uncategorised`.
Transfer rows get `Transfer`.

### Writing

1. Format each row as `date.isoformat()`, account, description,
   `format(amount, ".2f")` (with any zero amount replaced by `Decimal("0.00")`
   first so `-0.00` cannot appear), category, transfer_id or empty string.
2. Write the header `date,account,description,amount,category,transfer_id` and
   rows with `csv.writer(f, lineterminator="\n")` (default minimal quoting) to a
   temporary file created in the same directory as `--out`, opened with
   `encoding="utf-8", newline=""`.
3. `os.replace` the temporary file onto `--out`. If writing fails, delete the
   temporary file and exit 2.

### Messages and exit codes

| Situation | stderr | Exit |
|-----------|--------|------|
| Success | `txmerge: R rows read, S skipped, D duplicates removed, T transfers linked, W rows written` | 0 |
| Skipped row | `txmerge: warning: PATH:LINE: REASON; row skipped` | (continues) |
| Skipped rule | `txmerge: warning: RULES_PATH:LINE: REASON; rule skipped` | (continues) |
| File-level error | `txmerge: error: MESSAGE` (names the file) | 2 |
| Bad command line | argparse usage message | 2 |

`R` counts data rows that were not blank (parsed plus skipped). `S` counts
skipped rows. `W` = `R − S − D`.

### Scale

A personal ledger is thousands of rows, not millions. Everything is held in
memory. Dedup is linear; pairing is linear in rows times the number of inflows
sharing one amount. No performance work is planned.

## Alternatives Considered

### Alternative A: Deduplicate by summing, or by keeping one row per key

*   **Pros**: One line of code (`set()` or `Counter` sum).
*   **Cons**: Summing counts every overlap twice. One row per key drops the
    second of two identical real purchases in one export.
*   **Reason for Rejection**: Breaks G1 or G2. The max-count rule (D2) is the
    only one of the three that keeps real repeats and removes overlap copies.

### Alternative B: Deduplicate across accounts that point at the same file

*   **Pros**: Protects against the person passing one file under two names.
*   **Cons**: Contradicts the stakeholder's rule that different names are
    different accounts.
*   **Reason for Rejection**: Stakeholder decision (D4).

### Alternative C: Fuzzy description matching

*   **Pros**: Would catch the same transaction with truncated or reworded text.
*   **Cons**: Can merge two real, different transactions; behaviour is hard to
    predict; needs thresholds.
*   **Reason for Rejection**: Stakeholder ruled it out; G2 ("never lose a real
    transaction") outweighs catching reworded copies.

### Alternative D: Globally optimal transfer matching

*   **Pros**: Could minimise total date gap across all pairs, or avoid a greedy
    early choice stealing an inflow that a later outflow needed.
*   **Cons**: Needs an assignment algorithm; results are harder to explain and
    predict.
*   **Reason for Rejection**: The stakeholder specified the greedy rule (D7).

### Alternative E: Use descriptions to confirm transfers

*   **Pros**: Fewer false pairs (for example a card refund pairing with an
    unrelated outflow).
*   **Cons**: Bank wording varies; would miss real transfers.
*   **Reason for Rejection**: Stakeholder ruled descriptions out (D6) and
    accepted the false-pair risk.

### Alternative F: Hash-based transfer ids

*   **Pros**: An id would not change when unrelated rows are added.
*   **Cons**: Long, unreadable ids; identical row pairs would need a tie-break
    anyway.
*   **Reason for Rejection**: Sequential ids (D9) are readable and already
    deterministic for fixed inputs, which is what G5 asks for. Stable ids across
    *different* inputs are not a goal.

### Alternative G: Posting Date for Format B

*   **Reason for Rejection**: Stakeholder chose Transaction Date (D5).

### Alternative H: `float` amounts

*   **Pros**: Simpler parsing.
*   **Cons**: `0.1 + 0.2` style errors make equal amounts compare unequal,
    which breaks both dedup and transfer matching.
*   **Reason for Rejection**: `Decimal` is in the standard library and exact.

### Alternative I: Single-module script

*   **Pros**: Fewer files.
*   **Cons**: Harder to test each stage alone.
*   **Reason for Rejection**: Small separate modules let each rule (D1–D23) be
    tested directly; the cost is a few imports.

--------------------------------------------------------------------------------

## Non-Functional Requirements

*   **Security & Privacy**: Bank data stays on the local disk; no network
    access. The tool reads only the files named on the command line and writes
    only `--out` (plus its temporary file in the same directory).
*   **Performance**: Thousands of rows; in-memory; no targets beyond "finishes
    in well under a second for a year of exports".
*   **Rollout & Rollback**: None needed; the tool never modifies its inputs and
    rebuilds the ledger every run.

## Risks & Limits

*   **Greedy pairing is not optimal.** An earlier outflow can take an inflow a
    later outflow needed, leaving one unpaired (see the worked examples).
    Specified by the stakeholder.
*   **False transfers.** A card refund, or rows of one file given under two
    names, can pair as a transfer. Accepted.
*   **Card dates.** Transaction Date on a card payment may be more than 3 days
    after the current-account debit; such payments stay unpaired and are
    categorised by rules.
*   **Max-count dedup** cannot tell a genuine extra repeat in a later export
    from a copy when an earlier export was cut off mid-day. Accepted.
*   **Silent data loss is limited** by warning on every skipped row and
    printing a skipped count in the summary; `0.00` in the unused Debit/Credit
    column is treated as blank so such banks do not lose every row.
*   **Encoding.** Non-UTF-8 exports (for example cp1252) stop the run with exit
    2 rather than guessing an encoding.

### Future Improvements

*   Optional check of Format A running balances to spot missing rows.
*   Optional description hint to stop card refunds pairing as transfers.

--------------------------------------------------------------------------------

## Detailed Implementation Plan

All paths are relative to the repository root. Work is in four phases; each
phase ends with `python -m pytest` passing.

### Phase 1 – Parsing

#### 1. `txmerge/__init__.py` (Create)

*   **Type / Scope**: Python package marker.
*   **Proposed Changes**: Empty apart from a module docstring.

#### 2. `txmerge/model.py` (Create)

*   **Type / Scope**: Data types.
*   **Proposed Changes**:
    *   `class InputError(Exception)`: a file-level problem; the message names
        the file. Raised by readers and the rules loader, caught only in
        `cli.main`.
    *   `@dataclass(frozen=True) class Row`: fields `account: str`,
        `date: datetime.date`, `description: str`, `amount: Decimal`,
        `arg_index: int`, `line_no: int`.
    *   `@dataclass(frozen=True) class LedgerRow`: `row: Row`, `category: str`,
        `transfer_id: str` (empty string when not a transfer).
    *   `def normalise(description: str) -> str`: returns
        `" ".join(description.split()).casefold()`.
    *   `def row_key(row: Row) -> tuple`: returns
        `(row.account, row.date, row.amount, normalise(row.description))`.
    *   `Warn = Callable[[str], None]`: the warning callback type. Every
        function that can skip input takes `warn: Warn` and calls it with the
        full message text (`f"txmerge: warning: {path}:{line}: {reason}; row skipped"`).

#### 3. `txmerge/readers.py` (Create)

*   **Type / Scope**: Export parsing (D5, D13–D16, D18, D19).
*   **Proposed Changes**:
    *   Constants `FORMAT_A = ("Date", "Description", "Debit", "Credit", "Balance")`
        and `FORMAT_B = ("Transaction Date", "Posting Date", "Details", "Amount")`.
    *   `UNSIGNED = re.compile(r"^(\d{1,3}(,\d{3})+|\d+)(\.\d{1,2})?$")`.
    *   `def parse_amount(text: str, signed: bool) -> Decimal`: strip; if
        `signed` and the text starts with `-` or `+`, remember and drop the
        sign; the rest must match `UNSIGNED` else raise `ValueError`; remove
        commas; `Decimal(...)`, apply sign, `.quantize(Decimal("0.01"))`.
    *   `def parse_date(text: str, fmt: str, pattern: re.Pattern) -> date`:
        `pattern.fullmatch` else `ValueError`; then
        `datetime.strptime(text, fmt).date()` (its `ValueError` for 31/02 etc.
        propagates).
    *   `def read_export(path: str, account: str, arg_index: int, warn: Warn) -> tuple[list[Row], int, int]`:
        returns `(rows, rows_read, rows_skipped)`.
        *   `OSError` / `UnicodeDecodeError` on open or read →
            `InputError(f"cannot read {path}: {exc}")`.
        *   No non-blank row → `InputError(f"{path}: file is empty")`.
        *   A header-only file returns `([], 0, 0)`.
        *   Header not A or B → `InputError(f"{path}: unrecognised header: {','.join(cells)}")`.
        *   Per data row (non-blank): count as read; on wrong cell count,
            bad date, bad amount, or Debit/Credit both blank or both filled
            (a cell that `parse_amount` turns into zero counts as blank),
            call `warn` with reasons `"expected N cells, got M"`,
            `"bad date 'X'"`, `"bad amount 'X'"`,
            `"Debit and Credit both blank"`, `"Debit and Credit both filled"`;
            count as skipped.
        *   Description = `Description` (A) or `Details` (B), outer
            whitespace trimmed.

#### 4. `tests/test_readers.py` (Create)

*   **Type / Scope**: Unit tests (pytest, `tmp_path` fixtures written inline).
*   **Proposed Changes**: Cases:
    *   Format A debit row → negative amount; credit row → positive; `1,250.00`
        → `Decimal("1250.00")`; date `05/03/2026` → `2026-03-05`.
    *   Format B `-12.50` → `-12.50`; `+3` → `3.00`; Transaction Date used,
        Posting Date ignored.
    *   Header with BOM and spaces around cells is recognised.
    *   Unknown header → `InputError`; empty file → `InputError`; missing
        file → `InputError`.
    *   `0.00` debit with `25.00` credit → `+25.00`; `0.00` in both → skipped.
    *   Header-only file → no rows, no error; header with an extra empty
        column (`Date,Description,Debit,Credit,Balance,`) → `InputError`;
        invalid UTF-8 bytes → `InputError`.
    *   Skipped with warning (and exit unaffected): both blank, both filled,
        `£5.00`, `(5.00)`, `1.234`, `1,25.00`, `5/3/2026`, `2026-02-30`,
        wrong cell count. Warning text contains path and line number.
    *   Blank lines are skipped silently and not counted.
    *   Balance column value is ignored (garbage there does not skip the row).

### Phase 2 – Dedup and ordering

#### 5. `txmerge/dedup.py` (Create)

*   **Type / Scope**: Overlap removal (D1–D4).
*   **Proposed Changes**: `def deduplicate(rows: list[Row]) -> tuple[list[Row], int]`
    implementing the four steps in Technical Plan › Deduplication (kept copies
    get the first occurrence's text via `dataclasses.replace`); returns the
    kept rows (any order) and the number removed. Group by `row.account`; never
    compare rows of different accounts.

#### 6. `txmerge/ledger.py` (Create)

*   **Type / Scope**: Ordering and output (D12, D17, D21).
*   **Proposed Changes**:
    *   `def sort_rows(rows: list[Row]) -> list[Row]`: `sorted` by
        `(r.date, r.account, r.arg_index, r.line_no)`.
    *   `HEADER = ["date", "account", "description", "amount", "category", "transfer_id"]`.
    *   `def format_amount(a: Decimal) -> str`: `Decimal("0.00")` if `a == 0`
        else `a`, then `format(.., ".2f")`.
    *   `def write_ledger(path: str, rows: list[LedgerRow]) -> None`:
        `tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="",
        dir=os.path.dirname(os.path.abspath(path)), prefix=".txmerge-",
        suffix=".tmp", delete=False)`; `csv.writer(f, lineterminator="\n")`;
        write header and rows; close; `os.replace(tmp, path)`. On `OSError`
        remove the temp file if it exists and raise
        `InputError(f"cannot write {path}: {exc}")`.

#### 7. `tests/test_dedup.py` (Create)

*   **Type / Scope**: Unit tests on `Row` lists built in code.
*   **Proposed Changes**: Cases:
    *   Overlap of two exports → one copy.
    *   Two identical rows inside one export → both kept.
    *   Export 1 has K twice, export 2 has K three times → three kept; the two
        from export 1 are among them.
    *   Same PATH twice for one account → no change in count.
    *   Same rows under two account names → both kept.
    *   Descriptions differing only by case or inner/outer spaces → one copy,
        text from the earliest export kept.
    *   Truncated description, different date, or different amount → both kept.
    *   Account with Format A and Format B exports sharing a key → one copy.

#### 8. `tests/test_ledger.py` (Create)

*   **Type / Scope**: Unit tests.
*   **Proposed Changes**: sort order on ties of date and account;
    `format_amount(Decimal("-0.00")) == "0.00"`; written file starts with the
    exact header, uses `\n` only, has no BOM, quotes a description containing a
    comma; failed run leaves an existing `--out` unchanged.

### Phase 3 – Transfers and rules

#### 9. `txmerge/transfers.py` (Create)

*   **Type / Scope**: Transfer pairing (D6–D9, D17).
*   **Proposed Changes**: `def pair_transfers(rows: list[Row]) -> list[str]`:
    input is the sorted ledger; returns a list the same length holding the
    `transfer_id` for each position (empty string if unpaired). Algorithm as in
    Technical Plan › Transfer pairing.

#### 10. `txmerge/rules.py` (Create)

*   **Type / Scope**: Rules loading and categorisation (D10, D11).
*   **Proposed Changes**:
    *   `def load_rules(path: str, warn: Warn) -> list[tuple[str, str]]`:
        same open/BOM/blank-line handling as readers; missing/unreadable →
        `InputError`; header (cells trimmed) not exactly
        `["pattern", "category"]` or file empty → `InputError`; rows without
        exactly 2 cells or with a blank trimmed pattern or category →
        `warn(f"txmerge: warning: {path}:{line}: {reason}; rule skipped")`.
        Returns `(pattern.casefold(), category)` pairs in file order.
    *   `def categorise(description: str, rules) -> str`: first rule whose
        pattern is in `description.casefold()`, else `"Uncategorised"`.

#### 11. `tests/test_transfers.py` (Create)

*   **Type / Scope**: Unit tests.
*   **Proposed Changes**: Cases: basic pair across accounts; same account never
    pairs; gap of 3 days pairs, 4 does not; inflow dated before outflow pairs;
    nearest date wins; equal gaps → earlier ledger position wins; one inflow
    cannot serve two outflows; amounts must match exactly (`-500.00` vs
    `499.99` no pair); zero amounts never pair; ids numbered `T0001`, `T0002`
    in pairing order.

#### 12. `tests/test_rules.py` (Create)

*   **Type / Scope**: Unit tests.
*   **Proposed Changes**: case-insensitive substring; first rule in file order
    wins; no match → `Uncategorised`; regex characters (`.`, `*`) are literal;
    blank pattern/category rows skipped with warning; bad header →
    `InputError`; category literally `Transfer` is allowed.

### Phase 4 – Command line

#### 13. `txmerge/cli.py` (Create)

*   **Type / Scope**: Argument parsing and orchestration.
*   **Proposed Changes**:
    *   `def build_parser() -> argparse.ArgumentParser`: program name
        `txmerge`; sub-command `merge` (required) with `--account`
        (`action="append"`, required), `--rules` (required), `--out`
        (required).
    *   `def parse_account(value: str) -> tuple[str, str]`: split on the first
        `=`; both sides non-empty after trimming, else
        `parser.error(f"--account must be NAME=PATH, got {value!r}")` (exit 2).
    *   `def main(argv: list[str] | None = None) -> int`:
        1. Parse arguments.
        2. `warn = lambda msg: print(msg, file=sys.stderr)`.
        3. Inside `try`: load rules; read every export in argument order
           (all file-level checks happen here, before any writing);
           deduplicate; sort; pair transfers; build `LedgerRow`s
           (category `Transfer` where a `transfer_id` exists, else
           `categorise`); `write_ledger`.
        4. `except InputError as e`: print `f"txmerge: error: {e}"` to stderr,
           return 2.
        5. Print the summary line (Technical Plan › Messages) and return 0.

#### 14. `txmerge/__main__.py` (Create)

*   **Type / Scope**: Entry point for `python -m txmerge`.
*   **Proposed Changes**: `import sys; from txmerge.cli import main;
    sys.exit(main())`.

#### 15. `tests/test_cli.py` (Create)

*   **Type / Scope**: End-to-end tests calling `main([...])` and, once,
    `subprocess.run([sys.executable, "-m", "txmerge", "merge", ...])`.
*   **Proposed Changes**: Cases:
    *   CUJ 1–5 from this document, each as one test.
    *   Exact output bytes for a small fixed scenario (header, ordering,
        amounts, categories, transfer ids, blank `transfer_id`).
    *   Running twice gives byte-identical files.
    *   Malformed `--account` (`noequals`, `=path`, `name=`) → exit 2.
    *   Missing rules file → exit 2, no output file.
    *   Summary line printed to stderr; stdout empty.

#### 16. `README.md` (Create)

*   **Type / Scope**: User documentation.
*   **Proposed Changes**: Usage example, the two input formats, the rules file,
    and the rules D1–D23 in one short list each, plus exit codes.

### Verification Plan

*   **Build**: none (pure Python).
*   **Unit and end-to-end tests**: `python -m pytest` from the repository root
    must pass with zero failures.
*   **Static Analysis**: none required (no third-party tools allowed at
    runtime; optional `python -m pyflakes` is not part of the gate).
*   **Coverage**: every rule D1–D23 has at least one test named in the test
    lists above.
*   **E2E**: `tests/test_cli.py` runs the real `python -m txmerge` once via
    `subprocess`.

--------------------------------------------------------------------------------

*Drafted with EGM*
