# Comprehension Report (Stage 6)

**Target:** `docs/designs/txmerge.md` (FeatureRange 1-431, DetailedRange 432-634)
**Reviewer:** `egm-comprehension` (direct dispatch, per egm-review Stage 6). Status: completed.

**What this proposes**
`txmerge` is a standard-library Python CLI. It reads several bank CSV exports, each given as a `NAME=PATH` pair, plus a rules file, and writes one ledger CSV. Each file goes through a fixed in-memory pipeline: parse, deduplicate, sort, pair transfers, categorise, write. Within one account name, the same transaction is identified by the key (account, date, amount, normalised description). The ledger keeps each key as many times as its highest count in any single export, using the earliest occurrences and the first-ever description text. After sorting by (date, account, arg position, line), outflows are walked in order. Each one is greedily paired with an unpaired equal-and-opposite inflow in another account at most 3 days away, preferring the smallest gap and then the earliest position. Pairs get category `Transfer` and ids `T0001`, `T0002`, and so on. Every other row gets the first rule whose pattern is a case-insensitive substring of its description, or `Uncategorised`. File-level problems exit 2 before `--out` is touched. A bad row is skipped with a warning and the run exits 0. The output is byte-deterministic.

**How the existing system works, per this document**
There is no existing code; this is a new repository. The only fixed thing is the external contract in `BRIEF.md`: the command line, two input CSV formats (A for the current account, B for the credit card), a `pattern,category` rules file and a fixed six-column output header. The document leans on that contract by link and says it repeats it "where needed". The product rules come from stakeholder answers, and the document lists them as D1-D23 with S/E sources.

I could paraphrase every section. No section is a Blocker.

## Findings

1. **Major** — Overview 27-30; D5, D14, D15, D18; Row record; `FORMAT_A`/`FORMAT_B`; `HEADER`. The document never states the two input headers or the output header. Format B's `Details` column is never named; the Debit-negative / Credit-positive mapping appears only in a test bullet, not in the Decisions table; output column names and order are not given. CUJ 2's example row needs the Format A column order. Fix: add the three header strings and the Debit/Credit sign rule.
2. **Major** — Data flow 207-208 ("`--out` may name one of the inputs"); D23 ("next run rebuilds it from the unchanged inputs"); NFR Rollout ("never modifies its inputs"). Contradictory: if `--out` names an input, a run overwrites (or on failure deletes) that input. Pick one behaviour and make D23 and NFR agree.
3. **Major** — Risks & Limits, max-count bullet. The described "cut off mid-day" scenario does not fail (max keeps the larger count). The real loss case is two exports covering different parts of one day, each with one genuine same-key transaction: max is 1 and one real transaction is dropped. State the concrete example and its consequence.
4. **Nit** — Verification Plan coverage claim cannot be checked; missing tests for D23 delete-partial path, D20 overwrite of existing ledger, D16 case-sensitive headers.
5. **Nit** — `parse_account` calls `parser.error` but gets no parser; trimmed storage of NAME/PATH unstated; diagram `parse_args` has no matching function.
6. **Nit** — Diagram gives D8 to `categorise`, but `rules.categorise` takes only a description; no file owns D8.
7. **Nit** — Messages: `RULES` and `OUT` placeholders undefined; empty rules file message unstated; header-only rules file validity unstated.
8. **Nit** — Alternative I: Con ("harder to test") contradicts the Reason for Rejection ("readability, not testability").
9. **Nit** — "EGM" / "Elephant" undefined jargon in author line and footer.

**Verdict:** mostly self-contained; fix 1 and 2 before approval; reword 3.

---

# Re-audit (Stage 6, round 2)

**Target:** `docs/designs/txmerge.md` (FeatureRange 1-452, DetailedRange 453-673). Reviewer `egm-comprehension`: completed. No Blockers; every section paraphrasable.

**What this proposes** — A stdlib Python CLI merges two fixed CSV export formats into one ledger via one in-memory pipeline: parse (skip bad rows, exit 2 on bad files), dedup per account by max count per key, sort, greedy transfer pairing (equal-opposite, different account, <=3 days, ids T0001+), first-match substring rules else `Uncategorised`, write byte-identical ledger, summary on stderr. One module per concern, four phases with pytest tests.

**How the existing system works, per this document** — No existing code. Fixed parts are BRIEF.md and the stakeholder rulings, recorded as D1-D23 marked S or E. Each run rebuilds from the inputs.

## Findings
1. **Major** — The Problem says the ledger is written "atomically"; D23 says direct write, no temp file. Contradiction.
2. **Major** — Behaviour of an existing `--out` when the write fails is described five different ways (D13, line 217, D23, `write_ledger`, test). State plainly that the old ledger is lost and what remains.
3. **Major** — D20 same-file check runs "before reading anything" with `os.path.samefile`, which raises if a path is missing; behaviour for missing inputs with existing `--out` is undefined; `PATH` in the message ambiguous.
4. **Nit** — D16 "not counted" ambiguous (summary counts vs line numbers).
5. **Nit** — `T` is not a list-length difference; skipped rule rows in summary unstated.
6. **Nit** — Test monkeypatches `ledger.csv.writer` but item 6 never says `write_ledger` uses `csv.writer`.
7. **Nit** — Messages show path "as given" but `parse_account` trims.

## Resolution
1-3 cap reached for Stage 6 re-audits; all 3 Majors and all 4 Nits were still fixed: "atomically" replaced; D23 now states the existing-ledger case (truncated on open, deleted on failure) and line 217 limited to input-side checks; same-file check moved to after all inputs are read, only when `--out` exists, message `OUT: --out is also an input`; D16, counts, `csv.writer` and trimming clarified.
