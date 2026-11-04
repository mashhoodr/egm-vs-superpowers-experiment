# Goldfish Review Report

**Target:** `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers-p3/arms/egm/docs/designs/tsinvoice.md` (`643-895`, Detailed Implementation Plan; Stages 1-9 at lines 1-642 read as the normative spec)

Re-audit of Stage 9 (Implementation Readiness Test). Standard: `implementation-readiness-standard` (implementation-readiness, codebase-details); style used no standard.

## Reviewer Status

| Reviewer | Status |
| --- | --- |
| `egm-implementation-readiness` | completed |
| `egm-codebase-details` | completed |
| `egm-style` | completed |

| ID | Severity | Scope | Summary |
| --- | --- | --- | --- |
| implementation-readiness-2-1 | Major | 717-720 (vs 229-246, 283, 329) | Reader helper's return type cannot flag the unterminated record; blank or header unterminated records and the no-header case are undefined |
| implementation-readiness-2-2 | Major | 717-719, 800-806 (vs 229-246) | Strict pass 2 discards the rest of an erroring line, so it falls out of step with pass 1 on quote quirks: unterminated quotes go undetected, and valid rows get flagged |
| implementation-readiness-2-3 | Major | 717-720 (vs 232-235, 114) | How the in-memory text reaches `csv.reader` is unspecified; `StringIO` default newline or `splitlines` change exit codes and line numbers |
| codebase-details-2-1 | Major | 717-720, 803-804 (vs 226-228) | `csv.field_size_limit(sys.maxsize)` raises `OverflowError` on 64-bit Windows, which the plan treats as supported |
| codebase-details-2-2 | Major | 737-742 (vs 421-433, 501) | Temp-file API and open mode unstated; without `newline=""` Windows writes `\r\n`; `mkstemp` gives `0o600` and needs an explicit chmod |
| codebase-details-2-3 | Major | 659-666, 773-782 | `conftest.py` (P1) uses `tsinvoice.cli`, which does not exist until P4, so a module-level import breaks "pytest passes after each phase" |
| implementation-readiness-2-4 | Nit | 731-732 (vs 253-262, 305-311, 427-428) | Oversized rates (`quantize` `InvalidOperation` at prec 50) and >4300-digit durations (`int()` limit) crash with exit 1 |
| codebase-details-2-4 | Nit | 742 (vs 454) | `<OS reason>` not defined (`str(e)` includes the random temp file name; `e.strerror` does not) |
| style-2-1 | Nit | 650-655 | "where it seems to differ" hedges; say "where it differs" |
| style-2-2 | Nit | 753-754, 857 (vs 420) | `--help` stdout exception contradicts Stage 9 "Nothing is printed on stdout"; Stages win under Precedence |
| style-2-3 | Nit | 795-816, 822-841 | Test lists are one run-on sentence each with nested parentheses; split into sub-bullets |
| style-2-4 | Nit | 803 | 131072 is an unexplained magic number |
| style-2-5 | Nit | 846, 859-860, 888-889 | "One test through `python -m`" is stated three times; line 888 reads as if all tests use a subprocess |
| style-2-6 | Nit | 883 | "none (stdlib only, no linter dependency)" is a non sequitur; pytest is already a dev dependency |
| style-2-7 | Nit | 893-895 | Provenance comment duplicates "*Drafted with EGM*" |

## Prioritized Findings (Blockers -> Major -> Nits)

No Blockers.

### Reader helper cannot represent the unterminated record - Severity: Major
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details` (ID implementation-readiness-2-1)
* **Affected Scope:** `Lines 717-720` (implements 229-246; check (0) at 283; rates check order at 264-265; reason table row at 329)
* **Discrepancy Description**: The helper returns `(header_cells, [(start_line, cells)])` with blank records dropped. Nothing in that shape marks which record is unterminated, yet check (0) must run before the cell-count check. Three cases follow and none is defined. (a) An unterminated record whose content is blank (for example a last line `"` or `,,"`) returns `['']`/blank cells and is dropped as a blank record. The `unterminated quoted field` warning is then lost, or "the last record of pass 1" points at an earlier, valid row. (b) The header record itself can be the unterminated one (`client,description,start,"end` at EOF). It may still parse as a recognised header, and Stage 3 does not say what happens. (c) `header_cells` is undefined when a file has no non-blank record.
* **Rationale & Recommendation**: Return records as `(start_line, cells, unterminated: bool)`. State that an unterminated record is never dropped as blank, and that check (0) runs before blank-record skipping. Make `header_cells` `None` when there is no non-blank record, which maps to `unrecognised header` / `unrecognised rates header`. State that an unterminated header record is also `unrecognised header` / `unrecognised rates header` (exit 2). Add tests for (a), (b) and (c) to item 9.

