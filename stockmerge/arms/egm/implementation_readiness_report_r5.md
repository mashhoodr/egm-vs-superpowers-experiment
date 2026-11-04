# Goldfish Review Report

**Target:** `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers-p2/arms/egm/docs/designs/stockmerge.md` (`DetailedRange`: line 640 `## Detailed Implementation Plan` to end of file, line 1058/1059)

**Stage:** 9 (Implementation Readiness Test), egm-review-loop round 5
**GoldfishContext:** `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers-p2/arms/egm/BRIEF.md`

## Reviewer Status

| Reviewer | Status | Raw findings |
| --- | --- | --- |
| `egm-implementation-readiness` | completed | 0 Blocker, 1 Major, 6 Nit |
| `egm-codebase-details` | completed | 0 Blocker, 1 Major, 7 Nit |
| `egm-style` | completed | 0 Blocker, 0 Major, 11 Nit |

Each reviewer ran once (one instance). None failed or needed a retry.

## Severity Summary (after deduplication)

| Severity | Count |
| --- | --- |
| Blocker | 0 |
| Major | 1 |
| Nit | 21 |

Merged duplicates: the time-truncation Major (both reviewers), relative test paths, the `pyproject.toml` version, and the rule-to-test map gaps. Each merged finding uses the lowest id and lists the duplicate id.

Both technical reviewers confirmed that the plan follows the BRIEF contract (CLI shape, Format A/B headers, rules header, output header, exit 0, standard library only, Python 3.11+). Both traced the worked example, CUJ 1 and the R6.2/R6.5 move cases by hand, and all of them match the algorithms as specified.

## Prioritized Findings (Blockers -> Major -> Nits)

### egm-implementation-readiness-9.5-1: Test helper does not say whether it truncates times, so the R5.1 dedup test fails as written - Severity: Major
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details` (duplicate: `egm-codebase-details-9.5-1`; both rated it Major)
* **Affected Scope:** Lines 912-917 (`make_scan`), 1007 (R5.1 case "14:30:05 equals 14:30:59" in test_dedup), 1011 (R6.1 case "10:00:59 vs 12:00:30 links" in test_moves); see also lines 683, 224, 764-765.
* **Discrepancy Description**: `dedup` and `link_moves` work on `Scan.minute`. The readers truncate it to the minute with `to_minute`. `make_scan` passes `minute` straight through, so two scans built at :05 and :59 get different `scan_key`s and the R5.1 test fails. The implementer must then choose between truncating again in `dedup` (wrong layer), changing the helper, or rewriting the test. That breaks the Zero-Decision Rule. The R6.1 case passes either way (119 vs 120 min), so it does not test truncation at all.
* **Rationale & Recommendation**: Either state that `make_scan` applies `readers.to_minute` to `minute`, or move both truncation cases to `test_readers` (under R4.7) or to an end-to-end case in `test_cli`. Keep the `test_dedup`/`test_moves` cases on times already cut to the minute.

### egm-implementation-readiness-9.5-2: Map uses relative file names, but `run_cli` runs from the repo root - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details` (duplicate: `egm-codebase-details-9.5-2`)
* **Affected Scope:** Lines 908-911 (`run_cli`, `cwd=REPO_ROOT`); 983, 984, 986, 1030 (`shop=a.csv`, `" shop = a.csv "`, `--location back=b.csv`).
* **Discrepancy Description**: Fixtures write files under `tmp_path`, but the subprocess runs in the repo root. Relative names will not resolve, and `--out` could write into the repo.
* **Rationale & Recommendation**: State once that every CLI test passes absolute `tmp_path` paths for inputs, rules and `--out`. Alternatively, write map entries as `NAME=<path returned by write_file>`, or give `run_cli` a `cwd=tmp_path` parameter.

### egm-implementation-readiness-9.5-3: P6 README checkpoint asks for more than file entry 18 lists - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`
* **Affected Scope:** Line 654 vs lines 965-967.
* **Discrepancy Description**: The P6 checkpoint requires the README to show the worked example's command and output. File entry 18 does not include it in the README contents.
* **Rationale & Recommendation**: Add "the worked example's command, inputs and output" to entry 18.

