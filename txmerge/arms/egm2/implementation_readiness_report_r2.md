# Goldfish Review Report

**Target:** `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers/arms/egm2/docs/designs/txmerge.md` (lines 467-741, Detailed Implementation Plan)
**Stage:** 9 (Implementation Readiness Test), egm-review-loop round 2

## Reviewer Status

| Reviewer | Status | Findings as rated |
| --- | --- | --- |
| `egm-implementation-readiness` | completed | 0 Blocker, 0 Major, 8 Nit |
| `egm-codebase-details` | completed | 0 Blocker, 4 Major, 6 Nit |
| `egm-style` | completed | 0 Blocker, 1 Major, 5 Nit |

**Raw totals:** 0 Blocker, 5 Major, 19 Nit (24 findings).
**After deduplication:** 0 Blocker, 5 Major entries, 13 Nit-only entries (18 entries). When reviewers rated the same issue differently, the entry is listed under the highest rating and each reviewer's own rating is shown. No ratings were changed.

## Prioritized Findings (Blockers -> Major -> Nits)

### Blockers

None.

### Majors

### egm-codebase-details-2-1: Date parsing yields `datetime`, but `Row.date` is `date` - Severity: Major
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Lines 515-522 (relies on 235, 249, 304)
* **Discrepancy Description**: The plan says to parse with `datetime.strptime`, which returns `datetime.datetime`. `Row.date` is declared `datetime.date`. Taken literally, `.isoformat()` writes `2026-03-05T00:00:00`, which breaks the ISO `YYYY-MM-DD` output contract. The strptime format strings are not given either.
* **Rationale & Recommendation**: In item 3, state `datetime.strptime(cell, "%d/%m/%Y").date()` (Format A) and `datetime.strptime(cell, "%Y-%m-%d").date()` (Format B). State that the writer uses `row.date.isoformat()`.

### egm-codebase-details-2-2: Header comparison mixes tuple and list - Severity: Major
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Lines 501-510, 517-518, 622-623
* **Discrepancy Description**: `FORMAT_A`/`FORMAT_B` are "header tuples", but `read_csv` returns `list[str]`. In Python a list never equals a tuple, so a direct comparison rejects every export as "unrecognised header". The rules header is compared to a list, so the two checks are inconsistent.
* **Rationale & Recommendation**: Fix one form. For example, `tuple(c.strip() for c in cells) == FORMAT_A`, or define the format constants as lists.

### egm-codebase-details-2-3: `format_amount` has no rule against `-0.00`, and the place amounts are rounded is unstated - Severity: Major
* **Reviewer Lens:** `egm-codebase-details` (Major). Overlaps `egm-implementation-readiness-2-7` (Nit), which covers the rounding half.
* **Affected Scope:** Lines 511-514, 571, 602 (Row record at 237, test at 531)
* **Discrepancy Description**: `f"{amount:.2f}"` on `Decimal('-0.00')` gives `'-0.00'`, so the planned test at line 602 fails and D17 is broken. The plan states the rule but not how to meet it. The Row record says amounts have 2 decimal places, but `parse_amount` is never told to round (`+3` gives `Decimal('3')`). That leaves the implementer to decide whether parsing or formatting enforces 2 decimals.
* **Rationale & Recommendation**: Specify `format_amount` as: return `"0.00"` if `amount == 0`, else `f"{amount:.2f}"`. State where rounding happens: either `parse_amount` returns `value.quantize(Decimal("0.01"))` (IR's suggestion), or only `format_amount` guarantees 2 decimals (CD's suggestion). Make the `+3` test match whichever is chosen.

### egm-codebase-details-2-4: The required `merge` subcommand has no `dest` - Severity: Major
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Lines 654-656, 703-704
* **Discrepancy Description**: The plan does not give the `add_subparsers` arguments. On some CPython versions, `required=True` without `dest` raises `TypeError` instead of exiting 2 when no subcommand is given (bpo-29298). The reviewer could not confirm the fix covers every 3.11.x release. The plan also leaves the name `main` uses to check the subcommand to the implementer.
* **Rationale & Recommendation**: Specify `sub = parser.add_subparsers(dest="command", required=True)` and `m = sub.add_parser("merge")`, with the three options added to `m`.

### egm-style-2-1: Coverage table says "every rule is exercised", but some rules have no test - Severity: Major
* **Reviewer Lens:** `egm-style` (Major). Overlaps `egm-implementation-readiness-2-6` (Nit) and `egm-codebase-details-2-10` (Nit).
* **Affected Scope:** Lines 726-735 (test lists at 524-712)
* **Discrepancy Description**: The following rules have no listed test:
  - D23: an existing `--out` keeps its permission bits (`copymode`, line 582), and a new ledger is created with mode 0600 (IR).
  - D17: zero amounts are kept and categorised by rules.
  - D16: data cells are trimmed (only header trimming is tested, line 534).
  - The table does not list rules-file D13 under `test_cli.py`, although the tests are there (lines 701-702).
  The implementer will trust the table and will not add the missing tests.
* **Rationale & Recommendation**: Add these tests:
  - an existing `--out` at 0644 stays 0644 after a run;
  - a new ledger is 0600;
  - a Format B `0.00` row is written as `0.00` with its rule category;
  - padded data cells (` 12.50 `, ` 05/03/2026 `) parse.
  Add "D13 (rules file)" to the `test_cli.py` row, or narrow the claim.

### Nits

### egm-implementation-readiness-2-1 / egm-codebase-details-2-6: The end-to-end subprocess test does not say its working directory - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 685-686, 736-737
* **Discrepancy Description**: `python -m txmerge` only resolves from the repository root or with `PYTHONPATH` set. A natural `cwd=tmp_path` gives `ModuleNotFoundError`.
* **Rationale & Recommendation**: Pass `cwd=Path(__file__).resolve().parents[1]` (or the repository root), and pass absolute `tmp_path` file paths.

