Status: resolved

# Goldfish Annotated Review Report — Stage 9 (Implementation Readiness), round 2

**Target:** `docs/designs/stockmerge.md` (DetailedRange, lines 640-995 at review time)
Source findings: `implementation_readiness_report_r2.md`. Blocker = High, Major = Medium, Nit = Low.
User decision (made by the Elephant): **auto accept**.

| ID | Sev | Suggestion | Edit |
| --- | --- | --- | --- |
| impl-9.2-1 P6 checkpoint | Medium | PROPOSE FIX | P6 checkpoint is now checkable (pytest passes; README lists [builder] IDs and worked example) |
| impl-9.2-2 test gaps | Medium | PROPOSE FIX | map rows for R5.6, G5 backstop, warning line numbers, invalid UTF-8 header/rules row, R2.2 variants, CUJ 1/3/4; file 6 scope R5.1-R5.6 |
| codebase-9.2-1 cleanup test vacuous | Medium | PROPOSE FIX | `tests/test_writer.py` monkeypatches `os.replace` to fail after the temp file exists |
| impl-9.2-3 permissions/symlink | Medium | PROPOSE FIX | mode copied from existing `--out` or `0o666 & ~umask`; symlink replaced (accepted, stated) |
| codebase-9.2-2 conftest | Medium | PROPOSE FIX | `REPO_ROOT`, fixtures, `encoding="utf-8"`, `pythonpath = ["."]` |
| style-9.2-1 coverage counting | Medium | PROPOSE FIX | gate counts cases |
| 20 Nits | Low | DECLINE | message wording / small gaps; recorded in the reviewer report |

Counts: 6 Medium fixed, 20 Low declined.
