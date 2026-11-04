# Three problems, three arms: what held and what didn't

Runs: txmerge (2 Nov, EGM run 2), stockmerge (P2) and tsinvoice (P3) on 3 Nov.
Only the problem statement changed. All three use the published configuration:
the same prompts, EGM routed through its synthesizer, arms in parallel, the
same stakeholder protocol and the same judges. Kits for P2 and P3 are in
`../egm-vs-superpowers-p2/` and `-p3/`.

## TL;DR
- **Superpowers wrote the best code in all 3 problems.** The blind code judge
  ranked it first every time.
- **EGM wrote the best design in all 3 problems,** by 3 to 4 points out of 25.
  Each one ran 780 to 1,060 lines and takes about an hour to read.
- **The hidden tests barely separate the arms.** Every arm scored 17 or 18 out
  of 18. The only rule anyone missed (stockmerge's move category) was missed
  by all three on merit; EGM got it only through a stakeholder leak.
- **Data-loss probes, out of 6 cases:** EGM 3, Superpowers 2, baseline 0.
  Neither plugin is reliable here.
- **Cost per run:** baseline about $0.93, Superpowers about $7.41 (8×), EGM
  about $29.52 (32×, or 4× Superpowers). Time: about 5, 33 and 97 minutes.
- **The published recommendation holds:** EGM's questions, then Superpowers'
  plan, build and final review. Two cost figures in the live article are
  wrong and need fixing (see the end of this report).

## Scoreboard

Each cell shows txmerge / stockmerge / tsinvoice.

| | Baseline | Superpowers | EGM |
|---|---|---|---|
| Hidden tests (/18) | 18 / 17 / 18 | 18 / 17 / 18 | 18 / 18† / 18 |
| Unclosed quote keeps valid rows | ✕ / ✕ / ✕ | ✓ / ✓ / ✕ | ✕ / ✓ / ✕‡ |
| Refuses `--out` = an input | ✕ / ✕ / ✕ | ✕ / ✕ / ✕ | ✓ / ✓ / ✕‡ |
| Blind code review (/20) | 12 / 11 / 13 | **18 / 17 / 16** | 15 / 12* / 13 |
| Code rank | 3 / 3 / 3 | **1 / 1 / 1** | 2 / 2 / 2 |
| Blind design review (/25) | - | 17 / 16 / 18 | **21 / 20 / 21** |
| Policies discovered, Y (/13) | 9 / 9 / 10 | 10 / 11 / 11 | 11 / 9†(11) / **12** |
| Stakeholder questions | 14 / 15 / 18 | ~20 / 29 / 12 | 27 / 29 / 32 |
| Active minutes | 5 / 4 / 5 | 28 / 32 / 39 | ~100 / 114 / 77 |
| Cost in $ (model-priced) | 0.71 / 0.94 / 1.15 | 6.46 / 7.15 / 8.62 | 30.99 / 32.35 / 25.22 |
| Agents in the tree | 2 / 3 / 3 | 23 / 25 / 29 | 67 / 66 / 41 |

† **Stakeholder leak on stockmerge.** EGM's question about how to detect a
move got the move-category rule (K7) volunteered in the answer. On merit, all
three arms missed it.
\* **Judge error on stockmerge.** The code judge called EGM's `Move` category a
defect, but it is the key's own policy. EGM's real top defect is skipping
valid ISO timestamps that end in `Z` or carry an offset.
‡ **Lost by design on tsinvoice.** EGM asked about both probe cases. The
stakeholder ruled "one bad row, exit 0", which stretches the key, and the
spec chose atomic writes that allow `--out` to equal an input. The process
found the cases, but the decisions still lose data.

## What held across all three problems

1. **Superpowers' code beats EGM's code.** The judge's reasons were the same
   each time:
   - smaller modules, with a review after every task;
   - one final review of the whole branch that catches a real bug;
   - plans whose code runs.

   EGM's single implementer, working from a 1,000-line spec, produced more code
   and more over-building.
2. **EGM's spec beats Superpowers' spec.** It is complete and unambiguous, with
   exact messages and reasons for each decision. Superpowers' plan contradicted
   its own spec in 3 to 7 places every time.
3. **The baseline asks good questions and then loses data.** It lost data in
   every one of its 6 probe cases, and it is the only arm that can crash on a
   single bad value.
4. **Cost ranks the same way every time.** EGM costs 2.9 to 4.8 times as much
   as Superpowers. Superpowers costs 7.5 to 9 times as much as the baseline.
5. **The review loops never settle.** EGM hit its round cap on every problem
   that ran the full loop. Superpowers' per-task reviews passed almost
   everything, and its final review found the important bugs:
   - txmerge: the unclosed quote
   - tsinvoice: a hang on a huge duration, and failure on a file that isn't UTF-8

## What flipped between problems
- **The unclosed-quote probe is noise for both plugins.** Superpowers passed it
  2 of 3 times and EGM 1 of 3. It depends on what one final review or one
  implementer happened to check.
- **EGM's process changed between runs.** On tsinvoice it took
  `egm-review`'s one-re-audit cap instead of looping to 5 rounds. That made it
  about 20% cheaper and 30% faster, with design and code scores unchanged.
  The long loops bought nothing measurable.
- **Which hidden policy decides the score changes from problem to problem:** the
  transfer category on txmerge, the move category on stockmerge, nothing on
  tsinvoice. Whether an arm asks about it, or the stakeholder leaks it, is close
  to chance.

## Methodology problems, all three problems
- **The stakeholder agent leaked policy on every problem,** helping a different
  arm each time. It also ruled on questions outside the key instead of saying
  "Your call". A fairer stakeholder would answer from fixed text per policy,
  not from a model paraphrasing the key.
- **Judges can't see the key,** so they can score a required behaviour as a
  defect, as happened on stockmerge. Check each top finding against the key
  before using the scores.
- **One run per problem per arm.** Three problems give 3 samples per arm, which
  is enough to see the stable patterns above but not to put a confidence
  number on any single cell.
- **Output tokens are undercounted in the transcripts,** so every $ figure is a
  lower bound. Output is a small share of the cost, so the ratios between arms
  should hold.

## Corrections the live article needs
`10-personal-website/writing/three-ways-to-build-the-same-tool.md` (txmerge):

| Claim | Published | Corrected (model-priced) |
|---|---|---|
| Weighted cost, Superpowers | 15× | **~9×** ($6.46 against $0.71). It sends most subagents to Sonnet and Haiku. |
| Weighted cost, EGM | roughly 40× | **~44×** ($30.99). Still "roughly 40×". |
| EGM against Superpowers | "about three times as much" | **about 4.8×**. Across 3 problems, 2.9 to 4.8×. |

The direction of every conclusion in the article holds, and the new problems
strengthen it.

Data: `_judge/prices_all_runs.json` (`_judge/price_runs.py`), and each problem's
`_judge/tally.md`, `judge_code.md`, `judge_design.md` and `discovery.md`.
