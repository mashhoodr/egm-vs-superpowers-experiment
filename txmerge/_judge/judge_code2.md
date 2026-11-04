# Blind code judgement 2: txmerge X / Y / Z

Inputs read: `BRIEF.md` and `_judge/blind2/{X,Y,Z}` only. Not counted as defects (stakeholder rulings):
greedy transfer pairing, and skipping a malformed row with a warning while still exiting 0.

Test runs: X 100 passed, Y 88 passed, Z 19 passed.

## Score table

| | Correctness risk | Clarity | Test quality | Proportionality | Total |
|---|---|---|---|---|---|
| X | 3 | 4 | 4 | 4 | 15 |
| Y | 4 | 5 | 5 | 4 | 18 |
| Z | 2 | 3 | 2 | 5 | 12 |

**Ranking: Y > X > Z**

## Probes run (temp dir, all three implementations)

| Probe | X | Y | Z |
|---|---|---|---|
| Unclosed quote on line 2, then 2 valid rows | 0 rows written; one warning ("expected 5 cells, got 2" at line 4); summary says "1 rows read" | the bad line is skipped, both valid rows kept | 0 rows written; one warning; the 2 valid rows are lost |
| Valid quoted description with an embedded newline | kept | **row lost** (2 warnings) | kept |
| Format A `Debit=0.00, Credit=25.00` | kept, +25.00 | kept, +25.00 | **skipped** ("both filled") |
| Amount `12.345` | skipped with a warning | kept, unrounded internally, printed -12.35 | rounded at parse to -12.35 |
| Amount `1e3` | skipped | skipped | **accepted** as -1000.00 |
| Amount `"1,2,3"` | skipped | accepted as -123.00 | accepted as -123.00 |
| Amount `1e999999` | skipped | skipped | **traceback, exit 1, no ledger** |
| Debit `-5.00` | skipped | skipped | taken as -5.00 (sign forced by `abs`) |
| Duplicates within one export (2x) and across exports (3x vs 1x) | kept max per export (2 Coffee, 3 Lunch) | same | same |
| Card `100.004` vs current-account debit `100.00` | card row skipped (3dp) | both print `100.00` but are **not paired** | paired |

All three handle dedup the same way. Each keeps every key as many times as its highest count in any single export, scoped by account, so no real repeated transaction within one export is lost. All three are deterministic for identical inputs and argument order.

## X

**Correctness risk: 3**
- `X/txmerge/readers.py:48-54` reads the whole file with a non-strict `csv.reader`. An unclosed quote makes the reader swallow every later line into one field. Those rows disappear behind a single misleading warning ("expected 5 cells, got 2", reported at the last line). The summary at `X/txmerge/cli.py:69` then reports "1 rows read", which hides the loss. That breaks "never lose a real transaction" without a clear signal.
- Its money grammar is the strictest of the three. `X/txmerge/readers.py:18-42` uses a regex with real thousands-grouping, at most 2 decimals, and no exponent. Unsigned Debit/Credit values are quantized at parse time. Every rejected value is warned, never silently changed.
- Good safety extras: `--out` cannot be one of the inputs (`X/txmerge/cli.py:48-55`), writes are atomic (`X/txmerge/ledger.py:26-56`), and a 0.00 in the unused column is accepted (`X/txmerge/readers.py:79-80`).

**Clarity: 4**
- The module split (`readers`, `dedup`, `transfers`, `rules`, `ledger`, `cli`) is clean, and dedup is short and commented step by step (`X/txmerge/dedup.py:10-34`).
- Docstrings cite design IDs ("D1", "D13-D19", e.g. `X/txmerge/model.py:1`, `X/txmerge/readers.py:1`). Without the design doc those IDs mean nothing to a maintainer.
- `X/txmerge/readers.py:102`: `_RowError` is defined after the functions that use it. This is harmless but reads awkwardly.

**Test quality: 4**
- Broad coverage: a byte-exact end-to-end golden (`X/tests/test_cli.py:77`), max-not-sum dedup and first-text (`X/tests/test_dedup.py:25`), the same path passed twice (`X/tests/test_dedup.py:39`), the zero-column cases (`X/tests/test_readers.py:80-82`), and -0.00 formatting.
- It even tests an oversized quoted field (`X/tests/test_readers.py:196`). It does **not** test an unclosed quote followed by valid rows, which is the one case it gets wrong.

**Proportionality: 4**
- About 420 source lines over 7 modules. That is slightly heavy for the problem, but every piece earns its place. The rows-read/skipped summary line is a useful extra.

**Most serious defect:** an unclosed quote silently eats the rest of the export (`X/txmerge/readers.py:50`). Only one row's warning is printed, and the summary undercounts the rows read.

## Y

