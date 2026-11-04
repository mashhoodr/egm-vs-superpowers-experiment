# stockmerge: Deduplicated Brainstorm Findings

Author: EGM Elephant
Date: 2026-11-03
Sources: `anchored_hypothesis.md`, `BRIEF.md` (same directory). Mode: BRAINSTORM.

## Reviewer Status

| Reviewer | Status |
| --- | --- |
| `egm-design` | completed |
| `egm-codebase-details` | completed |
| `egm-zoom-out` | completed |
| `egm-comprehension` | completed |
| `egm-implementation-readiness` | completed |
| `egm-structural` | completed |

Severity counts after deduplication: 3 Blocker, 20 Major, 7 Nit (30 total).
Severity rule: when lenses disagreed, the highest severity raised is kept. Tier names refer to the hypothesis sections: Fixed contract, Settled with owner, Builder's calls.

## Blockers

### B1. Dedup does not say which physical rows survive - Blocker
* **Lenses:** `egm-implementation-readiness` (Blocker), `egm-design`, `egm-zoom-out`, `egm-structural`, `egm-codebase-details`
* **Scope:** Settled with owner, "Across exports of one location"
* **Description:** "Keep the highest count seen in any single export" fixes how many rows a scan key keeps, not which ones. Example: export 1 has key K once, export 2 has it twice. Keeping 1 from export 1 plus 1 from export 2 differs from keeping both from export 2. The choice changes input order of survivors, which feeds the output sort, the move tie-break, move_id numbering and the `sku` text. A tie between exports with equal counts is also unstated.
* **Recommendation:** State it as an algorithm: for each key, N = highest count in any one export; keep the first N rows of that key in global input order (fills from earlier exports first). Add a worked example. Confirm with owner, since this tier is owner-settled.

### B2. Header detection fails on common real exports (BOM, spacing, empty file) - Blocker
* **Lenses:** `egm-codebase-details` (Blocker), `egm-implementation-readiness`, `egm-design`, `egm-comprehension`, `egm-zoom-out`, `egm-structural`
* **Scope:** Fixed contract "Format detected from header row"; Builder's call on rules header
* **Description:** Excel and Windows exports often start with a UTF-8 BOM. Opened as `utf-8`, the first header cell becomes `﻿Scanned At`, so a valid file exits 2. Same for the rules file. Unstated: spaces around header cells, header case, trailing empty column, zero-byte file (`next(reader)` raises `StopIteration`), header-only file.
* **Recommendation:** Open every input with `encoding="utf-8-sig"`, `newline=""`. Strip each header cell; require exact names in exact order. Zero-byte file = unknown header (exit 2). Header-only file = valid, zero rows. Exit-2 message shows the header found and the two expected.

### B3. Timestamp grammar is open; an offset in Format B crashes the run - Blocker
* **Lenses:** `egm-codebase-details` (Blocker), `egm-implementation-readiness`, `egm-design`, `egm-comprehension`, `egm-zoom-out`
* **Scope:** Fixed contract formats; Settled "Same clock, no time zones"
* **Description:** Python 3.11 `datetime.fromisoformat` accepts date-only, no seconds, fractional seconds, space for `T`, basic format, week dates, `Z` and offsets. An offset gives an aware datetime; comparing it with a naive one raises `TypeError` in move matching, so one row crashes the run instead of being skipped. Format A `strptime("%d/%m/%Y %H:%M")` accepts single-digit parts, rejects surrounding spaces and impossible dates (`31/02`).
* **Recommendation:** Format B: accept only `YYYY-MM-DDTHH:MM:SS` with optional fractional seconds (truncated); offset, `Z`, date-only or other shapes are a bad date (skip, warn). Format A: strip, then strict `strptime`; single-digit day/month accepted and documented. No uncaught exception on any row.

## Major

