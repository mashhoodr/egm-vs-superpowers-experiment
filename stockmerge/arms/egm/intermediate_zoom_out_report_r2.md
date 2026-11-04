# Goldfish Review Report

**Target:** `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers-p2/arms/egm/docs/designs/stockmerge.md` (`1-899`)
**Stage:** 8, Intermediate Zoom Out Review, re-audit round 2
**Context:** `BRIEF.md` (fixed owner contract), Stage 5 `zoom_out_report.md`

## Reviewer Status

| Reviewer | Status |
| --- | --- |
| `egm-zoom-out` (instance A) | completed |
| `egm-zoom-out` (instance B) | completed |

**Severity counts (deduplicated):** 0 Blocker, 4 Major, 5 Nit.

When the two instances gave different severities, this report uses the higher one and notes the split.

**Verdict, both instances:** the design passes with changes. It still fixes the root problem and stays inside the BRIEF. The round-2 additions need trimming, not reversing.

## Prioritized Findings (Blockers -> Major -> Nits)

### zoom-out-8b-1: Bisect move matching is a premature optimisation - Severity: Major
* **Reviewer Lens:** `egm-zoom-out` (A: Major, B: Major)
* **Affected Scope:** Lines 608-613 (NFR Performance), 753-761 (`moves.py` plan), 594 (Risks row)
* **Discrepancy Description**:
  * The spec itself calls the 100,000-row size "assumed (not measured)". The BRIEF gives no size.
  * Grouping by `(sku_norm, qty_each)` already keeps each group small.
  * Bisect adds a parallel sorted list of minute times per group and two boundary calls.
  * That is a second place where the inclusive 120-minute rule (R6.1) can be off by one.
  * B: the stated cost claim, "the number of such positives", is inaccurate. Positives already used in a move stay in the window and are still scanned.
* **Rationale & Recommendation**:
  * Keep the grouping.
  * Inside each group, use a plain filter: within 120 minutes, not used, different location, then the minimum by the R6.2 key.
  * Remove the bisect sentences from the NFR.
  * Shrink risk row 594 to "all rows are held in memory".

### zoom-out-8b-2: Decision tags mark builder choices as [contract], and Stage 5 item 1-8 is half done - Severity: Major
* **Reviewer Lens:** `egm-zoom-out` (A: Major, B: Nit; the higher severity is reported)
* **Affected Scope:** Lines 101-105 (tag definitions), 240-246 (R1.1), 283-284 (R3.1), 312-319 (R4.2), 596 (Risks row), 390-391 (R6.3), 90-94 (Open Questions), 323-324 and 332/335 (R4.3, R4.6), 892-893 (Verification Plan)
* **Discrepancy Description**:
  * A [contract] tag means the owner cannot overrule the rule. Several [contract] spans are not in the BRIEF:
    * R1.1: the argparse message format, and `--help` on stdout.
    * R3.1: removing a BOM and trimming header cells.
    * R4.2: a zero-byte or blank-only file gives exit 2, plus the `no valid rows` warning.
  * Risk row 596 says the owner decided R4.2. That contradicts the rule's own tag.
  * R6.3 departs from the BRIEF's "Everything categorised by my rules", because moves get `Move`. It still has only an [owner] tag, with no inline quote of the owner's answer.
  * Open Questions still points to files that a reader who has only the BRIEF cannot see.
  * B: the convention that a tag covers text up to the next tag gives odd results:
    * R4.6 carries `[builder]` twice.
    * R4.3 switches from builder to owner in the middle of a sentence.
  * B: lines 892-893 require "a test per [owner]/[contract] rule". That implies [builder] rules need no tests.
* **Rationale & Recommendation**:
  * Retag the builder parts of R1.1, R3.1 and R4.2 as [builder], and make row 596 match.
  * Add a one-line owner quote at R6.3 (and at G2).
  * Use one tag per bullet.
  * Change line 892 to "at least one test per rule ID".
  * Both instances agree the tags themselves are worth keeping.

### zoom-out-8b-3: The feature spec (lines 1-631) has slipped into implementation detail - Severity: Major
* **Reviewer Lens:** `egm-zoom-out` (A: Nit, B: Major; the higher severity is reported. Stage 5 rated this zoom-out-1-7 as a Nit.)
* **Affected Scope:**
  * Goal G5, lines 56-61, and messages table row 433: Python exception classes.
  * Glossary, lines 114 and 119: `str.strip()`.
  * Line 207 and R9.3, lines 420-422: `os.replace`.
  * R4.1, line 304: `utf-8-sig`.
  * R4.3, line 320: `csv.reader`.
  * R4.8, lines 343-345: Python integer conversion.
  * R4.9 and R6.1, lines 348 and 384-385: constant names.
  * R8.1, lines 410-412: "plain Python `str` order".
  * R2.2, lines 271-275: how the OS decides two paths are one file.
  * R4.12 and Alternative K, lines 353-360 and 568-579: csv quoting mechanics.
  * NFR, lines 608-613: algorithm detail.