### egm-implementation-readiness-9.5-4: Format B skip-reason strings not given - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`
* **Affected Scope:** Lines 753-756; line 997 (R4.4 case).
* **Discrepancy Description**: `parse_b_row` says "same order" but gives no `RowError` reason strings (for example, "blank SKU" vs "blank barcode"). The R4.4 test does not say which format it uses.
* **Rationale & Recommendation**: List the Format B reasons, or state that they are identical to the Format A strings.

### egm-implementation-readiness-9.5-5: Some spec rules have no test case - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details` (duplicate: `egm-codebase-details-9.5-8`)
* **Affected Scope:** Lines 983 (R1.2), 993 (R3.5), 1014 (R6.4), 1027-1030 (CUJs), 847-848; spec line 456 / plan line 897.
* **Discrepancy Description**: These have no test case:
  - R1.2: a location name that is not valid UTF-8.
  - R3.5: a rule with category `Uncategorised` (only `Move` is tested).
  - R6.4: the move number going to `M10000` past 9999.
  - Nothing printed to stdout on success.
  - CUJ 2 and CUJ 5 are not mapped by name; they are covered only through R6.3 and G4.
* **Rationale & Recommendation**: Add one case for each. Examples:
  - R1.2: pass `\xff` in the name as bytes via `os.fsencode`; expect exit 2 and "location name is not valid UTF-8".
  - CUJ 2: `-6 ABC` at 10:05 in back and `6 abc` at 11:40 in shop; expect both rows `Move` with id `M0001`.

### egm-implementation-readiness-9.5-6: `pyproject.toml` `[project]` table has no version - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details` (duplicate: `egm-codebase-details-9.5-5`)
* **Affected Scope:** Lines 955-960.
* **Discrepancy Description**: PEP 621 requires `version` or `dynamic = ["version"]`. There is also no `[build-system]` table. pytest ignores this, but `pip install -e .` or any build tool would reject the file.
* **Rationale & Recommendation**: Add `version = "0.1.0"`, and optionally `[build-system]` (setuptools>=61). Alternatively, drop `[project]` and keep only `[tool.pytest.ini_options]`.

### egm-implementation-readiness-9.5-7: Unhandled per-line `csv.Error` would abort the whole run - Severity: Nit (to verify)
* **Reviewer Lens:** `egm-implementation-readiness`
* **Affected Scope:** Lines 718-728 (`iter_records`), 889-895 (CLI backstop).
* **Discrepancy Description**: The plan does not say what happens if `next(csv.reader([line]), [])` raises `csv.Error` for one line. If it does, the backstop exits 2, which goes against G5 and "never lose a real scan". The reviewer thinks 3.11 cannot raise here, but has not confirmed it.
* **Rationale & Recommendation**: Check on 3.11. If any input can trigger it, specify that a per-line `csv.Error` becomes a `RowError`.

### egm-codebase-details-9.5-3: R1.1 usage-error format is wrong for unrecognised options - Severity: Nit
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Lines 982, 849-854 (spec lines 242-244).
* **Discrepancy Description**: With all required options present plus `--loc x`, the top-level parser reports `stockmerge: error: unrecognized arguments`, not `stockmerge merge: error:`. The test checks only exit 2, so it passes, but the R1.1 claim is wrong for this case.
* **Rationale & Recommendation**: Allow either prefix in R1.1, or note the parent-parser format.

### egm-codebase-details-9.5-4: Backstop error handler blames the last export file for errors that are not file errors - Severity: Nit
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Lines 889-895, 1023.
* **Discrepancy Description**: `current_path` is never reset after the read loop. An `OSError` raised in `dedup`, `link_moves` or `build_rows` is therefore reported against the last export path. The plan also does not say exactly where the `try` block starts.
* **Rationale & Recommendation**: Reset `current_path` after reading (to `"stockmerge"`), set it to `args.out` before `write_csv`, and state that the `try` wraps steps 3-9.

### egm-codebase-details-9.5-6: Warning text for patterns that start with `0` is sometimes false - Severity: Nit
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Lines 782-783 (spec R3.4, lines 294-296).
* **Discrepancy Description**: "cannot match leading zeros of a SKU" reads as if the pattern can never match. In fact `0` still matches `10`, and `01` matches `101`.
* **Rationale & Recommendation**: Reword to "pattern starts with 0; leading zeros are removed from SKUs before matching".

