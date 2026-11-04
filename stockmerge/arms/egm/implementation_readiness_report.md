# Goldfish Review Report

**Target:** `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers-p2/arms/egm/docs/designs/stockmerge.md` (`640-906`, `## Detailed Implementation Plan` to end)

**Stage:** 9 (Implementation Readiness Test), egm-review-loop round 1
**GoldfishContext:** `BRIEF.md` (fixed contract). All three reviewers found that the plan honours the contract.

## Reviewer Status

| Reviewer | Status |
| --- | --- |
| `egm-implementation-readiness` | completed |
| `egm-codebase-details` | completed |
| `egm-style` | completed |

## Summary

| Severity | Count |
| --- | --- |
| Blocker | 0 |
| Major | 7 |
| Nit | 22 |

When two or more lenses raised the same defect, it appears once and lists every lens that raised it. If the lenses gave different severities, the higher one is used and the difference is noted.

## Prioritized Findings (Blockers -> Major -> Nits)

### Major

### egm-implementation-readiness-9.1-1: The plan has no phases or checkpoints - Severity: Major
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 640-902
* **Discrepancy Description**: The standard's "Phasing & Checkpoints" section requires incremental phases, each leaving the code buildable and testable. The plan is a flat list of 18 files with one verification step at the end. It gives no build order, although `rules.py` (736-738) depends on `iter_records` in `readers.py`.
* **Rationale & Recommendation**: Add a Phases section. A suggested order is: model + package files + pyproject/conftest; readers + test_readers; rules + test_rules; dedup + moves + tests; writer; cli + `__main__` + test_cli; README/.gitignore. Each phase ends with a specific `python -m pytest ...` command that must pass.

### egm-implementation-readiness-9.1-2: `--location` errors from `parse_location` use the wrong error format - Severity: Major
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 794-795 (checked against spec R1.1/R1.2, lines 239-250, and the messages table, line 428)
* **Discrepancy Description**: R1.2 classes a missing `=`, an empty name, an empty path and an unencodable name as usage errors. R1.1 requires the argparse format for usage errors (`usage: stockmerge merge ...` / `stockmerge merge: error: ...`). The plan raises `StockmergeError`, so `main` prints `stockmerge: error: ...` with no usage line. The plan also does not say whether `parse_location` is a `type=` callable or is called after parsing, how the UTF-8 check is done, or whether the path gets the same check.
* **Rationale & Recommendation**: Choose one route and write it down. Either use `type=parse_location` and raise `argparse.ArgumentTypeError`, or call `merge_parser.error(msg)`. Specify the check as `name.encode("utf-8")` catching `UnicodeEncodeError`. Add a test that checks the usage-format stderr.

### egm-implementation-readiness-9.1-3: The same-file check (R2.2, R1.5) and the R1.4 name comparison are not specified - Severity: Major
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details` (codebase-details rated the R1.4 part Nit)
* **Affected Scope:** Lines 796-800 (checked against spec lines 254-274)
* **Discrepancy Description**: The plan defines no helper, module, signature or exception handling for the same-file test. The implementer must pick between `realpath`, `samefile` and `stat`, decide which exceptions count as "check failed", write the R2.2 error text, and write the R1.4 normalisation. `" ".join(s.lower().split())` collapses all whitespace, but the spec says runs of spaces. The plan also does not give the pair iteration order or the texts of the R1.4 and R1.5 warnings.
* **Rationale & Recommendation**: Add `same_file(a: str, b: str) -> bool`. It returns True if the `realpath`s are equal; otherwise, when both paths exist, it returns `os.path.samefile`; any `OSError` gives False. Give exact templates for the R2.2 error and the R1.4 and R1.5 warnings. Check pairs in argument order (i<j). List the comparisons: `--out` against every input and against the rules path.

### egm-implementation-readiness-9.1-4: It is unclear who prints warnings, so they may print twice - Severity: Major
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-style`, `egm-codebase-details` (codebase-details rated it Nit)
* **Affected Scope:** Lines 671-676 and 800-802
* **Discrepancy Description**: `Warnings.add` writes `stockmerge: warning: ...` to its stream immediately. `main` is also said to print "each warning ... to stderr as it is collected". Read literally, every warning prints twice. The plan also never says what `Warnings`' count is used for. The summary's S must count only skipped export rows. It must exclude rules-file warnings, command-line warnings and `no valid rows`.
* **Rationale & Recommendation**: State that `main` builds one `Warnings(sys.stderr)` and passes it down, and that only `Warnings.add` writes. Remove the extra printing from cli.py. Either drop the count or state that it is not S.

