# Goldfish Review Report

**Target:** `docs/designs/txmerge.md` (lines 467-695, `## Detailed Implementation Plan` to end)
**Stage:** 9, Implementation Readiness Test. egm-review-loop round 1.
**Standard:** `/Users/mashhoodr/.claude/plugins/cache/egm/egm/0.1.0/resources/document_standards/implementation-readiness-standard.md` (readiness, codebase-details). The style reviewer used its persona's own rules.

## Reviewer Status

| Reviewer | Status |
| --- | --- |
| `egm-implementation-readiness` | completed |
| `egm-codebase-details` | completed |
| `egm-style` | completed |

## Severity Breakdown

| Severity | Count |
| --- | --- |
| Blocker | 0 |
| Major | 5 |
| Nit | 21 |

Verdict: **not ready.** No Blockers. In five places the implementer would have to make a decision, or the planned tests would fail on the first run.

Triage notes:
- Where reviewers reported the same gap, it appears once below, under the id of the reviewer who described it most precisely. The other lenses are listed with it, and the entry takes the highest severity any of them gave.
- `style-1-2` was downgraded from Major to Nit. It is a readability problem, and it does not leave the implementer a design decision.
- Findings that point at lines 1-466 have been re-anchored to the plan lines that cite those sections.

## Prioritized Findings (Blockers -> Major -> Nits)

### readiness-1-1: argparse usage errors raise `SystemExit`; `main` never returns 2 for them (Severity: Major)
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 626-640 (step 13), 653-654 and 664-666 (step 15 tests)
* **Discrepancy Description**: `main(argv) -> int` is specified to return 2 only on `TxmergeError`. A bad `--account` (`ArgumentTypeError`), a missing required option or a missing `merge` sub-command makes argparse call `parser.error()`, which raises `SystemExit(2)` inside `parse_args`. The step 15 tests call `cli.main([...])` and expect "exit 2". The implementer must choose between catching `SystemExit` in `main` and asserting it with `pytest.raises(SystemExit)` in the tests.
* **Rationale & Recommendation**: State the contract. For example: "argparse usage errors propagate as `SystemExit(2)`; `main` returns 0 or 2 only after parsing succeeds; usage-error tests use `pytest.raises(SystemExit)`, assert `excinfo.value.code == 2`, then read stderr with `capsys`." Add a test for a missing required option and a missing sub-command (D13).

