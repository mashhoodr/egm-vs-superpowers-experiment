# Goldfish Review Report

**Target:** `docs/designs/tsinvoice.md` (`Lines 1-717`)

## Reviewer Status

| Reviewer | Status |
| --- | --- |
| `egm-zoom-out` | completed (two independent instances, A and B, both returned reports) |

## Findings Summary

| id | severity | scope | summary |
| --- | --- | --- | --- |
| zoom-out-1-1 | Major | Lines 480-625 vs Stages 1-9 (177-344) | Implementation Plan restates the normative rules at code level, so two copies can drift and neither is marked authoritative |
| zoom-out-1-2 | Major | Lines 19-20, 71-75, 369-376, 466-470 | Relative links to BRIEF/stakeholder_log/concepts_brief are broken, and the reasons for the [D] decisions and "Open Questions: None" live only in concepts_brief.md |
| zoom-out-1-3 | Nit | G6 (56-57), Stage 8 (315-325), 589-591 | Overlap check is the largest designer-added scope, and G6 "Nothing silent" is worded as an open-ended mandate |
| zoom-out-1-4 | Nit | Stage 1 (183-187), 329, 617-618, test 682 | Warning for the same PATH under two NAMEs is a speculative guard that Stage 8 already covers |
| zoom-out-1-5 | Nit | Lines 157-158, 340-344, 595-604 | writer.py is a one-function module, and temp-file + os.replace only guards against a partial write |
| zoom-out-1-6 | Nit | Lines 329-333 vs 617-624 | If the output write fails, warnings have already gone to stderr, which contradicts the stated FatalError contract |
| zoom-out-1-7 | Nit | Lines 514-520, 584-592, 302-303 | Session and OutputRow duplicate one concept, and OutputRow carries sort-only fields |
| zoom-out-1-8 | Nit | Lines 85-87, 504-505 | Unicode NFC normalisation goes beyond the owner's trim/collapse/case rule and is not logged as [D] |

Totals: Blocker 0, Major 2, Nit 6.

## Prioritized Findings (Blockers -> Major -> Nits)

No Blockers. Both instances found that the design passes on context, root-problem focus and simplicity. It has a two-phase pipeline (validate all inputs, then a pure merge), one format-independent Entry record, flat stdlib-only modules, and Alternatives B-D correctly reject over-engineering. Neither instance found a contradiction with BRIEF.md or R1-R3.

### zoom-out-1-1: Implementation Plan duplicates the normative rules at code level - Severity: Major
* **Reviewer Lens:** `egm-zoom-out` (A: Major, B: Nit; kept at the higher severity)
* **Affected Scope:** `Lines 480-625`, especially 516, 529-535, 553-559, 570-578, 599-601, compared with Stages 1-9 (`Lines 177-344`)
* **Discrepancy Description**: Each rule is written twice: once in prose in the Stages and once as code fragments in the plan. Examples:
  * rounding appears as `ceil(m / 6) * 6` (l.291) and again as `-(-worked // 6) * 6` (l.516)
  * the `reader.line_num` arithmetic (l.532-533)
  * the `start_iso` and duration regex literals (l.554-556)
  * the private helpers `_records`, `_header_key` and `_fit`
  * the join bookkeeping `has_pred: set[int]` / `succ: dict[int,int]`, including a redundant `q != p` check (l.572-573)
  * the full `NamedTemporaryFile(...)` argument list (l.599-601)

  The document does not say which copy wins if the two disagree.
* **Rationale & Recommendation**: Under the zoom-out standard, loop variables and helpers are "weeds". Limit the plan to module responsibilities, public signatures and the data records (Entry, Rule, Session, output row). Refer back to Stage numbers for behaviour. If any code-level detail stays, state that the Stages and the test list are authoritative.

### zoom-out-1-2: Broken links, and decision rationale outside the design - Severity: Major
* **Reviewer Lens:** `egm-zoom-out` (A: Nit, borderline Major; B: Major)
* **Affected Scope:** `Lines 19-20, 71-75, 369-376, 466-470`
* **Discrepancy Description**: The design is at `docs/designs/` but links `./BRIEF.md`, `./stakeholder_log.md` and `./concepts_brief.md`. Those files are at the arm root, so all three links are broken (verified). The Decisions Log (l.371) and "Open Questions: None" (l.74) send the reader to concepts_brief.md section 5/5.2 for the reasons. Some [D] items have no reason anywhere in this file, for example:
  * skipping a blank client while keeping a blank description
  * the duplicate-PATH warning
  * producing a header-only output file
  * rejecting a date-only `start_iso`