### egm-implementation-readiness-9.1-5: `read_export` and the shared `iter_records` helper overlap - Severity: Major
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-style`, `egm-codebase-details` (codebase-details rated it Nit)
* **Affected Scope:** Lines 684-705 and 735-739
* **Discrepancy Description**: `read_export` describes its own line loop: header detection, splitting each physical line, skipping blank lines and line numbering. The helper `iter_records(path, f)` is named only in a nested parenthetical inside the rules.py entry. The plan leaves four questions open: whether the helper yields the header, why it takes `path`, where the surrogate check runs (rules need every field checked, exports only the fields the format reads), and where "no header row" is raised.
* **Rationale & Recommendation**: Define `iter_records(f) -> Iterator[tuple[int, list[str]]]` in the readers.py entry. It yields every non-blank physical line, header included, with its 1-based line number. Both `read_export` and `load_rules` call `next()` on it to get the header and raise `StockmergeError(f"{path}: no header row")` when it is empty. Each caller runs its own surrogate check; for rules, any field with a surrogate skips the row with `not valid UTF-8`. Shorten lines 735-739 to refer to the helper.

### egm-implementation-readiness-9.1-6: The test plan misses several rules and gives no expected values - Severity: Major
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 820-873 and 899-900
* **Discrepancy Description**: Line 899 requires a test for every [owner] and [contract] rule. These rules and cases have no test:
  * R1.1: `--help` goes to stdout with exit 0; a missing `merge` subcommand; an abbreviated option is rejected.
  * R1.2: an empty path; a non-UTF-8 name.
  * R1.3: the same path twice for one name.
  * R1.4 and R1.5 warnings.
  * R2.2: `--out` equal to the rules file; a symlink; a hard link.
  * R3.2: a header-only rules file; a wrong field count; a rules file with no header row; a BOM in the rules file; an invalid byte in the rules header.
  * R4.1: an invalid byte in the Format B note keeps the row; an invalid byte in a header row is exit 2.
  * R4.2: the `no valid rows` warning when every row is skipped.
  * R4.10: the note is ignored.
  * R4.11: a zero quantity is categorised.
  * R6.4: `M10000`.
  * R9.3: the temporary file is removed when writing fails.
  * The fixed summary wording (`linked 1 moves`).
  * The worked example (spec 458-491).

  "Summary line counts" and "output order" give no expected values. There is no table mapping rule IDs to tests.
* **Rationale & Recommendation**: Add the missing cases and tag each with its rule ID. Add an end-to-end golden test of the worked example that checks the exact output bytes and the exact summary line. Add a table mapping rule IDs to tests.

### egm-implementation-readiness-9.1-7: The Format B time regex is not written out - Severity: Major
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details` (codebase-details rated it Nit)
* **Affected Scope:** Lines 715-718 (and 713 for `parse_whole`)
* **Discrepancy Description**: "regex from R4.6" points to a description, not a pattern. R4.6 requires ASCII digits only. `\d` matches Unicode digits, and `re.match` with `$` accepts a trailing newline.
* **Rationale & Recommendation**: Write the pattern out: `re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?", text.strip())`. Use `fullmatch` in `parse_whole` too.

### Nits

### egm-implementation-readiness-9.1-8: The row parsers leave trimming, error conversion, check order and reason strings open - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 689-690, 700-701, 706-714, 739, 797
* **Discrepancy Description**: The plan has these gaps:
  * It does not say to trim the Format A time and unit, although R4.5 and R4.9 require it and the test at 826 depends on it.
  * The conversion of `strptime` `ValueError` to `RowError` is stated only for Format B.
  * Format A `strptime` accepts non-ASCII digits and space-padded days, unlike R4.6 and R4.8.
  * The check order (field count, surrogate, SKU, time, quantity, unit) is not fixed, and that order decides which reason is reported.
  * Most reason strings are missing: malformed, blank SKU, bad time, bad unit, R1.4, R1.5, R3.4, R3.5 and open errors.
