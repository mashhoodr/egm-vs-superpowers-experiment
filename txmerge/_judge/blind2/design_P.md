# txmerge: merge overlapping bank exports into one ledger

*   **Author:** Mashhood Rastgar (drafted by [redacted])
*   **Status:** Approved
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
a fixed contract defined in [`BRIEF.md`](../../BRIEF.md) and repeated in this
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

The proposed solution is a fixed sequence of in-memory stages: parse each file into rows,
remove overlap copies per account using a counting rule, sort, pair transfers
with a fixed greedy rule, apply category rules to the rest, and write the
ledger only after every input has been checked.

## Goals

*   **G1 – No overlap copies.** For each account, a transaction that appears in
    several exports appears in the ledger as many times as the highest count of
    it in any single export.
*   **G2 – Remove only overlap copies.** A row is only removed as a copy when
    another export of the same account has a row with the same date, amount
    and normalised description. Repeats inside one export are always kept. The
    one known case where this still drops a real transaction is described
    under Risks & Mitigations (R4).
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
question-and-answer record is in [`stakeholder_log.md`](../../stakeholder_log.md).

### Fixed formats (from `BRIEF.md`, not changeable)

| File | Header row (exact) | Columns used |
|------|--------------------|--------------|
| Format A (current account) | `Date,Description,Debit,Credit,Balance` | `Date` is `DD/MM/YYYY`. `Description` is the description. `Debit` and `Credit` are unsigned amounts or blank: amount = −Debit, or +Credit. `Balance` ignored (D18). |
| Format B (credit card) | `Transaction Date,Posting Date,Details,Amount` | `Transaction Date` is `YYYY-MM-DD` and is the ledger date (D5). `Details` is the description. `Amount` is signed: negative = spend, positive = refund/payment. `Posting Date` ignored. |
| Rules | `pattern,category` | one rule per row, in priority order (D10, D11) |
| Ledger (output) | `date,account,description,amount,category,transfer_id` | `date` ISO `YYYY-MM-DD`; `account` = NAME; `amount` signed, outflow negative, 2 decimals; `transfer_id` blank unless a transfer |

### Rules

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
| D13 | **File-level errors** (exit code 2, message on stderr, no ledger file written, and any existing file at `--out` left untouched): a header matching neither format (including a header with an extra column, even an empty one); an input or rules file that is missing, unreadable, not valid UTF-8, or has no non-blank line; a malformed `--account` value; a missing required option; `--out` naming an input or the rules file (D20). Failure to write `--out` also exits 2 and also leaves any existing `--out` unchanged (D23). | S (header) / E (rest) |
| D14 | **Row-level errors** (row skipped, warning on stderr naming file and line, run continues, exit 0): wrong number of cells; unparseable date (day and month may be unpadded, e.g. `5/3/2026`; impossible dates such as `31/02/2026` are row errors); unparseable amount; Format A row with both Debit and Credit blank or both filled, where a cell that parses to zero (`0`, `0.00`) counts as blank. A file with a header and no data rows is valid and contributes nothing. Checks run in this order and the first failure gives the warning's `REASON`: cell count; date; then Format A: each non-blank Debit/Credit parses (else `bad amount`), then both blank / both filled (zero counting as blank); or Format B: Amount parses. | S (Format A) / E (both filled, zero-as-blank, Format B) |
| D15 | **Amounts** use `decimal.Decimal`, never `float`. An amount is digits with optional comma thousands separators in groups of three (`1,250.00`) or no separators (`1250.00`), and an optional `.` followed by 1 or 2 digits. Format A Debit/Credit take no sign. Format B Amount takes an optional leading `-` or `+`. Anything else (currency symbols, brackets, spaces inside, 3+ decimals) makes the row malformed (D14). Exports are assumed to be standard CSV, where a cell containing a comma (such as `1,250.00`) is wrapped in double quotes. An unquoted `1,250.00` splits the row into extra cells; such a row is not repaired and is skipped with the `expected N cells, got M` warning (D14; stakeholder, review round). | E |
| D16 | **File clean-up**: files are read as UTF-8 with an optional byte-order mark. Header cells have outer whitespace trimmed; header names are otherwise exact and case-sensitive. Data cells have outer whitespace trimmed before parsing. Lines whose cells are all blank are skipped silently and are not counted in the summary counts `R` or `S`; they still count for physical line numbers. | E |
| D17 | **Zero amounts** (0.00) are kept and categorised by rules. Because of D14, a zero amount can only come from a Format B row. They are neither outflows nor inflows, so never part of a transfer. They are written as `0.00`, never `-0.00`. | E |
| D18 | The Format A `Balance` column is ignored. | E |
| D19 | One account NAME may receive files in both formats. All its rows form one account for D1–D7. | E |
| D20 | **Always rebuild**: the tool never reads an existing ledger; `--out` is overwritten on success. **Same-file check**: after the rules file and every input have been read successfully (so they all exist) and before `--out` is opened, if `--out` exists and `os.path.samefile(--out, X)` is true for any input or the rules file X, the run stops with exit 2 and the "--out is also an input" message. If `--out` does not exist it cannot be an input. If `os.path.samefile` itself raises `OSError`, the run stops with exit 2 and the "cannot read" message for that input. So the tool never modifies its inputs. | S / E (same-file check) |
| D21 | **Determinism**: the same inputs in the same order give a byte-identical ledger: UTF-8 without byte-order mark, `\n` line endings, minimal CSV quoting, amounts formatted with exactly 2 decimals. | S (goal) / E (encoding) |
| D22 | **Messages**: stdout stays empty. Warnings and the end-of-run summary go to stderr. | E |
| D23 | **Atomic write**: after every input check has passed, the ledger is written to a new temporary file in the same directory as `--out` and then renamed onto `--out` with `os.replace`. If `--out` already exists, its permission bits are copied to the temporary file first. If anything fails or the run is interrupted, the temporary file is removed and `--out` is left exactly as it was; an `OSError` exits 2 with the "cannot write" message. Accepted side effects: a new ledger gets mode 0600 (what `tempfile.mkstemp` creates; suitable for bank data); a symlink at `--out` is replaced by a regular file; no `fsync`, so a power cut right after the rename can lose the new ledger (the next run rebuilds it). | E |
| D24 | **`--account` value**: split on the first `=`; NAME is the text before it and PATH the text after it, each with outer whitespace trimmed (so `a=b=c` gives NAME `a`, PATH `b=c`). A value with no `=`, or with an empty NAME or PATH after trimming, is a usage error: exit 2 with the bad `--account` message. | E |

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
    has the "Skipped data row" warning (Messages table) for line 7 with
    reason `Debit and Credit both blank`.

