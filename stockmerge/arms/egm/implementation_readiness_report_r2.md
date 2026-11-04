# Goldfish Review Report: Stage 9 Implementation Readiness, Round 2

**Target:** `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers-p2/arms/egm/docs/designs/stockmerge.md` (lines 640-995, `## Detailed Implementation Plan` to the end of the file)
**GoldfishContext:** `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers-p2/arms/egm/BRIEF.md`
**Standard:** `implementation-readiness-standard` (used by `egm-implementation-readiness` and `egm-codebase-details`)

## Reviewer Status

| Reviewer | Status | Raw counts (B / M / N) |
| --- | --- | --- |
| `egm-implementation-readiness` | completed | 0 / 3 / 10 |
| `egm-codebase-details` | completed | 0 / 4 / 1 grouped (12 items) |
| `egm-style` | completed | 0 / 3 / 12 |

Each reviewer ran as a single instance. None needed a retry.

## Consolidated Severity Breakdown

- Blocker: 0
- Major: 6
- Nit: 20

`egm-codebase-details` recomputed the worked example (5 output lines; summary read 5, removed 1, skipped 0, linked 1, wrote 4) and CUJ 1 using the plan's own algorithms. Both match the spec.

## Prioritized Findings (Blockers -> Major -> Nits)

### egm-implementation-readiness-9.2-1: The P6 checkpoint uses worked-example files that no phase creates - Severity: Major
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`, `egm-style` (all three flagged it as Major)
* **Affected Scope:** Lines 654 (P6 row), 653, 923-928 (README), 981, 656-933 (target file list)
* **Discrepancy Description**: The P6 checkpoint is "the README command runs on the worked-example files". No Target Files entry creates `b.csv`, `s1.csv`, `s2.csv` or the rules file (`42,Spares`). They exist only as a summary at lines 463-469, which does not give header rows, spacing or quoting. The tests build their inputs at runtime with `write_file`. The checkpoint also never says what "runs" means: exit 0, exact output, or just no traceback.
* **Rationale & Recommendation**: The implementer would have to choose the fixture paths and exact bytes, which breaks the Zero-Decision Rule. Add Create entries for `examples/b.csv`, `examples/s1.csv`, `examples/s2.csv` and `examples/rules.csv` with exact contents. Have the README command and the worked-example test in `test_cli` use them. State the pass condition, for example "exits 0 and writes the 5 lines in the worked example". Otherwise, change the checkpoint to use files the plan already creates.

### egm-implementation-readiness-9.2-2: The rule-to-test map leaves spec behaviours untested - Severity: Major
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`, `egm-style` (all three flagged it as Major)
* **Affected Scope:** Lines 935-981 (map), 988-989 (coverage rule), 911-914 (test_cli scope claims it covers the CUJs), 786 (file 6 scope label)
* **Discrepancy Description**: Line 988 defines coverage as "every row of the map has a test", so any behaviour without a row goes untested. These have no row:
  - R5.6: dedup runs before move matching.
  - The G5 backstop: other `OSError`/`UnicodeError`/`csv.Error` gives exit 2 (messages table lines 425-436; `main` lines 871-874), including how `where` is chosen.
  - Warning LINE numbers: physical line, header is line 1, blank lines still count (spec lines 109-111, 438-439). No row checks the full `stockmerge: warning: PATH:LINE: reason` string, or that `record_no` continues past skipped rows.
  - The summary with S > 0 (`W = R - S - D`, `skipped S rows`). CUJ 3 is never run end to end.
  - CUJ 1 end to end (Format A against Format B in two files for one location).
  - CUJ 4 through the CLI: the `unrecognised header` error text, with the existing `--out` left unchanged.
  - Invalid UTF-8 in an export header and in the rules header (exit 2). Invalid UTF-8 in a rules data row (skipped with `not valid UTF-8`, R3.2).
  - R1.2: a location name that cannot be encoded as UTF-8 (exit 2).
  - R2.2 variants: `--out` equal to the rules file, a symlink to an input, a hard link to an input.
  - R4.12: each continuation line of a note that contains a real line break is skipped with a warning.
  - R1.4 and R1.5 command-line warnings have no PATH prefix.
  - Output under a different `--location` order (G4 determinism).
  - The file 6 scope label (line 786) says "R5.1 to R5.4", but line 968 tests R5.5 in test_dedup, and R5.6 also belongs to that file.
