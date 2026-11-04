# Goldfish Review Report: Stage 8 (Intermediate Zoom Out)

**Target:** `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers-p2/arms/egm/docs/designs/stockmerge.md` (lines 1-917)
**Context:** `BRIEF.md` (fixed contract), `zoom_out_report.md` (Stage 5)

## Reviewer Status

| Reviewer | Status |
| --- | --- |
| `egm-zoom-out` (instance A) | completed |
| `egm-zoom-out` (instance B) | completed |

**Summary:** 0 Blocker, 2 Major, 13 Nit, after deduplicating across the two instances.
- **Overall verdict.** Both instances found that the design still solves the brief's root problem, stays inside the fixed contract, and keeps one straight pipeline. Neither found a YAGNI feature at Blocker level.
- **Main cost.** The design's altitude has slipped. The rules have dropped further into code, which is a regression of Stage 5 finding 1-7.
- **Over-engineered additions.** A few additions are more than they need to be: the R4.12 recovery mode, the R2.2 realpath check, bisect matching, and possibly invalid-UTF-8 row skipping.
- **Severity disagreements.** Where the two instances disagreed on severity, both are reported below. The finding is listed under the higher one.

## Stage 5 Findings: Status

| Stage 5 id | Instance A | Instance B | Consolidated |
| --- | --- | --- | --- |
| zoom-out-5 / 1-1: G5 not backed by the design | Resolved | Resolved | Resolved (lines 56-61, 813-820) |
| 1-2: path pre-checks and race window | Resolved | Resolved | Resolved (R2.1, lines 266-268). R2.2 has grown since; see zoom-out-8-4 |
| 1-3: speculative builder warnings | Not resolved | Not resolved | Open; see zoom-out-8-11 |
| 1-4: categorise and sort inside the writer | Not resolved | Not resolved | Open; see zoom-out-8-12 |
| 1-5: Warnings collector | Mostly resolved | Mostly resolved | Wording leftovers only; see zoom-out-8-13 |
| 1-6: unused `Scan.path` and `Scan.line` | Not resolved | Not resolved | Open; see zoom-out-8-12 |
| 1-7: implementation detail in the rules | Regressed | Regressed | Regressed; see zoom-out-8-1 |
| 1-8: `[owner]` decisions not traceable | Not resolved | Partial | Partial. The tags help, but R6.3 still has no inline owner quote; see zoom-out-8-14 |

## Prioritized Findings (Blockers -> Major -> Nits)

### zoom-out-8-1: Rules section has dropped further into code (regression of 1-7) - Severity: Major (B) / Nit (A)
* **Reviewer Lens:** `egm-zoom-out` (A finding 1, B M2)
* **Affected Scope:** Lines 243, 271-276, 305-310, 330-331, 335-337, 345-348, 363-365, 372-374. Also the plan at 692-695 and 700-709.
* **Discrepancy Description**: The R-rules are the behaviour spec that the tests target, but they now name specific implementation details:
  * `argparse prog=`
  * `os.path.realpath` and `os.path.samefile`
  * `utf-8-sig` and `surrogateescape`
  * a `strptime` format string
  * full regexes
  * Python's 4300-digit `int()` limit
  * `next(csv.reader([line]), [])` and `csv.field_size_limit(2**31 - 1)`

  Several of these are repeated word for word in the Detailed Implementation Plan, so the two have to be kept in step.
* **Rationale & Recommendation**: State each rule as behaviour. Examples:
  * "a quote cannot run past the end of its own line"
  * "`--out` must not be the same file as any input"
  * "a quantity is an optional sign followed by 1-9 digits"

  Keep the calls, regexes and interpreter limits only in the plan. Instance A rated this Nit "but growing". Instance B rated it Major because the Critic and Comprehension additions made it substantially worse.

### zoom-out-8-2: R4.12 multi-line recovery is over-specified - Severity: Major (B) / Nit (A)
* **Reviewer Lens:** `egm-zoom-out` (B M1, A finding 2)
* **Affected Scope:** Lines 356-374 (R4.12), 286-287 (R3.2 applies it to the rules file), 582-592 (Alternative K), 700-709 and 746-748 (plan, including the shared `iter_records` helper)
* **Discrepancy Description**: Both instances agree the risk is real. A Format B free-text note with an unclosed quote would otherwise make `csv.reader` swallow the scans that follow, which breaks "never lose a real scan". They disagree on the fix.
  * **Instance B (Major).** The design already accepts that a real multi-line note is split, with its continuation lines skipped (369-371). So "detect a record spanning lines, then re-parse per line" gives the same rows and the same record numbers as "always parse each physical line on its own". The only difference is the range warning. The two-mode approach adds:
    * a line-capturing generator
    * `line_num + 1` arithmetic
    * span detection
    * a `PATH:START-END` warning format
    * Alternative K
    * an extra test path
  * **Instance A (Nit).** The behaviour is warranted and Alternative K weighed the options. The excess is the five-part mini-spec with code in it, and applying the recovery to the rules file. A swallowed rule cannot lose a scan.