### Two-pass unterminated-quote detection desynchronises on quote quirks - Severity: Major
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details` (ID implementation-readiness-2-2)
* **Affected Scope:** `Lines 717-719, 800-806` (method defined at 229-243)
* **Discrepancy Description**: The strict pass 2 "resumes at the next line after an error" (`Reader.__next__` calls `parse_reset`). Resuming throws away the rest of the erroring line, while the non-strict pass 1 keeps parsing it. Quote quirks are explicitly accepted (line 222, test at 805-806), so the two passes can disagree:
  - Missed detection: line 2 `Acme,"Design"x,08/10/2026 09:00,"08/10/2026 10:00`, line 3 `Acme,Build,08/10/2026 11:00,08/10/2026 12:00`, no later quote. Pass 1 swallows line 3 into an open quote that runs to EOF. Pass 2 errors at `x`, drops the rest of line 2, parses line 3 normally, and never sees `unexpected end of data`. The row is reported as `invalid end`, and the user is not told that line 3 was swallowed (R4.1).
  - False detection: line 2 `"A"c,"multi`, line 3 `",08/10/2026 09:00,08/10/2026 10:00`, no later quotes. Pass 1 reads one valid row. Pass 2 resumes at line 3, treats the leading `"` as an opening quote that runs to EOF, and reports `unexpected end of data`. A valid last record is dropped as unterminated, which loses billed time (G2).
* **Rationale & Recommendation**: Replace pass 2 with a detection that cannot desynchronise. Option 1 (implementation-readiness): a quote-state scan of the raw text that mirrors non-strict default-dialect rules (START_FIELD / IN_FIELD / IN_QUOTED / QUOTE_IN_QUOTED; the file is unterminated exactly when the scan ends in IN_QUOTED). Option 2 (codebase-details): one non-strict pass over `text + "\n" + SENTINEL`. If the last record is exactly `[SENTINEL]`, nothing is unterminated. Otherwise the last record is unterminated: strip the sentinel suffix from its last cell. Pick one, update the "Reading any CSV file" bullet (Stages win), and add both example files above to item 9's tests.

### In-memory text handoff to `csv.reader` unspecified - Severity: Major
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details` (ID implementation-readiness-2-3)
* **Affected Scope:** `Lines 717-720` ("Other private helpers are the implementer's choice"; spec at 232-235; "physical line" at 114)
* **Discrepancy Description**: The file is read once into memory and parsed twice, but the plan does not say how the text is given to the reader. `io.StringIO(text)` (default `newline="\n"`) splits only on `\n`, so a bare `\r` line ending raises "new-line character seen in unquoted field". Lines 244-246 make that a fatal `cannot read` (exit 2). `str.splitlines()` also splits on `\x0b`, `\x0c`, `\x1c`-`\x1e`, `\x85`, U+2028 and U+2029, which splits records and shifts the user-visible line numbers. `io.StringIO(text, newline="")` behaves like `open(..., newline="")`. The choice changes exit codes and fixed warning text.
* **Rationale & Recommendation**: Specify `csv.reader(io.StringIO(text, newline=""))` with `text = open(path, encoding="utf-8-sig", newline="").read()`. Define a physical line as text ended by `\n`, `\r\n` or `\r`. Add tests for CRLF input, bare-`\r` input and a U+2028 inside a field. The `write_file` fixture already supports bytes (line 771).

### `csv.field_size_limit(sys.maxsize)` fails on Windows - Severity: Major
* **Reviewer Lens:** `egm-codebase-details` (ID codebase-details-2-1)
* **Affected Scope:** `Lines 717-720, 803-804` (spec at 226-228)
* **Discrepancy Description**: On 64-bit Windows a C `long` is 32 bits, so `csv.field_size_limit(sys.maxsize)` raises `OverflowError: Python int too large to convert to C long` on every run. The plan treats Windows as supported: line 857 skips only two specific tests there.
* **Rationale & Recommendation**: Use a bounded value such as `min(sys.maxsize, 2**31 - 1)`, or halve on `OverflowError`. Amend the Stage bullet, since the Stages are normative, and keep the 131072 test at 803-804.

### Output temp-file API and open mode unspecified - Severity: Major
* **Reviewer Lens:** `egm-codebase-details`, `egm-implementation-readiness` (ID codebase-details-2-2)
* **Affected Scope:** `Lines 737-742` (spec at 421-433; Decisions Log 501, 513)
* **Discrepancy Description**: The plan fixes `lineterminator="\n"` and promises byte-stable output across platforms, but never says the temp file is opened with `newline=""`. In default text mode on Windows, every `\n` becomes `\r\n`, including breaks inside quoted fields. That breaks G5 and the byte test at 847-848. The temp-file API is also unnamed. `tempfile.mkstemp` creates mode `0o600`, so the `0o644` requirement needs an explicit `os.chmod`.
* **Rationale & Recommendation**: Specify `fd, tmp = tempfile.mkstemp(prefix=".tsinvoice-", dir=os.path.dirname(out_path) or ".")`, then `os.chmod(tmp, 0o644)`, then `open(fd, "w", encoding="utf-8", newline="")`. Close the file before `os.replace`. On any `OSError`, unlink `tmp` and raise `FatalError(f"{out_path}: cannot write: <reason>")`.

### P1 `conftest.py` depends on a P4 module - Severity: Major
* **Reviewer Lens:** `egm-codebase-details`, `egm-implementation-readiness` (ID codebase-details-2-3)
* **Affected Scope:** `Lines 659-666, 773-782`
* **Discrepancy Description**: P1 creates `tests/conftest.py`, whose `run_cli` fixture calls `tsinvoice.cli.main`. `cli.py` is not created until P4. A conventional module-level import fails pytest collection in P1-P3, which breaks the plan's rule at line 659 and the standard's phasing rule.
* **Rationale & Recommendation**: Either require `tsinvoice.cli` to be imported inside the `run_cli` fixture body, or create the `run_cli` and `run_module` fixtures in P4.

### Oversized numeric inputs crash instead of failing cleanly - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details` (ID implementation-readiness-2-4)
* **Affected Scope:** `Lines 731-732` (spec at 253-262, 305-311, 427-428)
* **Discrepancy Description**: The rate regex accepts any length. A rate with roughly 50 or more digits makes `quantize` raise `InvalidOperation` under the `prec=50` context. A `duration_minutes` over 4300 digits makes `int()` raise `ValueError` (the 3.11+ int/str digit limit). Both escape as tracebacks with exit 1, which is not in the exit-code table.
* **Rationale & Recommendation**: Map any conversion or overflow error on a duration to `invalid duration_minutes`. Either cap the rate size (rejected as `invalid hourly_rate`) or size the precision from the operands. Optionally pin the formatting as `format(value.quantize(Decimal("0.01"), ROUND_HALF_UP), "f")`.

