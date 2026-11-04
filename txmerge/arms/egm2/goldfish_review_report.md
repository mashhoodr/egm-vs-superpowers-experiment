Status: resolved

# Goldfish Annotated Review Report — Stage 7 (Critic), round 1

**Target:** `docs/designs/txmerge.md` (FeatureRange 1-456). Findings source: `critic_report.md` (7 Major, 26 Nit). Gate decision: Auto accept.

## Prioritized Findings & AI Suggestions

### design-1-1 [`egm-design`] - Severity: Medium (Major)
*   **Discrepancy:** write failure can delete an untouched ledger; atomic write not considered.
*   ***AI Suggestion:*** PROPOSE FIX. ***Justification:*** valid; data-loss risk. Churn with zoom-out-2-1 (which removed the atomic write); resolved in favour of the atomic write because D13's "existing ledger unchanged" is a user-facing promise, and zoom-out's side-effect objections (0600 mode, symlink replaced) are fixed by copying the mode and resolving the symlink.
*   ***Proposed Edit:*** D23 rewritten (temp file + `os.replace`, realpath, copymode/umask); Alternative J (direct write) added; R7; impl item 6 and tests updated.

### design-1-2 [`egm-design`] - Severity: Medium (Major)
*   ***AI Suggestion:*** PROPOSE FIX. New D24 (`--account` split/trim/malformed, message); Messages row updated.

### structural-1-1 [`egm-structural`] - Severity: Medium (Major)
*   ***AI Suggestion:*** PROPOSE FIX. Section renamed "Risks & Mitigations", table R1-R8 with impact and mitigation or "accepted by whom".

### style-1-1 [`egm-style`] - Severity: Medium (Major)
*   ***AI Suggestion:*** PROPOSE FIX. G2 retitled "Remove only overlap copies", cites R4; Alternative A reworded.

### style-1-2 [`egm-style`] - Severity: Medium (Major)
*   ***AI Suggestion:*** PROPOSE FIX. Quote now attributed to `BRIEF.md` goal 1.

