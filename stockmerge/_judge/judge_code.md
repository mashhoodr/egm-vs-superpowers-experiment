# Blind code verdict: stockmerge X / Y / Z

Judged against BRIEF.md only. Not counted as defects (stakeholder rulings): greedy move
pairing in scan order, and skip-with-warning + exit 0 for malformed rows.

## TL;DR

| | Correctness risk | Clarity | Tests | Proportionality | Total |
|---|---|---|---|---|---|
| **X** | 4 | 5 | 4 | 4 | **17** |
| **Y** | 3 | 3 | 4 | 2 | **12** |
| **Z** | 1 | 4 | 2 | 4 | **11** |

Ranking: **X > Y > Z** (5 = best on every axis; correctness weighted highest).

Top defect per implementation:
- **X**: `--out` equal to an input export is accepted. The run exits 0 and overwrites the source export (`X/stockmerge/cli.py:35-42`, no check), so the original scans are gone and a rerun exits 2.
- **Y**: rows in a move get the category `Move` in place of the category the rules give them (`Y/stockmerge/writer.py:20`). The brief asks for "everything categorised by my rules". Close second: a strict ISO regex (`Y/stockmerge/readers.py:21-23`) drops valid ISO 8601 scans such as `...+05:00`, `...Z` and `...T10:01`.
- **Z**: an unclosed quote silently swallows every following row. It uses a whole-file `csv.reader` (`Z/stockmerge/core.py:99`), so real scans are lost with no warning and exit 0. A large file makes it crash with a traceback.

## Evidence (runs in a scratch dir)

| Probe | X | Y | Z |
|---|---|---|---|
| Format B unclosed quote, then 2 valid rows | all 3 kept | all 3 kept | **only 1 kept, no warning, exit 0** |
| Format A unclosed quote, then 2 valid rows | bad row warned, 2 kept | same as X | **2 valid rows lost, 1 warning** |
| Unclosed quote, then 6000 rows | 6001 kept | 6001 kept | **traceback `field larger than field limit`, exit 1, no output** |
| `--out` = input export | **exit 0, input overwritten** | exit 2, input unchanged | **exit 0, input overwritten** |
| Duplicate row within one export | both kept | both kept | both kept |
| Overlap across exports (`ABC1` / `abc1`, same minute) | collapsed to max per export | same | same |
| `1 case` (A, `0042`) vs `12 each` (A, `42`), same minute, two exports | collapsed to one row of 12 | same | same |
| ISO with `+05:00`, `Z`, no seconds | kept (offset dropped, not converted) | **skipped as "bad date"** | kept |
| Multi-line quoted note | first line kept, continuation warned | same | kept whole |
| Rule pattern `00` vs SKU `0042` | matches the raw SKU | warns, can never match | no match |
| Move row whose SKU has a rule (`xyz,Widgets`) | `Widgets` | **`Move`** | `Widgets` |
| Missing output directory | exit 2, clean message | exit 2 | **traceback, exit 1** |
| Non-UTF-8 byte in a row | whole file fatal, exit 2 | that row skipped, exit 0 | **traceback, exit 1** |
| Output file mode | 0644 (umask) | 0644 | **0600** (mkstemp, no chmod) |
| Own tests | 77 pass | 122 pass | 24 pass |

## X

**Correctness risk: 4**
- It reads one physical line at a time (`readers.py:80-93`). A stray quote only affects its own line, and an oversized field becomes a warned bad row rather than a crash (`readers.py:126-128`). This directly serves "never lose a real scan".
- Dedupe keeps the per-export maximum count, takes the representative from the earliest export, and keeps repeats within one export (`dedupe.py:7-20`). Move tie-breaks are fully ordered (`moves.py:9-10, 28`). The output sort key is total (`writer.py:15-16`), so the run is deterministic.
- Defect: there is no guard for `--out` being an input or the rules file (`cli.py:35-42`). `write_atomic` (`writer.py:29-41`) then replaces the export after it has been read. The source data is destroyed and a second run fails on the header. Minor points: a timezone offset is dropped rather than converted (`readers.py:76`). A Format B note with unquoted commas is skipped as a bad row (test `test_readers.py:181`) where Z keeps it. One bad byte makes the whole file fatal (`readers.py:27-28`), which is conservative rather than lossy.

**Clarity: 5**
- Each stage is a small module with one job (readers, dedupe, moves, rules, writer). `cli.run_merge` (`cli.py:35-42`) reads as the pipeline itself.
- Names carry their meaning: `sku_key`, `input_order`, `FatalError` vs `BadRow` (`model.py:10-34`, `readers.py:19`). Policy constants sit in one place (`CASE_SIZE` `model.py:7`, `WINDOW_MINUTES` `moves.py:6`).
- Rules reuse the reader's line splitting (`rules.py:9`), so CSV behaviour is the same for both files.

**Tests: 4**
- The risky cases are asserted, not just named. Examples: the unclosed quote does not swallow later rows (`tests/test_readers.py:129-134`), multi-line note line numbers (`:137-144`), oversized fields (`:156`), max-not-sum dedupe with the representative chosen (`tests/test_dedupe.py:19-22`), and byte-identical reruns (`tests/test_cli.py:48`).
- Move tests cover the window boundary, ties and the greedy limit (`tests/test_moves.py:20-100`).
- Gaps: no test for out-is-input (the defect above), and no end-to-end case-vs-each dedupe across formats.

