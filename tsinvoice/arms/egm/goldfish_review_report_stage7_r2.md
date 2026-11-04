Status: resolved

# Goldfish Annotated Review Report — Stage 7 re-audit (round 2)

Source: `critic_report_r2.md`. Reviewers: egm-design, egm-structural, egm-style (all completed). Findings: 0 Blocker, 8 Major, 31 Nit. Round not clean (8 Majors).

| id | Severity | AI Suggestion | Edit |
| --- | --- | --- | --- |
| egm-design-2-1 | Medium | PROPOSE FIX | Decision reversed: Format B seconds are truncated to the minute; Decisions Log, Alternative E, gap rule (0-2 min), worked example "App handoff with seconds", plan and tests updated. Owner left seconds as "your call" (R2.4), so no escalation |
| egm-design-2-2 | Medium | PROPOSE FIX | Stage 8 skips pairs of single-entry sessions sharing a Stage 4 duplicate key; CUJ 3, G6, plan and tests updated |
| egm-structural-2-1 | Medium | PROPOSE FIX | Fatal-message and exit tables include malformed CSV |
| egm-structural-2-2 | Medium | PROPOSE FIX | New Goal G0: primary user and success criteria |
| egm-structural-2-3 | Medium | PROPOSE FIX | New section "Reading any CSV file (used by Stages 2 and 3)"; Stages 2/3 reference it |
| egm-style-2-1 | Medium | PROPOSE FIX | Non-Goals: Stage 8 warns only when edited versions overlap with the same client |
| egm-style-2-2 | Medium | PROPOSE FIX | G6 lists the long-entry warning and states one warning per additional NAME |
| egm-style-2-3 | Medium | PROPOSE FIX | Phase 1 summary lists all fatal cases and says bad export rows are not fatal |
| egm-design-2-3 | Low | PROPOSE FIX | Long-entry warning stated as per source row, before dedupe |
| egm-style-2-4 | Low | PROPOSE FIX | Removed "not guesswork" |
| egm-style-2-5 | Low | PROPOSE FIX | Removed the incorrect "standard canonical" claim; casefold effect stated |
| egm-design-2-9 | Low | PROPOSE FIX | (same edit) casefold ß/ss effect recorded |
| egm-style-2-7 | Low | PROPOSE FIX | "Python 3.11+" |
| egm-style-2-10 | Low | PROPOSE FIX | CUJ 5 "(or not created)" removed |
| all other Nits (25) | Low | DECLINE | Wording/structure polish or accepted limits (fsync, path aliasing, multi-line text in warnings, unbounded Decimal at absurd sizes, span includes join gaps) with no effect on behaviour the owner specified |

Accepted fixes: 14 (8 Medium, 6 Low). Contested: 0. Escalated: 0. Declined: 25 (Low). Remaining High/Medium: 0.
