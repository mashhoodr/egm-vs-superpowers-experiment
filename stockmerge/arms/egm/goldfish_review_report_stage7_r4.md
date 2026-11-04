Status: resolved

# Goldfish Annotated Review Report — Stage 7 (Critic Review), round 4

**Target:** `docs/designs/stockmerge.md` (FeatureRange, lines 1-628 at review time)
Source findings: `critic_report_r4.md`. Blocker = High, Major = Medium, Nit = Low.
User decision (made by the Elephant): **auto accept**.

| ID | Sev | Suggestion | Edit |
| --- | --- | --- | --- |
| egm-design-4-1 | Medium | PROPOSE FIX | R4.1: invalid byte only skips the row when it is in a field the tool reads; the Format B note is exempt |
| egm-design-4-2 | Medium | PROPOSE FIX | R4.11 re-tagged [builder]; R4.10 split into [owner] (notes ignored for moves) and [builder] (never read) |
| egm-style-4-1 (+structural-4-3) | Medium | PROPOSE FIX | Owner/Builder/Decision tags defined once, in the Glossary, with scope; totals non-goal explains the brief's "per SKU per location" |
| egm-style-4-2 | Medium | PROPOSE FIX | R2.2 split into sub-bullets |
| 23 Nits | Low | DECLINE | wording/layout; recorded in `critic_report_r4.md` |

Counts: 4 Medium fixed, 23 Low declined, 0 contested, 0 escalated.