### readiness-1-2: The transfer-id formatter is tested but never declared (Severity: Major)
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`, `egm-style`
* **Affected Scope:** Lines 588-590 (step 9), 607-609 (step 11)
* **Discrepancy Description**: The test checks that "the id format expression gives `T10000` for n = 10000 (checked directly)". Step 9 exposes only `pair_transfers`, so the test has nothing to call. The implementer must invent a public name and signature.
* **Rationale & Recommendation**: Add `transfer_id(n: int) -> str` (returns `f"T{n:04d}"`, D9) to `txmerge/transfers.py` and require `pair_transfers` to use it. Step 11 then asserts `transfer_id(1) == "T0001"` and `transfer_id(10000) == "T10000"`.

### readiness-1-3: How the input files are opened, and which exceptions become errors, is not stated (Severity: Major)
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 506-511 (`read_export`), 596-599 (`load_rules`), with tests at 523-525 and 532-533. Cites the Technical Plan and Messages at lines 250-251 and 330-331.
* **Discrepancy Description**:
  * `encoding="utf-8-sig"` is never named. With plain `"utf-8"` the first header cell keeps U+FEFF, which `str.strip()` does not remove, so the BOM test at line 523 fails.
  * `newline=""` is never named, although the csv module needs it for quoted multi-line cells and correct `line_num`.
  * `UnicodeDecodeError` is a `ValueError`, not an `OSError`, and it is raised while iterating the reader, not at `open()`. Catching `OSError` around `open` leaves the invalid-UTF-8 case at line 533 as a traceback instead of exit 2.
  * The format of the `<OS, decode or CSV error>` payload is not pinned.
  * Neither function says whether the shared D16 reading logic is one helper or two copies.
* **Rationale & Recommendation**: In both functions, state: `open(path, encoding="utf-8-sig", newline="")`; wrap the open and the whole `csv.reader` loop in `try`; catch `(OSError, UnicodeDecodeError, csv.Error)` as `e` and raise `TxmergeError(f"cannot read {path}: {e}")`. Optionally define one shared helper, such as `model.read_csv(path)`, that returns the trimmed header and the non-blank `(line_no, cells)` rows and handles "cannot read" and "file is empty".

### codebase-1-1: The `write_ledger` steps are underspecified, and the obvious version can break D23 (Severity: Major)
* **Reviewer Lens:** `egm-codebase-details`, `egm-implementation-readiness`, `egm-style`
* **Affected Scope:** Lines 554-561 (step 6), tested at 580-581 and 659-663
* **Discrepancy Description**:
  * (a) `mkstemp` returns a file descriptor. The plan never says to wrap it with `os.fdopen(fd, "w", encoding="utf-8", newline="")`, and `f` in `csv.writer(f, ...)` is never created.
  * (b) The plan does not say to close the stream before `os.replace`. If the rename happens inside the `with` block, a flush error on close (for example disk full) comes after the rename and leaves `--out` truncated. That silently breaks D23, and no planned test catches it.
  * (c) If `mkstemp` raises (exactly the missing-directory test at 580-581), `tmp` is unbound and the `finally` cleanup raises `NameError` instead of producing a `TxmergeError`.
  * (d) "directory of path" is `""` for a bare filename.
  * (e) The plan puts `copymode` after the write, while D23 says "first".
* **Rationale & Recommendation**: Spell out the order:
  1. `tmp = None`.
  2. `fd, tmp = mkstemp(dir=os.path.dirname(os.path.abspath(path)), prefix=".txmerge-", suffix=".tmp")`.
  3. `with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:`, write with `csv.writer(f, lineterminator="\n")`.
  4. After the `with` block closes, if `path` exists, call `shutil.copymode(path, tmp)`.
  5. `os.replace(tmp, path)`.
  6. Convert `OSError` to `TxmergeError("cannot write ...")`.
  7. In `finally`, unlink `tmp` if it is set and exists.

  Also state that copying the mode after writing satisfies D23.

### style-1-1: The coverage table claims every rule is tested, but the test lists leave gaps (Severity: Major)
* **Reviewer Lens:** `egm-style`, `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 680-689 (claim and table), and the test lists at 517-534, 613-618 and 651-666
* **Discrepancy Description**: "every rule is exercised by the tests listed above" is not supported by the lists. These cases have no listed test:
  * D14: the first failing check decides the reason (for example, bad date plus bad amount reports the date; cell count wins over both).
  * Format B bad date and bad or blank Amount.
  * A signed Format A Debit (`-5.00`), and `.50` / `5.`.
  * D17: a zero-amount row is kept and categorised by the rules.
  * A file containing only blank lines → "file is empty".
  * Which count blank lines are left out of (line 531).
  * Rules file: empty file, invalid UTF-8, header-only file → zero rules, header with an extra column.
  * D13: a missing required option or sub-command.
  * D20: `os.path.samefile` raising `OSError`.
  * A file that raises `csv.Error`.
* **Rationale & Recommendation**: Add these tests to steps 4, 12 and 15. Alternatively, reword the claim and list the cases left untested on purpose. The plan must not make an absolute claim its lists contradict.

### readiness-1-4: The `csv.Error` example (a NUL byte) is probably wrong on Python 3.11+ (Severity: Nit)
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 506-511 and 596-599, which rely on Technical Plan lines 250-251
* **Discrepancy Description**: Both reviewers believe the csv reader accepts NUL characters from 3.11 (bpo-27580). Neither could run Python to confirm. A test written from this example would fail.
* **Rationale & Recommendation**: Verify this. If it is confirmed, use a field larger than `csv.field_size_limit()` as the example and test that instead.