* **Discrepancy Description**:
  * The core R-rules still describe behaviour.
  * Almost every round-2 addition pushed mechanisms into the Goals, the NFR and the rules.
  * That makes the spec harder for the owner to check, and ties it to one implementation.
* **Rationale & Recommendation**:
  * The spec should state behaviour. The Detailed Implementation Plan should name the calls.
  * Example rewrites:
    * G5: "No file, argument or file-system problem ends in a traceback; each is a warned skip (exit 0) or exit 2."
    * R2.2: "`--out` must not be the same file as any input or the rules file."
    * R9.3: "`--out` is replaced only once the new file is complete."
    * R8.1: "code-point order, independent of locale".
  * Drop the algorithm sentence from the NFR.

### zoom-out-8b-4: Invalid-UTF-8 row skipping is over-built - Severity: Major
* **Reviewer Lens:** `egm-zoom-out` (B: Major, A: Nit; the higher severity is reported)
* **Affected Scope:** Lines 304-311 (R4.1), 433-436 (messages table), 60 (G5), 677-682 and 725-727 (plan); Non-Goals 84-85
* **Discrepancy Description**:
  * The BRIEF says nothing about encoding, and the Non-Goals already say only UTF-8 is supported.
  * R4.1 adds a lot of code for one stray byte:
    * `surrogateescape` decoding
    * a check of every field
    * a separate exception for the Format B `note`
    * a second copy of the handling for the rules file
    * two overlapping header rows in the messages table (434, 436)
  * A: a bad byte in a time, quantity or unit field already fails that field's own check (R4.5-R4.9). Only the SKU could pass a bad byte through unnoticed.
  * B: the earlier strict decode (exit 2 naming the file) was simpler. It also loses no scan, because the run stops visibly.
* **Rationale & Recommendation**:
  * B, preferred: go back to strict decoding. Invalid UTF-8 gives exit 2 with the path and line. Record it as an accepted limit in Risks & Limits.
  * A, the alternative if skipping stays: limit the check to the SKU ("a row whose SKU is not valid UTF-8 is skipped with a warning; other fields fail their own checks").
  * Either way:
    * drop the note exception
    * drop the field-by-field check
    * fold rows 434 and 436 into the existing "header unknown" rows.

### zoom-out-8b-5: R4.12 (one line per record) is justified, but its supporting text contradicts itself - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A: Nit, B: Nit)
* **Affected Scope:** Lines 224 and 439-440 ("first physical line"), 353-360 (R4.12), 687-689 vs 728-730 (line reader described twice), 789 (`csv.field_size_limit(2**31 - 1)`), 797-798 (backstop example), 826 (test)
* **Discrepancy Description**:
  * Both instances say the rule is needed. Without it, one unclosed quote in a free-text note swallows every later scan, which breaks BRIEF goal 1.
  * The supporting text has not caught up:
    * Lines 224 and 440 still say "first physical line", and the plan's reader still yields a "(start line, fields)" pair. Both date from when a record could span lines.
    * Line 360 says "no field size limit". Line 789 raises the csv limit, which makes the backstop's "field over the csv size limit" example (797-798) impossible.
    * The test at 826 uses a 5,000-character field, far below the 131,072-character default, so it tests nothing.
    * The line reader is described twice.
* **Rationale & Recommendation**:
  * Drop the `field_size_limit` call and the "no field size limit" sentence.
  * Keep the backstop example, which now holds again.
  * Write "line" instead of "first physical line" and "start line".
  * Describe the reader once, as `iter_records`.
  * Remove or fix the 5,000-character test.

### zoom-out-8b-6: The R2.2 same-file check uses two methods where one is enough - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A: Nit, B: Nit)
* **Affected Scope:** Lines 269-279 (R2.2), 261 (R1.5)
* **Discrepancy Description**:
  * The check is needed: without it, `os.replace` destroys an input.
  * The path comparison is redundant:
    * If `--out` does not exist, it cannot be an input.
    * If it exists, the OS same-file test alone covers symlinks, case-insensitive disks and hard links.
  * The fallback "if that check itself fails, the paths count as different" is one more branch to specify and test.
  * B: the hard-link reasoning is wrong. All reading finishes before writing, and replacing the `--out` name leaves the other linked name pointing at the original data.
* **Rationale & Recommendation**:
  * Reduce R2.2 to: "if `--out` exists and the OS reports it is the same file as any input or the rules file, exit 2".
  * Drop the path comparison, the fallback and the hard-link reasoning.

