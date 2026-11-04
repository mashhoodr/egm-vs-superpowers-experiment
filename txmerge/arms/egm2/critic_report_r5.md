# Goldfish Review Report

**Target:** `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers/arms/egm2/docs/designs/txmerge.md` (`Lines 1-465`, FeatureRange before `## Detailed Implementation Plan`)

**Round:** egm-review-loop round 5 (Stage 7, Critic Review)

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
| Major | 0 |
| Nit | 25 (26 raw; structural-5-5 merged into style-5-11) |

All three reviewers found every section that `feature-spec-standard` requires. The design reviewer re-ran the worked examples (deduplication, sort order, transfer pairing, CUJ 2), and they all hold. No stakeholder rulings were reopened.

## Prioritized Findings (Blockers -> Major -> Nits)

No Blockers. No Majors.

### design-5-1: Temporary file is only cleaned up after an OSError - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 136, 457` (D23, R7)
* **Discrepancy Description**: D23 says the temporary file is removed "if anything fails (`OSError`)". KeyboardInterrupt, SIGTERM and other exceptions are not covered, so they leave a stray temporary file.
* **Rationale & Recommendation**: Remove the temporary file in a `finally` (or on any `BaseException`) whenever the rename did not happen. State that a SIGKILL or crash can still leave one, and give its name pattern.

### design-5-2: The costs of temp-file-and-rename are not stated - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 136, 425-435, 457` (D23, Alternative J, R7)
* **Discrepancy Description**: `os.replace` has four costs the document does not mention:
  * It needs write permission on the directory, not just the file.
  * It breaks hard links to the old ledger.
  * The new file takes the process's owner and group.
  * With no fsync, a power loss can leave the ledger empty or truncated. R7's "left exactly as it was" guarantee therefore only holds for a process failure.
* **Rationale & Recommendation**: List these as accepted costs in Alternative J or R7, and limit R7's guarantee to process failures.

### design-5-3: Which error is reported, and in what order, is not specified - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 192-226, 309-315` (Data flow, Messages)
* **Discrepancy Description**: The document never states the order in which files are checked, or that the first file-level failure stops the run. It also does not say whether row warnings from earlier exports stay on stderr before a later exit 2.
* **Rationale & Recommendation**: State the order (rules, then exports by `arg_index`) and that the first failure stops the run. Say whether earlier warnings are printed or held back.

### design-5-4: A bad byte deep in a file is reported after warnings for earlier rows - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 129, 250-251, 330` (D16, Reading an export, cannot-read message)
* **Discrepancy Description**: If rows are decoded as the file is read, invalid UTF-8 or a NUL byte on a late line surfaces only after warnings for earlier rows. The order of output then depends on how reading is implemented.
* **Rationale & Recommendation**: Decode and check each whole file before parsing rows, or state the streaming behaviour explicitly.

### design-5-5: The bad `--account` message is ambiguous - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 137, 323` (D24, Messages table)
* **Discrepancy Description**: A `type=` function that raises `ArgumentTypeError` adds an `argument --account:` prefix to the message, and `parser.error()` does not. The table does not say which, so an exact-match test passes with one implementation and fails with the other.
* **Rationale & Recommendation**: Choose `parser.error()` after parsing and write out the full expected stderr line.

### design-5-6: "stdout stays empty" conflicts with `--help` - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Line 135` (D22)
* **Discrepancy Description**: argparse prints help to stdout and exits 0.
* **Rationale & Recommendation**: Limit D22 to merge runs, or note that help is the exception.

### design-5-7: The Messages table says it is complete but leaves out unexpected failures - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 311-323`
* **Discrepancy Description**: An unexpected exception prints a traceback and exits 1. The table does not cover this and mentions only exit codes 0 and 2.
* **Rationale & Recommendation**: Declare such cases out of scope ("traceback, exit 1, no ledger written per D23"), or add a catch-all row.

### design-5-8: R5 understates what happens when most rows are skipped - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Line 455` (R5); related lines 47-48, 133
* **Discrepancy Description**: A run that skips most rows still exits 0, and it overwrites the previous good ledger with a much smaller one. R5's impact says only that rows are missing.
* **Rationale & Recommendation**: Keep the ruling. Expand R5's impact to say the previous ledger is overwritten, and add version control of the ledger to the mitigation.

### structural-5-1: Solution summary sits inside "The Problem" - Severity: Nit
* **Reviewer Lens:** `egm-structural` (also `egm-style`, see style-5-11)
* **Affected Scope:** `Lines 50-53`
* **Discrepancy Description**: The paragraph starting "The proposed solution is..." describes the design, not the problem.
* **Rationale & Recommendation**: Move it to Overview or to the start of the Technical Plan.

### structural-5-2: Alternative G lacks the Pros/Cons structure used by every other alternative - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** `Lines 404-406`
* **Discrepancy Description**: Alternative G has only a Reason for Rejection. Every other alternative also has Pros and Cons.
* **Rationale & Recommendation**: Add short Pros and Cons bullets, or note that the entry is intentionally abbreviated.

