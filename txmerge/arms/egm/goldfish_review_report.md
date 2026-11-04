# Goldfish Annotated Review Report
Status: resolved

**Target:** `docs/designs/txmerge.md` (FeatureRange 1-296 at round start) — Stage 7, round 1
Reviewers: egm-design (completed), egm-structural (completed), egm-style (completed). Raw summaries: `reviews/stage7/r1_*.md`.

## Prioritized Findings & AI Suggestions (High = Blocker/Major)

| ID | Reviewer | Sev | Finding | Suggestion | Outcome |
| --- | --- | --- | --- | --- | --- |
| design-1-1 | design | High | No Risks & Mitigations; security (formula injection) and surviving-duplicate failure mode missing | PROPOSE FIX | Added `## Risks and Mitigations`; formula escaping asked of stakeholder (round 4: write as given) → D17 |
| structural-1-2 | structural | High | Same as design-1-1 (Risks section required by standard; temp collisions; --out = input) | PROPOSE FIX | Merged with design-1-1, design-1-2, design-1-3 |
| design-1-2 | design | High | `--out` can equal an input/rules file | PROPOSE FIX | Refuse with exit 2 (Stage 8, errors table, D18, `check_not_input`, test) |
| design-1-3 | design | High | Output-safety claim overstated (cleanup, fsync, fixed temp name, symlink) | PROPOSE FIX | mkstemp unique temp, fsync, chmod, realpath, cleanup on failure; claim scoped |
| style-1-1 | style | High | "never"/"any failure" absolute claims | PROPOSE FIX | Reworded (Stage 8, D15, G5) |
| design-1-4 | design | High | Linear transfer scan unbacked | PROPOSE FIX | Amount index restored (see churn note) |
| style-1-2 | style | High | Unmeasured performance claim | PROPOSE FIX | NFR reworded: growth with record count, no target time |
| style-1-3 | style | High | D9 reason contradicts stakeholder (header-only rules valid) | PROPOSE FIX | D9 rewritten, Stage 3 states header-only valid |
| style-1-4 | style | High | CUJ 1 "once (repeated purchases kept)" | PROPOSE FIX | Reworded to G1's max-count wording |
| structural-1-1 | structural | High | Decision Log/Limitations/Future nested under NFR | PROPOSE FIX | Promoted to H2; Known Limitations folded into Risks |
| design N5-N16, style N1-N14, structural N3-N9 | — | Low | Nits | PROPOSE FIX (most) / DECLINE | Applied: ASCII digits, InvalidOperation, first-`=` split, repeated --rules/--out, preamble limitation, REASON texts, Transfer/Uncategorised categories, U definition, Alt H/I reasons, Alt E split, Alt L (architecture), Stage 1/5 subsections, rules/terms wording, legend, D5 separators, D11/D14 wording. Declined: N4/author jargon (template), design N13 (rules checked after inputs; order is documented), design N14 (case-variant account warning; YAGNI), structural N9 (heading names; standard list non-exhaustive). |

## Churn note
design-1-4 asks for the amount index that Stage 5 zoom-out nit 3 asked to remove. Reverting the Stage 5 fix resolves it, which is churn under egm-review-loop 2.4. Resolved in favour of the index (two Major findings outweigh one Nit), with the reason stated in Stage 6.

## Counts
Accepted fixes: 10 High (8 distinct after merging), ~30 Nits. Contested: 0. Escalated: 1 (formula escaping → stakeholder). Declined: 5 Nits.

---

# Goldfish Annotated Review Report — Stage 7, round 2
Status: resolved

**Target:** `docs/designs/txmerge.md` (FeatureRange 1-329 at round start). Reviewers: egm-design (completed), egm-structural (completed), egm-style (completed). Raw summaries: `reviews/stage7/r2_*.md`. Round not clean (4 Major).

