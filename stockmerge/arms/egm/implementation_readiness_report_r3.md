# Goldfish Review Report

**Target:** `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers-p2/arms/egm/docs/designs/stockmerge.md` (`Lines 640-1021`, Detailed Implementation Plan)
**Stage:** 9 (Implementation Readiness Test), egm-review-loop round 3
**GoldfishContext:** `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers-p2/arms/egm/BRIEF.md`

## Reviewer Status

| Reviewer | Status | Standard | Own verdict |
| --- | --- | --- | --- |
| `egm-implementation-readiness` | completed | implementation-readiness-standard | READY with minor fixes (0 Blocker, 0 Major, 13 Nit) |
| `egm-codebase-details` | completed | implementation-readiness-standard | Pass with 1 Major, 12 Nit |
| `egm-style` | completed | none | No Blockers; 2 Major, 12 Nit |

All reviewers ran in one instance each. None failed or needed a retry.

## Severity Summary (after deduplication)

| Severity | Count |
| --- | --- |
| Blocker | 0 |
| Major | 3 |
| Nit | 22 |

Severity rule: where reviewers gave the same finding different severities, this report uses the higher one and records the disagreement.

Reviewers checked these and found them correct: the worked example traced by hand (N=2 dedup, the M0001 tie-break to s1 record 0, `42` sorted before `abc`, summary R=5 D=1 S=0 M=1 W=4); CUJ 1; the dedup count algorithm; the `minutes_between` arithmetic; the move tie-break; the unclosed-quote path; the BRIEF CLI, input-header and output-header contract; and the phase dependency order.

## Prioritized Findings (Blockers -> Major -> Nits)

### egm-codebase-details-9.3-1: `Scan` field order and types not set, and no test factory for `Scan` - Severity: Major
* **Reviewer Lens:** `egm-codebase-details` (Major); `egm-implementation-readiness` also raised it (Nit, item 10)
* **Affected Scope:** `Lines 676-678`, `883-899`, `916-922`, `814-817`
* **Discrepancy Description**: File 3 defines `Scan` only as "the fields in the record-type table". That table (spec lines 218-227) gives meanings, not Python types or field order, and lists `path`/`line` in one row. `conftest.py` has no helper for building `Scan` objects, so `test_dedup`, `test_moves` and any `build_rows` unit test must build nine-field records by hand. The implementer has to design both the record layout and the test helper. This breaks the Zero-Decision Rule.
* **Rationale & Recommendation**: List the fields in order with types: `location: str, arg_index: int, record_no: int, path: str, line: int, minute: datetime, sku: str, sku_norm: str, qty_each: int`. Add a `make_scan(...)` factory to `conftest.py` that works out `sku_norm` with `normalise_sku` and accepts a time string or a datetime for `minute`. State that `test_dedup` and `test_moves` use it.

### egm-style-9.3-1: Coverage gate counts "cases" in one place and "rows" in another - Severity: Major
* **Reviewer Lens:** `egm-style` (Major); `egm-implementation-readiness` also raised it (Nit, item 8)
* **Affected Scope:** `Lines 954-956`, `1014-1015`
* **Discrepancy Description**: Line 956 says "The coverage gate counts cases, not rows." Line 1014 says "every row of the rule-to-test map has a test". Under the second wording, a row with seven cases (for example R6.1) passes with one test.
* **Rationale & Recommendation**: Use one wording in both places, for example at line 1014: "every case (each `;`-separated item) in the rule-to-test map has its own test function or parametrised case."

### egm-style-9.3-2: `iter_records` is described as both streaming and fully read - Severity: Major
* **Reviewer Lens:** `egm-style` (Major); `egm-implementation-readiness` (Nit, item 13) and `egm-codebase-details` (Nit, item 8) raised the type mismatch
* **Affected Scope:** `Lines 714-724`
* **Discrepancy Description**: The signature returns an `Iterator` and the text says the function "reads physical lines one at a time" and "yields" records. Lines 723-724 then say the file is read fully into a list before returning. The two statements disagree on whether the result is lazy. "So the file is closed" gives a consequence where the requirement should be stated, and "first value / second value" makes the reader work out tuple positions.
* **Rationale & Recommendation**: State it directly: "Reads the whole file, closes it, and returns `(header, records)`, where `records` is a list of `(line_no, fields)` for each non-blank record after the header." Type it as `tuple[list[str], list[tuple[int, list[str]]]]`.

### egm-implementation-readiness-9.3-1: Rules header error message ends in a literal `...` - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** `Line 772`
* **Discrepancy Description**: The text after "found:" is a placeholder, unlike the export header error at line 732.
* **Rationale & Recommendation**: `f"{path}: rules header must be pattern,category, found: {','.join(header)}"`.

