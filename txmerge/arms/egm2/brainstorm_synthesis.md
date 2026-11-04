# Brainstorm Synthesis: `txmerge`

**Mode:** BRAINSTORM. **Inputs:** `BRIEF.md` (fixed contract), `stakeholder_log.md` (rounds 1-2), and the anchored hypothesis points (1)-(6).
**Note:** settled stakeholder rulings are not re-raised. Findings cover gaps in the "your call" items, ambiguities, and consequences of the rulings.

## Reviewer Status

| Reviewer | Role | Status |
| --- | --- | --- |
| `egm-design` | Skeptical Architect Brainstormer | completed |
| `egm-codebase-details` | Technical Accuracy Brainstormer | completed |
| `egm-zoom-out` | Simplicity & Scope Brainstormer | completed |
| `egm-comprehension` | Naive Reader Brainstormer | completed |
| `egm-implementation-readiness` | Implementation Readiness Brainstormer | completed |
| `egm-structural` | Document Structure Brainstormer | completed |

**Severity counts (after deduplication):** 3 Blocker, 16 Major, 9 Nit.

- When reviewers rated a finding differently, the highest rating is used and the range is shown.
- Lens abbreviations: D = design, C = codebase-details, Z = zoom-out, Co = comprehension, I = implementation-readiness, S = structural.

---

## Blockers

### B1. Which rows survive dedup, and their input-order position, is undefined (points 2, 3, 4, 6)
- **Raised by:** all 6 lenses. Co, I and S rated it Blocker; D, C and Z rated it Major.
- **Gap:** a key appears 2 times in export 1 and 3 times in export 2. Nothing says which physical row the 3rd copy is.
  - That choice sets the copy's input-order position, which is the sort tiebreak.
  - Output order drives greedy pairing, and pairing drives T-id numbering, so byte-identical output depends on it.
  - "Input order" across interleaved arguments (`A=x B=y A=z`) is also undefined.
- **Recommendation:** define it as an algorithm with a worked table.
  - Input-order key = (`--account` argument index, physical line number).
  - Walk exports in argument order. Emit a row when its key's running count in the current export is higher than the number of copies already emitted. Copy k therefore takes the position of the k-th occurrence in the first export that reaches count k.
- **Disagreements to resolve:**
  - C proposed instead that "every kept copy takes the index and text of its first occurrence", giving all copies the same position.
  - Co asked whether each copy keeps its own text or takes the key's first-seen text. Most lenses (D, I, Z, C) say every copy uses the key's first-occurrence text, trimmed.

### B2. Amount grammar and numeric type are not decided (points 1, 2, 4, 6; stakeholder R2Q2 "your call")
- **Raised by:** all 6 lenses. I rated it Blocker; the others rated it Major.
- **Gap:** dedup equality, transfer equality and the 2-decimal output all depend on one amount normaliser.
  - Floats break all three.
  - `Decimal(str)` accepts `NaN`, `Infinity`, `1e3`, `1_000` and `+5`. A NaN breaks sorting and comparisons, and `1e3` prints as `1E+3`.
  - A naive "strip commas" turns `1,25.00` into 125.00 without warning.
  - Undecided cases: `£`, `(5.00)`, `CR`/`DR`, more than 2 decimal places, a signed Debit/Credit, and thousands separators in Format B.
- **Recommendation (consensus):**
  - Use `Decimal` everywhere.
  - Validate with a strict regex before calling `Decimal()`: `^\d{1,3}(,\d{3})*(\.\d{1,2})?$|^\d+(\.\d{1,2})?$`.
    - Format A Debit/Credit: no sign.
    - Format B: optional leading `-`. D also allows a leading `+`.
  - Anything else is skip-and-warn: currency symbols, parentheses, CR, and more than 2 decimal places. Never round.
  - Normalise zero to `0.00`, never `-0.00`.
  - Format output with `f"{d:.2f}"` or `format(q, "f")`, never `str()`.

### B3. "Byte-identical" output is not pinned at the serialisation level (point 6)
- **Raised by:** all 6 lenses. I rated it Blocker; the others rated it Major or Nit.
- **Gap:**
  - `csv.writer` defaults to `\r\n` line endings.
  - Opening the file without `newline=""` can produce `\r\r\n`.
  - Encoding, BOM, quoting policy and the final newline are unstated.
