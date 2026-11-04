# Process log (Superpowers arm)

## Brainstorming
- Classification: **architectural** (new project, no existing flow). Full path: questions, approaches, sectioned design, written spec, spec review, writing-plans.
- Visual companion: not offered; no question in this CLI tool is visual.
- Departure: the skill asks for one question per message. Each stakeholder question costs a fresh subagent spawn, and the stakeholder prompt explicitly allows batching, so I asked in a few themed rounds instead of one at a time. Follow-up rounds were used where answers opened new questions.
- Understanding write-back and design sections (architecture, data flow, errors, testing): presented to myself section by section; approved each (process gate, decided myself). Approaches considered: pure-function pipeline (chosen), single script, in-memory SQLite.
- "Your call" product items from the stakeholder were decided and marked **[our call]** in the spec.
- Spec self-review done inline (placeholder/consistency/scope/ambiguity). Fixed: made rule matching explicit against the normalised SKU; made line numbering explicit.
- Spec review gate: approved by me (process gate) so writing-plans may start.

## Writing plans
- Plan saved to `docs/superpowers/plans/2026-11-03-stockmerge.md` (7 tasks). Self-review done: spec coverage, placeholder scan, type consistency, Review Focus (5 items, each pinned to a test in its owning task). Hand-traced the expected output of the end-to-end test and the move-pairing tests against the planned code.
- Plan review gate: approved by me (process gate).
- Execution method: **Subagent-driven** (the most thorough option: fresh implementer per task, fresh reviewers per task, whole-branch review at the end).

## Subagent-driven development
- Departure: no git worktree. The arm instructions forbid worktrees outside the repo; I worked on branch `feat/stockmerge` inside the arm repo instead (same isolation from `main`).
- Models: implementers haiku (plan carried complete code), task reviewers and scoped re-reviewers sonnet, final whole-branch review opus, final fix wave sonnet.
- Pre-flight scan table, per-task ledger, rulings and deferred minors live in `.superpowers/sdd/2026-11-03-stockmerge/progress.md` (git-ignored scratch).
- Departure: the skill says to delete the plan workspace after a clean final review. I kept it, because the user's standing rule is that deletions need explicit approval, and it holds the ledger.
- Product question raised by the final review (rule patterns with leading zeros; unquoted comma in a note) went to the stakeholder (see `stakeholder_log.md`); the "your call" part was decided and written into spec §4.

### Rulings made (from the ledger, in order, with cost if wrong)
1. Branch instead of worktree. Cost: none.
2. Commit trailers name the implementing model. Cost: cosmetic metadata.
3. Readers parse each physical line as its own CSV record. Cost: a note with an embedded newline becomes bad-row warnings and that scan is skipped (with a warning).
4. Writer applies umask mode; tie-break test rewritten. Cost: small extra code.
5. Rule pattern matches the normalised key OR the casefolded original text. Cost: two spellings of one SKU can, rarely, get different categories.
6. Unquoted comma in a Format B note stays a bad row (stakeholder answer). Cost: none.
7. Final fix wave scope: Important 1-3 plus four minors; other minors parked as non-blocking per the final reviewer's triage. Cost: parked minors stay open.

## Verification before completion
- `python3 -m pytest -q` → 77 passed (fresh run). `python` is not on this machine's PATH, so `python -m pytest` cannot run here; `python3` is 3.13.7.
- Manual CLI run on mixed Format A/B exports: duplicates across formats removed, intra-export repeats kept, a move at exactly 2 h linked as M1, bad row warned with file:line and exit 0; two runs byte-identical (`cmp`); unknown header → exit 2 and no output file.
- Ruling: fast-forwarded `main` to the reviewed `feat/stockmerge` head, so the default branch carries the work (a non-destructive fast-forward in this private arm repo; `finishing-a-development-branch` was skipped as instructed). Cost if wrong: none; both refs point at the same commit.
