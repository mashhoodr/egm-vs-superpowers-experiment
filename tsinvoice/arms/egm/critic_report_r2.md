# Goldfish Review Report

**Target:** `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers-p3/arms/egm/docs/designs/tsinvoice.md` (`FeatureRange, lines 1-607`)

## Reviewer Status

| Reviewer | Status |
| --- | --- |
| `egm-design` | completed |
| `egm-structural` | completed |
| `egm-style` | completed |

**Severity totals (after dedupe):** Blocker 0, Major 8, Nit 31.

## Findings Index

When several reviewers raised the same point, it is listed once under the first reviewer's id. The other lenses are named in the summary.

| id | severity | scope | summary |
| --- | --- | --- | --- |
| egm-design-2-1 | Major | Stage 3 277-278, Stage 5 326-331, DL 452, Alt E 517-523 | Keeping seconds in Format B breaks a phone-to-desktop handoff inside one minute: the gap is negative, so there is no join, it is billed twice as rounded sessions, and it produces an overlap warning |
| egm-design-2-2 | Major | G6 60-64, CUJ 3 137-145, Stage 8 369-381, Risks 561 | Overlap warnings fire on repeats the owner calls legitimate (k(k-1)/2 per group), which weakens the main double-billing safeguard |
| egm-structural-2-1 | Major | 216-223 vs 407-428 | The normative fatal-message and exit-code tables leave out malformed CSV (csv.Error); also raised by design |
| egm-structural-2-2 | Major | Goals 42-64, DL 472 | The primary user and success criteria (R1.12) appear only in a Decisions Log row |
| egm-structural-2-3 | Major | 216-224, 245, Risks | The CSV-reading rule for both file types sits inside Stage 2, and "both stages" is never defined; also raised by style |
| egm-style-2-1 | Major | Non-Goals 71, Stage 8 378-380, Risks 561 | "G6 warns about edited entries" overclaims: the warning fires only when the two versions share a client and overlap in time |
| egm-style-2-2 | Major | G6 60-64 vs 203-211, 284-288 | G6 leaves out the long-entry warning and miscounts the duplicate-PATH warnings; also raised by structural and design |
| egm-style-2-3 | Major | 174-175 | The Phase 1 summary of fatal cases leaves out invalid rates rows and implies that bad export rows are fatal |
| egm-design-2-3 | Nit | 284-288, 385-387 | The long-entry warning repeats for each source row before dedupe |
| egm-design-2-4 | Nit | 233-236, 351-353, 423-428 | Unbounded Decimal can raise InvalidOperation (traceback, exit 1), and no catch-all exit rule exists |
| egm-design-2-5 | Nit | 216-223, 355, 374 | Newlines or `'` inside fields break one-line warnings and their quoting |
| egm-design-2-6 | Nit | 398-405, Risks 567 | The atomic-write claim has no fsync, so it does not cover power loss |
| egm-design-2-7 | Nit | 203-211, Risks 561 | Duplicate PATHs are compared as strings, so `./x.csv` or a symlink is missed |
| egm-design-2-8 | Nit | 356-357, 371-373 | A session span includes unbilled join gaps, so false overlaps are possible |
| egm-design-2-9 | Nit | Glossary 94-98 | The effects of casefold (ß = ss) go beyond "ignoring case" and are not recorded as intended |
| egm-structural-2-4 | Nit | 407-445 | Reference tables are H3 siblings of the numbered stages |
| egm-structural-2-5 | Nit | CUJs 120-169 | CUJs differ in form: commands, exit codes and the "stderr identical" check in CUJ 6 are missing |
| egm-structural-2-6 | Nit | 108, 275, 376-377 | [D] tags and Decisions Log rows do not match one to one |
| egm-structural-2-7 | Nit | 22-23, 82, 522, 537 | Cross-references to the Decisions Log are plain text, not anchor links |
| egm-structural-2-8 | Nit | 210-211 | A code span breaks across a line, and the example drops the `--tracker` prefixes |
| egm-structural-2-9 | Nit | 7, 555, 578, 592, 606 | Horizontal rules are used inconsistently |
| egm-structural-2-10 | Nit | 594-604 | Future Improvements comes after Additional Resources |
| egm-structural-2-11 | Nit | 180-192 | The architecture diagram leaves out the duplicate-PATH and unrated-session warning sources |
| egm-style-2-4 | Nit | 34 | Persuasive wording ("fixed, exact rules, not guesswork") |
| egm-style-2-5 | Nit | Glossary 94-96 | "Standard canonical caseless form" is wrong: the standard uses NFD, the spec uses NFC |
| egm-style-2-6 | Nit | 105 | The "Input order" definition is awkward |
| egm-style-2-7 | Nit | 17 | "Python 3.11" should be "3.11+" to match BRIEF |
| egm-style-2-8 | Nit | 123, 130-131 | CUJ example rows use an informal notation instead of literal CSV |
| egm-style-2-9 | Nit | 143-145 | CUJ 3 does not give the exact overlap-warning count |
| egm-style-2-10 | Nit | 163 | "(or not created)" in CUJ 5 contradicts its Given |
| egm-style-2-11 | Nit | 235-236 | The negative-rate sentence repeats what the regex already says |
| egm-style-2-12 | Nit | 250 vs 266 | Header casing differs from BRIEF |
| egm-style-2-13 | Nit | 287-288 | "Catches day typos" overstates what the long-entry warning does |
| egm-style-2-14 | Nit | 303 | One row of the reason table holds two reasons |
| egm-style-2-15 | Nit | 387, 401-403 | Lines in Stage 9 are too long |
| egm-style-2-16 | Nit | 63, 455, 473, 475 | Filler or subjective wording |
| egm-style-2-17 | Nit | 496-498 | Alternative B says the same thing in Cons and in Reason for Rejection |
| egm-style-2-18 | Nit | Risks 569, NFR 584-585 | "Group" means two different scopes (join groups vs per-client overlap) |
| egm-style-2-19 | Nit | DL 472 | The success criterion "owner sends without hand edits" cannot be measured by the tool |