### readiness-1-5: The monkeypatch target depends on how `ledger.py` imports `os` (Severity: Nit)
* **Reviewer Lens:** `egm-implementation-readiness`
* **Affected Scope:** Lines 556-561 and 659-660
* **Discrepancy Description**: Patching `txmerge.ledger.os.replace` works only if `ledger.py` does `import os` and calls `os.replace(...)`.
* **Rationale & Recommendation**: State that requirement in step 6.

### readiness-1-6: `warn` must look up `sys.stderr` when it is called (Severity: Nit)
* **Reviewer Lens:** `egm-implementation-readiness`
* **Affected Scope:** Lines 492-495, and the `capsys` tests at 515-516 and 528-530
* **Discrepancy Description**: A module-level alias of `sys.stderr`, captured at import, would break the `capsys` tests.
* **Rationale & Recommendation**: Say `print(..., file=sys.stderr)` is evaluated at call time.

### readiness-1-7: The order of checks and the message placeholders are still ambiguous (Severity: Nit)
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 509-510, 528-530 and 596-599. Cites Messages at lines 325-333 and D11/D14.
* **Discrepancy Description**: The plan does not pin down:
  * whether `X` in `bad date 'X'` / `bad amount 'X'` is the trimmed cell, wrapped in literal single quotes;
  * which Format A amount is reported when both Debit and Credit fail (Debit first?);
  * whether `unrecognised header:` joins the trimmed cells or the raw ones;
  * the order of checks for rule rows (cell count, then pattern, then category).
* **Rationale & Recommendation**: Add one line pinning each point.

### readiness-1-8: The D15 amount grammar is prose only (Severity: Nit)
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 502-505
* **Discrepancy Description**:
  * `\d` in `re` matches Unicode digits, and `Decimal` accepts them, so a natural regex lets through input D15 implicitly rejects.
  * Whether a group like `0,123` is valid is unclear.
  * The plan does not say whether values are quantized to 2 places.
* **Rationale & Recommendation**: Give the exact pattern using `[0-9]` (or `re.ASCII`), with a `[+-]?` prefix only when `signed=True`. State whether `parse_amount` returns `quantize(Decimal("0.01"))`.

### readiness-1-9: The test run environment is unstated (subprocess `cwd`, `python -m pytest`) (Severity: Nit)
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 649-650, 677 and 690-691
* **Discrepancy Description**:
  * `python -m txmerge` imports only when the working directory is the repository root. If the test sets `cwd=tmp_path`, the import fails.
  * Bare `pytest` without a root `conftest.py` puts `tests/` on `sys.path` instead of the root, so imports fail.
* **Rationale & Recommendation**: Use `cwd=Path(__file__).resolve().parents[1]` with absolute fixture paths. Either require `python -m pytest`, or create an empty root `conftest.py`.

