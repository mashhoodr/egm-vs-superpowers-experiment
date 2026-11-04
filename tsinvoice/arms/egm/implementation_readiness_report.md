# Goldfish Review Report

**Target:** `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers-p3/arms/egm/docs/designs/tsinvoice.md` (`Lines 624-825`, Detailed Implementation Plan; Stages 1-9 at lines 1-623 read as normative spec)

**Stage:** 9 (Implementation Readiness Test). **Verdict:** Not ready. 1 Blocker, 6 Major, 19 Nit.

## Reviewer Status

| Reviewer | Status |
| --- | --- |
| `egm-implementation-readiness` | completed |
| `egm-codebase-details` | completed |
| `egm-style` | completed |

## Findings Index

| ID | Severity | Scope | Summary |
| --- | --- | --- | --- |
| `codebase-details-1-1` | Blocker | L226-234, 269, 314, 432, 442, 492; plan L679-686, 743-745 | Non-strict csv does not raise on EOF inside a quoted field; the design gives no working way to detect an unterminated quote |
| `implementation-readiness-1-1` | Major | L638-808 | Plan is a flat file list with no phases, order, or checkpoints |
| `codebase-details-1-2` | Major | L233-234, 442, 492 vs R4.1 | `csv.field_size_limit` (131072) turns a long unterminated quote into a fatal `csv.Error`, contradicting R4.1 |
| `codebase-details-1-3` | Major | L725-735 | `conftest.py` helpers (`run`, `write_csv`) under-specified: fixture vs function, `--out` discovery, bytes input |
| `codebase-details-1-4` | Major | L737-791, 816 | Test plan omits cases for several normative rules (decode errors, write guarantees, normalise, single-digit dates, warning wording) |
| `style-1-1` | Major | L816 | "Every rule has at least one test" has no countable unit, so the done criterion is unverifiable |
| `style-1-2` | Major | L631-633 | Precedence note's "only" list of user-visible text omits Stage 3 (bad-row warning wrapper) and argparse usage text |
| `implementation-readiness-1-2` | Nit | L670 | `OutputRow` "strings/ints" does not say which field is which type |
| `implementation-readiness-1-3` | Nit | L715-719 | `parse_tracker` `ArgumentTypeError` message text unspecified |
| `implementation-readiness-1-4` | Nit | L744 | Reader unit test asserts "exit 0", which `read_export` cannot produce |
| `implementation-readiness-1-5` | Nit | L243-251, 431-434, 753-755 | No check order for rates rows, yet tests assert exact messages |
| `implementation-readiness-1-6` | Nit | L428, 435 | `<OS, decode or csv reason>` text source (`strerror` vs `str(exc)`) not pinned |
| `codebase-details-1-5` | Nit | L226-232, 260-264 | Unterminated quote in a header record yields `unrecognised header`/exit 2, against the spirit of R4.1; unstated |
| `codebase-details-1-6` | Nit | L247-248, 360-362, 697-698 | Decimal context precision not pinned; long rates risk silent rounding or `InvalidOperation` |
| `codebase-details-1-7` | Nit | L214, 405, 715-717 | argparse `--help` to stdout and `allow_abbrev=True` conflict with stated CLI contract |
| `codebase-details-1-8` | Nit | L716 | Specify `add_subparsers(dest="command", required=True)` |
| `codebase-details-1-9` | Nit | L185, 412-419, 480, 583 | Atomic write: no `fsync`; `mkstemp` 0o600 needs explicit chmod to 0o644; `dir` for bare `--out` unstated in spec |
| `codebase-details-1-10` | Nit | L291-293 | `duration_minutes` rule ambiguous for `30.`; give a regex with `fullmatch` |
| `codebase-details-1-11` | Nit | L283-288 | Unicode digits / leading spaces accepted by `\d` and `strptime` not addressed |
| `codebase-details-1-12` | Nit | L406-409, 703-708 | Output `csv.writer` settings (`lineterminator`, quoting) and embedded line breaks unpinned |
| `style-1-3` | Nit | L634-636, 698 | "Never restates a rule" is false; L698 adds "never exponent notation" not stated in Stage 9 |
| `style-1-4` | Nit | L740-755, 761-778 | Test lists are single run-on sentences; hard to tick off |
| `style-1-5` | Nit | L752 | "ragged rows" is undefined jargon |
| `style-1-6` | Nit | L772 | "large values" has no concrete threshold or example |
| `style-1-7` | Nit | L777 | "exact in-export repeats" narrower than Stage 8 (cross-export repeats also exempt) |
| `style-1-8` | Nit | L790, 803, 814-815, 818-819 | Vague or inconsistent wording (expected result, "Short", optional pyflakes, `python -m` vs `main()`) |

