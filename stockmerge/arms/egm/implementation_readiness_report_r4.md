# Goldfish Review Report

**Target:** `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers-p2/arms/egm/docs/designs/stockmerge.md` (lines 640-1031, `## Detailed Implementation Plan` to end of file)
**Stage:** 9 (Implementation Readiness Test), egm-review-loop round 4
**GoldfishContext:** `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers-p2/arms/egm/BRIEF.md`

## Reviewer Status

| Reviewer | Status | Standard | Reported verdict |
| --- | --- | --- | --- |
| `egm-implementation-readiness` | completed | implementation-readiness-standard | Ready with fixes: 0 Blocker, 2 Major, 14 Nit |
| `egm-codebase-details` | completed | implementation-readiness-standard | No Blockers: 5 Major, 9 Nit |
| `egm-style` | completed | none | 0 Blocker, 0 Major, 17 Nit |

All three ran once, one instance each, and none needed a retry.

## Severity Summary (after deduplication)

| Severity | Count |
| --- | --- |
| Blocker | 0 |
| Major | 6 |
| Nit | 32 |

Severity rule: each finding keeps the severity its reviewer gave it. Where two reviewers raised the same issue at different severities, this report uses the higher one and says so.

## What the reviewers confirmed

- Both technical reviewers traced the worked example (lines 458-491) through the plan's `dedup`, `link_moves`, `output_order` and summary formula. Each got the same 4 data rows and the same summary line: `read 5, removed 1, skipped 0, linked 1, wrote 4`. The tie-break at 95 minutes goes to s1 record 0 through `scan_order`. CUJ 1 also traces correctly.
- The plan honours BRIEF.md in these points:
  - Python 3.11, standard library only, pytest.
  - The `python -m stockmerge merge` command and its flags.
  - The exact headers.
  - Exit code 0 on success.
- The standard-library usage checks out (csv, open, tempfile, os.replace, argparse, subprocess).
- The phases P1-P5 depend only on earlier phases, and every spec rule has an implementation step and an entry in the test map.

## Prioritized Findings (Blockers -> Major -> Nits)

### Blockers

None.

### Major

#### egm-codebase-details-9.4-1: The backstop handler can crash, and `where` is undefined - Severity: Major
* **Reviewer Lens:** `egm-codebase-details`. Also raised by `egm-implementation-readiness` as part of its Major 1.
* **Affected Scope:** Lines 878-881 and 1008
* **Discrepancy Description**:
  * The handler reads `exc.filename`, but only `OSError` has that attribute. `UnicodeError` and `csv.Error` do not, so the handler raises `AttributeError` and the user sees a traceback, which G5 forbids.
  * `where` is "updated before each file step", but the plan never says what it holds at the start or after reading ends. The G5 test raises inside `dedup`, so the message would name the last export, or print `None: boom`.
  * When `exc.filename` is set, `str(OSError)` already contains the path, so `{where}: {exc}` prints it twice.
* **Rationale & Recommendation**:
  * Use `getattr(exc, "filename", None)`.
  * Define the lifecycle of `where`: its starting value, the value it takes before `load_rules` and before each `read_export`, and the reset after reading.
  * Leave out the prefix when no path applies, or use a fixed `stockmerge` prefix.
  * When a filename is present, print `exc.strerror or exc` so the path appears once.

#### egm-codebase-details-9.4-2: Import style is unstated, and the G5 and R9.3 monkeypatch tests depend on it - Severity: Major
* **Reviewer Lens:** `egm-codebase-details` (Major M3). Also raised by `egm-implementation-readiness` as part of its Major 1.
* **Affected Scope:** Lines 834-883 (file 9, `cli.py`), 871, 1005, 1008
* **Discrepancy Description**:
  * `monkeypatch.setattr("stockmerge.cli.dedup", ...)` only takes effect if `cli.py` uses `from stockmerge.dedup import dedup`.
  * Patching `os.replace` in the R9.3 test only takes effect if `writer.py` uses `import os` and calls `os.replace`.
  * The plan fixes neither import.