### readiness-1-10: The fixed scenario for the exact-bytes test is left to the implementer (Severity: Nit)
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-style`
* **Affected Scope:** Lines 651-653
* **Discrepancy Description**: "a small fixed scenario" is not given. "small" carries no information.
* **Rationale & Recommendation**: Give the input rows and the expected ledger bytes.

### codebase-1-2: The required sub-command should name a `dest` (Severity: Nit)
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Line 627
* **Discrepancy Description**: In some Python versions (bpo-29298), `add_subparsers(required=True)` without `dest` raises `TypeError` when the sub-command is missing.
* **Rationale & Recommendation**: Specify `add_subparsers(dest="command", required=True)`.

### codebase-1-3: The D3 description replacement needs `dataclasses.replace` (Severity: Nit)
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Lines 541-545
* **Discrepancy Description**: `Row` is frozen, so its description cannot be assigned in place.
* **Rationale & Recommendation**: Add one sentence saying to use `dataclasses.replace(row, description=...)`.

### codebase-1-4: The `format_amount` method for negative zero is not stated (Severity: Nit)
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Line 553 (test at 578)
* **Discrepancy Description**: `f"{Decimal('-0.00'):.2f}"` gives `-0.00`, so an explicit zero check is needed. The test pins the behaviour.
* **Rationale & Recommendation**: State the zero normalisation in step 6.

### style-1-2: The `test_cli.py` item is one long paragraph and lists the `--account` cases twice (Severity: Nit; reviewer graded Major)
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 651-666
* **Discrepancy Description**: About 16 cases are joined by semicolons. The malformed `--account` cases appear at 653-654 and again at 664-666.
* **Rationale & Recommendation**: Use bullets grouped by rule (CUJs, D20, D22, D23, D24). Merge the two `--account` mentions into one bullet.

### style-1-3: Other test items also use run-on paragraphs (Severity: Nit)
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 566-572, 577-581, 605-609 and 614-618
* **Discrepancy Description**: These items put many cases in one paragraph, while `test_readers.py` uses one bullet per case.
* **Rationale & Recommendation**: Use one bullet per case or per group of cases.

### style-1-4: "One test per case" is ambiguous (Severity: Nit)
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 517
* **Discrepancy Description**: The bullets hold several values each, so "case" could mean a bullet or a value.
* **Rationale & Recommendation**: Say "one test per listed value (parametrised tests allowed)".

### style-1-5: "Exact warning text" is promised but never written out (Severity: Nit)
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 528-530
* **Discrepancy Description**: The implementer has to build every expected string from the Messages table.
* **Rationale & Recommendation**: Give one fully written-out expected line as a model.

### style-1-6: "Garbage there is fine" is informal (Severity: Nit)
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 521-522
* **Discrepancy Description**: The slang does not say what is accepted.
* **Rationale & Recommendation**: Write "any text in Posting Date / Balance is accepted and not parsed".

### style-1-7: "Not counted" does not say which count (Severity: Nit)
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 531
* **Discrepancy Description**: The line does not say whether blank lines are left out of the skipped count, the line numbering, or both.
* **Rationale & Recommendation**: Say they are excluded from the skipped count but still advance line numbers (D16).

### style-1-8: Double negative in `parse_amount` (Severity: Nit)
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 503-505
* **Discrepancy Description**: "Never calls `Decimal()` on text that has not passed..." is harder to read than it needs to be.
* **Rationale & Recommendation**: Write "Calls `Decimal()` only on text that matches the D15 grammar".

### style-1-9: A vague parameter name and unclear wording (Severity: Nit)
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 492-494, 598 and 634-640
* **Discrepancy Description**:
  * The `warn` parameter name `what` is vague.
  * "folded pattern" is jargon.
  * "`cli.main` owns D8" is unclear, inside a seven-line sentence.
* **Rationale & Recommendation**:
  * Rename `what` to `kind`.
  * Write "casefolded pattern".
  * Replace "owns" with "implements", and split `main` into numbered steps.

### style-1-10: Wrong D-numbers in the `readers.py` scope (Severity: Nit)
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 499
* **Discrepancy Description**: The range "D13–D19" includes D17 and D19, which belong to pairing/output and dedup, not to the readers.
* **Rationale & Recommendation**: List "D5, D13 (input files), D14, D15, D16, D18".

### style-1-11: Determinism wording in `dedup.py` reads as a contradiction (Severity: Nit)
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 542-545
* **Discrepancy Description**: "does not depend on hash randomisation" is followed by "output order is unspecified", which can read as a contradiction.
* **Rationale & Recommendation**: Say which rows are kept, and their descriptions, are deterministic; the order is left to the caller.

### style-1-12: Imprecise phrases, and the E2E test described twice (Severity: Nit)
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 577, 649-650, 672 and 690-691
* **Discrepancy Description**:
  * "tie-break order on equal date and account" does not name the keys.
  * "Does not copy the rules" could mean the category rules or the Decisions.
  * The subprocess E2E test is described twice without a name.
* **Rationale & Recommendation**:
  * Say "sort by `arg_index`, then `line_no`".
  * Write "Does not restate the Decisions table".
  * Name the E2E test once in step 15 and refer to that name from the Verification Plan.
