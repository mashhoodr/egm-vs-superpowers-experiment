# Blind design review 2: design_P vs design_Q (`txmerge`)

Files read: `BRIEF.md`, `_judge/blind2/design_P.md`, `_judge/blind2/design_Q.md`. Nothing else.

## TL;DR

- **P is the better design.** It specifies more, contradicts itself almost nowhere, and two engineers could build byte-identical output from it. It is heavy, though: 24 decisions plus risk and alternatives tables for a ~500-line tool.
- **Q is the faster route to running code.** It has a short spec, then the whole implementation and tests, task by task. But in at least six places the code does not do what Q's own spec says. One example: the spec promises an atomic write and the code writes the file directly.
- **Hand P to an engineer tomorrow.** Q's end-to-end fixture (`EXPECTED` in Task 6) is worth adding to P's test plan.

## Scores (1–5)

| Criterion | P | Q |
|---|---|---|
| 1. Completeness against the brief | **5** | 3 |
| 2. Unambiguity (byte-identical builds) | **5** | 3 |
| 3. Implementability + test strategy | 4 | 4 |
| 4. Proportionality / readability | 3 | **4** |
| 5. Decision quality | **4** | 3 |
| **Total** | **21** | 17 |

## 1. Completeness

**P: 5.** The Decisions table (D1–D24) settles every behaviour the brief leaves open:
- **Duplicates.** D1 defines the key and normalisation. D2 uses the max-not-sum count rule. D3 says which copies survive and which description text they keep. D4 says the same PATH twice is two exports and two NAMEs never merge.
- **Transfers.** D6 sets the inclusive 3-day window and lets the inflow come first. D7 gives the greedy pairing with its tie-break. D8 and D9 cover ids, including what happens past 9999. D17 says zero amounts never pair.
- **Rules.** D10 is a case-folded substring match on the kept text, with inner whitespace *not* collapsed. D11 covers header and bad-row handling.
- **Ordering.** D12 gives a total order.
- **Errors.** D13 covers file-level errors and D14 row-level errors, with a fixed check order that decides the REASON. D15 is the amount grammar, including the unquoted-`1,250.00` case. D16 covers BOM, trimming and blank lines.
- **Determinism and I/O.** D21 pins encoding and quoting. D23 specifies the atomic write. D20 stops `--out` from being an input. D22 says stdout stays empty.

The Messages-and-exit-codes table gives every stderr string exactly, plus a summary line whose counts are defined.

**Q: 3.** The brief's four goals are covered in "Behaviour" (Parsing, Duplicate removal, Output order, Transfer pairing, Categorisation, Writing). These are left open or not addressed:
- `--out` naming an input or the rules file.
- Message wording is not pinned in the spec (only the code has it), and there is no summary line.
- Rule rows with extra cells.
- Whether to trim the `--account` PATH.
- Rows of one file given under two NAMEs pairing with each other.
- 3+ decimal amounts.
- The order of row checks.

## 2. Unambiguity

**P: 5.** Implementation details are pinned down:
- `read_csv`, `parse_amount` (grammar check before `Decimal()`, then `quantize`) and `format_amount` (zero becomes `"0.00"`).
- The exact `mkstemp` / `copymode` / `os.replace` / `finally` steps in `write_ledger`.
- The argparse setup.

Where wording might differ, the Messages section says it wins. Remaining ambiguity is minor:
- Whether the "unrecognised header" message shows trimmed or raw cells.
- `<OS error>` text, which comes from `str(exc)` and so depends on the platform.
- D15 gives the amount grammar in prose, not as a regex.

**Q: 3.** The spec and the code disagree. An engineer following the spec and one copying the code will produce different output (see the contradiction list below). Where code exists, it removes ambiguity; where it contradicts the spec, it adds ambiguity back.

## 3. Implementability

**P: 4.**
- The Detailed Implementation Plan has four phases, a file for each concern, public signatures, and a numbered `cli.main` flow.
- The Verification Plan maps every D-rule to a test file.
- Each test file has a concrete list of cases, including exact-bytes and failing-write tests.
- What's missing: no test code and no fixed end-to-end expected output, so the engineer still writes all of it.

**Q: 4.**
- Tasks 1–6 contain complete module code and pytest code in red/green/commit steps. The `EXPECTED` ledger in Task 6 is correct; I traced it by hand.
- It is held back from 5 because copying the code faithfully ships a tool that breaks its own spec and crashes on some inputs:
  - `csv.Error` is never caught.
  - `InvalidOperation` from `quantize` on a 40-digit amount is never caught.

## 4. Proportionality / readability

**P: 3.**
- About 785 lines of dense prose for a ~500-line tool.
- Process padding:
  - The Author/Status: Approved header.
  - Alternatives G and H are one-line restatements of decisions already made.
  - Non-Functional "Rollout & Rollback".
  - CUJs that repeat the Decisions table.
- Some edge cases are more than a personal tool needs: `samefile` raising `OSError`, the csv field-size limit, a 40-digit amount, 0600 file modes.
- It is well organised (decisions → algorithms → plan) and cross-referenced by D-number, but heavy going.

