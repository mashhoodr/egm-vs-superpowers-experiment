# Goldfish Review Report

**Target:** `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers-p3/arms/egm/docs/designs/tsinvoice.md` (`L1-741`, full file)

**Standard:** `zoom-out-standard` | **Context:** `BRIEF.md` (fixed contract), `stakeholder_log.md` (R1.n/R2.n/R3.n)

## Reviewer Status

| Reviewer | Status |
| --- | --- |
| `egm-zoom-out` | completed (two independent instances, A and B; both returned reports) |

## Findings Summary

| id | severity | scope | one-line summary |
| --- | --- | --- | --- |
| zoom-out-2-1 | Nit | L183-187, L329, L386, L641-642, L706 | Duplicate-PATH warning is redundant with the Stage 8 overlap warning and only compares raw path strings |
| zoom-out-2-2 | Nit | L499-649 (Detailed Implementation Plan items 3-7) | Implementation plan restates the spec at code level, creating a second source of truth guarded only by the precedence clause |
| zoom-out-2-3 | Nit | L538-544, L608-617 | `OutputRow` copies sort/overlap fields from `Session`; three record types on a short data path |
| zoom-out-2-4 | Nit | L315-325, L119-125 | Overlap check will warn on every pair of identical in-export repeats (CUJ 3), but no CUJ says so |
| zoom-out-2-5 | Nit | L157-158, L342-346, L390 | Atomic-write rationale credits temp file + `os.replace` with a guarantee that the two-phase design already provides |
| zoom-out-2-6 | Nit | L332-335 vs L188 | "Single `tsinvoice: error:` line" claim does not hold for argparse usage errors |
| zoom-out-2-7 | Nit | L309-313, L393 | BRIEF's blank-for-single-entry session_id overrides owner's "non-empty" wording (R1.8) without an explicit Decisions Log note |
| zoom-out-2-8 | Nit | L619-628 | `writer.py` is a whole module for one ~10-line function called only by `cli.py` |

Totals: Blocker 0, Major 0, Nit 8. Both instances judged the design as PASS with Nits.

## Prioritized Findings (Blockers -> Major -> Nits)

No Blockers. No Majors.

### zoom-out-2-1: Duplicate-PATH warning duplicates the overlap check - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A and B)
* **Affected Scope:** Stage 1 third bullet `L183-187`; Stage 9 stderr order item (1) `L329`; Decisions Log row "Same PATH under two NAMEs" `L386`; `cli.main` `L641-642`; `test_cli` `L706`.
* **Discrepancy Description**: The same PATH under two NAMEs yields every entry twice in two trackers with identical spans. They cannot join each other (negative gap), so Stage 8 already warns on every such session. The duplicate-PATH warning adds its own message, stderr slot, CLI logic and test, and compares raw strings only (`./d.csv` vs `d.csv` slips past it; Stage 8 does not).
* **Rationale & Recommendation**: Not owner-requested (R2.7 was "your call"). Drop it and rely on Stage 8, reducing stderr to three warning kinds; or keep it and state in the Decisions Log that it is a convenience on top of Stage 8, with the reason the overlap warning alone is insufficient.

### zoom-out-2-2: Implementation plan drops to code-level detail - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A and B)
* **Affected Scope:** Detailed Implementation Plan items 3-7 `L522-649`; Precedence paragraph `L503-506`.
* **Discrepancy Description**: Stages 4-8 are re-specified as near-code: regex literals, `-(-worked // 6) * 6`, `reader.line_num` arithmetic, private helpers `_records`/`_header_key`/`_fit`, `has_pred`/`succ` structures, exact `NamedTemporaryFile` kwargs. A precedence clause was needed because two copies of the rules exist. No drift found today.
* **Rationale & Recommendation**: Anti-weeds concern, mitigated by the precedence clause. Optionally reduce items 3-7 to module responsibility, public signatures (`read_rates`, `read_export`, `merge`, `write_rows`, `main`), shared records and fixed message texts; drop private helpers and expression-level fragments. No change strictly required.

