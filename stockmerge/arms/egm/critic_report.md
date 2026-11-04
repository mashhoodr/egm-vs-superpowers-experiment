# Goldfish Review Report

**Target:** `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers-p2/arms/egm/docs/designs/stockmerge.md` (`FeatureRange, lines 1-537`)

**Stage:** 7 (Critic Review), egm-review-loop round 1
**GoldfishContext:** `BRIEF.md` (fixed owner contract)

## Reviewer Status

| Reviewer | Standard | Status |
| --- | --- | --- |
| `egm-design` | feature-spec-standard | completed |
| `egm-structural` | feature-spec-standard | completed |
| `egm-style` | (none) | completed |

## Severity Summary

| Severity | Count |
| --- | --- |
| Blocker | 0 |
| Major | 4 |
| Nit | 27 |

Dedup notes: the missing-risks-section finding was raised by `design` and `structural`, and is merged into `design-1-1`. Style's unsupported-size note is folded into it too. The H3-appendix finding came from `structural` and `style`, merged into `structural-1-1`. The line-233 wrap came from `structural` and `style`, merged into `structural-1-5`.

Verified outside scope: `design` checked CUJ 1 (lines 111-121) and the worked example (lines 403-435) by hand and found both correct. It found the dedup and move rules consistent with the owner answers in `stakeholder_log.md`, and the Alternatives section compliant with the standard.

## Prioritized Findings (Blockers -> Major -> Nits)

### design-1-1: No Risks & Limits section - Severity: Major
* **Reviewer Lens:** `design` (also raised by `structural`; size point also by `style`)
* **Affected Scope:** `Lines 437-522` (new section belongs between Alternatives and NFRs). Scattered risk content is at 230-236, 259-265, 343-345, 461-467 and 517-521.
* **Discrepancy Description**: The feature-spec standard says a spec must call out its failure modes, security implications, scalability limits and their mitigations. The doc has no such section. Risks are scattered across R1.4/R1.5, R3.4/R3.5, R6.5, Alternative D, the error table and one-line NFR bullets. Several risks are not stated anywhere:
  * (a) The scan key can merge two real scans of the same SKU and quantity, made in the same minute at one location but in different exports. This conflicts with the brief's "never lose a real scan" (BRIEF.md line 44) and should be recorded as an accepted loss.
  * (b) A real negative adjustment (write-off) can be greedily linked as a move to an unrelated positive scan within 120 minutes. That hides shrinkage, which conflicts with brief want 2.
  * (c) CSV formula injection: SKU or location text starting with `=`, `+`, `@` or `-` can run as a formula when opened in Excel.
  * (d) Everything is held in memory and move matching costs O(negatives x group size). The doc gives no row ceiling, only an unsupported "thousands of rows" (line 517).
  * (e) Location-name typos turn off dedup and can create false moves. R1.4 covers this, but it is not summarised.
  * Others to list with their existing rule: overwriting an input (R2.2), partial writes (R9.3), leading-zero SKU collisions (`0123` vs `123` really being different SKUs).
* **Rationale & Recommendation**: Add an H2 `## Risks & Limits`. For each risk give the impact, the mitigation (warning, documented acceptance or deferral), the rule ID, and the owner of the decision ([owner] or [builder]). For (c), decide explicitly between "accepted" and "prefix risky cells". Turn the size claim into a stated assumption with a number.

### design-1-2: An unclosed quote can silently swallow many rows, against G5 - Severity: Major
* **Reviewer Lens:** `design`
* **Affected Scope:** `Lines 53-56` (G5), `280-285` (R4.3), `379` (csv.Error backstop), `392-400` (summary counts)
* **Discrepancy Description**: Format B `note` is free text. The reviewer believes Python's default non-strict `csv.reader` continues a field that opens with `"` and never closes across later physical lines. One record would then hold many rows: those rows get no per-line warning, and R counts them as one record, so G5's accounting breaks. If the absorbed text exceeds the csv field size limit, `csv.Error` is raised, and the backstop turns it into exit 2 for the whole run. The reviewer flagged this as unverified because it could not run Python.
* **Rationale & Recommendation**: Check both behaviours on 3.11. If they hold, either detect records that span several physical lines or contain embedded newlines and warn with the line range, or record the case as a known limit and state that an over-limit field ends the run with exit 2.

