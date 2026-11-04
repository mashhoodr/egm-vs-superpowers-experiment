Status: resolved

# Goldfish Annotated Review Report — Stage 6 (Comprehension)

**Target:** `docs/designs/tsinvoice.md`. Source: `comprehension_report.md`. Findings: 0 Blocker, 1 Major, 6 Nit.

| id | Severity | AI Suggestion | Edit |
| --- | --- | --- | --- |
| comprehension-1-1 | Medium | PROPOSE FIX | Stage 1 now defines `<name1>` (first NAME seen with the PATH), one warning per new NAME, silence for a repeated (PATH, NAME) pair, plus a 4-argument example; cli.main points to Stage 1 |
| comprehension-1-2 | Low | PROPOSE FIX | Stage 3 states the check order and defines N and M in the cell-count reason |
| comprehension-1-3 | Low | PROPOSE FIX | Glossary defines "blank record"; blank records skipped anywhere, header is the first non-blank record |
| comprehension-1-4 | Low | PROPOSE FIX | Rate grammar fixed to `^[0-9]+(\.[0-9]+)?$`; no sign/exponent/underscore; `-0` impossible |
| comprehension-1-5 | Low | PROPOSE FIX | Glossary narrows "normalised text" to client, description and rate patterns |
| comprehension-1-6 | Low | PROPOSE FIX | Implementation Plan states the repository root |
| comprehension-1-7 | Low | PROPOSE FIX | Author line spells out EGM |

Accepted fixes: 7. Contested: 0. Escalated: 0. Declined: 0. Remaining High/Medium: 0.
