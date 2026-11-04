# Comprehension Report (Stage 6, round 1)

**Target:** `docs/designs/stockmerge.md` (FeatureRange 1-495, DetailedRange 496-735)
**Reviewer:** `egm-comprehension` (direct dispatch) — completed

**What this proposes**

`stockmerge` is a Python 3.11 command line tool that uses only the standard library. It reads CSV exports from two scanner formats (A and B), and each export is tagged with a location name. It drops duplicate copies of a scan that come from overlapping exports of the same location. For each scan key, it keeps as many rows as the largest count found in any one export, taking the first ones in argument and record order. It then greedily pairs each negative scan with an exactly opposite positive scan of the same normalised SKU at a different location within 120 minutes, and marks the pair as a `Move` with id `M0001`, `M0002` and so on. Every other row gets a category from the first rules-file substring that matches its normalised SKU, or `Uncategorised`. The tool writes one sorted row per kept scan, atomically through a temp file and `os.replace`. Bad rows become warnings and the run still exits 0. Structural problems (bad headers, unreadable files, usage errors, `--out` colliding with an input) exit 2 and leave `--out` untouched.

**How the existing system works, per this document**

The repo is greenfield, so there is no existing code. Today the shop owner has several overlapping CSV exports in two formats and no combined count. Adding the files together counts overlapping scans twice. Looking at each location on its own makes every move look like a loss at one place and a gain at another. The fixed contract in BRIEF.md sets the command line, the input and rules headers, the output header and exit 0 on success. The document works inside that contract.

I could paraphrase every section, so there are no Blockers. The parts connect: the glossary, the R-rules, the pipeline diagram and the module plan agree with each other in nearly every place.

## Findings

- **comprehension-1-1 (Major)** lines 371-372, 702. Summary line counters R, D, S, M, W are undefined (does R include skipped rows; is M pairs or rows; does R = W + D + S hold; does S include rules-file rows). Tests check these counts, so a reader must guess.
- **comprehension-1-2 (Major)** line 61 vs R6.1 (311-313). Non-goal "Dedup or SKU matching across different location names" contradicts move linking, which matches the same normalised SKU at a different location.
- **comprehension-1-3 (Nit)** 367-369, R1.4/R1.5, 529. Warning format requires PATH but R1.4/R1.5 warnings are not about one file.
- **comprehension-1-4 (Nit)** R4.2, diagram line 160, 541-550. Three slightly different statements of the empty-file rule (zero-byte, header-only, only blank lines; "empty" vs "no valid rows").
- **comprehension-1-5 (Nit)** 203-204 vs R1.1, R3.1, R4.2, R9.1, 728. Legend omits the **[contract]** tag.
- **comprehension-1-6 (Nit)** 57, 76-79, 402, 486-487. "Builder"/"owner" introduced late or not at all; `concepts_brief.md` / `stakeholder_log.md` cited without paths; Alternative A quote appears nowhere else.
- **comprehension-1-7 (Nit)** R1.4 line 219. "Inner spaces" ambiguous (collapse runs vs remove all).
- **comprehension-1-8 (Nit)** worked example 375-394. No headers, and the expected output table is not shown.
- **comprehension-1-9 (Nit)** 527-529, 634-635, 638. Unclear whether warnings stream or are buffered; backstop message PATH source unstated.
- **comprehension-1-10 (Nit)** 551-557, 564. Who calls `to_minute` and where `sku_norm` is computed is unstated.

**Summary:** 0 Blockers, 2 Majors, 8 Nits.
