# Goldfish Review Report

**Target:** `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers-p2/arms/egm/docs/designs/stockmerge.md` (`Lines 1-614`, FeatureRange before `## Detailed Implementation Plan`)

Stage 7 (Critic Review), egm-review-loop round 3. GoldfishContext: `BRIEF.md` (fixed owner contract).

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
| Major | 10 (design 3, style 7) |
| Nit | 21 |

Severities are reported as each reviewer gave them. Where reviewers raised the same point, the finding is listed once under the first id, with the duplicates noted.

Verified by reviewers, and not findings: all required standard sections are present. Heading levels, tables, code fences and links are valid. A design reviewer worked CUJ 1 and the worked example (lines 448-481) by hand and confirmed the results. It also confirmed the R4.12 claim about Python csv's non-strict EOF behaviour. Nothing in the reviewed range breaks the BRIEF contract.

## Prioritized Findings (Blockers -> Major -> Nits)

### design-3-1: `os.path.samefile` can raise on a missing path, breaking G5 - Severity: Major
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 249-250` (R1.5), `254-265` (R2.1, R2.2), `422` (backstop row), `55-58` (G5)
* **Discrepancy Description**: `os.path.samefile` raises `FileNotFoundError` when either path does not exist. R2.1 defers existence checks to steps 3-4. R1.5 uses the same comparison in step 1. The backstop row covers only errors "while reading". So a mistyped path can end in a traceback, which G5 rules out, and the user does not get the "error naming the path" that R2.1 promises.
* **Rationale & Recommendation**: Call `samefile` only when both paths exist, and fall back to `realpath` equality otherwise. State that any `OSError` in steps 1-2 is exit 2 with a message naming the path. Widen the backstop row to cover the whole run before writing. (Related: style-3-2.)

### design-3-2: An all-skipped file exits 0, and export shapes are unverified - Severity: Major
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 294-307` (R4.2, R4.3), `85-93` (Open Questions), `572-583` (Risks)
* **Discrepancy Description**: A file with a valid header and zero valid rows gets only a `PATH: no valid rows` warning, and the run exits 0. Realistic triggers:
  * a Format B row written as 3 fields when the note is empty (R4.3 skips every row);
  * a Format A file that Excel re-saved with seconds (`strptime` rejects every row).

  In both cases a whole location silently drops out. No real export sample was ever obtained (concepts_brief Stage 0 Q6 was answered "your call"). Even so, Open Questions says nothing is open, and Risks has no row for this.
* **Rationale & Recommendation**:
  * Accept 3-field Format B rows, since the note is never read, or record this as a rejected alternative.
  * Make "data rows present, none valid" exit 2, or a distinct loud condition, and add it to the exit table.
  * Add a Risks row for "export shape assumed, not checked against real files", or reopen the sample request.

### design-3-3: One undecodable byte stops the whole run - Severity: Major
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 291-293` (R4.1), `425` (exit table), `483-566` (Alternatives)
* **Discrepancy Description**: Problems inside a row are skipped with a warning, but a single non-UTF-8 byte anywhere in a file is exit 2 for the whole run. The likeliest source of such a byte is the Format B free-text note, which the tool never reads. This contradicts the skip-and-warn policy, and Alternatives does not cover the choice.
* **Rationale & Recommendation**: Decode each physical line separately and skip undecodable lines with a `PATH:LINE` warning. Alternatively, use `errors="surrogateescape"` and reject a row only if a field the tool uses is affected. Or keep exit 2 and record the rejected options under Alternatives.
* **Note:** The reviewer rated this "Major (a Nit is defensible)", because the failure is loud rather than silent data loss. It is kept at Major as given.

### style-3-1: "Never removing a real second scan" contradicts an accepted risk - Severity: Major
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 28-31` (with `574`)
* **Discrepancy Description**: The Problem section says the tool removes overlap "without ever removing a real second scan". The Risks table (line 574) accepts that two real scans with the same key, one in each of two exports, collapse to one. By the document's own rules, the absolute claim is false.
* **Rationale & Recommendation**: Scope the claim, for example: "without removing a second scan of the same item from the same export (R5.3); scans with equal keys in different exports are treated as copies (R5.1)."

### style-3-2: The "no traceback" goal is unbounded - Severity: Major
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 56-58` (with `67`, `422`)
* **Discrepancy Description**: "No input file, argument or file system error ends in a traceback" is open-ended. The backstop covers only `OSError` and `csv.Error` while reading, and line 67 allows a traceback on Ctrl-C. A reader cannot tell which error classes are covered.
* **Rationale & Recommendation**: List the covered classes (usage errors, `OSError`, `UnicodeDecodeError`, `csv.Error`, header errors) and point to the exit-code table. (Related: design-3-1.)

### style-3-3: Mixed attribution on the totals non-goal - Severity: Major
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 64-65`
* **Discrepancy Description**: "The owner confirmed one row per kept scan; totals are out of scope [builder]." credits the owner and tags the builder in the same sentence. Provenance tags decide what the owner may overrule (lines 91-93). BRIEF.md line 12 also asks for an inventory "per SKU per location".
* **Rationale & Recommendation**: Split the attribution: "One row per kept scan [owner]. A totals report is out of scope [builder]." Add one clause that reconciles this with the BRIEF wording.