### style-1-3 [`egm-style`] - Severity: Medium (Major)
*   ***AI Suggestion:*** PROPOSE FIX. CUJ 5 refers to the Messages table; precedence sentence added (Decisions + Messages tables win); Reading section no longer restates D14. D20 keeps its message (it is the D20 rule's own text, also in the Messages table).

### style-1-4 [`egm-style`] - Severity: Medium (Major)
*   ***AI Suggestion:*** PROPOSE FIX. "No performance target; under 50,000 rows", stated once in Scale; NFR refers to it.

### Nits
*   PROPOSE FIX: design-1-3 (D17 notes zero only from Format B), design-1-4 (R4 cites D2 / round 1 answer 2), design-1-6 (`csv.Error` is file-level), design-1-7 (R8 formula injection, accepted), structural-1-4 (Future Improvements promoted), structural-1-8 (same-file check in diagram), structural-1-10 (Exit column), style-1-6 ("single pass" removed), style-1-13 ("accepted by whom" in table).
*   DECLINE: design-1-5, design-1-8, design-1-9, structural-1-3, 1-5, 1-9, 1-11, 1-12, style-1-5, 1-7, 1-9, 1-10, 1-11, 1-12, 1-14, 1-15, 1-16 (wording/format nits; no reader impact).

Counts: 7 Major fixed, 9 Nits fixed, 17 Nits declined, 0 contested, 0 escalated.

---

# Stage 7 (Critic), round 2

**Target:** FeatureRange 1-465. Source: `critic_report_r2.md` (0 Blocker, 2 Major, 29 Nit). All 3 reviewers completed. Round not clean. Gate: Auto accept.

### style-2-1 [`egm-style`] - Severity: Medium (Major)
*   ***AI Suggestion:*** PROPOSE FIX. R1 no longer invents a stakeholder reason; cites round 1 answer 5 and says no reason was given.

### style-2-2 [`egm-style`] - Severity: Medium (Major) — re-opened style-1-3 (fix incomplete)
*   ***AI Suggestion:*** PROPOSE FIX. D20 and D24 now name their messages; texts live only in the Messages section; precedence stated (Decisions = behaviour, Messages = text; no overlap); `PATH`/`OUT`/`VALUE` defined once.

### Nits
*   PROPOSE FIX: design-2-1 (row-check order defines REASON, in D14), design-2-3 (NFR mentions temp file), design-2-5 (samefile `OSError` → "cannot read").
*   DECLINE: remaining 26 Nits (wording, formatting, section names; design-2-8 trimming patterns is a designer choice already recorded in D11).

Counts: 2 Major fixed, 3 Nits fixed, 26 declined, 0 contested.

---

# Stage 7 (Critic), round 3

**Target:** FeatureRange 1-465. Source: `critic_report_r3.md` (0 Blocker, 1 Major, 20 Nit). All 3 reviewers completed. Round not clean. Gate: Auto accept.

### design-3-1 [`egm-design`] - Severity: Medium (Major)
*   **Discrepancy:** unquoted thousands separators split rows; every amount >= 1,000 would be skipped; not stated.
*   ***AI Suggestion:*** PROPOSE FIX (after asking the stakeholder: no repair, skip and warn; quoting assumption is designer's call). D15 states the standard-CSV quoting assumption and the skip; R5 names the cause and mitigation.

### Nits
*   DECLINE: all 20 (wording/formatting; no behaviour impact).

Counts: 1 Major fixed, 0 Nits fixed, 20 declined.

---

# Stage 7 (Critic), round 4

**Target:** FeatureRange 1-465. Source: `critic_report_r4.md` (0 Blocker, 1 Major, 20 Nit). All 3 reviewers completed. Round not clean. Gate: Auto accept.

### style-4-1 [`egm-style`] - Severity: Medium (Major) — re-opened style-1-3 / style-2-2 (earlier fixes incomplete)
*   ***AI Suggestion:*** PROPOSE FIX. Dropped the absolute "only place / cannot disagree" claim; Messages section now "lists every text in full" and wins over any quote elsewhere. Fixed the real mismatch: `cannot read PATH: <OS, decode or CSV error>`; the csv.Error sentence now refers to the message by name.

### Nits
*   DECLINE: all 20.

Counts: 1 Major fixed, 20 Nits declined.

---

# Stage 7 (Critic), round 5

**Target:** FeatureRange 1-465. Source: `critic_report_r5.md` (0 Blocker, 0 Major, 25 Nit). All 3 reviewers completed. **Clean round.**

### Nits
*   PROPOSE FIX: design-5-1 (temp file removed on any exception), design-5-2 (D23 states the no-fsync power-loss limit), design-5-5 (tests check the `--account` message by containment).
*   DECLINE: remaining 22 (cosmetic).

## Stage 7 loop outcome
Rounds 1-4 not clean, round 5 clean. Cap (5 rounds) reached before two consecutive clean rounds. Open Blocker/Major findings at cap: none. Decision: accept and proceed to Stage 8.

---

# Stage 9 (Implementation Readiness), round 1

**Target:** DetailedRange 467-695. Source: `implementation_readiness_report.md` (0 Blocker, 5 Major, 21 Nit; the synthesizer downgraded style-1-2 from Major to Nit. The resolve skill forbids changing severity, so I count and fix it as Major). All 3 reviewers completed. Round not clean. Gate: Auto accept.

*   readiness-1-1 (Major) — PROPOSE FIX: `main` lets argparse's `SystemExit(2)` propagate; tests use `pytest.raises(SystemExit)`.
*   readiness-1-2 (Major) — PROPOSE FIX: `transfers.transfer_id(n)` declared and tested.
*   readiness-1-3 (Major) — PROPOSE FIX: shared `readers.read_csv` (utf-8-sig, newline="", decode/csv errors → "cannot read", empty → "file is empty").
*   codebase-1-1 (Major) — PROPOSE FIX: `write_ledger` given as an exact ordered step list (`tmp=None`, `with open(fd)` closes before copymode/replace, `finally` guards `tmp`).
*   style-1-1 (Major) — PROPOSE FIX: added tests for D14 check order, Format B bad cells, rules-file D13 cases, missing required options, samefile OSError; same-file check spelled out in `main`.
*   style-1-2 (Major per reviewer) — PROPOSE FIX: `test_cli.py` list rewritten as one bullet per test.
*   Nit (NUL-byte csv.Error example) — PROPOSE FIX: verified on Python 3.13 that NUL no longer raises; replaced with the field-size-limit case.
*   Other 20 Nits — DECLINE.

Counts: 6 Major fixed, 1 Nit fixed, 20 declined.

---

# Stage 9 (Implementation Readiness), round 2

**Target:** DetailedRange 467-741. Source: `implementation_readiness_report_r2.md` (0 Blocker, 5 Major, 13 Nit entries). All 3 reviewers completed. Round not clean. Gate: Auto accept.

*   codebase-details-2-1 (Major) — PROPOSE FIX: `parse_date` returns `.date()`.
*   codebase-details-2-2 (Major) — PROPOSE FIX: header constants are lists; comparison list-to-list.
*   codebase-details-2-3 (Major) — PROPOSE FIX: `format_amount` zero rule spelled out; `parse_amount` is the single quantize point.
*   codebase-details-2-4 (Major) — PROPOSE FIX: `add_subparsers(dest="command", required=True)` and the full argument setup given.
*   style-2-1 (Major) — PROPOSE FIX: tests added for D23 file mode, D17 zero row end to end, D16 data-cell trimming; coverage table corrected.
*   Nits — DECLINE (13).

Counts: 5 Major fixed, 13 Nits declined.

---

# Stage 9 (Implementation Readiness), round 3

**Target:** DetailedRange. Source: `implementation_readiness_report_r3.md` (0 Blocker, 1 Major, 20 Nit entries). All 3 reviewers completed. Round not clean. Gate: Auto accept.

*   style-3-1 (Major) — PROPOSE FIX: `cli.main` rewritten as a numbered 10-step list; test guidance kept only in item 15.
*   Nits — DECLINE (20).

---

# Stage 9 (Implementation Readiness), round 4

**Target:** DetailedRange. Source: `implementation_readiness_report_r4.md` (0 Blocker, 2 Major, 15 Nit). All 3 reviewers completed. Round not clean. Gate: Auto accept.

*   readiness-4-1 / codebase-details-4-1 (Major) — PROPOSE FIX: `decimal.InvalidOperation` → `ValueError` → `bad amount`; test added.
*   codebase-details-4-2 (Major) — PROPOSE FIX: rule-row check order and reasons defined; tests added.
*   Nits — DECLINE (15).

---

# Stage 9 (Implementation Readiness), round 5

**Target:** DetailedRange. Source: `implementation_readiness_report_r5.md` (1 Blocker, 0 Major, 18 Nit). All 3 reviewers completed. Round not clean.

*   readiness-5-1 / codebase-details-5-1 (Blocker, High) — PROPOSE FIX: churn from my round-4 test edit (row `,` is all-blank and dropped by `read_csv` per D16). Test now expects `,` skipped silently and uses ` ,Food` / `TESCO, ` for the blank-pattern/category warnings.
*   Nits — DECLINE (18).

## Stage 9 loop outcome
Cap (5 rounds) reached; no two consecutive clean rounds. Open Blocker/Major after round-5 fix: none. Decision: accept at cap and conclude review; document finalized (Status: Approved).