* **Rationale & Recommendation**: Strip every field and wrap every `ValueError` as `RowError`. Optionally add an ASCII pre-check regex for Format A. Add a table of check order and exact reason strings.

### egm-implementation-readiness-9.1-9: The csv field size limit contradicts the spec and sits in the wrong place - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 796-797, 804-805, 833
* **Discrepancy Description**: The limit is raised only in `main`, so unit tests that call `read_export` or `load_rules` directly use the default of 131072. The backstop example "a field over the csv size limit" contradicts R4.12 ("no field size limit"). The 5000-character test stays below the default limit, so it proves nothing.
* **Rationale & Recommendation**: Set the limit when `readers.py` is imported. Test with a field longer than 131072 characters. Drop the contradictory example.

### egm-implementation-readiness-9.1-10: `{raw}` in the unrecognised-header error is undefined - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`
* **Affected Scope:** Line 694
* **Discrepancy Description**: The plan does not say whether `{raw}` is the raw line, the list repr or the joined trimmed cells.
* **Rationale & Recommendation**: Specify one form, for example `",".join(trimmed_cells)`.

### egm-implementation-readiness-9.1-11: The source of each summary count is not stated - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 796-802
* **Discrepancy Description**: The plan does not map R, S, D, M and W to their sources, and does not say whether `main` asserts `W == R - S - D`.
* **Rationale & Recommendation**: State the mapping: R and S from `read_export` totals, D from `dedup`, M = `len(move_ids) // 2`, W = `len(rows)`.

### egm-implementation-readiness-9.1-12: `write_csv` leaves the temporary folder, permissions and cleanup open - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 778-783
* **Discrepancy Description**: For a bare `--out inv.csv`, "`dir` = folder of `out_path`" may be implemented as `dirname(...) or None`. That puts the temporary file in the system temp directory, where `os.replace` can fail across devices. `NamedTemporaryFile` creates the file with mode 0600, and `os.replace` carries that mode over to `--out`. If creating the temporary file fails, there is no file to remove.
* **Rationale & Recommendation**: Use `os.path.dirname(os.path.abspath(out_path))`. State the expected output permissions: accept 0600 or `chmod` to the umask default. Remove the temporary file only if it was created.

### egm-implementation-readiness-9.1-13: The test harness and pyproject leave setup details open - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 814-818, 875-880
* **Discrepancy Description**: The plan has these gaps:
  * It does not say how `run_cli` finds the repo root.
  * Helpers defined in `conftest.py` cannot be imported cleanly.
  * A bare `pytest` may fail to import `stockmerge` without `pythonpath`.
  * `[project]` has no `version`, which PEP 621 requires.
* **Rationale & Recommendation**: Use `Path(__file__).resolve().parents[1]` for the root. Make the helpers fixtures or move them to `tests/helpers.py`. Add `pythonpath = ["."]` and `version = "0.1.0"`.

### egm-implementation-readiness-9.1-14: The `main` signature is listed under `__main__.py` - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`
* **Affected Scope:** Lines 652-653
* **Discrepancy Description**: `main` is defined in cli.py (line 796), but its signature appears under the `__main__.py` entry.
* **Rationale & Recommendation**: Move the signature to the cli.py entry.

### egm-codebase-details-9.1-1: The subparser call is not exact - Severity: Nit
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Lines 789-793
* **Discrepancy Description**: The plan does not give `dest`. With `required=True` and no `dest`, some Python versions raise `TypeError` while formatting the missing-subcommand error.
* **Rationale & Recommendation**: Specify `add_subparsers(dest="command", required=True)`.

### egm-style-9.1-1: The `read_export` return signature appears twice and its values are unnamed - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 684, 703-704
* **Discrepancy Description**: The repeated signature adds nothing, and neither place says which int is which.
* **Rationale & Recommendation**: Delete the parenthetical and write "Returns `(scans, records_read, records_skipped)`".

