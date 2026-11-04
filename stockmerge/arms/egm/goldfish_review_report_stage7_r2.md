Status: resolved

# Goldfish Annotated Review Report — Stage 7 (Critic Review), round 2

**Target:** `docs/designs/stockmerge.md` (FeatureRange, lines 1-593 at review time)
Source findings: `critic_report_r2.md`. Severity map: Blocker = High, Major = Medium, Nit = Low.
Note: the synthesizer downgraded style-2-1 and structural-2-1 from the reviewers' Major to Nit.
Per egm-resolve ("do not change a severity") the Elephant treats both as Medium; both are fixed.
User decision (made by the Elephant): **auto accept**.

| ID | Sev | Suggestion | Edit |
| --- | --- | --- | --- |
| design-2-1 | Medium | PROPOSE FIX | R4.12 re-reads each line with normal quoting (verified: `"a, b"` stays one field; the unclosed-quote line gives 4 fields); Alternative K added |
| design-2-2 | Medium | PROPOSE FIX | R2.2 adds `os.path.samefile` when `--out` exists |
| style-2-1 | Medium (reviewer) | PROPOSE FIX | "the counts the counts" fixed |
| structural-2-1 | Medium (reviewer) | PROPOSE FIX | R4.11 moved before R4.12 |
| style-2-3 | Low | PROPOSE FIX | "command line layer" |
| style-2-5 | Low | PROPOSE FIX | "always uses the plural" |
| style-2-7 | Low | PROPOSE FIX | CUJ 1 shows each file's text |
| structural-2-4 | Low | PROPOSE FIX | Step 2 renamed "Output path check" |
| design-2-4 | Low | PROPOSE FIX | `str.strip()` named |
| design-2-5 | Low | PROPOSE FIX | R1.5 compares as in R2.2 |
| design-2-6 | Low | PROPOSE FIX | R3.2 names the parts of R4.x that apply |
| design-2-8 | Low | PROPOSE FIX | `prog="stockmerge"` named in R1.1 |
| design-2-3 | Low | DECLINE | owner (round 3 Q5) wants exactly 4 fields; header kept consistent; recorded in Risks & Limits |
| style-2-2, 2-4, 2-6, 2-8, 2-9, 2-10, structural-2-2, 2-3, 2-5, design-2-7 | Low | DECLINE | wording/layout preferences; no reader impact |

Counts: 4 Medium fixed, 8 Low fixed, 11 Low declined, 0 contested, 0 escalated.