* **Rationale & Recommendation**:
  * B: specify a single mode, where each physical line is one CSV record. Move "multi-line quoted fields not supported" to Non-Goals, and drop the span detection, the range warning and Alternative K.
  * A: at minimum, shorten R4.12 to Why, Behaviour and Warning. For the rules file, either exit 2 on a multi-line record or state that reusing the helper costs nothing.

### zoom-out-8-3: Invalid-UTF-8 row skipping conflicts with the Non-Goal and the diagram - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A finding 4, B N1)
* **Affected Scope:** Lines 305-313 (R4.1), 84-85 (Non-Goal: other encodings), 189 and 192 (diagram: "undecodable -> exit 2"), 448 and 450 (messages table), 690-695 and 743-745 (plan)
* **Discrepancy Description**: The feature reaches five places, including a separate rules-file variant. Three things conflict with it:
  * The Non-Goal reads as if this case is out of scope.
  * B notes that the diagram still says an undecodable file is exit 2, which contradicts R4.1.
  * B also notes the feature half-supports Latin-1 exports: the ASCII header matches, then some rows are skipped.
* **Rationale & Recommendation**: The two instances split.
  * **A.** The mechanism is small and justified: one bad byte in a note should not end the run, given G5's skip-and-warn. Keep it, but reword the Non-Goal, and consider exit 2 for bad bytes in the rules file.
  * **B.** It is speculative, since the brief is silent and no real export was available (608). The G5 backstop already exits 2 with a message naming the file, and `--out` is untouched. Revert to file-level exit 2 unless the owner asks for row-level tolerance.

  Either way, fix the diagram labels at 189 and 192.

### zoom-out-8-4: R2.2 uses two same-file mechanisms where one is enough - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A finding 3, B N3)
* **Affected Scope:** Lines 269-280 (R2.2), 261-262 (R1.5 depends on it), 610 (Risks row)
* **Discrepancy Description**: The realpath comparison is redundant once samefile is used:
  * If `--out` does not exist, it cannot be an input.
  * If an input is missing, step 3 or 4 exits 2 anyway.

  Samefile alone also covers hard links and case-insensitive disks, including the owner's macOS.
* **Rationale & Recommendation**: Use one rule: "if `--out` exists and is the same file as any input or the rules file, exit 2". Leave the call itself to the plan.

### zoom-out-8-5: Bisect window search is premature optimisation - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A finding 5, B N4)
* **Affected Scope:** Lines 621-626 (NFR Performance), 771-779 (moves plan), 607 (Risks row)
* **Discrepancy Description**: The figure of about 100,000 rows is admitted to be a guess. Groups keyed by `(sku_norm, qty_each)` are small, so a linear scan of each group gives the same result. A linear scan is also easier to check by hand against R6.2 and does not need parallel minute lists.
* **Rationale & Recommendation**: Specify a linear scan of the group, and note bisect as an option if a measured run is too slow. Drop the performance half of Risks row 607.

### zoom-out-8-6: Risks & Limits repeats mitigations that are already rules - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A finding 6). B explicitly did not flag this: it called the table the right altitude and said the duplicates are harmless.
* **Affected Scope:** Lines 596-611, especially rows 603, 604, 610 and 611
* **Discrepancy Description**: Rows 600-602, 606 and 609 record owner-accepted trade-offs, which is useful. Rows 603-604 and 610-611 only restate R2.2, R9.3, Alternative H, R1.4 and R4.12.
* **Rationale & Recommendation**: Keep the rows that record an accepted limit or an assumption. Drop or merge the rows whose mitigation is only a rule ID.

### zoom-out-8-7: Decision tags change inside one sentence - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A finding 7, B N8)
* **Affected Scope:** Lines 101-105 (Glossary convention), 240-242, 326-327, 330-338, 343-345, 349-353, 423-424
* **Discrepancy Description**: A sentence such as R4.5's "[contract] Format A time: [builder] trimmed ... [builder] This also accepts" is hard to read. Both instances consider the tags themselves useful; B notes they serve the Verification Plan's coverage rule at 910-911.
* **Rationale & Recommendation**: Use one tag per bullet, with `[builder]` sub-bullets under an `[owner]` or `[contract]` sentence.

### zoom-out-8-8: Glossary overlap for Normalised SKU - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A finding 8)
* **Affected Scope:** Lines 114-115 (Trim), 118-121 (Normalised SKU)
* **Discrepancy Description**: The Normalised SKU entry spells out `str.strip()` again, even though Trim is now defined.
* **Rationale & Recommendation**: Write "trimmed, lower-cased, leading `0`s removed".