## Prioritized Findings (Blockers -> Major -> Nits)

### Unterminated-quote detection relies on behaviour csv does not have - Severity: Blocker
* **ID:** `codebase-details-1-1` (also raised by `implementation-readiness` as Major, close to Blocker)
* **Reviewer Lens:** `egm-codebase-details`, `egm-implementation-readiness`
* **Affected Scope:** `Lines 226-234, 269, 314, 432, 442, 492`; plan `Lines 679-686, 743-745`
* **Discrepancy Description**: Lines 233, 442 and 492 treat an unterminated quoted field as a kind of `csv.Error` exempt from the fatal path. In default (non-strict) mode, CPython's csv reader raises nothing at EOF inside a quoted field; it returns the partial record, indistinguishable from a last line without a newline. Only `strict=True` raises `unexpected end of data`, but strict mode also rejects the `"Design" review` quirk the spec requires to read normally (L221-224, 745-746). Followed literally, the swallowed record falls through to `expected 4 fields, got 2` or `invalid end`/`invalid duration_minutes`, the required test (L743-745) fails, and the rates fatal message (L432) is unreachable. The readers.py entry leaves "private helpers" to the implementer, so the detection method is an undeclared design decision.
* **Rationale & Recommendation**: Choose and document one mechanism in "Reading any CSV file" and the readers.py entry, e.g. (a) wrap the line iterator, track each record's raw physical lines, and flag the final record if its raw text has unbalanced quotes; or (b) a second `strict=True` pass used only to detect `unexpected end of data`. Apply to both exports and rates. Reword L233, 442, 492 so an unterminated quote is no longer described as a `csv.Error`.

### No phases or checkpoints in the plan - Severity: Major
* **ID:** `implementation-readiness-1-1` (also `codebase-details` M2)
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** `Lines 638-808`
* **Discrepancy Description**: The standard requires incremental phases, each leaving the code buildable and testable. The plan is a flat list of 13 Create entries with no execution order or gates.
* **Rationale & Recommendation**: Add ordered phases with gating tests, e.g. P1 `pyproject.toml`, `__init__.py`, `model.py` + normalise/Entry tests; P2 `readers.py` + `test_readers.py`; P3 `core.py` + `test_core.py`; P4 `writer.py`, `cli.py`, `__main__.py`, `conftest.py` + `test_cli.py`; P5 `README.md`. Each phase ends with `python -m pytest` passing.

### csv field-size limit makes long unterminated quotes fatal, contrary to R4.1 - Severity: Major
* **ID:** `codebase-details-1-2`
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** `Lines 233-234, 442, 492` vs stakeholder R4.1
* **Discrepancy Description**: `csv.field_size_limit()` defaults to 131072 characters. An unterminated quote that swallows more than that raises `csv.Error: field larger than field limit`, which L233/442 make fatal (exit 2). R4.1 says "Don't stop with exit 2 for this." A few thousand rows is enough to hit it.
* **Rationale & Recommendation**: Either raise the limit (e.g. `sys.maxsize`, noting it is process-wide) or map this error, when inside an open quoted field, to the `unterminated quoted field` bad row. Add a test.

