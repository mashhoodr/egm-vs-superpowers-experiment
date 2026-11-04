Status: resolved

# Goldfish Annotated Review Report — Stage 9 (Implementation Readiness), round 4

**Target:** `docs/designs/stockmerge.md` (DetailedRange, line 640 to end at review time)
Source findings: `implementation_readiness_report_r4.md`. User decision (Elephant): **auto accept**.

| ID | Sev | Suggestion | Edit |
| --- | --- | --- | --- |
| codebase-9.4-1 backstop `where` | Medium | PROPOSE FIX | `getattr(exc,"filename",None) or current_path`; `strerror` avoids double path |
| codebase-9.4-2 import style | Medium | PROPOSE FIX | import style stated so monkeypatch targets are fixed |
| codebase-9.4-3 Warnings stream bound at import | Medium | PROPOSE FIX | `stream=None` resolves `sys.stderr` at write time |
| codebase-9.4-4 load_rules trimming / placeholder | Medium | PROPOSE FIX | fields trimmed first; message completed |
| codebase-9.4-5 location_arg texts | Medium | PROPOSE FIX | all four error texts given |
| impl-9.4-1 concrete test data | Medium | PROPOSE FIX | R6.2 (3 cases), R6.5, R4.11 split and worked-example file bytes given |
| 32 Nits | Low | DECLINE | wording |

Counts: 6 Medium fixed, 32 Low declined.
