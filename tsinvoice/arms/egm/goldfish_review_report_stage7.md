Status: resolved

# Goldfish Annotated Review Report — Stage 7 (Critic Review), round 1

**Target:** `docs/designs/tsinvoice.md` FeatureRange (1-543 at review time). Source: `critic_report.md`. Reviewers: egm-design, egm-structural, egm-style (all completed). Findings: 1 Blocker, 9 Major, 22 Nit.

| id | Severity | AI Suggestion | Edit |
| --- | --- | --- | --- |
| egm-structural-1-1 / egm-design-1-1 | High | PROPOSE FIX | New `## Risks & Mitigations` section (9 risks) with a Security paragraph (trusted local inputs, formula injection accepted, temp/symlink behaviour) |
| egm-design-1-2 | Medium | PROPOSE FIX | Decisions Log row for R1.12: primary user and measurable success criteria |
| egm-design-1-3 | Medium | PROPOSE FIX | Stage 2 "CSV reading" bullet: `newline=""`, default dialect, `strict=True`; any `csv.Error` fatal; plan + tests synced |
| egm-design-1-4 | Medium | PROPOSE FIX | Overflow → `invalid duration_minutes`; long-entry (>24 h) warning, kept; worked example; plan + tests synced |
| egm-structural-1-2 | Medium | PROPOSE FIX | Additional Resources / Future Improvements promoted to H2 |
| egm-structural-1-3 | Medium | PROPOSE FIX | Inline [D] tags + Decisions Log rows for every listed untagged rule (NFC, blank records, same PATH twice, extra cells, rates header, zero rate, touching sessions) |
| egm-style-1-1 | Medium | PROPOSE FIX | The Problem restates the duplicate rule exactly and lists the three warn-and-keep/skip behaviours |
| egm-style-1-2 | Medium | PROPOSE FIX | G6 renamed "Warn on data problems", scoped to listed cases; blank records/dedupe/joins stated as silent |
| egm-style-1-3 | Medium | PROPOSE FIX | Glossary defines "Blank"; "blank" used for all after-trim emptiness checks |
| egm-style-1-4 | Medium | PROPOSE FIX | Glossary term "Unrated session", used throughout |
| egm-design-1-5 | Low | PROPOSE FIX | Temp file `.tsinvoice-*`, `0o644`, removed on failure, symlink replaced |
| egm-design-1-6 | Low | PROPOSE FIX | Encoding risk row (accepted; re-export as UTF-8) |
| egm-design-1-7 | Low | PROPOSE FIX | G5 notes OS reason text may vary on exit 2 |
| egm-design-1-8 | Low | PROPOSE FIX | Zero rate allowed with no warning, stated as intended |
| egm-design-1-9 | Low | PROPOSE FIX | Substring over-match risk row (accepted, owner's rule) |
| egm-design-1-10 | Low | PROPOSE FIX | `normalise()` = NFC, trim/collapse, casefold, NFC |
| egm-structural-1-4 / egm-style-1-11 | Low | PROPOSE FIX | Field mapping moved before Format A/B bullets; blank cases in the reason table |
| egm-structural-1-5 / egm-style-1-9 | Low | PROPOSE FIX | Rewrapped the long lines; removed "So" filler |
| egm-structural-1-6 | Low | DECLINE | Unnumbered Non-Goals are not referenced anywhere |
| egm-structural-1-7 | Low | DECLINE | CUJ 1 shows the command once; later CUJs reuse it |
| egm-structural-1-8 | Low | DECLINE | Decisions Log location is linked from Overview and Open Questions |
| egm-structural-1-9 | Low | DECLINE | Section names follow the EGM design-doc template |
| egm-style-1-5 | Low | PROPOSE FIX | Dropped "small" |
| egm-style-1-6 | Low | PROPOSE FIX | "truncated" only |
| egm-style-1-7 | Low | PROPOSE FIX | "adds no rows" |
| egm-style-1-8 | Low | PROPOSE FIX | Removed "this is expected" |
| egm-style-1-10 | Low | PROPOSE FIX | Stage 2 and Alternatives E/G now point to the Decisions Log |
| egm-style-1-12 | Low | PROPOSE FIX | Stage 8 names the third case (Stage 1) |
| egm-style-1-13 | Low | PROPOSE FIX | Decisions Log wording tightened |
| egm-style-1-14 | Low | PROPOSE FIX | Alternatives use concrete facts |
| egm-style-1-15 | Low | PROPOSE FIX | Alternative H rationale corrected |
| egm-style-1-16 | Low | PROPOSE FIX | NFR performance wording made concrete |

Accepted fixes: 28 (1 High, 9 Medium, 18 Low). Contested: 0. Escalated: 0. Declined: 4 (Low). Remaining High/Medium: 0.
