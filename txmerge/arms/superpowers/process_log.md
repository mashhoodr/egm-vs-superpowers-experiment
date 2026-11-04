# Process log (Superpowers arm)

Decisions taken on process gates (not product questions), per arm instructions.

## Brainstorming
- **Path classification:** Architectural (new project, no existing flow in repo). Heavier path chosen per skill.
- **Visual companion:** not offered — no question is visual (CLI/CSV tool).
- **Question cadence:** skill says one question per message. Stakeholder protocol allows batching.
  Decision: ask the intent question alone first, then one topic per stakeholder spawn
  (closest to skill text while keeping the stakeholder fresh per spawn).
- **Departure:** spawn 6 batched three short input-handling questions (allowed by stakeholder protocol) instead of one per message, to keep spawn count reasonable; each was a narrow factual question.
- Stopped asking after 6 spawns: remaining unknowns were answered "your call" or are implementation details; choices recorded in stakeholder_log.md.
- **Approaches:** proposed 3 (see spec "Approaches considered"); chose pipeline of pure functions. Decision by me (process gate).
- **Design section approval:** each section (architecture, components, data flow, errors, testing) self-reviewed against stakeholder answers and approved by me; recorded here instead of asking the stakeholder (process gate).
- **Spec self-review:** fixed inline — survivors keep own source positions; Decimal quantize for amounts; explicit pipeline order.
- **Spec review gate:** process gate → self-approved. Every product-facing item came from a stakeholder answer or a "your call" answer (choices recorded). Did not re-spawn stakeholder.

## Subagent tokens
| # | Purpose | subagent_tokens |
|---|---------|-----------------|
| 1 | stakeholder Q1 | 45181 |
| 2 | stakeholder Q2 | 45511 |
| 3 | stakeholder Q3 | 45844 |
| 4 | stakeholder Q4 | 45864 |
| 5 | stakeholder Q5 | 45395 |
| 6 | stakeholder Q6 | 45846 |
| 7 | T1-implementer | 61253 |
| 8 | T1-reviewer | 61800 |
| 9 | T2-implementer | 55638 |
| 10 | T2-reviewer | 54216 |
| 11 | T3-implementer | 56632 |
| 12 | T3-reviewer | 56547 |
| 13 | T4-implementer | 54559 |
| 14 | T4-reviewer | 53713 |
| 15 | T5-implementer | 52322 |
| 16 | T5-reviewer | 53181 |
| 17 | T6-implementer | 54789 |
| 18 | T6-reviewer | 58014 |
| 19 | final-reviewer | 73822 |
| 20 | stakeholder-Q7 | 45668 |
| 21 | final-fixer | 68072 |
| 22 | final-rereviewer | 66285 |

## Writing plans
- Plan: `docs/superpowers/plans/2026-11-02-txmerge.md`, 6 tasks. Self-review fixed 3 test bugs inline (imprecise warning assertion, wrong expected survivor sources, odd literal).
- **Execution method gate:** process → chose **Subagent-driven** (most thorough: fresh implementer + reviewers per task + whole-branch review).
- **Plan review gate:** process → self-approved; plan maps 1:1 onto spec sections, no new product decisions introduced.

## Subagent-driven development
- **Workspace:** skill wants isolated worktree; arm rules forbid worktrees outside repo. Decision: feature branch `feat/txmerge` inside the arm repo (no worktree), not main.
- Models: implementers haiku (plan has full code → cheapest tier per skill), task reviewers sonnet, final review opus.

