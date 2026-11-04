# Goldfish Review Report

**Target:** `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers/arms/egm2/docs/designs/txmerge.md` (`Lines 1-456`, FeatureRange before `## Detailed Implementation Plan`)

**Stage:** 7 (Critic Review), egm-review-loop round 1

## Reviewer Status

| Reviewer | Status | Standard | Raw findings |
| --- | --- | --- | --- |
| `egm-design` | completed | feature-spec-standard | 0 Blocker, 2 Major, 7 Nit |
| `egm-structural` | completed | feature-spec-standard | 0 Blocker, 2 Major, 10 Nit |
| `egm-style` | completed | persona rules | 0 Blocker, 4 Major, 12 Nit |

## Severity Breakdown (after deduplication)

| Severity | Count |
| --- | --- |
| Blocker | 0 |
| Major | 7 |
| Nit | 26 |

37 raw findings were reduced to 33. Merged findings keep the id of the primary entry and list the absorbed ids. The synthesizer checked that D23 is marked `E` (designer call) at line 134 and that the stakeholder log has no ruling on temp files or atomic writes. Changing D23 therefore does not reopen a settled requirement.

## Prioritized Findings (Blockers -> Major -> Nits)

### Major

### design-1-1: Write failure can delete a ledger the tool never touched; atomic write is not considered - Severity: Major
* **Reviewer Lens:** `egm-design` (absorbs `structural-1-2`)
* **Affected Scope:** Lines 134 (D23), 124 (D13), 216-221, 299-303, 344-413 (Alternatives)
* **Discrepancy Description**:
  * (a) D23 deletes `--out` "whether or not a ledger existed before", on the grounds that its old contents "were already lost when it was opened". That is false when `open()` itself fails, for example with EACCES on an existing read-only ledger. It is unclear whether an open failure counts as "fails part-way". If it does, the tool deletes user data it never truncated.
  * (b) "Symlinks followed" combined with "`--out` is deleted": `os.remove` on a symlink removes the link and leaves the truncated target behind.
  * (c) "No temporary file, no fsync" has no rationale. Alternatives A-I contain no entry for writing a temp file and then calling `os.replace`. That option would make D13's "existing file left untouched" true for every exit-2 case.
* **Rationale & Recommendation**: The standard's Alternatives Rule requires rejected options for each major design choice, and this choice affects data loss. Either adopt temp file plus `os.replace`, or add "Alternative J: atomic temp-file-and-rename" with Pros, Cons and a reason for rejection. In both cases, state that nothing is deleted when `open()` fails, and define the behaviour for a symlinked `--out` and for a failed delete.

### design-1-2: `parse_account` splitting, trimming and malformed rules are undefined - Severity: Major
* **Reviewer Lens:** `egm-design` (absorbs the `parse_account` part of `style-1-9`)
* **Affected Scope:** Lines 124 (D13 "a malformed `--account` value"), 193, 317, 325-326
* **Discrepancy Description**: The document never says:
  * whether `NAME=PATH` splits on the first `=` or the last;
  * what is trimmed (NAME, PATH or both);
  * what counts as malformed (no `=`, empty NAME, empty PATH).

  NAME is the `account` column, part of the D1 dedup key, and part of the D12 sort key. Different guesses therefore produce different ledgers.
* **Rationale & Recommendation**: Add a D-rule. For example: split on the first `=`; trim outer whitespace on both sides; a missing `=`, an empty NAME or an empty PATH is exit 2 with a named message. Add that message to the Messages table at lines 322-326.

### structural-1-1: Risks are listed without mitigations - Severity: Major
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** Lines 427-448; also 338-342 and 417-425
* **Discrepancy Description**: The standard requires each failure mode to come with a mitigation. Only "Silent data loss" (444-446) has one. "Greedy pairing", "False transfers", "Card dates", "Max-count dedup" and "Encoding" each stop after naming the risk, or say only "Accepted". Security and scale risks sit outside this section.
* **Rationale & Recommendation**: Give every risk the same shape: Risk / Impact / Mitigation, or "Accepted: by whom, why". A table works well. Either rename the section "Risks & Mitigations" or cross-reference the security and scale items from it.