### M1. "Input order", "scan order" and sort comparison are undefined - Major
* **Lenses:** all six
* **Scope:** Settled, move processing and output sort
* **Description:** Several tie-breaks end in "input order" but nothing defines it across several files, whether line numbers count the header, or which position a row keeps after dedup. String comparison (code-point vs locale vs case-insensitive; `"123"` before `"45"`) is unstated.
* **Recommendation:** Input order = (`--location` argument index, data record number in that file). Scan order = (minute, location name, input order). All string sorts use plain Python `str` order. Define each once in a glossary.

### M2. Scope of the output `sku` "first occurrence" is ambiguous - Major
* **Lenses:** all six
* **Scope:** Settled, "Output `sku`"
* **Description:** "First" could be per (location, normalised SKU) or global across locations; if global, a back-room row could print the shop-floor spelling. Unclear whether the candidate set is before or after dedup.
* **Recommendation:** Per (location, normalised SKU), the trimmed text of the first kept row in input order. Alternative: each row keeps its own trimmed text, which removes the rule. Confirm with owner.

### M3. Time resolution for moves, closeness and sort is unstated - Major
* **Lenses:** `egm-design`, `egm-zoom-out`, `egm-comprehension`, `egm-codebase-details`
* **Scope:** Settled, "Time compared to the minute" and "Move"
* **Description:** Minute truncation is stated for dedup only. If moves use seconds, 14:00:59 vs 16:00:30 gives a different answer. With truncation, the raw-time window is effectively up to 2h00m59s, and there are more ties.
* **Recommendation:** Truncate to the minute at parse time; every time operation (dedup, window, distance, scan order, sort) uses that value. Tests at exactly 2h, 2h+1min and a seconds-straddling pair.

### M4. Output bytes are not pinned down - Major
* **Lenses:** `egm-implementation-readiness`, `egm-design`, `egm-comprehension`, `egm-structural`, `egm-codebase-details`, `egm-zoom-out` (Nit)
* **Scope:** Fixed contract output; Brief goal 4
* **Description:** `csv.writer` defaults to `\r\n`; without `newline=""` Windows writes `\r\r\n`. Encoding, BOM, quoting of SKUs with commas, and header-only output when no rows are kept are unstated.
* **Recommendation:** UTF-8, no BOM, `newline=""`, `lineterminator="\n"`, `QUOTE_MINIMAL`; header always written. Golden-file byte comparison test.

### M5. Failure safety of `--out` is incomplete - Major
* **Lenses:** `egm-implementation-readiness`, `egm-design`, `egm-comprehension`, `egm-structural`, `egm-codebase-details`, `egm-zoom-out` (Nit)
* **Scope:** Settled errors "no output file written"
* **Description:** Unstated: what happens to an existing INVENTORY.csv on exit 2; a crash or full disk partway through writing; an unknown header discovered after output was opened.
* **Recommendation:** Parse and validate everything before opening `--out`. Write to a temp file in the same directory, then `os.replace`. On error, leave any existing file untouched.

### M6. Exit-2 conditions are incomplete and spread across tiers - Major
* **Lenses:** `egm-implementation-readiness`, `egm-structural`, `egm-comprehension`, `egm-codebase-details`, `egm-design`
* **Scope:** Settled errors; Builder's calls
* **Description:** No rule for missing/unreadable rules file, missing `--rules`/`--out`, missing output directory, unwritable output, `--out` equal to an input path, or the exit code for unexpected crashes. Conditions are split between two tiers with no single list.
* **Recommendation:** One error table: condition, exit code, stderr text, output written. All the above exit 2 and write nothing.

### M7. All-zero SKU normalises to an empty string - Major
* **Lenses:** `egm-implementation-readiness`, `egm-design`, `egm-codebase-details`, `egm-comprehension` (Nit), `egm-structural`
* **Scope:** Settled, SKU normalisation
* **Description:** `"000".lstrip("0")` is `""`, which collides with the blank-SKU skip rule and merges every all-zero SKU. `lower()` vs `casefold()` is unstated; whether `007X` equals `7X` is unstated.
* **Recommendation:** `normalise(s) = s.strip().lower().lstrip("0") or "0"`, applied to every SKU, alphanumeric included.

