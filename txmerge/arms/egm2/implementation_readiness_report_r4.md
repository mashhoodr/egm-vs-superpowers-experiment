# Goldfish Review Report

**Target:** `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers/arms/egm2/docs/designs/txmerge.md` (lines 467-772, `## Detailed Implementation Plan` to end)
**Stage:** 9 (Implementation Readiness Test), egm-review-loop round 4
**Standard:** `/Users/mashhoodr/.claude/plugins/cache/egm/egm/0.1.0/resources/document_standards/implementation-readiness-standard.md` (implementation-readiness, codebase-details); egm-style used its persona's own rules.

## Reviewer Status

| Reviewer | Status | Raw findings |
| --- | --- | --- |
| `egm-implementation-readiness` | completed | 0 Blocker, 1 Major, 6 Nit |
| `egm-codebase-details` | completed | 0 Blocker, 2 Major, 6 Nit |
| `egm-style` | completed | 0 Blocker, 0 Major, 7 Nit |

**Severity breakdown (raw, 22 findings):** 0 Blocker, 3 Major, 19 Nit.
**After deduplication (17 unique issues):** 0 Blocker, 2 Major, 15 Nit. One merged issue has a different rating from each reviewer (codebase-details Major, implementation-readiness Nit). It is listed under Major and both ratings are shown. No reviewer's rating was changed.

## Prioritized Findings (Blockers -> Major -> Nits)

No Blockers.

### Very long amounts crash `parse_amount` with an uncaught `decimal.InvalidOperation` - Severity: Major
* **Ids:** `egm-implementation-readiness-4-1` (Major), `egm-codebase-details-4-1` (Major)
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 517-524 (`parse_amount`), 525-532 (how `read_export` uses it); D15 at line 128
* **Discrepancy Description**: D15 does not limit the number of digits. The default decimal precision is 28 digits. With 27 or more integer digits, `.quantize(Decimal("0.01"))` raises `decimal.InvalidOperation`, and negation can silently round the value. `InvalidOperation` is an `ArithmeticError`, not a `ValueError`. Neither `read_export` nor `cli.main` (`except TxmergeError`) catches it, so the run dies with a traceback and exit 1 instead of a `bad amount 'X'` warning. That breaks G6 and D14. The plan's claims that quantize "never changes a value" and that `parse_amount` raises only `ValueError` are false.
* **Rationale & Recommendation**: Pick one rule and write it into D15 and item 3. Either (a) cap the integer digits in the grammar (for example at most 15), so longer values become `bad amount`; or (b) have `parse_amount` turn `decimal.InvalidOperation` into `ValueError`. Add a test for it to `tests/test_readers.py` (around line 549).

### No check order or REASON for rule rows that fail more than one check - Severity: Major (codebase-details) / Nit (implementation-readiness)
* **Ids:** `egm-codebase-details-4-2` (Major), `egm-implementation-readiness-4-4` (Nit)
* **Reviewer Lens:** `egm-codebase-details`, `egm-implementation-readiness`
* **Affected Scope:** Lines 637-642 (`load_rules`), 660-661 (test_rules); D11 at line 124; REASON list at lines 325-328
* **Discrepancy Description**: D14 fixes the check order for export rows, but nothing fixes it for rule rows. Some rows have no defined warning: a row with both pattern and category blank, or a row with the wrong cell count and a blank cell, could produce either of two REASONs. The tests check the exact warning text.
* **Rationale & Recommendation**: State the order in D11 or item 10: cell count (`expected 2 cells, got M`), then `blank pattern`, then `blank category`. The first check that fails gives the REASON.

### D15 amount grammar is prose, not an exact pattern - Severity: Nit
* **Ids:** `egm-implementation-readiness-4-2`, `egm-codebase-details-4-3`
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 517-524; D15 at line 128
* **Discrepancy Description**: `\d` matches non-ASCII digits, and `Decimal()` accepts them. `re.match` with `$` accepts different strings than `re.fullmatch`. The plan also does not say how many digits the first comma group may have.
* **Rationale & Recommendation**: Give the exact pattern with ASCII digits, used with `re.fullmatch`, for example `(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]{1,2})?`, with an optional `[+-]` prefix only when `signed=True`.

### Quoted text in warnings is not fully defined (raw vs trimmed, which cell, quoting) - Severity: Nit
* **Ids:** `egm-implementation-readiness-4-3`, `egm-codebase-details-4-5`
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 326, 331, 527-531, 549-551
* **Discrepancy Description**: The plan does not say whether `X` in `bad date 'X'` / `bad amount 'X'`, and the cells in `unrecognised header: ...`, are raw or trimmed. It does not say which cell is reported when both Debit and Credit fail, or whether `'VALUE'` in the `--account` message is `'{value}'` or `{value!r}`. The tests check the exact text.
* **Rationale & Recommendation**: State that the text is the cell after the D16 trim, that Debit is checked before Credit and the first failure is reported, and that the quotes are literal (`f"... got '{value}'"`).

### Subprocess end-to-end test has no working directory set - Severity: Nit
* **Ids:** `egm-implementation-readiness-4-5`, `egm-codebase-details-4-8`
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 712-713, 767-768
* **Discrepancy Description**: If the implementer sets `cwd=tmp_path`, `python -m txmerge` fails with "No module named txmerge".
* **Rationale & Recommendation**: Run from the repository root (`cwd=pathlib.Path(__file__).resolve().parent.parent`, or no `cwd`) and pass absolute fixture paths.

