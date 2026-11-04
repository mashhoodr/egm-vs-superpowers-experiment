# Goldfish Review Report

**Target:** `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers-p2/arms/egm/docs/designs/stockmerge.md` (`Lines 1-628`, FeatureRange before `## Detailed Implementation Plan`)

**Stage:** 7 (Critic Review), egm-review-loop round 4
**GoldfishContext:** `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers-p2/arms/egm/BRIEF.md`

## Reviewer Status

| Reviewer | Status | Standard | Raw findings (B / M / N) |
| --- | --- | --- | --- |
| `egm-design` | completed | feature-spec-standard | 0 / 2 / 8 |
| `egm-structural` | completed | feature-spec-standard | 0 / 0 / 9 |
| `egm-style` | completed | none | 0 / 2 / 11 |

After merging duplicates there are 27 findings: **0 Blocker, 4 Major, 23 Nit**. Each finding keeps the severity its reviewer gave it. Where reviewers gave the same issue different severities, the merged finding takes the highest one and the note lists the others. Merged findings list every source id.

Reviewer notes on what they checked:
- `egm-design` checked CUJ 1, the worked example and the summary arithmetic, and found them correct. It found no breach of the brief's contract.
- `egm-structural` found every area the standard requires present. Heading nesting, code fences and tables are well formed. All links resolve.
- `egm-style` did not open the linked files, so the claims that cite them (lines 90-96, 502) were not checked by that lens. `egm-design` did read them.

## Prioritized Findings (Blockers -> Major -> Nits)

### Blockers

None.

### Major

### egm-design-4-1: A bad byte in the ignored note field drops a real scan - Severity: Major
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 296-301` (R4.1); related: 46-49 (G1), 79 (Non-Goals), 340 (R4.10)
* **Discrepancy Description**: R4.1 skips any data row that has an invalid UTF-8 byte in any field. That includes the Format B `note`, which the spec says is never read. A valid timestamp, SKU and count are then lost because of a field the tool ignores. This goes against the brief's "never lose a real scan" and G1. The owner was never asked about encoding, and the rule is neither tagged [builder] nor explained.
* **Rationale & Recommendation**: Skip a row only when the bad byte is in a field the tool uses: Format A `Scanned At`/`SKU`/`Qty`/`Unit`, or Format B `timestamp`/`barcode`/`count`. Ignore a bad byte in the note, with at most a warning. Tag the rule [builder] and add a line to Risks & Limits. Keep exit 2 for a header row with a bad byte.

### egm-design-4-2: R4.11 is tagged as an owner decision, but the owner left it to the builder - Severity: Major
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 340-342` (R4.10, R4.11); tag contract at 95-96 and 229-231
* **Discrepancy Description**: R4.11 tags "A quantity of 0 is kept as a real scan" as [owner]. In `stakeholder_log.md`, round 2, Q7, the owner answered "Your call — pick something reasonable and write down what you chose." The synthesizer checked this at `stakeholder_log.md:49` and `:69`. Lines 95-96 say builder's calls are tagged so the owner can overrule them, and the wrong tag hides this one from the owner. A smaller case: R4.10 tags "The note is never read" as [owner], but the owner only said to ignore notes when matching moves (round 1 Q4).
* **Rationale & Recommendation**: Tag R4.11 as fully [builder]. Split R4.10 into an [owner] part (notes are ignored for moves) and a [builder] part (the note is never read at all). Check every [owner] tag against `stakeholder_log.md` again.

### egm-style-4-1: The decision tags are defined after first use, in two places, with no stated scope - Severity: Major
* **Reviewer Lens:** `egm-style` (also `egm-structural-4-3`, which rated it Nit)
* **Affected Scope:** `Lines 67-68`, `89-96`, `229-231`, `318-342` (R4.5, R4.6, R4.8, R4.9, R4.11)
* **Discrepancy Description**: The tags [owner] and [builder] first appear at lines 67-68. The roles are defined under Open Questions (90-96), and the full legend, including [contract], comes only at 229-231. No text says how far a tag reaches, yet many bullets switch tags mid-sentence (for example R4.5 "[contract] Format A time: [builder] trimmed..."). Only the first Non-Goal carries tags. Line 67 also reads as if it contradicts BRIEF.md line 12 ("one clean inventory, per SKU per location"), and no reason is given.
* **Rationale & Recommendation**: Put one legend in the Glossary, before any rule. State a scope rule (for example "a tag applies up to the next tag"), or split mixed bullets so each has one tag. Tag every Non-Goal or none of them. In the Non-Goals entry, explain why per-SKU totals are out of scope.

### egm-style-4-2: R2.2 is one overloaded sentence with stacked parentheticals - Severity: Major
* **Reviewer Lens:** `egm-style` (also `egm-structural-4-8`, which raised the double parenthetical at line 266 as a Nit)
* **Affected Scope:** `Lines 262-271`
* **Discrepancy Description**: Two parentheticals sit back to back, and "this" in the second could refer to `samefile` or to the whole rule. The bullet mixes three subjects: the equality test, why the check runs before any reading, and what happens when the `--out` folder is missing.
* **Rationale & Recommendation**: Split it into short sentences or sub-bullets: (a) the equality test, (b) how a `samefile` OSError is treated, (c) what `samefile` catches beyond realpath, (d) why the check runs early, (e) the missing-folder behaviour.