**Q: 4.**
- The spec is about 95 lines and easy to scan. The rest is the code itself, which has to be written anyway.
- "Review Focus" is a useful short list of edge cases, each tied to the test that owns it.
- Noise:
  - The agentic-worker banner ("REQUIRED SUB-SKILL").
  - Checkboxes and per-task `git commit` steps.
  - A `docs/[redacted]/specs/...` path the reader may not have.
  - The Global Constraints section repeats the contract a second time.

## 5. Decision quality

**P: 4.**
- Every decision is tagged (S) stakeholder or (E) engineer, so it's clear where each one came from.
- The reasoning that matters is written down:
  - Alternative A: why max-count, rather than summing counts or keeping one row per key.
  - Alternative J: why the atomic write.
  - Alternative H: why `Decimal` rather than `float`.
  - R4: the max-count rule can drop a real transaction that sits on a cut-off boundary. The design states this and explains why no rule on these files could avoid it.
  - R5: the unquoted-thousands trap.
- Weak spots: several alternatives say only "stakeholder decided" (D, E, G). New ledgers getting mode 0600 is a side effect a user may not expect.

**Q: 3.**
- "Approaches considered" weighs pipeline vs streaming vs sqlite, sensibly but in one line each.
- Engineer choices are marked *(our choice)* but mostly not explained.
- Some choices make little sense:
  - The spec has both-zero Format A rows kept as `0.00` while saying zero counts as blank.
  - Reporting a malformed rules CSV as an "argparse-style usage error".

## Where Q contradicts itself or is wrong, and P is not

| Topic | P | Q spec | Q code |
|---|---|---|---|
| Atomic write | D23: temp file, then `os.replace`, then cleanup | "temp file beside the target and `os.replace`d" | `writer.write_ledger` opens `path` with `"w"` directly, so a failure leaves a partial file |
| Exponent / `NaN` / underscore amounts | D15 grammar rejects them before `Decimal()` | regex `[+-]?(\d+(\.\d*)?\|\.\d+)`; "exponents (`1e5`)… unparseable" | `parse_amount` calls `Decimal(cleaned)` and accepts `1e5` and `1_000`; `test_format_amount` even asserts `1E+3 → "1000.00"` |
| Zero in a Format A column | D14: a zero counts as blank; `0.00` + `25.00` gives `+25.00`; both zero → skipped | "zero counts as blank" **and** "both present but zero → keep row with `0.00`" (contradicts itself) | treats the string `"0.00"` as filled, so `0.00` + `25.00` is skipped as "both set" |
| Malformed CSV | `csv.Error` → exit 2, "cannot read" | parse line by line; a bad quote spoils only its own line (warn and skip) | plain `csv.reader`; `csv.Error` is not caught, so the run crashes with a traceback (exit 1) |
| Huge amount | `bad amount` row warning, exit 0 | exit 2, no output | `quantize` raises `InvalidOperation`, which is not caught, so it crashes |
| Rule with blank category | warn and skip | "ignored" | accepted, and matching rows get category `""` |
| Rule row with 3+ cells | warn `expected 2 cells, got M` | not specified | silently uses the first two cells |
| 3+ decimal amounts | the row is malformed | not specified | accepted; dedup key uses the unrounded value, the writer rounds HALF_UP (so `-3.505` and `-3.51` stay separate keys but are written identically) |
| `--out` is an input | D20: exit 2, inputs never modified | not specified | inputs are read, then overwritten |
| Messages | full table, `txmerge: warning: PATH:LINE: REASON; row skipped`, summary line, stdout empty | not specified | `WARNING: path:line: <free text>`, `error: …`, no summary |
| `--account` trimming | NAME and PATH trimmed; empty after trimming is an error | split on the first `=` | NAME trimmed, PATH not; `cur= ` passes |
| Same file under two NAMEs pairing with itself | stated and accepted (D4, R2) | implied | implied |
| Unpadded dates `5/3/2026`, impossible dates | stated (D14) | not stated | handled the same way by `strptime` |

**Where Q is clearer than P:**
- A ready-made end-to-end fixture with the exact expected bytes.
- The `pyproject.toml` pytest config.
- The Review Focus list (CRLF, `=` in a path, quotes in descriptions).
- A runnable test for an id past 9999 (P has only a unit test of the id format).

## Which to hand to an engineer tomorrow

**P.** It is the only one of the two that can serve as a contract: an engineer can implement it, then check behaviour against D-numbers and the Messages table without guessing. Q's code looks finished, which is exactly the risk. Copied as written, it ships a non-atomic writer, crashes on malformed CSV and on huge amounts, accepts the exponent amounts its spec rejects, and drops valid `0.00`-padded bank rows. Best combination: P as the spec, plus Q's `test_cli.py` fixture and its module layout as a starting point.

## Estimated careful reading time (senior engineer)

- **P:** about 45–60 min. It's dense; the Decisions table needs a slow read and cross-checking against the algorithms.
- **Q:** about 10 min for the spec. Add about 35–45 min to review the code against the spec, which is necessary because they diverge. About 50 min in total.
