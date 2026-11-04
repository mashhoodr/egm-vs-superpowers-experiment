Status: resolved

# Goldfish Annotated Review Report — Stage 9 re-audit (round 2)

Source: `implementation_readiness_report_r2.md`. Reviewers: all 3 completed. Findings: 0 Blocker, 6 Major, 9 Nit.

| id | Severity | AI Suggestion | Edit |
| --- | --- | --- | --- |
| implementation-readiness-2-1 | Medium | PROPOSE FIX | Helper returns `(start_line, cells, unterminated)`; unterminated records never dropped as blank; check (0) first; `header_cells` None for no non-blank record; unterminated header → unrecognised header; tests (a)-(c) |
| implementation-readiness-2-2 | Medium | PROPOSE FIX | Two-pass replaced by the sentinel method (one non-strict parse of `text + "\n" + SENTINEL`); both reviewer counter-examples verified in a scratch script and added as tests |
| implementation-readiness-2-3 | Medium | PROPOSE FIX | Text handoff pinned (`open(..., newline="").read()`, `io.StringIO(text, newline="")`); physical line defined; CRLF / bare CR / U+2028 tests |
| codebase-details-2-1 | Medium | PROPOSE FIX | Field limit `min(sys.maxsize, 2**31 - 1)` |
| codebase-details-2-2 | Medium | PROPOSE FIX | Writer: `mkstemp`, `chmod 0o644`, `open(fd, ..., newline="")`, close, `os.replace`, unlink on error |
| codebase-details-2-3 | Medium | PROPOSE FIX | `run_cli` imports `tsinvoice.cli` inside the fixture body |
| codebase-details-2-4 | Low | PROPOSE FIX | Write error reason is `e.strerror or e` |
| style-2-1 | Low | PROPOSE FIX | "where it differs" |
| style-2-2 | Low | PROPOSE FIX | Stage 9 states the `--help` stdout exception |
| style-2-4 | Low | PROPOSE FIX | 131072 explained as the csv default limit |
| style-2-6 | Low | PROPOSE FIX | "none required" |
| implementation-readiness-2-4 | Low | DECLINE | Absurd sizes (>48-digit rates, >4300-digit durations); durations already fall to a ValueError bad row |
| style-2-3 | Low | DECLINE | Test lists stay as prose |
| style-2-5 | Low | DECLINE | Repetition is harmless |
| style-2-7 | Low | DECLINE | Provenance marker is the template's |

Accepted fixes: 11 (6 Medium, 5 Low). Declined: 4 (Low). Remaining High/Medium: 0. Re-audit cap reached; Stage 9 closed.
