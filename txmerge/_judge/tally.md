# Running tally (raw numbers, written as each arm finishes)

Started 2026-11-02 14:02 PKT, all three in parallel.

| Arm | Hidden | Own tests | Wall time | Orchestrator tokens | Nested tokens | Total | Subagents | Stakeholder Qs | Audit |
|---|---|---|---|---|---|---|---|---|---|
| baseline | 18/18 | 19 | 4m48s | 66,273 | 47,751 | ~114k | 1 | 14 (1 batch) | clean |
| superpowers | 18/18 | 88 | 27m53s | 205,344 | 1,200,152 | ~1.41M | 22 | 10 (7 spawns) | clean |
| egm | 18/18 | 105 | 71m06s | 459,748 | 1,753,983 | ~2.21M | 45 | 24 (4 spawns) | clean |

Notes
- Orchestrator token figures appear to exclude nested subagents: superpowers' 205k is far below its 1.2M nested.
- Superpowers left its code on branch `feat/txmerge`, not merged to `main`.
- Superpowers' final review found 1 Important issue: an unclosed quote swallowed the following rows. Its fix parses each line on its own.

## Robustness probe (`_judge/robustness_probe.py`, written before EGM finished)
All three handle 10/10 cases without crashing (reference too). The one real difference:
- **unclosed_quote** (3 rows, the first one broken): baseline warns about line 2 only
  and outputs **0 rows**. It silently loses 2 valid transactions, which breaks the
  brief's "never lose a real transaction". Superpowers outputs 2 rows and loses only
  the broken one.
- EGM unclosed_quote: exits 2 and writes no output. Fails closed: no silent loss, but no ledger either.
- EGM review: 52 Majors raised and fixed, about 250 Nits. Both review loops hit the 5-round cap without converging.

## EGM run 2 (synthesizer)
- Hidden 18/18. Tests 100. Unclosed quote: exit 0, 0 rows (silent loss). 67 agents, 33.6M processed, 9.23M cost units, root peak 303k, ~120 active min (slept 16:38–18:40). Audit clean (4 stakeholder spawns).