## Prioritized Findings (Blockers -> Major -> Nits)

No Blockers were reported. Structural and design both say the spec meets every area of `feature-spec-standard`: Problem, Goals and Non-Goals, architecture, nine alternatives each with a rejection reason, and Risks plus Security.

### Seconds precision breaks phone-to-desktop joins - Severity: Major
* **Reviewer Lens:** `egm-design` (egm-design-2-1)
* **Affected Scope:** `Lines 277-278, 326-331, 452, 517-523`
* **Discrepancy Description**: Format B keeps seconds; Format A has none. A phone entry runs 09:00:30 + 7 min, so it ends 09:07:30. The desktop entry then starts 09:07. The gap is -30 s, so R2.2 gives no join. The result is two separately rounded sessions (12 + 12 = 24 instead of 18) and an overlap warning. This is the normal way a user switches apps, which is BRIEF want #2. The arguments in Alternative E against truncating weigh false joins and ignore the false non-joins this choice creates. The false-duplicate case it cites can barely happen.
* **Rationale & Recommendation**: Compare gaps and dedupe keys at minute granularity, for example by truncating Format B to the minute for those comparisons only. Or define a mixed-precision rule. If seconds are kept, rewrite Alternative E and the Decisions Log row to weigh both sides, and add a worked example of the handoff.

### Overlap warnings fire on owner-sanctioned repeats - Severity: Major
* **Reviewer Lens:** `egm-design` (egm-design-2-2)
* **Affected Scope:** `Lines 60-64, 137-145, 369-381, 561`
* **Discrepancy Description**: R1.1 says identical entries inside one export are real work, yet k copies produce k(k-1)/2 overlap warnings. The same flood happens when one PATH is given under two NAMEs. The Risks table names the overlap warning as the main double-billing mitigation. Warnings on legitimate data teach the user to ignore it.
* **Rationale & Recommendation**: Skip pairs that share a Stage 4 duplicate key, or collapse warnings to one per overlapping group. If the current behaviour is on purpose, say so in G6 and CUJ 3.

