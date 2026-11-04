Status: resolved

# Goldfish Annotated Review Report — Stage 7 (Critic Review), round 3

**Target:** `docs/designs/stockmerge.md` (FeatureRange, lines 1-614 at review time)
Source findings: `critic_report_r3.md`. Blocker = High, Major = Medium, Nit = Low.
User decision (made by the Elephant): **auto accept**.

| ID | Sev | Suggestion | Edit / justification |
| --- | --- | --- | --- |
| design-3-1 | Medium | PROPOSE FIX | R2.2: `samefile` only when both exist; `OSError` counts as "not the same" |
| design-3-2 | Medium | PROPOSE FIX (part) / CONTEST (part) | Exit 0 when every row is skipped is the owner's rule (doc: R4.2 tags, linked `stakeholder_log.md` round 1 Q8) — contested. Formats unchecked against real files — added to Risks & Limits |
| design-3-3 | Medium | PROPOSE FIX | R4.1: `errors="surrogateescape"`; a row with an invalid byte is skipped with a warning, not exit 2 (verified in scratchpad) |
| style-3-1 | Medium | PROPOSE FIX | Problem statement points to the accepted same-minute risk |
| style-3-2 | Medium | PROPOSE FIX | G5 names the covered exception types |
| style-3-3 | Medium | PROPOSE FIX | Totals non-goal split into [owner] and [builder] |
| style-3-4 | Medium | PROPOSE FIX | Glossary "Trim" = `str.strip()` |
| style-3-5 | Medium | PROPOSE FIX | R3.2 rewritten without sentence positions |
| style-3-6 | Medium | PROPOSE FIX | R4.12 split into Why/Detect/Warn/Recover/Result/Limit |
| style-3-7 | Medium | PROPOSE FIX | size figure labelled as an unmeasured builder assumption |
| 21 Nits | Low | DECLINE | wording/layout; recorded in `critic_report_r3.md` |

Counts: 10 Medium addressed (9 fixed, 1 part-fixed/part-contested), 0 Low fixed, 21 Low declined.
