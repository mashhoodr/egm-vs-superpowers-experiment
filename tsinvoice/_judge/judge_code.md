# Blind code verdict: X, Y, Z

Paths are relative to `_judge/blind/<arm>/`. Tests: X 86 passed, Y 160 passed, Z 19 passed.
Probes were run in a scratch dir. They covered duplicates within and across exports, joins across trackers, tracker order swapped, seconds and offsets in `start_iso`, `1e1` and huge durations, cp1252 input, a NUL byte, bad rate rows, a whitespace-variant client, an unclosed quote followed by valid rows (both small and 3000-row files), and `--out` equal to an input.

Not counted as defects (stakeholder rulings): greedy joining, and skip-with-warning plus exit 0 on a malformed row.

## Scores

| | Correctness risk | Clarity | Tests | Proportionality | Total |
|---|---|---|---|---|---|
| X | 4 | 4 | 4 | 4 | 16 |
| Y | 3 | 3 | 4 | 3 | 13 |
| Z | 2 | 4 | 2 | 5 | 13 |

**Ranking: X > Y > Z.** Y and Z tie on total. Y ranks above Z because Z can crash the whole run on one bad row or file, and Y does not.

## Behaviour all three share (not used to rank them)
- **Duplicates.** Each arm keeps, per key, as many copies as the single export holding the most. The key is tracker, normalised client/description, start and end. All three gave identical output on the main dedupe/join probe.
- **Identical entries in two different trackers are both kept** and billed twice. Only Y warns about it, through its overlap warning.
- **An unclosed quote swallows the valid rows after it.** On a 3-row file, all three exit 0 and lose the two valid rows that follow, with one warning.
- **`--out` equal to an input overwrites that export.** The run reads everything first, so it is consistent. But the raw export is destroyed and a re-run fails on the header. None of them refuse. Y's test `tests/test_cli.py:186` explicitly blesses this.
- **Chains depend on the order of `--tracker` arguments.** Ties are broken by argument index, so swapping the order can change which chain forms, the session_id and the display casing. Running the same command again gives the same bytes in all three.
- **Pricing.** Billed minutes are rounded up to multiples of 6 after summing the chain. Amounts use Decimal with ROUND_HALF_UP, so there is no float money anywhere.

## X

**Correctness risk: 4**
- Robust input handling. A cp1252 fallback with a warning (`tsinvoice/csvio.py:19-24`) means a non-UTF-8 export is not lost. Out-of-range and overflow durations are skipped as bad rows (`tsinvoice/parse.py:83-89`). `csv.Error` becomes a clean exit 2 rather than a traceback (`csvio.py:25`).
- Unclosed quote: on a small file the following rows are silently dropped. The warning points at line 4 with "expected 4 fields, got 2" rather than naming the quote (`parse.py:40-41`). On a large file the swallowed field passes the csv field limit. That is fatal (exit 2, no output), which is loud and loses nothing silently. The small-versus-large split comes from Python's default field limit rather than anything X designed, but X did deliberately map `csv.Error` to exit 2.
- Format B seconds are kept rather than truncated (`parse.py:73`), unlike Format A's minute resolution. Example: a phone entry from 09:00:45 for 30 minutes, followed by one at 09:30:10, did not join, because the second starts before the first ends. This is a missed join, not lost time. `1e1` is accepted as 10 minutes.

**Clarity: 4**
- One concern per module: `dedupe.py` 24 lines, `join.py` 49, `rates.py`, `session_id.py`, `output.py`. `Entry` and `Session` in `model.py:20-67` read cleanly, with derived properties (`minutes` rounds up to 6).
- The dedupe loop (`dedupe.py:13-24`) is compact, but the "seen in this file > kept so far" idea needs its docstring to be understood.
- The split is slightly fragmented for ~450 lines. For example, `csvio.py` is a 26-line module.

**Tests: 4**
- Covers the risky core. Within-file repeats are kept and the max count holds across exports (`tests/test_dedupe.py:11-26`). Gaps are measured in seconds, with 2m01s not joining (`tests/test_join.py:26`). Tie-breaks have tests (`test_join.py:52-80`), and so do byte-identical re-runs (`tests/test_cli.py:50`) and a failed write leaving the old output (`test_cli.py:120`).
- Gaps: no test for an unclosed quote, and none for `--out` equal to an input.

**Proportionality: 4.** About 450 source lines for the job. Hashed session ids with a collision suffix (`session_id.py`) are a reasonable extra that keeps ids stable as exports grow.

**Most serious defect:** an unclosed quote silently drops the valid rows after it, with exit 0 and a misleading line-4 "field count" warning (`parse.py:36-47`). This is real worked time disappearing.

## Y