### egm-style-9.1-2: The `read_export` paragraph is long and out of execution order - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 685-705 (over-long lines 690, 700, 704, 808, 831)
* **Discrepancy Description**: The UTF-8 rule comes before rows are introduced. The header is said to be read "with `csv.reader`" before the per-line split is explained. Several lines run past the wrap width the rest of the document uses.
* **Rationale & Recommendation**: Split the paragraph into sub-bullets in execution order: open, header, records, parse, result. Move the UTF-8 sentence to the parser bullets. Re-wrap the long lines.

### egm-style-9.1-3: "which skip the Format B note" is ambiguous - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 690
* **Discrepancy Description**: "Skip" elsewhere means skipping a row. Here it means a field is not checked.
* **Rationale & Recommendation**: Write "the check does not cover the Format B `note` field".

### egm-style-9.1-4: The filler word "anyway" - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 717
* **Discrepancy Description**: "(the fraction is dropped anyway)" is conversational.
* **Rationale & Recommendation**: Write "(fractional seconds are discarded; see `to_minute`)".

### egm-style-9.1-5: "minute difference in whole minutes" is redundant and repeated - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 765, 767
* **Discrepancy Description**: The phrase says "minute" twice and appears twice within three lines.
* **Rationale & Recommendation**: Define `d = abs(neg.minute - pos.minute)` in whole minutes once, then use `d <= MOVE_WINDOW_MINUTES` and `(d, scan_order)`.

### egm-style-9.1-6: The dedup counter step is ambiguous - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 751-753
* **Discrepancy Description**: In "keep a scan while its key's counter is below N, then increment", the reader cannot tell whether the counter goes up for every scan or only for kept ones, and "while" suggests a loop.
* **Rationale & Recommendation**: Write: "for each scan in input order: if `counter[key] < N[key]`, keep it; increment `counter[key]`", and state explicitly whether the increment applies to every scan or only to kept ones.

### egm-style-9.1-7: "messages table" does not match the heading it points to - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 787
* **Discrepancy Description**: The heading is "Messages and exit codes" (line 423).
* **Rationale & Recommendation**: Use the heading text.

### egm-style-9.1-8: Unnecessary "already" - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 792
* **Discrepancy Description**: In "argparse already exits 2", "already" adds no meaning.
* **Rationale & Recommendation**: Write "argparse exits 2 on usage errors".

### egm-style-9.1-9: The test lists are dense mixed-form run-ons with unverifiable shorthand - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 823-833, 847-851, 856-861, 866-873
* **Discrepancy Description**: Each list is one semicolon-separated sentence. Items switch between outcomes and bare topics. Some items are shorthand a reader cannot check: "2 vs 1 keeps 2", "10:00:59 and 12:00:30 link", "×12", "summary line counts".
* **Rationale & Recommendation**: Use one bullet per case, each giving the input and the expected result.

### egm-style-9.1-10: "the builder's calls" is jargon - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 887
* **Discrepancy Description**: "Calls" could be read as function calls.
* **Rationale & Recommendation**: Write "decisions made by the builder (R-IDs marked [builder])".

### egm-style-9.1-11: "Repo hygiene" is jargon - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 891
* **Discrepancy Description**: "Hygiene" is a metaphor and does not say what the file does.
* **Rationale & Recommendation**: Write "Excludes generated files from version control".

### egm-style-9.1-12: The Compilation/Build entry contradicts itself - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 896
* **Discrepancy Description**: "none; ... runs" says there is no build step, then gives a check.
* **Rationale & Recommendation**: Write "No build step. Check: `python -m stockmerge merge --help` exits 0".

### egm-style-9.1-13: The reason given for not linting does not follow - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 898
* **Discrepancy Description**: Being limited to the standard library at runtime does not rule out a linter.
* **Rationale & Recommendation**: Write "None." or give the actual reason.

### egm-style-9.1-14: Tool attribution footer - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 906
* **Discrepancy Description**: "*Drafted with EGM*" is not engineering content.
* **Rationale & Recommendation**: Remove it, or move it to the document metadata.