### Test helpers in conftest.py under-specified - Severity: Major
* **ID:** `codebase-details-1-3` (also `implementation-readiness` Nit 4, `style` N3)
* **Reviewer Lens:** `egm-codebase-details`, `egm-implementation-readiness`, `egm-style`
* **Affected Scope:** `Lines 725-735`
* **Discrepancy Description**: `run(args)` "calls `main(args)` with `capsys`", but `capsys` is a fixture a plain function cannot reach. It is not stated how `run` finds the `--out` path, what `out_text` is when no file was written (exit 2) or when a pre-existing file must be shown unchanged (CUJ 5). Test modules cannot cleanly import plain functions from conftest. `write_csv` does not say text vs bytes or newline handling, yet BOM, CRLF and non-UTF-8 tests need bytes.
* **Rationale & Recommendation**: Define each helper as a fixture with exact signature and return values, e.g. fixture `run(capsys, tmp_path)` returning `run(args, out_path) -> (code, stdout, stderr, out_text | None)`; give `write_csv` a bytes option.

### Test plan omits cases for normative rules - Severity: Major
* **ID:** `codebase-details-1-4` (also `implementation-readiness` Nit 5)
* **Reviewer Lens:** `egm-codebase-details`, `egm-implementation-readiness`
* **Affected Scope:** `Lines 737-791, 816` vs spec `Lines 100-104, 283-285, 304-315, 406-442, 485, 494`
* **Discrepancy Description**: No named test for: undecodable input (`cannot read: <decode reason>`); a non-quote `csv.Error` (fatal); missing/unwritable output directory (`cannot write`, exit 2, no temp left); symlinked `--out` replaced by regular file; temp mode 0o644 and cleanup on failure; no `.tsinvoice-*` leftovers on success; missing sub-command or required option; `normalise` NFC (composed vs decomposed é), casefold (ß vs ss), whitespace collapse (no test file at all); single-digit Format A (`5/1/2026 9:00`); exact wording of unrated-session and overlap warnings; extra blank vs non-blank cells; field-limit case (see `codebase-details-1-2`). The L816 coverage claim therefore does not hold.
* **Rationale & Recommendation**: Add these as named cases (normalise tests in a new `tests/test_model.py` or `test_core.py`; write guarantees in `test_cli.py`, skipping permission checks on Windows).

### Coverage done-criterion has no countable unit - Severity: Major
* **ID:** `style-1-1`
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Line 816`
* **Discrepancy Description**: "Every rule in Stages 1-9 has at least one test" relies on "rule", which is never defined; stages mix rules, rationale and cross-references, so two reviewers would count differently.
* **Rationale & Recommendation**: Use a countable unit, e.g. "every bullet in Stages 1-9, every row of the bad-row reasons, Fatal error messages, exit-code and worked-examples tables, and every CUJ", optionally requiring each test to cite its stage/row.

### Precedence note's list of user-visible text is incomplete - Severity: Major
* **ID:** `style-1-2`
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 631-633`
* **Discrepancy Description**: The note says user-visible text is defined "only" in the bad-row table, Fatal error table, and warning formats in Stages 6, 8 and 9. The bad-row warning wrapper `tsinvoice: warning: <path>:<line>: <reason>` is in Stage 3 (L267), and argparse usage text is also user-visible.
* **Rationale & Recommendation**: Change to "Stages 3, 6, 8 and 9" and add argparse's usage text (Stage 1), or drop "only".