- **Recommendation:**
  - Open with `open(tmp, "w", encoding="utf-8", newline="")`.
  - Use `csv.writer(f, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)`.
  - Write no BOM, and end every row with `\n`, including the last.
  - Golden tests compare raw bytes.

---

## Major

### M1. Pipeline stage order and the meaning of "output order" (points 1-6)
- **Raised by:** S (Blocker), Co (Major), D (Nit).
- **Gap:** pairing walks "output order" before category and transfer_id exist. The dependency chain is implicit.
- **Recommendation:** make one numbered pipeline the spine of the design doc, with an input, output and invariant for each stage:
  1. Validate all inputs.
  2. Parse into canonical rows.
  3. Dedup per account.
  4. Sort.
  5. Pair transfers.
  6. Assign T-ids.
  7. Apply rules to rows that are not transfers.
  8. Serialise.
  9. Write atomically.

  Output order is fixed at stage 4 and never changes after that.

### M2. Atomic write and "nothing written on exit 2" mechanics (points 1, 6)
- **Raised by:** D, C, Z, Co, I, S.
- **Recommendation:**
  - Read and validate every input header, every file and the rules file before opening any temp file.
  - Create the temp file with `mkstemp` or `NamedTemporaryFile(delete=False)` in `dirname(abspath(out))`, then `os.replace` it onto the output.
  - Unlink the temp file in `finally`.
  - An existing `--out` is untouched on any exit 2.
  - A missing output directory exits 2.
  - `--out` being the same path as an input is safe, because inputs are read first. Say so in the doc.
- **Disagreement:**
  - C and I want `fsync` plus a `chmod` to the umask-derived mode, because `mkstemp` creates files as 0600.
  - Z says no fsync and no locking (YAGNI).
  - D says chmod, or document that the file is 0600.

### M3. Header, row-shape, blank-line and line-number rules (point 1; stakeholder R2Q7 "your call")
- **Raised by:** D, C, Z, Co, I, S.
- **Gaps:**
  - "Surrounding spaces stripped" could apply per cell or to the whole line.
  - A trailing empty header column (Excel re-saves often add one) is not covered.
  - Leading or body blank lines: `csv.reader` returns `[]` for them.
  - Wrong field count is not covered.
  - A header-only file versus a 0-byte file is not covered.
  - "Line" in warnings is undefined: physical line versus record number. They differ when a quoted field contains a newline.
- **Recommendation (consensus):**
  - Strip each cell and match case-sensitively.
  - Skip blank lines silently.
  - A wrong field count is skip-and-warn.
  - A header-only file is valid and yields zero rows.
  - An empty file exits 2.
  - Warnings use `reader.line_num`, 1-based, with the header as line 1.
  - D adds that a trailing empty header column makes the header unrecognised, so exit 2.

### M4. Non-UTF-8 input crashes with exit 1 (contract, point 1)
- **Raised by:** D, C, I, Z.
- **Gap:** UK exports are often cp1252, where `£` is byte 0xA3. Reading with `utf-8-sig` raises an uncaught `UnicodeDecodeError`, so the run exits 1 with a traceback. That is neither of the documented outcomes.
- **Recommendation:**
  - Read with `encoding="utf-8-sig", newline=""`. This also removes the BOM.
  - On a decode error, exit 2 with a message naming the file.
  - I offers an explicit cp1252 fallback as the alternative.

### M5. Rules-file edge cases (point 5; stakeholder R2Q8 "your call")
- **Raised by:** all 6 lenses.
- **Gap:**
  - A blank pattern is a substring of every description, so with first-match-wins it silently catches every later row.
  - A blank category is not covered.
  - A category literally named `Transfer` produces rows that look like transfers but have no transfer_id.
  - Rule rows with the wrong column count are not covered.
- **Disagreement on each case:**
  - **Blank pattern or category:** D and C say it is a malformed rules file (exit 2). I and Z say skip that rule with a warning.
  - **`Transfer` category:**
    - C: reject with exit 2.
    - D: allow, with a warning.
    - I and Z: allow silently.
    - Co: allow, with no transfer_id.
  - **Wrong column count:** D and I say exit 2.
