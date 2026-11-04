You are running the **EGM arm** of a workflow comparison. Work autonomously
to the end, then report back.

Setup:
- Experiment dir: `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers`
- Your repo is `arms/egm/`. Create it and `git init` it, then copy `BRIEF.md` into it.
  Work and commit only in there.
- How to ask the stakeholder: read `prompts/stakeholder.md` and follow it exactly.
- Do not read `_judge/`, `arms/` other than your own, `REPORT.md`, or the other prompts.
- Isolation: ignore the routing rules in mars_pa's CLAUDE.md. Do not read anything in
  mars_pa outside this experiment dir (especially `05-finance-manager/`). Do not use the
  `finance` or `lunch-money` skills, or web search. Build from first principles.
- Your final reply must also list `subagent_tokens` for every subagent you spawned
  (from its completion notification), including stakeholder spawns.
- Do NOT use any superpowers skills, and don't invoke other process skills.

Workflow: the Elephant-Goldfish Model plugin. You are the Elephant. Its skills
can't be model-invoked, so read each one and follow it step by step:
`/Users/mashhoodr/.claude/plugins/cache/egm/egm/0.1.0/skills/<skill>/SKILL.md`
(`CLAUDE_PLUGIN_ROOT=/Users/mashhoodr/.claude/plugins/cache/egm/egm/0.1.0`; read `$CLAUDE_PLUGIN_ROOT/docs/claude.md` first).
1. `egm-brainstorm` on BRIEF.md → `concepts_brief.md`
2. `egm-draft` → `design_draft.md`
3. `egm-review` on the draft, using the most complete preset. Spawn the
   Goldfish reviewers as the skill says, using the `egm:egm-*` named subagent
   types if available, or general-purpose agents told to read the persona file.
4. `egm-resolve`: address every finding that is high or medium severity.
5. Once the design is approved, spawn ONE fresh `general-purpose` implementer
   subagent with this prompt only: "Implement the design in
   `<FINAL_DESIGN_PATH>` inside `<repo>`, honouring the fixed contract in
   `<repo>/BRIEF.md`. Write pytest tests. Make sure `python -m pytest` passes.
   Commit your work. Don't read anything outside `<repo>`."
   `<FINAL_DESIGN_PATH>` is the final approved design, wherever EGM saved it after
   resolve (it may not be `design_draft.md`). Name that path in your final reply.

Gates. When the skill tells you to ask "the user":
- About product behaviour or requirements → ask the stakeholder.
- About process (approve a section, pick a preset, which findings to fix) →
  decide yourself, choosing the most thorough option, and write the decision
  in `process_log.md`.

Final reply (under 30 lines): which files you produced, how many stakeholder
questions you asked, how many review findings came up and how many you fixed,
how many subagents you spawned, whether the implementer's tests pass, and any
point where you departed from the skill text and why.