### style-1-1: G2 and Alternative A claim no transaction is lost, but the Risks section admits one can be - Severity: Major
* **Reviewer Lens:** `egm-style` (related: `design-1-4`)
* **Affected Scope:** Lines 60-62 (G2 "No lost transactions"), 351-352, contradicted by 437-443
* **Discrepancy Description**: The goal title and the Alternative A rejection state an absolute outcome. The document's own max-count risk shows that a real transaction can be dropped.
* **Rationale & Recommendation**: Retitle G2 to describe the rule, not the outcome (for example, "Repeats within one export are kept; a row is removed only when ..."). Reword 351-352 the same way and cross-reference the max-count risk.

### style-1-2: Quotation attributed to the wrong source - Severity: Major
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 366-367
* **Discrepancy Description**: The phrase `G2 ("never lose a real transaction")` does not appear in G2 (60-62). It paraphrases BRIEF.md "What I want" item 1, and it repeats the overclaim in style-1-1.
* **Rationale & Recommendation**: Cite BRIEF.md goal 1 directly, or quote G2's actual wording.

### style-1-3: Message texts are defined in several places, and two sections each claim to be the sole source - Severity: Major
* **Reviewer Lens:** `egm-style` (absorbs `structural-1-6`)
* **Affected Scope:** Lines 307, 181, 131 (D20), 177 (CUJ 5), 244-247 (restate D14 despite the promise at 183)
* **Discrepancy Description**: Line 307 says the Messages table is "the only place the message texts are defined". D20 and CUJ 5 also define message text. Line 181 says the Decisions table is the "single source of truth for behaviour". The texts agree today, but a reader cannot tell which section wins if they diverge.
* **Rationale & Recommendation**: Replace the inline texts in D20 and CUJ 5 with references to the Messages table, or soften line 307. State once which section takes precedence. Make 244-247 cite D14 instead of restating it.

### style-1-4: The performance statement cannot be measured and contradicts itself - Severity: Major
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 422-423, 340-342
* **Discrepancy Description**: "No targets" is followed immediately by a target ("well under a second for a year of exports"). Neither that target nor "thousands of rows" has a number, so neither can be tested. The statement also appears in two sections.
* **Rationale & Recommendation**: Either state a measurable bound (for example, "< 1 s for 20,000 input rows on a laptop") or say "no performance target; inputs expected under N rows". Keep it in one place, either Scale or NFR.

### Nit

### design-1-3: D14 zero-as-blank makes D17's "zero amounts kept" apply to Format B only - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Lines 125, 128, 445-446
* **Discrepancy Description**: A Format A zero row (`0.00,` or `0.00,0.00`) is skipped as "both blank", so it never becomes a kept 0.00 row. D17 reads as if it applied to both formats.
* **Rationale & Recommendation**: Say in D17 that kept zero rows come only from Format B.

