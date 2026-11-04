# Goldfish Review Report

**Target:** `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers/arms/egm2/docs/designs/txmerge.md` (`Lines 1-465`, FeatureRange before `## Detailed Implementation Plan`)

**Round:** Stage 7 Critic Review, egm-review-loop round 4

## Reviewer Status

| Reviewer | Status |
| --- | --- |
| `egm-design` | completed |
| `egm-structural` | completed |
| `egm-style` | completed |

## Severity Breakdown

| Severity | Count |
| --- | --- |
| Blocker | 0 |
| Major | 1 |
| Nit | 20 |

Duplicates merged:
* `structural-4-5` was merged into `style-4-1`.
* `structural-4-7` was partly merged into `style-4-2` (line 225 wrap).
* `structural-4-4` was merged into `style-4-3` (lines 331-332).

Both the design and the structural reviewers found every required section of the feature-spec standard present. The design reviewer found no contradictions with BRIEF.md or stakeholder_log.md.

## Prioritized Findings (Blockers -> Major -> Nits)

### style-4-1: The Messages section claims to be the only place message texts are defined, but other sections also define them - Severity: Major
* **Reviewer Lens:** `egm-style` (also raised as `structural-4-5`)
* **Affected Scope:** Lines 311-314. Contradicted by lines 127 (D14), 128 (D15), 133 (D20), 181 (CUJ 5) and 251.
* **Discrepancy Description**: Lines 311-314 say this section is "the only place message texts are defined" and that the sections "cannot disagree". Other lines contain literal message text anyway:
  * D15 (line 128) quotes `expected N cells, got M`.
  * D14 (line 127) uses `bad amount`.
  * D20 (line 133) paraphrases the "--out is also an input" and "cannot read" messages.
  * CUJ 5 (line 181) gives a literal REASON.
  * Line 251 defines its own text for a `csv.Error`: `cannot read PATH: <error>`. The Messages list at line 329 gives `cannot read PATH: <OS or decode error>`, and that placeholder does not cover a CSV parse error.

  The synthesizer checked these lines. Lines 251 and 329 already disagree in wording, which shows the "cannot disagree" guarantee is false as written.
* **Rationale & Recommendation**:
  * At line 251, refer to the message by name instead of restating it.
  * Widen the line 329 placeholder to `<OS, decode or CSV error>`.
  * Then do one of the following:
    * Remove the literal strings from D14, D15, D20 and CUJ 5.
    * Or reword lines 311-314 so the Messages table is authoritative and other sections quote it, and delete "so they cannot disagree".

### design-4-1: Temp-file cleanup only covers `OSError` - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Lines 136 (D23), 72-74 (G6) and 456 (R7)
* **Discrepancy Description**: D23 removes the temp file only when an `OSError` occurs. Any other exception leaves a stray temp file and ends with a traceback and exit 1. Examples are `KeyboardInterrupt`, or a `UnicodeEncodeError` when NAME contains surrogate-escaped characters taken from non-UTF-8 argv bytes. This sits badly with G6's "clear failures".
* **Rationale & Recommendation**:
  * Clean up the temp file in a `finally` block.
  * State whether G6 covers unexpected exceptions.
  * Optionally, treat a NAME that cannot be encoded as a usage error in D24.

### design-4-2: The costs of the atomic rename write are not fully recorded - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Lines 136 (D23), 424-434 (Alternative J) and 456 (R7)
* **Discrepancy Description**: The doc does not record what a rename-based replacement gives up:
  * Hard links to the old file are cut.
  * Owner, group, ACLs and extended attributes are lost.
  * The write needs write permission on the directory. If the file is writable but its directory is not, the run exits 2 with "cannot write".
  * A SIGKILL leaves the temp file behind.
* **Rationale & Recommendation**: List these as accepted costs in D23, R7 or Alternative J.

### design-4-3: Transfer pairing is quadratic in the worst case, and the Scale section does not say so - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Lines 276-283 and 344-349
* **Discrepancy Description**: When many rows share one amount, pairing is O(n^2). At the 50,000-row ceiling that is about 6x10^8 checks, which takes minutes. The Scale section says "No performance work is planned" and does not mention this.
* **Rationale & Recommendation**: Use `bisect` on the date-ordered inflow list to limit each search to the ±3-day window. Alternatively, record the quadratic worst case as an accepted risk.

### design-4-4: The order in which files are checked is not stated - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Lines 126 (D13), 196-226 and 316-334
* **Discrepancy Description**: The doc does not say whether the rules file or the exports are read first, or that the run stops at the first bad file. When several files are bad, stderr is therefore not reproducible.
* **Rationale & Recommendation**: Add one sentence giving the order, for example: "rules first, then exports in `--account` order; the first file-level error stops the run; warnings already printed stay printed."