* **Rationale & Recommendation**: List the exact import lines for `cli.py`: `dedup`, `link_moves`, `build_rows`, `write_csv`, `load_rules` and `read_export`. Do the same for `writer.py` (`import os`), and ideally for every module.

#### egm-codebase-details-9.4-3: The `Warnings` default stream is bound at import time - Severity: Major
* **Reviewer Lens:** `egm-codebase-details` rated it Major. `egm-implementation-readiness` rated it Nit (its Nit 1). This report uses the higher severity.
* **Affected Scope:** Line 691
* **Discrepancy Description**: `__init__(self, stream=sys.stderr)` takes `sys.stderr` as it was when the module was imported. Tests that read warnings through `capsys` will see nothing, and that includes the G5 test, which runs `main` in the same process.
* **Rationale & Recommendation**: Use `stream=None` and look up `sys.stderr` each time a warning is written.

#### egm-codebase-details-9.4-4: `load_rules` omits trimming and leaves a placeholder in a message - Severity: Major
* **Reviewer Lens:** `egm-codebase-details` rated it Major. `egm-implementation-readiness` rated it Nit (its Nit 2). This report uses the higher severity.
* **Affected Scope:** Lines 769-782
* **Discrepancy Description**:
  * Spec R3.2 says the pattern and the category are both trimmed. The plan only lower-cases the pattern, so a category written as `Spares ` would keep its trailing space.
  * The header error message ends in a literal `found: ...`.
  * The plan does not say whether the `Move`/`Uncategorised` comparison is case-sensitive.
* **Rationale & Recommendation**:
  * State `pattern = fields[0].strip().lower()` and `category = fields[1].strip()`.
  * State that the blank checks run on the trimmed values.
  * State that the comparison with `MOVE_CATEGORY`/`UNCATEGORISED` is exact and case-sensitive.
  * Write the message out in full, for example `found: {','.join(header)}`.

#### egm-codebase-details-9.4-5: `location_arg` error messages are only partly specified - Severity: Major
* **Reviewer Lens:** `egm-codebase-details` rated it Major. `egm-implementation-readiness` rated it Nit (its Nit 3). This report uses the higher severity.
* **Affected Scope:** Lines 838-843
* **Discrepancy Description**: The plan only gives the message for a value with no `=`. It gives no text for an empty name, an empty path, or a name that cannot be encoded. `name.encode` raises `UnicodeEncodeError`, and the plan does not say to catch it and convert it to `ArgumentTypeError`. Under the Zero-Decision Rule, the implementer should not have to invent these.
* **Rationale & Recommendation**: Give one exact string for each case, for example `empty location name in: <value>`, `empty path in: <value>` and `location name is not valid UTF-8`. Specify the try/except.

#### egm-implementation-readiness-9.4-1: Several test-map cases have no concrete data - Severity: Major
* **Reviewer Lens:** `egm-implementation-readiness` (its Major 2).
* **Affected Scope:** Lines 916-939 (test files 12-17 only point at the map), 653, 990, 997, 1000, 1015
* **Discrepancy Description**:
  * R6.2, third case (line 997): "negatives in scan order decide which takes a shared partner" gives no rows.
  * R6.5 (line 1000): "the N1/P1/P2/N2 case" gives no times, quantities or locations.
  * R4.11 (line 990): one case is listed under two files, and the plan does not say which file tests which part.
  * Worked example (lines 653, 1015): the plan says the output must match "exactly", but the inputs are only summarised. The `""` notes and the spaces after commas are not real file bytes.
