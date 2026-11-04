# Session analysis: where the tokens went

Source: every agent's JSONL transcript, with each arm's agent tree rebuilt
from its `Agent` tool results. Script: `_judge/token_analysis.py`. Raw data:
`_judge/tokens.json` and `_judge/token_categories.txt`.

## TL;DR
- **The token numbers in the first report were wrong by 7–21×.** The
  `subagent_tokens` figure an agent reports is its **final context size**,
  not its spend. Real spend is 0.85M (baseline), 17.6M (superpowers) and
  47.5M (EGM) tokens processed.
- **The orchestrator is the bill, not the subagents.** It is 93% of EGM's
  tokens and 74% of superpowers'. Every API call re-reads the whole growing
  context, so cost ≈ calls × average context. EGM made 160 calls at an
  average of about 280k context.
- **EGM's reviewers were cheap. Bringing their reports back was expensive.**
  The 39 reviewer runs used only about 2M tokens. But their 46 reports,
  averaging about 8k chars each, were pasted into the orchestrator. It then
  rewrote the 33k-char design about 10 times and re-read all of it on every
  later call.
- **Some of this is my experiment's fault.** I asked every arm to report
  per-subagent token counts. To get them, the EGM arm called reviewers
  directly and skipped `egm:egm-synthesizer`, which normally merges findings
  outside the orchestrator. That probably inflated EGM's orchestrator
  context.

## Corrected totals

| | Baseline | Superpowers | EGM |
|---|---|---|---|
| Agents in tree | 2 | 23 | 46 |
| API calls | 16 | 190 | 268 |
| Tokens processed | **0.85M** | **17.6M** (21×) | **47.5M** (56×) |
| …of which cache reads | 89% | 94% | 96% |
| Cost-weighted units¹ | 0.21M | 3.07M (15×) | 7.64M (36×) |
| Illustrative $ at $5/M input-equivalent¹ | ~$1 | ~$15 | ~$38 |
| Orchestrator share of cost | 81% | 51% | 69% |
| Orchestrator peak context | 65k | 203k | **458k** |
| Wall time | 4.8 min | 27.9 min | 71.1 min |

¹ Weights relative to uncached input: cache read 0.1×, cache write 1.25×,
output 5×. These are Opus-family price ratios; the $ figure illustrates
scale only. **Output tokens are undercounted**: transcripts log usage before
a reply has finished streaming, and the baseline recorded 4.8k output tokens
against about 10k of code it wrote. Treat cost as a lower bound.

## Where each arm spent it

**Baseline: one loop with a flat context.**

| Spend | Processed | Cost share |
|---|---|---|
| Orchestrator (15 calls, 40k → 65k context) | 0.76M | 81% |
| Stakeholder (1 spawn, 14 questions) | 0.09M | 19% |

- Half its context was the fixed startup load: system prompt, tool schemas,
  CLAUDE.md and the skill listing.
- It wrote the code directly with `Write`.

**Superpowers: a heavy orchestrator and light workers.**

| Spend | n | Processed | Cost share | Agent-minutes |
|---|---|---|---|---|
| Orchestrator (100 calls, 40k → 203k) | 1 | 12.95M | 51% | 27.9 |
| Task implementers | 6 | 2.10M | 17% | 3.2 |
| Per-task reviewers | 6 | 0.63M | 12% | 2.6 |
| Final review, fix, re-review | 3 | 1.33M | 11% | 4.7 |
| Stakeholder | 7 | 0.60M | 9% | 1.1 |

- **The orchestrator did the real authoring.** Its spec and plan, ~1,240
  lines with complete code for each task, went to disk through Bash heredocs
  (127k chars) that stayed in its context. The skill bodies it loaded added
  another 62k chars.
- **The implementers mostly copied code from the plan.** All 6 took 3.2
  agent-minutes in total. That's why their output looks so small.
- **The cheapest child found the important bug.** The 3-agent final-review
  cycle, 11% of cost, caught the unclosed-quote bug. The 6 per-task reviewers
  (12%) passed everything first time.
- **Stakeholder questions cost the most per question.** It asked them one at
  a time, as the skill says, at ~85k tokens per spawn. That made 7 spawns
  against EGM's 4 batches.

**EGM: cheap reviewers and a giant orchestrator.**

| Spend | n | Processed | Cost share | Agent-minutes |
|---|---|---|---|---|
| Orchestrator (160 calls, 40k → 458k) | 1 | 44.39M | 69% | 71.1 |
| Stage 9 (readiness / codebase / style × 5 rounds) | 15 | 0.79M | 13% | 44.2 |
| Stage 7 (design / structure / style × 5 rounds) | 15 | 0.71M | 9% | 19.3 |
| Stages 5, 6, 8 | 4 | 0.31M | 3% | 6.2 |
| Implementer | 1 | 0.84M | 3% | 3.0 |
| Brainstorm lenses | 6 | 0.13M | 2% | 8.6 |
| Stakeholder (4 batches, 24 questions) | 4 | 0.34M | 2% | 0.9 |

What filled the orchestrator's 458k context:

| Source | Chars | Share |
|---|---|---|
| Subagent reports pasted back (46 reports) | 363k | 24% |
| Bash calls, mostly heredoc rewrites of the design | 238k | 15% |
| Tool results: skill files, git, test runs | 268k | 17% |
| Its own thinking | 146k | 9% |

- **EGM's reviewers are cheap to start.** They are restricted to Read, Grep
  and Glob, so they start at **~14k context**. A general-purpose agent starts
  at **~45k**, because it carries all tool schemas, CLAUDE.md and the skill
  listing.
- **Stage 9 used the most wall time.** The codebase-details reviewer read up
  to 92k of context and wrote reports of up to 18k tokens.

## What drives the cost differences
1. **Orchestrator calls × its context size.** EGM's 160 calls at an average
   of ~280k is about 44M tokens. Superpowers' 100 calls at ~130k is about 13M.
   Every extra round, report or rewrite raises the context that all later
   calls re-read, so the cost grows roughly with the square of the number of
   calls.
2. **Where reports land.** Both plugins send findings back as full messages to
   the orchestrator. EGM's 46 reports are 5× superpowers' total by volume.
   EGM's synthesizer exists to keep these out of the orchestrator, and this
   run bypassed it.
3. **Who writes the main document.** In both plugins the orchestrator writes
   the design and plan into its own context. EGM revised a 33k-char design
   about 10 times, and superpowers wrote a plan full of code once. The
   baseline wrote only code.
4. **Fixed startup cost per spawn.** A general-purpose subagent costs ~45k
   tokens of context before doing anything. Stakeholder spawns paid that each
   time to answer from a 3k-char file. EGM's restricted agents avoid most of
   it.
5. **Review loops that don't settle.** Both EGM loops ran to the 5-round cap.
   The style reviewer ran 10 times and kept finding new wording to fix, and
   each round added reports and a rewrite to the orchestrator.

## How to cut the cost without losing the benefit
- **EGM:** route reviewers through `egm:egm-synthesizer` so findings land in
  files, not the orchestrator. Drop or cap the style lens. Stop a loop as soon
  as there are no Majors, not after 2 clean rounds.
- **Superpowers:** keep the final whole-branch review, which is where the real
  bug was found. Consider skipping per-task reviews when the plan already
  contains the code. Batch stakeholder questions.
- **Either:** start a fresh orchestrator per phase, handing over a summary on
  disk. Most of the cost is one context that keeps growing.
- **Next experiment:** don't make arms report per-subagent tokens, which
  changed EGM's behaviour. Get the numbers from the transcripts afterwards, as
  done here.
