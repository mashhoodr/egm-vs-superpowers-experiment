# Goldfish Review Report

**Target:** `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers/arms/egm2/docs/designs/txmerge.md` (`lines 467-766`, Detailed Implementation Plan)
**Stage:** 9 (Implementation Readiness Test), egm-review-loop round 3

## Reviewer Status

| Reviewer | Status | Raw findings |
| --- | --- | --- |
| `egm-implementation-readiness` | completed | 0 Blocker, 0 Major, 6 Nit |
| `egm-codebase-details` | completed | 0 Blocker, 0 Major, 11 Nit |
| `egm-style` | completed | 0 Blocker, 1 Major, 11 Nit (its summary line said 10 Nits, but it listed N1-N11) |

**Severity breakdown (raw, as each reviewer rated it):** 0 Blocker, 1 Major, 28 Nit.
**After deduplication:** 0 Blocker, 1 Major, 20 Nit entries. Merged entries list every source id. No severity has been changed.

Finding ids: `ir` = egm-implementation-readiness, `cd` = egm-codebase-details, `style` = egm-style. The number is the reviewer's own item order.

## Prioritized Findings (Blockers -> Major -> Nits)

### Blockers

None.

### Major

### The `cli.main` specification is one overloaded run-on bullet - Severity: Major
* **Ids:** `style-3-1`
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 683-697. Line 693 is unwrapped (about 170 characters). The test guidance is repeated at 708-709.
* **Discrepancy Description:** One sentence-chain covers six things: argument parsing, argparse exit behaviour, `pytest.raises(SystemExit)` test guidance, the whole stage order, the inline same-file check with two error messages, and D8 ownership plus error handling and the summary. The pipeline order is buried after a long parenthetical. The reader has to infer whether `try/except TxmergeError` starts before or after `parse_args`.
* **Rationale & Recommendation:** Rewrite as a numbered list:
  1. `parse_args` (not caught).
  2. `try:` load rules.
  3. Read exports.
  4. Same-file check (own sub-bullet with its two messages).
  5. Dedup.
  6. Sort.
  7. Pair.
  8. Categories (D8).
  9. Write.
  10. `except TxmergeError` → print the File-level error, return 2.
  11. Print the summary (cite lines 337-342), return 0.

  Keep the `pytest.raises` guidance in item 15 only. Wrap line 693.

### Nits

### The amount format (D15) is described in words, not as an exact pattern - Severity: Nit
* **Ids:** `ir-3-1`, `cd-3-4`
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 517-524 (D15 at line 128)
* **Discrepancy Description:** The implementer still has to write the pattern. These inputs are not settled:
  - `1234,567.00`
  - `.50`
  - `1.`
  - `,250.00`

  Python's `\d` (and `Decimal()`) also accepts non-ASCII digits such as `١٢.٥٠`.
* **Rationale & Recommendation:** State the exact check, with ASCII `[0-9]`, applied via `re.fullmatch` to the trimmed cell after removing an optional `[+-]` (only when `signed=True`). For example: `[0-9]{1,3}(,[0-9]{3})+(\.[0-9]{1,2})?|[0-9]+(\.[0-9]{1,2})?`.

### Very large amounts raise `decimal.InvalidOperation`, which is not a `ValueError` - Severity: Nit
* **Ids:** `cd-3-5`
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Lines 517-524
* **Discrepancy Description:** An amount with 27 or more integer digits passes the grammar, but `.quantize(Decimal("0.01"))` then exceeds the default context precision of 28 and raises `InvalidOperation`. That error is an `ArithmeticError`, so it escapes the row-skip logic and crashes with a traceback (exit 1), which breaks G6.
* **Rationale & Recommendation:** Catch `InvalidOperation` in `parse_amount` and re-raise it as `ValueError` (giving the `bad amount` warning). Add one test.

### Nobody owns data-cell stripping, and the values filled into messages are not pinned down - Severity: Nit
* **Ids:** `cd-3-2`, `style-3-4` (N3), `ir-3-4`
* **Reviewer Lens:** all three
* **Affected Scope:** Lines 504-506, 515-516, 517-532, 549-551, 556. Message text is at lines 323-331.
* **Discrepancy Description:** `read_csv` returns untrimmed cells ("callers trim"). `parse_date` strips. "Data cells are strip()ped before any parsing" (under `parse_amount`) is passive and names no owner. These points are also open:
  - whether `X` in `bad date 'X'` / `bad amount 'X'` is the trimmed or the raw cell;
  - whether the quotes are literal `'...'` or come from `!r`;
  - which cell supplies `X` when both Debit and Credit fail;
  - whether the "unrecognised header" message joins trimmed or raw cells;
  - how `VALUE` in `--account ... got 'VALUE'` is quoted (lines 680-681).
