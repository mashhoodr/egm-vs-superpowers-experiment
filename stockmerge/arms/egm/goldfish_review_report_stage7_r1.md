Status: resolved

# Goldfish Annotated Review Report — Stage 7 (Critic Review), round 1

**Target:** `docs/designs/stockmerge.md` (FeatureRange, lines 1-537)
Source findings: `critic_report.md`. Severity map: Blocker = High, Major = Medium, Nit = Low.
User decision (made by the Elephant, see `process_log.md`): **auto accept** (apply every PROPOSE FIX).

### design-1-1 No Risks & Limits section [`design`] - Severity: Medium
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Valid; the feature-spec standard asks for failure modes. Risks (a) and (b) follow from owner-settled rules and must be recorded as accepted, not changed.
*   ***Proposed Edit:*** new `## Risks & Limits` H2 after Alternatives: same-minute merge (owner rule, accepted), write-off linked as a move (owner rule, accepted; visible via `Move` + id), formula injection (accepted; output must keep scanned text), size assumption (up to ~100,000 rows, in memory), location typo (R1.4), leading-zero collision (owner rule), overwrite of input (R2.2), partial write (R9.3).

### design-1-2 Unclosed quote swallows rows [`design`] - Severity: Medium
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Verified on CPython 3.13 (same csv module behaviour as 3.11): a note opening `"` absorbs all later lines into one 4-field record, so scans vanish without a warning. Also raises `csv.Error` past the field size limit.
*   ***Proposed Edit:*** new R4.12: a record that spans more than one physical line gets a warning with the line range and each physical line is re-read on its own with quoting turned off, then parsed as a normal row. `csv.field_size_limit` raised so a long field cannot abort the run. Detailed plan updated.

### design-1-3 Very long quantity -> traceback [`design`] - Severity: Medium
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Verified: `int("9"*5000)` raises `ValueError` in 3.11+.
*   ***Proposed Edit:*** R4.8 limits quantity to at most 9 digits; longer values are skipped with a warning.

### style-1-1 I/O claim contradicts R2.1 [`style`] - Severity: Medium
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Proposed Edit:*** "Steps 3, 4 and 9 do file I/O; steps 5 to 8 are pure functions; only the CLI layer chooses the exit code."

### Nits (Low)
| ID | Suggestion | Note |
| --- | --- | --- |
| design-1-4 | PROPOSE FIX | reworded "input-related exit-2 conditions" |
| design-1-5 | PROPOSE FIX | G1 wording matches R5.4 |
| design-1-6 | PROPOSE FIX | usage errors use argparse format with `prog="stockmerge"`; `--help` exception |
| design-1-7 | PROPOSE FIX | rules file follows the same blank/empty rules as exports |
| design-1-8 | PROPOSE FIX | tags split |
| design-1-9 | PROPOSE FIX | stated as accepted in Risks & Limits |
| design-1-10 | PROPOSE FIX | `[0-9]` |
| design-1-11 | DECLINE | single-user local tool; temp-file mode/symlinks out of scope |
| design-1-12 | PROPOSE FIX | Ctrl-C listed as a non-goal |
| structural-1-1 | PROPOSE FIX | Additional Resources / Future Improvements promoted to H2 |
| structural-1-2 | PROPOSE FIX | links |
| structural-1-3 | PROPOSE FIX | `#### Step N` headings |
| structural-1-4 | DECLINE | follows the EGM template's rule placement |
| structural-1-5 | PROPOSE FIX | re-wrapped with style-1-4 |
| structural-1-6 | PROPOSE FIX | block labelled as a summary |
| style-1-2, 1-3, 1-4, 1-5, 1-6, 1-7, 1-8, 1-9, 1-10, 1-11, 1-12 | PROPOSE FIX | wording |
| style-1-13 | PROPOSE FIX | "folder" throughout; "copy"/"duplicate" glossary entry |

Counts: 4 Medium fixed, 25 Low fixed, 2 Low declined, 0 contested, 0 escalated.