- **Shared recommendation:** apply the same BOM and per-cell-strip header handling to the rules header as to the input headers.

### M6. What rules match against, and how case is folded (points 2, 5)
- **Raised by:** D, C, I, Co.
- **Gap:** with matching on the raw text, pattern `costa coffee` misses `COSTA  COFFEE` (double space).
- **Disagreement:**
  - D: match against the normalised description (whitespace collapsed).
  - I and C: match against the kept, trimmed text, with `casefold` only.
- **Consensus:**
  - Use `casefold`, not `lower`, everywhere. They differ for `ß`.
  - Z and D trim the pattern; I says do not trim it.

### M7. Does `0.00` in Debit or Credit count as "filled"? (point 1)
- **Raised by:** D (risk), C and I (opposite choice).
- **Risk:** many banks write `0.00` in the unused column. Under the strict "both filled = malformed" rule, every row of such an account is skipped and the run still exits 0. That silently loses the whole account, against "never lose a real transaction".
- **Disagreement:**
  - D: a field that parses to zero counts as blank for the both/neither test.
  - C and I: a non-blank `0.00` counts as filled.
- **Must be decided explicitly** and covered by a test.

### M8. Zero-amount rows: kept or dropped, and how they print (points 1, 4; stakeholder R2Q4)
- **Raised by:** all 6 lenses.
- **Gap:** the hypothesis says zero rows never pair. It does not say whether they stay in the ledger.
- **Recommendation (consensus):**
  - Keep them and categorise them by rules.
  - Always print them as `0.00`.
  - A zero row is neither an outflow nor an inflow.
  - D adds that a Format A row with both fields zero counts as "neither filled", so it is skip-and-warn. This interacts with M7.

### M9. One account NAME given both formats (points 1, 2; stakeholder R1Q12 "your call")
- **Raised by:** all 6 lenses.
- **Recommendation (consensus):**
  - Allow it, with no special case.
  - The dedup key (ISO date, signed Decimal, normalised text) does not depend on format, so mixing works.
  - The same-account exclusion from transfers still holds.
  - Record the choice before the dedup section.

### M10. Account-name sort comparator (point 3)
- **Raised by:** Co, I, C, D.
- **Gap:** the order could be codepoint, casefolded or locale-based. For `Amex` versus `barclays` the result differs.
- **Recommendation:**
  - Compare as plain `str`, by codepoint, case-sensitive, with no locale.
  - Full key: (date, account, argument index, line).

### M11. Transfer distance and greedy behaviour need precise wording and worked examples (point 4)
- **Raised by:** Co, S, I, C.
- **Recommendation:**
  - Distance is `abs((d_in - d_out).days)` on `date` objects, and pairs are allowed when it is `<= 3`.
  - An inflow dated before its outflow can pair.
  - Add a scenario table covering:
    - an inflow dated before its outflow
    - two inflows at equal distance
    - an earlier outflow taking the inflow a later one wanted (greedy is not optimal)
    - identical dedup copies, each pairing separately
    - the accepted refund mis-pair
  - Add one end-to-end golden example.

### M12. Decision log for every "your call" item, plus Alternatives and Risks sections (all points)
- **Raised by:** S.
- **Gap:** about 14 items were delegated. These are unanswered in the hypothesis:
  - same name in both formats (R1Q12)
  - amount syntax (R2Q2)
  - blank lines (R2Q7)
  - rules edge cases (R2Q8)
  - success output (R2Q9)
  - zero-row retention (R2Q4, partly answered)
- The feature-spec standard requires Alternatives and Risks sections.
- **Recommendation:**
  - Add a decision-log table with columns Log ref, Decision, Rationale, Alternatives rejected and Test ID.
  - Add "Alternatives Considered". Record the stakeholder-rejected options there: sum vs max, optimal vs greedy, fuzzy matching.
  - Add "Risks & Limits".

### M13. CLI parsing edge cases (contract)
- **Raised by:** I (Major), Co, C and Z (Nit).
- **Recommendation:**
  - Split `--account` on the first `=`. An empty NAME or PATH triggers `parser.error()`, which exits 2.
  - Mark `--rules`, `--out` and at least one `--account` as required, and use `add_subparsers(required=True)`.
  - argparse usage errors also exit 2, which is consistent with the other exit-2 cases. State it.
  - IsADirectory and PermissionError on inputs exit 2, the same as a missing file.

