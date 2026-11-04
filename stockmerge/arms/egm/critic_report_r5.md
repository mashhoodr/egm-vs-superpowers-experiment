# Goldfish Review Report

**Target:** `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers-p2/arms/egm/docs/designs/stockmerge.md` (`Lines 1-639`, FeatureRange, everything before `## Detailed Implementation Plan`)

Stage 7 (Critic Review), egm-review-loop round 5. GoldfishContext: `BRIEF.md` (fixed contract). None of the findings asks to change the contract.

## Reviewer Status

| Reviewer | Status | Standard |
| --- | --- | --- |
| `egm-design` | completed | feature-spec-standard |
| `egm-structural` | completed | feature-spec-standard |
| `egm-style` | completed | none |

## Severity Summary

| Severity | Count (after dedup) |
| --- | --- |
| Blocker | 0 |
| Major | 3 |
| Nit | 20 |

Reviewers raised 25 findings. Two duplicate findings were merged into existing entries: style-5-4 into structural-5-1, and style-5-6 into structural-5-3. Parts of design-5-7 are cross-referenced where they overlap. When reviewers gave different severities to the same issue, the entry shows each reviewer's severity. Severities are as reported; none were changed.

Standard compliance: design and structural both confirm that every required section is present (Problem, Goals/Non-Goals, Architecture, Alternatives, Risks), with no skipped heading levels. All links in the range resolve.

## Prioritized Findings (Blockers -> Major -> Nits)

### design-5-1: The performance claim conflicts with the quadratic move-matching cost - Severity: Major
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 604, 618-621` (also R6.2, lines 398-401)
* **Discrepancy Description**:
  * The NFR claims about 100,000 rows in memory with no tuning.
  * Risks line 604 says move matching is quadratic within one (normalised SKU, qty) group.
  * Data with one row per item (qty 1 or -1) puts every scan of a popular SKU into one group. In the worst case that is about 5e9 comparisons, plus O(n) list removals. That is hours, not seconds.
  * The risk is "Accepted" on an unmeasured figure.
* **Rationale & Recommendation**:
  * Either state a bound on group size, or specify the index now.
  * For the index: keep each group's positives sorted by (minute, scan order), use `bisect` to find the ±120-minute window, and mark matched rows instead of deleting them. This keeps the tie-break deterministic: smallest absolute difference, then first in scan order.
  * The concepts brief deferred a `bisect` index "only if real file sizes need it". The spec's own 100k figure is that need.

### structural-5-2: Alternative K breaks the Pros/Cons/Reason layout - Severity: Major
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** `Lines 574-583`
* **Discrepancy Description**: Alternatives A-J use Pros, Cons and Reason for Rejection. K lists three sub-options with their downsides and one shared rejection reason. It has no Pros/Cons bullets, so the pros of each rejected option are not visible.
* **Rationale & Recommendation**: Split K into three alternatives in the standard layout, or give each sub-option its own Pros, Cons and Reason for Rejection.

### structural-5-3 (+ style-5-6): The exit-code table leaves out exit-2 conditions stated elsewhere - Severity: Major (structural) / Nit (style)
* **Reviewer Lens:** `egm-structural`, `egm-style`
* **Affected Scope:** `Lines 438-449`, compared with `56-61` (G5), `189`, `286` (R3.2), `311`, `445`
* **Discrepancy Description**:
  * R3.2 makes a rules file with no header row exit 2. The table has no row for it.
  * The diagram (line 189) shows an undecodable rules file as exit 2. No row covers a rules header that is not valid UTF-8; line 448 covers export headers only.
  * G5 lists `OSError`, `UnicodeError` and `csv.Error`. The backstop row (line 445) names only `OSError` and `csv.Error`.
  * Style also flags "backstop" as loose wording.
* **Rationale & Recommendation**:
  * Add rows for "Rules file has no header row (R3.2)" and "Rules header not valid UTF-8".
  * Make the exception lists in G5 and line 445 match.
  * Style suggests "caught in the command line layer" in place of "backstop".
* **Synthesizer note:** design-5-3 adds a related gap: a `UnicodeEncodeError` on write. Fix both together.

### design-5-2: Some decision tags credit builder calls to the contract - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 282-283` (R3.1), `312-319` (R4.2)
* **Discrepancy Description**:
  * R3.1 is tagged [contract], but it also covers BOM removal, trimming and exit 2 on a bad header. stakeholder_log round 2 Q9 left those to the builder.
  * R4.2 is tagged [contract], but it also covers:
    * header trimming;
    * exit 2 on a missing header;
    * header-only files being valid, with a warning.
  * Exit 2 on an unknown header is [owner] (round 1 Q8).
  * The wrong tags hide choices the owner could overrule.
