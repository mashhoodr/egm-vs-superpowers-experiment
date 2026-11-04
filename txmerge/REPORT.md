# Report: EGM vs Superpowers vs Baseline: `txmerge`

Run 2026-11-02, 14:02–15:13 PKT. One model (Opus 5.5) for every arm and judge.
All three arms ran in parallel. Each answered the same scripted stakeholder.

## TL;DR
- **On the 13 scripted policies, all three tied at 18/18 hidden tests.** A
  plain agent that asked 14 questions up front got every one.
- **On the brief's own first requirement, the baseline fails and both plugins
  pass.** That requirement is "never lose a real transaction". After an
  unclosed CSV quote, the baseline silently drops every row that follows.
  Superpowers recovers line by line, and EGM refuses the file. A blind code
  judge ranked **EGM > Superpowers > Baseline**.
- **EGM produced the best design and asked the deepest questions.** It covered
  11/13 policies and asked 15 questions beyond the key, and a blind design judge
  scored it 20/25 against Superpowers' 16. But it was 580 lines and needed
  2.2M tokens.
- **Cost.** Baseline processed 0.85M tokens in 5 minutes. Superpowers
  processed 17.6M in 28 minutes (15× the baseline's cost-weighted spend), and
  EGM 47.5M in 71 minutes (36×). Most of it was each orchestrator re-reading
  its own growing context. See [SESSION_ANALYSIS.md](SESSION_ANALYSIS.md).
- **Verdict.** Both plugins caught a real data-loss bug that the plain agent
  shipped. EGM's code is slightly stronger: it won correctness 4 to 3 in the
  blind review. On cost, Superpowers delivers hardened code at about 40% of
  EGM's cost and 40% of its time. EGM is worth it when what you need is a
  spec someone else will implement.
  The cheapest likely fix is probably a fourth option: the baseline plus one
  final whole-branch review. See "If we run it again".

## Scoreboard

| | Baseline | Superpowers | EGM |
|---|---|---|---|
| Hidden tests (/18) | 18 | 18 | 18 |
| Robustness probe, graceful (/10) | 10 | 10 | 10 |
| Unclosed quote, 2 good rows after it | ❌ 0 rows, silent loss | ✅ keeps 2, warns | ⚠️ exit 2, no ledger |
| Blind code judge (/20) | 11 (3rd) | 16 (2nd) | 16 (1st on tiebreak) |
| Blind design judge (/25) | n/a | 16 | **20** |
| Policies discovered (Y + partial, /13) | 9 + 1 | 10 + 1 | **11 + 1** |
| Questions beyond the key ("your call") | 3 | 5 | **15** |
| Wall time | **4m48s** | 27m53s | 71m06s |
| Tokens processed (all agents) | **0.85M** | 17.6M | 47.5M |
| Cost-weighted vs baseline | 1× | 15× | 36× |
| Subagents | 1 | 22 | 45 |
| Source / test lines | 309 / 230 | 371 / 623 | 459 / 783 |
| Review findings | none | 29 (1 Important) | 52 Major, ~250 Nit |

Raw numbers: `_judge/tally.md`. Judge verdicts: `_judge/judge_code.md`,
`_judge/judge_design.md`, `_judge/discovery.md`. Probe: `_judge/robustness_probe.py`.

## What each process bought

**Baseline:** one batch of 14 questions, then code. It found almost
everything the key held. Where it went wrong was everything nobody reviewed:
- an unclosed quote silently swallows the rows after it (`core.py:120`)
- a negative Debit has its sign flipped without a warning
- `1e3` and `1,2,3` are accepted as amounts
- some CSV errors crash with a traceback

None of these are tested.

**Superpowers:**
- **Process:** a short spec (~95 lines), then a plan full of code, then 6
  tasks each built by an implementer subagent with a reviewer after it.
- **Reviews:** all 6 per-task reviews passed first time. The **one Important
  bug, the unclosed quote, was caught only by the final whole-branch review.**
  The per-task reviews mostly paid for clean modules (the judge scored it
  highest on clarity, 5/5).
- **Defects left:**
  - Its line-by-line CSV reading drops a quoted description that spans two
    lines. Its own test treats this as intended.
  - `1,2,3` is read as 123.
  - It matches transfers on unrounded amounts, so `10.005` matches but is
    written as `-10.01`.
  - Per the blind design judge, the plan's code contradicts its own spec in
    about 7 places. Some of these were fixed in the final fix commit, as the
    judge read the plan, not the final code.

**EGM:**
- **Process:** a brainstorm with zero-context reviewers, then a draft, then a
  5-stage review (~10 rounds), then resolve. Only then did one implementer
  write the code.
- **Questions:** it asked the most, and the most precise:
  - `--out` pointing at an input file
  - amount grammar, with rounding when the amount is read
  - warning line numbers for rows that span several lines
- **Results:** the judge found the design specifies every byte of output, and
  the code never silently drops or misreads a row.
- **Cost:**
  - Both review loops hit the 5-round cap without converging. The
    writing-style reviewer raised new wording issues every round.
  - The design is ~580 lines with duplication across its alternatives, the
    Decision Log and the risks table.
  - Rejecting a row because the unused Debit/Credit column holds `0.00` arguably
    goes against "never lose a real transaction".

## Corrections to the judges
- The code judge called greedy transfer pairing a defect in all three. But the
  stakeholder **required** greedy, closest-date pairing (K8), so it isn't a
  bug against this spec.
- The design judge scored the Superpowers *plan's* inline code. Some of the
  gaps between spec and code it lists were fixed later, so its score
  understates the final code. The code judge's score is the better measure of
  what Superpowers shipped.

## Threats to validity
- **n = 1 per arm.** This is one run on one task. Treat it as a signal, not a
  measurement.
- **The answer key was too easy to discover.** The brief made most policies
  obvious enough that the baseline asked about them directly, so the hidden
  tests hit their ceiling. A harder brief would hide policies that only
  appear once you work through the edge cases.
- **The stakeholder made mistakes.**
  - EGM got a firm rules-matching answer on its second attempt, a rule that
    isn't in the key: a small advantage.
  - The stakeholder told Superpowers how to handle the unclosed quote by
    stretching the skip-malformed-rows policy. So Superpowers' handling was
    partly given to it, though its own review found the bug.
  - A few answers volunteered policies nobody had asked about, with no net
    effect.
- **EGM was followed from its skill files.** All its skills are
  user-invocable only, so an agent read and followed them, with no human at
  the gates. The arm batched its questions, called reviewers directly rather
  than through the synthesizer, and self-approved the draft sections. Real use
  has a human at each gate, which costs more time and may give better results.
- **Token figures were corrected after the fact.** The first draft used each
  agent's reported `subagent_tokens`, which turned out to be its final context
  size. The numbers here come from the per-call usage in the transcripts.
  Output tokens are still undercounted, so treat these as lower bounds.
- **Reporting tokens changed how EGM ran.** Because arms had to report
  per-subagent tokens, EGM skipped its synthesizer and pasted every
  reviewer's report into its orchestrator. That probably inflated its cost.
- **EGM used its real reviewers.** It ran the registered `egm:egm-*` agents
  (style ×10, design/structural/readiness/codebase ×6 each,
  comprehension/zoom-out ×3), not general-purpose stand-ins. That supports the
  claim that it followed EGM faithfully.
- **Superpowers left its work on branch `feat/txmerge`** and skipped the
  branch-finishing step, as instructed.
- **Neither plugin had a human partner.** Both are built around one, so this
  test measures them running unattended.
- **Same model throughout.** The judges are the same model as the builders and
  may share their blind spots.

## If we run it again
1. Use a brief with hidden traps: rows spanning lines, refunds that look like
   transfers, and amount formats that differ by locale.
2. Run each arm 3 times to see the variance.
3. Cap EGM's style-reviewer rounds, or drop that reviewer, to see if cost
   halves without losing quality.
4. Add a fourth arm, the baseline plus one final whole-branch review. It's
   likely most of Superpowers' benefit at a fraction of the cost.

## Addendum: EGM run 2 with the synthesizer (2026-11-02, 16:10–19:47 PKT)

Change from run 1: reviewers were routed through `egm:egm-synthesizer`, and
the arm did not report its own tokens. Everything else was identical. The
laptop slept from 16:38 to about 18:40 mid-run; active time is estimated
with that pause left out.

| | EGM run 1 (direct) | EGM run 2 (synthesizer) |
|---|---|---|
| Hidden tests | 18/18 | 18/18 |
| Unclosed quote | ⚠️ exit 2, no ledger | ❌ **exit 0, 0 rows, 2 good rows lost** |
| Stakeholder questions | 24 | 27 |
| Review rounds / Blocker+Major fixed | ~16 / 52 | 16 / 35 |
| Final design | 581 lines | **784 lines** |
| Source / test lines | 459 / 783 | 423 / 802 |
| Agents in tree | 46 | 67 (15 synthesizers) |
| Tokens processed | 47.5M | **33.6M (−29%)** |
| Orchestrator peak context | 458k | **303k (−34%)** |
| Cost-weighted units | 7.64M | **9.23M (+21%)** |
| Active time | 71 min | ~120 min |

**Why fewer tokens but higher cost**
- **The orchestrator's cache reads halved,** from 43.9M to 23.5M. That part
  worked as intended: the reports stayed out of its context.
- **But its cache writes quadrupled,** from 0.46M to 1.87M. The orchestrator
  now waits longer each round while a synthesizer finishes. When the wait
  outlasts the prompt-cache lifetime, the next call has to rewrite the whole
  ~230–290k context at 1.25× the price. That happened 6 times; 2 were caused
  by the laptop sleeping.
- **The 15 synthesizers cost 1.85M units of their own.**
- **Net effect: the synthesizer moves cost around rather than removing it.**
  Synthesizers plus cache rewrites cost more than the cache reads they saved.

**What it says about EGM**
- **Results vary from run to run.** The same workflow and brief produced
  opposite behaviour on the unclosed quote: one run refused the file, the
  other silently lost rows. A long review process didn't make this edge case
  reliable, and neither design specifies line-spanning or broken quotes in a
  way the implementer copied faithfully.
- **The design grew,** from 581 to 784 lines. Neither run's review loop
  settled before the 5-round cap.
- **Revised ranking on the unclosed-quote requirement:** Superpowers 1/1,
  EGM 1/2, baseline 0/1. Each is a single sample.

Data: `_judge/tokens_egm_runs.json`. Script: `_judge/token_analysis.py`.

## Addendum 2: re-judged with EGM run 2 (used for the published article)

Run 1 was set aside: my instruction to self-report tokens made it skip the
synthesizer. All three arms were re-judged blind, together, with a fresh
shuffle (`_judge/blind2/`). Judges were told that greedy transfer pairing and
skip-and-warn were stakeholder requirements.

| | Baseline | Superpowers | EGM (run 2) |
|---|---|---|---|
| Blind code review (/20) | 12 | **18** | 15 |
| Blind design review (/25) | n/a | 17 | **21** |
| Policies discovered (/13) | 9 + 1 partial | 10 + 1 partial | **11 + 1 partial** (27 questions) |
| Unclosed quote | ❌ loses rows | ✅ keeps rows | ❌ loses rows |
| `--out` points at an input | ❌ overwrites it | ❌ overwrites it | ✅ refuses, exit 2 |
| Active time | 5 min | 28 min | ~100 min |
| Cost-weighted | 1× | 15× | ~44× (≈41× without the 2 cache rebuilds caused by sleep) |

- **EGM cost by phase.** Brainstorm and stakeholder rounds were 7% of its cost,
  and that is where most of its discovery happened. The review stages (5–9)
  were 39%, and the orchestrator another 52%.
- **The unclosed-quote case.** EGM's spec never mentions it. Its 16 review
  rounds read the design and never ran code.
- **Sources:** `_judge/judge_code2.md`, `_judge/judge_design2.md`,
  `_judge/discovery_egm2.md`, and the `--out` probe run by hand 2026-11-02.