### design-1-3: Very long quantity strings can end in a traceback, against G5 - Severity: Major
* **Reviewer Lens:** `design`
* **Affected Scope:** `Lines 53-56` (G5), `300-302` (R4.8), `379` (backstop covers only `OSError` / `csv.Error`)
* **Discrepancy Description**: `^[+-]?[0-9]+$` accepts any number of digits. Python 3.11's `int()` raises `ValueError` above its default limit of 4300 digits. The backstop does not catch `ValueError`, so the run ends in a traceback, which G5 forbids.
* **Rationale & Recommendation**: Limit quantity length in R4.8 (for example at most 9 digits) and skip longer values with a warning, or turn any `ValueError` during row parsing into a skipped row. Name the exception types the backstop covers.

### style-1-1: The "only the CLI layer touches the filesystem" claim contradicts R2.1 - Severity: Major
* **Reviewer Lens:** `style`
* **Affected Scope:** `Lines 156-157`, compared with `169-172` and `240-242`
* **Discrepancy Description**: The architecture says the pipeline is pure functions and only the command line layer touches the filesystem. R2.1 and the diagram say steps 3 and 4 open files and turn `OSError` and decode errors into exit 2. A reader cannot tell where I/O happens.
* **Rationale & Recommendation**: State exactly which steps do I/O, for example "Steps 3, 4 and 9 open files; steps 5-8 are pure functions over in-memory lists". Or, if the CLI opens files and passes text in, reword R2.1 to say so.

### design-1-4: "Every exit-2 condition is found before step 9" contradicts the error table - Severity: Nit
* **Reviewer Lens:** `design`
* **Affected Scope:** `Lines 190-192` vs `366-368`, `378`, `383`
* **Discrepancy Description**: R9.3 and the error table list exit-2 cases that happen inside step 9: a missing or unwritable folder, or a failed write. The behaviour is correct; only the wording is wrong.
* **Rationale & Recommendation**: Reword to "every input-related exit-2 condition is found before step 9; step-9 failures leave `--out` untouched because of the temp file".

### design-1-5: G1 "all kept" wording conflicts with R5.4 - Severity: Nit
* **Reviewer Lens:** `design`
* **Affected Scope:** `Lines 45-46` vs `317-321`
* **Discrepancy Description**: Repeated identical rows in a later export can all be removed when an earlier export has at least as many.
* **Rationale & Recommendation**: Say the output keeps as many rows as the highest count in any one export.

### design-1-6: argparse error format and `--help` stdout are not addressed - Severity: Nit
* **Reviewer Lens:** `design`
* **Affected Scope:** `Lines 221-226`, `375`, `391`, `401`
* **Discrepancy Description**: Under `python -m`, argparse names the program `__main__.py` and prints `usage: ... error: ...`, not `stockmerge: error: message`. `--help` prints to stdout and exits 0, which contradicts "Nothing is printed to stdout".
* **Rationale & Recommendation**: Set `prog="stockmerge"`, state the usage-error format, and list `--help` as an exception.

### design-1-7: Rules-file edge cases are not stated - Severity: Nit
* **Reviewer Lens:** `design`
* **Affected Scope:** `Lines 252-256` vs `276-283`
* **Discrepancy Description**: Step 4 defines what happens with a zero-byte file, blank lines before the header, or a header with no rows. Step 3 does not define these cases for the rules file.
* **Rationale & Recommendation**: Make step 3 match step 4 and add a row to the error table.

### design-1-8: Tier tags hide some builder choices - Severity: Nit
* **Reviewer Lens:** `design`
* **Affected Scope:** `Lines 221-223` (R1.1), `288-289` (R4.5), `303-305` (R4.9)
* **Discrepancy Description**: "Abbreviated options are not accepted" is tagged [contract], and the trimming and lower-casing of `Unit` is tagged [owner], but both are builder choices. The Format A time shape is tagged [owner] but comes from the contract. Lines 88-91 tell the owner to look for [builder] tags, so mislabelled choices escape that check.
* **Rationale & Recommendation**: Split mixed rules so each choice carries its own tag.

