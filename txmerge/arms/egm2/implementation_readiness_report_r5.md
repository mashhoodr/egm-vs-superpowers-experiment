# Goldfish Review Report

**Target:** `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers/arms/egm2/docs/designs/txmerge.md` (lines 467-782, `## Detailed Implementation Plan` to end)

**Stage:** 9 (Implementation Readiness Test), egm-review-loop round 5

## Reviewer Status

| Reviewer | Status | Raw findings |
| --- | --- | --- |
| `egm-implementation-readiness` | completed | 1 Blocker, 0 Major, 6 Nit |
| `egm-codebase-details` | completed | 1 Blocker, 0 Major, 6 Nit |
| `egm-style` | completed | 0 Blocker, 0 Major, 9 Nit |

## Severity Breakdown (after deduplication)

| Severity | Count |
| --- | --- |
| Blocker | 1 |
| Major | 0 |
| Nit | 18 |

There were 23 raw findings. Four pairs reported the same problem and were merged, leaving 19 unique findings. A merged finding keeps both reviewers' ids. Each severity is the one the reviewer gave; none was changed.

## Prioritized Findings (Blockers -> Major -> Nits)

### A rules-file test contradicts `read_csv` and D16 - Severity: Blocker
* **Ids:** `egm-implementation-readiness-5-1`, `egm-codebase-details-5-1` (found independently by both)
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 670 (test_rules), 508-516 (`read_csv`), 643-651 (`load_rules`), 129 (D16), 124 (D11)
* **Discrepancy Description**:
  * Line 670 expects the rules row `,` (both cells blank) to warn `blank pattern`.
  * `csv.reader` turns `,` into `['', '']`.
  * `read_csv` (lines 511-512) silently drops every row whose cells are all blank after `strip()`, as D16 requires.
  * So `load_rules` never sees the row, no warning is printed, and the test fails when built exactly as specified.
  * To make it pass, the implementer must decide whether D16 or D11 governs all-blank rows in the rules file. That is a design decision. Synthesizer check: lines 508-516 and 670 confirm the contradiction.
* **Rationale & Recommendation**:
  * Keep D16, since `read_csv` is shared code.
  * Rewrite line 670 so a `,` (or `" , "`) row in a rules file is skipped silently, with no warning.
  * Test `blank pattern` with a row that is not all blank, such as ` ,Food`.
  * State once, at D11 or in item 10, that the `blank pattern` and `blank category` warnings apply only to rows with at least one non-blank cell.
  * If D11 should win instead, give `read_csv` a parameter that keeps all-blank rows and add an exception to D16. Choose one and state it.

### Subprocess end-to-end test does not set its working directory - Severity: Nit
* **Ids:** `egm-implementation-readiness-5-6`, `egm-codebase-details-5-4`
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 722-723, 777-778
* **Discrepancy Description**: The plan has no `pyproject.toml` and no install step. So `python -m txmerge` finds the package only when the child process runs from the repo root, or when the repo root is on `PYTHONPATH`. With `cwd=tmp_path` the test fails with `No module named txmerge`.
* **Rationale & Recommendation**: Pass `cwd=Path(__file__).resolve().parents[1]` and give every fixture as an absolute `tmp_path` path.

### D15 amount grammar does not define "digits" - Severity: Nit
* **Ids:** `egm-implementation-readiness-5-3`, `egm-codebase-details-5-5`
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 517-528 (`parse_amount`), 128 (D15)
* **Discrepancy Description**: If the check uses `\d` or `str.isdigit()`, it accepts non-ASCII digits (full-width or Arabic-Indic), and `Decimal()` parses them. The plan also leaves three cases implicit: the first thousands group must be 1-3 digits, and both a leading `.` (`.50`) and a trailing `.` (`1.`) are rejected.
* **Rationale & Recommendation**: Give the exact pattern, for example `re.fullmatch(r"(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]{1,2})?", body)`, after stripping an optional `[+-]` (allowed only when `signed=True`). Add tests showing `.50` and `1.` give `bad amount`.

