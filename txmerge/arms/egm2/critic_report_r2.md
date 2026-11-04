# Goldfish Review Report

**Target:** `arms/egm2/docs/designs/txmerge.md` (lines 1-465, everything before `## Detailed Implementation Plan`)
**Round:** Stage 7 Critic Review, egm-review-loop round 2
**Standard:** `resources/document_standards/feature-spec-standard.md` (egm-design, egm-structural); egm-style used its persona's own rules.

## Reviewer Status

| Reviewer | Status | Raw findings |
| --- | --- | --- |
| `egm-design` | completed | 10 (0 Blocker, 0 Major, 10 Nit) |
| `egm-structural` | completed | 10 (0 Blocker, 0 Major, 10 Nit) |
| `egm-style` | completed | 13 (0 Blocker, 2 Major, 11 Nit) |

## Severity Breakdown (after deduplication)

| Severity | Count |
| --- | --- |
| Blocker | 0 |
| Major | 2 |
| Nit | 29 |

Merges:
- `structural-2-3` was merged into `style-2-2`. Both cover the Messages "only place" claim, and the higher severity (Major) was kept.
- `structural-2-10` was merged into `style-2-13`. Both cover the wrapping at lines 225-226.

`design-2-10` and `style-2-9` both touch the Scale complexity line, but they make different points. They are kept separate and cross-referenced.

Overall, the reviewers agree on these points:
- The range meets the feature-spec standard.
- Every Decision row is consistent with BRIEF.md and the stakeholder log.
- The worked examples recompute correctly.
- All stakeholder citations match except the one in R1 (`style-2-1`).

## Prioritized Findings (Blockers -> Major -> Nits)

### style-2-1: R1 credits the stakeholder with a rationale they never gave - Severity: Major
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 450 (Risks, R1)
* **Discrepancy Description**: R1 reads "Accepted by the stakeholder (round 1, answer 5): the rule is easy to predict." Round 1 answer 5 in `stakeholder_log.md` (line 29) only states the greedy pairing rule. It says nothing about predictability and does not mention that the pairing is not optimal. The synthesizer checked this against the log. The designer's own opinion is presented as the stakeholder's reason.
* **Rationale & Recommendation**: A misattributed ruling weakens the traceability the document depends on. Separate the source from the opinion. For example: "Follows the stakeholder's pairing rule (round 1, answer 5). Both rows stay visible in the ledger." Either drop "the rule is easy to predict" or mark it as the designer's view.

### style-2-2: The "only place" and "single source of truth" claims are false, and neither says which table wins - Severity: Major
* **Reviewer Lens:** `egm-style` (merged with `structural-2-3`, which rated it Nit)
* **Affected Scope:** Lines 185, 311-313, 323-334, 133 (D20), 137 (D24)
* **Discrepancy Description**:
  * Line 311 says the Messages table "is the only place the message texts are defined". That is not true:
    * D20 (line 133) contains the literal `OUT: --out is also an input`.
    * D24 (line 137) contains the literal `--account must be NAME=PATH, got 'VALUE'`.
    * The REASON strings (lines 323-326) and the file-level MESSAGE strings (lines 328-334) are written as prose after the table, not inside it.
  * Line 185 calls the Decisions table "the single source of truth for behaviour".
  * Lines 312-313 say "those two tables win" but do not say which one wins when the two tables disagree.
  * PATH ("as given on the command line, after parse_account trimming") is defined twice, at line 323 and at lines 331-332.
  * The texts match today, so nothing is broken yet. The risk is that a later edit lets them drift apart.
* **Rationale & Recommendation**:
  * Make D20 and D24 point to the Messages subsection instead of repeating the strings. Otherwise, reword the "only place" claim so that it covers "this subsection".
  * State which table wins on message text.
  * Turn the REASON and MESSAGE paragraphs into lists or table rows.
  * Define PATH once.
  * Consider replacing "single source of truth" with "The Decisions table defines behaviour" (see `style-2-12`).

### design-2-1: The order of row-error checks, and so the warning REASON, is not defined - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Lines 127 (D14), 247-248, 323-326
* **Discrepancy Description**: One row can fail more than one check. Examples:
  * a bad date together with a bad amount;
  * Debit `abc` with Credit `25.00`;
  * Debit `0.00` with an unparseable Credit.

  The spec does not say which REASON is reported, so two correct implementations could print different warnings.
* **Rationale & Recommendation**: Fix the order of checks: cell count, then date, then each amount cell (zero counts as blank), then the both-blank / both-filled check. Report the first failure.

### design-2-2: The D24 message clashes with argparse formatting, and the program name is not set - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Lines 137 (D24), 321
* **Discrepancy Description**:
  * If validation uses argparse `type=` with `ArgumentTypeError`, stderr gets an `argument --account:` prefix in front of the D24 text.
  * `python -m txmerge` shows `__main__.py` as the program name, but every other message uses the `txmerge:` prefix.