| ID | Reviewer | Sev | Finding | Suggestion | Outcome |
| --- | --- | --- | --- | --- | --- |
| design-2-1 | design | High | Symlink sentence contradicts `os.replace` mechanism | PROPOSE FIX | Option (a): resolve with realpath; temp in target dir; checks on target; dangling link creates target; D21 |
| style-2-1 | style | High | Perf claims unmeasurable/inconsistent, repeated | PROPOSE FIX | Single honest cost statement in NFR (quadratic per same-amount bucket); size envelope; cross-refs |
| style-2-2 | style | High | "Exact matching never merges two different transactions" false (boundary-day) | PROPOSE FIX | Narrowed; boundary-day max-count case added as accepted risk |
| style-2-3 | style | High | Row definition conflicts; row/record mixed | PROPOSE FIX | Row = csv.reader record (may span lines); record used for in-memory unit |
| Nits (design 2-7, structural 1-7, style 4-10) | — | Low | | PROPOSE FIX / DECLINE | Applied: trimming decision D20, empty description + `.50`/`1250.` D22, trailing-comma risk, directory-fsync caveat, size envelope, G1 link, L21 wording, Alt E1 cons, D12/D13/D17 reasons, Stage capitalisation, determinism wording, Stage 1 link, argparse message cell. Declined: re-lettering alternatives (E1/E2 clear), moving Open Questions (template order), bisect window (design N2: cost is documented instead), Future Improvements duplication (template section). |

Counts: accepted 4 High + 15 Nits; contested 0; escalated 0; declined 4 Nits.

---

# Goldfish Annotated Review Report — Stage 7, round 3
Status: resolved

Reviewers: egm-design (completed), egm-structural (completed), egm-style (completed). Raw: `reviews/stage7/r3_*.md`. Round not clean (3 Major).

| ID | Reviewer | Sev | Finding | Suggestion | Outcome |
| --- | --- | --- | --- | --- | --- |
| design-3-1 | design | High | Non-strict csv silently swallows rows after an unclosed quote | PROPOSE FIX (verified in scratchpad) | Option (a): `strict=True`; whole file exit 2; D24; errors table; test |
| style-3-1 | style | High | G1 heading "no lost rows" absolute | PROPOSE FIX | Renamed "Duplicates from overlapping exports removed by max count" |
| style-3-2 | style | High | Risk row wording says the opposite | PROPOSE FIX | "Rules match inner whitespace exactly" |
| Nits | — | Low | | PROPOSE FIX / DECLINE | Applied: encoding/csv error decision (D24), G4 Python version, same-file-two-names risk row, Empty description bullet moved, "touches", sort sentence, comma splice, dangling-link wording, mkstemp prefix/suffix, umask wording, paragraph split, Alt F cons, Alt L wording, memory estimate, Risks label consistency, D3/D6/D12/D19/D20 reasons, D22 split (D23). Declined: bisect window (cost documented; avoids a third change to Stage 6), E1/E2 re-lettering, metadata colon style, diagram label alignment, Open Questions placement, "one entry" repetition, author jargon, CUJ 1 bullets. |

Counts: accepted 3 High + 22 Nits; contested 0; escalated 0; declined 8 Nits.

---

# Goldfish Annotated Review Report — Stage 7, round 4
Status: resolved

Reviewers: egm-design (completed, 0 Major), egm-structural (completed, 0 Major), egm-style (completed, 1 Major). Raw: `reviews/stage7/r4_*.md`. Round not clean (1 Major).

| ID | Reviewer | Sev | Finding | Suggestion | Outcome |
| --- | --- | --- | --- | --- | --- |
| style-4-1 | style | High | row/record still mixed (re-opened style-2-3: earlier fix incomplete) | PROPOSE FIX | Diagram, summary U, Risks rows now say "record" |
| Nits | — | Low | | PROPOSE FIX / DECLINE | Applied: check order for malformed rows, `--help` stdout exception, macOS fsync caveat, risks for same-amount buckets / `0.00` unused cells / single non-UTF-8 byte, Conversion label, D25 (first-`=`, repeated flags, PATH as typed), L11 superset wording, Problem wording, "max count", G4 cross-ref, size basis, D5/D13 reasons, formula-risk wording, umask/Alt D wording. Declined (settled earlier): bisect window, E1/E2 labels, "one entry" repetition, NFR placement. |