* **Rationale & Recommendation:** Say that `read_export` strips every cell once, before the D14 checks. `X` and the joined header cells are trimmed values formatted as `f"'{x}'"`. Debit is checked before Credit. `VALUE` is the raw argument in literal single quotes.

### The type of `ledger.HEADER` is not stated - Severity: Nit
* **Ids:** `ir-3-3`, `cd-3-6`
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Line 582
* **Discrepancy Description:** `FORMAT_A` and `FORMAT_B` are explicitly lists, but `HEADER` is not. If it is a string, `writer.writerow(HEADER)` writes one character per cell.
* **Rationale & Recommendation:** `HEADER = ["date", "account", "description", "amount", "category", "transfer_id"]`.

### The `samefile`-raises-`OSError` test needs `--out` to exist first - Severity: Nit
* **Ids:** `ir-3-5`, `cd-3-9`
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 723-725 (the check is at lines 689-693)
* **Discrepancy Description:** `samefile` is only called when `os.path.exists(out)`. If `--out` does not exist, the patched function is never reached, so the D20 `OSError` branch goes untested.
* **Rationale & Recommendation:** Add "with an existing `--out` file" to the test bullet.

### The subprocess end-to-end test does not say its working folder or which test it is - Severity: Nit
* **Ids:** `ir-3-6`, `cd-3-8`, `style-3-11` (N11)
* **Reviewer Lens:** all three
* **Affected Scope:** Lines 706-707, 711, 761-762
* **Discrepancy Description:** No packaging file exists, so `python -m txmerge` only imports when the repository root is on `sys.path`. With `cwd=tmp_path` it fails with `No module named txmerge`. The plan also does not say which test uses the subprocess, and "a small fixed scenario" is unspecified.
* **Rationale & Recommendation:**
  - Run with `cwd` = repository root (`Path(__file__).resolve().parents[1]`) and absolute fixture paths, or set `PYTHONPATH`.
  - Name the subprocess test (e.g. the CUJ 1 test).
  - List the scenario's minimum contents: two accounts, one transfer, one categorised row, one `Uncategorised` row, and one D12 equal-date tie.

### `read_csv` exception wrapping must cover iteration, not just `open()` - Severity: Nit
* **Ids:** `cd-3-1`
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Lines 508-516 (tests at 554, 563)
* **Discrepancy Description:** `UnicodeDecodeError` and `csv.Error` are raised during iteration. A `try` around `open()` alone gives a traceback instead of exit 2.
* **Rationale & Recommendation:** Say that the `try` encloses `open` and the full iteration, e.g. `rows = list(csv.reader(f))` inside the `with`.

### Fixtures containing `1,250.00` / `1,25.00` must be CSV-quoted - Severity: Nit
* **Ids:** `cd-3-3`
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Lines 539-541, 549-551
* **Discrepancy Description:** Unquoted, these values split into extra cells and trigger `expected N cells` instead of the intended path.
* **Rationale & Recommendation:** Specify quoted cells, or say that fixtures are written with `csv.writer`.

### The check order for rule rows is not given - Severity: Nit
* **Ids:** `ir-3-2`
* **Reviewer Lens:** `egm-implementation-readiness`
* **Affected Scope:** Lines 637-642 (D11 at line 124), tests at 657-662
* **Discrepancy Description:** A 3-cell row with a blank pattern could warn about either the cell count or the blank pattern. The tests check each failure on its own, so either order passes.
* **Rationale & Recommendation:** "Cell count, then blank pattern, then blank category. The first failure gives the REASON."

### The text refers to a `transfer_id` field on the row, but `Row` has no such field - Severity: Nit
* **Ids:** `cd-3-7`
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Lines 693-695 (Row at 489, record at 232-239)
* **Discrepancy Description:** The text says "`Transfer` where the row has a `transfer_id`", but the ids live in the parallel list returned by `pair_transfers`.
* **Rationale & Recommendation:** "`Transfer` where `transfer_ids[i]` is non-empty."