### egm-implementation-readiness-9.3-2: `load_rules` does not say to trim the pattern and category - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** `Lines 767-780` (spec R3.2, line 288)
* **Discrepancy Description**: R3.2 says both cells are trimmed, but the plan has no `strip()`. Untrimmed patterns never match, and untrimmed categories put spaces into `inv.csv`. The plan also does not say whether lower-casing comes before or after trimming.
* **Rationale & Recommendation**: Add "`pattern = fields[0].strip().lower()`, `category = fields[1].strip()`; the blank checks, the starts-with-0 check and the Move/Uncategorised check all use the trimmed values."

### egm-implementation-readiness-9.3-3: Backstop `where` is not defined outside file steps - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`; `egm-style` (item 5) flagged the unclear phrase "file step"
* **Affected Scope:** `Lines 876-879`, `1000`
* **Discrepancy Description**: During dedup, moves and `build_rows`, `where` still holds the last export path, or it may be unset. The G5 test makes `dedup` raise, which is exactly this case, so the message would name the wrong file or print `None`. "Each file step" does not list which operations update the variable, and the extent of the `try` block is not stated.
* **Rationale & Recommendation**: List the update points (rules path, each export path, output path). Set `where = None` after the read loop. When both `exc.filename` and `where` are None, print `stockmerge: error: {exc}`. State which steps the `try` wraps.

### egm-implementation-readiness-9.3-4: The G5 monkeypatch depends on a `cli.py` import style the plan never states - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** `Lines 853-870`, `1000`
* **Discrepancy Description**: Patching `stockmerge.cli.dedup` only works if `cli.py` uses `from stockmerge.dedup import dedup`.
* **Rationale & Recommendation**: List the imports in `cli.py` (`dedup`, `link_moves`, `read_export`, `load_rules`, `build_rows`, `write_csv`, `StockmergeError`, `Warnings`).

### egm-implementation-readiness-9.3-5: The `Warnings` default stream is fixed at import time - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** `Line 689`
* **Discrepancy Description**: `stream=sys.stderr` is evaluated when the module is imported. Warnings would then miss `capsys` and other in-process stderr swaps, while errors and the summary still go to the current stderr.
* **Rationale & Recommendation**: Use `stream=None` and look up `sys.stderr` each time a warning is written.

### egm-implementation-readiness-9.3-6: `run_cli` uses `cwd=REPO_ROOT`, so relative test paths resolve into the repo - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`
* **Affected Scope:** `Lines 892-895`, `961`, `963-964`
* **Discrepancy Description**: Map cases use relative names (`" shop = a.csv "`, `a=x.csv`, `shop=a.csv`). These resolve against the repo root, not `tmp_path`, and a relative `--out` would write into the repo.
* **Rationale & Recommendation**: Require absolute paths from `write_file` (for example `f" shop = {path} "`), or add a `cwd` parameter that defaults to `tmp_path` and set `PYTHONPATH=REPO_ROOT`.

### egm-implementation-readiness-9.3-7: The R1.5 same-file warning does not say which path to print and can repeat - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** `Lines 861-863`
* **Discrepancy Description**: `{path}` could be either spelling of the shared file. With three or more exports, the rule as written can warn more than once for the same pair of names.
* **Rationale & Recommendation**: Print the path of the export that comes first in argument order, and warn once per pair (i<j) in argument order.

### egm-implementation-readiness-9.3-8: The rule-to-test map has no case for some spec behaviours - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details` (union of both lists)
* **Affected Scope:** `Lines 952-1007`
* **Discrepancy Description**: These have no case:
  - R1.1: no subcommand, which should exit 2.
  - R1.2: a location name that is not valid UTF-8, which should be a usage error (skip on Windows).
  - R2.2: `--out` is a symlink to an input.
  - R4.2: the "no valid rows" warning when a file has data rows but every row is skipped.
  - R4.6: an impossible date such as `2026-02-30T10:00:00`.
  - R4.12: a quoted note with a real line break.
  - R6.4: move id `M10000` after 9999 moves.
  - A rules header with invalid UTF-8, which should exit 2 (messages table, line 433).
  - CUJ 2, which has no row of its own.
* **Rationale & Recommendation**: Add these cases so the gate covers every exit-2 row of the messages table and every CUJ.

### egm-implementation-readiness-9.3-9: `pyproject.toml` has no `version` and no minimum pytest version - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** `Lines 936-938`, `898-899`
* **Discrepancy Description**: PEP 621 requires `version` (or `dynamic`). The `pythonpath` ini option needs pytest 7.0 or later.
* **Rationale & Recommendation**: Add `version = "0.1.0"` and state "requires pytest >= 7.0".