### `<OS reason>` text not defined - Severity: Nit
* **Reviewer Lens:** `egm-codebase-details` (ID codebase-details-2-4)
* **Affected Scope:** `Line 742` (table row at 454)
* **Discrepancy Description**: The plan does not say whether the reason is `str(e)` or `e.strerror`. `str(e)` embeds the random `.tsinvoice-*` name, so tests cannot assert a stable message.
* **Rationale & Recommendation**: Specify `e.strerror or str(e)`.

### Hedged Precedence wording - Severity: Nit
* **Reviewer Lens:** `egm-style` (ID style-2-1)
* **Affected Scope:** `Lines 650-655`
* **Discrepancy Description**: "where it seems to differ from the Stages" invites judgement by impression.
* **Rationale & Recommendation**: "where it differs from Stages 1-9, the Stages win."

### `--help` stdout exception not in Stage 9 - Severity: Nit
* **Reviewer Lens:** `egm-style` (ID style-2-2)
* **Affected Scope:** `Lines 753-754, 857` (vs Stage 9 at 419-420)
* **Discrepancy Description**: The plan says `--help` is "the one case where stdout is used". Stage 9 says "Nothing is printed on stdout", and its only stated exception is usage errors, which go to stderr. Under Precedence, the Stage wins and contradicts argparse's default.
* **Rationale & Recommendation**: Add the exception to Stage 9: "except argparse's `--help` output". Qualify the "nothing on stdout" test at 857 the same way.

### Run-on test lists - Severity: Nit
* **Reviewer Lens:** `egm-style` (ID style-2-3)
* **Affected Scope:** `Lines 795-816, 822-841`
* **Discrepancy Description**: Each list is one sentence about 20 lines long, with nested parentheses (for example at line 838). That makes per-case coverage hard to check.
* **Rationale & Recommendation**: Split each list into sub-bullets by group (format detection, Format A, Format B, quotes, line numbers, check order, rates; dedupe, join, price, rate matching, printed text, sort/session_id, overlap). Keep the wording.

### Unexplained 131072 - Severity: Nit
* **Reviewer Lens:** `egm-style` (ID style-2-4)
* **Affected Scope:** `Line 803`
* **Discrepancy Description**: A reader cannot tell why 131072 matters.
* **Rationale & Recommendation**: Add "(the csv module's default field size limit; see Field size limit, line 226)".

### Repeated `python -m` test statement - Severity: Nit
* **Reviewer Lens:** `egm-style` (ID style-2-5)
* **Affected Scope:** `Lines 846, 859-860, 888-889`
* **Discrepancy Description**: The same fact appears three times. Line 888 reads as if the whole of `test_cli.py` uses a subprocess.
* **Rationale & Recommendation**: Keep one mention in item 11. At 888, say "one test in `tests/test_cli.py` (via `run_module`) runs the real command".

### Linting rationale does not follow - Severity: Nit
* **Reviewer Lens:** `egm-style` (ID style-2-6)
* **Affected Scope:** `Line 883`
* **Discrepancy Description**: Using only the standard library at run time does not rule out a dev-time linter. pytest is already a dev dependency (line 625).
* **Rationale & Recommendation**: "none; no linter is added as a dev dependency [D]", or simply "none".

### Duplicate provenance line - Severity: Nit
* **Reviewer Lens:** `egm-style` (ID style-2-7)
* **Affected Scope:** `Lines 893-895`
* **Discrepancy Description**: The HTML comment repeats the visible "*Drafted with EGM*" in wordier form.
* **Rationale & Recommendation**: Keep the visible line only, or shorten the comment to `<!-- Drafted with EGM -->` if a template requires it.