### M8. Rules matched against the normalised SKU cannot match leading-zero patterns - Major
* **Lenses:** `egm-design`, `egm-comprehension`, `egm-structural`, `egm-codebase-details`, `egm-zoom-out` (Nit), `egm-implementation-readiness` (Nit)
* **Scope:** Builder's call, "Rules match against the normalised SKU"
* **Description:** A pattern like `0012` or `00-`, written from the label, never matches because zeros are stripped from the SKU. Pattern trimming is unstated.
* **Recommendation:** Keep the builder's call (scanner-independent categories). Trim and lowercase patterns; warn at startup on any pattern starting with `0`. Document in help text.

### M9. Whole-number and unit grammar is undefined - Major
* **Lenses:** `egm-implementation-readiness`, `egm-codebase-details`, `egm-design`, `egm-comprehension` (Nit), `egm-zoom-out` (Nit), `egm-structural`
* **Scope:** Fixed contract "whole number"; Settled skip rules
* **Description:** `int()` accepts `1_000`, Unicode digits, `+5`, surrounding spaces; rejects `12.0`. `\d` matches Unicode digits. Unit case (`Each`, `CASE`) unstated.
* **Recommendation:** `re.fullmatch(r"[+-]?[0-9]+", s.strip())` before `int()`; `5.0` and `1,000` are non-whole (skip). Unit compared after `strip().lower()`.

### M10. "Malformed row" is not defined in csv-module terms - Major
* **Lenses:** `egm-codebase-details`, `egm-implementation-readiness`, `egm-design`
* **Scope:** Settled errors
* **Description:** Blank lines, wrong field count, an unquoted comma in a Format B note (5+ fields, probably a real scan), and trailing empty columns are not covered. `DictReader` hides these cases.
* **Recommendation:** Use `csv.reader`. Fully blank lines skipped without warning. Field count other than 4 = malformed, skip with warning. Open question below on Format B extra fields.

### M11. Non-UTF-8 input crashes with a traceback - Major
* **Lenses:** `egm-codebase-details`, `egm-design`
* **Scope:** Not written
* **Description:** A cp1252 or UTF-16 export raises `UnicodeDecodeError`, giving exit 1 and a traceback, outside both defined error paths.
* **Recommendation:** Catch decode errors per file; treat as unreadable (exit 2, message names the file). Do not guess encodings.

### M12. Format B quantity unit and note handling are unstated - Major
* **Lenses:** `egm-implementation-readiness` (Major), `egm-zoom-out` (Nit)
* **Scope:** Settled behaviour
* **Description:** Nothing says Format B `count` is single items, or that `note` is ignored everywhere, not only in move matching.
* **Recommendation:** Add: "Format B: qty_each = count; note is never read."

### M13. Location names differing only by case or spacing are silently separate - Major
* **Lenses:** `egm-design`, `egm-comprehension`
* **Scope:** Builder's call, location names exact
* **Description:** `Back room` and `back room` disable dedup between them and can create false moves, with no warning.
* **Recommendation:** Keep exact matching; warn on stderr when two names are equal after trim and casefold.

### M14. No visibility into what a run did; an all-skipped run exits 0 silently - Major
* **Lenses:** `egm-comprehension` (Major), `egm-codebase-details` (Nit)
* **Scope:** Not written
* **Description:** The owner cannot see how many rows were read, skipped, deduplicated, linked or left uncategorised. A file malformed throughout gives exit 0 and an empty inventory.
* **Recommendation:** One summary line on stderr (`read= skipped= deduped= moves= uncategorised=`); warn when a file yields zero valid rows. Exit codes unchanged; stdout empty.

### M15. Spec has no pipeline section and no rule IDs - Major
* **Lenses:** `egm-structural`
* **Scope:** Whole hypothesis layout
* **Description:** Stage order must be pieced together from three tiers. Rules cannot be cited by tests.
* **Recommendation:** Add a numbered pipeline (args, detect, parse, normalise, dedup, moves, categorise, sku text, sort, write) with inputs and outputs per stage. Give rules IDs (D1, M1, C1, E1, O1) with a tier tag on each.

