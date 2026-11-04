Status: resolved

# Goldfish Annotated Review Report — Stage 9 (Implementation Readiness), round 1

**Target:** `docs/designs/stockmerge.md` (DetailedRange, lines 640-906 at review time)
Source findings: `implementation_readiness_report.md`. Blocker = High, Major = Medium, Nit = Low.
User decision (made by the Elephant): **auto accept**. The plan section was rewritten as one edit.

| ID | Sev | Suggestion | Edit |
| --- | --- | --- | --- |
| 9.1-1 no phases | Medium | PROPOSE FIX | `### Phases` table P1-P6 with checkpoints |
| 9.1-2 parse_location format | Medium | PROPOSE FIX | `location_arg` is an argparse `type=` raising `ArgumentTypeError` -> argparse usage format, exit 2 |
| 9.1-3 same-file / name fold | Medium | PROPOSE FIX | `same_file`, `fold_name` defined; warning texts given |
| 9.1-4 who prints warnings | Medium | PROPOSE FIX | `Warnings.add` is the only printer; no count; S from `read_export` |
| 9.1-5 read_export vs iter_records | Medium | PROPOSE FIX | `iter_records` fully specified; `read_export` and `load_rules` both use it |
| 9.1-6 test plan gaps | Medium | PROPOSE FIX | rule-to-test map with inputs and expected values; `test_model.py` added |
| 9.1-7 Format B regex | Medium | PROPOSE FIX | `ISO_RE`/`WHOLE_RE` written out with `[0-9]`, `fullmatch` |
| 22 Nits | Low | PROPOSE FIX where covered by the rewrite (error texts, file list, temp-file prefix); rest DECLINE | |

Counts: 7 Medium fixed.