### Nits

### egm-design-4-4: Exit-2 cases disagree across G5, the diagram and the exit-code table - Severity: Nit
* **Reviewer Lens:** `egm-design` (also `egm-structural-4-5`, `egm-style-4-6`)
* **Affected Scope:** `Lines 57-61` (G5), `182-186` (diagram), `425-438` (exit table, especially rows 434-436)
* **Discrepancy Description**:
  * G5 names `UnicodeError`, but the catch-all row (434) lists only `OSError` and `csv.Error`.
  * The diagram shows "undecodable" as exit 2 in step 4, but under R4.1 that applies only to a header row.
  * The diagram leaves out R3.2 (rules file with no header) and R2.1 (file fails to open).
  * Row 435 covers only "Rules header wrong (R3.1)". The table is presented as the full list of exit cases.
  * With `surrogateescape`, `UnicodeError` can only happen when the output is encoded (for example a location name from argv that is not valid UTF-8). The spec never says so.
  * "Backstop" is jargon.
* **Rationale & Recommendation**: Use one exception list in all three places. Change row 435 to "Rules header wrong or missing, or not valid UTF-8 (R3.1, R3.2)". Fix the diagram labels to match R2.1, R3.2 and R4.1-R4.2. Say where `UnicodeError` can occur and that it gives exit 2 with `--out` untouched.

### egm-design-4-3: Summary count R is ambiguous for split records - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 447-457`; related: 343-358 (R4.12), 103-105 (Glossary: record number)
* **Discrepancy Description**: R4.12 splits one csv record into one record per physical line. "Data records read" could then mean csv records or assigned record numbers. Only the second reading keeps `W = R - S - D` true.
* **Rationale & Recommendation**: Define R (and S) as counts of assigned record numbers across all exports.

