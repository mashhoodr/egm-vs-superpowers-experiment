# Goldfish Review Report

**Target:** `arms/egm2/docs/designs/txmerge.md` (`Lines 1-465`, everything before `## Detailed Implementation Plan`)
**Round:** egm-review-loop round 3 (Stage 7, Critic Review)
**Standards:** `feature-spec-standard` (egm-design, egm-structural); persona rules (egm-style)

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

There were 22 raw findings. Two pairs were merged:
- `egm-structural-3-3` and `egm-style-3-2`
- `egm-structural-3-4` and the code-span and line-wrap parts of `egm-style-3-11`

No reviewer disputed any stakeholder ruling.

## Prioritized Findings (Blockers -> Major -> Nits)

### egm-design-3-1: The design never says whether amounts with thousands separators arrive quoted - Severity: Major
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 105, 127-128` (D14, D15), `246-248`, `454` (R5)
* **Discrepancy Description**: BRIEF.md says Format A Debit and Credit may contain thousands separators (`1,250.00`). D15 accepts that text, but only as a single cell. The design never states that the bank must quote these values in the CSV.
  - An unquoted row such as `05/03/2026,RENT,1,250.00,,` splits into 6 cells, so it fails the cell-count check in D14.
  - The row is then skipped with a warning and the run exits 0.
  - The result is that every amount of 1,000 or more in that file is lost. This conflicts with BRIEF goal 1 ("never lose a real transaction").
  - R5 covers skipped rows only in general terms and does not name this cause. The Format B `Amount` column has the same problem.
* **Rationale & Recommendation**:
  - State in D15 or D16 that values containing commas must be quoted, as standard CSV requires, and that unquoted values produce `expected N cells, got M`.
  - Add a Risks row that names this failure and its impact, and says whether it is mitigated or accepted.
  - If the risk is not accepted, either define a deterministic recovery rule for over-long A/B rows, or make the condition a file-level error so the data loss cannot pass with only a warning and exit 0.

### egm-design-3-2: No order is defined when several files have errors - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 126` (D13), `133` (D20), `197-203`, `222-226`
* **Discrepancy Description**: D20 implies the tool stops at the first file-level error, but no rule says so. Nothing says whether the rules file is read before or after the exports. If both are bad, the message that appears is unspecified.
* **Rationale & Recommendation**: Add one sentence: stop at the first file-level error, reading in a stated order (for example, `--account` files in argument order, then the rules file).

### egm-design-3-3: Temporary-file cleanup only covers `OSError` - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 136` (D23), `456` (R7)
* **Discrepancy Description**: If the write is interrupted by `KeyboardInterrupt` or an unexpected exception, a temporary file containing bank data is left next to the ledger. The exit code for unexpected internal errors is also not defined.
* **Rationale & Recommendation**:
  - Remove the temporary file on any exit from the write step (`try/finally`, or catch `BaseException`).
  - Either state the exit code for unexpected errors, or say explicitly that the default traceback behaviour is accepted.

### egm-design-3-4: Strict header matching rejects trailing commas, but this is not listed as a risk - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 126` (D13), `129` (D16), `446-457`
* **Discrepancy Description**: A header with an extra empty column makes the run exit 2. Many bank exports end every line with a comma. The strictness is deliberate and allowed by the rulings, but Risks does not record it.
* **Rationale & Recommendation**: Add a Risks row (R9) parallel to R6:
  - **Impact:** the run stops.
  - **Mitigation:** the user fixes the file.
  - **Reason accepted:** strict headers keep format detection unambiguous.

### egm-design-3-5: A blank description is not addressed - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 114` (D1), `127` (D14), `236`
* **Discrepancy Description**: D14 does not mention an empty `Description` or `Details` cell. By omission such a row is valid: it deduplicates on an empty key and is categorised `Uncategorised`. The design does not say whether that is intended.
* **Rationale & Recommendation**: State in D14 or D16 whether a blank description is valid or a row error.

### egm-design-3-6: "Whitespace" in the D1 normalisation is not defined - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 114` (D1), `123` (D10), `129` (D16)
* **Discrepancy Description**: The text does not say whether "whitespace" means Unicode whitespace (as `str.split()` and `str.strip()` use) or ASCII space only. The choice changes which rows count as duplicates.
* **Rationale & Recommendation**: Name the operation, for example "`' '.join(s.split())` then `casefold()`; trimming uses `str.strip()`".

### egm-structural-3-1: Alternative G has no Pros or Cons - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** `Lines 403-405`
* **Discrepancy Description**: Every other alternative uses the Pros / Cons / Reason for Rejection layout. Alternative G (Posting Date for Format B) has only a Reason for Rejection.
* **Rationale & Recommendation**: Add Pros and Cons, or say that the stakeholder fixed this choice so no trade-off was weighed.

### egm-structural-3-2: Solution text inside the Problem section - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** `Lines 50-53`
* **Discrepancy Description**: The paragraph starting "The proposed solution is a fixed sequence of in-memory stages..." describes the solution while sitting under `## The Problem`. It repeats the data-flow description at lines 190-217, and line 50 is over-long.
* **Rationale & Recommendation**: Move the paragraph to Overview or Technical Plan, or delete it. Re-wrap it either way.

