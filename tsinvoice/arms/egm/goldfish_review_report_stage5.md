Status: resolved

# Goldfish Annotated Review Report

**Target:** `docs/designs/tsinvoice.md` (full file) — Stage 5 (Initial Zoom Out). Source: `zoom_out_report.md`.

## Prioritized Findings & AI Suggestions

### zoom-out-1-1 [`egm-zoom-out`] - Severity: Medium
*   **Affected Scope:** Detailed Implementation Plan vs Stages 1-9
*   **Discrepancy Description:** Implementation Plan restates normative rules at code level; two copies can drift and neither is authoritative.
*   **Rationale:** Drift risk for the implementer.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Valid. The code fragments help the implementer, so rather than delete them, declare precedence.
*   ***Proposed Edit:*** Add a "Precedence" paragraph at the top of the Detailed Implementation Plan: Stages, tables and Decisions Log are the spec; plan fragments are guidance; Stages win. Remove the redundant `q != p` check.

### zoom-out-1-2 [`egm-zoom-out`] - Severity: Medium
*   **Affected Scope:** links at lines 19-20, 74, 371, 468-470; Decisions Log
*   **Discrepancy Description:** Relative links broken (doc lives in docs/designs/); [D] reasons live only in concepts_brief.md.
*   **Rationale:** The design must stand alone.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Valid; verified the links resolve to the wrong directory.
*   ***Proposed Edit:*** Links changed to `../../`. Decisions Log rewritten as a self-contained table with one reason per [D] item. Open Questions now points at the R-citations and the Decisions Log.

### zoom-out-1-6 [`egm-zoom-out`] - Severity: Low
*   **Affected Scope:** Stage 9 / cli.main
*   **Discrepancy Description:** Warnings printed before the write; a failed write would print warnings plus an error.
*   ***AI Suggestion:*** PROPOSE FIX (worth it: real contract inconsistency)
*   ***Proposed Edit:*** Write first, then print warnings; on any FatalError print only the error. Diagram and Stage 9 updated.

### zoom-out-1-8 [`egm-zoom-out`] - Severity: Low
*   **Discrepancy Description:** NFC normalisation not logged as [D].
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Proposed Edit:*** Added NFC row with reason to the Decisions Log.

### zoom-out-1-3 [`egm-zoom-out`] - Severity: Low
*   **Discrepancy Description:** Overlap check is the largest designer-added scope; G6 open-ended.
*   ***AI Suggestion:*** DECLINE
*   ***Justification:*** Kept on purpose: it is the only signal for the double billing the owner's rules allow (brainstorm 2.3). G6 lists exactly three warning kinds.

### zoom-out-1-4 [`egm-zoom-out`] - Severity: Low
*   **Discrepancy Description:** Duplicate-PATH warning is speculative; Stage 8 covers it.
*   ***AI Suggestion:*** DECLINE
*   ***Justification:*** One-line check that names the cause directly; Stage 8 only shows a symptom per pair.

### zoom-out-1-5 [`egm-zoom-out`] - Severity: Low
*   ***AI Suggestion:*** DECLINE — atomic write is needed for "exit 2 leaves --out untouched" when the write itself fails mid-way; a one-function module is acceptable.

### zoom-out-1-7 [`egm-zoom-out`] - Severity: Low
*   ***AI Suggestion:*** DECLINE — Session/OutputRow split is guidance only (see Precedence); implementer may merge them.

## Resolution summary
Accepted fixes: 4 (2 Medium, 2 Low). Contested: 0. Escalated: 0. Declined: 4 (Low). Remaining High/Medium: 0.