### OutputRow field types unstated - Severity: Nit
* **ID:** `implementation-readiness-1-2` (also `codebase-details` N9, `style` N2)
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`, `egm-style`
* **Affected Scope:** `Line 670`
* **Discrepancy Description**: "the six output columns as strings/ints" does not say which.
* **Rationale & Recommendation**: State `date`, `client`, `description`, `amount`, `session_id`: `str` (blank session_id is `""`); `minutes`: `int`.

### parse_tracker error text unspecified - Severity: Nit
* **ID:** `implementation-readiness-1-3` (also `codebase-details` N4)
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** `Lines 715-719`
* **Discrepancy Description**: The `ArgumentTypeError` message is not given.
* **Rationale & Recommendation**: Fix the text (e.g. `expected NAME=PATH with non-empty NAME and PATH`) or state it is free-form and untested.

### Reader unit test asserts an exit code - Severity: Nit
* **ID:** `implementation-readiness-1-4` (also `style` N5)
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-style`
* **Affected Scope:** `Line 744`
* **Discrepancy Description**: `test_readers.py` expects "exit 0" but `read_export` returns entries and warnings only.
* **Rationale & Recommendation**: Assert the warning and returned entries (no `FatalError`) there; move the exit-0 check to `test_cli.py`.

### Rates-row check order missing - Severity: Nit
* **ID:** `implementation-readiness-1-5`
* **Reviewer Lens:** `egm-implementation-readiness`
* **Affected Scope:** `Lines 243-251, 431-434, 753-755`
* **Discrepancy Description**: Stage 3 fixes export check order but Stage 2 does not for rates; a row with several faults could yield different messages while tests assert the exact one.
* **Rationale & Recommendation**: State order: unterminated quote, cell count, empty pattern, invalid hourly_rate.

### OS/decode reason text source unpinned - Severity: Nit
* **ID:** `implementation-readiness-1-6`
* **Reviewer Lens:** `egm-implementation-readiness`
* **Affected Scope:** `Lines 428, 435`
* **Discrepancy Description**: `<OS, decode or csv reason>` could be `str(exc)` or `exc.strerror`.
* **Rationale & Recommendation**: State `exc.strerror or str(exc)` for `OSError`, `str(exc)` otherwise; tests match only the `<path>: cannot read: ` prefix.

### Unterminated quote in a header record - Severity: Nit
* **ID:** `codebase-details-1-5` (also `implementation-readiness` finding 2, related edge)
* **Reviewer Lens:** `egm-codebase-details`, `egm-implementation-readiness`
* **Affected Scope:** `Lines 226-232, 260-264`
* **Discrepancy Description**: An open quote on the header line swallows the file into the header record, giving `unrecognised header` / exit 2, which a reader of R4.1 may not expect.
* **Rationale & Recommendation**: State which rule wins and add a test.

### Decimal precision not pinned - Severity: Nit
* **ID:** `codebase-details-1-6`
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** `Lines 247-248, 360-362, 697-698`
* **Discrepancy Description**: Default context has 28 significant digits and the rate regex has no length cap, so `minutes * rate / 60` can round before `quantize`, and `quantize` can raise `InvalidOperation` (traceback, exit 1).
* **Rationale & Recommendation**: Use `decimal.localcontext()` with an explicit `prec`, or cap rate digits.

### argparse defaults vs CLI contract - Severity: Nit
* **ID:** `codebase-details-1-7`
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** `Lines 214, 405, 715-717`
* **Discrepancy Description**: `--help` prints to stdout (contract says nothing on stdout); `allow_abbrev=True` accepts `--rate`/`--trac` (contract says exactly this CLI).
* **Rationale & Recommendation**: Declare `--help` acceptable; set `allow_abbrev=False` or accept abbreviations explicitly.

### Required sub-command should set dest - Severity: Nit
* **ID:** `codebase-details-1-8`
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** `Line 716`
* **Discrepancy Description**: `add_subparsers(required=True)` without `dest` has historically raised `TypeError` instead of a usage error when the sub-command is missing (reviewer did not confirm affected 3.11.x releases).
* **Rationale & Recommendation**: Specify `add_subparsers(dest="command", required=True)`.

### Atomic-write mechanism partly unpinned - Severity: Nit
* **ID:** `codebase-details-1-9`
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** `Lines 185, 412-419, 480, 583`
* **Discrepancy Description**: Without `flush` + `os.fsync` before `os.replace`, "never leaves a truncated --out" does not hold across power loss. `mkstemp` creates 0o600, so an explicit chmod to 0o644 is needed; spec should say `dir` when `--out` has no directory part.
* **Rationale & Recommendation**: Add flush/fsync or narrow the claim; state `os.chmod`/`fchmod` 0o644 and `dir=dirname(out) or "."` in the spec.