**Correctness risk: 4**
- It is the only implementation that survives an unclosed quote. Each physical line is parsed with `strict=True` (`Y/txmerge/readers.py:92-115`), so the bad line is skipped with a warning and the later rows are kept. The trade-off is that a *legitimate* quoted description with an embedded newline also gets split and dropped (two warnings). The loss is loud, but it is still a real transaction lost. Bank exports rarely contain these.
- Amounts are not quantized when parsed (`Y/txmerge/readers.py:21-31`). Rounding happens only in the writer (`Y/txmerge/writer.py:14-18`). So `100.004` and `100.00` print identically, yet they neither pair as a transfer (`Y/txmerge/transfers.py:22,29`) nor dedupe (`Y/txmerge/dedupe.py:14`). A reader sees two equal amounts that the tool treats as different.
- `Y/txmerge/readers.py:22` strips every comma before the grammar check, so `"1,2,3"` becomes 123.00 without a warning. Rules rows that are malformed or blank are dropped without a warning (`Y/txmerge/categorise.py:19-20`).

**Clarity: 5**
- Each module is small and does one job. `Transaction` and `LedgerEntry` are frozen dataclasses (`Y/txmerge/model.py`). The pipeline order is stated explicitly (`Y/txmerge/cli.py:21`), and the comments explain intent (`Y/txmerge/readers.py:62,92`; `Y/txmerge/dedupe.py:13`).
- The writer formats everything first, then swaps the file in atomically and keeps normal file permissions (`Y/txmerge/writer.py:21-44`).

**Test quality: 5**
- It explicitly tests the unclosed-quote recovery (`Y/tests/test_readers.py:135`), the full zero-column matrix (`Y/tests/test_readers.py:203-231`), max-not-sum dedup and the same file passed twice (`Y/tests/test_dedupe.py:21,28`), and amount formatting edge cases (`Y/tests/test_writer.py:15-18`).
- Gap: no test for a valid multi-line quoted field, which would have exposed the trade-off above. No test for sub-cent amounts reaching dedup or pairing.

**Proportionality: 4**
- About 370 source lines over 7 modules. The size is right. The split into `transfers.py` (which also owns ordering) and `writer.py` is reasonable.

**Most serious defect:** amounts are not quantized when parsed (`Y/txmerge/readers.py:21-31`). Values that print the same can fail to dedupe or pair, and `"1,2,3"` is silently accepted. Close second: valid multi-line quoted descriptions are dropped (`Y/txmerge/readers.py:110-115`).

## Z

**Correctness risk: 2**
- An unclosed quote behaves as in X (`Z/txmerge/core.py:120`, non-strict `csv.reader`). Every following row is swallowed behind a single warning.
- `Z/txmerge/core.py:89-93` treats any non-blank cell as "filled". A common bank pattern such as `Debit=0.00, Credit=25.00` is therefore skipped as "both filled", which drops real income or spending.
- `Z/txmerge/core.py:65-74` passes raw text to `Decimal()`, so `1e3` is accepted as 1000.00. `1e999999` raises an uncaught `decimal.InvalidOperation` when quantized. `Z/txmerge/cli.py:57-62` catches only `InputError` and `OSError`, so one bad cell crashes the whole run with a traceback and exit 1. `abs()` at `Z/txmerge/core.py:95-97` silently corrects a mis-signed Debit or Credit instead of flagging it.

**Clarity: 3**
- A single 240-line `core.py` holds parsing, rules, dedup, pairing and categorisation. It reads fine today but is the hardest of the three to change in isolation.
- `Txn` is a mutable dataclass whose `category` and `transfer_id` are set in place by `link_transfers` and `categorise` (`Z/txmerge/core.py:30-39,217-226`). The data flow is implicit.
- `Txn.sort_key` (`Z/txmerge/core.py:44-45`) orders by `line_no` before `arg_index`. Rows from different exports interleave by line number, which is deterministic but surprising.

**Test quality: 2**
- 19 tests. Dedup is covered: max-not-sum, whitespace and case normalisation (`Z/tests/test_txmerge.py:95-124`). Greedy pairing and its tie-break are covered (`Z/tests/test_txmerge.py:157-166`), and there is a determinism check (`Z/tests/test_txmerge.py:184`).
- There are no malformed-CSV tests (no unclosed quote, no wrong cell count beyond one case), no zero-column tests, and no amount-grammar or overflow tests. The defects above are exactly in those untested areas.

**Proportionality: 5**
- About 300 lines in two files is the leanest fit for a single-command tool, with no needless abstraction.

**Most serious defect:** real transactions are lost silently or the run crashes on ordinary-looking inputs. Specifically, `0.00` in the unused Format A column drops the row (`Z/txmerge/core.py:89-91`), and the unclosed-quote swallow and the `1e999999` traceback are on top of that.

## Overall

1. **Y**: the only implementation that keeps valid rows after a broken quote, with the cleanest structure and tests aimed at the risky paths. Its weaknesses are sub-cent precision handling and multi-line quoted fields.
2. **X**: the most rigorous money parsing and the best safety extras. One serious blind spot: the unclosed quote silently loses rows.
3. **Z**: compact, but it has the most ways to lose or misread money and the thinnest tests.
