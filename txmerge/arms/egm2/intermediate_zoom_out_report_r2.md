# Goldfish Review Report

**Stage:** 8, Intermediate Zoom Out Review (re-audit)
**Target:** `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers/arms/egm2/docs/designs/txmerge.md` (`1-696`)
**Prior report:** `zoom_out_report_r2.md` (Stage 5)
**Standard:** `resources/document_standards/zoom-out-standard.md`

## Reviewer Status

| Reviewer | Status |
| --- | --- |
| `egm-zoom-out` (instance A) | completed |
| `egm-zoom-out` (instance B) | completed |

**Verdict (both instances):** Pass with minor changes.

**Severity breakdown:** 0 Blocker, 0 Major, 6 Nit.

The changes made after Stage 5 add no new feature, abstraction, configuration or premature optimisation. These additions are each required by the contract, required by a stakeholder ruling, or needed to prevent data loss: D20 (same-file check), D24 (`--account` parsing), the D14 warning check order, the D15 unquoted-thousands ruling, R8 and Alternative J.

## Stage 5 Findings: Status

| Id | Topic | Status |
| --- | --- | --- |
| zoom-out-2-1 | D23 atomic write | Resolved within the agreed minimum. D23 (line 136) and `write_ledger` (554-561) are mkstemp, write, copymode, os.replace, with cleanup in `finally`. The mode-0600 test is gone. Alternative J (425-435) states the trade-off. Not re-raised. |
| zoom-out-2-2 | Date leniency missing from Decisions | Resolved in D14 (line 127). |
| zoom-out-2-3 | Library details in Technical Plan | Partly resolved. See zoom-out-4-1. |
| zoom-out-2-4 | `T10000` test | Resolved (608-609). |
| zoom-out-2-5 | Summary shapes reader signature | Not resolved. See zoom-out-4-2. |
| zoom-out-2-6 | Amount index in pairing | Unchanged. Stage 5 marked it optional. See zoom-out-4-6. |

## Prioritized Findings (Blockers -> Major -> Nits)

No Blockers. No Majors.

### zoom-out-4-1: Library calls and parser wiring still in the Technical Plan - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A, B)
* **Affected Scope:** Lines 197, 239, 248-251, 340-342
* **Discrepancy Description**: The data-flow diagram names CLI helpers (`build_parser / parse_account`, 197). The Technical Plan still names `csv.reader.line_num` (239), `datetime.strptime` and `csv.Error` for a NUL byte (248-251). Lines 248-250 now repeat D14 in the form of an implementation hint. Lines 340-342 are new since Stage 5 and describe how `cli.main` derives each count, which is wiring inside one function.
* **Rationale & Recommendation**: In the Technical Plan, state only the intent: the physical line where a row ends, dates parsed per D14, a reader-level CSV error is a file-level "cannot read" error. Rename the diagram node to "parse CLI args (D24)". Move the call names and the count derivation into the Detailed Implementation Plan, or leave them to the code.

### zoom-out-4-2: Summary counts still shape the reader interface and CUJ 1 (carried over from zoom-out-2-5) - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A, B)
* **Affected Scope:** Lines 150-151, 337-343, 506-511 (also D16, line 129; `model.warn`, 492-495)
* **Discrepancy Description**: Success output is the designer's choice (round 2, Q9). Even so, the five-count summary makes `read_export` return `tuple[list[Row], int]` and is an acceptance criterion in CUJ 1. The summary keeps creating rules: D16 now has to say how blank lines affect `R` and `S`, and 340-342 add the plumbing. `model.warn` already sees every skipped row.
* **Rationale & Recommendation**: Count skips in one place (in `model.warn` or a counter beside it) and have `read_export` return `list[Row]`. Alternatively, cut the summary to counts that come from list lengths. In either case, take the summary out of CUJ 1's "Then". If the author keeps the current shape on purpose, a one-line Decision saying so closes this finding.

### zoom-out-4-3: D20 same-file check is written at code level, with an extra OSError sub-rule - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A, B)
* **Affected Scope:** Line 133 (D20), 222-226, 658-659
* **Discrepancy Description**: The check is justified, because without it `os.replace` could overwrite an input export. However, D20 also spells out code-level sub-cases. One is "If `--out` does not exist it cannot be an input". Another is a dedicated rule and message for `os.path.samefile` raising `OSError`, which can only happen if a file changes during the run, since every input has already been read. Lines 222-226 repeat the D20/D23 guarantees.
* **Rationale & Recommendation**: Shorten D20 to the rule: after all inputs are read and before writing, if `--out` is the same file as any input or the rules file, exit 2 with the "--out is also an input" message. Any `OSError` during the check falls under the general D13 file-level error. Reduce 222-226 to a pointer to D20 and D23.

### zoom-out-4-4: D24 trims whitespace around NAME and PATH without a stated need - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A, B)
* **Affected Scope:** Lines 137 (D24), 325, 665-666
* **Discrepancy Description**: Splitting on the first `=` is the minimum the NAME=PATH contract needs. Trimming outer whitespace is not requested by BRIEF or any stakeholder ruling. It silently rewrites a path that legitimately starts or ends with a space, adds a qualifier to the Messages section (325), and adds a test case (` cur = x.csv `).
* **Rationale & Recommendation**: Either drop trimming (split on the first `=`, reject an empty NAME or PATH) and delete the qualifier at 325 and the trimming test, or keep it and add a one-line reason.

### zoom-out-4-5: Precedence clause in Messages works around duplicated message text - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A, B)
* **Affected Scope:** Lines 311-315 (related quotes: CUJ 5 at 179-181, D20, D24)
* **Discrepancy Description**: The rule that "this section's wording is the one to implement" exists only because message text is quoted in more than one place. It resolves conflicts instead of removing the duplication.
* **Rationale & Recommendation**: Have other sections refer to messages by row name or `REASON` instead of quoting them, then delete the precedence sentence. Optional.

### zoom-out-4-6: Amount-to-inflows index sits next to "no performance work" (carried over from zoom-out-2-6) - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (B; A treated it as accepted and did not re-raise it)
* **Affected Scope:** Lines 276-278, 347-350
* **Discrepancy Description**: Pairing step 1 specifies an index, but the Scale section says no performance work is planned. The index is small, so this is a preference.
* **Rationale & Recommendation**: Describe pairing as a scan of the unpaired inflows for the opposite amount, and leave the index as an implementation choice. Stage 5 accepted either option.

## Categories With No Findings

* **Context sufficiency:** Pass (9-53).
* **Root-problem focus:** Pass. G1-G6 map to BRIEF's wants. D15 and R5 (unquoted thousands) follow the Stage 7 ruling and add no repair logic.
* **YAGNI and scope creep in the post-Stage-5 additions:** None. R8 (458) is an acceptance with nothing behind it to build. The D14 check order keeps warnings deterministic. Non-Goals (76-87) and Future Improvements (460-463) are listed but not built.
* **Architectural dead-ends:** None. The stages are plain functions over immutable `Row` records, and I/O stays at the edges.
* **Reuse:** Not applicable (new repository). Only the standard library is used.
