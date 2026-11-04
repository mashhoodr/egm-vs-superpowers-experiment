# Goldfish Review Report

**Target:** `arms/egm2/docs/designs/txmerge.md` (`1-675`)
**Stage:** 5 – Initial Zoom Out Review
**Context:** `BRIEF.md` (fixed contract), `stakeholder_log.md` (settled rulings). New repository; no in-repo code to reuse.

## Reviewer Status

| Reviewer | Status |
| --- | --- |
| `egm-zoom-out` (instance A) | completed |
| `egm-zoom-out` (instance B) | completed |

**Severity breakdown:** 0 Blocker, 1 Major, 8 Nit (after deduplication across both instances).

**Clean audit vectors (both instances agree):**
* Context sufficiency and root-problem focus both pass.
* No (S) rule contradicts the stakeholder log.
* Reinventing the wheel: none. The design uses the standard library throughout.
* Premature optimisation: none. The amount-to-inflows index is the simplest correct lookup.
* Architectural dead-ends: none.
* Future Improvements are listed but not built, so they are not a YAGNI problem.

## Prioritized Findings (Blockers -> Major -> Nits)

### zoom-out-1-1: Rules restated three to four times; the implementation plan drops to code level - Severity: Major
* **Reviewer Lens:** `egm-zoom-out` (A and B)
* **Affected Scope:**
  * Decisions `99-123`
  * Technical Plan `221-237`, `266-276`, `297-307`
  * Detailed Implementation Plan `445-463`, `469-495`, `533-544`, `583-591`, `617-640`
  * README item `655-659`
* **Discrepancy Description:**
  * Each rule appears in the Decisions table, again as an algorithm in the Technical Plan, and a third time as near-code in the Implementation Plan. The README plans to restate D1-D23 a fourth time.
  * Examples of the repetition:
    * `normalise` at `101`, `216-217` and `457-458`
    * zero-as-blank at `114`, `229-230`, `488-489` and `422`
    * `-0.00` handling at `117`, `299-301` and `536-537`
    * the amount grammar at `115` and `471-475`
    * the write path at `121`/`123`, `297-307` and `538-544`
    * the `transfer_id` format at `109` and `273`
  * Examples of code-level detail:
    * the regex literal at `471`
    * the `NamedTemporaryFile` keyword arguments at `539-541`
    * the exact exception and warning strings at `483-492`
    * `warn = lambda ...` at `626`
    * `__main__` written out as code at `639-640`
  * The copies have already drifted. The `Warn` docstring (`461-463`) says every skipping function emits `"; row skipped"`, but the rules loader (`588`) and the messages table (`315`) use `"; rule skipped"`.
* **Rationale & Recommendation:**
  * The rules drift apart as copies multiply, and every change must be made in several places.
  * Make the Decisions table the single source of truth for behaviour.
  * Keep the Technical Plan to:
    * the data flow
    * the Row record
    * the dedup and pairing algorithms with their worked examples
    * the messages table
  * Everywhere else, cite D-numbers.
  * In the Implementation Plan, list modules, public signatures and the D-numbers each one covers. Delete function bodies, regex literals, message strings and library keyword arguments.
  * Have the README link to or summarise the rules instead of copying them.
  * Fix the `row skipped` / `rule skipped` mismatch.

### zoom-out-1-2: D23 presents a side effect of the temp-file mechanism as a privacy decision - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A and B)
* **Affected Scope:**
  * D13 "left untouched" wording `113`
  * D23 `123`
  * Data flow `192`
  * Writing `297-307`
  * `write_ledger` `538-544`
  * Test `567`
  * CUJ 4 `159`
* **Discrepancy Description:**
  * Lines `197-199` already validate every file before anything is written. That alone satisfies the stakeholder's "no output file" rule (round 1, answer 9) and leaves an existing ledger intact.
  * Temp-file-plus-rename only adds protection when the write itself fails part-way.
  * The 0600 mode is simply what `tempfile` produces, not a product choice.
  * Side effects the design does not mention:
    * re-running silently resets an existing ledger's permissions to 0600
    * a symlink at `--out` is replaced instead of written through
  * D23 has no test, even though line `668` says every D-rule has one.
