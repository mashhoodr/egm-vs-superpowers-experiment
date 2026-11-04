# Blind design review: tsinvoice, design P vs design Q

Inputs read: `BRIEF.md`, `_judge/blind/design_P.md`, `_judge/blind/design_Q.md`. Nothing else.

## TL;DR

| Criterion | P | Q |
|---|---|---|
| 1. Completeness against the brief | **5** | 3 |
| 2. Unambiguity (byte-identical output) | **5** | 3 |
| 3. Implementability and test strategy | 4 | **5** |
| 4. Proportionality and readability | 2 | **4** |
| 5. Decision quality | **5** | 3 |
| **Total** | **21** | 18 |

- **P** is a complete, normative spec with no code. It pins every open behaviour, every message text and the stderr order. It is also about twice the size a ~500-line tool needs.
- **Q** is a short spec (~165 lines) plus a TDD plan that contains nearly the whole implementation. It is fast to build from, but its spec and its code disagree in three places, and the code crashes on one input class.
- **Hand to an engineer tomorrow: P**, after cutting about 30% of it. Q's code is a good starting point only if someone first fixes the contradictions listed below.

## Reading time (senior engineer, reading properly)

- **P:** 50–70 min. About 920 lines of dense normative prose, a 26-row Decisions Log, nine Alternatives and an implementation plan with no code. Every sentence carries a rule, so you can't skim it.
- **Q:** 10–15 min for the spec section. Another 30–40 min to check the plan's code and tests properly (~1,300 lines, mostly code). About 45–55 min in total, but the spec alone can be read in a coffee break.

---

## 1. Completeness against the brief

**P: 5.** Every behaviour the brief leaves open is pinned down:
- *Duplicates* (Stage 4): the key, a per-export max count, which copies survive (CUJ 3: "export 1's two copies and the first copy from export 2"), the same PATH under one NAME or two (Stage 1).
- *Joining* (Stage 5): group key, walk order, smallest gap then input order, claimed successors, chain termination argument. The worked example "Claimed successor" A/B/C makes the greedy rule concrete.
- *Rounding/pricing* (Stage 6): `ceil(m/6)*6` per session, `Decimal`, `ROUND_HALF_UP`, precision-50 context, never exponent notation, zero rate allowed, unrated = `0.00` + warning.
- *Ordering* (Stage 7, Stage 9): output sort key, session ID assignment order, and stderr order (bad rows → unrated → overlaps), printed only after the file is in place.
- *Errors* (Stage 3 reasons table, Fatal error messages table, Exit codes table): fixed texts for every bad-row reason and every exit-2 path.
- *Determinism* (G5, NFR): byte-identical output and stderr, with the one platform-dependent exception (OS reason text) named.
- It also covers less obvious cases: blank records before the header, unterminated quotes (R4.1), phone seconds, duration overflow, `--out` equal to an input, and double billing made visible by Stage 8's overlap warning.

**Q: 3.** The core rules are there (Deduplication, Joining, Pricing, Session id, Output). Several things are left open or covered only by the code:
- No stderr ordering rule. In the code it falls out of call order (rates warnings → bad rows → unrated warnings), but the spec never says so.
- Fatal message texts are not specified. "Fatal errors" lists causes only; the texts exist only in code (`cannot read tracker file …`, `error: …`).
- Unterminated or malformed quotes are not addressed. Blank lines *before* the header are fatal by accident: `rows[0]` is `[]`, which gives "unrecognised header". Whitespace-only or `,,,` lines become bad rows. None of this is stated.
- Same work timed in both apps, or edited entries, are double-billed silently. There is no overlap visibility, so the user gets no signal about the main way the "exact match only" rule bills time twice.
- Write safety is incomplete: "Written only after all inputs are read" is met, but the output is not atomic. A write failure can leave a truncated `--out`.

## 2. Unambiguity: would two engineers produce byte-identical output?

**P: 5.** Every user-visible byte is specified: output dialect (`csv.writer`, `lineterminator="\n"`, `QUOTE_MINIMAL`, UTF-8 no BOM), amount format, warning formats, error table, stderr order, session ID scheme (`S1, S2…` in output order). Parsing is pinned to exact regexes (`[0-9]+(\.0+)?` for durations, `^[0-9]+(\.[0-9]+)?$` for rates) rather than "is a number". Normalisation is defined exactly (NFC → trim → collapse → casefold → NFC). The "Precedence" note says the Stages win over the plan, so there's no doubt which text governs. The only residual variation is `str(exception)` in `cannot read`, and the design names it.