**Proportionality: 4**
- About 390 runtime lines across 8 files is right for the problem. The extra handling (umask chmod at `writer.py:38-40`, U+2028-safe splitting at `readers.py:80-85`) is small and each piece earns its place.

## Y

**Correctness risk: 3**
- Moved rows are forced to category `Move` (`writer.py:20`). The rule category is overwritten exactly on the rows that goal 2 touches (verified: `xyz,Widgets` becomes `Move`). The team chose this on purpose (`tests/test_cli.py:205` is named `test_move_rows_not_categorised`; `rules.py:51-54` warns about the reserved name), but it departs from brief goal 3 as written.
- The ISO regex (`readers.py:21-23`, `85`) needs exactly `YYYY-MM-DDTHH:MM:SS[.ffffff]`. Valid ISO 8601 stamps with `Z`, an offset, or no seconds are skipped as bad rows, which loses real scans (with a warning). Leading-zero rule patterns can never match (`rules.py:46-50` warns rather than fixes; `categorise` only sees `sku_norm`, `rules.py:59-62`).
- Strengths: it is the only one that refuses `--out` equal to an input or the rules file, including symlinks and hard links (`cli.py:54-62, 91-93`). It has line-based quote safety (`readers.py:50-51`), a raised field limit (`readers.py:26`), and per-row handling of bad bytes. Dedupe (`dedup.py:10-24`) and moves (`moves.py:35`) are deterministic.

**Clarity: 3**
- The module split matches X, but the design is spread thin. `Warnings` is a class that writes to the stream and also records every message (`model.py:57-74`). `main` keeps a `current_path` variable to build error text (`cli.py:88-117`). `read_export` returns a 3-tuple of scans and counts (`readers.py:127-158`).
- The `Scan` record has six fields of identity and position (`arg_index`, `record_no`, `path`, `line`, `ident`) (`model.py:16-30`). Comments point to an R-number spec the reader cannot see (`readers.py:1`, `dedup.py:1`).

**Tests: 4**
- It has the widest coverage of the risky paths: out-is-input asserts the bytes are unchanged (`tests/test_cli.py:131-136`), plus hard links and the rules file (`:146-158`), the unclosed quote (`tests/test_readers.py:188-191`), and dedupe 2-vs-1 and 2-vs-3 (`tests/test_dedup.py:30-44`).
- Some tests lock in the questionable choices: `test_iso_rejected` (`tests/test_readers.py:144`) and `test_move_rows_not_categorised`. Many tests check incidental behaviour (help text, abbreviations, warning formatting in `tests/test_model.py`).

**Proportionality: 2**
- About 545 runtime lines with extras the brief never asked for: warnings for location names that differ only in case or spaces (`cli.py:65-81`), a check that one file is used for two names, a reserved-category warning, a run summary line (`cli.py:118-122`), surrogate-escape bad-byte tracking (`readers.py:35, 65-66`), and `copymode` on the existing output (`writer.py:47-48`). Each adds surface without serving the four goals.

## Z

**Correctness risk: 1**
- `csv.reader` over the whole file (`core.py:99-111`) means an unclosed quote absorbs every following line into one note field. This is verified: Format B lost 2 valid rows with **no warning** and exit 0. Format A lost 2 valid rows behind one warning. With enough rows it hits the 131072 field limit, crashes with a traceback (exit 1) and writes no output. This is the worst failure against "never lose a real scan".
- `--out` equal to an input export is accepted and overwrites it (`cli.py:31-32`, `core.py:235-247`). Uncaught `OSError` and `UnicodeDecodeError` give tracebacks with exit 1 for a missing output directory (`core.py:240`) and for non-UTF-8 input (`core.py:95-111`). The output file is mode 0600 (`core.py:240`, no chmod).
- Smaller points: the header must be on physical line 1 (`core.py:100`). A rule with a blank category is accepted (`core.py:150`). Location names are not trimmed (`cli.py:11-14`). Strength: it keeps Format B rows with unquoted commas in the note (`core.py:116-118`). Dedupe (`core.py:157-180`) and moves (`core.py:183-210`) are correct and deterministic.

**Clarity: 4**
- One 250-line `core.py` reads top to bottom as parse, dedupe, moves, categorise, write (`core.py:225-232`). The docstrings state the policy (`core.py:158-165, 214-215`).
- Drawbacks: stages change the `Scan` records in place (`move_id` and `category` are set at `core.py:209, 218-221`). Moves are tracked by `id(pos)` (`core.py:190-210`). `write_output` imports inside the function (`core.py:236-237`).

**Tests: 2**
- Dedupe and move policy are covered well end to end: max count (`tests/test_stockmerge.py:50`), cross-format case/seconds/zeros (`:73`), the representative's spelling (`:87`), and determinism through a subprocess (`:205`).
- There is nothing on the riskiest input paths: no unclosed quote, no oversized field, no out-is-input, no missing directory, no bad encoding. `test_bad_rows_skipped_with_warning` (`:176`) only uses well-formed CSV. The defects that lose data are exactly the ones left untested.

**Proportionality: 4**
- It is the smallest solution and roughly the right size, but it saves size by skipping input robustness that the brief's first goal calls for. The judgment is right; the coverage is thin.

## Overall ranking

1. **X**: robust input handling, correct dedupe and moves, clean structure. One real hole: `--out` can be an input.
2. **Y**: the safest file handling, but two departures from the brief (the `Move` category and the strict ISO regex) and the most over-built code.
3. **Z**: clear and compact, but it silently loses real scans on malformed CSV and crashes on several ordinary errors.