### Raw or trimmed value and quoting in message text not pinned - Severity: Nit
* **Ids:** `egm-implementation-readiness-5-4`, `egm-codebase-details-5-6`
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 533-535, 553-555; Messages table 325-331; D14; D24
* **Discrepancy Description**: The tests at line 553 check exact warning text, but the plan does not pin these choices:
  * Whether `X` in `bad date 'X'` and `bad amount 'X'` is the trimmed cell or the raw cell.
  * Whether quotes are added with `f"'{x}'"` or `repr(x)`.
  * Which cell is named when both Debit and Credit fail (Debit or Credit checked first).
  * Whether the header in `unrecognised header:` lists trimmed or raw cells.
  * How `VALUE` in the D24 `got 'VALUE'` message is formatted.
* **Rationale & Recommendation**: State that Debit is checked first, that messages use the literal form `f"'{x}'"` with the trimmed cell, and that headers are shown as trimmed cells joined by `,`.

### `HEADER` has no stated type - Severity: Nit
* **Ids:** `egm-implementation-readiness-5-2`
* **Reviewer Lens:** `egm-implementation-readiness`
* **Affected Scope:** Lines 588, 598-600
* **Discrepancy Description**: `FORMAT_A` and `FORMAT_B` are given as lists, but `HEADER` is described only as "the output header from BRIEF.md". If it is a string, `writer.writerow` writes one character per cell.
* **Rationale & Recommendation**: Specify `HEADER = ["date", "account", "description", "amount", "category", "transfer_id"]`.

### No test pins the exact summary line or its counts - Severity: Nit
* **Ids:** `egm-implementation-readiness-5-5`
* **Reviewer Lens:** `egm-implementation-readiness`
* **Affected Scope:** Lines 730, 337-343
* **Discrepancy Description**: The tests check only that a summary is printed and that stdout is empty. A wrong R/S/D/T/W count would still pass.
* **Rationale & Recommendation**: Add one test_cli scenario with known counts: 1 blank line, 1 skipped data row, 1 skipped rule row, 1 duplicate and 1 transfer. Assert the exact stderr line.

### Order of same-file checks is not stated - Severity: Nit
* **Ids:** `egm-implementation-readiness-5-7`
* **Reviewer Lens:** `egm-implementation-readiness`
* **Affected Scope:** Lines 703-707
* **Discrepancy Description**: "For each input path and the rules path" does not give an order. The order decides which path a "cannot read" message names.
* **Rationale & Recommendation**: Check inputs in `--account` order, then the rules path, and stop at the first error or match.

### Ambiguous `datetime` import form - Severity: Nit
* **Ids:** `egm-codebase-details-5-2`
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Lines 504-505
* **Discrepancy Description**: The code `datetime.strptime(...)` and the return type `datetime.date` cannot both be right under one import style.
* **Rationale & Recommendation**: Specify `import datetime` and `datetime.datetime.strptime(text.strip(), fmt).date()`.

### Samefile test needs an existing `--out` - Severity: Nit
* **Ids:** `egm-codebase-details-5-3`
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Lines 739-741, 703
* **Discrepancy Description**: `samefile` is called only when `os.path.exists(args.out)` is true. Without an existing `--out` file, the monkeypatch is never reached and the run exits 0.
* **Rationale & Recommendation**: Add "with an existing `--out` file" to the test bullet.

### Fixtures containing commas must be quoted - Severity: Nit
* **Ids:** `egm-codebase-details-5-7`
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Lines 543, 545, 554; D15 (line 128)
* **Discrepancy Description**: Unquoted, `1,250.00` and `1,25.00` split into extra cells, so the result is `expected N cells, got M` instead of the intended parse or `bad amount`.
* **Rationale & Recommendation**: State that the fixtures quote these cells, or write the fixtures with `csv.writer`.