### Same-file check order across inputs and rules path is not stated - Severity: Nit
* **Ids:** `egm-implementation-readiness-4-6`
* **Reviewer Lens:** `egm-implementation-readiness`
* **Affected Scope:** Lines 693-697
* **Discrepancy Description**: "for each input path and the rules path" does not give the order. The order decides which message is shown when one path raises and another matches `--out`.
* **Rationale & Recommendation**: Check inputs in `--account` order, then the rules path, and stop at the first error.

### Two tests are not fully specified - Severity: Nit
* **Ids:** `egm-implementation-readiness-4-7`
* **Reviewer Lens:** `egm-implementation-readiness`
* **Affected Scope:** Lines 549-551, 717-718
* **Discrepancy Description**: No test checks that a signed Format A Debit/Credit (`-5.00`, `+5.00`) is skipped as `bad amount` (D15). The "exact expected bytes" scenario gives no input rows or expected output.
* **Rationale & Recommendation**: Add the signed Format A case to the readers tests. Optionally write the scenario's inputs and expected ledger bytes into the plan.

### Type of `HEADER` is not stated - Severity: Nit
* **Ids:** `egm-codebase-details-4-4`
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Lines 582, 592-594
* **Discrepancy Description**: If `HEADER` is a string, `csv.writer.writerow(HEADER)` writes one cell per character.
* **Rationale & Recommendation**: Declare `HEADER = ["date", "account", "description", "amount", "category", "transfer_id"]` (a list).

### The `try` in `read_csv` must cover iteration, not just `open()` - Severity: Nit
* **Ids:** `egm-codebase-details-4-6`
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Lines 508-516 (tests at 554, 563-564)
* **Discrepancy Description**: `UnicodeDecodeError` and `csv.Error` are raised while iterating, not at `open()`. If only `open()` is wrapped, the invalid-UTF-8 and field-size tests fail with uncaught exceptions.
* **Rationale & Recommendation**: State that the `try` covers both the open and the full iteration.

### Samefile-`OSError` test needs an existing `--out` - Severity: Nit
* **Ids:** `egm-codebase-details-4-7`
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Lines 729-731; `main` step 5 at line 693
* **Discrepancy Description**: `samefile` is only called when `--out` exists. Without that file, the monkeypatch is never reached and the run exits 0.
* **Rationale & Recommendation**: Add "with an existing `--out` file" to the test bullet.

### Wrong step cross-reference in `write_ledger` - Severity: Nit
* **Ids:** `egm-style-4-1`
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 593-598
* **Discrepancy Description**: "closes the file before step 3" points to the wrong step: step 3 is the `except OSError` clause. The intended steps are `copymode` and `os.replace` inside step 2.
* **Rationale & Recommendation**: "The `with` block closes the file before `copymode` and `os.replace` run."

### Unclear owner of data-cell trimming - Severity: Nit
* **Ids:** `egm-style-4-2`
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 515-516, 523-524
* **Discrepancy Description**: `read_csv` says "callers trim", but the D16 trim sentence sits in the `parse_amount` bullet. That placement suggests `parse_amount` trims its own input.
* **Rationale & Recommendation**: Move the sentence into the `read_export` bullet, or state that `parse_amount` expects already-trimmed text.

### Informal wording: "garbage there is fine" - Severity: Nit
* **Ids:** `egm-style-4-3`
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 542-543
* **Discrepancy Description**: The wording is colloquial and does not say what the test asserts.
* **Rationale & Recommendation**: "a non-date value in Posting Date does not cause a skip"; "a non-numeric Balance value does not cause a skip (D18)".

### "exit 2 (usage)" convention is defined by capitalisation but used in lower case - Severity: Nit
* **Ids:** `egm-style-4-4`
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 714-715, 735, 740
* **Discrepancy Description**: The definition contrasts "Exit 2 (usage)" with "exit 2", but the bullets use lower case. The real difference is the "(usage)" suffix.
* **Rationale & Recommendation**: "'exit 2 (usage)' means `SystemExit` with code 2; plain 'exit 2' means `main` returns 2."

### "rule" means two different things - Severity: Nit
* **Ids:** `egm-style-4-5`
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 748-749, 757 (vs 640-642, 657-662)
* **Discrepancy Description**: In the README and coverage bullets, "rule" means a Decision (D1-D24). Elsewhere it means a row of the rules file.
* **Rationale & Recommendation**: Say "Decisions (D1-D24)" at lines 748-749 and 757.

### Phase 2 heading leaves out output writing - Severity: Nit
* **Ids:** `egm-style-4-6`
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 566 (with 577-599, 612-621)
* **Discrepancy Description**: "Dedup and ordering" leaves out `format_amount` and `write_ledger` (D21, D23), which Phase 2 also builds and tests.
* **Rationale & Recommendation**: Rename the heading to "Phase 2 – Dedup, ordering and output".

### Inconsistent range punctuation and minor jargon - Severity: Nit
* **Ids:** `egm-style-4-7`
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 687, 700
* **Discrepancy Description**: "steps 3-9" uses a hyphen, while the rest of the document uses an en dash. "(D8, owned here)" is mild jargon.
* **Rationale & Recommendation**: Write "steps 3–9", and say "computed in `main`, not in `rules.py`".

## Notes

* All reviewers found that file and signature names match across the plan, the Technical Plan and the Messages table. They also found the phase boundaries, file list and test-to-Decision coverage meet the standard.
* Every reviewer completed on its first attempt. No retries were needed.