* **Rationale & Recommendation**:
  * Give explicit rows for R6.2 case 3 and R6.5. The reviewer suggests: N1 shop -5 X 10:00, N2 shop -5 X 10:30, P1 back +5 X 10:10, P2 back +5 X 11:50. For R6.5, use P2 at 12:15.
  * Give the exact contents of `b.csv`, `s1.csv` and `s2.csv`, header rows included.
  * Split R4.11: `test_moves` covers "never a move" and `test_cli` covers "categorised".

### Nits

#### egm-codebase-details-9.4-6: `pyproject.toml` has no version and no build-system - Severity: Nit
* **Reviewer Lens:** `egm-codebase-details`. Also raised by `egm-implementation-readiness` (its Nit 7).
* **Affected Scope:** Lines 944-946
* **Discrepancy Description**:
  * A `[project]` table with no `version` is invalid PEP 621 metadata, so `pip install .` fails.
  * There is no `[build-system]` table.
  * The `pythonpath` ini option needs pytest 7 or later, and the plan does not pin a pytest version.
* **Rationale & Recommendation**: Add `version = "0.1.0"` and state "pytest >= 7".

#### egm-codebase-details-9.4-7: The R1.2 test path resolves against the repo root - Severity: Nit
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Line 969, together with line 897
* **Discrepancy Description**: `run_cli` uses `cwd=REPO_ROOT`, so the argument `" shop = a.csv "` looks for `a.csv` in the repo root, not in `tmp_path`.
* **Rationale & Recommendation**: Inside the quoted argument, use the absolute path that `write_file` returns, with spaces around it.

#### egm-codebase-details-9.4-8: Usage-error prefix differs from R1.1 for unknown options - Severity: Nit
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Line 968 (spec lines 242-243)
* **Discrepancy Description**: An unknown option such as `--loc` is reported by the top-level parser (`stockmerge: error: unrecognized arguments`), not in the `stockmerge merge: error:` form. The test still passes because it only checks exit code 2.
* **Rationale & Recommendation**: Loosen the wording of R1.1, or note the exception.

#### egm-codebase-details-9.4-9: Format A accepts non-ASCII digits, and Format B rejects them - Severity: Nit
* **Reviewer Lens:** `egm-codebase-details`. Also raised by `egm-implementation-readiness` (its Nit 13).
* **Affected Scope:** Line 746 (compare lines 705-708)
* **Discrepancy Description**: `strptime` matches Unicode digits, while R4.6 rejects them for Format B times and for quantities. The spec says nothing about Format A, so the gap starts in the spec.
* **Rationale & Recommendation**: Check for ASCII digits before calling `strptime`, or document that Format A accepts them by choice.

#### egm-codebase-details-9.4-10: Error text can read "None" - Severity: Nit
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Lines 713-715
* **Discrepancy Description**: An `OSError` raised without an errno has `strerror` set to `None`, which gives `cannot read file: None`.
* **Rationale & Recommendation**: Use `exc.strerror or exc`.

#### egm-codebase-details-9.4-11: Warning counts and path text for R1.4/R1.5, and R2.2 wording - Severity: Nit
* **Reviewer Lens:** `egm-codebase-details`. Also raised by `egm-implementation-readiness` (its Nit 4).
* **Affected Scope:** Lines 860-867
* **Discrepancy Description**:
  * The plan does not say how many warnings print when three names fold to the same text, or when one path appears under several names. A path repeated this way can print duplicate R1.5 warnings.
  * It does not say which spelling of `{path}` the message shows.
  * The R2.2 message says "is also an input file" even when `--out` matches the rules file.
* **Rationale & Recommendation**:
  * Define one warning per unordered pair of distinct names, in first-seen order.
  * Print the path as it was given for the earlier export.
  * Adjust the R2.2 wording so it fits the rules-file case.

#### egm-codebase-details-9.4-12: A lone CR inside a quoted note splits the record - Severity: Nit
* **Reviewer Lens:** `egm-codebase-details`. Also raised by `egm-implementation-readiness` (its Nit 13).
* **Affected Scope:** Line 720 (also lines 713-721)
* **Discrepancy Description**: With `newline=""`, iterating the file also splits on a bare `\r`. A bare CR inside a note therefore splits the record, and the line numbers in warnings shift.
* **Rationale & Recommendation**: Add one sentence that accepts this behaviour, or list it under Risks & Limits.