### Normative error and exit tables leave out malformed CSV - Severity: Major
* **Reviewer Lens:** `egm-structural` (egm-structural-2-1); also `egm-design`
* **Affected Scope:** `Lines 216-223 vs 407-428 (row at 414)`
* **Discrepancy Description**: Stage 2 makes csv.Error fatal (`<path>: cannot read: <csv error text>`, exit 2) for both file types. The `cannot read` row of the normative table lists only missing, unreadable or non-UTF-8 files. The exit-2 row of the Exit codes table never mentions malformed CSV or a field that is too large.
* **Rationale & Recommendation**: Add "malformed CSV (csv.Error)" to the When cell, or give it its own row. Add it to the exit-2 row too.

### Success criteria are hidden in the Decisions Log - Severity: Major
* **Reviewer Lens:** `egm-structural` (egm-structural-2-2)
* **Affected Scope:** `Goals 42-64, Decisions Log line 472`
* **Discrepancy Description**: The answer to R1.12 (who the primary user is and how success is measured) appears only as a [D] row three levels deep. Goals and Overview never state success criteria.
* **Rationale & Recommendation**: Add a Success criteria bullet (or G7) to Goals that names the user and the success tests. Reduce the Decisions Log row to a pointer. See also egm-style-2-19 on the criterion that cannot be measured.

### Shared CSV-reading rule is placed inside Stage 2 - Severity: Major
* **Reviewer Lens:** `egm-structural` (egm-structural-2-3); also `egm-style` (Nit)
* **Affected Scope:** `Lines 216-224, 245, Risks table`
* **Discrepancy Description**: The rule "CSV reading (both stages) [D]" also governs exports, but it is the first bullet of Stage 2. A stray blank line follows it, so Stage 2 has two separate bullet lists. "Both stages" is not defined at that point. Stage 3 refers back to it only as "Same opening rules", and the Risks table cites "(Stage 2)".
* **Rationale & Recommendation**: Move the CSV-dialect and utf-8-sig rules into their own H3 before Stage 2. Have Stages 2 and 3 refer to it by name, and fix the Risks citation.

### "Warns about edited entries" overclaims - Severity: Major
* **Reviewer Lens:** `egm-style` (egm-style-2-1)
* **Affected Scope:** `Lines 71, 378-380, 561`
* **Discrepancy Description**: The overlap warning fires only when both versions share a normalised client and their spans overlap. An entry whose client was edited, or whose times moved so it no longer overlaps (09:00-10:00 changed to 10:00-11:00), gets no warning. Yet the text says "G6 warns about them" and "makes visible".
* **Rationale & Recommendation**: Limit the claim: "when the two versions share a client and overlap in time, Stage 8 warns". Apply the same limit in Stage 8 and the Risks row.

### G6 warning list is incomplete and miscounted - Severity: Major
* **Reviewer Lens:** `egm-style` (egm-style-2-2); also `egm-structural` (Nit), `egm-design` (Nit)
* **Affected Scope:** `Lines 60-64 vs 203-211, 284-288`
* **Discrepancy Description**: G6 claims to list every warning but leaves out the long-entry warning (over 24 h). "Every PATH given under two NAMEs produces one warning" contradicts Stage 1. Stage 1 warns once for each additional NAME, and its own example produces two warnings.
* **Rationale & Recommendation**: Add "every entry longer than 24 hours". Reword the PATH clause to "every additional NAME given for an already-seen PATH produces one warning".

### Phase 1 summary of fatal cases is inaccurate - Severity: Major
* **Reviewer Lens:** `egm-style` (egm-style-2-3)
* **Affected Scope:** `Lines 174-175`
* **Discrepancy Description**: "Any problem with a whole file or with the command line stops the run" leaves out the fatal invalid rates row (line 230). It also implies that bad export rows are fatal, when they are skipped with a warning.
* **Rationale & Recommendation**: "Any command-line error, any file-level error, or any invalid rates row stops the run with exit 2 before anything is written; invalid export rows are skipped with a warning."