### zoom-out-2-3: Session and OutputRow overlap - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A and B)
* **Affected Scope:** `model.py` `Session` / `OutputRow` `L538-544`; `core.merge` `L608-617`.
* **Discrepancy Description**: `OutputRow` carries `client_key`, `start`, `end`, `order` copied from the session only to sort and run the overlap check. Data flows Entry -> Session -> OutputRow -> CSV with sort keys on two types.
* **Rationale & Recommendation**: Sort, assign IDs and run the overlap check on `Session` (it already exposes `first`, `start`, `end`), and convert to output tuples only at write time; or give `OutputRow` a reference to its `Session`. Removes one record type and duplicated fields.

### zoom-out-2-4: Overlap warnings on legitimate in-export repeats are undocumented - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A)
* **Affected Scope:** Stage 8 `L315-325`; CUJ 3 `L119-125`.
* **Discrepancy Description**: R1.1 says identical entries inside one export are separate work and all stay. Their spans are identical, so every pair triggers an overlap warning; CUJ 3 alone emits three. Neither CUJ 3 nor Stage 8 mentions this expected output.
* **Rationale & Recommendation**: Stage 8 is a valid designer call (R3.7) and output-neutral, so not YAGNI. State the expected warnings in CUJ 3 (or Stage 8) so the behaviour reads as deliberate and gets a test.

### zoom-out-2-5: Atomic-write rationale overstates its role - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A)
* **Affected Scope:** Technical Plan intro `L157-158`; Stage 9 `L342-346`; Decisions Log row "Atomic write via temp file + `os.replace`" `L390`; `writer.py` `L622-628`.
* **Discrepancy Description**: The Decisions Log says temp file + `os.replace` "guarantees 'exit 2 writes nothing'". The two-phase design (validate all inputs before writing) already provides that, and already makes `--out` equal to an input safe. The temp file only adds protection against a failure mid-write (e.g. full disk).
* **Rationale & Recommendation**: Keep the mechanism (cheap; instance B judged it proportionate), but reword the reason to "guards against a partially written `--out`" so readers do not treat it as the primary exit-2 safeguard.

### zoom-out-2-6: Single-line fatal error claim excludes argparse errors - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (B)
* **Affected Scope:** Stage 9 first bullet `L332-335` vs Stage 1 last bullet `L188`.
* **Discrepancy Description**: Stage 9 says a fatal error prints a single `tsinvoice: error: <message>` line. Usage errors go through argparse, which prints a usage line plus `tsinvoice merge: error: ...` (two lines, different prefix).
* **Rationale & Recommendation**: Narrow the Stage 9 sentence to non-usage fatal errors (those raised as `FatalError`).

### zoom-out-2-7: session_id rule reconciliation is implicit - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (B)
* **Affected Scope:** Stage 7 `L309-313`; Decisions Log row on session IDs `L393`.
* **Discrepancy Description**: R1.8 says session_id "must be non-empty and different for each session"; BRIEF says it is blank unless the row was joined. The design correctly follows BRIEF but only cites it in passing.
* **Rationale & Recommendation**: Add one Decisions Log line stating that BRIEF's blank-for-single-entry rule overrides R1.8's "non-empty" wording because BRIEF is the fixed contract, and that uniqueness applies to joined rows.

### zoom-out-2-8: writer.py is a module for one small function - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (B)
* **Affected Scope:** Detailed Implementation Plan item 6 `L619-628`.
* **Discrepancy Description**: One ~10-line function, called only from `cli.py`, gets its own module; Alternative B's "few flat modules, avoid indirection" argument applies here too.
* **Rationale & Recommendation**: Optional: fold `write_rows` into `cli.py`, or keep it and add no further modules.

## Checked and Not Flagged

Both instances confirmed these are proportionate and tied to owner answers or recorded decisions: Stage 8 overlap check (R3.7), NFC before casefold (extends R1.1/R1.10), fatal bad rates rows (Alternative G, R3.5), seconds kept in `start_iso` and `30.0` accepted (R2.4), single format-agnostic entry record (Alternative C), sequential `S<n>` IDs (R3.6), quadratic in-group scans at freelancer scale (NFRs), Future Improvements listed not built. No existing code in the arm folder, so the leverage-existing check reduces to stdlib use, which the design does throughout.