**Q: 3.** Where the code exists it settles questions, and an engineer who copies it gets one answer. The trouble is that the spec and code disagree, so an engineer who follows the spec gets different bytes:
- **Encoding fallback.** The Parsing section says a non-UTF-8 file is "re-read as Windows-1252" with a warning, via `tsinvoice/csvio.py`. Neither the fallback nor `csvio.py` appears in the module layout or the code: `read_tracker` and `load_rates` raise `FatalError` on `UnicodeDecodeError`. Same input: exit 0 under the spec, exit 2 under the code.
- **Date-only `start_iso`.** The spec makes it a bad row (`start_iso ... has no time`). The code calls `datetime.fromisoformat("2026-03-02")`, which returns midnight, and accepts it. No test covers it.
- **Absurd durations.** The spec says 10^10 minutes or more is a bad row. The code has no such check, and `start + timedelta(minutes=…)` raises an uncaught `OverflowError`: a traceback, exit 1, which matches neither exit code in the spec.
- "duration_minutes must parse as a number": the code uses `Decimal`, so `1e2` and `1E+2` are accepted as 100. That isn't stated.
- `hourly_rate` "a number": `Decimal` accepts `1e2` and `5E-1` too. Unstated.
- NAME is "exact string" in the Entry model, but `parse_tracker_arg` strips it (`name.strip()`).
- The unrated warning text in the spec is `'<client>'`. The code uses `{s.client!r}`, which switches to double quotes when the client contains an apostrophe.

## 3. Implementability and test strategy

**P: 4.** Clear build phases (P1–P5), each gated on `pytest`. It gives module responsibilities and public signatures, frozen dataclasses, conftest fixtures (`write_file`, `run_cli`, `run_module`), and a long enumerated test list per module. The Verification Plan asks for a test per Stage bullet and per table row, each citing what it covers. That traceability is good. Points off because there is no code: the engineer still has to write it all. Some of it is fiddly to get right, such as the sentinel-based unterminated-quote detection ("Reading any CSV file") and physical line numbers with bare `\r`. The full feature set will also likely push past ~500 lines.

**Q: 5.** It is close to copy-paste-able. Seven TDD tasks, each with failing tests, implementation, expected pytest output and a commit. I traced the tests and they are consistent with the code: the max-count dedupe ordering, the join tie-breaks (`test_smallest_gap_wins_then_input_order`, `test_earlier_session_gets_first_pick`), the half-up cases (`0.015 → 0.02`) and the end-to-end numbers (Acme 7+7 → 18 → 30.00; Beta 20 → 24 → 24.00). The "Review Focus" list ties five risky user expectations to named tests, which is useful. The caveat is that the tests don't catch the three contradictions above, so following the plan to green produces a tool that departs from its own spec.

## 4. Proportionality and readability

**P: 2.** Far too large for a ~500-line tool. Examples of over-specification:
- Unicode line separators (U+2028), `csv.field_size_limit` with a Windows overflow note, a sentinel string `__TSINVOICE_EOF__`, symlinked `--out`, temp-file mode `0o644`, an Alternatives section with nine entries (A–I), and a 26-row Decisions Log that largely repeats the inline **[D]** reasons.
- Process noise: "Status: Approved", provenance comment, "Drafted with [redacted]", R-number citations to a log the reader may not have.
- The prose itself is clear and well organised (Glossary, CUJs, numbered Stages, tables). It is just three to four times longer than the problem needs.

**Q: 4.** The spec section is the right size: one screen per rule set, decisions tagged **(ours)**. The plan is long, but most of it is working code and tests, which an engineer would write anyway. Process noise: the "For agentic workers: REQUIRED SUB-SKILL…" banner, checkbox steps, `git commit` per task, and a spec path under `docs/[redacted]/specs/` that points to itself.

## 5. Decision quality

