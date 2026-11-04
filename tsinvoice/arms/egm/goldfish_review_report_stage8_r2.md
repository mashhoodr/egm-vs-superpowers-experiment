Status: resolved

# Goldfish Annotated Review Report — Stage 8 re-audit

Source: `intermediate_zoom_out_report_r2.md`. Reviewer: egm-zoom-out (completed). Findings: 0 Blocker, 1 Major, 6 Nit.

| id | Severity | AI Suggestion | Edit |
| --- | --- | --- | --- |
| zoom-out-4-1 | Medium | PROPOSE FIX | Strict mode dropped: CSV is read non-strict so row-level quote quirks become ordinary bad rows (R1.11). Only a quote left open at end of file is fatal (`cannot read: unterminated quoted field`), recorded as a deliberate exception to R1.11 in the reading section, Exit codes, Decisions Log and Risks; tests updated |
| zoom-out-4-6 | Low | PROPOSE FIX | `empty rates file` message folded into `unrecognised rates header` |
| zoom-out-4-2 | Low | DECLINE | Narrow exemption is intentional (see Stage 8 resolution, zoom-out-3-3) |
| zoom-out-4-3 | Low | DECLINE | Settled earlier (zoom-out-1-5, 3-6) |
| zoom-out-4-4 | Low | DECLINE | Wording/cross-reference polish |
| zoom-out-4-5 | Low | DECLINE | G0 kept as is; the log row points to it on purpose (single home) |
| zoom-out-4-7 | Low | DECLINE | Remaining detail is behaviour-defining (formats, regex grammar) |

Escalation follow-up: zoom-out-4-1 touches owner behaviour (R1.11), so it was escalated to the stakeholder (round 4). Owner answer R4.1: an unterminated quote is one bad row, exit 0. The design was changed to that: bad-row reason `unterminated quoted field`; only other `csv.Error`s are fatal; in the rates file it is a fatal bad rates row.

Accepted fixes: 2. Declined: 5. Remaining High/Medium: 0. Re-audit cap reached; Stage 8 closed.