### design-1-4: Split-day max-count loss is credited to the stakeholder without a ruling in the log - Severity: Nit
* **Reviewer Lens:** `egm-design` (also noted in `egm-structural`'s clean-points list)
* **Affected Scope:** Lines 437-443
* **Discrepancy Description**: The stakeholder set the max-count rule but never ruled on the case where two exports each cut off part-way through a day. "Accepted by the stakeholder (D2)" claims more than the log shows.
* **Rationale & Recommendation**: Reword to "a consequence of D2, not separately raised with the stakeholder". Optionally add it to Open Questions.

### design-1-5: `str.casefold()` goes further than "ignore case"; "inner whitespace" is undefined - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Lines 112 (D1), 121 (D10)
* **Discrepancy Description**: `casefold` maps `ß` to `ss`. `str.split()` treats NBSP and other Unicode spaces as whitespace, but the stakeholder said "spaces".
* **Rationale & Recommendation**: Justify `casefold`, or use `lower()`. State which characters count as whitespace.

### design-1-6: Exceptions from the `csv` module are not classified - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Lines 124-125, 238-247
* **Discrepancy Description**: A `csv.Error`, such as `field_size_limit` being exceeded, is neither a file-level nor a row-level error under any rule. It would probably end in a traceback with exit 1, which breaks G6.
* **Rationale & Recommendation**: Classify it as a file-level exit-2 error with a "cannot read PATH" style message.

### design-1-7: Spreadsheet formula injection is not listed - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Lines 419-421
* **Discrepancy Description**: Descriptions are written verbatim. A description starting with `=`, `+`, `-` or `@` can run as a formula when the ledger is opened in Excel or Sheets.
* **Rationale & Recommendation**: Record it as an accepted risk. Do not change the output; the fixed contract and determinism rule it out.

### design-1-8: The designer's own (E) decisions have no rejected alternatives - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Lines 122-134 (D11, D13, D16, D22) against 344-413
* **Discrepancy Description**: Several designer choices have no alternatives listed:
  * strict headers vs tolerant matching;
  * stopping on a missing input file vs skipping it;
  * failing on non-UTF-8 vs a cp1252 fallback;
  * a summary on stderr vs silence.
* **Rationale & Recommendation**: Add short Alternatives entries, at least for encoding and header strictness.

### design-1-9: Write-path prose is out of order, and G6 disagrees with D13 - Severity: Nit
* **Reviewer Lens:** `egm-design` (absorbs `structural-1-7` and the ordering part of `style-1-11`)
* **Affected Scope:** Lines 216-221, 70-72 (G6), 124 (D13)
* **Discrepancy Description**: Line 220 ("The ledger is then written ...") follows the D23 failure sentence without a paragraph break, so it reads in the wrong order. G6 says "no ledger file" while D13 says "existing file left untouched", and D23 is an exception to both.
* **Rationale & Recommendation**: Reorder to: checks, then write, then write failure. Align G6 with D13 and name the D23 exception, or remove the exception if design-1-1 adopts atomic replace.

### structural-1-3: Alternative G breaks the entry template - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** Lines 394-396; also 359, 375, 382-383
* **Discrepancy Description**: G has only a reason for rejection, with no Pros or Cons. B, D and E rest only on "stakeholder decision".
* **Rationale & Recommendation**: Add Pros and Cons to G.

### structural-1-4: "Future Improvements" is nested under Risks - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** Lines 450-453
* **Discrepancy Description**: Roadmap content is filed as an H3 under "Risks & Limits".
* **Rationale & Recommendation**: Promote it to an H2, or fold it into Non-Goals.

### structural-1-5: Section names differ from the standard's - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** Lines 32, 179, 427
* **Discrepancy Description**: The document uses "The Problem", "Technical Plan (Architecture)" and "Risks & Limits". The standard uses "Problem Statement", "Proposed Architecture" and "Risks & Mitigations".
* **Rationale & Recommendation**: Use the standard's names so each section maps one-to-one.

### structural-1-8: The data-flow diagram leaves out the same-file check - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** Lines 192-211
* **Discrepancy Description**: The D20 check is a stage that can exit 2, but it is not in the diagram.
* **Rationale & Recommendation**: Add a "same-file check (D20), else exit 2" node before `write_ledger`.

### structural-1-9: Code fences are tagged inconsistently - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** Lines 20, 192
* **Discrepancy Description**: The fence at line 20 is untagged; the one at line 192 is tagged `text`.
* **Rationale & Recommendation**: Tag both.

### structural-1-10: The Messages table's Exit column mixes kinds of value - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** Lines 309-315
* **Discrepancy Description**: Two rows hold "run continues" in a column that otherwise holds exit codes.
* **Rationale & Recommendation**: Use "—" with an Effect column, or write "(none; final exit 0)".

### structural-1-11: Uneven wrapping, a split code span, and a repeated PATH definition - Severity: Nit
* **Reviewer Lens:** `egm-structural` (absorbs `style-1-8`)
* **Affected Scope:** Lines 317, 324-326
* **Discrepancy Description**: Lines 317 and 326 run past the document's line width. The code span `cannot write PATH: <OS error>` is broken across lines. The PATH definition appears twice (317 and 325-326).
* **Rationale & Recommendation**: Re-wrap, keep code spans on one line, and merge the two PATH/OUT definitions into one sentence.

### structural-1-12: Goals and CUJs are not traced to each other - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** Lines 55-85, 136-177
* **Discrepancy Description**: The CUJs never cite goals, Non-Goals have no IDs, and no CUJ demonstrates G4 (categorisation) directly.
* **Rationale & Recommendation**: Add "Covers: Gx" to each CUJ and number the Non-Goals.

### style-1-5: Filler adverbs - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 35, 36, 42, 120, 391
* **Discrepancy Description**: "Naively", "Simply" and "already" add tone but no information.
* **Rationale & Recommendation**: Remove them.

### style-1-6: "Single pass pipeline" is inaccurate - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 50
* **Discrepancy Description**: The pipeline includes a full sort, so it is not single-pass. Line 188 uses accurate wording.
* **Rationale & Recommendation**: Write "a fixed in-memory pipeline".

### style-1-7: Editorial remark in the worked example - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 290
* **Discrepancy Description**: "Expected, not a bug." is defensive and repeats 429-431.
* **Rationale & Recommendation**: Delete it.

### style-1-9: Summary symbols are used before they are defined - Severity: Nit
* **Reviewer Lens:** `egm-style` (the `parse_account` part is merged into `design-1-2`)
* **Affected Scope:** Line 127 (D16 `R` / `S`); defined only at 330
* **Discrepancy Description**: D16 relies on symbols defined about 200 lines later.
* **Rationale & Recommendation**: Write "the summary counts (see Messages)".

### style-1-10: Several words for one concept - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 57, 59, 61, 148, 249, 311, 332, 341, 437
* **Discrepancy Description**: "Overlap copies", "copy", "duplicates", "dedup" and "deduplication" are used interchangeably.
* **Rationale & Recommendation**: Use one noun ("duplicate") and one process name ("deduplication") throughout.

### style-1-11: "The tool never modifies its inputs" is stated three times - Severity: Nit
* **Reviewer Lens:** `egm-style` (the ordering part is merged into `design-1-9`)
* **Affected Scope:** Lines 131, 220-221, 424-425
* **Discrepancy Description**: The same assurance is repeated.
* **Rationale & Recommendation**: State it once, in D20, and cross-reference it elsewhere.

### style-1-12: The "Silent data loss" entry is vague and has an unclear referent - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 444-446
* **Discrepancy Description**: "Limited" is vague. "Such banks" refers to nothing named earlier. It is rows, not banks, that are lost.
* **Rationale & Recommendation**: Rewrite as an explicit mitigation: every skipped row is warned about and counted.

### style-1-13: "Accepted" does not say by whom - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 431, 433
* **Discrepancy Description**: Per stakeholder_log round 3 Q4, the same-file case was a designer call, not a stakeholder acceptance.
* **Rationale & Recommendation**: Write "Accepted by the stakeholder (D6) for refunds; designer decision (D4) for one file under two names."

### style-1-14: Source markers do not match their description - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 94-96, 112-134 (D4 at 115)
* **Discrepancy Description**: The prose says "(S)" and "(E)", but the table uses bare letters. D4 embeds "(accepted, E)" in a row whose source is S.
* **Rationale & Recommendation**: Use one form, and give D4 the source "S / E (same-file pairing)".

### style-1-15: Alternative I repeats itself - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 408-413
* **Discrepancy Description**: The Cons and the reason for rejection say the same thing. "Keeps each file short" has no number behind it.
* **Rationale & Recommendation**: Shorten the reason for rejection.

### style-1-16: Small wording issues - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 58, 246-247, 401
* **Discrepancy Description**: "The highest count of it" reads awkwardly. The G2 justification at 246-247 is loose. "`0.1 + 0.2` style errors" is informal.
* **Rationale & Recommendation**: Write "its highest count in any single export", "so unpadded dates are not reported as errors" and "binary rounding errors (e.g. 0.1 + 0.2 != 0.3)".

## Points Reviewers Found Clean

* Every section the standard requires is present, and heading levels never skip (`egm-structural`).
* The Decisions table matches the stakeholder log on every settled ruling. The D20 same-file check, the D12 ordering and the D7 pairing are correct as written (`egm-design`).
* All D-number cross-references resolve, and all five CUJs use the same Given/When/Then layout (`egm-structural`).
