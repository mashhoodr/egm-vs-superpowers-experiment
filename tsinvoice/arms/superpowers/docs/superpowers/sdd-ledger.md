# SDD ledger — plan: docs/superpowers/plans/2026-11-03-tsinvoice.md

Spec: docs/superpowers/specs/2026-11-03-tsinvoice-design.md (reachable)
Workspace: branch feat/tsinvoice in arms/superpowers (no separate worktree — arm rules forbid worktrees outside the repo; a branch gives the isolation).

## Pre-flight scan
| Pair / task | Produces vs consumes | Finding |
|---|---|---|
| T1→T2 | Entry(tracker,arg_index,line,client,description,start,end,minutes), FatalError | T2 constructs Entry positionally in field order — matches |
| T1→T3 | Entry.order, norm | matches |
| T1→T4 | Session(entries), norm; Session.minutes ceil-6 | matches; T4 tests rely on Session.minutes |
| T1→T5 | norm, FatalError | matches |
| T1→T6 | Session.first/client/start/date/minutes/session_id | matches |
| T2/T3/T4/T5/T6→T7 | read_tracker(path,tracker,arg_index,warn), dedupe, join, load_rates(path,warn), find_rate, price(minutes, Decimal), assign_ids, sort_sessions, session_row, render_csv | all signatures match; T7 passes Decimal(0) for no-rate |
| T1 self | tests vs model code | consistent (Session doesn't trim; test asserts untrimmed) |
| T2 self | tests vs code | consistent; empty-client check runs after field parse — test row has valid dates |
| T3 self | tests vs code | consistent (max-count walk verified by hand) |
| T4 self | tests vs code | consistent; chain test hour formatted :02d |
| T5 self | tests vs code | consistent; 0.015 → 0.02 half-up |
| T6 self | tests vs code | consistent |
| T7 self | e2e expectations vs pipeline | hand-computed: Acme 7+7=14→18 @100=30.00; Beta dedup 30 @60=30.00; Beta 20→24=24.00; Gamma 10→12 no rate 0.00; p.csv:4 warned |
| Global constraints | | no conflicts |
Scan clean; no rulings needed.

## Progress
Task 1: implemented 6bae0a6..93b51a1 (DONE_WITH_CONCERNS: no .gitignore for __pycache__; trailer named Haiku)
Ruling: add .gitignore (__pycache__/, .pytest_cache/) as part of Task 2's dispatch — generated caches should never be committed; costs nothing if wrong.
Task 1: minor (deferred): no .gitignore (handled by ruling → Task 2)
Task 1: minor (deferred): Session.first IndexError on empty entries (never constructed empty)
Task 1: minor (deferred): order test checks one tuple only
Task 1: minor (deferred): norm NBSP handling untested
Task 1: complete (commits 6bae0a6..93b51a1, review clean)
Task 2: implemented 93b51a1..ba45a72 (DONE_WITH_CONCERNS: added OverflowError guard for huge durations beyond brief)
Task 2: minor (deferred): int(Decimal('1E+999999999')) may hang before OverflowError guard — cap durations
Task 2: minor (deferred): csv.Error/UnicodeDecodeError anywhere makes whole file fatal
Task 2: minor (deferred): line_num is end line for multi-line quoted records
Task 2: minor (deferred): no tests for quoted comma, whitespace-only row, format B empty client
Task 2: complete (commits 93b51a1..ba45a72, review clean)
Task 3: implemented ba45a72..968b822 (DONE)
Task 3: minor (deferred): untyped dict annotations / _key no return annotation
Task 3: minor (deferred): docstring doesn't say function sorts internally
Task 3: minor (deferred): no test with 3+ files or mixed keys
Task 3: complete (commits ba45a72..968b822, review clean)
Task 4: implemented 968b822..5b15814 (DONE)
Task 4: minor (deferred): entries in a (currently impossible) cycle would vanish silently — no conservation guard
Task 4: minor (deferred): quadratic candidate scan per key (plan-mandated)
Task 4: minor (deferred): loose typing on _join_key / by_key
Task 4: minor (deferred): no test of returned session order with unsorted input
Task 4: complete (commits 968b822..5b15814, review clean)
Task 5: implemented 5b15814..448e268 (DONE)
Task 5: minor (deferred): Decimal accepts 1_000, +5, -0; rate -0 would print -0.00
Task 5: minor (deferred): no test for too-many-fields rates row
Task 5: minor (deferred): blank/BOM-only rates file reports header error (acceptable)
Task 5: complete (commits 5b15814..448e268, review clean)
Task 6: implemented 448e268..c62ba52 (DONE)
Task 6: minor (deferred): sort test never exercises line tiebreak
Task 6: minor (deferred): test named test_write_csv_* tests render_csv (plan-given name, Review Focus reference)
Task 6: minor (deferred): no -3 collision test
Task 6: minor (deferred): session_row formats unquantised Decimal without rounding control (caller quantises)
Task 6: minor (deferred): '|' separator not escaped in id hash input
Task 6: complete (commits 448e268..c62ba52, review clean)
Task 7: implemented c62ba52..d4f9952 (DONE)
Task 7: ⚠️ resolved by controller: parse.py catches OSError/UnicodeDecodeError/csv.Error → FatalError (verified in Task 2 review)
Task 7: minor (deferred): open(out,'w') truncates before write; write failure would clobber existing file (plan-mandated) — temp+os.replace would fix
Task 7: minor (deferred): unused tmp_path arg in run(); f-string without placeholder
Task 7: minor (deferred): bad-arg loop not parametrized
Task 7: minor (deferred): whitespace-only PATH accepted (still exits 2 later)
Task 7: complete (commits c62ba52..d4f9952, review clean)
Final review: 1 Critical (huge duration hang), 1 Important (non-UTF-8 fatal), 5 Minor (-0 rate, truncate-before-write, !r quoting, spec overclaim on id stability, date-only start_iso). Promoted deferred minors: T2 duration cap, T7 truncate, T5 -0.
Ruling: encoding falls back to cp1252 with a warning — stakeholder left it to us; real Windows exports should not kill the run — if wrong, a mis-decoded file yields odd characters but warned.
Ruling: date-only start_iso is a bad row — brief says ISO 8601 datetime — if wrong, such rows are skipped (warned), not silently mis-timed.
Ruling: fix all 7 final findings in one fix wave (thorough option) — costs a slightly larger fix diff.
Final fix wave: d4f9952..ed61f5a — re-review: 7/7 addressed, no new Critical/Important.
Final: parked — output file mode becomes 0600 via NamedTemporaryFile — Ruling: real, deferred; no second fix wave allowed by the skill; cost if wrong: other local users can't read the CSV until chmod.
Final: parked — absurd hourly_rate like 1E+999999999 raises decimal.Overflow traceback at load (not exit 2) — Ruling: real, deferred, pathological input; cost if wrong: traceback instead of a clean error message.
