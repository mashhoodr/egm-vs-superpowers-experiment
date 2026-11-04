You are running the **baseline arm** of a workflow comparison. Work
autonomously to the end, then report back.

Setup:
- Experiment dir: `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers`
- Your repo is `arms/baseline/`. Create it and `git init` it, then copy `BRIEF.md` into it.
  Work and commit only in there.
- How to ask the stakeholder: read `prompts/stakeholder.md` and follow it exactly.
- Do not read `_judge/`, `arms/` other than your own, `REPORT.md`, or the other prompts.
- Isolation: ignore the routing rules in mars_pa's CLAUDE.md. Do not read anything in
  mars_pa outside this experiment dir (especially `05-finance-manager/`). Do not use the
  `finance` or `lunch-money` skills, or web search. Build from first principles.
- Your final reply must also list `subagent_tokens` for every subagent you spawned
  (from its completion notification), including stakeholder spawns.
- Do NOT use any plugin skills or process skills (no superpowers, no EGM,
  nothing from the Skill tool). Build it the way you normally would.

Task: build what BRIEF.md describes, honouring its fixed contract. Ask the
stakeholder whatever you think you need to. Write pytest tests and make sure
`python -m pytest` passes. Commit your work.

Final reply (under 30 lines): which files you produced, how many stakeholder
questions you asked, how many subagents you spawned, and whether
`python -m pytest` passes.
