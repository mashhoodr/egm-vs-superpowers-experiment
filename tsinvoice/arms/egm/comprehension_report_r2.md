# Comprehension Report (Stage 6 re-audit)

**Target:** `docs/designs/tsinvoice.md` (FeatureRange 1-518, DetailedRange 519-765). Reviewer: `egm-comprehension` (direct). Status: completed.

**What this proposes**
A new standard-library Python 3.11 command-line tool, `python -m tsinvoice merge`. It reads every timesheet CSV export (desktop Format A or phone Format B, detected from the header) and the rates file before writing anything. Inside each tracker it removes exact duplicates, keeping the largest per-export count. It then joins entries with the same client and description where the next one starts 0 to 120 s after the previous one ends, choosing greedily in start order. Each session is rounded up to a multiple of 6 minutes and priced by the first matching substring rule, half-up in `Decimal`. The rows are sorted, joined rows get `S1..Sn` IDs, overlapping sessions for one client are warned about, and the output is written atomically. All warnings go to stderr in a fixed order. File, rates and usage errors exit with code 2 and leave `--out` unchanged. The detailed plan lays this out as cli, readers, core and writer modules plus pytest suites.

**How the existing system works, per this document**
There is no existing code; this is a new build. Today the owner exports CSVs from two apps every couple of weeks and removes repeats and joins split entries by hand before invoicing. Overlapping exports repeat entries, and switching apps splits work. Mistakes in the hand cleanup either drop worked time or bill it twice. BRIEF.md fixes the CLI, the input headers, the rates header and the output header.

**Overall:** The document stands on its own and can be implemented. Every project-specific term is defined or linked, and the stages connect into a clear flow.

| id | Severity | Lines | Gap | Recommendation |
| --- | --- | --- | --- | --- |
| comprehension-2-1 | Major | 89-97, 407, 579-583, 695-696 | "Blank records skipped before the header" conflicts with "header is line 1" for line numbering | State physical 1-based numbering; add a leading-blank-lines test |
| comprehension-2-2 | Nit | 237-239 vs 265 | Table says "non-empty cell count"; N before/after dropping trailing header cells unclear | Raw M; N after dropping trailing empty header cells (4) |
| comprehension-2-3 | Nit | 228, 254-256 | Format B `task` → description mapping never stated | Add field mapping line |
| comprehension-2-4 | Nit | 233-236, 266-268 | Blank Start / blank `start_iso` reason unclear | Say they give `invalid start` / `invalid start_iso` |
| comprehension-2-5 | Nit | 336-341, 387 | Overlap warning client text: which row's? | "printed client of row i" |
| comprehension-2-6 | Nit | 208-215, 594-595 | Fatal message texts only in the non-normative plan | Add a fatal-message table to the spec |
| comprehension-2-7 | Nit | 682-684, 758-759 | Subprocess test needs cwd=repo root / PYTHONPATH | State cwd and absolute paths |
| comprehension-2-8 | Nit | 3 | EGM named without explanation | Explain or drop |

No Blockers.