### Long-entry warning repeats before dedupe - Severity: Nit
* **Reviewer Lens:** `egm-design` (egm-design-2-3)
* **Affected Scope:** `Lines 284-288, 385-387`
* **Discrepancy Description**: The warning is raised for each row read. Exports overlap by design, so one typo produces several warnings but only one output row.
* **Rationale & Recommendation**: Raise it after dedupe, or say that it is per source row.

### Unbounded Decimal can crash outside the exit-code table - Severity: Nit
* **Reviewer Lens:** `egm-design` (egm-design-2-4)
* **Affected Scope:** `Lines 233-236, 351-353, 423-428`
* **Discrepancy Description**: Rate digits are unlimited, and billed minutes can reach about 5e9 (End in year 9999). `quantize` can then raise InvalidOperation, which gives a traceback and exit 1. The exit-code table says exit 1 cannot happen, and nothing maps unexpected exceptions to an exit code.
* **Rationale & Recommendation**: Cap the rate's digits or use a local Decimal context with enough precision. Add a catch-all rule: print `tsinvoice: error:`, remove the temp file, and exit 2.

### Inner newlines or quotes break warning lines - Severity: Nit
* **Reviewer Lens:** `egm-design` (egm-design-2-5)
* **Affected Scope:** `Lines 216-223, 355, 374`
* **Discrepancy Description**: A quoted field can contain newlines, and a `'` inside a name makes the quoting ambiguous. This breaks one line per warning and makes stderr harder to test.
* **Rationale & Recommendation**: Escape or whitespace-collapse field text in warnings only, and say so in the spec.

### Atomic-write claim has no fsync - Severity: Nit
* **Reviewer Lens:** `egm-design` (egm-design-2-6)
* **Affected Scope:** `Lines 398-405, 567`
* **Discrepancy Description**: Without fsync before `os.replace`, a power loss can leave `--out` empty or truncated on some filesystems.
* **Rationale & Recommendation**: Add fsync (on the file, and ideally the directory), or narrow the claim to process crashes.

### Duplicate-PATH detection compares strings - Severity: Nit
* **Reviewer Lens:** `egm-design` (egm-design-2-7)
* **Affected Scope:** `Lines 203-211, 561`
* **Discrepancy Description**: `x.csv` and `./x.csv`, or a symlink, are not detected.
* **Rationale & Recommendation**: Compare with `os.path.realpath` or `samefile`, or list "compared as typed" as an accepted limit.

### Session span includes unbilled join gaps - Severity: Nit
* **Reviewer Lens:** `egm-design` (egm-design-2-8)
* **Affected Scope:** `Lines 356-357, 371-373`
* **Discrepancy Description**: A same-client session that fits inside a 0-2 minute join gap is flagged as an overlap, even though no time is billed twice.
* **Rationale & Recommendation**: Check overlap per entry, or document the limit.

### casefold goes beyond "ignore case" - Severity: Nit
* **Reviewer Lens:** `egm-design` (egm-design-2-9)
* **Affected Scope:** `Lines 94-98`
* **Discrepancy Description**: casefold equates ß with ss, which is more than the owner's "ignoring case" (R1.1).
* **Rationale & Recommendation**: Add a line to the Decisions Log row saying this side effect is intended.

### Reference tables are siblings of the numbered stages - Severity: Nit
* **Reviewer Lens:** `egm-structural` (egm-structural-2-4)
* **Affected Scope:** `Lines 407-445`
* **Discrepancy Description**: Fatal error messages, Exit codes, Worked examples and Decisions Log are H3s next to Stages 1-9.
* **Rationale & Recommendation**: Group them under a "Reference" H3, or promote the Decisions Log to its own H2. Then update the "at the end of the Technical Plan" wording on lines 22-23 and 81-82.

### CUJs differ in form - Severity: Nit
* **Reviewer Lens:** `egm-structural` (egm-structural-2-5)
* **Affected Scope:** `Lines 120-169`
* **Discrepancy Description**: Only CUJ 1 gives a full command. CUJs 3 and 6 state no exit code. CUJ 6 does not assert identical stderr (G5). CUJ 2's entries have no dates.
* **Rationale & Recommendation**: Give every CUJ a concrete command and an exit code, and add "stderr identical" to CUJ 6.