* **Rationale & Recommendation**: Change the links to `../../BRIEF.md` etc. Make the Decisions Log self-contained, with one line of reasoning per [D] item. Point Open Questions at the R-citations and the [D] list in this document rather than at a brainstorm artifact that may not be kept.

### zoom-out-1-3: Overlap check is designer-added scope; tighten G6 - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A, B)
* **Affected Scope:** `G6 (Lines 56-57)`, `Stage 8 (Lines 315-325)`, `Lines 589-591`, test at l.671
* **Discrepancy Description**: R3.7 was "your call". The design answers it with a new goal, a new stage, a pairwise scan within each client and a new warning category. The reason is real: exact-match dedupe can double-bill edited entries or work timed in both apps. However, G6 reads as a broad principle that invites more warning features. The check also warns once per overlapping pair, which can be noisy when a whole day was timed in both apps.
* **Rationale & Recommendation**: Keep Stage 8. Record it in the Decisions Log as a deliberate scope addition. Reword G6 to list exactly the warning kinds. Consider reporting one warning per overlapping group rather than per pair.

### zoom-out-1-4: Same-PATH-under-two-NAMEs warning is speculative - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A, B)
* **Affected Scope:** `Stage 1 (Lines 183-187)`, `Line 329`, `Lines 617-618`, test at l.682
* **Discrepancy Description**: No one has reported this mistake and the owner did not ask for the guard (R2.7 "your call"). It still adds its own warning category, an ordering slot and a test. When it happens, the Stage 8 overlap warning already fires, because identical sessions for the same client overlap exactly.
* **Rationale & Recommendation**: Drop it (YAGNI) and rely on Stage 8. If it stays, add a one-line reason why it is needed beyond Stage 8.

### zoom-out-1-5: writer.py and atomic write are more machinery than needed - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A, B)
* **Affected Scope:** `Lines 157-158, 340-344, 595-604`
* **Discrepancy Description**: Phase 1 already ensures every exit-2 error happens before any output (BRIEF, R1.11, CUJ 5, and `--out` equal to an input). The temp file + `os.replace` only protects against a write that fails partway through. It also brings its own costs: a temp-file naming scheme, cleanup, and possible permission or ownership changes when it replaces an existing file. On top of that, it lives in a separate module that holds a single function.
* **Rationale & Recommendation**: The approach is acceptable because it is cheap and stdlib-only. State plainly that it only guards against a partial write. Fold `write_rows` into `cli.py` unless a separate module is justified. A direct write after Phase 2 would also be acceptable.

### zoom-out-1-6: stderr contract breaks when the output write fails - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A, B)
* **Affected Scope:** `Lines 329-333` vs `Lines 617-624`
* **Discrepancy Description**: `main()` prints the collected warnings and then calls `write_rows`. Lines 622-624 say a FatalError returns 2 "without printing warnings collected so far". If the write fails (for example, the output directory is missing or not writable, l.344), the warnings have already been printed, and the error line follows them.
* **Rationale & Recommendation**: Write the output first and print the warnings only after the write succeeds. Otherwise, document write failures as the one exception.

### zoom-out-1-7: Session and OutputRow overlap - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A, B)
* **Affected Scope:** `Lines 514-520, 584-592`, Stage 6 "span" (`Lines 302-303`)
* **Discrepancy Description**: OutputRow repeats `client_key`, `start`, `end` and `order` only so it can be sorted and checked for overlaps, all of which Session already holds. That makes two records for one concept and adds an extra conversion step.
* **Rationale & Recommendation**: Sort and run the overlap check on Session, and turn it into a plain 6-field CSV row only at write time. This also makes the separate "span" concept unnecessary.

### zoom-out-1-8: NFC normalisation not specified by the owner - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A)
* **Affected Scope:** `Lines 85-87, 504-505`
* **Discrepancy Description**: The owner defined normalisation as trim, collapse whitespace and ignore case (R1.1, R1.10). Adding Unicode NFC is harmless and arguably correct, but nobody asked for it and it is not recorded as a [D] decision.
* **Rationale & Recommendation**: Mark it [D] with a one-line reason, or drop it.