* **Rationale & Recommendation**: Say that D24 is raised through `parser.error(...)` after parsing, or accept the prefix. Set `prog="txmerge"` explicitly.

### design-2-3: The NFR says the tool writes "only `--out`", but D23 also writes a temporary file - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Lines 440-442 vs 136 (D23), 456 (R7)
* **Discrepancy Description**: D23 creates a temporary file next to the target. A SIGKILL or a power loss before the rename leaves that file behind.
* **Rationale & Recommendation**:
  * Change the NFR to "writes only `--out` and a temporary file in its directory".
  * Name the temp-file pattern.
  * Add the leftover temp file to R7.

### design-2-4: Side effects of the atomic write are not listed as accepted risks - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Lines 136 (D23), 424-434 (Alternative J), 456 (R7)
* **Discrepancy Description**: Rename-into-place has costs that Alternative J does not list. Alternative J only names mode and symlinks. The missing costs are:
  * it needs write permission on the directory;
  * it silently replaces a read-only existing ledger;
  * it breaks hard links to the old ledger;
  * it does not keep ownership or ACLs.
* **Rationale & Recommendation**: Add one sentence to Alternative J or R7 that accepts these effects.

### design-2-5: An OSError from the same-file check has no defined outcome - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Lines 133 (D20), 126 (D13)
* **Discrepancy Description**: `os.path.exists` and `os.path.samefile` can raise `OSError`. As written, that would end in an uncaught traceback with exit 1.
* **Rationale & Recommendation**: Treat this case as `cannot write OUT: <error>` with exit 2.

### design-2-6: The `csv.Error` rule appears only under exports - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Lines 249-251
* **Discrepancy Description**: The rules file can also raise `csv.Error`, for example on a NUL byte or a field over the size limit. The spec does not say how that is handled.
* **Rationale & Recommendation**: State that the rule covers every file read, including `--rules`.

### design-2-7: "Whitespace" is not defined for normalisation and trimming - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Lines 114 (D1), 123 (D10), 129 (D16)
* **Discrepancy Description**: Whether NBSP and tabs count as whitespace changes which rows dedupe together.
* **Rationale & Recommendation**: Name the exact operation, for example `" ".join(s.split()).casefold()` and `s.strip()` with no arguments.

### design-2-8: Trimming rule patterns removes the only way to match whole words - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Lines 124 (D11), 85-86
* **Discrepancy Description**: Whole-word matching is a non-goal, so a padded pattern such as ` BP ` is the person's only workaround. D11 trims patterns, which removes it. D11 is a designer decision (E), and the trade-off is not recorded.
* **Rationale & Recommendation**: Either keep the spaces in patterns and trim only the category, or record the trade-off.

### design-2-9: G3 reads as unconditional, but greedy pairing leaves some qualifying rows unpaired - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Lines 65-67 (G3) vs 294, 450 (R1)
* **Discrepancy Description**: G3 says every qualifying pair is labelled `Transfer`. Under D7, some qualifying pairs are not linked.
* **Rationale & Recommendation**: Reword G3 as "...linked as transfers by the pairing rule D7 (each row in at most one transfer)" and reference R1.

### design-2-10: The quadratic worst case for pairing is not stated - Severity: Nit
* **Reviewer Lens:** `egm-design` (related to `style-2-9`)
* **Affected Scope:** Lines 344-349
* **Discrepancy Description**: Pairing is O(outflows × inflows of the same amount). Many repeated equal amounts make it close to quadratic.
* **Rationale & Recommendation**: Add one line saying the worst case is acceptable at the stated scale. Optionally, use date-sorted inflow lists with bisect.

### structural-2-1: Alternative G has no Pros or Cons - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** Lines 403-405
* **Discrepancy Description**: Alternative G is the only alternative without Pros and Cons. It has a Reason for Rejection only.
* **Rationale & Recommendation**: Add Pros, such as "matches when the money moves". Add Cons, such as "lags the purchase date, so more card payments fall outside the 3-day window".

### structural-2-2: "The Problem" section describes the solution - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** Lines 50-53
* **Discrepancy Description**: The pipeline summary repeats Technical Plan › Data flow (lines 190-217) inside the problem statement.
* **Rationale & Recommendation**: Move it to the Overview or the Technical Plan, or delete it. Re-wrap line 50.

### structural-2-4: An inline code span is broken across a line wrap - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** Lines 329-332
* **Discrepancy Description**: `` `cannot write PATH: <OS `` / `` error>` `` is split across a line break. It renders correctly, but the raw text is fragile.
* **Rationale & Recommendation**: Re-wrap so that no code span crosses a line break.