* **Rationale & Recommendation:** Choose one of two options:
  * Write `--out` directly once validation has passed. Drop D23 and the cleanup path, and narrow the D13 wording.
  * Keep the atomic write as a robustness mechanism. State the failure it guards against, and present 0600 as a side effect (or preserve the existing file's mode).

### zoom-out-1-3: Summary counters leak into stage return types - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A and B)
* **Affected Scope:**
  * D22 `122`
  * CUJ 1 `136-137`
  * Messages `313`, `319-320`
  * `read_export` `480-481`
  * `deduplicate` `523`
* **Discrepancy Description:**
  * Two stages return counter tuples instead of plain lists, which contradicts "takes a list and returns a list" (`173`).
  * Every count can be derived in `cli.main`:
    * skipped rows from the number of warn calls
    * duplicates as row count before minus after dedup
    * transfers from the non-empty ids
    * written rows from `len(ledger)`
* **Rationale & Recommendation:** Keep each stage list-in, list-out and compute the summary in `cli.main`. Alternatively, print nothing on success. The stakeholder left this as "your call".

### zoom-out-1-4: Injected `Warn` callback and duplicated warning format - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A and B)
* **Affected Scope:**
  * `Warn` alias `461-463`
  * `read_export` `480`
  * `load_rules` `583-588`
  * cli `626`
* **Discrepancy Description:**
  * The callback exists for testability, but pytest's `capsys` already captures stderr.
  * The full message format is built separately in readers and in rules.
* **Rationale & Recommendation:** Use one module-level helper such as `warn(path, line, reason, what="row")` that prints to stderr. Drop the type alias and the callback parameters. This also fixes the suffix drift in zoom-out-1-1.

### zoom-out-1-5: `LedgerRow` wrapper type is unnecessary - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A and B)
* **Affected Scope:**
  * `LedgerRow` `455-456`
  * `214`
  * cli step 3 `629-631`
  * `write_ledger` signature `538`
* **Discrepancy Description:** A second frozen dataclass only carries two strings from the orchestrator to the writer. `pair_transfers` already returns ids aligned with the rows (`574`).
* **Rationale & Recommendation:** Pass `(Row, category, transfer_id)` tuples, or parallel lists, to `write_ledger`.

### zoom-out-1-6: The reason for rejecting a single module (Alternative I) does not hold - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A)
* **Affected Scope:** Alternative I `389-394`; the seven-module split `440-640`
* **Discrepancy Description:** "Harder to test each stage alone" is false. pytest tests functions in one module as easily as functions in seven. The split is not harmful, but it is justified on a false premise.
* **Rationale & Recommendation:** Either justify the split honestly (readability, one concern per module) or merge it into readers / core / cli.

### zoom-out-1-7: The zero-padding date regex skips rows that `strptime` would parse - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A and B)
* **Affected Scope:**
  * Reading an export `235-237`
  * `parse_date` `476-479`
  * Test case `5/3/2026` `513`
* **Discrepancy Description:**
  * `strptime` alone already rejects impossible dates such as `31/02/2026`.
  * The extra regex only turns unambiguous unpadded dates into skipped rows, which works against G2 ("no lost transactions").
  * It also adds a parameter and two regexes.
* **Rationale & Recommendation:** Drop the regex and the `pattern` parameter. If the strictness is deliberate (a literal reading of `DD/MM/YYYY` in the brief), say so in D14.

### zoom-out-1-8: `InputError` is reused for an output write failure - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A)
* **Affected Scope:**
  * `InputError` `449-451`
  * `write_ledger` `543-544`
  * Writing step 3 `306-307`
  * D13 `113`
* **Discrepancy Description:** A failure to write `--out` is not an input error, and D13 lists only input-side causes for exit 2.
* **Rationale & Recommendation:** Rename it to a tool-level error such as `TxmergeError`, and add "cannot write `--out`" to D13's exit-2 list.

### zoom-out-1-9: Alternatives B, C, D, E and G only restate stakeholder rulings - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (B)
* **Affected Scope:** Alternatives `338-380`
* **Discrepancy Description:** Each of these is rejected only because "the stakeholder decided". They duplicate Non-Goals (`76-85`) and the (S) Decisions, and they are not real design alternatives.
* **Rationale & Recommendation:** Fold them into one Non-Goals line that cites D4/D5/D6/D7. Keep A, F, H and I, which are genuine designer choices.