### The argparse `dest` rationale is out of date - Severity: Nit
* **Ids:** `cd-3-10`
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Lines 672-674 (the VALUE-quoting half is merged into the stripping entry above)
* **Discrepancy Description:** The `TypeError` for a required subparser without `dest` was a pre-3.9 bug. Setting `dest` is still correct, but the stated reason is stale.
* **Rationale & Recommendation:** Drop or soften the remark.

### The blank-line test is underspecified - Severity: Nit
* **Ids:** `style-3-9` (N8), `cd-3-11` (second half)
* **Reviewer Lens:** `egm-style`, `egm-codebase-details`
* **Affected Scope:** Line 552
* **Discrepancy Description:** "Not counted" has no object. The test also does not check D16's rule that blank lines still advance physical line numbers.
* **Rationale & Recommendation:** "Blank lines produce no warning and do not add to the skipped count. A warning after a blank line reports the correct physical line number (D16)." Assert that in the test.

### `datetime.strptime` / `datetime.date` naming is mixed - Severity: Nit
* **Ids:** `cd-3-11` (first half)
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Line 505
* **Rationale & Recommendation:** Say `datetime.datetime.strptime(...).date()`, or `from datetime import datetime`.

### Wrong step reference in the `write_ledger` steps - Severity: Nit
* **Ids:** `style-3-2` (N1)
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 594-595
* **Discrepancy Description:** "closes the file before step 3", but step 3 is the `except` clause. The file must close before `copymode` / `os.replace`, which are still inside step 2.
* **Rationale & Recommendation:** "The `with` block closes the file before `copymode` and `os.replace` below."

### Inconsistent list markers - Severity: Nit
* **Ids:** `style-3-3` (N2)
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 591-597
* **Rationale & Recommendation:** Use one marker style (`*   `) throughout.

### "Rounded" contradicts "never changes a value" - Severity: Nit
* **Ids:** `style-3-5` (N4)
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 521-523
* **Rationale & Recommendation:** "`.quantize(Decimal("0.01"))` only pads to two places. D15 input never needs rounding."

### Informal wording "(garbage there is fine)" - Severity: Nit
* **Ids:** `style-3-6` (N5)
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 542-543
* **Rationale & Recommendation:** "A non-date Posting Date or a non-numeric Balance does not cause a skip (D5, D18)."

### Unclear test granularity - Severity: Nit
* **Ids:** `style-3-7` (N6)
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 538, 648, 708
* **Discrepancy Description:** The plan uses three phrasings: "one test per case", "as its own test" and "one test per bullet". Several bullets list multiple inputs.
* **Rationale & Recommendation:** State one rule: one test function per bullet, and `pytest.mark.parametrize` for bullets that list several inputs.

### Ambiguous zero-amount case - Severity: Nit
* **Ids:** `style-3-8` (N7)
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 547-548
* **Rationale & Recommendation:** List the exact row(s) and the expected REASON (`Debit and Credit both blank`).

### Jargon: "folded pattern" - Severity: Nit
* **Ids:** `style-3-10` (N9)
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 641
* **Rationale & Recommendation:** "`(pattern.casefold(), category)` with both trimmed."

### Self-contradicting wording in the zero-amount CLI test - Severity: Nit
* **Ids:** `style-3-12` (N10)
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 716-719
* **Discrepancy Description:** "pair" is used for both the setup and the result. The account placement is unclear.
* **Rationale & Recommendation:** "A Format B row `-0.00` in account X and a Format B row `0.00` in account Y on the same date both have blank `transfer_id` (D17)."

## Below-Nit observations (no action required)

- **ir:** Lines 525-532 do not repeat that a Format A amount is −Debit or +Credit, or which `signed` value each format passes. Both follow from line 105 and D15.
- **style:** Line 695 ("`cli.main` owns D8") repeats the coverage table. Lines 501-503 could be shortened.

## Verified correct (reported by reviewers, no finding)

- **`write_ledger`:** the `mkstemp` → `open(fd)` → `copymode` → `os.replace` sequence with `finally` cleanup, and `0o600` for new files.
- **Amounts:** `-0.00` is written as `0.00`, and Decimal keys work for dedup and pairing.
- **Tests:** both monkeypatch targets resolve, and the D17 `-0.00` tests are consistent.
- **CLI and imports:** argparse handles the required subcommand and missing options correctly, and `python -m pytest` from the root imports the package.
- **Plan structure:** there are no import cycles, every phase can be tested on its own, and D1-D24 all appear in the coverage table.
- **Contract:** nothing contradicts BRIEF.md or stakeholder_log.md.