### zoom-out-8b-7: Risks & Limits restates rules and has rows with no basis - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A: Nit, B: Nit)
* **Affected Scope:** Lines 583-598
* **Discrepancy Description**:
  * Most rows record real accepted trade-offs.
  * Rows 590, 591, 597 and 598 restate R1.4, R4.12, R2.2 and R9.3 rather than any remaining risk. A named 597-598 and B named all four.
  * B: row 593 (spreadsheet formula injection) has no basis in the BRIEF and is accepted anyway, so it tells the reader nothing.
  * A: the "Decided by" column repeats the tags and has already drifted from them (row 596, see 8b-2).
* **Rationale & Recommendation**:
  * Keep only the rows that record an accepted trade-off.
  * Drop the restating rows and row 593.
  * Either drop the "Decided by" column or keep it strictly in sync with the tags.

### zoom-out-8b-8: Stage 5 findings still open - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A: Nit, B: Nit)
* **Affected Scope:** Lines 261-262 (R1.5), 295-300 (R3.4 warning, R3.5), 201 and 231 (diagram step 7), 655-659 (`ident`/`input_order`), 663 and 793-794 (`Warnings`), 767-770 (`build_rows`), 224 (`Scan.path`/`Scan.line`)
* **Discrepancy Description**:
  * **1-3:** the R1.5, R3.4 and R3.5 warnings still have no owner confirmation. The R4.2 warning is now justified by row 596 and is no longer flagged.
  * **1-4:** `writer.build_rows` still categorises and sorts, while the diagram shows those as their own steps 7 and 8. `ident` and `input_order` still return the same tuple.
  * **1-5:** the instances disagree.
    * B says it is resolved: `Warnings` prints at once and keeps a count.
    * A says one overlap remains: line 663 says `Warnings` collects the strings, but lines 793-794 say `main` prints them.
  * **1-6:** `Scan.path` and `Scan.line` are still unused after step 4.
* **Rationale & Recommendation**:
  * Move R1.5, the R3.4 warning and R3.5 to Future Improvements, or record the owner's yes.
  * Give categorising its own function called from `cli.main`.
  * Keep only one of `ident` and `input_order`.
  * Make line 663 say that `Warnings.add` writes immediately and keeps only a count.
  * Drop `Scan.path` and `Scan.line`.

### zoom-out-8b-9: R1.2's invalid-byte clause and a fixed summary wording go beyond the BRIEF - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (B only)
* **Affected Scope:** Lines 248-251 (R1.2), 448-449 (summary wording)
* **Discrepancy Description**:
  * Rejecting a location name with invalid bytes guards an edge case no owner will hit.
  * Fixing the summary wording "so scripts can parse it" builds for a consumer the BRIEF never mentions.
* **Rationale & Recommendation**: Optional:
  * drop the R1.2 clause and let the G5 backstop cover it
  * do not test the summary wording as a contract.

## Not Flagged (both instances)
* R4.12, one line per record: needed for BRIEF goal 1. Only its leftover text is flagged (8b-5).
* R2.2, `--out` must not be an input: needed. Only the redundant method is flagged (8b-6).
* Decision tags and the Risks & Limits section: worth keeping. Only the labels and the restating rows are flagged.
* Resolved since Stage 5:
  * 1-1: the G5 backstop is now in `main`.
  * 1-2: the R2.1 pre-checks are gone.
* Owner-settled and not reopened: R5.4, R6.2, R6.3 and R6.5; grouping by (normalised SKU, quantity); writing a temp file and then replacing `--out`.

---
## Resolution (Elephant, egm-resolve rules)
- zoom-out-8b-1 (Major): PROPOSE FIX. Churn noted: bisect was the round-5 fix for design-5-1.
  Resolved both by removing bisect *and* the unmeasured 100,000-row claim that design-5-1 objected
  to: plain per-group filter, NFR states cost = size of the (SKU, qty) group, Risks row updated.
- zoom-out-8b-2 (Major, A): PROPOSE FIX. R3.1/R4.2 split into [contract] + [builder]; Risks row
  reworded; R6.3 quotes the owner's answer.
- zoom-out-8b-3 (Major, B): PROPOSE FIX (part). Exception class names removed from G5; `os.replace`,
  `utf-8-sig`, the constant name removed from the feature spec. CONTEST (part): the Glossary's
  `str.strip()` and the accepted value shapes stay because tests depend on their exact meaning.
- zoom-out-8b-4 (Major, B): CONTEST with document evidence: both simpler options were reviewed and
  rejected (exit 2 loses the run — critic round 3 design-3-3; skip-any-field loses a real scan —
  critic round 4 egm-design-4-1). Evidence added as Alternative L so a reviewer can check it.
- Nits: declined.
