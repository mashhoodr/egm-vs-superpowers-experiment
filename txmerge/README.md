# Experiment: EGM vs Superpowers vs Baseline

**Question:** given the same vague-ish brief and the same stakeholder, which
workflow finds the hidden requirements and ships correct code?

| Arm | Workflow | Implementation |
|-----|----------|----------------|
| `egm` | EGM brainstorm → draft → goldfish review → resolve | plain implementer subagent |
| `superpowers` | brainstorming → writing-plans → subagent-driven-development (TDD) | per superpowers |
| `baseline` | no plugin, no process skills | the arm agent itself |

## Layout
- `BRIEF.md`: the only spec every arm gets (fixed CLI contract plus goals).
- `_judge/STAKEHOLDER.md`: 13 policies (K1–K13). Arms reach it only by asking.
- `_judge/hidden_tests/`: 18 acceptance tests, one or more per policy. They
  pass 18/18 against `_judge/reference/`.
- `arms/<arm>/`: each arm's own git repo (gitignored by mars_pa).
- `prompts/<arm>.md`: the exact prompt each arm orchestrator gets.
- `REPORT.md`: results, written last.

## Fairness rules
1. Same model for all arms, all launched in parallel from one session.
2. **Product questions** go to a fresh stakeholder subagent, which answers
   only what it's asked (see `prompts/stakeholder.md`). Every Q&A goes in
   `arms/<arm>/stakeholder_log.md`.
3. **Process gates** (approve a section, pick a review preset, choose
   execution mode) are answered by the arm itself, using the most thorough
   option the workflow offers.
4. No arm reads `_judge/`, the other arms, or `REPORT.md`.
5. All EGM skills are `disable-model-invocation`, so the EGM arm follows the
   SKILL.md files under `~/.claude/plugins/cache/egm/egm/0.1.0/skills/`
   step by step. This is the only route open to an agent.

## Scoring (in REPORT.md)
- Hidden tests passed (/18), plus which policies each arm got wrong.
- Discovery: which K-policies the arm actually asked the stakeholder about.
- Cost: subagent tokens, wall time, number of subagents.
- Blind code review: a fresh judge sees the three repos as X/Y/Z and scores
  correctness risk, clarity and test quality (1–5 each).
- Design artefact quality (egm vs superpowers spec), also blind.

## Run (in a fresh session, after the plugin install)
Tell Claude: "run the experiment in 06-project-manager/experiments/egm-vs-superpowers".
The orchestrating session follows these steps exactly:

1. **Preflight.** Check that `egm:egm-*` agent types (e.g. `egm:egm-zoom-out`) are in
   the available agent list. If they aren't, note it in REPORT.md; the
   EGM arm falls back to persona files. Check that `arms/` is empty.
2. **Launch.** Spawn three `general-purpose` agents in ONE message, each with
   the text of `prompts/<arm>.md` as its prompt. Record each one's start time.
3. **Wait** for all three notifications. Record `subagent_tokens`,
   `duration_ms` and `tool_uses`, plus the nested token totals each arm reports.
4. **Honesty audit.** For each arm, count `_judge` mentions in its task output
   file with `grep -c "_judge/STAKEHOLDER\|_judge/hidden\|_judge/reference"`.
   Hits are expected only from stakeholder spawn prompts. Any Read of `_judge/`
   by the arm itself voids the arm. Never read the transcript itself.
5. **Hidden tests.** For each arm:
   `TXMERGE_ROOT=arms/<arm> python3 -m pytest -q _judge/hidden_tests -rA`
   Map each failure to its K-id.
6. **Discovery.** A fresh subagent reads each `stakeholder_log.md` and the
   key, then tabulates which K1–K12 each arm asked about, plus UNCOVERED questions.
7. **Blind code review.** Copy only `txmerge/` and `tests/` from each arm into
   `_judge/blind/{X,Y,Z}/` (no `.git`, no docs), in a random order. Seal the
   mapping in `_judge/blind/MAPPING.txt`. A fresh judge reads only
   `_judge/blind/{X,Y,Z}` + BRIEF.md and scores correctness risk, clarity
   and test quality (1–5 each) with reasons.
8. **Blind design review.** Copy the EGM final design and the superpowers
   spec+plan into `_judge/blind/design_{P,Q}.md`, stripping workflow names,
   skill names and file headers. A fresh judge scores completeness against
   the brief, how ambiguous it is, and whether it could be implemented.
9. **Write REPORT.md**: TL;DR, a scoreboard table, per-policy results, cost,
   judge quotes, threats to validity (n=1, same model, scripted stakeholder,
   EGM run by hand from its skill files).