## Technical Plan (Architecture)

The Decisions table above is the single source of truth for behaviour. This
section explains how the pieces fit and gives the two algorithms that need
more than one sentence (deduplication and transfer pairing). It cites rules by
number instead of repeating them.

### Data flow

The tool is one process that runs a fixed pipeline over in-memory lists. Only
the readers and the writer touch the filesystem; the middle stages are plain
functions.

```text
 CLI args ──► build_parser / parse_account (D24) ──► list of (account, path, arg_index)
                                   │
 rules.csv ──► load_rules ─────────┼──────────────────────────────┐
                                   ▼                              │
 each export ──► read_export ──► Rows (all accounts, input order) │
   (header check: Format A / B,    │   bad rows → stderr warning  │
    else exit 2)                   ▼                              │
                             same-file check (D20; exit 2)        │
                                   ▼                              │
                             deduplicate (per account, D1–D4)     │
                                   ▼                              │
                             sort_rows (D12)                      │
                                   ▼                              │
                             pair_transfers (D6–D9)               │
                                   ▼                              │
                             categorise (D8, D10) ◄───────────────┘
                                   ▼
                             write_ledger (D21, D23)
                                   ▼
                             summary line → stderr, exit 0
```

Ledger order is fixed by `sort_rows` and never changes afterwards, so "ledger
order" in D7 means the sorted order.

All input-side file-level checks (D13: every input file, the rules file, and
the same-file check of D20) happen before anything is written. The ledger is
then written atomically (D23), so no exit-2 case creates a partial `--out` or
changes an existing one. `--out` can never be one
of the inputs (D20), so writing it never changes an input.

### Row record

Every parsed row becomes one immutable record:

| Field | Type | Meaning |
|-------|------|---------|
| `account` | `str` | NAME from `--account` |
| `date` | `datetime.date` | ledger date (D5) |
| `description` | `str` | original text, outer whitespace trimmed |
| `amount` | `Decimal` | signed, outflow negative, 2 decimal places (D15) |
| `arg_index` | `int` | 0-based position of the `--account` argument the row came from |
| `line_no` | `int` | 1-based physical line number where the row ends (`csv.reader.line_num`; header is line 1 when it is the first line) |

The **same-transaction key** (D1) is `(account, date, amount, normalise(description))`.

### Reading an export