### structural-5-3: Code fences are labelled inconsistently - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** `Lines 20, 196`
* **Discrepancy Description**: The block at line 20 has no language label. The block at line 196 uses ```text.
* **Rationale & Recommendation**: Label the line-20 block.

### structural-5-4: Internal cross-references are plain prose, not links - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** `Lines 180, 444, 451`
* **Discrepancy Description**: "Messages table", "Technical Plan › Scale" and "worked examples" refer to sections by name only. R1's "worked examples" does not say which section it means.
* **Rationale & Recommendation**: Use anchor links. At minimum, name the Transfer pairing section in R1.

### structural-5-6: Fixed formats are listed under "Decisions" - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** `Lines 94-108`
* **Discrepancy Description**: "Fixed formats" restates the BRIEF contract, so its rules are neither (S) nor (E), but it sits under Decisions.
* **Rationale & Recommendation**: Move it to its own H2 (for example "Fixed Contract"), or add a line to the Decisions intro saying the first table restates the contract.

### structural-5-7: Section headings differ from the standard's labels - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** `Lines 32, 183`
* **Discrepancy Description**: The document says "The Problem" and "Technical Plan (Architecture)". The standard says "Problem Statement" and "Proposed Architecture". The standard calls its labels examples, so this does not fail it.
* **Rationale & Recommendation**: Optional: rename the headings to match.

### style-5-1: Filler and judgment adverbs - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 35, 36, 42, 122`
* **Discrepancy Description**: "Naively" (lines 35 and 42) is a judgment, and "simply" (lines 36 and 122) is filler.
* **Rationale & Recommendation**: Remove both, for example "Concatenating them double-counts...".

### style-5-2: Editorial aside in the worked-examples table - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Line 294`
* **Discrepancy Description**: "Expected, not a bug." is defensive, and R1 already covers this limitation.
* **Rationale & Recommendation**: Delete the sentence or replace it with "see R1".

### style-5-3: "No reason was given" in R1 - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Line 451`
* **Discrepancy Description**: The clause adds nothing actionable and reads as mild criticism of the stakeholder ruling.
* **Rationale & Recommendation**: End the mitigation at the ruling citation and the visibility note.

### style-5-4: Repeated "never modifies inputs" statement - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 133, 225-226, 442-443`
* **Discrepancy Description**: The same guarantee appears three times, and line 133 opens with an informal "So".
* **Rationale & Recommendation**: State it once in D20 and cite D20 elsewhere.

### style-5-5: Repeated zero-as-blank clause in D14 - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Line 127`
* **Discrepancy Description**: The rule that zero counts as blank is stated twice in the same cell.
* **Rationale & Recommendation**: Drop the parenthetical.

### style-5-6: Repeated performance statement in Scale - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 347, 350`
* **Discrepancy Description**: "No performance target." and "No performance work is planned." say the same thing.
* **Rationale & Recommendation**: Delete the second sentence.

### style-5-7: Alternative I restates its own Cons, and "obvious" is subjective - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 418-423`
* **Discrepancy Description**: The Reason for Rejection restates the Con instead of giving a deciding factor, and "obvious" is an opinion.
* **Rationale & Recommendation**: Give the deciding factor instead, for example: one module per concern maps each Decision to one file.

### style-5-8: Hedge clause admitting possible message mismatches - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 311-315`
* **Discrepancy Description**: The precedence rule plans for inconsistency between quotes and the table. The quotes at lines 133, 137 and 180-181 match the table, so there is none to resolve.
* **Rationale & Recommendation**: Say that other sections refer to messages by name, and drop the conflict-resolution sentence.

### style-5-9: Vague citation in D15 - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Line 128`
* **Discrepancy Description**: "(stakeholder, review round)" names no round or answer, and the Source column says only "E".
* **Rationale & Recommendation**: Give the round and answer number, and use "E / S" in the Source column, as D13 and D14 do.

### style-5-10: Inconsistent terms for the same concepts - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 57-64, 151, 253-255, 319, 349, 359, 412, 454`
* **Discrepancy Description**: "Copy" and "duplicate" name the same thing, and "dedup" and "deduplication" are mixed in prose.
* **Rationale & Recommendation**: Use one noun in prose, and spell out "deduplication" outside code identifiers.

### style-5-11: Wordy lead-in and uneven line wrapping - Severity: Nit
* **Reviewer Lens:** `egm-style` (merged with `egm-structural` structural-5-5)
* **Affected Scope:** `Lines 50, 225-226, 325, 332-333`
* **Discrepancy Description**: "The proposed solution is" is a wordy opener. Lines 50, 325 and 333 exceed the ~80-column wrap, and line 225 breaks short. The inline code span `` `cannot write PATH: <OS error>` `` is split across lines 332-333.
* **Rationale & Recommendation**: Write "The design is...". Rewrap these lines to the document's width, and keep each exact message string in one code span on a single line.