#### egm-codebase-details-9.4-13: Gaps in the rule-to-test map - Severity: Nit
* **Reviewer Lens:** `egm-codebase-details`. The first item was also raised by `egm-implementation-readiness` (its Nit 10).
* **Affected Scope:** Lines 960-1015 (spec lines 356-358 and 449)
* **Discrepancy Description**: These cases have no test:
  * The R4.12 note that contains a real line break, where each continuation line is skipped with a warning.
  * The summary counts leaving out rows skipped from the rules file.
  * G6 for a bad rules header.
  * `scan_key`, `input_order`, `scan_order` and `output_order` in `test_model`.
* **Rationale & Recommendation**: Add a map entry for each. For R4.12, a quoted note over 2 lines should give the first line as a scan and one malformed warning for line 2.

#### egm-implementation-readiness-9.4-2: There are two ways to use `make_scan` - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`
* **Affected Scope:** Lines 898-903
* **Discrepancy Description**: `make_scan` is both a plain function in `conftest.py` and a fixture. Importing it from conftest relies on pytest adding that folder to `sys.path`.
* **Rationale & Recommendation**: State that tests use only the `scan_factory` fixture.

#### egm-implementation-readiness-9.4-3: Temp-file cleanup can reference an unbound name - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`
* **Affected Scope:** Lines 830-832
* **Discrepancy Description**: If `NamedTemporaryFile` fails, "remove the temporary file if it exists" refers to a variable that was never assigned.
* **Rationale & Recommendation**: Set `tmp = None` before the `NamedTemporaryFile` call.

#### egm-implementation-readiness-9.4-4: The README checkpoint and the README contents disagree - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`
* **Affected Scope:** Line 654 compared with lines 951-953
* **Discrepancy Description**: The P6 checkpoint requires the README to show the worked example's command and output. File 18's Proposed Changes leave that out, and the full command line is never written anywhere in the doc.
* **Rationale & Recommendation**: Add the worked example to file 18 and write the command out in full.

#### egm-implementation-readiness-9.4-5: The encoding of subprocess stderr is not pinned - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`
* **Affected Scope:** Lines 894-897
* **Discrepancy Description**: The encoding of the child process's stderr depends on the locale, but `run_cli` decodes it as UTF-8.
* **Rationale & Recommendation**: Pass `env={**os.environ, "PYTHONUTF8": "1"}`.

#### egm-implementation-readiness-9.4-6: A test case is filed under the wrong rule - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`
* **Affected Scope:** Line 974
* **Discrepancy Description**: "`--out` in a missing folder" is filed under R2.2, but it tests R9.3 (creating the temporary file fails).
* **Rationale & Recommendation**: Move the case to R9.3, or tag it R2.2/R9.3.

#### egm-implementation-readiness-9.4-7: CUJ 2 and CUJ 5 are not named in the test map - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`
* **Affected Scope:** Lines 1012-1014
* **Discrepancy Description**: Only CUJ 1, 3 and 4 have rows in the map.
* **Rationale & Recommendation**: Add rows for CUJ 2 and CUJ 5. For CUJ 2: `-6 ABC` at 10:05 back and `6 abc` at 11:40 shop should give a Move with M0001.

#### egm-implementation-readiness-9.4-8: The repo root is never stated - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`
* **Affected Scope:** Lines 656-958
* **Discrepancy Description**: The repo root is only implied (as `arms/egm/`) by the `../../BRIEF.md` link.
* **Rationale & Recommendation**: State the repo root explicitly.