**Correctness risk: 3**
- **The unclosed-quote handling is built to lose time.** A sentinel trick detects the open quote (`tsinvoice/readers.py:46-71`). The csv field limit is raised to 2^31 (`readers.py:39`) so that the swallowed remainder becomes one "bad row". On a 3000-row file with an open quote on row 2, Y exited 0, wrote a header-only output and printed one warning: about 3000 hours silently gone. The tests lock this in. `tests/test_readers.py:178-186` asserts that the valid 13:00-14:00 row after the quote is dropped. `test_readers.py:188` asserts a 200 KB swallowed field is "not fatal".
- **Strengths.** Overlap warnings for the same client (`core.py:131-145`) flag double-billing, including the same entry tracked in both apps. Strict rates validation is fatal on bad rows (`readers.py:100-120`). Seconds are truncated (`readers.py:149`). NFC normalisation is handled (`model.py:18-22`). An undecodable file gets a clean exit 2.
- Session ids are sequential `S1, S2…` (`core.py:115-118`). This is deterministic for the same inputs, but every id shifts when a new export adds an earlier joined session, which is fragile for invoices that cite ids.

**Clarity: 3**
- The `core.py` pipeline is readable. Pure logic is separated from I/O (`core.py`, `readers.py`, `writer.py`).
- `_read_records` (`readers.py:32-84`) is the hardest code in all three arms. The sentinel append-and-strip logic is subtle and easy to break.
- Comments refer to a "Stage 4", "R4.1" and similar spec that is not in the repo (`core.py:1`, `cli.py:1`). A maintainer gets the labels without the document behind them.

**Tests: 4**
- The broadest coverage. It includes join tie-breaks and claimed successors (`tests/test_core.py:94-135`), dedupe max-count (`test_core.py:26`), a seconds handoff, overlap warnings, CRLF and line endings, a file mode or symlink at the output path, and an exit 2 that leaves `--out` unchanged (`tests/test_cli.py:76`).
- The deduction is for asserting harmful behaviour as correct: the valid rows after an open quote are asserted dropped (`test_readers.py:178`).

**Proportionality: 3.** About 536 source lines and about 950 test lines, roughly 1.5x X. The extras are the sentinel CSV machinery, the overlap analysis, chmod and symlink handling, and header leniency (case-insensitive, trailing blank columns). They are more than the brief needs.

**Most serious defect:** an unclosed quote swallows the rest of the file, by design and under test, and the run still exits 0. Every later entry is lost with one warning (`readers.py:39,46-71`; `tests/test_readers.py:178-192`).

## Z

**Correctness risk: 2**
- **Exceptions escape on single bad inputs and crash the whole run** (traceback, exit 1, no output):
  - a huge duration raises `OverflowError` (`tsinvoice/parse.py:109`, not caught by the `except ValueError` at `parse.py:112`);
  - a cp1252 export raises `UnicodeDecodeError` (`parse.py:77-81`);
  - a long unclosed-quote tail raises `csv.Error` "field larger than field limit" (`parse.py:81`);
  - a write `OSError` is uncaught (`__main__.py:46-49`).

  The first one contradicts the stakeholder's "malformed row is skipped, exit 0" rule.
- **Rate matching uses casefold only, without whitespace normalisation** (`core.py:82-88`), while dedupe and join use `norm()`. The client "Acme  Corp" (double space) missed the `acme corp,0.05` rule and was priced by `acme,100`: 10.00 instead of 0.01.
- A bad rate row is skipped with a warning rather than being fatal (`parse.py:150-152`). A typo in a specific rule silently drops that session to a broader rule or 0.00. The temp file is a fixed `out + ".tmp"` name (`__main__.py:46`), left behind on failure.
- Strengths: money is safe, because `Decimal(minutes)/60` is exact when minutes are multiples of 6 (`core.py:120`), but only because `BILL_STEP` is 6. Hashed session ids are stable. Small-file behaviour on an unclosed quote matches X.

**Clarity: 4**
- Compact two-module split, `parse.py` and `core.py`, with good docstrings on dedupe and join (`core.py:20-48`).
- `price()` also builds the output records, assigns ids and sorts (`core.py:109-138`). That is a misleading name for a do-everything stage. `norm` and `warn` live in `parse.py` and are imported by `core.py`.
- Line numbers come from `enumerate` (`parse.py:93`), so they are wrong after any multi-line quoted field.

**Tests: 2**
- 19 end-to-end tests in one file cover the happy-path rules well: dedupe, the edited entry keeping both copies, joins, tie-breaks and half-up rounding (`tests/test_tsinvoice.py:41-133`).
- No tests for encoding, overflow, an unclosed quote, whitespace in rate matching or write failure: exactly where the crashes and mispricing live.

**Proportionality: 5.** About 355 source lines. It is the leanest arm and has no gold-plating.

**Most serious defect:** an unhandled `OverflowError`, `UnicodeDecodeError` or `csv.Error` from a single bad row or file crashes the run with a traceback and exit 1. A whole invoice run is lost over one row (`parse.py:77-81,109,112`).
