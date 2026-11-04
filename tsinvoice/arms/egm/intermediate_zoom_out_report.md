# Goldfish Review Report

**Target:** `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers-p3/arms/egm/docs/designs/tsinvoice.md` (`1-890`)

**Stage:** 8 (Intermediate Zoom Out), Mode: REVIEW

## Reviewer Status

| Reviewer | Status |
| --- | --- |
| `egm-zoom-out` | completed |

## Findings Summary

| ID | Severity | Scope | Summary |
| --- | --- | --- | --- |
| zoom-out-3-1 | Major | l.425-439, l.238-249, l.262, l.309-319, l.686-722, l.763-770 | Error message text now lives in three places (Stages, the new Fatal-error table, the plan's f-strings), and it is unclear which one wins |
| zoom-out-3-2 | Major | G6 l.65-71, l.212-220, l.295-301, l.398-399 | Warnings the designer added keep growing: the duplicate-PATH warning got bigger instead of being dropped, and the long-entry warning is new and no owner asked for it |
| zoom-out-3-3 | Nit | l.391-395, l.151-152, l.753-755, l.843 | The exact-repeat exemption patches Stage 8, ties it to Stage 4's duplicate key, and misses repeats that chain into joined sessions |
| zoom-out-3-4 | Nit | l.369-370, l.671-677, l.747-756 | Session and OutputRow still overlap (Stage 5 1-7). Stage 8 now needs entry-level data, so OutputRow's extra fields have no use |
| zoom-out-3-5 | Nit | l.44-48 vs l.491 | G0 is copied into the Decisions Log, and the copy already disagrees with it |
| zoom-out-3-6 | Nit | l.416-423, l.485, l.499, l.588, l.763-770 | The atomic write got bigger (chmod, symlinks), and the reason given for it is wrong |
| zoom-out-3-7 | Nit | l.578-597, l.603-606 | Risks & Mitigations mostly repeats the Decisions Log. One cross-reference points to the wrong section, and one README promise is missing from the README item |
| zoom-out-3-8 | Nit | l.230-231, l.285-289, l.358 | Small implementation details and formatting slips inside normative Stages |
| zoom-out-3-9 | Nit | l.536-566 | Alternatives E, G and H repeat the Decisions Log |

**Totals:** Blocker 0, Major 2, Nit 7.

## Status of Stage 5 Findings

- **1-1 (plan repeats the rules at code level):** partly resolved. A precedence paragraph was added (l.636-639), but every code fragment Stage 5 named is still there. Carried forward as zoom-out-3-1.
- **1-2 (broken links, rationale kept elsewhere):** resolved.
- **1-3 (overlap check is designer scope, G6 open-ended):** mostly resolved. G6 now lists each warning kind and the overlap check is logged at l.489. The per-pair warning remains, and G6 grew by one kind.
- **1-4 (warning for the same PATH under two NAMEs):** regressed. See zoom-out-3-2.
- **1-5 (atomic write is more machinery than needed):** regressed. See zoom-out-3-6.
- **1-6 (warnings printed before a failed write):** resolved (l.405-408, l.786-790).
- **1-7 (Session and OutputRow overlap):** unresolved. See zoom-out-3-4.
- **1-8 (NFC normalisation):** resolved (l.102, l.490).

## Prioritized Findings (Blockers -> Major -> Nits)

### zoom-out-3-1: Rule text is kept in three places - Severity: Major
* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:**
  * Fatal error messages (l.425-439)
  * Stage 2 (l.238-249)
  * Stage 3 (l.262, l.309-319)
  * Implementation Plan readers.py and writer.py (l.686-722, l.763-770)
  * Regexes at l.245/l.704 and l.285/l.713
* **Discrepancy Description**:
  * The new Fatal-error table works as a test contract. But each error string now appears three times: in the Stage prose, in the table, and in the plan's f-strings (l.688, l.701-706, l.709-711, l.770).
  * The regexes appear twice.
  * The precedence note (l.636-639) says the Stages beat the plan. It does not say whether the Stages or the table win, and the table calls itself "normative".
  * This is the Stage 5 drift risk (1-1), now with one more copy.
* **Rationale & Recommendation**:
  * Make the Fatal-error table and the bad-row table (l.311-319) the only place that holds message text. Stages 2 and 3 should point to them.
  * Cut the Implementation Plan down to module responsibilities, public signatures and records.
  * Delete these from the plan:
    * the regex literals
    * the `reader.line_num` arithmetic (l.690-691)
    * the private helpers `_records`, `_header_key` and `_fit` (l.686-699)
    * the `has_pred`/`succ` join bookkeeping (l.735-739)
    * the `-(-worked // 6) * 6` formula (l.673)
    * the `NamedTemporaryFile` argument list (l.764-767)

### zoom-out-3-2: Warnings the designer added keep growing - Severity: Major
* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:**
  * G6 (l.65-71)
  * Stage 1 (l.212-220)
  * Stage 3 long-entry warning (l.295-301)
  * Stage 8 note (l.398-399)
  * Stage 9 order (l.403-405)
  * Worked example (l.461)
  * Decisions (l.481, l.498)
  * Risks (l.582, l.587)
  * Tests (l.812, l.855)
* **Discrepancy Description**:
  * G6 has five warning kinds. The owner asked for two: bad rows (R1.11) and unrated sessions (R1.4/R3.9). The owner's "your call" (R3.7) covers only the overlap check.
  * **Duplicate-PATH warning (l.212-220):** Stage 5 called it speculative. It now has its own algorithm (a (PATH, NAME) seen-set and a `<name1>`/`<nameK>` message) and a four-argument example.
    * It is also redundant. When the same PATH comes under two NAMEs, the duplicate keys differ, so the exact-repeat exemption (l.391-393) does not apply.
    * Stage 8 therefore already warns on every overlapping pair, and the user gets two warnings for one mistake. The design nearly admits this at l.398-399.
  * **Long-entry warning (l.295-301):** no owner answer asks for it. It adds:
    * an arbitrary 1440-minute threshold
    * a new stderr group
    * a per-source-row, before-dedupe placement rule, which means every deduplicated copy warns again
    * a worked example, a Decisions row, a Risks row and tests

    The case it targets, a year typo, already shows in the `minutes` column, which the owner reviews before invoicing.
* **Rationale & Recommendation**:
  * Drop both warnings. Stage 8 already catches a reused PATH, and the owner's review of the minutes column catches typos. G6 goes back to three kinds: bad row, unrated, overlap.
  * If the long-entry warning stays:
    * mark it in the Decisions Log as an addition the owner did not request
    * drop the "before dedupe" placement and warn once per kept entry
  * Keep the overflow-to-bad-row rule (l.292-294). It is the simplest crash guard and fits R1.11.

### zoom-out-3-3: The exact-repeat exemption is a partial patch - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** Stage 8 (l.391-395); CUJ 3 (l.151-152); plan (l.753-755); test (l.843)
* **Discrepancy Description**:
  * R1.1 justifies the exemption, so it should stay. But it fixes noise that Stage 8 itself creates, and it ties Stage 8 to Stage 4's duplicate key.
  * It only exempts sessions with a single entry. Example of a miss:
    * A1/A2 are identical and B1/B2 are identical.
    * A1 joins B1 into one session, and A2 joins B2 into another.
    * The two identical joined sessions still get a warning. That contradicts the reason given at l.394-395.
* **Rationale & Recommendation**:
  * Pick one:
    * Define the exemption at session level: both sessions consist of entries whose duplicate keys are equal pair by pair.
    * Or state the gap in one line.
  * Also consider one warning per overlapping group instead of per pair, as Stage 5 suggested.

### zoom-out-3-4: Session and OutputRow still overlap - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** l.369-370, l.671-677, l.747-756
* **Discrepancy Description**:
  * The exemption needs each row's tracker and duplicate key, which OutputRow does not carry. So Stage 8 has to work on Session anyway.
  * That leaves no use for OutputRow's extra fields (`client_key`, `start`, `end`, `order`) or for "span".
* **Rationale & Recommendation**:
  * Sort, number and overlap-check Sessions.
  * Turn them into plain 6-field CSV rows only at write time.
  * Remove "span".

### zoom-out-3-5: G0 copy already disagrees with G0 - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** G0 (l.44-48) vs Decisions Log (l.491)
* **Discrepancy Description**:
  * G0 says "every case in G6" appears on stderr.
  * l.491 lists only bad rows, unrated sessions and overlaps. It leaves out the long-entry and duplicate-PATH warnings.
  * G0 also mixes a statement for the user with test criteria that the Verification Plan already covers (l.881-882).
* **Rationale & Recommendation**: Keep G0. Change l.491 to a one-line pointer: "see G0".

### zoom-out-3-6: The atomic write got bigger and its reason is wrong - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** Stage 9 (l.416-423); Decisions (l.485, l.499); Risks (l.588); writer.py (l.763-770)
* **Discrepancy Description**:
  * **Wrong reason:** l.485 says the temp file guarantees "exit 2 writes nothing". That guarantee actually comes from Phase 1 finishing before any write. The temp file only protects against a write that fails partway through.
  * **New machinery:**
    * a `.tsinvoice-*` prefix
    * a forced `chmod 0o644`, which ignores the user's umask and loosens an existing 0600 `--out` file
    * symlink replacement
    * cleanup
    * an accepted leftover file after a hard kill
  * writer.py is still a module with one function in it.
* **Rationale & Recommendation**:
  * Correct the reason at l.485.
  * Then either:
    * keep temp-file-plus-replace and drop the chmod and symlink details,
    * or write directly after Phase 2 and document a failed write as the one exception.
  * Fold `write_rows` into cli.py.

### zoom-out-3-7: Risks & Mitigations repeats the Decisions Log - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** l.578-597; NFR Performance (l.603-606)
* **Discrepancy Description**:
  * Most rows restate Decisions rows (l.479, l.481, l.485, l.497, l.498).
  * The Scale row repeats the Performance NFR.
  * The "Malformed CSV" row cites "Stage 2", but the rule is in "Reading any CSV file" (l.223-233).
  * l.585 promises rule-ordering advice in the README, but the README item (l.866-872) does not list it.
  * What works: the Security paragraph and the Encoding and Scale rows correctly mark accepted limits.
* **Rationale & Recommendation**:
  * Shorten each row to the risk plus a pointer.
  * Fix the cross-reference.
  * Add the rule-ordering advice to the README item, or drop it.

### zoom-out-3-8: Implementation details and slips inside normative Stages - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** l.230-231; l.285-289; l.358 (and l.673)
* **Discrepancy Description**:
  * l.230-231 has a "csv module field size limit" aside.
  * l.289 is missing a line break between the seconds rule and `duration_minutes`.
  * The rounding formula appears in two forms (l.358 and l.673).
* **Rationale & Recommendation**:
  * Drop the size-limit aside.
  * Keep one form of the rounding formula, in Stage 6.
  * Fix the line break.

### zoom-out-3-9: Alternatives E, G and H repeat the Decisions Log - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** Alternatives E, G, H (l.536-566)
* **Discrepancy Description**: Each of these either says "See Decisions Log" or restates it. They add length without new reasoning.
* **Rationale & Recommendation**: Optional: merge each into one line in the Decisions Log.

## Additions Reviewed With No Change Needed

- **Truncating phone seconds (l.284-289, l.471, l.536-544, l.454):** within R2.4's "your call". It is the simplest rule that gives both formats one-minute precision, and the cost is stated.
- **Strict CSV reading (l.225-233, l.497, l.586):** a single flag with a sound reason. Making it fatal matches the existing whole-file exit-2 rule.
- **Duration overflow becomes a bad row (l.292-294):** the simplest crash guard.
- **Context, root problem and Alternatives A-D and I:** still correct.
- **Reuse:** there is no existing code, and the stdlib choices are appropriate.
