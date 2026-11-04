# Process log (Superpowers arm)

## Brainstorming
- Classification: **Architectural** (new project, no existing flow in repo). Announced; no override possible (autonomous) so the heavier path stands.
- Visual companion: not offered — CLI tool with no visual questions.
- Clarifying questions: the skill says one question per message, so each stakeholder spawn carries exactly one question (stakeholder.md permits batching, but the skill text wins for this arm).

## Subagent tokens
- stakeholder Q1: 45777
- stakeholder Q2: 46057
- stakeholder Q3: 45776
- stakeholder Q4: 45958
- stakeholder Q5: 45784
- stakeholder Q6: 45810
- stakeholder Q7: 46200
- stakeholder Q8: 46294
- stakeholder Q9: 46287
- stakeholder Q10: 47096

## Brainstorming gates (decided myself — process)
- Stopped asking after Q10: every product rule needed for the algorithm is now pinned (dedupe, join, rounding, pricing, time, errors, ordering, ids).
- Approaches considered: (A) pipeline of small pure modules (parse → dedupe → join → price → write) with a thin CLI; (B) one-file script; (C) load into sqlite and do dedupe/join in SQL. Chose **A**: each rule is testable in isolation, stdlib only, deterministic. B is harder to test; C makes the greedy tie-break join awkward and adds nothing.
- Design sections (architecture, components, data flow, error handling, testing): presented to myself in order and approved each — most thorough option is the full sectioned spec, which is what I wrote.
- Extra decisions not covered by stakeholder: empty client → bad row (description may be empty); a row with the wrong number of fields → bad row; blank lines skipped silently; CSV output uses `\n` line endings; Decimal arithmetic for money.
- Spec written: `docs/superpowers/specs/2026-11-03-tsinvoice-design.md`. Self-review: no placeholders; dedupe walk-through (2 vs 3 copies → 3) checked; scope fits one plan.
- "User reviews written spec" gate: process gate → approved myself (spec content already validated with stakeholder via Q10 write-back).

## Writing plans
- Plan: `docs/superpowers/plans/2026-11-03-tsinvoice.md` — 7 tasks (model, parse, dedupe, join, rates, ids+output, CLI+e2e), Review Focus with 5 pinned tests.
- Self-review fixes inline: invalid ISO hour in a join test (`T9:00` → `T09:00`); CLI used `price(..., 0)` instead of `Decimal(0)`.
- Execution-method gate (process): chose **Subagent-driven** (the most thorough option: fresh implementer + reviewers per task, final whole-branch review).

## Subagent-driven development
- Departure: skill says use a worktree; arm rules say don't create worktrees outside the repo. Used branch `feat/tsinvoice` inside the arm repo instead (isolation from main without a worktree).
- Ledger: `.superpowers/sdd/2026-11-03-tsinvoice/progress.md` (git-ignored).
- `python` is not on PATH in this environment (only `python3` 3.13.7); all test runs use `python3 -m pytest`.
- implementer T1: 55566
- reviewer T1: 53669
- implementer T2: 66504
- reviewer T2: 60969
- implementer T3: 54262
- reviewer T3: 52471
- implementer T4: 58214
- reviewer T4: 55558
- implementer T5: 61560
- reviewer T5: 57310
- implementer T6: 56043
- reviewer T6: 56819
- implementer T7: 64343
- reviewer T7: 60265
- final reviewer: 90290
- stakeholder Q11: 45816
- final fixer: 62774
- final re-reviewer: 61619

## Rulings I made (copied from SDD ledger before workspace deletion)
- Ruling: add .gitignore (__pycache__/, .pytest_cache/) as part of Task 2's dispatch — generated caches should never be committed; costs nothing if wrong.
- Ruling: encoding falls back to cp1252 with a warning — stakeholder left it to us; real Windows exports should not kill the run — if wrong, a mis-decoded file yields odd characters but warned.
- Ruling: date-only start_iso is a bad row — brief says ISO 8601 datetime — if wrong, such rows are skipped (warned), not silently mis-timed.
- Ruling: fix all 7 final findings in one fix wave (thorough option) — costs a slightly larger fix diff.
- Final: parked — output file mode becomes 0600 via NamedTemporaryFile — Ruling: real, deferred; no second fix wave allowed by the skill; cost if wrong: other local users can't read the CSV until chmod.
- Final: parked — absurd hourly_rate like 1E+999999999 raises decimal.Overflow traceback at load (not exit 2) — Ruling: real, deferred, pathological input; cost if wrong: traceback instead of a clean error message.

## Review findings tally
- Task reviews (7): 0 Critical, 0 Important, 27 Minor (deferred) + 1 ⚠ item resolved by controller. 1 minor (.gitignore) fixed via ruling in Task 2.
- Final whole-branch review: 1 Critical, 1 Important, 5 Minor — all 7 fixed in one fix wave (ed61f5a); this also resolved 3 deferred minors (T2 duration cap, T5 -0, T7 truncate).
- Fix-wave re-review: 7/7 addressed; 1 new Minor + 1 out-of-scope observation, both parked with rulings (no second fix wave per skill).

## Verification (verification-before-completion)
- `python3 -m pytest -q` → 86 passed, exit 0 (`python` not on PATH here).
- CLI smoke: dedupe by max count, cross-tracker join, pricing, exit 0, re-run byte-identical (cmp).
- Workspace `.superpowers/sdd/2026-11-03-tsinvoice/` deleted after final review per skill; finishing-a-development-branch skipped per arm instructions. Work left committed on branch `feat/tsinvoice`.

## Departures from skill text
- Worktree: used branch `feat/tsinvoice` in the arm repo (arm rules forbid worktrees outside it), then fast-forwarded `main` to it so `main` holds the work (not the finishing skill; no PR/options).
- `superpowers:test-driven-development` was not invoked via the Skill tool by me; TDD (RED/GREEN evidence) was required inline in every implementer dispatch and in the plan's steps.
- Q11 (SDD phase) batched two questions in one stakeholder spawn; brainstorming questions were one per spawn.
- SDD workspace deleted per skill; its ledger is preserved at `docs/superpowers/sdd-ledger.md`.
- `python` not on PATH: verification used `python3 -m pytest` / `python3 -m tsinvoice`.
