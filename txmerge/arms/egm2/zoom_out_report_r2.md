# Goldfish Review Report

**Target:** `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers/arms/egm2/docs/designs/txmerge.md` (`1-638`)

**Round:** Stage 5 (Initial Zoom Out Review), re-audit r2. The `egm-zoom-out` lens ran as two independent instances (A and B). The persona file is `agents/zoom_out.md`.

## Reviewer Status

| Reviewer | Status |
| --- | --- |
| `egm-zoom-out` (instance A) | completed |
| `egm-zoom-out` (instance B) | completed |

**Severity breakdown:** 0 Blocker, 1 Major, 5 Nit.

**Overall verdict (both instances):** Pass with minor changes. The design addresses the root problem and uses only the standard library. It stays within BRIEF.md and the stakeholder rulings, and no finding asks to change the brief or reopen an S ruling.

## Prioritized Findings (Blockers -> Major -> Nits)

### zoom-out-2-1: The atomic temp-file-and-rename write (D23) is unneeded complexity with side effects users can see - Severity: Major
* **Reviewer Lens:** `egm-zoom-out` (A and B both raised it)
* **Affected Scope:** D13 (line 113, the clause "failure to write `--out`, existing file left untouched"); D23 (line 123); Data flow (lines 205-211); Writing (lines 291-293); NFR Security (lines 403-404); Rollout & Rollback (lines 407-408); `write_ledger` (lines 520-525); test at line 544 ("written file has mode 0600")
* **Discrepancy Description**: The stakeholder asked only that a file-level error writes no output file. Lines 205-206 already meet that, because every check runs before `--out` is opened. D23, a designer (E) choice, adds a temporary file renamed into place. That brings temp-file cleanup and a second write location in the security notes. It also brings two side effects the design accepts: the ledger gets mode 0600 (because that is how `tempfile` creates files) and a symlink at `--out` is replaced by a regular file. The test at line 544 then makes mode 0600 part of the contract.
* **Rationale & Recommendation**: The ledger is always rebuilt from inputs the tool never changes (D20, and lines 407-408: "None needed"). A re-run therefore repairs a write that crashed partway, and protecting the old copy is a speculative safeguard. Recommendation:
  * Validate all inputs, then write `--out` directly.
  * Narrow D13 to "file-level input errors never create or change `--out`".
  * Drop D23, the temp-file mention at line 404, and the mode-0600 test.
  * If atomicity stays, at minimum remove the 0600 assertion and state at line 407 why atomicity matters when the ledger can be rebuilt.

### zoom-out-2-2: The lenient date-parsing rule is not in the Decisions table - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (B)
* **Affected Scope:** Line 170 (the Decisions table "is the single source of truth for behaviour"); lines 233-237
* **Discrepancy Description**: Accepting unpadded day and month (`5/3/2026`) is product behaviour that supports G2. It is decided only in the Technical Plan, through `strptime` format strings. D14 and D15 make amounts strict but say nothing about how strict dates are.
* **Rationale & Recommendation**: Add a one-line rule, in D14 or as a new D24: "day and month may be unpadded; impossible dates are row errors". Then cut lines 233-237 down to "parsed per D-x".

### zoom-out-2-3: Library-level details in the Technical Plan - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A and B)
* **Affected Scope:** Line 224 (`csv.reader.line_num`); lines 233-237 (`datetime.strptime` formats); lines 508-510 ("never iteration over a `set`"); line 522 (`tempfile.NamedTemporaryFile(..., delete=False)`)
* **Discrepancy Description**: The architecture section names specific library calls and rules at the level of individual loops. Each one supports a real requirement (physical line numbers, date tolerance, determinism), so the drop to a lower level of detail is small.
* **Rationale & Recommendation**: In the Technical Plan, state what each detail is for (for example, "line numbers are physical lines where the row ends"). Leave the library calls to the Detailed Implementation Plan or the code. Line 522 goes away if zoom-out-2-1 is accepted. This is optional and is raised so the pattern does not grow.

### zoom-out-2-4: A test for the 10,000th transfer id (`T10000`) - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A and B)
* **Affected Scope:** D9 (line 109, the sentence "Past 9999 …"); test at line 573
* **Discrepancy Description**: Scale (lines 324-326) says a personal ledger is thousands of rows. Producing 10,000 pairs would need at least 20,000 matched transfer rows in one run, so a dedicated test covers a case the tool will not meet.
* **Rationale & Recommendation**: Keep the D9 sentence, since it costs nothing and documents the format. Drop the `T10000` test, or check the id-formatting expression directly without building 10,000 pairs.

### zoom-out-2-5: The five-count end-of-run summary changes reader signatures - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A)
* **Affected Scope:** D22 (line 122); CUJ 1 "Then" (lines 136-137); Messages table success row (line 301); Counts paragraph (lines 316-320); `read_export` return type `tuple[list[Row], int]` (lines 474-479)
* **Discrepancy Description**: The stakeholder left success output as "your call" (round 2, Q9). The design chose a summary with five counts. To support it, `read_export` returns a skipped count in a tuple, and the summary is part of CUJ 1's acceptance criteria. Per-row warnings already report every skipped row.
* **Rationale & Recommendation**: The summary can stay, but it should not change the reader interface.
  * Either count skips in one place (`model.warn` already sees every skip), or limit the summary to counts that can be read from list lengths.
  * Take the summary out of CUJ 1's acceptance criteria.

### zoom-out-2-6: The amount-to-inflows index in transfer pairing is a minor premature optimisation - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A; B looked at the same index and judged it not worth flagging)
* **Affected Scope:** Transfer pairing step 1 (lines 262-264); Scale (lines 324-326)
* **Discrepancy Description**: The pairing algorithm builds an index from amount to inflow positions, but Scale says "No performance work is planned" and the ledger is thousands of rows. A direct scan maps one-to-one onto D6 and D7.
* **Rationale & Recommendation**: Describe pairing as "for each outflow in ledger order, scan the unpaired inflows". Mention the index only as an optional implementation detail. This is a simplicity preference, and either way is acceptable.

## Categories With No Findings (both instances)

* **Context sufficiency:** Pass. Lines 9-53 state the objective and why it matters.
* **Root-problem focus and alignment:** Pass. G1-G6 map to BRIEF's four wants, and no settled ruling is re-argued.
* **Speculative features:** None beyond the findings above. Non-Goals (lines 76-85) and Future Improvements (lines 430-431) are listed but not built.
* **Architectural dead-ends:** None. The stages are plain functions over immutable `Row` records, which leaves clean places to add things later.
* **Reuse / platform standards:** Not applicable, because this is a new repository. The design uses stdlib `csv`, `argparse`, `decimal` and `datetime`. The strict amount grammar ahead of `Decimal()` (lines 470-473) is justified, because `Decimal()` alone accepts `NaN`, `1e3` and `1_000`.
* **Module structure:** Seven small modules (Alternative I, lines 389-396) is reasonable for this size.