**P: 5.** Trade-offs are stated with reasons, and several are sharp:
- **Truncate phone seconds** (Decisions Log, Alternative E): a phone entry 09:00:30 + 7 min followed by a desktop entry at 09:07 would otherwise be a 30 s overlap. That means no join, 24 billed minutes instead of 18, and a false warning. This protects brief goal 2 directly.
- **Bad rates rows are fatal** (Alternative G): under first-match-wins, skipping a specific rule lets a broader rule misprice silently. That reasoning is correct.
- **Stage 8 overlap warning**: keeps the owner's exact-match dedupe (no lost time) while showing double billing from edited entries or work timed in both apps. It also exempts exact repeats so the warning doesn't train the user to ignore it.
- Atomic write, `--out` equal to an input, and NFC so both apps' "é" match all have reasons given.
- Debatable: sequential `S1…` IDs shift when inputs change (Alternative F accepts this, citing R3.6). That's defensible but weaker than Q's choice.

**Q: 3.**
- **Good:** content-hash session IDs with a deterministic `-2, -3` collision suffix, stable when exports are added. That's better than P for invoices.
- **Weak:** "Seconds are kept **(ours)**" with no reasoning. Combined with the 0–120 s gap rule, a normal phone→desktop handoff with seconds fails to join and is billed as two rounded sessions. Q tests the opposite edge (`test_gap_measured_in_seconds`) but never the handoff. This undercuts brief goal 2.
- Windows-1252 fallback guesses at the encoding (and isn't implemented). Empty rates patterns warn-and-skip but bad rates are fatal, with no reasoning for the inconsistency. Strict exact case for headers is reasonable but unexplained.
- Most **(ours)** tags have no rationale. Q records decisions; P justifies them.

---

## Things one design specifies that the other leaves ambiguous or gets wrong

**P specifies, Q leaves ambiguous or wrong**
1. Phone seconds: P truncates to the minute, with a reason. Q keeps them, which breaks cross-app handoffs that carry seconds.
2. Date-only `start_iso`: P rejects it, and its tests do too. Q's spec rejects it but its code accepts it as midnight.
3. Huge duration: P makes it a bad row, `invalid duration_minutes`. Q's spec says bad row, but its code crashes with `OverflowError` (exit 1).
4. Non-UTF-8 input: P exits 2 with `cannot read`. Q's spec says fall back to cp1252 with a warning; its code exits 2.
5. Exact regexes for durations and rates. Q accepts any finite `Decimal`, including `1e2`.
6. Fixed stderr order, with warnings printed after the file is in place. Q's order comes from call sequence only.
7. Fixed error and warning texts in tables. Q's texts are in code only and partly diverge from its spec (`!r` quoting).
8. Atomic write via temp file + `os.replace`, with `--out` allowed to equal an input. Q can truncate `--out` on a write failure.
9. Blank records anywhere, including before the header, and `,,,` lines. In Q, a blank line before the header is fatal and `,,,` is a bad row; neither is stated.
10. Unterminated quoted fields (R4.1). Q is silent; the csv module's non-strict mode quietly swallows the rest of the file.
11. Overlap or double-billing warning (Stage 8). Q double-bills silently.
12. Unicode NFC before casefold. Q uses casefold only, so a composed and a decomposed "é" don't match.
13. Header matching is case-insensitive and ignores trailing blank cells. Q's is case-sensitive after strip, and a trailing comma breaks it.
14. Extra blank cells are allowed on data rows. In Q, a trailing comma makes a bad row.
15. Unrated warning includes the date, which tells apart repeated identical sessions.

**Q specifies, P leaves weaker or open**
1. Session IDs are a content hash, stable across added exports, with a defined collision suffix. P's `S1…` IDs change whenever inputs change.
2. Concrete code and tests for every module, so less is left to the implementer's reading.
3. "Review Focus" maps the risky user expectations to named tests.
4. Explicit midnight-crossing join test (`test_join_across_midnight_keeps_start_date`). P covers it by rule (R1.7) but has no worked example.

## Verdict

**Hand P to an engineer tomorrow.** Its Stages 1–9 and the three tables are a spec two engineers could implement independently and diff byte for byte, and its decisions (truncating seconds, fatal rates rows, the overlap warning) protect the brief's goals: "never lose real time", "join continuations", "same output". Before handing it over, cut the U+2028 / field-size / symlink / `0o644` material, fold the Decisions Log into the inline **[D]** notes, and drop Alternatives B, C and H. That gets it to roughly 550–600 lines.

Q is the faster path to green tests and has the better session-ID idea. But its spec and code disagree in three places (cp1252, date-only start, duration overflow), one of which is a crash. Its kept-seconds rule also quietly breaks the handoff case the brief cares most about. An engineer working from Q would ship those defects with all tests passing.