Counts: accepted 1 High + 19 Nits; contested 0; escalated 0; declined 4 Nits.

---

# Goldfish Annotated Review Report — Stage 7, round 5 (cap)
Status: resolved

Reviewers: egm-design (completed, 0 Major), egm-structural (completed, 0 Major), egm-style (completed, 3 Major). Raw: `reviews/stage7/r5_*.md`. Round not clean (3 Major). **Cap of 5 rounds reached.**

| ID | Reviewer | Sev | Finding | Suggestion | Outcome |
| --- | --- | --- | --- | --- | --- |
| style-5-1 | style | High | Row defined using the word "record"; L49 "where the record starts" | PROPOSE FIX | Row is its own definition; L49 says "row" |
| style-5-2 | style | High | G5 "bad" undefined | PROPOSE FIX | G5 now names malformed data rows, invalid rule rows, and links the errors table |
| style-5-3 | style | High | Crash terms mixed; "always" too broad | PROPOSE FIX | Two named cases (process termination / OS crash or power loss); "not guaranteed" |
| Nits | — | Low | | PROPOSE FIX / DECLINE | Applied: field rules reordered to match check order, rules-row precedence, full message strings, diagram Stage 2 label, Stage 2 opening split, CUJ 3/4 headings, Stage 6 descriptive voice, stdout sentence, D13 help exception, Alt L reason, formula-risk clause, D5 reason, account NAME typo risk, unquoted separator risk, read-only `--out` refusal + hard-link/metadata note (D27), `casefold` decision (D26), line breaks in descriptions + test. Declined (settled): E1/E2, "one entry" repetition, Risks grouping by type, link style for D-ids, G4 repetition in The Problem. |

Counts: accepted 3 High + 19 Nits; contested 0; escalated 0; declined 5 Nits.

## Cap decision (egm-review-loop 2.4)
Open findings by severity after round-5 fixes: Blocker 0, Major 0 known (all raised Majors fixed, not re-verified by a fresh round), Nit: the declined items above. Gate (accept and proceed / continue past cap / return to drafting): **accept and proceed to Stage 8**. Stage 8 is a fresh zoom-out over the whole file and acts as a check on the round-5 edits.

---

# Goldfish Annotated Review Report — Stage 9, round 1
Status: resolved

**Target:** `docs/designs/txmerge.md` DetailedRange 347-479. Reviewers: egm-implementation-readiness (completed), egm-codebase-details (completed), egm-style (completed). Raw: `reviews/stage9/r1_*.md`. Round not clean (15 Major across reviewers, many overlapping).