### M14. Date parsing strictness (point 1)
- **Raised by:** C (Major), D, I.
- **Gap:**
  - In 3.11, `date.fromisoformat` accepts `20240105` and week dates.
  - `strptime("%d/%m/%Y")` accepts the non-padded `1/2/2024`.
- **Recommendation:**
  - Strip the cell, check it against a strict zero-padded regex, then call `strptime`.
  - An impossible date such as `31/02` is skip-and-warn.
  - Format B bad rows get the same skip-and-warn as Format A (R2Q3).
  - Posting Date is never parsed or validated (Co).

### M15. Unquoted thousands separators in Format A shift columns (point 1)
- **Raised by:** C.
- **Gap:** an unquoted `1,250.00` splits into an extra field.
- **Recommendation:** treat any wrong field count as malformed (see M3), and document this as the case it catches.

### M16. Architecture shape: format registry vs two plain functions (points 1, 4, 5)
- **Raised by:** S (Major) and Z (Nit). The two disagree.
- **S:** use a format registry keyed by the normalised header tuple. Each parser emits a canonical record. Dedup, sort, pairing and rules are pure functions, and IO happens only at the edges.
- **Z:** no registry and no class hierarchy. Write two parse functions, use no `logging`, and list cuts as Non-Goals.
- **Common ground:** a canonical row type with pure middle stages satisfies both.

---

## Nits

- **N1. T-id overflow (point 4).** Co, S, I, D, Z: use `f"T{n:04d}"`, which grows naturally to `T10000`. Number pairs in the order they are found.
- **N2. Success output and warning format (R2Q9).**
  - I: `txmerge: warning: {path as given}:{line}: {reason}`, with stdout empty.
  - C: add a deterministic one-line stderr summary (rows read, skipped, duplicates, transfers, uncategorised).
  - Z: print nothing (YAGNI), but notes this leaves the refund mis-pair risk invisible.
  - D: a summary is optional.
- **N3. Exact normalisation formula (point 2).** C, I, D: the key text is `" ".join(s.split()).casefold()` and the kept text is `s.strip()`. Both handle Unicode whitespace, including NBSP.
- **N4. Hidden non-determinism (point 6).** C: never iterate a `set` of strings, because hash randomisation changes the order. Use lists and insertion-ordered dicts.
- **N5. Consequences of settled rulings to document (point 4).** D, S, Co:
  - The card's Transaction Date can lag a current-account debit past the 3-day window.
  - Two names pointing at the same file can self-pair that file's own rows as a transfer.
  - Greedy pairing can leave an outflow unpaired when a full matching existed. This is expected; say so, so testers do not "fix" it.
  - The refund mis-pair stays an accepted risk.
- **N6. Non-Goals list (contract).** Z: Balance checks, fuzzy matching, incremental mode, config file, `--dry-run`/`--verbose`, and locale or currency handling.
- **N7. Traceability tags.** S: tag every normative sentence with `[R#Q#]`, `[contract]` or `[D-nn]`, so settled items are distinguishable from design choices.
- **N8. Pairing complexity (point 4).** Z and D: O(n^2) greedy pairing is fine at personal scale. Indexing inflows by amount is optional.
- **N9. Stdlib over hand-written code (points 1, 6).** Z:
  - `utf-8-sig` removes the BOM.
  - `strptime` rejects impossible dates.
  - `argparse` `action="append"` collects repeated `--account` values.

---

## Open decisions for the Elephant (disagreements recorded, not resolved)

1. Kept-copy position rule (B1): position of the k-th copy, versus all copies sharing the first occurrence's position.
2. `0.00` in Debit or Credit: blank or filled (M7).
3. Blank rule pattern or category: exit 2, or skip with a warning (M5).
4. Rule category `Transfer`: reject, warn, or allow (M5).
5. Rule matching basis: normalised text or trimmed text (M6).
6. `fsync` and `chmod` on the atomic write (M2).
7. Success summary on stderr, or silence (N2).
8. Format registry, or two functions (M16).