### style-3-4: "Spaces" and "whitespace" are used interchangeably - Severity: Major
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 106-107, 209, 214, 237-238, 302-304`
* **Discrepancy Description**: The Glossary defines trimming as `str.strip()`, which removes all whitespace, but rules say "outer spaces trimmed" or "trimming spaces". So it is unclear whether tabs and other whitespace are removed.
* **Rationale & Recommendation**: Define "trimmed" once as `str.strip()` and use only "trimmed" everywhere else.

### style-3-5: R3.2 cites sentence positions, then restates them - Severity: Major
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 271-278`
* **Discrepancy Description**: "(R4.3, first two sentences)" breaks if R4.3 is edited. The rule then restates the referenced content in its own words, so the same content appears twice.
* **Rationale & Recommendation**: Either state the reading rules directly, or cite R4.1, R4.3 and R4.12 by ID and list only the differences (2 fields instead of 4).

### style-3-6: R4.12 is one 15-line bullet - Severity: Major
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 335-349`
* **Discrepancy Description**: One bullet holds the cause, the warning text, the re-parse method, the effects on quoted and multi-line fields, and the field-size limit. "Most likely" is speculation. As written, the rule is hard to test.
* **Rationale & Recommendation**: Split it into sub-bullets: (a) detection and warning, (b) per-line re-parse, (c) consequences, (d) `csv.field_size_limit`. Delete "most likely". (Related: design-3-8.)

### style-3-7: Unverified sizing claim - Severity: Major
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 581, 593-594`
* **Discrepancy Description**: "Stock-takes are far smaller" and "about 100,000 rows" have no source. The NFR calls the size "assumed", but the Risks table states it as fact.
* **Rationale & Recommendation**: Cite where the owner gave the figure, or tag it [builder] in both places. Replace "far smaller" with the expected range.

### structural-3-1: Alternative K comes before J - Severity: Nit
* **Reviewer Lens:** `egm-structural` (also style-3-15, design-3-10)
* **Affected Scope:** `Lines 551-566`
* **Discrepancy Description**: K (line 551) comes before J (line 562). Future Improvements (line 610) refers to J.
* **Rationale & Recommendation**: Reorder or re-letter so the alternatives run in order.

### structural-3-2: Alternative K breaks the Pros/Cons/Reason template - Severity: Nit
* **Reviewer Lens:** `egm-structural` (also style-3-15)
* **Affected Scope:** `Lines 551-560`
* **Discrepancy Description**: K puts three sub-options, each with an inline pros/cons sentence, under one shared Reason for Rejection.
* **Rationale & Recommendation**: Split K into three alternatives, or add an explicit "Options" bullet so the labels match the other entries.

### structural-3-3: Alternative I has no substantive reason for rejection - Severity: Nit
* **Reviewer Lens:** `egm-structural` (also style-3-14, design-3-10)
* **Affected Scope:** `Lines 544-549`
* **Discrepancy Description**: Cons is "none that matter for correctness", and the reason is "builder preference". "Most shells and diff tools" cannot be checked.
* **Rationale & Recommendation**: Tag it [builder] and give a concrete reason, such as byte-identical golden-file diffs, or name the trade-off (Excel on Windows). Or move it to a note under R9.2.

### structural-3-4: Definitions sit under Open Questions - Severity: Nit
* **Reviewer Lens:** `egm-structural` (also style-3-9)
* **Affected Scope:** `Lines 85-93`
* **Discrepancy Description**: The section defines owner and builder and explains the [builder] tag, which are Glossary material. The tag is first used at line 65, but the full legend only appears at lines 224-226. "Every behaviour question was answered" is an absolute claim (see also design-3-2).
* **Rationale & Recommendation**: Move the definitions and the tag legend into the Glossary or just after the metadata. Reduce the section to "None open" plus pointers to the decision logs.

### structural-3-5: Several provenance tags inside one rule, mid-sentence - Severity: Nit
* **Reviewer Lens:** `egm-structural` (also style-3-10)
* **Affected Scope:** `Lines 230-236, 306-307, 310-318, 323-334, 399`
* **Discrepancy Description**: R1.1, R4.3, R4.5, R4.6, R4.8, R4.9, R4.11 and R8.1 each carry two tags, the second starting partway through a sentence. It is unclear where each tag's scope ends.
* **Rationale & Recommendation**: Write one tagged sentence or sub-item per decision, or state in the legend that a tag applies until the next tag.

### structural-3-6: Step 2 heading does not match R2.1 - Severity: Nit
* **Reviewer Lens:** `egm-structural` (also style-3-11)
* **Affected Scope:** `Lines 252-265`
* **Discrepancy Description**: "Output path check" contains R2.1, which is about input and rules paths.
* **Rationale & Recommendation**: Rename it "Path checks", or move R2.1.