| ID | Reviewer(s) | Sev | Finding | Suggestion | Outcome |
| --- | --- | --- | --- | --- | --- |
| ir-1-1 / cd-1-1 | readiness, codebase | High | No phases/checkpoints | PROPOSE FIX | `### Phases` (6 phases, pytest green per phase) |
| ir-1-2 / cd-1-2 / style-1-5 | all | High | Coverage claim vs tests (D4, D5, D6, D8, D13, D15, D19, D20, D25, D26, symlink, blank-only input) | PROPOSE FIX | Tests added and tagged with decision IDs; D15 tested via monkeypatched `os.replace` |
| ir-1-3 | readiness | High | Summary/warning assertions loose | PROPOSE FIX | Exact summary line with counts (M excludes rule warnings) and exact CUJ 3 warning |
| ir-1-4 / cd-1-5 | readiness, codebase | High | Embedded lone `\r` quoting | PROPOSE FIX (verified on 3.13: quoted) | Tests for `\n` and lone `\r` |
| cd-1-3 | codebase | High | REASON undefined; temp path leaks | PROPOSE FIX | `os_reason(e)` helper; per-type REASON rules |
| cd-1-4 / style-1-2 | codebase, style | High | Date regex `\d` vs `[0-9]` | PROPOSE FIX | `[0-9]` + `re.fullmatch`, one pattern per function; non-ASCII date test |
| style-1-1 | style | High | Empty-header message double prefix | PROPOSE FIX | Exact `TxmergeError` strings, `EXPECTED` constant |
| style-1-3 | style | High | "key" names two tuples; input-position order undefined | PROPOSE FIX | `count[(e, k)]`, `limit[k]`, `kept[k]`; terms defined at top of plan |
| style-1-4 | style | High | Fixture text vs bytes | PROPOSE FIX | `write` accepts `str` or `bytes` |
| style-1-6 | style | High | outflow/inflow undefined; walk order | PROPOSE FIX | Defined; "walks positions in output order"; "considers candidates" |
| Nits | all | Low | | PROPOSE FIX | Applied: negative-zero reason corrected (verified `-Decimal("0.00")` is positive), cleanup only after successful open, samefile OSError, M via `read_export` skipped count, header-line return removed, `allow_abbrev=False`, `version` + `pythonpath`, exact unclosed-quote input, decode-position wording, heading "Create", `__init__` claim dropped, `parse_a` names `parse_date_dmy`, `{n}/{m}` explicit, `format_amount` wording, write steps numbered, main steps numbered, test lists as bullets, CUJ link, Build label. Declined: footer `*Drafted with EGM*` (template provenance). |

Counts: accepted 10 High (15 raw) + ~30 Nits; contested 0; escalated 0; declined 1 Nit.

---

# Goldfish Annotated Review Report — Stage 9, round 2
Status: resolved

Reviewers: egm-implementation-readiness (completed), egm-codebase-details (completed), egm-style (completed). Raw: `reviews/stage9/r2_*.md`. Round not clean (5 Major raw, 3 distinct).

| ID | Reviewer(s) | Sev | Finding | Suggestion | Outcome |
| --- | --- | --- | --- | --- | --- |
| style-2-1 / ir-2-2 / cd-2-1 | all | High | Lone `\r` quoting verified only on 3.13 | PROPOSE FIX | Verified by the Elephant on CPython 3.11.14 (uv-managed) and 3.13.7; note updated; Verification Plan runs pytest on 3.11 and newest |
| ir-2-1 | readiness | High | conftest importing `txmerge.cli` at module level breaks Phases 2–5 | PROPOSE FIX | conftest imports nothing from `txmerge` at top level; `run` imports inside the fixture |
| cd-2-2 | codebase | High | "Repository root" ambiguous | PROPOSE FIX (reviewer assumed the outer git root; the arm is its own git repo) | Root defined as the directory containing `BRIEF.md`; subprocess `cwd` from `__file__` |
| Nits | all | Low | | PROPOSE FIX / DECLINE | Applied: M/records init, U as count, test-per-bullet wording, rejected-date formats, zero-guard removed, `os_reason` claim narrowed, governing-rule sentence, D16/D21 exemption, argparse error assertion, `detect` None-first, removal error ignored, samefile message accepted, pytest>=7.0, `read_ledger` fixture, parent dirs + chdir, Stage 8 citation for symlink test, `[D1]`/`[D11]` tags, help strings, `import sys`, field-size limit kept, Phase 1 check. Declined: footer. |

Counts: accepted 3 High + 22 Nits; contested 0; escalated 0; declined 1 Nit.

---

# Goldfish Annotated Review Report — Stage 9, round 3
Status: resolved

Reviewers: egm-implementation-readiness (completed), egm-codebase-details (completed), egm-style (completed). Raw: `reviews/stage9/r3_*.md`. Round not clean (4 Major raw, 3 distinct). Codebase-details checked the coverage claim and found it holds.