### egm-structural-3-3 / egm-style-3-2: "Only place message texts are defined" is contradicted elsewhere - Severity: Nit
* **Reviewer Lens:** `egm-structural`, `egm-style`
* **Affected Scope:** `Lines 311-314` (the claim); conflicting text at `127` (D14 `bad amount`) and `181` (CUJ 5 `Debit and Credit both blank`); message fragments also quoted in `133` (D20) and `137` (D24)
* **Discrepancy Description**: The Messages section says it is the only place message texts are defined, and that the sections "do not overlap, so they cannot disagree". D14 and CUJ 5 repeat exact REASON strings, so both claims are false as written.
* **Rationale & Recommendation**:
  - Either refer to these messages by name in D14 and CUJ 5, or change the claim to "Where another section quotes a message, this table is authoritative."
  - Drop "cannot disagree".

### egm-structural-3-4: Inline code split across a line break, and over-long lines - Severity: Nit
* **Reviewer Lens:** `egm-structural`, `egm-style` (part of style-3-11)
* **Affected Scope:** `Lines 50, 324, 331-332`
* **Discrepancy Description**: The code span `cannot write PATH: <OS error>` is split across lines 331-332. Lines 50, 324 and 332 are much longer than the document's roughly 80-column wrap.
* **Rationale & Recommendation**: Keep each code span on one line and re-wrap these paragraphs.

### egm-structural-3-5: Usage code block has no language tag - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** `Lines 20-25`
* **Discrepancy Description**: The usage block opens with a bare fence, but the diagram at line 196 uses `text`.
* **Rationale & Recommendation**: Add `text` or `shell` to the fence.

### egm-style-3-1: Placeholder definition points to the wrong trimming rule - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Line 324`
* **Discrepancy Description**: The text says `PATH` and `OUT` are given "after the trimming in D24". D24 trims only `--account` values. It does not cover the `--rules` path or `--out`.
* **Rationale & Recommendation**: Reword to: "`PATH` is the file path as given (for `--account`, after D24 trimming); `OUT` is the `--out` value as given."

### egm-style-3-3: Filler adverbs ("simply", "naively") - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 35-37, 42, 122` (D9)
* **Discrepancy Description**: "Simply" adds nothing. "Naively" is a mild judgement where a plain description of the operation would do.
* **Rationale & Recommendation**: Describe the operation instead. Examples:
  - "Concatenating them double-counts..."
  - "Past 9999 the number has more digits."

### egm-style-3-4: Defensive aside in the worked-examples table - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Line 294`
* **Discrepancy Description**: "Expected, not a bug." argues with an imagined reader. R1 already says this result is intended.
* **Rationale & Recommendation**: Delete the sentence or replace it with "See R1."

### egm-style-3-5: Stock phrase "single source of truth" - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Line 185`
* **Discrepancy Description**: This is a stock phrase. Lines 311-313 already state the precedence plainly.
* **Rationale & Recommendation**: "The Decisions table defines behaviour; this section explains how the pieces fit."

### egm-style-3-6: "Never modifies its inputs" is stated three times - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 133` (D20), `225-226`, `441-442`
* **Discrepancy Description**: The same point is made three times, and lines 224-226 are wrapped awkwardly.
* **Rationale & Recommendation**: Keep the statement in D20. At 225-226, replace it with a reference to D20 or remove it, then re-wrap the paragraph.

### egm-style-3-7: Alternative I repeats itself - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 417-422`
* **Discrepancy Description**: The Cons and the Reason for Rejection make the same point ("where each rule lives"). "Keeps each file short" is a subjective benefit with no measure behind it.
* **Rationale & Recommendation**: Merge them into one sentence about mapping each D-rule to one module.

### egm-style-3-8: Repeated sentence in Scale - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 346-349`
* **Discrepancy Description**: "No performance target." and "No performance work is planned." say the same thing.
* **Rationale & Recommendation**: Remove the last sentence.

### egm-style-3-9: Overstated absolute claims in the alternatives - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 412, 432-434`
* **Discrepancy Description**:
  - "`Decimal` is ... exact" is too broad: `Decimal` is exact only within its context precision.
  - "Only the temporary-file-and-rename write keeps that promise" rules out alternatives the document never evaluates.
* **Rationale & Recommendation**:
  - Say "represents 2-decimal amounts exactly".
  - Drop "Only".

### egm-style-3-10: Two terms for the same concept - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 57-64, 151, 253, 318, 348, 411`
* **Discrepancy Description**: "Overlap copy" and "duplicate" name the same thing, and "Dedup" and "deduplication" alternate.
* **Rationale & Recommendation**:
  - Use "overlap copy" for the row and "deduplication" for the stage.
  - Gloss the fixed summary text once.

### egm-style-3-11: Small wording items - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 105, 450`
* **Discrepancy Description**:
  - Line 105: "`Description` is the description." tells the reader nothing.
  - Line 450 (R1): "no reason was given" is commentary that does not help the reader.
* **Rationale & Recommendation**:
  - Change line 105 to "`Description` is the ledger description."
  - Delete the aside in R1.
