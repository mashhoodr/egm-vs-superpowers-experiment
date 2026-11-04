# stockmerge

Author: EGM Elephant
Date: 2026-11-03

## Overview

`stockmerge` is a stdlib-only Python 3.11 CLI. It merges stock-take CSV exports from two scanner formats into one deterministic inventory CSV (`location,sku,qty_each,category,move_id`, one row per kept scan). It removes copies of a scan that appear in overlapping exports of one location, links stock-outs to stock-ins across locations as moves, and categorises the remaining rows by substring rules.

Six reviewers ran in BRAINSTORM mode against `anchored_hypothesis.md` and `BRIEF.md`. All six completed. After deduplication there are 3 Blockers, 20 Majors and 7 Nits; the full list is in `brainstorm_findings.md` (IDs B1-B3, M1-M20, N1-N7 below refer to it).

The hypothesis is close to buildable. The gaps are definitions the settled rules depend on but do not state, and parsing details that make real exports fail or crash.

## Analysis

**Where the lenses agreed.** Every lens raised the same three ambiguities in the owner-settled tier:
- Which physical rows survive cross-export dedup (B1).
- What "input order" means across several files (M1).
- Whether the output `sku` text is chosen per location or globally (M2).

These three are linked. The survivor choice sets each row's input order, and input order drives the output sort, the move tie-break, move_id numbering and the `sku` text. Leave any one of them open and "same inputs, same output" (brief goal 4) cannot be tested.

**Parsing risks.** The codebase-details lens found two problems that block real use:
- A UTF-8 BOM, which Excel exports often carry, makes a valid file fail the header check, so the run exits 2 (B2).
- `datetime.fromisoformat` accepts timezone offsets. One Format B row with an offset produces an aware datetime, and comparing it with naive datetimes raises `TypeError` during move matching, so the run crashes (B3).

Several lenses also found that the whole-number, unit, malformed-row and encoding rules are not pinned down (M9-M11). Each one can either drop a real scan or end in an uncaught traceback.

**Time model.** Minute truncation is stated only for dedup (M3). Applying it at parse time and using it everywhere gives one time model, so both scanners behave the same way. Side effect: measured on raw times, the 2h window allows up to 2h00m59s.

**Output and failure safety.** By default, the csv module's line endings and the lack of an atomic write break byte-level determinism and the "no output on error" rule (M4, M5). The exit-2 conditions are spread across two tiers and miss the rules-file and `--out` cases (M6).

**Builder's calls that drew pushback:**
- Matching rules against the normalised SKU means a pattern with leading zeros can never match (M8).
- Exact location names let a case typo silently turn off dedup and create false moves (M13).

Both calls are kept below, with a startup warning added to each.

**Spec structure.** The structural lens asked for a pipeline section, rule IDs and an error table (M15, M6). These make the spec usable as a test plan. They do not change any behaviour.

## Goals vs. Non-Goals