### "rules" used for two different things - Severity: Nit
* **Ids:** `egm-style-5-1`
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 759, 767
* **Discrepancy Description**: Elsewhere "rules" means the categorisation rules file. At these lines it means the design decisions D1-D24.
* **Rationale & Recommendation**: Say "decisions" or "the Decisions table (D1-D24)".

### Informal wording: "garbage there is fine" - Severity: Nit
* **Ids:** `egm-style-5-2`
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 546-547
* **Discrepancy Description**: The phrase is casual and does not say what the test checks.
* **Rationale & Recommendation**: Write "any value in Posting Date / Balance is ignored (D18)", or name the test input.

### Trimming sentence in the wrong bullet - Severity: Nit
* **Ids:** `egm-style-5-3`
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 527-528 (compare 516)
* **Discrepancy Description**: "Data cells are `strip()`ped before any parsing (D16)" ends the `parse_amount` bullet. A reader cannot tell whether `parse_amount` trims the cell or `read_export` trims it first.
* **Rationale & Recommendation**: Move the sentence into the `read_export` bullet, and state whether `parse_amount` also trims.

### Filler words - Severity: Nit
* **Ids:** `egm-style-5-4`
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 505 ("note"), 594 ("exact")
* **Discrepancy Description**: Both words add nothing.
* **Rationale & Recommendation**: Remove them.

### Unclear wording about `dest` - Severity: Nit
* **Ids:** `egm-style-5-5`
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 682-684
* **Discrepancy Description**: "the `dest` is required" reads as if `dest` were a required argument.
* **Rationale & Recommendation**: Write "Setting `dest` stops a missing sub-command from raising `TypeError`; argparse exits 2 instead."

### Jargon: "owned here" - Severity: Nit
* **Ids:** `egm-style-5-6`
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 710
* **Discrepancy Description**: "Categories (D8, owned here)" uses ownership jargon.
* **Rationale & Recommendation**: Write "Categories (D8; assigned in `main`, not in `rules` or `transfers`)".

### One section, three names - Severity: Nit
* **Ids:** `egm-style-5-7`
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 470, 488, 494, 535, 713; heading at 309
* **Discrepancy Description**: The same section is called "Messages table", "Messages section" and "Messages and exit codes".
* **Rationale & Recommendation**: Use one name throughout.

### Inconsistent punctuation and list format - Severity: Nit
* **Ids:** `egm-style-5-8`
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 697; lines 610-616, 621-627, 657-661, 666-672
* **Discrepancy Description**: Line 697 writes "3-9" with a hyphen where the rest of the document uses an en dash. The test lists for items 7, 8, 11 and 12 are run together with semicolons and slashes, which hides how many tests are expected.
* **Rationale & Recommendation**: Use an en dash. Put one test per bullet, as items 4 and 15 already do.

### Process signature at the end - Severity: Nit
* **Ids:** `egm-style-5-9`
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 782
* **Discrepancy Description**: "Drafted with the Elephant-Goldfish Model (EGM) design workflow" describes how the document was made, not the design.
* **Rationale & Recommendation**: Remove the line, or move it to document metadata.

## Verified Correct (per `egm-codebase-details` and `egm-implementation-readiness`)

* **Ledger write:** the `write_ledger` atomic-write sequence (`mkstemp` → `copymode` → `os.replace`, with cleanup in `finally`) and the 0o600 mode for new ledgers.
* **argparse:** `add_subparsers(dest=..., required=True)`, and `type=parse_account` raising `ArgumentTypeError`.
* **Monkeypatch targets:** `txmerge.cli.os.path.samefile` and `txmerge.ledger.os.replace` both resolve.
* **Decimal:** `-0.00` handling, `InvalidOperation` raised by `quantize` for a 40-digit amount, and equal dedup hashing of `0.00` and `-0.00`.
* **CSV reading and dates:** `utf-8-sig` with `newline=""`, `csv.Error` from the field-size limit, and `strptime` accepting unpadded day and month while rejecting `31/02/2026`.
* **Overall plan:** module import direction, phase checkpoints, and the D1-D24 coverage table.
