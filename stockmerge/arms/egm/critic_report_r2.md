# Goldfish Review Report

**Target:** `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers-p2/arms/egm/docs/designs/stockmerge.md` (`FeatureRange, lines 1-593`)

Stage 7 (Critic Review), egm-review-loop round 2. GoldfishContext: `arms/egm/BRIEF.md` (fixed contract).

## Reviewer Status

| Reviewer | Status |
| --- | --- |
| `egm-design` | completed |
| `egm-structural` | completed |
| `egm-style` | completed |

**Severity totals (after deduplication):** 0 Blocker, 2 Major, 21 Nit.

**Triage notes:**
- Three reviewers reported the duplicated "the counts the counts" at L429. Style rated it Major, the other two Nit. It is a one-word typo whose intended meaning is clear, so it is triaged as a Nit (style-2-1).
- Three reviewers reported that R4.12 comes before R4.11 at L327-341. Structural rated it Major, the other two Nit. Both IDs exist and are stable; only the order is wrong. It is triaged as a Nit (structural-2-1).
- Design's Major on R4.12 was checked against the target at L327-338. The rule does re-read each physical line with `csv.QUOTE_NONE`, so a properly quoted note that contains a comma, on a swallowed line, splits into 5 fields and is dropped. The finding stands.
- Ids are per report. Where findings were merged, the "Merged from" line gives each reviewer's own item number from its raw report.

## Prioritized Findings (Blockers -> Major -> Nits)

### design-2-1: R4.12 recovery drops valid scans that have quoted fields - Severity: Major
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 327-338` (R4.12). Also Alternatives Considered (L473-546).
* **Discrepancy Description**: When a record spans several physical lines, every one of those lines is re-parsed with `csv.reader([line], quoting=csv.QUOTE_NONE)`. In non-strict mode, an unclosed `"` is closed by the next `"` on a later line, so the joined span easily takes in a healthy row that has a properly quoted field. Re-read without quoting, that healthy row breaks apart. Example (Format B):
  ```
  2026-03-05T10:00:00,111,5,"oops
  2026-03-05T10:01:00,222,3,"shelf 2, top"
  2026-03-05T10:02:00,333,1,
  ```
  Lines 2-3 become one record. Under R4.12, line 3 read with `QUOTE_NONE` gives 5 fields and is skipped as malformed, so a real scan is lost. This contradicts BRIEF want 1 ("never lose a real scan") inside the very mechanism meant to protect it. The recovery strategy has no entry in Alternatives Considered.
* **Rationale & Recommendation**: Re-read each physical line with default quoting (`csv.reader([line])`). In non-strict mode the bad line still yields 4 fields, and properly quoted lines parse correctly. Alternatively, apply `QUOTE_NONE` only to the line that holds the odd quote. Add an Alternatives entry for the recovery choice (exit 2, split with no quoting, split with default quoting). Add the 3-line sample above as a test.

### design-2-2: R2.2 "--out is not an input" check misses aliases - Severity: Major
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 256-261` (R2.2), Risks row at `Line 561`.
* **Discrepancy Description**: `os.path.realpath` only resolves symlinks. It does not fold letter case or detect hard links. On macOS's default case-insensitive APFS, `--out INV.csv` with input `inv.csv` passes the check, and step 9's `os.replace` then overwrites the input. The spec calls this "the only check made before reading, because ... writing would destroy an input", but the chosen mechanism does not keep that promise.
* **Rationale & Recommendation**: When `--out` already exists, compare it with each input and the rules path using `os.path.samefile` (device and inode). Use `realpath` only when `--out` does not exist yet. Add a test with a case-variant `--out`.

### style-2-1: Duplicated words in the summary-line paragraph - Severity: Nit
* **Reviewer Lens:** `egm-style` (rated Major), `egm-structural` (Nit), `egm-design` (Nit). Merged from: style #1, structural #2, design Nit 2.
* **Affected Scope:** `Lines 429-430`
* **Discrepancy Description**: "The counts the counts cover export files only (not the rules file):". The line is also much longer than the lines around it, which points to an edit that was spliced in.
* **Rationale & Recommendation**: Rewrite as "The counts cover export files only, not the rules file:" and re-wrap the line.

### structural-2-1: R4.12 comes before R4.11 - Severity: Nit
* **Reviewer Lens:** `egm-structural` (rated Major), `egm-style` (Nit), `egm-design` (Nit). Merged from: structural #1, style #7, design Nit 3.
* **Affected Scope:** `Lines 327-341`
* **Discrepancy Description**: Step 4's rules run R4.10, R4.12, R4.11. L223 says the tests use these rule IDs, so readers who scan for an ID depend on the order.
* **Rationale & Recommendation**: Move the R4.11 bullet (L339-340) between R4.10 and R4.12. Do not renumber, because other rules already cite R4.12.

