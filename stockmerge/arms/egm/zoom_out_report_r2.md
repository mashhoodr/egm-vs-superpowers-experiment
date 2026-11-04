# Goldfish Review Report

**Target:** `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers-p2/arms/egm/docs/designs/stockmerge.md` (`1-735`)

**Mode:** REVIEW, Stage 5 (Initial Zoom Out Review), re-audit round 2
**GoldfishContext:** `BRIEF.md` (the owner's fixed contract)
**Instances:** two independent `egm-zoom-out` reviewers (A and B), merged and deduplicated

## Reviewer Status

| Reviewer | Status |
| --- | --- |
| `egm-zoom-out` | completed (instances A and B both completed; no retries needed) |

## Summary

- Verdict from both instances: **PASS**
- Blockers: **0**
- Majors: **0**
- Nits: **12**

Both instances confirmed these points:
- The context is sufficient.
- All four "What I want" items in the brief map to G1-G4, and the fixed contract is kept.
- The design is one linear pipeline of pure functions, with I/O only in the CLI.
- It uses only the standard library (argparse, csv, dataclasses, tempfile, os.replace).
- Out-of-scope items (`--strict`, totals) sit correctly under Future Improvements.
- Grouping positives by `(sku_norm, qty_each)` is a natural index, not a premature optimisation.
- G6 (temporary file plus `os.replace`) and R2.2 (`--out` must not equal an input) earn their small cost.

## Prioritized Findings (Blockers -> Major -> Nits)

No Blockers.

No Majors.

### zoom-out-2-1: The Non-Goals wording contradicts the move rule and the near-duplicate warning - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A, B)
* **Affected Scope:** `Lines 61-63` against G2 (`41-42`), R6.1 (`311-315`) and R1.4 (`217-222`)
* **Discrepancy Description**: Line 61 lists "Dedup or SKU matching across different location names" as a non-goal. Move linking (G2) is exactly SKU matching across different location names. Line 63 rules out "fuzzy matching of location names", yet R1.4's near-duplicate location-name warning is a light form of fuzzy comparison.
* **Rationale & Recommendation**: A fresh reader sees non-goals that seem to rule out a core goal and an existing rule. The rules section settles it. Reword line 61 to "Dedup across different location names". Reword line 63 to "No fuzzy matching of location names (a near-duplicate warning only)".

### zoom-out-2-2: The empty-file rules and the implementation plan disagree - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A, B)
* **Affected Scope:** `Lines 160`, `262-263` (R4.2), `540-542`, `549-550`
* **Discrepancy Description**: R4.2 gives exit 2 only for a zero-byte file, and a warning that a header-only file "is empty". The diagram says "empty file -> exit 2". `read_export` also exits 2 for a blank-lines-only file. It warns "no valid rows" whenever no scans result, which also fires when every data row was skipped.
* **Rationale & Recommendation**: The tests check against rule IDs (line 203), so having two sources of truth invites drift. State the blank-lines-only case and a single warning condition and wording in R4.2. Have `readers.py` cite R4.2 rather than restate it.

### zoom-out-2-3: Two helpers for the same identity tuple - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A, B)
* **Affected Scope:** `Lines 197-198`, `518-523`
* **Discrepancy Description**: `Scan.ident` and `input_order(s)` both return `(arg_index, record_no)`.
* **Rationale & Recommendation**: Keep one name (`ident`). Use it as both the move-map key and the input-order tie-breaker.

### zoom-out-2-4: The messages table lists the same R9.3 failure twice - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A, B)
* **Affected Scope:** `Lines 360` and `365`
* **Discrepancy Description**: "`--out` folder missing or not writable (R9.3)" and "Writing the output fails (R9.3)" are one failure path: creating or writing the temporary file fails, the tool exits 2, and `--out` is untouched.
* **Rationale & Recommendation**: Merge them into one row.

### zoom-out-2-5: Code-level detail in the implementation plan (altitude) - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A, B)
* **Affected Scope:** `Lines 503`, `521`, `545-548`, `560-564`, `613-616`, `721`
* **Discrepancy Description**: The plan includes implementation choices: `__all__ = []`, the `normalise_sku` one-liner, the `line_num + 1` arithmetic, the "first 19 characters" slice in `parse_iso_naive`, the `to_minute` / `dt.replace(...)` body, the full `NamedTemporaryFile` keyword list and the `.gitignore` contents.
* **Rationale & Recommendation**: This is acceptable in a "Detailed" section and does not affect the design. It does lock in choices the R-rules already pin down by behaviour, and it makes zoom-out-2-2 worse. Optional fix: keep signatures, data flow and R-ID references, and drop the function bodies.

### zoom-out-2-6: Step 7 (categorise) is drawn as its own stage but runs inside the writer - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A)
* **Affected Scope:** `Lines 169`, `197-199` against `609-612`
* **Discrepancy Description**: The diagram and the record-type text show categorise as a separate step that returns a category per scan. The file plan has `writer.build_rows` call `categorise` while it sorts, so `writer.py` depends on `rules.py`.
* **Rationale & Recommendation**: The stated architecture and the place the logic lives do not match (Standard section 3, Right Placement). Either compute categories in `cli.main` and pass them to the writer, or redraw the diagram with steps 7 and 8 merged.

### zoom-out-2-7: `Scan.path` and `Scan.line` have no consumer (YAGNI) - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (B)
* **Affected Scope:** `Lines 184`, `191`, `518-520`
* **Discrepancy Description**: The fields are justified "for warnings". Every row-level warning, though, is raised inside `read_export` before a `Scan` exists (lines 545-549). No later step emits a row-level warning.
* **Rationale & Recommendation**: Drop both fields, or name the step that reads them.

### zoom-out-2-8: The `Warnings` class conflicts with how the CLI prints warnings - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (B)
* **Affected Scope:** `Lines 527-529` against `633-634`
* **Discrepancy Description**: `model.py` says `Warnings` "collects warning strings in order". `cli.py` says each warning is printed "as it is collected". These two cannot both be true, and a class that only formats `PATH:LINE: reason` is heavier than it needs to be.
* **Rationale & Recommendation**: Pick one behaviour. The simplest is a `warn(path, line, reason)` callable that prints straight to stderr and bumps a counter for the summary line. The alternative is to state that warnings are buffered and printed before the summary.

### zoom-out-2-9: "Nothing is printed to stdout" conflicts with `--help` - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A)
* **Affected Scope:** `Line 373` against `725`
* **Discrepancy Description**: argparse's `--help` prints to stdout, and the Verification Plan uses `--help`.
* **Rationale & Recommendation**: Qualify the rule with "during a merge run" or "except `--help`".

### zoom-out-2-10: The summary counts are not defined, so G5 cannot be checked - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A)
* **Affected Scope:** `Lines 47-48` (G5), `372`
* **Discrepancy Description**: G5 says every data row is written, removed or skipped. The summary line prints R, D, S, M and W, but never defines R or states R = W + D + S.
* **Rationale & Recommendation**: State the equation. That makes G5 testable from the summary line alone.

### zoom-out-2-11: A known limit of the owner's dedup rule is not recorded - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (B)
* **Affected Scope:** `Lines 39-40` (G1), `294-303` (R5.x); brief item 1, "never lose a real scan"
* **Discrepancy Description**: Suppose both scanners genuinely count the same SKU and quantity at the same location in the same minute. Their rows share a scan key, so R5.4 collapses them into one row and a real scan is lost. The design records the matching trade-off for greedy matching (R6.5) but does not record this one.
* **Rationale & Recommendation**: The rule is `[owner]`-settled, so do not change it. Add an R5.x note in the style of R6.5 that records the accepted limit, so the owner can see it.

### zoom-out-2-12: The R3.5 reserved-category warning is the weakest extra - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (B)
* **Affected Scope:** `Lines 249-251` (R3.5)
* **Discrepancy Description**: The warning about rule categories named `Move` or `Uncategorised` guards against a speculative misuse, and it adds code and tests. R1.4 and R1.5, by contrast, earn their place.
* **Rationale & Recommendation**: Optional. Drop R3.5, or keep it as an accepted small cost.

## Not Checked

- Neither instance could verify the `[owner]` attributions or the "None are open" statements (lines 76-79, 203-204, 485-487). `concepts_brief.md` and `stakeholder_log.md` were outside the allowed inputs. Both instances treated the tagged rules as owner-settled. Each decision is restated inline, so this does not block understanding. Make sure those files ship next to the design.
- Reuse search (Standard section 4) was not applicable, because the repo is greenfield.