### egm-implementation-readiness-2-2 / egm-codebase-details-2-7: Rule-row check order and reason text are unstated - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 621-626 (D11 at 124, Messages at 325-328)
* **Discrepancy Description**: D14 fixes the check order for export rows only. For rule rows, the order of the cell-count and blank checks is not given. That `N` = 2 is only implied.
* **Rationale & Recommendation**: Add: "checks in order: cell count (`expected 2 cells, got M`), then `blank pattern`, then `blank category`."

### egm-implementation-readiness-2-3 / egm-codebase-details-2-9: "Unrecognised header" message does not say raw or trimmed cells - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 331, 517-519
* **Discrepancy Description**: It is not stated whether `<header cells joined by ,>` shows the raw or the trimmed cells.
* **Rationale & Recommendation**: Say "the trimmed header cells joined by `,`".

### egm-implementation-readiness-2-4: Which cell is quoted when both Debit and Credit are bad - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`
* **Affected Scope:** Lines 519-521 (D14 at 127)
* **Discrepancy Description**: When both cells fail to parse, `X` in `bad amount 'X'` could be either one.
* **Rationale & Recommendation**: Add "Debit is checked before Credit; `X` is the first cell that fails."

### egm-implementation-readiness-2-5: Same-file check order - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`
* **Affected Scope:** Lines 668-672
* **Discrepancy Description**: The order the paths are checked is not given. The message printed depends on it when `--out` matches more than one file, or when `samefile` errors on one file and matches another.
* **Rationale & Recommendation**: State the order: inputs in argument order, then the rules path, stopping at the first error.

### egm-implementation-readiness-2-8: Test fixtures must quote amounts that contain commas - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`
* **Affected Scope:** Lines 529-531, 539-540
* **Discrepancy Description**: Unquoted `1,250.00` / `1,25.00` split into extra cells. The row then triggers the cell-count warning instead of `bad amount`, so the test checks the wrong reason.
* **Rationale & Recommendation**: Note that fixtures write comma-containing amounts as quoted cells, e.g. `"1,250.00"`.

### egm-codebase-details-2-5: The samefile-failure test is missing a precondition - Severity: Nit
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Lines 698-700 (vs 669-672, D20 at 133)
* **Discrepancy Description**: `samefile` is only called when `--out` exists. The test does not say to create it, so the patched function is never reached and the test fails.
* **Rationale & Recommendation**: Add "with an existing file at `--out`".

### egm-codebase-details-2-8: The Messages table leaves out argparse's `argument --account:` prefix - Severity: Nit
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Line 323 (vs 657-661, 709-710)
* **Discrepancy Description**: argparse prints `error: argument --account: --account must be ...`. The table describes the text without the prefix. The test checks a substring, so it still passes.
* **Rationale & Recommendation**: Note the prefix in the table.

### egm-style-2-2: The `cli.main` instruction is one run-on sentence - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 662-676 (line 672 runs past the document's line wrap)
* **Discrepancy Description**: The whole orchestration is one sentence, with nested parentheses, try/except prose, arrow-notation outcomes and a semicolon tail.
* **Rationale & Recommendation**: Rewrite as numbered steps, as `write_ledger` does at lines 574-585. Re-wrap line 672.

### egm-style-2-3: Redundant or loose wording in `cli.main` - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 664-667, 673-674
* **Discrepancy Description**: The `pytest.raises(SystemExit)` guidance is repeated at 687-688. The note "`cli.main` owns D8" repeats the D8 point and uses loose jargon.
* **Rationale & Recommendation**: Keep the test guidance only in item 15. Delete "; `cli.main` owns D8".

### egm-style-2-4: Wrong step reference in `write_ledger` - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 580-581
* **Discrepancy Description**: The text says the file closes "before step 3". Step 3 is the `except` clause. It should name `copymode`/`os.replace`.
* **Rationale & Recommendation**: "The `with` block closes the file before `copymode` and `os.replace`."

### egm-style-2-5: Informal wording - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 532-533, 574
* **Discrepancy Description**: "Garbage there is fine" and "this exact order" are casual or padded.
* **Rationale & Recommendation**: Use "any text in that column is accepted" and "in this order".

### egm-style-2-6: Exit-code labels and the E2E note are repeated - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 687-688, 704, 709; 685-686 vs 736-737
* **Discrepancy Description**: The capitalised "Exit 2 (usage)" definition is followed by lowercase uses, so only the suffix separates the two meanings. The subprocess E2E note appears twice.
* **Rationale & Recommendation**: Define the labels by suffix only, e.g. "'exit 2 (usage)' means `SystemExit(2)`; plain 'exit 2' means `main` returns 2". Keep the E2E note in one place.

## Confirmed Sound (no action)

- `write_ledger` atomic-write order: `mkstemp` fd, `newline=""`, `copymode` after close, `tmp = None` after replace, `finally` cleanup (IR, CD).
- `read_csv` encoding (`utf-8-sig`), `line_num` semantics, exception coverage (CD, IR).
- Monkeypatch targets `txmerge.ledger.os.replace` and `txmerge.cli.os.path.samefile` resolve correctly (CD).
- Decimal hashing in dedup keys and the pairing index; `T{n:04d}` overflow behaviour; zero rows kept out of pairing (CD, IR).
- Message wording at lines 508-509, 519, 584, 623-624, 671-672 matches the Messages table; D-number references are correct (style).
- The phase order and module dependencies are consistent; no `conftest.py` is needed (CD).