* **Rationale & Recommendation**: Add one map row for each item above, giving the exact input, exit code, stderr substring and output bytes. Change line 786 to "R5.1 to R5.6". Example rows: "blank line 2 and a bad date on line 4 → `PATH:4: bad date: ...`"; "CUJ 3 files → exit 0, summary `read 3 rows, removed 0 duplicates, skipped 2 rows, linked 0 moves, wrote 1 rows`"; "backstop: monkeypatch `readers.open_text` to raise `OSError(5, 'I/O error', 'x.csv')` → returns 2, stderr `stockmerge: error: x.csv: ...`".

### egm-codebase-details-9.2-1: The R9.3 temp-file cleanup test always passes - Severity: Major
* **Reviewer Lens:** `egm-codebase-details` (Major). `egm-implementation-readiness` raised the same gap inside its coverage finding (Major).
* **Affected Scope:** Lines 978 (R9.3 row), 948, 818-825 (`write_csv`)
* **Discrepancy Description**: "no `.stockmerge-*.tmp` left" only tests something if a temp file was created and the cleanup then ran. Every exit-2 case in the map fails before step 9. The "`--out` in a missing folder" case (line 948) fails before the temp file is created. The cleanup and the `cannot write output` message in `write_csv` are never run, so the G6 guard has no real test.
* **Rationale & Recommendation**: Name a trigger. For example, point `--out` at an existing non-empty directory so `os.replace` raises. Expect exit 2, the directory unchanged, stderr containing `cannot write output`, and no `.stockmerge-*.tmp` in the parent folder. You can also add a unit test that patches `os.replace` to raise.

### egm-implementation-readiness-9.2-3: Output file permissions are not specified (temp file plus `os.replace`) - Severity: Major
* **Reviewer Lens:** `egm-implementation-readiness` (Major), `egm-codebase-details` (Nit). The reviewers disagreed, so this report uses the higher severity.
* **Affected Scope:** Lines 818-825 (`write_csv`)
* **Discrepancy Description**: `tempfile.NamedTemporaryFile` creates the file with mode 0600, and `os.replace` puts that file in place as `--out`. An existing 0644 `inv.csv` becomes owner-only after every run, and a new output ignores the umask. If `--out` is a symlink, the link itself is replaced rather than its target. Neither the spec nor the plan defines this behaviour, and the user can see it.
* **Rationale & Recommendation**: Choose one: (a) `os.chmod(tmp, 0o666 & ~umask)` before `os.replace`; (b) copy `st_mode` from the existing `--out`, or use the umask default if it does not exist; (c) accept 0600 and the symlink replacement explicitly in Risks & Limits.

### egm-codebase-details-9.2-2: Test helpers in conftest are not fully specified - Severity: Major
* **Reviewer Lens:** `egm-codebase-details` (Major). `egm-implementation-readiness` and `egm-style` flagged the `REPO_ROOT` and `read_out` parts as Nits.
* **Affected Scope:** Lines 878-886, 919-921
* **Discrepancy Description**:
  - `REPO_ROOT` is never defined.
  - The plan does not say whether `run_cli` and `read_out` are fixtures or plain functions imported from conftest.
  - The `subprocess.run` call gives no `text=True` or stderr encoding, which matters for backslash-escaped bad bytes (R4.1).
  - `read_out` does not say it uses `csv.DictReader`, or what encoding and newline it opens with.
  - `stockmerge` is importable only because `python -m pytest` adds the current directory to `sys.path`. A bare `pytest` run fails because `tests/` has no `__init__.py` and pyproject sets no `pythonpath`.
