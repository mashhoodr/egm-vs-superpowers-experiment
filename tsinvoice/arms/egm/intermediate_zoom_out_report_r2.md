# Goldfish Review Report

**Target:** `docs/designs/tsinvoice.md` (`Lines 1-813`)
**Stage:** 8 (Intermediate Zoom Out), re-audit r2
**Verdict:** pass with fixes. 0 Blocker, 1 Major, 6 Nit.

## Reviewer Status

| Reviewer | Status |
| --- | --- |
| `egm-zoom-out` | completed |

| ID | Severity | Scope | Summary |
| --- | --- | --- | --- |
| zoom-out-4-1 | Major | Lines 216-226, 432, 482, 571 | Strict CSV reading makes any row-level `csv.Error` fatal, which overrides R1.11 (bad rows are skipped) without being logged as a deviation |
| zoom-out-4-2 | Nit | Lines 377-381, 65-69, 148-150 | The exact-repeat overlap exemption covers only single-entry sessions, so a legitimately repeated chain still gets a warning |
| zoom-out-4-3 | Nit | Lines 402-409, 470, 484, 573, 693-698 | The atomic temp-file write has grown extra rules, and its stated reason ("exit 2 writes nothing") is inaccurate |
| zoom-out-4-4 | Nit | Lines 521-559, 567-571, 456, 464, 482 | The same rationale is repeated across Decisions Log, Alternatives and Risks; Alternative H is not a real alternative; one Risks pointer is wrong |
| zoom-out-4-5 | Nit | Lines 44-48, 476 | Goal G0 mixes the goal with the test plan, and its Decisions Log row only points back to G0 |
| zoom-out-4-6 | Nit | Lines 419-421, 233 | An empty rates file gets its own fatal message where `unrecognised rates header` would do |
| zoom-out-4-7 | Nit | Lines 101-102, 224, 240, 264-266, 285-287, 650-651, 688, 722-725, 734-735 | Some sections still go down to code-level detail; one rule appears only in the plan |

Stage 5 findings now resolved: 1-1, 1-2, 1-4, 1-6, 1-7 and 1-8. Finding 1-5 (atomic write) is still open and is tracked as zoom-out-4-3.
The reviewer found that truncating phone seconds (Stage 3, lines 277-282) and the slimmed Implementation Plan need no change, apart from the items in zoom-out-4-7.

## Prioritized Findings (Blockers -> Major -> Nits)

### zoom-out-4-1: Strict CSV reading overrides the owner's bad-row rule - Severity: Major
* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** "Reading any CSV file" (Lines 216-226); Exit codes (Line 432); Decisions Log (Line 482); Risks (Line 571)
* **Discrepancy Description**: R1.11 says to skip any row that can't be parsed and exit 0. Only an unrecognised header is fatal. `strict=True` makes every `csv.Error` fatal, including one harmless quoting quirk in a single row (for example `"Design" review,...`), which non-strict mode would read without trouble. The doc logs this as a designer [D] call, not as a departure from an owner answer. The only case that actually loses data is an unterminated quote that swallows the rest of the file.
* **Rationale & Recommendation**: Simplest fix: keep strict mode, but state in the Decisions Log and Exit codes that this is a deliberate exception to R1.11, because the reader cannot recover after a structural quote error. Alternative: treat a mid-file `csv.Error` as a bad row and keep only "unexpected end of data" fatal.

### zoom-out-4-2: Exact-repeat exemption misses repeated chains - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** Stage 8 (Lines 377-381); G6 (Lines 65-69); CUJ 3 (Lines 148-150)
* **Discrepancy Description**: The exemption covers only single-entry sessions that share a Stage 4 duplicate key. Take one export that legitimately holds the same two-entry handoff twice (A, A, B, B). Stage 5 builds two joined sessions that overlap exactly, and they still get a warning, against the reason the doc gives for the exemption.
* **Rationale & Recommendation**: State the exemption at session level: skip a pair when both sessions have the same tracker and the same sequence of entry duplicate keys. Or add one line accepting that repeated chains still get a warning.

### zoom-out-4-3: Atomic write keeps growing and its stated reason is inaccurate - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** Stage 9 (Lines 402-409); Decisions Log (Lines 470, 484); Risks (Line 573); writer.py (Lines 693-698)
* **Discrepancy Description**: Stage 5 finding 1-5 is still open. The temp-file approach has since gained a fixed `0o644` mode, a rule that a symlinked `--out` is replaced, cleanup on failure, and an accepted-leftover risk. Line 470 says the temp file guarantees "exit 2 writes nothing", but Phase 1 ordering already guarantees that (Lines 178-181, CUJ 5). The temp file only guards against a write that fails partway.
* **Rationale & Recommendation**: Write directly to `--out` after Phase 2 and drop the extra rules. If the temp file stays, change Line 470 to "only guards against a partial write" and drop the `0o644` and symlink rules.

### zoom-out-4-4: Rationale repeated across Decisions Log, Alternatives and Risks - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** Alternatives E-I (Lines 521-559); Risks (Lines 567-571); Decisions Log (Lines 456, 464, 482)
* **Discrepancy Description**: Truncating seconds, fatal rates rows, strict CSV and double billing are each explained two or three times. Alternative H (floats for money) is not a real alternative. The Risks row "Malformed CSV ... (Stage 2)" points to the wrong section: strict reading is described in "Reading any CSV file".
* **Rationale & Recommendation**: Keep each reason in the Decisions Log only. Shorten Alternatives E-I to one-line pointers or delete them. Fix the Risks pointer.

### zoom-out-4-5: Goal G0 mixes the goal with the test plan - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** G0 (Lines 44-48); Decisions Log (Line 476)
* **Discrepancy Description**: "Every CUJ and worked example passes as an automated test" repeats the Verification Plan (Lines 804-805). The Decisions Log row "Primary user and success | See Goal G0" points back to G0 and gives no reason.
* **Rationale & Recommendation**: Cut G0 to the user and the outcome: one freelancer sends the CSV without hand edits, and a rerun gives an identical file. Leave test coverage to the Verification Plan. Give row 476 a real reason or drop it.

### zoom-out-4-6: Two fatal messages for the same condition - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** Fatal error messages table (Lines 419-421); Stage 2 (Line 233)
* **Discrepancy Description**: An export with no non-blank record gets `unrecognised header`, but an empty rates file gets its own `empty rates file` message. That adds one message and one test for no benefit.
* **Rationale & Recommendation**: Use `<path>: unrecognised rates header` for an empty rates file too, and delete the `empty rates file` row.

### zoom-out-4-7: Some sections still go down to code-level detail - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** Lines 101-102 (NFC again), 224 (field-size limit), 240 (-0), 264-266 (N/M definition), 285-287 / 483 / 734-735 (`99999999999` overflow example), 650-651 (`Entry.order` plus `Entry.line`), 688 ("never exponent notation"), 722-725 (conftest helper internals)
* **Discrepancy Description**: These are implementation or test details. "Never exponent notation" is a rule that appears only in the Implementation Plan, which breaks the doc's own rule that the plan never restates a rule.
* **Rationale & Recommendation**: Move these details to tests or leave them to the implementer. Fold "no exponent notation" into the Stage 9 amount format. Drop the separate `line` field from `Entry`.