### egm-codebase-details-9.5-7: A lone `\r` ends a line under `newline=""` - Severity: Nit
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Lines 715-728 (spec R4.1 line 303, spec line 439).
* **Discrepancy Description**: Iterating lines with `newline=""` also splits on a lone `\r`. A stray CR in a note splits the row, and line numbers then differ from editors and `wc -l`. Separately, the spec's "1 is the header" is wrong when blank lines come before the header.
* **Rationale & Recommendation**: Record the lone-`\r` behaviour as accepted in Risks & Limits, or split only on `\n`. Change the spec to "LINE is the physical line number, counting from 1".

### egm-style-9.5-1: Size assumption stated as fact - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 720 (vs line 617).
* **Discrepancy Description**: "(stock-take files are small)" reads as a fact. Line 617 records it as a [builder] assumption.
* **Rationale & Recommendation**: Write "file size is assumed small; see Non-functional Requirements: Performance", or drop the parenthetical.

### egm-style-9.5-2: A non-action listed as a numbered step - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 867 (repeats line 713).
* **Discrepancy Description**: Step 1 of `main` only restates that `readers.py` raises the csv field size limit. It adds no action.
* **Rationale & Recommendation**: Remove the step and renumber.

### egm-style-9.5-3: Bullet under the wrong file - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 860-865.
* **Discrepancy Description**: The `cli.py` "Imports" bullet describes `writer.py` (`import os`, the monkeypatch target `stockmerge.writer.os.replace`).
* **Rationale & Recommendation**: Move that sentence into file 8 (lines 815-835).

### egm-style-9.5-4: Inconsistent letters for the summary counts - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 698, 880-882, 885, 1010 (definitions at lines 446-455).
* **Discrepancy Description**: The summary counts are R, S, D, M elsewhere, but line 882 uses lowercase `d`. Line 885 mixes `{R}`, `{d}`, `{S}` and `len(move_ids)//2`. Line 698 uses "the S count" with no pointer to its definition.
* **Rationale & Recommendation**: Use the same letters throughout, and add a pointer to the summary-line definition.

### egm-style-9.5-5: Undefined term "coverage gate", stated twice - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 976-978 and 1050-1052.
* **Discrepancy Description**: "Coverage gate" is not defined anywhere, and the rule appears in two places.
* **Rationale & Recommendation**: Keep it once, in the Verification Plan, worded as "Each `;`-separated case needs its own test function or parametrised case."

### egm-style-9.5-6: Rationale that does not follow - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 1049.
* **Discrepancy Description**: "Linting: none required (standard library only)". Linting has nothing to do with the dependency policy, so the reason does not support the conclusion.
* **Rationale & Recommendation**: Drop the reason, or give the real one.

### egm-style-9.5-7: Informal wording in a test spec - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 1015.
* **Discrepancy Description**: "5 min beats 119" is casual and leaves the unit off 119.
* **Rationale & Recommendation**: Write "(5 min is closer than 119 min)".

### egm-style-9.5-8: Two ways of writing rule ranges - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 1007 vs lines 703, 769, 791, 802, 817.
* **Discrepancy Description**: Line 1007 writes "R5.1–R5.3" with an en dash. Everywhere else uses "R4.1 to R4.12".
* **Rationale & Recommendation**: Use "R5.1 to R5.3".

### egm-style-9.5-9: Different phrasing for the same pointer - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 932, 936, 940, 944, 953.
* **Discrepancy Description**: The same pointer appears as "(see the rule-to-test map)" and as "(see the map)".
* **Rationale & Recommendation**: Use one phrase with a section link.

### egm-style-9.5-10: Section numbering "17a" and order - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 951-960 (phase table line 653).
* **Discrepancy Description**: "17a" breaks the numbering pattern. `test_writer.py` (file 17) also sits after file 16 instead of with the other unit tests.
* **Rationale & Recommendation**: Renumber in phase order and drop the suffix.

### egm-style-9.5-11: Attribution line that adds nothing - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 1058.
* **Discrepancy Description**: "*Drafted with EGM*" is a tooling credit, not engineering content.
* **Rationale & Recommendation**: Remove it, or move it to document metadata.