### duration_minutes rule ambiguous - Severity: Nit
* **ID:** `codebase-details-1-10`
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** `Lines 291-293`
* **Discrepancy Description**: "Digits, optionally `.` and only zeros" leaves `30.` undefined.
* **Rationale & Recommendation**: Give `^[0-9]+(\.0+)?$` with `re.fullmatch`.

### Unicode digits and whitespace in date parsing - Severity: Nit
* **ID:** `codebase-details-1-11`
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** `Lines 283-288`
* **Discrepancy Description**: The `start_iso` prefix check does not pin `[0-9]`; `strptime` numeric directives accept Unicode digits and leading spaces, and a format space matches any whitespace run.
* **Rationale & Recommendation**: State `[0-9]` for the prefix and whether strptime's leniency is acceptable.

### Output writer settings unpinned - Severity: Nit
* **ID:** `codebase-details-1-12`
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** `Lines 406-409, 703-708`
* **Discrepancy Description**: Without naming `lineterminator="\n"` the default `\r\n` may be kept; embedded line breaks in client/description are not addressed.
* **Rationale & Recommendation**: Specify `csv.writer(f, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)` on `open(..., encoding="utf-8", newline="")`, and state that inner line breaks are written as-is inside quoted fields.

### "Never restates a rule" is not true - Severity: Nit
* **ID:** `style-1-3`
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 634-636, 698`
* **Discrepancy Description**: The plan restates rules (L698, L707-708, test lists), and L698 adds "never exponent notation", only implied by Stage 9 examples.
* **Rationale & Recommendation**: Say the plan "summarises rules for orientation; the Stages win", and move "never exponent notation" into Stage 9's `amount` bullet.

### Run-on test-case paragraphs - Severity: Nit
* **ID:** `style-1-4`
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 740-755, 761-778`
* **Discrepancy Description**: Each test list is one 15+ line sentence; at L755 the scope of "with the exact message" is unclear.
* **Rationale & Recommendation**: Convert to bullets and state the exact-message requirement once for all `FatalError` cases.

### "ragged rows" undefined - Severity: Nit
* **ID:** `style-1-5` (also noted in `codebase-details` M4)
* **Reviewer Lens:** `egm-style`, `egm-codebase-details`
* **Affected Scope:** `Line 752`
* **Discrepancy Description**: Term not used in Stages 1-9.
* **Rationale & Recommendation**: "too few cells; extra blank cells accepted; extra non-blank cells rejected".

### "large values" unmeasurable - Severity: Nit
* **ID:** `style-1-6`
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Line 772`
* **Discrepancy Description**: No threshold or example.
* **Rationale & Recommendation**: Give a concrete case (e.g. 999999 minutes at 1000 -> `16666650.00`).

### Repeat exemption narrower than Stage 8 - Severity: Nit
* **ID:** `style-1-7`
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Line 777`
* **Discrepancy Description**: "exact in-export repeats not warned" omits cross-export copies (CUJ 3) that Stage 8 also exempts.
* **Rationale & Recommendation**: "exact repeats (same duplicate key, single-entry sessions, including CUJ 3 copies across exports) not warned".

### Vague or inconsistent wording - Severity: Nit
* **ID:** `style-1-8`
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 790, 803, 814-815, 818-819`
* **Discrepancy Description**: L790 "`--out` equal to an input path works" lacks an expected result; L803 "Short" is subjective; L814-815 "optional pyflakes if available" is uncheckable; L818-819 says `test_cli.py` runs `python -m tsinvoice`, conflicting with L782-783 (mostly via `main()`).
* **Rationale & Recommendation**: "exits 0 and `--out` holds the merged output"; delete "Short"; say "None" or name a required lint command; "runs CUJs through `main()` and at least one case via `python -m tsinvoice merge ...` in a subprocess".