### design-1-9: Trailing empty columns are made fatal without saying so - Severity: Nit
* **Reviewer Lens:** `design`
* **Affected Scope:** `Lines 272-275`, `283-284`
* **Discrepancy Description**: `concepts_brief.md` planned to check real exports for trailing empty columns. With strict matching, a header like `Scanned At,SKU,Qty,Unit,` exits 2 and 5-field rows are skipped, but the spec does not call this out.
* **Rationale & Recommendation**: State that this is a deliberate choice and that the risk is accepted.

### design-1-10: `\d` in the R4.6 regex matches non-ASCII digits - Severity: Nit
* **Reviewer Lens:** `design`
* **Affected Scope:** `Lines 292-297` vs `300`
* **Discrepancy Description**: In Python, `\d` matches any Unicode digit, so R4.6 is looser than intended and inconsistent with R4.8's `[0-9]`.
* **Rationale & Recommendation**: Use `[0-9]` (or ASCII matching) and say the whole value must match.

### design-1-11: Temp-file permissions, symlinks and hard links - Severity: Nit
* **Reviewer Lens:** `design`
* **Affected Scope:** `Lines 187`, `243-244`, `366-368`
* **Discrepancy Description**: Temp files are typically created with mode 0600. `os.replace` replaces a symlinked `--out` link itself, not its target. `realpath` does not catch hard links to an input.
* **Rationale & Recommendation**: State the expected output mode and the symlink behaviour, and add an `os.path.samefile` check when `--out` exists.

### design-1-12: Ctrl-C during write is not covered - Severity: Nit
* **Reviewer Lens:** `design`
* **Affected Scope:** `Lines 53-58`, `366-368`
* **Discrepancy Description**: An interrupt during step 9 could leave a stray temp file and print a traceback. G6 still holds for `--out` itself.
* **Rationale & Recommendation**: Say whether interrupts are cleaned up with a defined exit code or are out of scope.

### structural-1-1: Appendix sections sit at H3 under Non-Functional Requirements - Severity: Nit
* **Reviewer Lens:** `structural` (also raised by `style`)
* **Affected Scope:** `Lines 525-534`
* **Discrepancy Description**: `### Additional Resources` and `### Future Improvements` appear as subsections of the NFRs in the outline, even though the rule at line 523 shows they were meant to be separate. Future Improvements also repeats Alternative J (lines 504-508).
* **Rationale & Recommendation**: Make both H2, or put them under a `## Appendix` H2. Keep a single cross-reference for `--strict`.

### structural-1-2: Additional Resources entries are not links - Severity: Nit
* **Reviewer Lens:** `structural`
* **Affected Scope:** `Lines 527-529` (compare `87-88`)
* **Discrepancy Description**: These are plain code text, while Open Questions links the same files.
* **Rationale & Recommendation**: Use `../../BRIEF.md`, `../../concepts_brief.md` and `../../stakeholder_log.md` links.

### structural-1-3: Bold paragraphs used as sub-headings - Severity: Nit
* **Reviewer Lens:** `structural`
* **Affected Scope:** `Lines 219, 238, 250, 267, 310, 327, 347, 353, 360`
* **Discrepancy Description**: "**Step N. ...**" works as a heading but does not appear in the outline and cannot be linked to.
* **Rationale & Recommendation**: Change these to `#### Step N. ...`.

### structural-1-4: Horizontal rules are used unevenly - Severity: Nit
* **Reviewer Lens:** `structural`
* **Affected Scope:** `Lines 7, 510, 523, 536`
* **Discrepancy Description**: Rules appear only around the metadata and the last sections, so the visual grouping does not match the heading structure.
* **Rationale & Recommendation**: Use rules between every H2, or only at major part boundaries.

### structural-1-5: Over-long source line - Severity: Nit
* **Reviewer Lens:** `structural` (also raised by `style`)
* **Affected Scope:** `Line 233`
* **Discrepancy Description**: The line runs far past the roughly 80-column wrap used elsewhere.
* **Rationale & Recommendation**: Re-wrap it.

### structural-1-6: Worked-example inputs are not real file contents - Severity: Nit
* **Reviewer Lens:** `structural`
* **Affected Scope:** `Lines 407-413`
* **Discrepancy Description**: The block mixes file labels, format tags and alignment spaces, and leaves out the header rows that R4.2 requires. Fixtures copied from it would exit 2.
* **Rationale & Recommendation**: Label the block as a summary, or show each file as its own block with its header.