#### egm-style-9.4-1: The size claim is unverified - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 718
* **Discrepancy Description**: "(stock-take files are small)" is stated as fact, but it rests only on the assumption at line 617.
* **Rationale & Recommendation**: Say that the size is assumed and refer to Non-Functional Requirements, Performance, or remove the parenthetical.

#### egm-style-9.4-2: A step in the `main` algorithm does nothing - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 856
* **Discrepancy Description**: Step 1 is a note, not an action.
* **Rationale & Recommendation**: Remove step 1 and renumber, or move the note after the list.

#### egm-style-9.4-3: The coverage definition is stated twice - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 962-964 and 1022-1024
* **Rationale & Recommendation**: Keep the definition in one place and refer to it from the other.

#### egm-style-9.4-4: "Coverage gate" is undefined - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 964
* **Rationale & Recommendation**: Refer to the Test Coverage Requirement in the Verification Plan by name.

#### egm-style-9.4-5: The reason given for skipping linting does not follow - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 1021
* **Rationale & Recommendation**: State "none" on its own, or give the real reason.

#### egm-style-9.4-6: The Compilation/Build entry mixes "none" with a check - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 1019
* **Rationale & Recommendation**: Write "No build step. Smoke check: `python -m stockmerge merge --help` exits 0."

#### egm-style-9.4-7: Cross-references to "the Technical Plan" are vague - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 653, 1006, 1015
* **Rationale & Recommendation**: Refer to the "Worked example (dedup, moves, order)" subsection (line 458) by name.

#### egm-style-9.4-8: "Messages table" is an informal reference - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 836
* **Rationale & Recommendation**: Use the heading name, "Messages and exit codes" (line 423).

#### egm-style-9.4-9: The P4 checkpoint gives no command - Severity: Nit
* **Reviewer Lens:** `egm-style`. Also raised by `egm-codebase-details` (its Nit 9).
* **Affected Scope:** Line 652 (compare lines 649-651)
* **Rationale & Recommendation**: Write `python -m pytest tests/test_dedup.py tests/test_moves.py` passes.

#### egm-style-9.4-10: The file list numbering and order are inconsistent - Severity: Nit
* **Reviewer Lens:** `egm-style`. Also raised by `egm-codebase-details` (its Nit 9) and `egm-implementation-readiness` (its Nit 14).
* **Affected Scope:** Lines 932-946
* **Discrepancy Description**: The list has an entry numbered "17a" (line 941), and `test_writer.py` comes after `test_cli.py`.
* **Rationale & Recommendation**: Renumber 1-20 in order, with no letter suffix.

#### egm-style-9.4-11: The entries for test files are incomplete - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 916-939
* **Discrepancy Description**: Entries 12-17 have no "Proposed Changes" field, and "(see the map)" is shorthand for the map's heading.
* **Rationale & Recommendation**: Add a "Proposed Changes" field to each entry and use the full heading name, "Rule-to-test map".

#### egm-style-9.4-12: "Glossary helpers" is a misnomer - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 911
* **Rationale & Recommendation**: Write "Unit tests for `model.py` helpers".

#### egm-style-9.4-13: Rule ranges are written two ways - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 992 (compare lines 701, 767, 788, 799, 814)
* **Rationale & Recommendation**: Use either the en dash form or "to" throughout.

#### egm-style-9.4-14: "Backstop" is undefined jargon - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 878 and 1008 (also line 432)
* **Rationale & Recommendation**: Describe the handler plainly, or add "backstop" to the Glossary.

#### egm-style-9.4-15: "Accepted" in the symlink clause is unclear - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 828-829
* **Rationale & Recommendation**: Write "This is a known limitation: the symlink is replaced, not followed."

#### egm-style-9.4-16: The summary symbol S is not defined locally - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 696-697 and 869-870
* **Rationale & Recommendation**: At line 697, write "the skipped-row count (S in the summary line)".

#### egm-style-9.4-17: "Repo hygiene" is informal wording - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 957
* **Rationale & Recommendation**: Write "Excludes Python and pytest cache files from version control."