### [D] tags and Decisions Log rows do not match - Severity: Nit
* **Reviewer Lens:** `egm-structural` (egm-structural-2-6)
* **Affected Scope:** `Lines 108, 275, 376-377`
* **Discrepancy Description**: Line 108 has a Decisions Log row but no [D] tag. The `T`-or-space rule at line 275 is tagged but not logged. The (i, j) pair order is only loosely covered by an existing row.
* **Rationale & Recommendation**: Make tags and rows match one to one.

### Cross-references are plain text - Severity: Nit
* **Reviewer Lens:** `egm-structural` (egm-structural-2-7)
* **Affected Scope:** `Lines 22-23, 82, 522, 537`
* **Discrepancy Description**: Mentions of the Decisions Log are not links.
* **Rationale & Recommendation**: Use `[Decisions Log](#decisions-log)`.

### Code span breaks across a line - Severity: Nit
* **Reviewer Lens:** `egm-structural` (egm-structural-2-8)
* **Affected Scope:** `Lines 210-211`
* **Discrepancy Description**: The inline example splits across a source line and drops the `--tracker` prefixes.
* **Rationale & Recommendation**: Put it on one line or in a code block, using the full `--tracker` form.

### Horizontal rules are used inconsistently - Severity: Nit
* **Reviewer Lens:** `egm-structural` (egm-structural-2-9)
* **Affected Scope:** `Lines 7, 555, 578, 592, 606`
* **Discrepancy Description**: Rules appear only between some H2 sections.
* **Rationale & Recommendation**: Put a rule between every H2, or use them only at the major part boundaries.

### Future Improvements comes after Additional Resources - Severity: Nit
* **Reviewer Lens:** `egm-structural` (egm-structural-2-10)
* **Affected Scope:** `Lines 594-604`
* **Discrepancy Description**: Resources normally close the spec.
* **Rationale & Recommendation**: Swap the two sections, or move Future Improvements next to Non-Goals.

### Architecture diagram leaves out warning sources - Severity: Nit
* **Reviewer Lens:** `egm-structural` (egm-structural-2-11)
* **Affected Scope:** `Lines 180-192`
* **Discrepancy Description**: The diagram does not show the Stage 1 duplicate-PATH or Stage 6 unrated-session warnings, although Stage 9 orders four warning groups.
* **Rationale & Recommendation**: Show all four warning sources.

### Persuasive wording in the problem statement - Severity: Nit
* **Reviewer Lens:** `egm-style` (egm-style-2-4)
* **Affected Scope:** `Line 34`
* **Discrepancy Description**: "Fixed, exact rules, not guesswork" says the same thing twice and argues against a straw man.
* **Rationale & Recommendation**: "The tool applies these rules:".

### Mislabelled Unicode standard - Severity: Nit
* **Reviewer Lens:** `egm-style` (egm-style-2-5)
* **Affected Scope:** `Lines 94-96`
* **Discrepancy Description**: Canonical caseless matching uses NFD, but the procedure here uses NFC.
* **Rationale & Recommendation**: Drop the label, or write "an NFC variant of canonical caseless matching".

### Awkward "Input order" definition - Severity: Nit
* **Reviewer Lens:** `egm-style` (egm-style-2-6)
* **Affected Scope:** `Line 105`
* **Discrepancy Description**: The parenthetical tuple is hard to read.
* **Rationale & Recommendation**: "Entries ordered by argument position of their export, then by line number."

### Python version narrower than the contract - Severity: Nit
* **Reviewer Lens:** `egm-style` (egm-style-2-7)
* **Affected Scope:** `Line 17`
* **Discrepancy Description**: The spec says "Python 3.11" where BRIEF says "3.11+".
* **Rationale & Recommendation**: Write "3.11+".

### CUJ example rows use informal notation - Severity: Nit
* **Reviewer Lens:** `egm-style` (egm-style-2-8)
* **Affected Scope:** `Lines 123, 130-131`
* **Discrepancy Description**: Rows such as "acme, design , start 09:07, 7 minutes" are neither CSV nor the documented formats, so a test author has to translate them.
* **Rationale & Recommendation**: Give literal CSV rows with their headers.