### structural-3-7: Some table entries do not point to a rule ID - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** `Lines 422, 576, 581`
* **Discrepancy Description**: Two Risks "Rule" cells are section names ("Glossary", "NFR"). The backstop row in the Messages table has no rule reference.
* **Rationale & Recommendation**: Give the backstop its own rule ID (for example R9.4), and make the Risks references precise.

### structural-3-8: Horizontal rules are used inconsistently - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** `Lines 7, 568, 585, 600, 613`
* **Discrepancy Description**: `---` appears between some H2 sections and not others.
* **Rationale & Recommendation**: Choose one convention and apply it throughout.

### structural-3-9: Inline code span split across a line break - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** `Lines 437-438`
* **Discrepancy Description**: The span `` `linked 1 moves` `` crosses a line break. It is part of the fixed summary line that scripts rely on.
* **Rationale & Recommendation**: Keep the span on one line.

### structural-3-10: The worked-example input reads like fixture CSV - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** `Lines 450-459`
* **Discrepancy Description**: The hand-written summary, with file labels, padded commas and `""`, sits next to a literal CSV output block.
* **Rationale & Recommendation**: Show the literal CSV per file in separate fenced blocks, or turn the summary into a table.

### structural-3-11: Line wrapping is inconsistent - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** `Lines 107-108, 233, 318, 330, 347`
* **Discrepancy Description**: A few lines run long and others break early, unlike the roughly 80-column wrap used elsewhere.
* **Rationale & Recommendation**: Re-wrap these lines to the file's usual width.

### style-3-8: Three synonyms for one concept, plus the undefined "survivors" - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 111-113, 436, 485-491`
* **Discrepancy Description**: The Glossary makes copy, duplicate and dedup synonyms. Alternative A uses "survivors", which is never defined.
* **Rationale & Recommendation**: Use "copy" in prose and keep "duplicates" only in the summary line. Replace "survivors" with "kept rows".

### style-3-12: Long compound sentences - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 18-22, 198-201, 257-265`
* **Discrepancy Description**: Several sentences each chain multiple actions or conditions.
* **Rationale & Recommendation**: Split each into two or three sentences. The Overview sentence can become a list.

### style-3-13: Vague or informal words - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 163, 399-400, 510-512`
* **Discrepancy Description**: "Straight pipeline", "plain Python `str` order", "crash move matching" and "strict shape" are imprecise.
* **Rationale & Recommendation**: Use "pipeline", "Python `str` order (code points)", "raise `TypeError` in move matching" and "a fixed regular expression (R4.6)".

### style-3-16: "Not touched" is less precise than G6 - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 59-60, 415-426`
* **Discrepancy Description**: The table says "not touched", while G6 says "not created and an existing one is not changed".
* **Rationale & Recommendation**: Use G6's wording in the table.

### design-3-4: "1 is the header" conflicts with blank lines allowed before the header - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 428-429` (vs `303-305`, `99-102`)
* **Discrepancy Description**: R4.3 allows blank lines before the header, so the header is not always physical line 1.
* **Rationale & Recommendation**: Define LINE as the 1-based physical line number and drop "(1 is the header)".

### design-3-5: Replacing `--out` has unmentioned side effects on success - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 195, 409-411` (R9.3), `59-60`, `597-598`
* **Discrepancy Description**: `mkstemp` creates the temp file with mode 0600, so `os.replace` changes the mode, owner and group of an existing `--out`. A symlinked `--out` is replaced by a regular file rather than written through.
* **Rationale & Recommendation**: Copy the old file's mode before replacing, and define symlink handling (resolve with `realpath`, or reject). Or list both effects as accepted limits.

### design-3-6: A rejected option from the concepts brief is missing from Alternatives - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 515-521` (Alt E), `281-284` (R3.4)
* **Discrepancy Description**: concepts_brief.md also weighed "normalise patterns too" (strip leading zeros from patterns). The spec drops it with no reason.
* **Rationale & Recommendation**: Add it to Alternative E with its reason for rejection, for example that it would also change patterns that are just `0`.

### design-3-7: The same file under two location names gets only a warning, and the risk is not listed - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 249-250` (R1.5), `572-583`
* **Discrepancy Description**: Scans are counted at both locations, and the file's negative and positive rows can pair into false moves across the two names. There is no Risks row, and the spec does not explain why a warning is chosen over exit 2.
* **Rationale & Recommendation**: Add a Risks row that justifies the warning, or make this case exit 2.

### design-3-8: Splitting a multi-line record can invent a scan - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 335-349` (R4.12)
* **Discrepancy Description**: A continuation line from a real multi-line note that happens to parse as 4 valid fields would be accepted as a scan nobody made.
* **Rationale & Recommendation**: Mention this in R4.12 or Risks, and optionally flag rows that come from a split span in their warning.

### design-3-9: Byte-identical output depends on how the file is opened and on the OS - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 21-22, 53-54` (G4), `407-408` (R9.2)
* **Discrepancy Description**: `\n` endings hold only with `newline=""` and `lineterminator="\n"`. G4 does not say whether byte-identical means on the same platform or on every platform.
* **Rationale & Recommendation**: State both settings in R9.2, and make G4 explicit about cross-platform identity.