### style-2-2: Mixed-tag rules and unwrapped lines - Severity: Nit
* **Reviewer Lens:** `egm-style`, `egm-structural`. Merged from: style #6, structural #5, structural #8.
* **Affected Scope:** `Lines 224-225` and `304-325` (R4.5, R4.6, R4.9; also R1.1, R4.3, R4.8, R4.11). Long lines at `312` and `324`.
* **Discrepancy Description**: Provenance tags appear mid-sentence, sometimes several per rule (for example "R4.5 [contract] Format A time: [builder] trimmed ..."). The convention at L223-225 does not say how far a tag reaches. Lines 312 and 324 run past the roughly 80-column wrap used elsewhere.
* **Rationale & Recommendation**: Add to L225: "A tag applies to the text that follows it, up to the next tag." Or split each mixed-tag rule into one sentence (or sub-bullet) per tag, with the tag first. Re-wrap L312 and L324.

### structural-2-2: Owner/builder definitions sit in Open Questions - Severity: Nit
* **Reviewer Lens:** `egm-structural`, `egm-style`. Merged from: structural #4, style #11 (first part).
* **Affected Scope:** `Lines 85-93`; first tag use at `Line 65`.
* **Discrepancy Description**: Open Questions defines **owner** and **builder** and explains the tag scheme. That is glossary content. Tags are first used at L65, before either definition.
* **Rationale & Recommendation**: Move the definitions into the Glossary (L95). Keep Open Questions to "None are open" plus the source links.

### style-2-3: Forward reference to `cli.main` - Severity: Nit
* **Reviewer Lens:** `egm-style`. From: style #11 (second part).
* **Affected Scope:** `Line 413` (Messages table)
* **Discrepancy Description**: The table names `cli.main`, a module that only appears in the Detailed Implementation Plan, after the audited range.
* **Rationale & Recommendation**: Say "the command line layer" instead.

### style-2-4: Alternative I has no real Cons or reason - Severity: Nit
* **Reviewer Lens:** `egm-style`, `egm-structural`. Merged from: style #8, structural #9.
* **Affected Scope:** `Lines 534-539`
* **Discrepancy Description**: "Cons: none that matter for correctness" is a judgement, not a con. "Most shells and diff tools" cannot be checked. "Reason for Rejection: builder preference:" has two colons in a row. The standard's Alternatives Rule asks for a specific, documented reason.
* **Rationale & Recommendation**: Name the concrete reason, for example "[builder] `\n` matches the test fixtures' line endings". Or drop the entry and keep the decision only in R9.2.

### style-2-5: "Singular" example shows the plural form - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 427-429`
* **Discrepancy Description**: "never switches to the singular (`linked 1 moves`)". The text in brackets is the plural form the tool keeps, so a reader can take it as the form that is avoided.
* **Rationale & Recommendation**: "always uses the plural, for example `linked 1 moves`, never `linked 1 move`".

### style-2-6: Mixed scanner/format naming - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 33-34`, `Line 509`
* **Discrepancy Description**: "scanner B drops leading zeros (`00123` from scanner 1 is `123` from scanner 2)". BRIEF uses "scanner 1/2" and "Format A/B"; "scanner B" mixes the two schemes.
* **Rationale & Recommendation**: Use "Format B (scanner 2)" on first use, then "Format B".

### style-2-7: CUJ 1 says both files contain the same literal scan - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 119-122`
* **Discrepancy Description**: "Both contain the scan 'SKU `00123`, 1 case, 05/03/2026 14:30'". `shop2.csv` holds `123`, count 12 and `:41` seconds. The two rows are the same scan only after normalisation.
* **Rationale & Recommendation**: "Both contain the same scan: `shop.csv` as `00123`, 1 case, 14:30; `shop2.csv` as `123`, 12, 14:30:41."

### style-2-8: Conflicting provenance in a Non-Goal - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 64-65`
* **Discrepancy Description**: "The owner confirmed one row per kept scan; totals are out of scope [builder]." The decision is credited to the owner but tagged [builder], so it is unclear who decided it.
* **Rationale & Recommendation**: Tag the two clauses separately ([owner] and [builder]), or drop one of the tags.