| ID | Reviewer(s) | Sev | Finding | Suggestion | Outcome |
| --- | --- | --- | --- | --- | --- |
| ir-3-1 / cd-3-1 | readiness, codebase | High | `cli.main` rebinds `records` per export, losing all but the last | PROPOSE FIX | `batch, skipped = ...; records.extend(batch); M += skipped` |
| style-3-1 | style | High | Symlink test cites "Stage 8" not a decision | PROPOSE FIX (Stage 8 is a Technical Plan section the reviewer did not read) | D21 made a live decision; test tagged `[D21]` |
| style-3-2 | style | High | "Newest Python available" not checkable | PROPOSE FIX | "Python 3.11 and Python 3.13" |
| Nits | all | Low | | PROPOSE FIX | Applied: explicit `next(reader)` loop, parse return order + `Record` construction, `with f:`, `run` fixture 3-tuple, exact header-error strings, `parse_amount` called directly for amount cases, `warn` defined in `main`, `--out` = rules test, `warn` annotation, Posting Date and `--help` tests, "rare" wording, author note removed, 50 inflows, Phase 6 wording, exit-2 assertions split, L351 shortened. Declined: how pytest is installed (environment, not repository; `pytest>=7.0` is declared). |

Counts: accepted 3 High + 17 Nits; contested 0; escalated 0; declined 1 Nit.

---

# Goldfish Annotated Review Report — Stage 9, round 4
Status: resolved

Reviewers: egm-implementation-readiness (completed), egm-codebase-details (completed), egm-style (completed). Raw: `reviews/stage9/r4_*.md`. Round not clean (4 Major raw, 3 distinct).

| ID | Reviewer(s) | Sev | Finding | Suggestion | Outcome |
| --- | --- | --- | --- | --- | --- |
| ir-4-1 / cd-4-1 | readiness, codebase | High | Lone `\r` quoting on 3.11 not settled in the doc | PROPOSE FIX — **churn**: round 3 removed the verification note at style's request; reverting that removal resolves it | Note restored as an engineering fact ("verified on 3.11.14 and 3.13.7; no extra code needed") |
| cd-4-2 | codebase | High | Multi-line test cannot catch the `for`-loop start-line bug | PROPOSE FIX | The multi-line row itself is malformed; exact `PATH:3:` warning asserted |
| style-4-1 | style | High | `run` fixture normal-return exit code unstated | PROPOSE FIX | Both paths stated |
| Nits | all | Low | | PROPOSE FIX / DECLINE | Applied: brute-force fixture fully specified, subprocess inputs and exact summary, `reader` binding, `categorise` types, counters before `try`, capsys/conftest reasons, `format_amount` precondition, exception examples, "it" wording, tie-break tuple as code, field-count case named, CR/LF named, "pair" wording, `[D25]` scope. Declined: precedence hedge and definition repetition (deliberate cross-reference), CUJ 1 bullet split, arrow-vs-verb uniformity, footer. |

Counts: accepted 3 High + 15 Nits; contested 0; escalated 0; declined 5 Nits.

---

# Goldfish Annotated Review Report — Stage 9, round 5 (cap)
Status: resolved

Reviewers: egm-implementation-readiness (completed, verdict Ready), egm-codebase-details (completed, verdict Ready), egm-style (completed). Raw: `reviews/stage9/r5_*.md`. **Clean round** (0 Blocker, 0 Major; 16 Nits). Cap of 5 reached with one clean round (convergence needs two).

Applied Nits: `run` fixture returns a callable, per-case `--out` state for exit-2 tests, CUJ 1 expected string worked out by hand, pytest install and interpreters, trailing newline in summary comparison, `read_ledger` encoding, symlink test target, "malformed row" / "input-position order" terms, "same duplicate key" wording, precedence sentence. Declined: verification note in the `\r` test (settled in round 4: churn), nested "so" wording, caveat sentence split, rule-row naming across the spec (FeatureRange closed).

## Stage 9 terminal gate
Open findings by severity: Blocker 0, Major 0, Nit 4 declined. Gate: **Conclude review and finalize document.** Status set to Approved.