* **Rationale & Recommendation**: Add [builder] and [owner] tags inside R3.1 and R4.2. Keep [contract] only on the header names.

### design-5-3: A location name that is not valid UTF-8 can crash the write step - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 59-61, 247-249` (R1.2), `432-434` (R9.3), `438-449`
* **Discrepancy Description**:
  * Location names come from argv. On POSIX, Python decodes non-UTF-8 argv bytes into surrogates.
  * Writing such a name as UTF-8 raises `UnicodeEncodeError` in step 9. R9.3 only says "writing fails", so an `OSError`-only catch would let a traceback through. That breaks G5.
* **Rationale & Recommendation**:
  * Reject a location name that cannot be encoded as UTF-8 in R1.2 (exit 2), or state that R9.3 catches `UnicodeEncodeError`.
  * Add a matching row to the exit table.

### design-5-4: The temporary-file write changes permissions and symlinks, and does not fsync - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 72-73, 207, 432-434, 608`
* **Discrepancy Description**:
  * `mkstemp` creates the temp file with mode 0600, and the replaced output keeps that mode.
  * If `--out` is a symlink, `os.replace` replaces the link itself.
  * Without fsync, "never half-written" does not hold through a power loss.
* **Rationale & Recommendation**:
  * Say how the temp file is created and what mode it gets.
  * Say what happens when `--out` is a symlink.
  * Add fsync, or narrow the guarantee at line 73.

### design-5-5: Record numbering for recovered multi-line records is under-specified - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 110-112, 359-369` (R4.12), `462-468`
* **Discrepancy Description**: R4.12 does not say how blank lines inside a recovered span are numbered. It also does not say whether R counts the span once or once per line, and the W = R - S - D check depends on that.
* **Rationale & Recommendation**: State that blank lines inside a span are dropped and get no number. State that each recovered non-blank line counts once in R and gets the next record number.

### design-5-6: Risks & Limits is missing a silent double-count from minute alignment - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 116-117, 339-340` (R4.7), `597, 605`
* **Discrepancy Description**: Cross-format dedup assumes scanner 1 truncates `HH:MM`. If it rounds instead, the same scan lands one minute apart in the two formats. It survives dedup and is counted twice, with no warning.
* **Rationale & Recommendation**: Add a Risks row for this case. Do not change the owner's minute rule.