* **Rationale & Recommendation**: Define `REPO_ROOT = Path(__file__).resolve().parent.parent`. Make the helpers fixtures that return callables, or put them in `tests/helpers.py` with the import line. Specify `subprocess.run([...], cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8", errors="backslashreplace")`. Specify `read_out` as `open(path, encoding="utf-8", newline="")` with `csv.DictReader`. Add `pythonpath = ["."]` to `[tool.pytest.ini_options]`.

### egm-style-9.2-1: The rule-to-test map counts tests two ways - Severity: Major
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 937-938, 988-989
* **Discrepancy Description**: Line 937 says "Each line is one test (or one parametrised case)". Most rows hold several cases separated by semicolons (R1.1 has 3, R4.6 has 6). Line 988 requires only that "every row ... has a test", so a row with one test out of six cases passes the gate.
* **Rationale & Recommendation**: Replace both sentences with one definition: "Each case separated by `;` is one test or parametrised case. Every case must have a test."

### egm-implementation-readiness-9.2-4: Error message text is left as placeholders or repeats the filename - Severity: Nit
* **Reviewer Lens:** all three
* **Affected Scope:** Lines 772, 825, 871-874
* **Discrepancy Description**: `found: ...` (rules header) and `cannot write output: ...` leave the text to the builder. The backstop prints `{where}: {exc}`, and `str(OSError)` already contains the filename, so it appears twice.
* **Rationale & Recommendation**: Use `found: {','.join(header)}` and `{exc.strerror}` (or `exc.strerror or exc`), matching `open_text` at line 713.

### egm-implementation-readiness-9.2-5: `parse_b_row` gives no warning reason strings and does not match `parse_a_row` in structure - Severity: Nit
* **Reviewer Lens:** all three
* **Affected Scope:** Lines 738-752 (compare 743, 957-958)
* **Discrepancy Description**: "Same order" does not say whether a blank barcode reports `blank SKU` or `blank barcode`, or whether bad-date reasons quote the raw or the trimmed value. `parse_b_row` is prose, while `parse_a_row` is a numbered list.
* **Rationale & Recommendation**: Write `parse_b_row` as a numbered list with a quoted reason for each check. Use `"blank SKU"` for both formats.

### egm-implementation-readiness-9.2-6: `load_rules` does not specify trimming or case sensitivity - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 769-780
* **Discrepancy Description**: R3.2 requires both fields to be trimmed before the blank checks. The plan only says the pattern is "stored lower-cased". It does not say whether the `Move`/`Uncategorised` check is exact and case-sensitive.
* **Rationale & Recommendation**: State `pattern = fields[0].strip().lower()` and `category = fields[1].strip()` before the checks, and give the comparison rule.

### egm-implementation-readiness-9.2-7: The return type of `iter_records` contradicts its body - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-style`
* **Affected Scope:** Lines 714-724
* **Discrepancy Description**: The signature says `Iterator[...]`, but the body reads everything into a list first.
* **Rationale & Recommendation**: Declare `list[tuple[int, list[str]]]`, or rename the function to `read_records`.

### egm-implementation-readiness-9.2-8: The `Warnings` default stream is fixed when the class is defined - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Line 689
* **Discrepancy Description**: `stream=sys.stderr` as a default argument bypasses capsys or a monkeypatched stderr.
* **Rationale & Recommendation**: Use `stream=None`, then `self.stream = stream or sys.stderr`.

### egm-implementation-readiness-9.2-9: `pyproject.toml` `[project]` has no `version` - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 919-921
* **Discrepancy Description**: PEP 621 requires `version`, and there is no `[build-system]`. pytest ignores this, but `pip install .` fails.
* **Rationale & Recommendation**: Add `version = "0.1.0"`, or drop the `[project]` table.

### egm-implementation-readiness-9.2-10: The R1.5 duplicate-file warning details are not specified - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 856-858
* **Discrepancy Description**: The plan does not say which path is printed, how many warnings appear when one file is given under three or more names, or in what pair order.
* **Rationale & Recommendation**: Go through pairs in (i, j) argument order with i < j. Print export i's path as given. Warn once per name pair and resolved file.

