# P3 tsinvoice tally
Launched 2026-11-03 11:47 PKT, 3 arms in parallel, published config (EGM via synthesizer).
Transcript ids: egm=a32b84d7c9f54dd6f superpowers=ab4e960e60dab1e7e baseline=a07946619ec1673f4
Kit verified: reference 18/18, naive set-dedupe fails 2 (K2), probe frozen before launch (reference graceful 9/10).

| Arm | Hidden | Probe graceful | unclosed_quote | out_is_input | Active time | Processed | Cost units | Agents |
|---|---|---|---|---|---|---|---|---|
| baseline | 18/18 | 10/10 | ✕ 0 rows | ✕ overwrites | 5.3 min | tbd | tbd | 3 |
- baseline: 18 questions in 2 rounds; audit clean (2 stakeholder spawns). Stakeholder emitted a '[Judge log]' line listing which answers were 'your call' (post-hoc, no policy leaked).
| superpowers | 18/18 | 10/10 | ✕ 0 rows | ✕ overwrites | 39.0 min | tbd | tbd | 29 |
- superpowers: 12 questions over 11 spawns (one per spawn, as the skill says); audit clean. 36 findings; final review found 1 Critical (1E+999999999 duration hang) + 1 Important (non-UTF-8 stops run), both fixed. Unclosed quote NOT caught this time.
| egm | 18/18 | 10/10 | ✕ 0 rows (by design, stakeholder-approved) | ✕ overwrites (by design, atomic) | 76.9 min | tbd | tbd | tbd |
- egm: 32 questions over 4 spawns; audit clean. 159 findings (2 Blocker, 36 Major) over ~10 rounds. It read the review caps as one re-audit per stage, not loop-to-5, so it was shorter than P1/P2.
- NUANCE: both probe failures were DELIBERATE design decisions. Unclosed quote: EGM asked; stakeholder answered "one bad row, exit 0" (a stretch of K5, as for SP on txmerge); spec R4.1 makes the rest of the file one bad row. --out == input: spec explicitly allows it via atomic temp+rename (design.md:447,510). The process found the cases; the decisions still lose data.

## Blind judges (unsealed: X=superpowers Y=egm Z=baseline, P=egm Q=superpowers)
- Code (/20): superpowers 16 (1st), egm 13 (2nd), baseline 13 (3rd: crashes on one bad value).
- Design (/25): egm 21, superpowers 18. EGM ~920 lines; SP spec/code disagree in 3 places; SP keeps phone seconds, so a handoff bills 24 min instead of 18.
- Discovery Y: baseline 10, superpowers 11, egm 12. The session_id fairness flag is moot (BRIEF says blank unless joined).
- $ (model-priced): baseline 1.15, superpowers 8.62, egm 25.22.