### style-2-9: Unquantified size claim in Risks - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Line 560`; see also NFR `Line 572`.
* **Discrepancy Description**: "Accepted: stock-takes are far smaller" is unquantified, and the size assumption is already stated in the NFR.
* **Rationale & Recommendation**: "Accepted: assumed run size is at most 100,000 rows (see NFR)."

### style-2-10: Synonyms copy / duplicate / dedup - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 110-112` (Glossary) and throughout.
* **Discrepancy Description**: The three terms are defined as synonyms and used interchangeably.
* **Rationale & Recommendation**: Use "copy" in the prose. Keep "duplicates" only where the fixed summary line needs it.

### structural-2-3: Inconsistent horizontal rules - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** `Lines 7, 547, 564, 579, 592`
* **Discrepancy Description**: `---` appears before some H2 sections and not others, with no pattern.
* **Rationale & Recommendation**: Put a rule before every H2, or keep rules only after the metadata and before the Detailed Implementation Plan.

### structural-2-4: Step 2 name differs from the diagram - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** `Line 251` vs `Line 173`
* **Discrepancy Description**: The diagram says "check --out", but the heading says "Step 2. Paths".
* **Rationale & Recommendation**: Rename the heading to "Step 2. Output path check", or relabel the diagram box.

### structural-2-5: Risks "Rule" column mixes reference kinds - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** `Lines 551-562` (cells at L555, L560)
* **Discrepancy Description**: Most cells hold rule IDs, but one says "Glossary" and one says "NFR".
* **Rationale & Recommendation**: Use explicit section references ("Glossary: Normalised SKU", "Non-Functional Requirements: Performance"), or note in the column header that a cell can hold a section reference.

### design-2-3: Trailing empty header cell is fatal - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Line 558` (Risks); R4.2 `Lines 288-295`
* **Discrepancy Description**: A header like `Scanned At,SKU,Qty,Unit,`, a common artefact of re-saving in Excel, fails the whole run. "The contract fixes the headers" overstates BRIEF, which fixes which header identifies a format, not that trailing empty cells must be fatal. It is a Nit because exit 2 is loud, not silent loss.
* **Rationale & Recommendation**: Drop trailing empty cells before matching, or state the real builder reason for keeping the failure.

### design-2-4: "Outer spaces" understates `str.strip()` - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Glossary `Line 106`; R1.2, R4.3, R4.4 and other trimming references.
* **Discrepancy Description**: `str.strip()` also removes tabs, non-breaking spaces and other Unicode whitespace.
* **Rationale & Recommendation**: Name the exact function (or the exact characters) so tests and code agree.

### design-2-5: R1.5 "same PATH" is underspecified - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Line 248` (R1.5)
* **Discrepancy Description**: It does not say whether "same PATH" means the string as given or the resolved file.
* **Rationale & Recommendation**: Specify the comparison (string, `realpath` or `samefile`), and keep it consistent with the fix for design-2-2.

### design-2-6: R3.2 cites R4.3, which conflicts on field count - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 267-272` (R3.2)
* **Discrepancy Description**: "read like an export (R4.1, R4.3, R4.12)", but R4.3 requires exactly 4 fields while R3.2 requires 2.
* **Rationale & Recommendation**: Say which parts of R4.3 apply (blank-line handling, header detection).

### design-2-7: Atomic replace changes output permissions and symlinks - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 400-402` (R9.3)
* **Discrepancy Description**: `mkstemp`/`NamedTemporaryFile` create files with mode 0600, so after `os.replace` the output loses the permissions of the file it replaced. A symlinked `--out` is replaced by a regular file instead of being written through.
* **Rationale & Recommendation**: State that this is accepted, or `chmod` the temp file to match the existing file (or the umask) before the replace.

### design-2-8: Usage text needs an explicit `prog` - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 232-234` (R1.1)
* **Discrepancy Description**: The committed text `usage: stockmerge merge ...` will not appear under `python -m stockmerge`, where argparse's default prog is `__main__.py`.
* **Rationale & Recommendation**: Say in the rule that `prog="stockmerge"` is set explicitly.

## Confirmed Without Findings

- **Design:** CUJ 1, CUJ 2 and the worked example were re-derived by hand (dedup, surviving rows, move pairing and tie-break, code-point sort, summary counts W = R - S - D = 4) and match the rules. The owner, builder and contract tags match `stakeholder_log.md`. The claims about `fromisoformat`, `strptime` and `int()` were checked and are correct.
- **Structural:** Every area the standard requires is present. The heading hierarchy has no skipped levels. The three relative links resolve. The Alternative A citation (round 3, Q1) matches `stakeholder_log.md` L81-94.
- **Style:** No hyperbole, marketing language or praise or criticism of code was found.