### egm-implementation-readiness-9.3-10: Format A date parsing is laxer than Format B (optional) - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`
* **Affected Scope:** `Lines 744-745` (spec R4.5)
* **Discrepancy Description**: `strptime` accepts non-ASCII digits and a leading space. Format B rejects non-ASCII digits (lines 703-706).
* **Rationale & Recommendation**: Add an ASCII `re.fullmatch` pre-check, or record that the difference is accepted.

### egm-codebase-details-9.3-2: Most `location_arg` error messages are not written out - Severity: Nit
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** `Lines 836-841`
* **Discrepancy Description**: Only the missing-`=` message is given. The empty-name, empty-path and invalid-UTF-8 messages are left to the implementer.
* **Rationale & Recommendation**: Write all four strings.

### egm-codebase-details-9.3-3: `shutil.copymode` follows symlinks, against the "not followed" wording - Severity: Nit
* **Reviewer Lens:** `egm-codebase-details`; `egm-style` (item 6) flagged the "(accepted; not followed)" wording
* **Affected Scope:** `Lines 823-827`
* **Discrepancy Description**: When `out_path` is a symlink, the mode is copied from the link's target, so the link is partly followed. "Accepted" reads as a review decision rather than a description of behaviour.
* **Rationale & Recommendation**: Write "If `out_path` is a symlink, the link is replaced by a regular file; the target is not written." Also either state that the mode comes from the target, or use `os.lstat` and the umask default for symlinks.

### egm-style-9.3-3: File list numbering and order - Severity: Nit
* **Reviewer Lens:** `egm-style`, `egm-codebase-details`
* **Affected Scope:** `Lines 924-938`
* **Discrepancy Description**: `pyproject.toml` is numbered "17a" but belongs to P1. `test_writer.py` (17) comes after `test_cli.py` (16).
* **Rationale & Recommendation**: Renumber in phase order using whole numbers only.

### egm-style-9.3-4: A numbered step in `main` that is not a step - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Line 854`
* **Discrepancy Description**: Step 1 is a note in parentheses about what `main` does not do, and it repeats line 709.
* **Rationale & Recommendation**: Delete it and renumber, or move it to a sentence before the list.

### egm-style-9.3-5: The Format B note statement is repeated - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 750-752`
* **Discrepancy Description**: "(the note is not checked)" and "The note is not read." say nearly the same thing.
* **Rationale & Recommendation**: "The note is not validated or read (R4.10)."

### egm-style-9.3-6: Undefined shorthand "M" in a test case - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Line 987`
* **Discrepancy Description**: "(D = 1, M = 1)" uses M, which the reviewer did not find defined as a summary variable.
* **Rationale & Recommendation**: State the expected summary text instead (`removed 1 duplicates`, `linked 1 moves`).

### egm-style-9.3-7: The reason given for no linting does not follow - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Line 1013`
* **Discrepancy Description**: "Standard library only" is not a reason for having no linting.
* **Rationale & Recommendation**: Write "none", or give the real reason.

### egm-style-9.3-8: Test-file entries use different fields - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 908-931`
* **Discrepancy Description**: Entries 12-17 have no "Proposed Changes" field. They put "see the map" inside "Type / Scope".
* **Rationale & Recommendation**: Add `**Proposed Changes**: cases listed in the rule-to-test map for R...` to each of these entries.

### egm-style-9.3-9: Phase checkpoint wording differs - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 649-652`
* **Discrepancy Description**: P1-P3 give the exact pytest command. P4 says only "both test files pass".
* **Rationale & Recommendation**: "`python -m pytest tests/test_dedup.py tests/test_moves.py` passes."

### egm-style-9.3-10: Range notation differs, and the Rule column mixes IDs with labels - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 698, 765, 786, 797, 812, 984, 1000-1003`
* **Discrepancy Description**: Ranges are written both as "R4.1 to R4.12" and as "R5.1–R5.3". The Rule column mixes rule IDs with descriptive labels ("Warning format", "G5 backstop", "Summary").
* **Rationale & Recommendation**: Use one range style. Give each non-rule row its nearest rule ID and put the description in the case column.

### egm-style-9.3-11: Informal phrase "Repo hygiene" - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Line 949`
* **Discrepancy Description**: The phrase is informal and does not say what the file does.
* **Rationale & Recommendation**: "Excludes Python and pytest cache files from version control."

### egm-style-9.3-12: Tooling sign-off line - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 1019-1021`
* **Discrepancy Description**: "*Drafted with EGM*" is not design content.
* **Rationale & Recommendation**: Remove it or move it to the document metadata.