### M16. Shared definitions risk being written more than once - Major
* **Lenses:** `egm-structural`, `egm-zoom-out`
* **Scope:** Not written
* **Description:** Normalisation, scan key and scan order are used by dedup, moves, rules and sort.
* **Recommendation:** One record type built at parse time (location, raw SKU, normalised SKU, minute, qty_each, input order). Pure stage functions. One key function per concept.

### M17. Assumptions likely to change are hard-coded - Major
* **Lenses:** `egm-structural` (Major), `egm-implementation-readiness` (Nit)
* **Scope:** Settled case size; move window; format detection
* **Description:** Case size 12, the 2h window, and exact-header detection are plausible change points (per-SKU case sizes, a third scanner).
* **Recommendation:** Named constants in one module; format detection as a table of header -> parser. No config flags now.

### M18. argparse details that affect the contract - Major
* **Lenses:** `egm-codebase-details` (Major), `egm-zoom-out` (Nit)
* **Scope:** Fixed contract CLI
* **Description:** Subparser not required by default; `allow_abbrev=True` accepts `--loc`; paths may contain `=`.
* **Recommendation:** `add_subparsers(dest="cmd", required=True)`, `allow_abbrev=False`, `action="append"` for `--location`, `str.partition("=")`, `--rules` and `--out` required. argparse usage errors already exit 2.

### M19. Warning format and "line" meaning are undefined - Major
* **Lenses:** `egm-codebase-details` (Major), `egm-implementation-readiness` (Nit), `egm-comprehension` (Nit)
* **Scope:** Settled "warn on stderr with file and line"
* **Description:** Physical line and CSV record line differ when a quoted note spans lines; `reader.line_num` points at the record's last physical line.
* **Recommendation:** Format `stockmerge: warning: PATH:LINE: reason`, header = line 1, LINE = first physical line of the record, path as typed.

### M20. Brief says "per SKU per location"; contract says one row per scan - Major
* **Lenses:** `egm-zoom-out` (Major), `egm-comprehension` (Nit)
* **Scope:** BRIEF problem statement vs Fixed contract
* **Description:** The contract wins, but the owner may expect totals, and a builder may start aggregating.
* **Recommendation:** List totals as a non-goal; confirm with owner that summing is left to them.

## Nits

### N1. `NAME=PATH` edge cases - Nit
* **Lenses:** `egm-implementation-readiness`, `egm-design`, `egm-comprehension`, `egm-structural`, `egm-codebase-details`
* **Recommendation:** Split on the first `=`; trim name only; empty path is exit 2.

### N2. Same file under two location names creates false moves - Nit
* **Lenses:** `egm-implementation-readiness`
* **Recommendation:** Warn when one resolved path appears under more than one name.

### N3. Rule categories may collide with `Move` / `Uncategorised` - Nit
* **Lenses:** `egm-structural`, `egm-design`, `egm-comprehension`
* **Recommendation:** Allow, warn at startup; move_id still distinguishes real moves.

### N4. Greedy move matching is order-dependent by design - Nit
* **Lenses:** `egm-structural`, `egm-design`, `egm-zoom-out`
* **Recommendation:** State it is intended; add one test where greedy differs from optimal so it is not "fixed" later.

### N5. Naive move matching is O(N^2) - Nit
* **Lenses:** `egm-design`
* **Recommendation:** Only if needed: index positives by (normalised SKU, qty_each), sorted by minute, search with `bisect`.

### N6. move_id stable only for identical inputs - Nit
* **Lenses:** `egm-implementation-readiness`
* **Recommendation:** Non-goal; pad to 4 digits, allow wider beyond M9999.

### N7. Partial, split and multi-leg moves are not linked - Nit
* **Lenses:** `egm-comprehension`, `egm-structural`, `egm-design` (non-goal)
* **Recommendation:** Non-goal, told to the owner; count unmatched negatives in the stderr summary.