Files are opened as in D16. The first non-blank row is the header and selects
Format A or B (D13 for failures). Each later non-blank row must have as many
cells as the header; it is then parsed per D5, D14, D15 and D18. A row that
fails any check is skipped with a warning (see Messages). Dates are parsed with
`datetime.strptime` using the formats of the Fixed formats table, which gives
the D14 date behaviour directly. A `csv.Error` raised while reading a file
(for example a quoted field longer than the `csv` module's field size limit) is a file-level error with the "cannot read" message.

### Deduplication

Within each account (rows grouped by NAME; D4):

1. For each export (`arg_index`), count how many rows have each key.
2. `target[key]` = the largest of those counts (D2).
3. Walk the account's rows ordered by `(arg_index, line_no)` and keep a row only
   while fewer than `target[key]` rows with that key have been kept.
4. Give every kept row the description of its key's first occurrence in that
   same order (D3).

Worked example: export 1 has key K twice, export 2 has K three times. Target is
3. Both rows from export 1 are kept, then the first K row of export 2; the
other two K rows of export 2 are dropped. All three kept rows carry the text
of export 1's first K row.

### Sorting

Sort by D12: `(date, account, arg_index, line_no)`. Every row has a unique
`(arg_index, line_no)`, so the order is total.

### Transfer pairing

1. Build an index from amount to the ledger positions of inflows (amount > 0)
   with that amount, in ledger order. Zero-amount rows are never indexed or
   looked up (D17).
2. Walk the ledger in order. For each outflow (amount < 0), look up inflows
   with amount `-amount`. Keep those that are unpaired, in a different account,
   and within 3 days (D6). If any remain, choose the one with the smallest
   `(absolute day gap, ledger position)` (D7).
3. Give both rows the next id (D9) and mark them paired.

Worked examples (accounts `cur` and `card`, all amounts 50.00, dates in March
unless shown):

| Ledger (in order) | Result | Why |
|---|---|---|
| cur 03-01 −50; card 03-04 +50 | pair | gap 3 |
| cur 03-01 −50; card 03-05 +50 | no pair | gap 4 |
| card 02-27 +50; cur 03-01 −50 | pair | inflow may come first (gap 2) |
| cur 03-01 −50; card 03-02 +50; card 03-02 +50 | first card row pairs | equal gaps, earlier ledger position wins |
| cur 03-01 −50; cur 03-03 −50; card 03-03 +50 | first cur row pairs, second stays unpaired | greedy: earlier outflow takes the only inflow even though the second outflow is closer. Expected, not a bug. |
| cur 03-01 −50; cur 03-02 +50 | no pair | same account |

### Categorisation

Transfer rows get `Transfer` (D8). Every other row gets the category of the
first matching rule, else `Uncategorised` (D10).

### Writing

Each output row is `date` in ISO form, account, description, amount with
exactly 2 decimals (`-0.00` never appears; D17), category, and `transfer_id` or
empty. Encoding, line endings and quoting follow D21; write failures follow
D23.

### Messages and exit codes

This section lists every message text in full. Other sections may quote a
`REASON` or a message in passing to say which message applies; if any such
quote differs from this section, this section's wording is the one to
implement. When a message is printed and with which exit code is defined by the
Decisions table.

| Situation | stderr text | Exit |
|-----------|-------------|------|
| Success | `txmerge: R rows read, S skipped, D duplicates removed, T transfers linked, W rows written` | 0 |
| Skipped data row | `txmerge: warning: PATH:LINE: REASON; row skipped` | 0 (run continues) |
| Skipped rule row | `txmerge: warning: PATH:LINE: REASON; rule skipped` | 0 (run continues) |
| File-level error | `txmerge: error: MESSAGE` | 2 |
| Bad command line | argparse usage message ending in `error: ...`; for a bad `--account` (D24) the error text is `--account must be NAME=PATH, got 'VALUE'` | 2 |

`PATH` is the path of the file concerned and `OUT` the `--out` path, both exactly as given on the command line after the trimming in D24. `VALUE` is the `--account` value as typed. `REASON` is one of:
`expected N cells, got M`; `bad date 'X'`; `bad amount 'X'`;
`Debit and Credit both blank`; `Debit and Credit both filled`;
`blank pattern`; `blank category`.

File-level `MESSAGE` is one of: `cannot read PATH: <OS, decode or CSV error>`;
`PATH: file is empty`; `PATH: unrecognised header: <header cells joined by ,>`;
`PATH: header must be pattern,category` (rules file); `cannot write PATH: <OS
error>` (`--out`); `OUT: --out is also an input` (D20). An empty rules file gets `PATH: file is
empty`; a header-only rules file is valid and gives zero rules (every row is
`Uncategorised` or `Transfer`).

Counts: `R` = non-blank data rows in all exports (parsed plus skipped); `S` =
skipped data rows; `D` = rows removed by deduplication; `T` = number of pairs;
`W` = rows written = `R − S − D`. Each reader returns its parsed rows and its
skipped count; `cli.main` computes `R`, `D` and `W` from list lengths before
and after each stage, and `T` as the number of distinct non-empty ids returned
by `pair_transfers`. Skipped rule rows are warned about but not counted in the
summary.

### Scale

No performance target. Expected input is under 50,000 data rows in total
(several years of personal exports). Everything is held in memory. Dedup is
linear; pairing is linear in rows times the number of inflows sharing one
amount. No performance work is planned.

## Alternatives Considered

### Alternative A: Deduplicate by summing, or by keeping one row per key

*   **Pros**: One line of code (`set()` or `Counter` sum).
*   **Cons**: Summing counts every overlap twice. One row per key drops the
    second of two identical real purchases in one export.
*   **Reason for Rejection**: Breaks G1 or G2. Of the three, the max-count rule
    (D2) is the only one that keeps repeats inside one export and removes
    overlap copies; its remaining gap is R4.

### Alternative B: Deduplicate across accounts that point at the same file

*   **Pros**: Protects against the person passing one file under two names.
*   **Cons**: Contradicts the stakeholder's rule that different names are
    different accounts.
*   **Reason for Rejection**: Stakeholder decision (D4).

### Alternative C: Fuzzy description matching

*   **Pros**: Would catch the same transaction with truncated or reworded text.
*   **Cons**: Can merge two real, different transactions; behaviour is hard to
    predict; needs thresholds.
*   **Reason for Rejection**: Stakeholder ruled it out (round 1, answer 1);
    `BRIEF.md` goal 1 ("never lose a real transaction") outweighs catching
    reworded copies.

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
*   **Cons**: One long file mixes reading, matching and output, so it is
    harder to see where each rule lives.
*   **Reason for Rejection**: One module per concern (reading, dedup,
    transfers, rules, output, command line) keeps each file short and makes it
    obvious where each rule lives. This is a readability choice, not a
    testability one; the cost is a few imports.

### Alternative J: Write `--out` directly (no temporary file)

*   **Pros**: No temporary file; the ledger keeps whatever mode and link it
    had without extra steps.
*   **Cons**: Opening `--out` truncates the old ledger, so a failure part-way
    (disk full, killed process) leaves a damaged or empty ledger, and
    deleting it on failure destroys the person's previous ledger.
*   **Reason for Rejection**: The person's existing ledger may be the only
    copy of past results they compare against (`BRIEF.md` goal 4, re-runs).
    A failed run should not destroy it. The temporary-file-and-rename write
    (D23) costs one extra file and one `copymode` call.

--------------------------------------------------------------------------------

## Non-Functional Requirements

*   **Security & Privacy**: Bank data stays on the local disk; no network
    access. The tool reads only the files named on the command line and writes
    only `--out` and, briefly, its temporary file in the same directory (D23).
*   **Performance**: see Technical Plan › Scale.
*   **Rollout & Rollback**: None needed; the ledger is rebuilt every run (D20).

## Risks & Mitigations

| # | Risk | Impact | Mitigation or acceptance |
|---|------|--------|--------------------------|
| R1 | Greedy pairing is not optimal: an earlier outflow can take an inflow a later outflow needed (worked examples). | One real transfer is shown as spending and income. | Specified by the stakeholder (round 1, answer 5); no reason was given. Both rows stay visible in the ledger. |
| R2 | False transfers: a card refund, or rows of one file given under two names, pair with an unrelated equal amount within 3 days. | A refund is labelled `Transfer` instead of by rules. | Accepted by the stakeholder (round 2, answer 6) for refunds; by the designer (D4) for two names. Future improvement: description hint. |
| R3 | Card dates: a card payment's Transaction Date can be more than 3 days after the current-account debit. | Payment shown as spending and income. | Accepted: follows from the stakeholder's 3-day rule (D6). The person can add a rule to label such rows. |
| R4 | Max-count dedup can drop a real transaction. Example: export 1 covers 1–10 March and export 2 covers 10–20 March, each cut part-way through 10 March. A £3.50 coffee at 09:00 is only in export 1 and another £3.50 coffee at 16:00 (same description) only in export 2. Each export has the key once, so the ledger keeps it once. | One real transaction missing. | Accepted: a direct consequence of the stakeholder's max-not-sum rule (D2, round 1 answer 2). Exports carry no time of day, so no rule on these files can tell this apart from an overlap copy. |
| R5 | Rows skipped as malformed, including every row of a bank that writes amounts of 1,000 or more with an unquoted thousands separator (D15). | Rows missing from the ledger. | Every skipped row gets a warning naming file and line, and the summary shows the skipped count `S`. `0.00` in the unused Debit/Credit column counts as blank (D14), so banks that write it do not lose every row. Such rows are not repaired (stakeholder ruling); the warnings make the cause visible, and the person can re-export or quote the file. |
| R6 | Non-UTF-8 export (for example cp1252). | Run stops. | Exit 2 naming the file (D13) instead of guessing an encoding; the person re-saves the file as UTF-8. |
| R7 | Write failure (disk full, permission denied). | No new ledger. | Atomic write (D23): the old ledger, if any, is left exactly as it was. |
| R8 | Spreadsheet formula injection: a description starting with `=` opens as a formula in a spreadsheet. | Unexpected formula when the ledger is opened in a spreadsheet. | Accepted: the ledger is the person's own bank data, and the output must match the input text (D3). |

## Future Improvements

*   Optional check of Format A running balances to spot missing rows.
*   Optional description hint to stop card refunds pairing as transfers.

--------------------------------------------------------------------------------

## Detailed Implementation Plan

All paths are relative to the repository root. Behaviour is defined by the
Decisions table (D-numbers), the Technical Plan algorithms, and the Messages
table; this plan says which file implements which rule, with public
signatures. Work is in four phases; each phase ends with `python -m pytest`
passing.

### Phase 1 – Parsing

#### 1. `txmerge/__init__.py` (Create)

*   **Type / Scope**: Package marker.
*   **Proposed Changes**: Module docstring only.

#### 2. `txmerge/model.py` (Create)

*   **Type / Scope**: Shared types and helpers.
*   **Proposed Changes**:
    *   `class TxmergeError(Exception)`: any file-level failure (D13),
        including failure to write `--out`. The message is the `MESSAGE` text
        from the Messages table. Caught only in `cli.main`.
    *   `@dataclass(frozen=True) class Row` with the fields of the Row record.
    *   `normalise(description: str) -> str` (D1).
    *   `row_key(row: Row) -> tuple` (D1).
    *   `warn(path: str, line: int, reason: str, what: str = "row") -> None`:
        prints the "Skipped data row" / "Skipped rule row" text from the
        Messages table to `sys.stderr` (`what` is `"row"` or `"rule"`). The only
        place warnings are formatted.

#### 3. `txmerge/readers.py` (Create)

*   **Type / Scope**: Export parsing (D5, D13–D19).
*   **Proposed Changes**:
    *   `FORMAT_A` and `FORMAT_B` header **lists** of strings (from
        `BRIEF.md`); the trimmed header is built as a list, so `==` compares
        list with list.
    *   `parse_date(text: str, fmt: str) -> datetime.date`: returns
        `datetime.strptime(text.strip(), fmt).date()` (note `.date()`, so the
        ledger writes `2026-03-05`, not a datetime); `ValueError` propagates.
        Formats: `"%d/%m/%Y"` (A), `"%Y-%m-%d"` (B).
    *   `read_csv(path: str) -> list[tuple[int, list[str]]]`: shared by
        `read_export` and `rules.load_rules`. Opens with
        `open(path, encoding="utf-8-sig", newline="")`, iterates
        `csv.reader(f)` and returns `(reader.line_num, cells)` for every row
        whose cells are not all blank after `strip()` (D16). Any `OSError`,
        `UnicodeDecodeError` or `csv.Error` becomes
        `TxmergeError(f"cannot read {path}: {exc}")`. An empty result becomes
        `TxmergeError(f"{path}: file is empty")`. Cells are returned untrimmed;
        callers trim.
    *   `parse_amount(text: str, signed: bool) -> Decimal`: implements D15;
        raises `ValueError` on anything D15 rejects. Never calls `Decimal()`
        on text that has not passed the D15 grammar check (so `NaN`, `1e3`
        and `1_000` are rejected). After the check: remove commas, build the
        `Decimal`, apply the sign, then `.quantize(Decimal("0.01"))`. This is
        the only place amounts are rounded, and since D15 allows at most 2
        decimals it never changes a value. The `Decimal`/`quantize` calls are
        wrapped in `try/except decimal.InvalidOperation` and re-raised as
        `ValueError`, so an amount too long for the default 28-digit context
        (e.g. 40 digits) is a skipped row with reason `bad amount`, never a
        crash. Data cells are `strip()`ped before
        any parsing (D16).
    *   `read_export(path: str, account: str, arg_index: int) -> tuple[list[Row], int]`:
        returns the parsed rows (input order) and the number of skipped rows.
        Uses `read_csv`; the first returned row is the header (cells trimmed,
        compared with `FORMAT_A` / `FORMAT_B`, else `TxmergeError` with the
        "unrecognised header" message). Each later row is checked in the D14
        order. Calls `model.warn` for every skipped row with a
        `REASON` from the Messages table. A header-only file returns
        `([], 0)`.

#### 4. `tests/test_readers.py` (Create)

*   **Type / Scope**: pytest unit tests; fixture files written to `tmp_path`;
    warnings checked with `capsys`.
*   **Proposed Changes**: one test per case:
    *   Format A debit → negative, credit → positive, `1,250.00` → `1250.00`,
        `05/03/2026` → 2026-03-05, unpadded `5/3/2026` → 2026-03-05.
    *   Format B `-12.50`, `+3` → `3.00`, `1,250.00` → `1250.00`;
        Transaction Date used, Posting Date ignored (garbage there is fine).
    *   Balance column ignored (garbage there is fine) (D18).
    *   BOM and spaces around header cells accepted (D16); lower-case header
        `date,description,debit,credit,balance` → `TxmergeError` (D16 is
        case-sensitive).
    *   `0.00` debit with `25.00` credit → `+25.00`; `0` and `0.00` in both →
        skipped (D14).
    *   Skipped with the exact warning text: both blank, both filled, `£5.00`,
        `(5.00)`, `1.234`, `1,25.00`, `NaN`, `1e3`, `31/02/2026`, wrong cell
        count. Warning contains the path and the physical line number.
    *   Blank lines skipped silently and not counted.
    *   `TxmergeError`: unknown header; header with an extra empty column;
        missing file; empty file; file with invalid UTF-8 bytes.
    *   Header-only file → `([], 0)`.
    *   A 40-digit amount (`1234567890123456789012345678901234567890.00`) →
        skipped with `bad amount`, no exception.
    *   Data cells with outer spaces (`" 05/03/2026 "`, `" 12.50 "`) parse
        normally (D16); `Row.date` is a `datetime.date`, not a `datetime`.
    *   Check order (D14): a row with a bad date *and* both Debit/Credit blank
        warns `bad date`; a row with a bad Debit and a blank Credit warns
        `bad amount`.
    *   Format B: bad Transaction Date → `bad date`; Amount `£5` → `bad
        amount`; wrong cell count → skipped.
    *   A file containing a quoted field longer than the `csv` field size
        limit → `TxmergeError` "cannot read".

### Phase 2 – Dedup and ordering

#### 5. `txmerge/dedup.py` (Create)

*   **Type / Scope**: Overlap removal (D1–D4).
*   **Proposed Changes**: `deduplicate(rows: list[Row]) -> list[Row]`
    implementing Technical Plan › Deduplication (steps 1–4). Uses lists and
    insertion-ordered dicts only, never iteration over a `set`, so the result
    does not depend on hash randomisation. Output order is unspecified (the
    caller sorts).

#### 6. `txmerge/ledger.py` (Create)

*   **Type / Scope**: Ordering and output (D12, D17, D21, D23).
*   **Proposed Changes**:
    *   `sort_rows(rows: list[Row]) -> list[Row]` (D12).
    *   `HEADER` = the output header from `BRIEF.md`.
    *   `format_amount(amount: Decimal) -> str` (D17, D21): if
        `amount == 0` return `"0.00"` (this covers `Decimal("-0.00")`);
        otherwise return `format(amount, ".2f")`.
    *   `write_ledger(path: str, rows: list[Row], categories: list[str], transfer_ids: list[str]) -> None`:
        the three lists are aligned by position. Implements D21 and D23 in
        this exact order:
        1. `tmp = None`.
        2. `try:`
           * `fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(path)), prefix=".txmerge-", suffix=".tmp")`
           * `with open(fd, "w", encoding="utf-8", newline="") as f:` write
             `HEADER` and every row through
             `csv.writer(f, lineterminator="\n")`. The `with` block closes
             the file before step 3.
           * if `os.path.exists(path)`: `shutil.copymode(path, tmp)`.
           * `os.replace(tmp, path)`; then `tmp = None`.
        3. `except OSError as exc: raise TxmergeError(f"cannot write {path}: {exc}")`.
        4. `finally: if tmp is not None and os.path.exists(tmp): os.remove(tmp)`.

#### 7. `tests/test_dedup.py` (Create)

*   **Type / Scope**: Unit tests on `Row` lists built in code.
*   **Proposed Changes**: overlap of two exports → one copy; two identical
    rows in one export → both kept; export 1 has K ×2, export 2 has K ×3 → three
    kept, all with export 1's text (D3); same PATH twice → count unchanged
    (D4); same rows under two names → both kept (D4); case/whitespace-only
    differences → one copy; truncated text, different date or amount → both
    kept; one account with Format A and Format B rows sharing a key → one copy
    (D19).

#### 8. `tests/test_ledger.py` (Create)

*   **Type / Scope**: Unit tests.
*   **Proposed Changes**: tie-break order on equal date and account (D12);
    `format_amount(Decimal("-0.00")) == "0.00"`; written bytes start with the
    exact header, use `\n` only, have no BOM, end with `\n`, and quote a
    description containing a comma (D21); a write into a missing directory
    raises `TxmergeError` (D23); a new ledger has mode `0o600`
    (`stat.S_IMODE(os.stat(path).st_mode)`); overwriting an existing ledger
    whose mode was set to `0o644` keeps `0o644` (D23).

### Phase 3 – Transfers and rules

#### 9. `txmerge/transfers.py` (Create)

*   **Type / Scope**: Transfer pairing (D6–D9, D17).
*   **Proposed Changes**: `transfer_id(n: int) -> str` returns
    `f"T{n:04d}"` (D9). `pair_transfers(rows: list[Row]) -> list[str]`:
    input is the sorted ledger; returns the `transfer_id` for each position
    (empty string if unpaired). Algorithm: Technical Plan › Transfer pairing.

#### 10. `txmerge/rules.py` (Create)

*   **Type / Scope**: Rules (D10, D11).
*   **Proposed Changes**:
    *   `load_rules(path: str) -> list[tuple[str, str]]`: uses
        `readers.read_csv`; header (cells trimmed) must equal
        `["pattern", "category"]`, else `TxmergeError` with the "header must
        be pattern,category" message; checks each later row in this order and
        warns (`model.warn(path, line, reason, what="rule")`) and skips on the
        first failure: (1) cell count is not 2 → `expected 2 cells, got M`;
        (2) trimmed pattern empty → `blank pattern`; (3) trimmed category
        empty → `blank category`. Returns `(folded pattern, category)`
        in file order.
    *   `categorise(description: str, rules: list[tuple[str, str]]) -> str` (D10).

#### 11. `tests/test_transfers.py` (Create)

*   **Type / Scope**: Unit tests.
*   **Proposed Changes**: every row of the worked-examples table in the
    Technical Plan as its own test; plus: one inflow cannot serve two outflows;
    `-500.00` vs `+499.99` → no pair; zero amounts never pair; ids `T0001`,
    `T0002` in pairing order; `transfer_id(1) == "T0001"` and
    `transfer_id(10000) == "T10000"` (D9).

#### 12. `tests/test_rules.py` (Create)

*   **Type / Scope**: Unit tests.
*   **Proposed Changes**: case-insensitive substring; first rule wins;
    no match → `Uncategorised`; `.` and `*` are literal; pattern `costa coffee`
    does **not** match `COSTA  COFFEE` (D10); blank pattern / blank category /
    wrong cell count → rule skipped with warning; bad header → `TxmergeError`;
    a row `,` (all cells blank) is skipped silently with no warning (D16);
    a row ` ,Food` warns `blank pattern`; a row `TESCO, ` warns
    `blank category`; a 3-cell row with a blank
    pattern warns `expected 2 cells, got 3`; category `Transfer` allowed; header-only rules file → zero rules, every
    non-transfer row `Uncategorised`.

### Phase 4 – Command line

#### 13. `txmerge/cli.py` (Create)

*   **Type / Scope**: Argument parsing and orchestration.
*   **Proposed Changes**:
    *   `build_parser() -> argparse.ArgumentParser`:
        `argparse.ArgumentParser(prog="txmerge")`;
        `sub = parser.add_subparsers(dest="command", required=True)`
        (the `dest` is required so a missing sub-command exits 2 instead of
        raising `TypeError`); `m = sub.add_parser("merge")`;
        `m.add_argument("--account", action="append", required=True, type=parse_account)`;
        `m.add_argument("--rules", required=True)`;
        `m.add_argument("--out", required=True)`.
    *   `parse_account(value: str) -> tuple[str, str]`: used as the
        argparse `type=` for `--account`. Implements D24 and returns the
        trimmed `(NAME, PATH)`; on a bad value raises
        `argparse.ArgumentTypeError` with the D24 message, which argparse turns
        into a usage error (exit 2, D13).
    *   `main(argv: list[str] | None = None) -> int` runs these steps in
        order:
        1. `args = build_parser().parse_args(argv)`. Usage errors raise
           `SystemExit(2)`; `main` does not catch it (tests: see item 15).
        2. Inside `try:` steps 3-9; `except TxmergeError as e:` print
           `f"txmerge: error: {e}"` to stderr and return 2.
        3. `rules = load_rules(args.rules)`.
        4. For each `(i, (name, path))` in `enumerate(args.account)`:
           `read_export(path, name, i)`; collect rows and add up skipped
           counts.
        5. Same-file check (D20): if `os.path.exists(args.out)`, for each
           input path and the rules path `X`, call
           `os.path.samefile(args.out, X)`; an `OSError` becomes
           `TxmergeError(f"cannot read {X}: {exc}")`, a `True` result becomes
           `TxmergeError(f"{args.out}: --out is also an input")`.
        6. `kept = deduplicate(rows)`; `ledger = sort_rows(kept)`.
        7. `ids = pair_transfers(ledger)`.
        8. Categories (D8, owned here): `"Transfer"` where `ids[k]` is
           non-empty, else `categorise(ledger[k].description, rules)`.
        9. `write_ledger(args.out, ledger, categories, ids)`.
        10. Print the summary line (Messages section) to stderr; return 0.

#### 14. `txmerge/__main__.py` (Create)

*   **Type / Scope**: Entry point for `python -m txmerge`.
*   **Proposed Changes**: calls `cli.main()` and exits with its return value.

#### 15. `tests/test_cli.py` (Create)

*   **Type / Scope**: End-to-end tests calling `cli.main([...])`, and once
    `subprocess.run([sys.executable, "-m", "txmerge", "merge", ...])`.
*   **Proposed Changes**: one test per bullet. "Exit 2 (usage)" means
    `SystemExit` with code 2 (see `main`); "exit 2" means `main` returns 2.
    *   CUJ 1–5, one test each.
    *   Exact expected bytes for a small fixed scenario covering ordering,
        amounts, categories, transfer ids and blank `transfer_id`.
    *   Running twice gives identical bytes (G5).
    *   Summary on stderr, stdout empty (D22).
    *   Two names pointing at one file can pair that file's own rows (D4).
    *   A Format B row with Amount `0.00` and description matching a rule is
        written with amount `0.00`, that rule's category and blank
        `transfer_id`, and a same-day `-0.00`/`0.00` pair in another account
        does not pair (D17).
    *   Existing `--out` is overwritten on success (D20).
    *   `--out` equal to an input path, or to the rules path → exit 2, input
        unchanged (D20).
    *   `os.path.samefile` raising `OSError` (monkeypatch
        `txmerge.cli.os.path.samefile`) → exit 2 with the "cannot read"
        message (D20).
    *   Missing rules file, empty rules file, rules file with a wrong header
        → exit 2 and `--out` not created (D13).
    *   Missing `--rules`, missing `--out`, no `--account`, no `merge`
        sub-command → exit 2 (usage) (D13).
    *   Failing write (monkeypatch `txmerge.ledger.os.replace` to raise
        `OSError`), once with no existing `--out` and once with an existing
        ledger → exit 2; `--out` absent in the first case, byte-identical to
        the old ledger in the second; no `.txmerge-*.tmp` left (D23).
    *   `--account` values `noequals`, `=path`, `name=` → exit 2 (usage) and
        stderr contains `--account must be NAME=PATH, got` (D24).
    *   `parse_account("a=b=c") == ("a", "b=c")` and
        `parse_account(" cur = x.csv ") == ("cur", "x.csv")` (D24).

#### 16. `README.md` (Create)

*   **Type / Scope**: User documentation.
*   **Proposed Changes**: one usage example, exit codes, and a link to
    `docs/designs/txmerge.md` for the rules. Does not copy the rules.

### Verification Plan

*   **Build**: none (pure Python).
*   **Tests**: `python -m pytest` from the repository root passes with zero
    failures.
*   **Static Analysis**: none required.
*   **Coverage**: every rule is exercised by the tests listed above:

    | Rules | Test file |
    |-------|-----------|
    | D1–D4, D19 | `tests/test_dedup.py` (D4 self-pairing also in `test_cli.py`) |
    | D5, D13 (input files), D14, D15, D16 (header and data-cell trimming), D18 | `tests/test_readers.py` |
    | D6, D7, D9, D17 (pairing) | `tests/test_transfers.py` |
    | D8, D13 (rules file, command line, same-file), D17 (zero row end to end), D20, D22, D23 (failing write), D24 | `tests/test_cli.py` |
    | D10, D11 | `tests/test_rules.py` |
    | D12, D17 (formatting), D21, D23 (missing directory, file mode) | `tests/test_ledger.py` |
*   **E2E**: `tests/test_cli.py` runs `python -m txmerge` once via
    `subprocess`.

--------------------------------------------------------------------------------

*Drafted with the [redacted]-[redacted] Model ([redacted]) design workflow.*
