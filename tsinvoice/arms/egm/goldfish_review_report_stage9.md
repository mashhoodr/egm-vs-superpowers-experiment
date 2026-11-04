Status: resolved

# Goldfish Annotated Review Report — Stage 9 (Implementation Readiness), round 1

Source: `implementation_readiness_report.md`. Reviewers: egm-implementation-readiness, egm-codebase-details, egm-style (all completed). Findings: 1 Blocker, 6 Major, 19 Nit.

| id | Severity | AI Suggestion | Edit |
| --- | --- | --- | --- |
| codebase-details-1-1 | High | PROPOSE FIX | Detection mechanism specified: read once, non-strict pass for records + strict pass only to detect `unexpected end of data` (continuing past other errors); last pass-1 record becomes the bad row. Verified in a scratch script (Python 3, 5000 swallowed rows). Unterminated quote no longer described as a `csv.Error` |
| implementation-readiness-1-1 | Medium | PROPOSE FIX | New "Build phases" P1-P5, each gated on `python -m pytest` |
| codebase-details-1-2 | Medium | PROPOSE FIX | Field size limit raised to `sys.maxsize` before reading; test for >131072-char swallowed text |
| codebase-details-1-3 | Medium | PROPOSE FIX | conftest fixtures `write_file`, `run_cli`, `run_module` with exact signatures and return values (bytes support) |
| codebase-details-1-4 | Medium | PROPOSE FIX | Added named tests: decode error, missing out dir, temp cleanup, 0o644, symlink, missing sub-command/options, normalise (new `tests/test_model.py`), single-digit dates, exact warning texts, blank vs non-blank extra cells, field-limit case |
| style-1-1 | Medium | PROPOSE FIX | Countable coverage criterion (bullets, table rows, CUJs; tests cite them) |
| style-1-2 | Medium | PROPOSE FIX | Precedence lists Stages 3, 6, 8, 9 and argparse usage text |
| implementation-readiness-1-2 | Low | PROPOSE FIX | OutputRow field types |
| implementation-readiness-1-3 | Low | PROPOSE FIX | `ArgumentTypeError("expected NAME=PATH")` |
| implementation-readiness-1-4 | Low | PROPOSE FIX | Reader test asserts returned warnings, not an exit code |
| implementation-readiness-1-5 | Low | PROPOSE FIX | Rates row check order stated |
| implementation-readiness-1-6 | Low | PROPOSE FIX | Reason text is `str(exception)` |
| codebase-details-1-6 | Low | PROPOSE FIX | Decimal local context precision 50 |
| codebase-details-1-7 | Low | PROPOSE FIX | `allow_abbrev=False`; `--help` stdout exception stated |
| codebase-details-1-8 | Low | PROPOSE FIX | `add_subparsers(dest="command", required=True)` |
| codebase-details-1-10 | Low | PROPOSE FIX | Duration `re.fullmatch` regex; `30.` rejected |
| codebase-details-1-12 | Low | PROPOSE FIX | Writer settings pinned in Stage 9 |
| style-1-3 | Low | PROPOSE FIX | "Never exponent notation" moved into Stage 9; "never restates" claim removed |
| style-1-5 | Low | PROPOSE FIX | "ragged rows" replaced |
| style-1-6 | Low | PROPOSE FIX | Concrete large-value example |
| style-1-7 | Low | PROPOSE FIX | Exact-repeat test wording matches Stage 8 |
| codebase-details-1-5 | Low | DECLINE | An unterminated quote in the header line leaves no valid header; exit 2 `unrecognised header` is consistent with R1.11's header rule |
| codebase-details-1-9 | Low | DECLINE | fsync/power-loss out of scope; chmod already specified |
| codebase-details-1-11 | Low | DECLINE | Trimmed values; non-ASCII digits in dates are an accepted edge |
| style-1-4 | Low | DECLINE | Test lists kept as prose; each item is distinct |
| style-1-8 | Low | DECLINE | Minor wording |

Accepted fixes: 21 (1 High, 6 Medium, 14 Low). Declined: 5 (Low). Remaining High/Medium: 0.