### structural-2-5: D13 and the Messages table group command-line errors differently - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** Lines 126 (D13), 320-321
* **Discrepancy Description**: D13, "File-level errors", lists a malformed `--account` and a missing option. The Messages table puts these under "Bad command line" with argparse usage output.
* **Rationale & Recommendation**: Rename D13 to "Run-stopping errors (exit 2)", or split the command-line cases into their own row.

### structural-2-6: The `### Rules` heading clashes with the rules-file concept - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** Line 110 (also 96, 107, 123-124)
* **Discrepancy Description**: The H3 "Rules" heads D1-D24, while "rules" also names the category-rules file.
* **Rationale & Recommendation**: Rename the H3 to "Product rules" or "Decision table".

### structural-2-7: Code fences are labelled inconsistently - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** Lines 21-25, 196
* **Discrepancy Description**: The usage block has no language tag. The data-flow block uses `text`.
* **Rationale & Recommendation**: Tag both blocks consistently.

### structural-2-8: G4's bold label is formatted differently from the other goals - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** Line 68 (G4, within 57-74)
* **Discrepancy Description**: G4 bolds part of a sentence. The other goals use a bold title that ends with a period.
* **Rationale & Recommendation**: Use "**G4 – Everything else categorised.** Each other row gets...".

### structural-2-9: Section names differ from the standard's labels - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** Lines 32, 183
* **Discrepancy Description**: The standard says "Problem Statement" and "Proposed Architecture". The document says "The Problem" and "Technical Plan (Architecture)". The standard's labels are non-exhaustive examples.
* **Rationale & Recommendation**: Optionally rename the sections to match the standard.

### style-2-3: Filler adverbs - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 35, 36, 42, 122
* **Discrepancy Description**: "Naively" and "simply" add tone but no meaning.
* **Rationale & Recommendation**: Drop them. For example: "Concatenating them double-counts" and "Past 9999 the number gets longer".

### style-2-4: An editorial aside sits inside a worked example - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 294
* **Discrepancy Description**: "Expected, not a bug." defends the design inside an examples table.
* **Rationale & Recommendation**: Remove it, or replace it with "See R1."

### style-2-5: Alternatives use subjective, unmeasured judgements - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 355, 373, 382-383, 399, 412
* **Discrepancy Description**: The section uses "One line of code", "hard to predict", "harder to explain and predict", "readable" and "exact".
* **Rationale & Recommendation**: State the concrete property instead. Examples: a threshold dependency, a pair that changes when an unrelated row is added, 5+ character ids against 64-character hashes, and decimal values with no binary rounding.

### style-2-6: Alternative I repeats one point - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 417-422
* **Discrepancy Description**: The Cons and the Reason for Rejection both say "where each rule lives".
* **Rationale & Recommendation**: Keep the point once, in the Reason for Rejection.

### style-2-7: Alternative J makes an absolute "only" claim - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 432-434
* **Discrepancy Description**: "Only the temporary-file-and-rename write keeps that promise" cannot be proven. Backup-and-restore is another way.
* **Rationale & Recommendation**: Remove "Only".

### style-2-8: "Inputs are never modified" is stated twice - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 133 (D20), 225-226
* **Discrepancy Description**: Lines 187-188 say the Technical Plan cites rules by number instead of repeating them, but this rule is restated at lines 225-226.
* **Rationale & Recommendation**: Reduce lines 225-226 to a citation of "(D20)".

### style-2-9: The complexity wording is imprecise - Severity: Nit
* **Reviewer Lens:** `egm-style` (related to `design-2-10`)
* **Affected Scope:** Lines 348-349
* **Discrepancy Description**: The text says "linear in rows times the number of inflows sharing one amount", but a product of those two is not linear.
* **Rationale & Recommendation**: Write "O(n × k), where k is the largest number of inflows sharing one amount".

### style-2-10: "Appear twice" understates the overlap case - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 12-13
* **Discrepancy Description**: A row can appear in three or more exports. G1 describes the general max-count rule.
* **Rationale & Recommendation**: Write "removes the extra copies of rows that appear in more than one export".

### style-2-11: A Brief section is named wrongly - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 375
* **Discrepancy Description**: The text says "`BRIEF.md` goal 1", but the Brief has no goals list. The item is "What I want" 1.
* **Rationale & Recommendation**: Write "`BRIEF.md` 'What I want' item 1".

### style-2-12: "Single source of truth" is a stock phrase - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 185
* **Discrepancy Description**: Mild jargon. It overlaps with `style-2-2`.
* **Rationale & Recommendation**: Write "The Decisions table defines behaviour."

### style-2-13: Line wrapping is inconsistent - Severity: Nit
* **Reviewer Lens:** `egm-style` (merged with `structural-2-10`)
* **Affected Scope:** Lines 50, 225-226, 323, 331-332
* **Discrepancy Description**: These lines break the ~80-column wrap. At lines 225-226, "`--out` can never be one" breaks early.
* **Rationale & Recommendation**: Re-wrap to the document's column width.