## SDD ledger (copied before workspace deletion)
```
# SDD ledger — plan: docs/superpowers/plans/2026-11-02-txmerge.md
Spec: docs/superpowers/specs/2026-11-02-txmerge-design.md
Branch: feat/txmerge (from main @ ff of plan commit)

## Pre-flight scan
| Pair / task | Produces vs consumes | Finding |
|---|---|---|
| T1→T2 | Transaction(account,date,amount,description,source) | consistent |
| T1→T3 | Transaction fields date/account/source/amount | consistent |
| T1→T4 | InputError | consistent |
| T1→T5 | LedgerEntry(txn,category,transfer_id) | consistent |
| T2→T6 | dedupe(list)->list | consistent |
| T3→T6 | order(list)->list, pair_transfers(list)->list[str] | consistent |
| T4→T6 | load_rules(path), categorise(desc,rules), TRANSFER | consistent |
| T5→T6 | write_ledger(path, entries) | consistent |
| T1 self | tests vs code: warning reason substrings (neither/both/date/amount/fields) present in messages; blank-line source (0,3) via csv line_num | consistent |
| T2 self | survivors first-N in source order; expected (0,2),(1,2) | consistent |
| T3 self | tie/greedy tests vs strict `<` over inflows in output order | consistent; 10k-row test relies on amount index (present) |
| T4 self | empty pattern skipped; header stripped | consistent |
| T5 self | -0.00→0.00; HALF_UP 0.005→0.01 | consistent |
| T6 self | EXPECTED traced by hand; BAD ROW at cur2 line 5 | consistent |
| Rubric | no assert-nothing tests, no duplicated logic block | readers/categorise share similar OSError/UnicodeDecodeError handling (2 small except clauses) — not a verbatim logic block; no ruling needed |
Scan clean.

## Tasks
Task 1: implementer done 3617a16 (base 1753b7d), review pending
Task 1: minor (deferred): thousands separator stripped blindly — "12,50" parses as 1250 silently (plan-mandated; reviewer rated Minor)
Task 1: minor (deferred): zero debit yields Decimal("-0"); exponent input like 1e5 accepted
Task 1: minor (deferred): csv.Error not caught in read_export → traceback instead of exit 2
Task 1: minor (deferred): multi-line quoted field reports end line not start line
Task 1: minor (deferred): test gaps — non-UTF-8 file, Format B thousands/short row, zero amount, arg_index for A
Task 1: minor (deferred): no .gitignore (__pycache__, .pytest_cache untracked)
Task 1: complete (commits 1753b7d..3617a16, review clean)
Task 2: implementer done de0b97a (base 3617a16), review pending
Task 2: ⚠️ resolved — readers.py strips descriptions (verified by controller grep)
Task 2: minor (deferred): dedupe relies on reader trimming; no .strip() in dedupe
Task 2: minor (deferred): bare Counter/dict annotations
Task 2: minor (deferred): no test for empty input / duplicate source tuple
Task 2: complete (commits 3617a16..de0b97a, review clean)
Task 3: implementer done 2a29c7b (base de0b97a), review pending
Task 3: ⚠️ resolved — Transaction is @dataclass(frozen=True) → hashable (model.py)
Task 3: minor (deferred): same-amount inflow bucket scanned without date bound — O(k²) for many recurring equal amounts
Task 3: minor (deferred): test_id_widens_past_9999 doesn't assert performance
Task 3: minor (deferred): tests use dict(zip(rows, ids)) — fragile if two rows compare equal
Task 3: minor (deferred): .gitignore missing (dup of T1)
Task 3: complete (commits de0b97a..2a29c7b, review clean)
Task 4: implementer done 342df71 (base 2a29c7b), review pending
Task 4: ⚠️ resolved — InputError(Exception), not OSError subclass (model.py)
Task 4: minor (deferred): rule row with empty category accepted → empty category in ledger
Task 4: minor (deferred): csv.Error in rules file not mapped to InputError (same as T1 item)
Task 4: minor (deferred): no tests for non-UTF-8 / empty rules file / directory path
Task 4: complete (commits 2a29c7b..342df71, review clean)
Task 5: implementer done b00c6b7 (base 342df71), review pending
Task 5: minor (deferred): write_ledger writes in place (no temp+rename) — partial file possible if a write fails midway
Task 5: minor (deferred): tests missing negative half-up (-0.005), -0.004→0.00, non-ASCII, no-BOM check
Task 5: minor (deferred): quantize may raise InvalidOperation for >28-digit amounts (theoretical)
Task 5: complete (commits 342df71..b00c6b7, review clean)
Task 6: implementer done c739c0a (base b00c6b7), review pending
Task 6: minor (deferred): test_unwritable_out_exits_2 doesn't assert stderr message
Task 6: minor (deferred): OSError handler in main labels any OSError as "cannot write"
Task 6: minor (deferred): write_ledger truncates in place (dup of T5)
Task 6: complete (commits b00c6b7..c739c0a, review clean)
Final review (3ee3223..c739c0a, opus): With fixes — 1 Important (non-strict csv swallows rows on unterminated quote; csv.Error not mapped), 3 Minor (exponent/huge amounts + partial output file; .gitignore; empty-category rule)
Final: Ruling: fix all 4 final findings in ONE fix dispatch — Important is the stakeholder's worst failure; Minors are cheap and close deferred T1/T4/T5/T6 items — cost if wrong: slightly larger diff
Final: Ruling: empty-category rule rows are skipped like empty-pattern rows — a blank category is never useful in a ledger; falls through to next rule/Uncategorised — cost if wrong: user expecting blank category gets another
Final: Ruling: amounts must match [+-]?(digits[.digits]|.digits) after removing commas; exponent/other forms are bad rows (warn+skip) — brief says amounts are plain numbers — cost if wrong: an export using exponent notation loses rows with a warning
Final: declined-to-judge "0.00 in unused Debit/Credit column" — product question, sent to stakeholder (spawn 7)
Final: Ruling: Important #1 resolved per stakeholder Q7.2 (carry on, warn+skip) instead of reviewer's exit-2 suggestion — parse exports line-by-line with csv strict=True; a csv.Error line is a bad row (warn file:line, skip); header line error → InputError — cost if wrong: legit multi-line quoted descriptions (rare in bank exports) become warned bad rows
Final: Ruling: rules file csv.Error → InputError (exit 2) — rules are user-authored config, fail loud; stakeholder answer covered input exports only — cost if wrong: user must fix a rules typo before running
Final: Ruling: Format A zero in one column counts as blank (stakeholder Q7.1 "your call"); both zero → keep a 0.00 row — cost if wrong: a row the bank meant as malformed is kept
Final: fix wave done 2d3a41e (FIX_BASE f9325f5), re-review pending
Final: re-review — F1..F5 all ADDRESSED, no new Critical/Important
Final: parked — umask round-trip in writer is process-global — Ruling: single-threaded CLI, harmless — cost if wrong: none for CLI use
Final: parked — os.replace doesn't preserve existing out file perms/symlink — Ruling: output is a regenerated artifact; atomicity matters more — cost if wrong: a symlinked out path gets replaced by a regular file
Final: parked — CLI huge-amount test wouldn't catch leftover temp file — Ruling: writer test already asserts no temp left — cost if wrong: none
```

## Verification (verification-before-completion)
- `python3 -m pytest -q` → 88 passed (`python` is not on PATH in this environment; `python3` is 3.13.7).
- Independent CLI smoke run (overlap dedupe, transfer to card, broken-quote line, zero credit column, thousands separators): exit 0, one warning, expected ledger; re-run byte-identical (`cmp`); unknown header → exit 2, no output file.

## Departures from skill text
- Brainstorming: one stakeholder spawn batched 3 questions (Q6) and Q7 batched 2.
- SDD: no worktree (arm rules) — feature branch `feat/txmerge` instead.
- SDD final review Important #1: reviewer suggested exit 2; stakeholder (Q7.2) said warn+skip, so the ruling followed the stakeholder.
- Controller un-tracked the fix subagent's force-added workspace report (bookkeeping, not code).
- finishing-a-development-branch skipped per arm instructions; work left committed on `feat/txmerge`.