### style-1-2: Narrative aside in Non-Goals - Severity: Nit
* **Reviewer Lens:** `style`
* **Affected Scope:** `Lines 62-64`
* **Discrepancy Description**: "totals were left to the builder, who left them out" reads as a story.
* **Rationale & Recommendation**: "Owner confirmed one row per scan. Totals: [builder] out of scope."

### style-1-3: "explainable rule" is vague - Severity: Nit
* **Reviewer Lens:** `style`
* **Affected Scope:** `Lines 30-31`
* **Discrepancy Description**: "Explainable" is neither defined nor testable.
* **Rationale & Recommendation**: "under a fixed, deterministic rule (R6.1, R6.2)".

### style-1-4: "usually means a typo" is unprovable - Severity: Nit
* **Reviewer Lens:** `style`
* **Affected Scope:** `Lines 233-234`
* **Discrepancy Description**: "Usually" is a guess about frequency.
* **Rationale & Recommendation**: "because this can be a typo that turns off dedup and creates false moves". The line wrap is covered by structural-1-5.

### style-1-5: Awkward word order in R3.5 - Severity: Nit
* **Reviewer Lens:** `style`
* **Affected Scope:** `Lines 264-265`
* **Discrepancy Description**: "the output could then not tell a real move from a rule" is hard to parse.
* **Rationale & Recommendation**: "the output could not then tell a real move apart from a rule match".

### style-1-6: Filler word "simply" - Severity: Nit
* **Reviewer Lens:** `style`
* **Affected Scope:** `Line 342`
* **Discrepancy Description**: "simply" adds nothing.
* **Rationale & Recommendation**: "Past 9999 the number has more digits (`M10000`)."

### style-1-7: Subjective reasons for accepting greedy matching - Severity: Nit
* **Reviewer Lens:** `style`
* **Affected Scope:** `Lines 344-345`, `487-488`
* **Discrepancy Description**: "simple/harder to explain" are opinions, "rare crossing cases" claims a frequency nobody has shown, and "crossing" is not defined.
* **Rationale & Recommendation**: Keep the checkable reasons (fixed, deterministic, set by the owner) and describe in one line when greedy matching misses a pair.

### style-1-8: "tidier output" is subjective - Severity: Nit
* **Reviewer Lens:** `style`
* **Affected Scope:** `Line 449`
* **Discrepancy Description**: An aesthetic judgment is used as a Pro.
* **Rationale & Recommendation**: "Each normalised SKU appears with one spelling in the output."

### style-1-9: "a few lines less" is vague - Severity: Nit
* **Reviewer Lens:** `style`
* **Affected Scope:** `Line 494`
* **Discrepancy Description**: It cannot be measured, and the grammatical form is "fewer".
* **Rationale & Recommendation**: "No temporary-file handling."

### style-1-10: Weak reason for rejecting `\r\n` - Severity: Nit
* **Reviewer Lens:** `style`
* **Affected Scope:** `Lines 501-502`
* **Discrepancy Description**: `\r\n` output can also be tested byte for byte.
* **Rationale & Recommendation**: Give a concrete reason, or state it as a builder preference.

### style-1-11: Determinism claim is broader than true - Severity: Nit
* **Reviewer Lens:** `style`
* **Affected Scope:** `Lines 515-516`
* **Discrepancy Description**: The temp file in R9.3 normally gets a random name.
* **Rationale & Recommendation**: "No clock, locale or random value affects the output content."

### style-1-12: Summary-line plurals look like typos - Severity: Nit
* **Reviewer Lens:** `style`
* **Affected Scope:** `Lines 393`, `435`
* **Discrepancy Description**: "removed 1 duplicates" and "linked 1 moves" read as mistakes.
* **Rationale & Recommendation**: Add a sentence saying the format is fixed and never switches to singular.

### style-1-13: Inconsistent terms - Severity: Nit
* **Reviewer Lens:** `style`
* **Affected Scope:** `Lines 55` vs `157`; `187, 247, 366, 520`; `18-19, 45` vs `393, 398`; `45, 175, 228, 310`
* **Discrepancy Description**: The doc uses both "file-system" and "filesystem", uses "folder" without settling on it over "directory", and uses "copies" and "duplicates" for the same thing. "Dedup" has no Glossary entry.
* **Rationale & Recommendation**: Pick one spelling and one word for each, and add a Glossary entry for dedup and copy/duplicate.
