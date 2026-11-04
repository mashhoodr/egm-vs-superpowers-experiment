# EGM vs Superpowers vs a plain agent

**Results: [Three ways to build the same tool](https://karachiwala.dev/writing/three-ways-to-build-the-same-tool)** on karachiwala.dev.

This repo holds every file from that experiment, so the results can be audited:
the briefs, the prompts, everything each arm produced, the hidden tests, the
answer keys and the blind judges' verdicts.

## The experiment
The question: given the same loose brief and the same stakeholder, what do two
popular agent workflows buy over a plain agent, in correctness, robustness,
code quality, design quality and cost?

Three arms built the same small Python CLI in Claude Code, on the same model:

| Arm | Workflow |
|---|---|
| `baseline` | No plugin, no process skills |
| `superpowers` | [Superpowers](https://github.com/obra/superpowers): brainstorming, then writing-plans, then subagent-driven development with TDD and a final whole-branch review |
| `egm` | [Elephant-Goldfish Model](https://github.com/google/elephant-goldfish-model): an elephant drafts a spec, goldfish reviewers critique it through a synthesizer, then a separate implementer writes the code |

It was repeated on three problems. Only the problem statement changed between
them:

| Folder | Problem | Run |
|---|---|---|
| [`txmerge/`](txmerge/) | Merge overlapping bank CSV exports into one ledger: dedupe, link transfers, categorise | 2 Nov 2026 |
| [`stockmerge/`](stockmerge/) | Merge overlapping stock-take scans into one inventory: dedupe, link moves between locations, categorise | 3 Nov 2026 |
| [`tsinvoice/`](tsinvoice/) | Merge overlapping timesheet exports into invoice-ready sessions: dedupe, join continued entries, price | 3 Nov 2026 |

The article has the findings. For the full numbers across all three problems,
see [`txmerge/CROSS_PROBLEM_REPORT.md`](txmerge/CROSS_PROBLEM_REPORT.md).

## What was held constant
- The arm prompts (`prompts/`), with only paths and the module name swapped.
- A loose `BRIEF.md` with a fixed CLI contract. The rest was hidden in 13
  stakeholder policies (`_judge/STAKEHOLDER.md`, K1 to K13).
- A scripted stakeholder subagent that answered only what it was asked
  (`prompts/stakeholder.md`). Every Q&A is in `arms/<arm>/stakeholder_log.md`.
- 18 hidden acceptance tests per problem, validated at 18/18 against a
  reference implementation (`_judge/reference/`). On txmerge a naive
  set-dedupe variant was checked to fail the two K2 tests.
- A robustness probe, written before the arms ran, for cases beyond the key
  (`_judge/robustness_probe.py`).
- Blind judges for code (arms shuffled as X/Y/Z) and design (P/Q), with the
  mapping sealed in `_judge/blind*/MAPPING.txt` until scoring was done.
- An audit of each arm's transcript for reads of `_judge/`. There were none.

## Layout of each problem folder
```
BRIEF.md                 the only spec every arm received
prompts/                 the exact prompt each arm and the stakeholder got
arms/<arm>/              everything the arm produced: code, tests, specs,
                         review reports, stakeholder_log.md, process_log.md
arms/<arm>/GIT_HISTORY.txt   the arm's own commit history (its .git is not included)
_judge/                  key, hidden tests, reference, probe, blind judging,
                         tally.md (the scores)
```

## Re-running the checks
```bash
# hidden tests against an arm (env var per problem: TXMERGE_ROOT, STOCKMERGE_ROOT, TSINVOICE_ROOT)
TXMERGE_ROOT=txmerge/arms/superpowers python3 -m pytest -q -p no:cacheprovider txmerge/_judge/hidden_tests

# robustness probe
python3 -I txmerge/_judge/robustness_probe.py txmerge/arms/superpowers
```
With no env var set, the tests run against the reference and should pass 18/18.

## Things to know before auditing
- **txmerge has two EGM runs.** `arms/egm/` is run 1, where my instruction to
  self-report tokens led the arm to skip EGM's synthesizer. `arms/egm2/` is the
  rerun with the synthesizer (`prompts/egm2.md`), and it is the one the article
  and the cross-problem report use. `_judge/blind2/`, `judge_*2.md` and
  `discovery_egm2.md` are the re-judge with run 2. `REPORT.md` and
  `SESSION_ANALYSIS.md` cover both runs.
- **Cost.** `_judge/price_runs.py` prices every API call by the model that made
  it, with cache writes split by TTL. Its output is `_judge/prices_all_runs.json`.
  It reads Claude Code's raw subagent transcripts, which are **not** in this
  repo because they carry the host session's private context. Output tokens
  are undercounted in those transcripts, so every dollar figure is a lower
  bound.
- **The stakeholder leaked.** The LLM stakeholder volunteered policy it wasn't
  asked about on every problem, helping a different arm each time. On
  stockmerge it handed EGM the move-category rule (K7) that all three arms
  missed on merit.
- **The judges can't see the key.** On txmerge the code judge called greedy
  transfer pairing a defect, though K8 requires it (`REPORT.md`). On stockmerge
  it marked EGM's `Move` category as a defect, though K7 requires it. I
  corrected both by hand before ranking.
- **One run per arm per problem.** Three samples per arm show the stable
  patterns, but not a confidence interval on any single cell.
- The prompts contain absolute paths from my machine (`/Users/mashhoodr/...`).
  That is how the arms were pointed at their folders.
