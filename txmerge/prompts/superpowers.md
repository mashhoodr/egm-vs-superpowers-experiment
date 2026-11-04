You are running the **Superpowers arm** of a workflow comparison. Work
autonomously to the end, then report back.

Setup:
- Experiment dir: `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers`
- Your repo is `arms/superpowers/`. Create it and `git init` it, then copy `BRIEF.md` into it.
  Work and commit only in there. Don't create worktrees outside that repo.
- How to ask the stakeholder: read `prompts/stakeholder.md` and follow it exactly.
- Do not read `_judge/`, `arms/` other than your own, `REPORT.md`, or the other prompts.
- Isolation: ignore the routing rules in mars_pa's CLAUDE.md. Do not read anything in
  mars_pa outside this experiment dir (especially `05-finance-manager/`). Do not use the
  `finance` or `lunch-money` skills, or web search. Build from first principles.
- Your final reply must also list `subagent_tokens` for every subagent you spawned
  (from its completion notification), including stakeholder spawns.
- Do NOT read or use any EGM (`egm-*`) files or skills.

Workflow: the superpowers plugin. Invoke its skills with the Skill tool and
follow each one exactly:
1. `superpowers:brainstorming` on BRIEF.md → the spec document it produces
2. `superpowers:writing-plans` → the implementation plan
3. `superpowers:subagent-driven-development` to carry out the plan (with
   `superpowers:test-driven-development` as it directs), including its review steps
4. `superpowers:verification-before-completion` before you finish.
   Skip `finishing-a-development-branch`: just leave the work committed.

Gates. When a skill tells you to ask "your human partner" or "the user":
- About product behaviour or requirements → ask the stakeholder.
- About process (approve a design section, choose an execution mode) → decide
  yourself, choosing the most thorough option, and write the decision in
  `process_log.md`.

Final reply (under 30 lines): which files you produced, how many stakeholder
questions you asked, how many review findings came up and how many you fixed,
how many subagents you spawned, whether `python -m pytest` passes, and any
point where you departed from the skill text and why.