### egm-design-4-5: The atomic write changes file permissions and symlinks - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 62-63` (G6), `200`, `421-423` (R9.3)
* **Discrepancy Description**: A `tempfile` file is created with mode 0600. `os.replace` then drops the permissions of an existing `--out`, and replaces a symlinked `--out` instead of writing through it.
* **Rationale & Recommendation**: State the intended behaviour: copy the existing mode or apply the umask, and say whether a symlink is followed (for example by reusing R2.2's realpath) or replaced.

### egm-design-4-6: How `\n` line endings are produced is not stated - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 419-420` (R9.2); G4 at 54-55
* **Discrepancy Description**: Byte-identical output needs `newline=""` on the output file handle and `lineterminator="\n"` on the csv writer. Without them, Windows newline translation or csv's default `\r\n` changes the bytes.
* **Rationale & Recommendation**: Write both settings into R9.2.

### egm-design-4-7: Alternative E is missing the "normalise patterns too" option - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 527-533`
* **Discrepancy Description**: `concepts_brief.md` lists three options for rule matching. The spec weighs only raw SKU against normalised SKU.
* **Rationale & Recommendation**: Add pattern normalisation as an option and give the reason it was rejected (for example, `01` would become `1` and match more SKUs).

### egm-design-4-9: Trimming PATH makes some valid paths unusable - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 242-244` (R1.2)
* **Discrepancy Description**: The path in `NAME=PATH` is trimmed, so a file whose name starts or ends with a space cannot be passed. The spec does not list this as a limit.
* **Rationale & Recommendation**: Trim only NAME, or list this as a deliberate limit.

### egm-design-4-10: Move matching may slow down well before 100,000 rows - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Line 593` (Risks), `607-610` (NFR Performance)
* **Discrepancy Description**: Scanners that record one item per scan put most rows in the (SKU, 1) group. The accepted quadratic cost within one group can then bite well below the assumed limit.
* **Rationale & Recommendation**: Sort each group by time and search only the ±120-minute window (for example with `bisect`), keeping the R6.2 tie-break. This gives the same greedy result at bounded cost.

### egm-structural-4-1: Alternatives are out of letter order - Severity: Nit
* **Reviewer Lens:** `egm-structural` (also `egm-design-4-8`, `egm-style-4-11`)
* **Affected Scope:** `Lines 556-578`; reference at 624
* **Discrepancy Description**: The alternatives run A-I, then K (563), then J (574).
* **Rationale & Recommendation**: Reorder the sections or rename them, and update line 624 to match.

### egm-structural-4-2: Alternative K does not follow the format of the other alternatives - Severity: Nit
* **Reviewer Lens:** `egm-structural` (also `egm-style-4-11`)
* **Affected Scope:** `Lines 563-572`
* **Discrepancy Description**: K lists three sub-options with inline reasons and one shared rejection reason, instead of Pros / Cons / Reason for Rejection.
* **Rationale & Recommendation**: Split K into three alternatives, use the standard bullets, or note that K compares several options.

### egm-structural-4-4: Open Questions holds definitions instead of questions - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** `Lines 88-96`
* **Discrepancy Description**: The section says "None are open", then defines owner and builder.
* **Rationale & Recommendation**: Keep the statement and the pointer to the decision logs. Move the role definitions to the Glossary (see egm-style-4-1).

### egm-structural-4-6: The risks table's Rule column has entries that are not rule IDs - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** `Lines 588, 593`
* **Discrepancy Description**: These rows cite "Glossary" and "NFR". Every other row cites a rule ID.
* **Rationale & Recommendation**: Use "Glossary: Normalised SKU" / "NFR: Performance", or rename the column "Rule / Section".

### egm-structural-4-7: Horizontal rules are used inconsistently - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** `Lines 7, 580, 599, 614, 627`
* **Discrepancy Description**: Rules separate only some of the H2 sections.
* **Rationale & Recommendation**: Put a rule before every H2, or keep only the one after the metadata and the one before the Implementation Plan.

### egm-structural-4-8: Ragged line wrapping in the source - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** `Lines 238, 266-267, 280-282, 326, 338, 607-608`
* **Discrepancy Description**: Some lines run well past about 80 columns, and others break early mid-sentence. This makes diffs and reviews harder. The double parenthetical at line 266 is covered under egm-style-4-2.
* **Rationale & Recommendation**: Rewrap these paragraphs to the same width.

### egm-structural-4-9: R4.12 has a different layout from its sibling rules - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** `Lines 343-361`
* **Discrepancy Description**: R4.12 uses labelled sub-bullets (Why / Detect / Warn once / Recover / Result / Limit). Every other rule is a single prose bullet.
* **Rationale & Recommendation**: Say at lines 229-231 that complex rules may use this layout, or cut R4.12 to prose and move the detail to the Implementation Plan.

### egm-style-4-3: R2.1 sits under a heading that does not describe it - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 257-261`
* **Discrepancy Description**: The heading is "Step 2. Output path check", but R2.1 is about the input and rules paths, and says no check happens in step 2.
* **Rationale & Recommendation**: Move R2.1 or rename the heading.

### egm-style-4-4: A cross-reference sends the reader away for a one-clause fact - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 29-31`
* **Discrepancy Description**: "(the one case it cannot tell apart is listed under Risks & Limits)" points elsewhere for a fact that fits in one clause.
* **Rationale & Recommendation**: State the case inline: two real identical scans in the same minute, one in each export, are treated as one.

### egm-style-4-5: The Overview sentence chains five actions - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 17-22`
* **Discrepancy Description**: One sentence lists read, dedup, link, categorise and write.
* **Rationale & Recommendation**: Split it, or use a numbered list that matches the pipeline steps.

### egm-style-4-7: The rationale in R3.4 and R3.5 is imprecise - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 286-292`
* **Discrepancy Description**: A pattern starting with `0` can still match zeros inside a SKU (for example `012` in `1012`). R3.5's reason fits `Move` but not `Uncategorised`.
* **Rationale & Recommendation**: Say exactly what each warning protects against, and give a separate reason for each reserved category.

### egm-style-4-8: A parenthetical in R4.8 adds no information - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 334-336`
* **Discrepancy Description**: A 9-digit cap is far below Python's 4300-digit `int()` limit, so the remark tells the reader nothing.
* **Rationale & Recommendation**: Delete it, or give the real reason for 9 digits.

### egm-style-4-9: Speculative and absolute wording - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Line 345`, `90-93`
* **Discrepancy Description**: "most likely a Format B note" is an unsupported guess. "Every behaviour question was answered" is an absolute claim the reader cannot check.
* **Rationale & Recommendation**: Write "for example, a Format B note". Scope the second claim to the questions raised during design.

### egm-style-4-10: Subjective or informal wording in Non-Goals and Alternatives - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 70, 523, 547, 559, 560-561, 565`
* **Discrepancy Description**: Several words are vague or cannot be checked: "Clean handling", "crash move matching", "harder to predict by hand", "none that matter", "most shells and diff tools" and "simplest". The phrase "the test files" is also undefined in a greenfield repo.
* **Rationale & Recommendation**: Replace each with a concrete statement. For example, write "No KeyboardInterrupt handling" and "raises TypeError when compared with naive times".

### egm-style-4-12: Unexplained parenthetical in CUJ 1 - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Line 127`
* **Discrepancy Description**: A new reader may not see that "(two shelves)" means these are two real scans.
* **Rationale & Recommendation**: Write "twice (two real scans of two shelves)".

### egm-style-4-13: The 100,000-row assumption is repeated in Risks and NFR - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 593, 607-610`
* **Discrepancy Description**: The figure and the "not measured" caveat appear in full in both places, and "about" is vague.
* **Rationale & Recommendation**: State the figure and caveat once, in the NFR, and point to it from the Risks row.