**Goals** (from the brief's four wants, plus what the reviewers showed they require):
1. Remove copies of a scan across overlapping exports of one location. Never drop a repeat scan within one export.
2. Link moves between locations under one documented, deterministic greedy rule.
3. Categorise every non-move row the same way, whichever scanner read it.
4. Same arguments and same input bytes give byte-identical output.
5. Every input row is either written, removed as a counted duplicate, or skipped with a `PATH:LINE: reason` warning. No uncaught exceptions.
6. A failed run leaves the filesystem unchanged.
7. Each rule is defined once (one record type, one key function per concept) and can be tested by its rule ID.

**Non-Goals:**
- Totals per SKU per location. Output stays one row per scan (M20; confirm with owner).
- Time zones, DST, or comparing times below the minute.
- Dedup or SKU unification across different location names. Fuzzy location or SKU matching beyond trim, case and leading zeros.
- Per-SKU or configurable case sizes.
- Reading Format B notes for any purpose.
- Partial, split or multi-leg moves. Globally optimal move matching.
- Formats other than A and B, encoding detection, `csv.Sniffer`, other delimiters.
- Regex rules, rule priority other than file order, more than one category per row.
- move_id values that stay the same when the input set changes.
- Runtime dependencies, config files, subcommands other than `merge`, performance tuning beyond an index if one is needed.

## Alternatives Weighed

| Question | Option chosen | Option not chosen | Reason |
| --- | --- | --- | --- |
| Dedup survivors (B1) | First N rows of the key in global input order | Take all N from the export with the highest count | Matches "earlier `--location` first"; no export tie-break needed |
| Output `sku` text (M2) | Per (location, normalised SKU), first kept row | Each row keeps its own text; or global first | Fits "dedup only within one location"; tidy output. Own-text is the fallback if the owner prefers it |
| Time resolution (M3) | Truncate to the minute at parse time, use everywhere | Keep seconds for moves and sort | One time model; both scanners behave the same |
| Format B timestamps (B3) | Strict `YYYY-MM-DDTHH:MM:SS[.fff]`, anything else is a bad date | Lenient `fromisoformat` plus checks | Skips are predictable and testable; no aware/naive crash |
| Rule matching target (M8) | Normalised SKU, warn on patterns starting with `0` | Raw trimmed SKU; or normalise patterns too | Keeps the builder's call (scanner-independent); the warning covers the gap |
| Location names (M13) | Exact, warn on case/space near-duplicates | Case-insensitive names | Keeps the builder's call; still shows typos |
| Move matching (N4) | Greedy, closest in time (settled) | Optimal bipartite matching | Already settled, deterministic, easy to explain |
| Output write (M5) | Validate all, temp file, `os.replace` | Validate all, then write directly | Also covers failures during the write; a few lines |
| Line ending (M4) | `\n` | csv default `\r\n` | Easier to diff and test; revisit if the owner opens files in Excel and has problems |
| Skipped rows exit code | Exit 0 (contract) plus a stderr summary | `--strict` flag for non-zero exit | Deferred; one more mode to test, no stated need |
| Spec layout (M15) | By pipeline stage, with a tier tag per rule | By decision tier (current) | Rules can be found and tested; who-decided stays visible |

## Key Decisions & Staging for Next Steps

**Stage 0. Owner confirmation (settled-tier clarifications, must be asked):**
- Q1 (B1): For each scan key, keep the first N rows in global input order, where N is the highest count in any one export.
- Q2 (M2): The output `sku` text is the first kept row's trimmed text per (location, normalised SKU). Alternative: each row prints its own text.
- Q3 (M3): All time comparisons, moves included, use minute-truncated times.
- Q4 (M20): The output stays one row per scan, and totals are left to the owner.
- Q5 (M10): Should a Format B row with more than 4 fields (an unquoted comma in the note) be kept, with the extra fields joined into the note, or skipped as malformed? Proposed: keep it, because "never lose a real scan" and the note is ignored anyway.
- Q6 (B2, M10): Ask for one real export from each scanner, to check for a BOM, trailing empty columns and line endings.

**Stage 1. Builder decisions (adopted now, written into the spec):**
- D1 Input order = (`--location` argument index, data record number). Scan order = (minute, location, input order). Sorts use plain `str` code-point order. (M1)
- D2 Read inputs with `utf-8-sig` and `newline=""`. Strip header cells and require exact names in exact order. A zero-byte file exits 2. A header-only file is valid with zero rows. A decode error exits 2 and names the file. (B2, M11)
- D3 Format A: strip, then `strptime("%d/%m/%Y %H:%M")`. Format B: strict shape, optional fraction truncated. An offset, `Z` or date-only value is a bad date. (B3)
- D4 Qty must match `^[+-]?[0-9]+$` after strip, so `5.0` is skipped. Unit is compared after `strip().lower()`. Format B: `qty_each = count`, and the note is never read. (M9, M12)
- D5 Use `csv.reader`. Skip blank lines silently. A field count other than 4 is malformed, except for the Format B question in Q5. (M10)
- D6 `normalise(s) = s.strip().lower().lstrip("0") or "0"`. Patterns are trimmed and lowercased. Warn on patterns that start with `0` and on categories named `Move` or `Uncategorised`. (M7, M8, N3)
- D7 Output: UTF-8, no BOM, `\n`, `QUOTE_MINIMAL`, header always written. (M4)
- D8 Validate everything, then write a temp file and `os.replace` it. Exit 2, with nothing written, for a missing or unreadable rules file, an unwritable `--out`, `--out` equal to an input path, or an empty PATH. (M5, M6, N1)
- D9 argparse: required subparser, `allow_abbrev=False`, `--location` uses `action="append"` and splits on the first `=`, `--rules` and `--out` are required. (M18, N1)
- D10 Warnings use the format `stockmerge: warning: PATH:LINE: reason`, where LINE is the first physical line of the record. One summary line per run on stderr. Warn when a file has no valid rows, on location names that differ only by case or spacing, and when the same path appears under two names. (M13, M14, M19, N2)
- D11 Structure: one record type and pure stage functions. `CASE_SIZE` and `MOVE_WINDOW` are named constants. Format detection is a header-to-parser table. No config flags. (M16, M17)

**Stage 2. Spec revision:** Rewrite the hypothesis with a numbered pipeline section, rule IDs with tier tags, a glossary (input order, scan order, scan key, minute), an error table, and worked examples for B1, M2, M3 and the greedy-vs-optimal case (M15, N4).

**Stage 3. Tests before code:** One test per rule ID. Byte-level golden-file tests. Boundary tests for the move window at 2h, 2h+1min and a pair that straddles a minute boundary in seconds. Tests for a BOM, an offset timestamp, an all-zero SKU and a failed run that leaves an existing `--out` untouched.

**Deferred:** a `--strict` flag, a `bisect` index for move matching (only if real file sizes need it), and move_id stability across changed inputs (non-goal, N6).

## Owner Answers to Stage 0 (round 3, see `stakeholder_log.md`)

- Q1 confirmed: keep N = highest per-export count; survivors are the first N copies in input order.
- Q2 resolved: each output row prints the trimmed SKU text of the copy that was kept. No unification of
  spelling across rows. This replaces the "per (location, normalised SKU)" option in Alternatives Weighed.
- Q3 confirmed: every time comparison (dedup, move window, closest-in-time tie-break, sort) uses
  minute-truncated times. The 2h window is inclusive on minute times.
- Q4: one row per kept scan. Builder's call: no totals (non-goal).
- Q5 resolved: a Format B row with a field count other than 4 is malformed: skip with a warning.
- Q6 builder's call: accept a UTF-8 BOM and CRLF line endings (`utf-8-sig`, `newline=""`).
- Q7 builder's call: Qty/count must match `^[+-]?[0-9]+$` after trimming; `+5` accepted, `5.0` skipped.
- Q8 builder's call: Format A parsed with `strptime("%d/%m/%Y %H:%M")`, which also accepts unpadded
  day/month/hour values such as `5/3/2026 9:05`.