### design-5-7: The Alternatives section has no architecture-level alternative - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 506-589`
* **Discrepancy Description**: Every alternative is about an individual rule. None weighs the in-memory batch pipeline against streaming or `sqlite3`, which bears on design-5-1. (This finding's points on J/K order and Alternative I are merged into structural-5-1 and style-5-5.)
* **Rationale & Recommendation**: Add a short architecture-level alternative that rejects streaming or `sqlite3` for stated reasons.

### structural-5-1 (+ style-5-4, design-5-7): Alternatives are out of letter order (I, K, J) - Severity: Nit
* **Reviewer Lens:** `egm-structural`, `egm-style`, `egm-design`
* **Affected Scope:** `Lines 567-590` (cross-references at `589, 635`)
* **Discrepancy Description**: K (line 574) comes before J (line 585). Lines 589 and 635 cite "Alternative J".
* **Rationale & Recommendation**: Swap the two subsections, or re-letter them and update the cross-references.

### structural-5-4: The diagram shows no exit-2 path for step 9 - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** `Line 207` (compared with `277-278, 434, 444, 449`)
* **Discrepancy Description**: Step 9 shows only `──► exit 0`, but R9.3 and the exit table list exit-2 failures for it.
* **Rationale & Recommendation**: Add a `──write failure──► exit 2` branch.

### structural-5-5: The Step 2 heading doesn't fit R2.1 - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** `Lines 186, 262-278`
* **Discrepancy Description**: The heading says "Output path check", but R2.1 is about input and rules paths.
* **Rationale & Recommendation**: Rename the heading to "Path checks", or move R2.1.

### structural-5-6: The glossary list is split in two - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** `Lines 105-107`
* **Discrepancy Description**: A blank line after the "Decision tags" bullet splits the glossary into two Markdown lists.
* **Rationale & Recommendation**: Remove the blank line at 106.

### structural-5-7: The Risks table's "Rule" column mixes value types - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** `Lines 595-608` (notably `599, 604`)
* **Discrepancy Description**: Most rows cite rule IDs, but two cite "Glossary" and "NFR".
* **Rationale & Recommendation**: Use a consistent value, for example "Glossary: Normalised SKU" and "NFR: Performance".

### structural-5-8: Decision tags are used unevenly in the NFR section - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** `Lines 614-623`
* **Discrepancy Description**: Only the Performance bullet carries a tag (`[builder]`). Determinism and Safety carry none.
* **Rationale & Recommendation**: Tag every NFR bullet, or drop the tag from Performance.

### structural-5-9: Section dividers are placed unevenly - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** `Lines 7, 591, 610, 625, 638`
* **Discrepancy Description**: Horizontal rules appear only at some H2 boundaries.
* **Rationale & Recommendation**: Put a rule between every H2 section, or keep rules only for major part breaks and do so consistently.

### structural-5-10: A hard-wrapped line is broken mid-sentence - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** `Lines 287-289`
* **Discrepancy Description**: The R3.2 sentence wraps at odd points in the raw text.
* **Rationale & Recommendation**: Re-wrap the paragraph.

### style-5-1: Scanner names are mixed - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 35-36, 542`
* **Discrepancy Description**: The text uses "scanner B" alongside "scanner 1/2". BRIEF.md uses scanner 1/2 and Format A/B.
* **Rationale & Recommendation**: Pick one naming scheme. For example, "the Format B scanner (scanner 2)" the first time, then "scanner 2".

### style-5-2: "Trim" is defined, then described again in other words - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 114-121, 221, 226, 247-248, 320-322`
* **Discrepancy Description**: The text says "outer spaces trimmed", "outer whitespace removed" and "trimming spaces". "Spaces" vs "whitespace" leaves it unclear whether tabs count.
* **Rationale & Recommendation**: Use "trimmed (see Glossary)" everywhere, and remove the restatement in the Normalised SKU entry.

### style-5-3: Decision tags repeat inside one bullet - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 328-329` (R4.5), `332-336` (R4.6)
* **Discrepancy Description**: A second `[builder]` tag follows an earlier `[builder]` with no change of owner between them.
* **Rationale & Recommendation**: Remove the repeated tags.

### style-5-5 (+ design-5-7): Alternative I gives claims that cannot be checked - Severity: Nit
* **Reviewer Lens:** `egm-style`, `egm-design` (structural noted it as a content point)
* **Affected Scope:** `Lines 570-572`
* **Discrepancy Description**: "Cons: none that matter for correctness" records a preference, not a trade-off. "Most shells and diff tools" has no source. The test files it mentions do not exist yet.
* **Rationale & Recommendation**: State the builder choice directly, give real cons, and tie "test files" to the fixtures defined in the plan.

### style-5-7: Asides that interrupt or confuse - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 29-32, 67-70, 287-288`
* **Discrepancy Description**:
  * Lines 30-31: the aside about the indistinguishable case doesn't name the case.
  * Line 69: "confirmed that" has an unclear referent.
  * Line 70: "(a builder's call)" reads as a second reason.
  * Line 288: "(not 4)" only makes sense next to the export rule.
* **Rationale & Recommendation**:
  * Name the case in the aside.
  * Rewrite lines 69-70 as: "The owner confirmed one row per kept scan (stakeholder_log.md, round 3, Q4) and left totals to the builder; totals are out of scope."
  * Drop "(not 4)".

### style-5-8: Small wording points - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 175, 344-346, 557`
* **Discrepancy Description**:
  * Line 175: "straight pipeline" is informal.
  * Lines 344-346: the `int()` 4300-digit note adds words without adding a reason.
  * Line 557: "harder to predict by hand" is subjective, and the owner-settled reason is enough on its own.
* **Rationale & Recommendation**: Use "linear pipeline", trim the parenthetical, and keep only the owner-settled reason.

## Verified as Correct (no action)

From `egm-design`:
* CUJ 1 and the worked example (lines 471-504): dedup, the move tie-break, the sort order and the summary counts.
* The [owner] tags spot-checked against stakeholder_log.md.
* The Python 3.11 claims: `fromisoformat`, the `int()` digit limit, `samefile` vs `realpath`, and the non-strict `csv` behaviour on an unclosed quote.

From `egm-style`:
* The stakeholder-log round-3 citations in Alternatives A and B and in the totals Non-Goal.