### design-4-5: The doc does not say that a blank description is valid - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Lines 127 (D14) and 236
* **Discrepancy Description**: The D14 check list implies that a blank description is accepted and the row comes out `Uncategorised`, but the doc never says so. An implementer might add a rejection check of their own.
* **Rationale & Recommendation**: Add "a blank description is valid" to D14 or D16.

### design-4-6: "stdout stays empty" does not account for argparse; the subcommand is not marked required - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Lines 135 (D22) and 322
* **Discrepancy Description**: `--help` prints to stdout. The doc also does not say what happens when the `merge` subcommand is missing, and argparse subparsers are optional by default.
* **Rationale & Recommendation**: Limit D22 to merge runs, and state `required=True` for the subcommand so a missing one exits 2.

### structural-4-1: The Problem section contains a solution summary - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** Lines 50-53
* **Discrepancy Description**: The paragraph starting "The proposed solution is..." sits in The Problem. Line 50 also exceeds the ~80-column wrap.
* **Rationale & Recommendation**: Move the paragraph to Overview or to the start of the Technical Plan, and re-wrap it.

### structural-4-2: Alternative G has no Pros or Cons - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** Lines 403-405
* **Discrepancy Description**: Every other alternative has Pros, Cons and a Reason for Rejection. G has only the Reason for Rejection.
* **Rationale & Recommendation**: Add short Pros and Cons, or note that G is intentionally brief.

### structural-4-3: Code fence language tags are inconsistent - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** Lines 20 and 196
* **Discrepancy Description**: The fence at line 20 has no language tag. The fence at line 196 uses `text`.
* **Rationale & Recommendation**: Tag line 20 as `text` or `sh`.

### structural-4-6: Cross-references are plain text and one heading name does not match - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** Lines 180, 248 and 443
* **Discrepancy Description**: "Messages table", "see Messages" and "Technical Plan › Scale" are plain text, not links. The actual heading is "Messages and exit codes".
* **Rationale & Recommendation**: Use anchor links whose text matches the heading names.

### structural-4-7: Uneven line wrapping - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** Lines 225-226 and 324
* **Discrepancy Description**: Line 225 breaks early. Line 324 is one very long line.
* **Rationale & Recommendation**: Re-wrap both to about 80 columns.

### style-4-2: The Technical Plan says it cites rules by number, then restates them - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 187-188, compared with 222-226 and 305
* **Discrepancy Description**: The Technical Plan restates D13/D23, the `-0.00` rule from D17, and the input-safety point that D20 already makes at line 133.
* **Rationale & Recommendation**: Drop the restatements, or soften the claim at lines 187-188. Delete the duplicate sentence at lines 225-226.

### style-4-3: The `--out` placeholder is inconsistent, and the D24 trimming claim is wrong - Severity: Nit
* **Reviewer Lens:** `egm-style` (also raised as `structural-4-4`)
* **Affected Scope:** Lines 324 and 331-332
* **Discrepancy Description**:
  * The cannot-write message uses `PATH (--out)`, while the same-file message uses `OUT`.
  * Line 324 says D24 trimming applies to every path. D24 trims only `--account` values.
  * The code span `cannot write PATH: <OS error>` is split across a line break.
* **Rationale & Recommendation**:
  * Write `cannot write OUT: <OS error>` and keep the code span on one line.
  * Reword line 324 so that the D24 trimming applies only to `--account` paths.

### style-4-4: Filler adverbs - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 35, 37, 42 and 122
* **Discrepancy Description**: "Naively" appears twice and "simply" twice; neither adds meaning.
* **Rationale & Recommendation**: Delete them.

### style-4-5: Editorial aside in the worked example - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 294
* **Discrepancy Description**: "Expected, not a bug." is a defensive aside.
* **Rationale & Recommendation**: Replace it with "See R1."

### style-4-6: Alternative I repeats a phrase and uses subjective wording - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 417-422
* **Discrepancy Description**: "Where each rule lives" appears twice. "Obvious" is subjective. One sentence restates a point already made.
* **Rationale & Recommendation**: Shorten the Reason for Rejection to one sentence.

### style-4-7: Alternative J overclaims "Only" - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 432-434
* **Discrepancy Description**: The doc says only the temp-file-and-rename write keeps the promise. Other approaches could also keep it.
* **Rationale & Recommendation**: Change "only" to "with standard-library calls".

### style-4-8: The Scale section is redundant - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 346-349
* **Discrepancy Description**: "No performance target" and "No performance work is planned" say the same thing.
* **Rationale & Recommendation**: Delete the final sentence. Note that this interacts with design-4-3.

### style-4-9: Comment about the stakeholder in R1 - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 450
* **Discrepancy Description**: "no reason was given" adds no engineering information.
* **Rationale & Recommendation**: Delete the clause.

### style-4-10: Mixed terms for removed rows - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 57-64, 151, 318, 337 and 455
* **Discrepancy Description**: The doc uses "overlap copies", "duplicates" and "rows removed by deduplication" for the same thing.
* **Rationale & Recommendation**: Use one term throughout, or tie the terms together in G1.
