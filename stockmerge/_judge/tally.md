# P2 stockmerge tally
Launched 2026-11-03 09:52 PKT, 3 arms in parallel, published config (EGM via synthesizer).
Transcript ids (subagents/agent-<id>.jsonl): egm=a661920d7e95a5fba superpowers=ab2cb61ae60b9b76e baseline=ae5166f2caa015cc4
Kit verified: reference 18/18, naive set-dedupe fails 2 (K2), probe frozen before launch (reference graceful 10/10).

| Arm | Hidden | Probe graceful | unclosed_quote | out_is_input | Active time | Processed | Cost units | Agents |
|---|---|---|---|---|---|---|---|---|
| baseline | 17/18 (K7: never asked move category) | 10/10 | ✕ 0 rows | ✕ overwrites | 4.0 min | tbd | tbd | 3 |
- baseline: 15 questions in 2 rounds; audit clean (2 stakeholder spawns).
| superpowers | 17/18 (K7: never asked move category) | 10/10 | ✓ keeps 2 | ✕ overwrites | 32.3 min | tbd | tbd | 25 |
- superpowers: 29 questions over 5 spawns (audit shows 6 stakeholder Agent calls, clean). 38 findings (7 Important, all fixed). 77 own tests.
- MODEL MIX FINDING: superpowers runs subagents on Sonnet/Haiku (txmerge: 9 opus / 9 sonnet / 5 haiku; p2: 7/11/7). baseline + EGM are all-Opus. The published cost weighting priced every token alike, so it overstates superpowers' relative $ cost. Re-price by model in the cross-problem analysis.
| egm | **18/18** | 10/10 | ✓ keeps 2 | ✓ refuses, exit 2 | 113.6 min | tbd | tbd | tbd |
- egm: 29 questions over 3 spawns; audit clean. 59 Majors (all addressed) + 277 Nits. Both loops hit the 5-round cap. Final design docs/designs/stockmerge.md. 122 own tests.

## Fairness correction (discovery judge, verified by hand against arms/egm/stakeholder_log.md:24)
- EGM's K7 pass is a STAKEHOLDER LEAK. EGM asked only what must match for a move and the time window. The answer volunteered "category `Move`, rules are not applied". On merit, all three arms missed the move category. Treat hidden tests as 17/17/17 + 1 leaked.
- The baseline got a "dedupe before moves = Yes" ruling that SP and EGM were refused ("Your call"). Lower impact; the tests don't hinge on it.
- Discovery (Y/P/N): baseline 9/3/1 (15 Qs), superpowers 11/2/0 (29 Qs), egm 11/1/1 incl. 2 leaked, 9/3/1 without them (29 Qs).
- Probe results are NOT affected by the leak: neither probe case is in the key.

## Blind judges (mapping above unsealed after both reported)
- Code (/20): superpowers 17 (1st), egm 12 (2nd), baseline 11 (3rd).
  CORRECTION: the judge's "most serious defect" for egm (move rows get category `Move`) is the key's K7 policy. EGM got it via the leak and the judge didn't know. EGM's correctness score (3) is understated; its real top defect is the runner-up: ISO times with `Z`/offset/no-seconds are skipped.
  Superpowers' top defect: `--out` = input overwrites the export (matches probe). Baseline: unclosed quote swallows rows; crashes past ~6k rows.
- Design (/25): egm 20, superpowers 16. EGM ~1,060 lines, 60-75 min read; SP plan contradicts its design in 3 places and leaves move category, --out-as-input and unclosed quote open.
