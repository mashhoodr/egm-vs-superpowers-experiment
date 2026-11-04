# Blind code verdict: txmerge X / Y / Z

All three test suites pass (X 105, Y 88, Z 19). All three use the same core design: dedupe by `(account, date, amount, normalised description)` keeping the **max count seen in any one export** (so repeated same-day purchases inside one export survive), then sort, greedily pair outflows with equal-and-opposite inflows in another account within ±3 days (nearest date, then earliest row), then categorise by first-match case-insensitive substring. So the differences are in how they parse input, how they handle errors, and how well they test.

## Scores

| | Correctness risk | Clarity | Test quality | Proportionality | Total |
|---|---|---|---|---|---|
| X | 4 | 4 | 5 | 3 | 16 |
| Y | 3 | 5 | 4 | 4 | 16 |
| Z | 2 | 3 | 2 | 4 | 11 |

**Ranking: X > Y > Z.** X and Y tie on points. X ranks first because it is the only one that never silently corrupts or drops rows on malformed CSV. That matters most against the brief's "never lose a real transaction".

## X

**Correctness 4**
- Strict CSV parsing with a fatal error on structural breakage (`csvio.py:17`, `csvio.py:34-35`). An unclosed quote aborts the whole run with exit 2 and writes nothing, so no rows are lost silently. Multiline quoted descriptions parse correctly (probe output was correct; `tests/test_parsing.py:160`).
- Strict amount grammar (`formats.py:22-24`). It rejects `1,2,3`, `.50`, `1e3`, `-5` in Debit, `1 000` and amounts with 3 decimals. Malformed values are warned about and skipped, never reinterpreted. A run summary reports how many rows were parsed, skipped, de-duplicated and linked (`cli.py:65-69`), so any loss is visible.
- Shared flaw: pairing is greedy (`transfers.py:15-35`). With outflows on 10/03 and 14/03 and inflows on 07/03 and 11/03, it links 10↔11 and leaves both 07 and 14 unlinked, although 10↔07 and 14↔11 are both within the window. Y and Z do the same. Pairing also ignores the description, so a coincidental equal refund in another account becomes a "Transfer". One bad quote also stops the whole run, which is strict but safe.

**Clarity 4**
- Each module does one job (`formats`, `dedup`, `transfers`, `rules`, `ledger`), and the `Format` table (`formats.py:84-94`) makes adding a third bank format easy.
- Stages mutate `Record` in place (`transfers.py:33-35`, `rules.py:36`), so the pipeline order is load-bearing but not stated.

**Tests 5**
- Covers the risky paths: max-count dedup (`tests/test_dedup.py:15-63`), the same path passed twice, Format A and Format B rows in one account, multiline rows, rejected amount formats (`tests/test_parsing.py:75,114`), the transfer window edges and tie-breaks (`tests/test_transfers.py:23-59`), an index-vs-full-scan equivalence check (`:87`), determinism (`tests/test_cli.py:90`), and the atomic write failing.
- Gap: no test for globally ambiguous pairing, like the case above.

**Proportionality 3**
- About 460 source lines across 9 modules. The extras go beyond the brief: an `--out`-is-an-input check (`ledger.py:49-60`), symlink handling, a summary line and a custom temp-file scheme. Each is defensible, but together they are more than needed.

**Most serious defect:** greedy transfer pairing can leave pairable transfers unlinked (`transfers.py:15-35`), so they count as spending. This flaw is shared. X has no data-loss defect of its own.

## Y

**Correctness 3**
- Reads one physical line at a time (`readers.py:92-115`). A legitimate quoted description that contains a newline is broken into fragments. The probe dropped the real transaction `"Tesco\nExpress",10.00` with two warnings. The test `tests/test_readers.py:135` treats this per-line design as a feature.
- Amount parsing removes every comma before validating (`readers.py:22`), so `1,2,3` becomes 123. It keeps more than 2 decimals: `10.005` is used unrounded for dedup and transfer matching, then written as `-10.01` (`writer.py:15`). The value matched is not the value written.
- Good: frozen dataclasses, negative Debit/Credit rejected (`readers.py:48-52`), exponents rejected, very large amounts give a clean exit 2 (`cli.py:55-58`), atomic write.

**Clarity 5**
- The cleanest of the three: an immutable `Transaction`/`LedgerEntry` (`model.py:11-24`), transfer ids returned as a list instead of mutated in (`transfers.py:17-40`), and the pipeline order stated in `cli.py:21`.

**Tests 4**
- Thorough on parsing, the zero-in-unused-column rules (`tests/test_readers.py:202-230`), max-count dedup, transfer tie-breaks and contention (`tests/test_transfers.py:54-83`), the credit-card payoff, and a byte-identical rerun.
- Gap: no multiline quoted-field test. The unclosed-quote test asserts the behaviour that causes the data loss.

**Proportionality 4**
- About 370 lines in 7 small modules, which suits the problem. Small extras such as the umask/chmod handling (`writer.py:35-37`).

**Most serious defect:** line-by-line CSV reading (`readers.py:93-115`) drops valid transactions whose quoted description spans more than one line. It does warn when this happens.

## Z

**Correctness 2**
- Non-strict `csv.reader` (`core.py:120`). One unclosed quote swallows the rest of the file into a single field. The probe had 4 transactions after a stray `"` and produced **zero** rows, with one warning (`expected 5 fields, got 2`) that does not say three more transactions went with it. This silently loses real transactions, the brief's top concern. A `csv.Error` (for example, a field over the size limit) is also uncaught and would end in a traceback (`cli.py:57`).
- Lenient amount parsing (`core.py:65-74`): it accepts `1,2,3`→123, `1e3`→1000 and `1 000`, and silently rounds `10.005`. `-abs()` on Debit/Credit (`core.py:95-97`) quietly turns a negative Debit into an outflow instead of flagging it.
- Line numbers in warnings are CSV record indices, not file lines (`core.py:140`), so they are wrong after multiline rows. A rule with a blank category gives the category `""` (`core.py:164-166`). The sort key `(date, account, line_no, arg_index)` (`core.py:45`) interleaves exports by line number. It is deterministic but odd.

**Clarity 3**
- One 240-line `core.py` that reads well top to bottom. However, parsing, dedup, pairing, rules and formatting share one file, and `read_export` defaults to printing (`core.py:117`).

**Tests 2**
- 19 tests that cover the happy paths, max-count dedup, the window, closest-then-first pairing and determinism (`tests/test_txmerge.py:75-205`).
- Nothing on malformed quoting, the amount grammar, negative Debit, multiline fields or a large-field `csv.Error`, which is exactly where the defects are.

**Proportionality 4**
- The smallest at about 300 lines, which fits the problem well. The cost of that size shows up in parsing safety, not in structure.

**Most serious defect:** an unclosed quote silently drops every transaction after it in that export (`core.py:120`, non-strict `csv.reader`), with only a single misleading warning.

## Shared observations
- Determinism: all three gave the same output on repeated runs and in the probes. Output order depends on `--account` argument order, which is acceptable for "same inputs".
- Cross-export duplicates: all three correctly keep two identical same-day coffees from one export when an overlapping export has one.
- All three link transfers greedily without looking at descriptions, and none reports ambiguous candidates to the user.