### zoom-out-8-9: R1.2's UTF-8 check repeats a downstream error - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (B N2)
* **Affected Scope:** Lines 248-251; see also 793-794 and 815
* **Discrepancy Description**: A location name that cannot be encoded already fails in `write_csv` with a `UnicodeError`. That becomes exit 2 with `--out` untouched. This is the same early-check pattern that Stage 5 1-2 rejected.
* **Rationale & Recommendation**: Drop the check, or keep it only for a clearer early message and say that this is the reason.

### zoom-out-8-10: The csv field size limit is set in the wrong layer - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (B N7)
* **Affected Scope:** Lines 372-374, 807
* **Discrepancy Description**: A reader concern is handled by changing process-wide state in `cli.main`. The backstop already turns `csv.Error` into a clean exit 2.
* **Rationale & Recommendation**: Drop the call, or set it in readers.py and state the reason once.

### zoom-out-8-11: Speculative builder warnings remain (Stage 5 1-3) - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A finding 9, B N5)
* **Affected Scope:** Lines 261-262 (R1.5), 295-301 (R3.4's leading-`0` warning, R3.5), 852-853 (tests)
* **Discrepancy Description**: These warnings still have no stated need. Two related warnings are now justified:
  * The R4.2 "no valid rows" warning (319-321) is justified by Risks row 609. Both instances say it can stay.
  * Alternative E (540-546) partly justifies the R3.4 warning (A).
* **Rationale & Recommendation**: Keep R1.4. Move R1.5, R3.4's leading-`0` warning and R3.5 to Future Improvements unless the owner confirms them.

### zoom-out-8-12: Categorise and sort in writer.py, duplicate helpers, unused Scan fields (Stage 5 1-4, 1-6) - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A finding 9, B N6)
* **Affected Scope:** Lines 785-788 (`build_rows`), 201-205 (the diagram shows steps 7 and 8 as separate), 668-672 (`Scan.ident` duplicates `input_order`), 224 (`Scan.path` and `Scan.line`)
* **Rationale & Recommendation**: The same as Stage 5:
  * Move categorise and sort out of writer.py.
  * Keep one of `ident` / `input_order`.
  * Drop `Scan.path` and `Scan.line`.

### zoom-out-8-13: Warnings collector wording leftovers (Stage 5 1-5) - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A finding 9, B N8)
* **Affected Scope:** Lines 676-681, 811-813
* **Discrepancy Description**: The text still says Warnings "collects warning strings in order" and keeps a count, and that cli prints each warning "as it is collected". Nothing uses the stored list or the count, because S comes from read_export's return value (689, 712-714).
* **Rationale & Recommendation**: Describe Warnings as a plain writer and remove the "collect" wording.

### zoom-out-8-14: R6.3 owner decision not quoted inline (Stage 5 1-8) - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A finding 9, B N8)
* **Affected Scope:** Lines 404-405 (R6.3), 90-94 (Open Questions)
* **Discrepancy Description**: R6.3 departs from the brief's "Everything categorised by my rules" without an inline citation of the owner's answer.
* **Rationale & Recommendation**: Add a one-line citation in the style of Alternative A ("round N, QM"), as at line 515.

### zoom-out-8-15: R2.1 is placed under the wrong step - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (B N8)
* **Affected Scope:** Lines 266-268
* **Discrepancy Description**: R2.1 sits under "Step 2. Output path check" but describes how steps 3 and 4 behave when they open the files.
* **Rationale & Recommendation**: Move it to step 3/4 or to the messages section.

## Deliberately Not Flagged (both instances unless noted)
- The G5 backstop catches `OSError`, `UnicodeError` and `csv.Error` and lets programming errors through (814-820). Both instances consider this the right fix.
- Alternative K's comparison of the simpler options (A). Note that B's zoom-out-8-2 argues that one of those options could replace the chosen mode.
- The Risks rows that record owner-accepted trade-offs (600-602, 609).
- The new Glossary entries Owner, Builder, Trim and Record number (B).
- The decision tags as a mechanism (B).
- Several choices B named as fine:
  * the temp file plus `os.replace`
  * grouping move candidates by `(sku_norm, qty_each)`
  * R1.4
  * the owner-settled rules R5.4, R6.2 and R6.5

---
## Resolution (Elephant, egm-resolve rules)
- zoom-out-8-1 (Major per instance B): PROPOSE FIX (part) — stdlib call names, `prog`, `strptime`,
  `realpath`/`samefile`, `surrogateescape`, regexes and `int()` wording moved out of the rules into
  plain behaviour; they remain in the Detailed Implementation Plan. CONTEST (part): accepted value
  shapes (e.g. 1-9 ASCII digits, `YYYY-MM-DDTHH:MM:SS[.f]`) stay in the rules because they are the
  behaviour tests check (Verification Plan: one test per rule ID).
- zoom-out-8-2 (Major per instance B): PROPOSE FIX — R4.12 replaced by "each physical line is one
  record"; detection/range warning removed; Alternative K and plan updated.
- Diagram vs R4.1 contradiction (Nit): fixed. Other Nits: declined.