### CUJ 3 does not give the warning count - Severity: Nit
* **Reviewer Lens:** `egm-style` (egm-style-2-9)
* **Affected Scope:** `Lines 143-145`
* **Discrepancy Description**: "An overlap warning for each pair" gives a test nothing exact to check.
* **Rationale & Recommendation**: State the exact count and pairs. This interacts with egm-design-2-2.

### CUJ 5 contradicts its Given - Severity: Nit
* **Reviewer Lens:** `egm-style` (egm-style-2-10)
* **Affected Scope:** `Line 163`
* **Discrepancy Description**: The Given says `out.csv` exists, so "(or not created)" cannot apply.
* **Rationale & Recommendation**: Drop the parenthetical, or split it into a separate case.

### Negative-rate sentence repeats the regex - Severity: Nit
* **Reviewer Lens:** `egm-style` (egm-style-2-11)
* **Affected Scope:** `Lines 235-236`
* **Discrepancy Description**: The regex already rules out any sign.
* **Rationale & Recommendation**: Delete the sentence or shorten it.

### Header casing differs from BRIEF - Severity: Nit
* **Reviewer Lens:** `egm-style` (egm-style-2-12)
* **Affected Scope:** `Line 250 vs 266`
* **Discrepancy Description**: Line 250 writes `client,description,start,end`, but BRIEF uses `Client,Description,Start,End`.
* **Rationale & Recommendation**: Use BRIEF's casing and add "(compared case-insensitively)".

### "Catches" overstates the long-entry warning - Severity: Nit
* **Reviewer Lens:** `egm-style` (egm-style-2-13)
* **Affected Scope:** `Lines 287-288`
* **Discrepancy Description**: A day typo that produces an entry of 24 hours or less is not flagged.
* **Rationale & Recommendation**: "Flags typos that make an entry longer than 24 hours."

### Reason table puts two reasons in one row - Severity: Nit
* **Reviewer Lens:** `egm-style` (egm-style-2-14)
* **Affected Scope:** `Line 303`
* **Discrepancy Description**: `invalid start` / `invalid end` share one row.
* **Rationale & Recommendation**: Split it into two rows.

### Stage 9 lines too long - Severity: Nit
* **Reviewer Lens:** `egm-style` (egm-style-2-15)
* **Affected Scope:** `Lines 387, 401-403`
* **Discrepancy Description**: These lines are much longer than the surrounding prose.
* **Rationale & Recommendation**: Rewrap them to match the rest of the document.

### Filler and subjective words - Severity: Nit
* **Reviewer Lens:** `egm-style` (egm-style-2-16)
* **Affected Scope:** `Lines 63, 455, 473, 475`
* **Discrepancy Description**: "by design", "Standard parser behaviour", "Simple, and", "not what we think it is".
* **Rationale & Recommendation**: State facts. For example, write "`strptime` accepts single-digit fields" and "does not match the header's layout".

### Alternative B says the same thing twice - Severity: Nit
* **Reviewer Lens:** `egm-style` (egm-style-2-17)
* **Affected Scope:** `Lines 496-498`
* **Discrepancy Description**: "A third format is a non-goal" appears in both Cons and Reason for Rejection.
* **Rationale & Recommendation**: Keep it only in Reason for Rejection.

### "Group" has two scopes - Severity: Nit
* **Reviewer Lens:** `egm-style` (egm-style-2-18)
* **Affected Scope:** `Lines 569, 584-585`
* **Discrepancy Description**: Joins group by (client, description), but the overlap check works per client.
* **Rationale & Recommendation**: Name each scope explicitly in both places.

### Success criterion cannot be measured - Severity: Nit
* **Reviewer Lens:** `egm-style` (egm-style-2-19)
* **Affected Scope:** `Line 472`
* **Discrepancy Description**: The tool cannot observe "the owner sends the CSV without hand edits".
* **Rationale & Recommendation**: Mark it as an outcome check done by the owner, or drop it. Coordinate with egm-structural-2-2.