### egm-implementation-readiness-9.2-11: Format A dates accept non-ASCII digits and extra whitespace - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 744-745
* **Discrepancy Description**: `strptime` matches Unicode `\d` and accepts any whitespace between date and time, while R4.6 and R4.8 are ASCII-only. No test covers this.
* **Rationale & Recommendation**: Check with `re.fullmatch(r"[0-9]{1,2}/[0-9]{1,2}/[0-9]{4} [0-9]{1,2}:[0-9]{2}", value)` before `strptime` and add a test row, or document the leniency.

### egm-implementation-readiness-9.2-12: The README content is vague - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`
* **Affected Scope:** Lines 926-928
* **Discrepancy Description**: "The list of [builder] rules" does not say whether to copy the rules or summarise them.
* **Rationale & Recommendation**: For example, "one line per [builder] rule, with its rule ID".

### egm-codebase-details-9.2-3: `location_arg` gives only one of its error messages - Severity: Nit
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Lines 831-836
* **Discrepancy Description**: Only the message for a missing `=` is given. The messages for an empty name, an empty path and a name that cannot be encoded are not.
* **Rationale & Recommendation**: Give all four messages.

### egm-codebase-details-9.2-4: `link_moves` "positive scans" should state `qty_each > 0` - Severity: Nit
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Lines 803-806
* **Discrepancy Description**: The plan does not state explicitly that a quantity of zero is never a move (R4.11).
* **Rationale & Recommendation**: Write `qty_each > 0`.

### egm-codebase-details-9.2-5: An unrecognised option is not reported in the `stockmerge merge:` usage format - Severity: Nit
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Line 942 (spec lines 242-244)
* **Discrepancy Description**: An unrecognised option such as `--loc` is reported by the top-level parser (`usage: stockmerge [-h] {merge} ...` / `unrecognized arguments`), not in the `stockmerge merge:` format the spec claims for all usage errors. The test checks only the `usage: stockmerge` prefix, so it passes anyway.
* **Rationale & Recommendation**: Change the spec wording, or note the difference.

### egm-codebase-details-9.2-6: Some readers test rows need exact input strings - Severity: Nit
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Lines 954-962
* **Discrepancy Description**: R4.6 "Arabic-Indic digits" does not give the string to use.
* **Rationale & Recommendation**: Give it, for example `"٢٠٢٦-03-05T14:30:12"`.

### egm-style-9.2-2: Placeholder notation is mixed - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 713, 732, 741, 745, 748, 772, 780, 825
* **Discrepancy Description**: The section uses `N`, `<value>`, `<c>`, `{path}` and `...` for the same purpose.
* **Rationale & Recommendation**: Use f-string `{name}` placeholders everywhere.

### egm-style-9.2-3: Step 1 of `main` does nothing - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 849 (repeats 709-710)
* **Discrepancy Description**: The step is a reminder that the csv field size limit is already raised, not an action.
* **Rationale & Recommendation**: Delete it and renumber, or make it an unnumbered note.

### egm-style-9.2-4: "where `where`" reads badly - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 872-874
* **Rationale & Recommendation**: Rename the variable (for example `current_path`), or rephrase the sentence.

### egm-style-9.2-5: Test files 12-16 have no "Proposed Changes" field - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 895-915
* **Rationale & Recommendation**: Add the field, or say once that the rule-to-test map takes its place.

### egm-style-9.2-6: Rule ranges are written two ways - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 966 ("R5.1–R5.3") against 699, 765, 786, 797 ("to")
* **Rationale & Recommendation**: Use "to" everywhere.

### egm-style-9.2-7: The reason given for skipping linting does not follow - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 987
* **Discrepancy Description**: "none required (standard library only)": being standard-library only says nothing about whether linting is needed.
* **Rationale & Recommendation**: Write "none", or give the real reason.

### egm-style-9.2-8: The heading and closing signature add nothing - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 656, 995
* **Discrepancy Description**: In "Target Files to Create/Modify", every entry is Create. "*Drafted with EGM*" is a tool signature, not content.
* **Rationale & Recommendation**: Rename the heading to "Files to Create". Drop the signature or move it into the metadata block.
