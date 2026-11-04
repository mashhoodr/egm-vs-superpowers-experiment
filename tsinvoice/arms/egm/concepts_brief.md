# Concepts Brief: `tsinvoice`

**Mode:** BRAINSTORM
**Inputs:** `BRIEF.md` (fixed contract), `stakeholder_log.md` (rounds 1-2; cited below as R1.n / R2.n)

## Reviewer Status

| Reviewer | Lens | Status |
| --- | --- | --- |
| `egm-design` | Skeptical Architect Brainstormer | completed |
| `egm-codebase-details` | Technical Accuracy (Python 3.11 stdlib) Brainstormer | completed |
| `egm-zoom-out` | Simplicity & Scope Brainstormer | completed |
| `egm-comprehension` | Naive Reader Brainstormer | completed |
| `egm-implementation-readiness` | Implementation Readiness Brainstormer | completed |
| `egm-structural` | Document Structure Brainstormer | completed |

---

## 1. Overview

`tsinvoice` is a stdlib-only Python 3.11 CLI. It merges overlapping timesheet exports from two tracker apps (desktop format A, phone format B) into one deterministic, priced CSV of sessions. The pipeline is: parse and validate, then normalise, dedupe within each tracker, join continuations across trackers, round up to 6 minutes, price, sort, assign session IDs, and write.

All six reviewers agree the problem is framed correctly and fits in a small design: pure functions plus a thin CLI. They also agree the owner's rules are **not yet implementation-ready**:
- Two pairs of answers conflict or leave gaps: client text (R1.8 vs R1.10) and join claiming (R1.3 vs R2.3).
- The rules never say which duplicate copies survive dedupe.
- Several "your call" items change output bytes or the exit code. Two implementers would produce different CSVs today.

## 2. Analysis

### 2.1 Contradictions in the owner's rules

- **Blocker: client text, R1.8 vs R1.10** (design, comprehension, structural, implementation-readiness).
  - R1.8 says client and description come from the session's first entry.
  - R1.10 says the output client is the "original text from the first occurrence" of that normalised client.
  - So "Acme" in one session and "ACME" in another print differently under R1.8, and the same under a global reading of R1.10.
  - "Its first occurrence" in R1.8 is also ambiguous. It could mean the first duplicate copy, or the first appearance anywhere in the input.
- **Blocker: join claiming, R1.3 vs R2.3** (implementation-readiness, structural, comprehension). R2.3 says the earlier-starting entry takes the shared successor. Three things are left open:
  - (a) Whether the losing predecessor falls back to its next-best *free* candidate or gets no successor.
  - (b) What order applies to predecessors with the same start time. Identical in-export copies (R1.1) guarantee such ties happen.
  - (c) Whether a claimed entry still picks its own successor. That is how chains form.
  - Comprehension's worked example: A 09:00-10:00, B 09:30-10:01, C starts 10:01. A takes C (gap 1), even though B's gap is 0. A reader could implement this as a global smallest-gap pairing instead.

### 2.2 Gaps: edge cases the rules do not decide

- **Blocker: which duplicate copies survive** (all six). "Keep the max per-export count" fixes how many copies remain, not which ones. The surviving copies carry three things:
  - input order, used by the join tie-break and as the third sort key
  - the raw text that gets printed (copies can differ in case or spacing)
  - line numbers
  - The reviewers proposed three different rules (see Q2).
- **Blocker: output bytes are not pinned** (structural, codebase-details, implementation-readiness, design).
  - `csv.writer` defaults to `\r\n`.
  - Encoding, BOM, quoting and amount formatting are unstated.
  - "Same output" (Want 4) cannot be tested byte for byte until these are fixed.
- **Blocker: money arithmetic** (all six). Float `round()` rounds half to even and works on binary values. For example, 6 min at 10.05/h = 1.005 should round half-up to 1.01, but float gives 1.00.
  - Money must use `Decimal` and `ROUND_HALF_UP`.
  - `Decimal()` also accepts `NaN`, `Infinity` and `1e2`, and raises `InvalidOperation`, not `ValueError` (codebase-details).
- **Major: "exit 2, no output" needs load-then-write** (all six).
  - A bad header in the third file must not truncate an existing `--out`.
  - So every input must be validated first, then written to a temp file and moved into place with `os.replace`.
  - `--out` equal to an input path: design says reject it; implementation-readiness says it is safe once reading finishes first.
- **Major: time precision** (all six). The seconds decision affects exact-match dedupe, the inclusive 2-minute gap and whole-minute sums. Python 3.11 `fromisoformat` accepts more than expected:
  - date-only values, which silently become midnight
  - hour-only values
  - basic format and week dates
  - any separator character
  - `strptime("%d/%m/%Y %H:%M")` accepts single-digit day, month and hour, and fails on surrounding whitespace.
- **Major: phone duration parsing** (codebase-details, implementation-readiness).
  - `int()` rejects "30.0".
  - It accepts " 30", "+30", "3_0" and non-ASCII digits.
  - Huge values overflow `timedelta`.
- **Major: rate matching is under-specified** (design, comprehension, structural, implementation-readiness, codebase-details).
  - Normalised or raw text?
  - Is the pattern itself normalised?
  - Does an empty pattern match everything?
  - Loop order: rules outer, then fields?
  - `lower()` or `casefold()`?
- **Major: a bad rates row is not like a bad tracker row** (structural, design, comprehension). Under first-match-wins, skipping a broken rule lets a broader later rule price the session. The invoice is then silently wrong instead of flagged at 0.00.
- **Major: missing configuration errors.** None of these is defined: missing or unreadable files, encoding errors, a zero-byte file, malformed `--tracker` (no `=`, empty NAME or PATH, `=` inside the path), bad rates header.
- **Major: "line" and "input order" are ambiguous** (comprehension, codebase-details, design, structural).
  - `reader.line_num` is the line where a record *ends*.
  - "--tracker argument order" could mean the position of each pair or NAMEs grouped together.
- **Major: warning text, order and count are unspecified**, so tests that assert on stderr will disagree. This includes whether the unmatched-rate warning appears per row or per distinct pair.
- **Major: blank fields and ragged rows** (implementation-readiness, codebase-details, design).
  - Empty client or description after trimming.
  - Fully blank lines.
  - Wrong cell count. `DictReader` hides these by mapping them to `None`.
  - A repeated header mid-file.
- **Nit: rounding of exact multiples** (comprehension). Does 12 stay 12? The only example is 14 to 18.
- **Nit: Unicode** (design, codebase-details). NFC before casefold for "Café" from different apps. `str.split()` collapses NBSP but not zero-width spaces.
- **Nit: determinism scope** (structural). "Same inputs" must mean the same files *and* the same argument order. Reordering `--tracker` legitimately changes tie-breaks.

### 2.3 Tension with the owner's goal ("never lose real time")

The rules protect against *losing* time, but nothing protects against *double billing* (zoom-out, design, comprehension, codebase-details):
- An entry edited between exports (09:00-10:00, then 09:00-10:30) survives as two overlapping sessions: 150 min billed for 90 min of work.
- The same work timed in both apps, or the same file passed under two NAMEs, is billed twice with no signal.
- Skipped rows (a blank End usually means a running timer) drop real time with only one stderr line as notice.

All reviewers keep the owner's rules. They propose warning-only safeguards: overlap warnings, a summary line, and a duplicate-path warning (or exit, per design).

### 2.4 Open questions raised by reviewers (deduplicated, with recommended defaults)

Where reviewers disagreed, every option is listed with the lenses that back it.

1. **Printed client text.** Is it the global first occurrence per normalised client (R1.10) or the session's first entry (R1.8)? *Default (design, structural, implementation-readiness):* client from the global first occurrence in input order; description from the session's first entry. *Alternative (comprehension):* both from the session's first entry.
2. **Which duplicate copies survive dedupe?** Three options:
   - (a) The first N occurrences in global input order across that tracker's exports, where N = max per-export count (zoom-out, codebase-details, structural).
   - (b) All copies from the export with the highest count; ties go to the earliest `--tracker` (implementation-readiness, comprehension).
   - (c) The copies from the first export, in argument order, that reaches the max (design).
3. **Join fallback.** If P's best successor is already claimed, does P take its next-best free candidate? *Default:* yes. A claimed entry still picks its own successor. Successor ties go to the successor's input order.
4. **Same-start ordering.** In what order are same-start entries processed (join) and sorted (output)? *Default:* (start, input order) everywhere.
5. **Seconds in `start_iso`.** *Option A (implementation-readiness, comprehension, structural):* truncate to the minute, so all arithmetic is integer. *Option B (zoom-out, codebase-details, design):* keep full precision; the gap is at most 120 s inclusive, because truncation creates false duplicates and false joins.
6. **"30.0" as `duration_minutes`.** *Default:* accept digits optionally followed by `.0…`, value > 0. Reject "29.5", "0", negatives, "1e2", "3_0", non-ASCII digits and blank. On a leading "+", reviewers split: codebase-details accepts it, the others reject it.
7. **Date-only or hour-only `start_iso`.** *Default:* skip with a warning. Require the date plus at least HH:MM, with `T` or a space as separator.
8. **Desktop strictness.** Should single-digit day or month ("5/1/2026 9:00") be accepted? Should desktop times with seconds be accepted? *Default (implementation-readiness):* strict `DD/MM/YYYY HH:MM` after trimming. *Alternative (codebase-details):* also accept `%H:%M:%S`.
9. **Header strictness.** *Default:* strip the BOM (`utf-8-sig`), trim cells, exact names and order, no extra columns; anything else exits 2. An empty or zero-byte file exits 2. A header-only file is valid with zero entries. Two points are disputed:
   - Case: case-sensitive (zoom-out, implementation-readiness, codebase-details, structural) or case-insensitive (comprehension, design).
   - Trailing empty header cells are allowed (codebase-details).
10. **One NAME with mixed formats.** May one NAME hold both format A and B files, with each file detected on its own? *Default:* yes.
11. **Missing or unreadable files, encoding errors.** *Default:* exit 2 with a message, no output, all checked before any write.
12. **Malformed `--tracker`.** *Default:* split on the first `=`; no `=`, an empty NAME or an empty PATH is an argparse error with exit 2. All three options are required.
13. **Bad rates file.** A wrong header or missing file exits 2. Bad rows (empty pattern, non-numeric, negative, NaN or Infinity rate): *Option A (zoom-out, implementation-readiness, codebase-details):* skip with a warning. *Option B (structural, design, comprehension):* fatal exit 2, because skipping a rule can misprice through a later rule. Either way, an empty pattern is never a catch-all.
14. **Rate matching text and loop order.** *Default:* the same `normalise()` (trim, collapse whitespace, casefold) on the pattern and on the session's client and description. Rules form the outer loop; a rule matches if it is a substring of either field.
15. **Unmatched-rate warning frequency.** *Option A (implementation-readiness, structural):* once per output row. *Option B (comprehension, design):* once per distinct normalised (client, description), in output order.
16. **Tracker identity.** *Default:* the NAME is an exact, case-sensitive string. Different NAMEs never dedupe. Every PATH under one NAME is an export of it.
17. **Same PATH under two NAMEs.** It would bill twice. *Default (most reviewers):* allow it and warn. *Alternative (design):* exit 2. The same PATH twice under one NAME is a no-op.
18. **Blank client or description.** *Default:* skip a blank client with a warning. *Split on description:* implementation-readiness and structural allow it blank; design and comprehension skip it.
19. **Blank lines, ragged rows, repeated header.** *Default:* skip blank lines silently. A wrong cell count is skipped with a warning; extra cells are tolerated only if they are empty. A repeated header mid-file is a bad row.
20. **Line numbering.** *Default:* the header is line 1. Use the physical line where the record *starts* for warnings, and the record position for input order. Implementation-readiness instead proposes `reader.line_num`.
21. **"--tracker argument order".** *Default:* the position of each individual NAME=PATH argument, not grouped by NAME.
22. **Warning format and order.** *Default:* `warning: <path-as-given>:<line>: <reason>` on stderr, in input order, followed by rate warnings in output order. Comprehension adds a `tsinvoice:` prefix.
23. **Is 12 rounded to 12?** *Default:* yes, a ceiling to a multiple of 6 with integer arithmetic `-(-m // 6) * 6`. 0 cannot occur.
24. **No valid entries.** *Default:* write a header-only CSV and exit 0.
25. **Existing `--out`.** *Default:* overwrite atomically with a temp file and `os.replace`, and leave it untouched on any exit-2 path. On `--out` equal to an input path, reviewers split: design rejects it, implementation-readiness allows it.
26. **stdout on success.** *Default:* print nothing. Warnings go to stderr only.
27. **Output bytes.** *Default:* UTF-8 with no BOM, `\n` line endings, `QUOTE_MINIMAL`. Amount is plain `0.00` with no currency sign or separator; minutes is a bare integer.
28. **`session_id` format.** *Option A (zoom-out, codebase-details, comprehension, structural, design):* a sequential `S0001`/`S1` over joined rows in output order. It is simple and unique, but IDs shift when inputs change. *Option B (implementation-readiness):* `S-` plus a 10-hex sha256 of the normalised key, start and end, with a `-2` suffix on collision. It stays stable across new exports, which matters if invoices cite IDs.
29. **Overlap safeguard.** Warn, without changing output, when surviving sessions for the same normalised client overlap in time, within or across trackers. *Default:* yes.
30. **Summary line.** Print one stderr summary (rows read, skipped, duplicates removed, joined, sessions, unrated)? *Default:* yes (zoom-out, codebase-details).
31. **Unicode normalisation.** Apply NFC before casefold? *Default:* yes (design).
32. **Determinism definition.** *Default:* same files, same arguments, same order give byte-identical CSV, and stderr too if warnings are buffered and ordered.
33. **Main user and success measure** (R1.12, uncovered). *Default:* the freelancer at invoice time. Success means re-runs are byte-identical, billed minutes are at least the deduped worked minutes, and no line is silently zero or doubled without a warning.

## 3. Goals vs. Non-Goals

**Goals**
- Meet the fixed contract exactly: CLI shape, formats A and B detected by header, rates header, output header, exit 0 and exit 2.
- Dedupe only within a tracker, by exact normalised key and max per-export count. Never lose real time.
- Join continuations across apps with the greedy, deterministic rule (0-2 min inclusive, smallest gap, then input order).
- Round each session up to 6 minutes. Price with exact `Decimal` half-up.
- Produce byte-identical output for the same arguments in the same order.
- Make every dropped or suspicious row visible on stderr.

**Non-Goals** (agreed across lenses)
- Time zones, DST, offset conversion (R1.6). Splitting at midnight (R1.7).
- Fuzzy or near-duplicate matching. Auto-resolving edited entries. Cross-tracker dedupe (R1.1, R1.2).
- Per-client totals, invoice documents or PDF, currencies.
- Configurable rounding or gap. Persistent state between runs. Formats beyond A and B.
- Format plugin systems, class hierarchies, config files.

## 4. Alternatives Weighed

| Topic | Option chosen as default | Alternative | Trade-off |
| --- | --- | --- | --- |
| Architecture | Two phases: load and validate everything, then a pure `merge(entries, rates) -> rows` and an atomic write | Streaming per file | Two phases satisfy "exit 2, no output" and `--out`-as-input for free |
| Modules | 2-3 flat modules (`cli`, `io`/parse, `core`) with frozen dataclasses | One module per stage, or a header-to-parser registry (structural) | Flat is smaller; a registry makes a third format one entry |
| Internal record | One format-agnostic `Entry(tracker, input_key=(arg_idx, line), client_raw, desc_raw, client_key, desc_key, start, end, minutes)` | Per-format types | Nothing after parsing knows about A or B |
| Dedupe | `Counter` per export, merged with `\|` (per-key max), then keep survivors per Q2 | Pairwise comparison | About 10-20 lines, no fuzzy logic |
| Join | Group by (client_key, desc_key); sort by (start, input_key); greedy scan with a bisect window | One global list; graph or optimal matching | Grouping gives the same result and is easier to test; optimal matching is not what the owner asked for |
| Time resolution | See Q5 | Truncate vs keep seconds | Integer simplicity vs avoiding false duplicates and joins |
| session_id | See Q28 | Sequential vs content hash | Simplicity vs stability across new exports |
| CSV reading | `csv.reader` with explicit length checks, `utf-8-sig`, `newline=""` | `DictReader` | DictReader hides ragged rows |
| Money | `Decimal` only at pricing; `int` minutes elsewhere | float | Float breaks half-up |
| Warnings | One `warn()` helper that buffers, orders and counts warnings, and prints a summary | Print warnings inline | Deterministic stderr, and the summary costs nothing extra |
| Double-billing guard | Warning only (overlap, duplicate path) | Change the dedupe rule | Keeps the owner's rule intact |

## 5. Key Decisions & Staging for Next Steps

All 33 open questions in 2.4 are now closed: by the owner (rounds 1-3, cited R1.n / R2.n / R3.n) or by the Elephant where the owner said "your call" (marked **[Elephant]**). `/egm-draft` carries these forward verbatim.

### 5.1 Owner decisions (round 3)
- **Q1 printed text (R3.1):** client and description both come from the session's own first entry (the kept copy), outer spaces trimmed, case kept. "ACME" prints as "ACME" even if "Acme" appeared earlier.
- **Q2 dedupe survivors (R3.2):** per tracker, per key, keep the first N copies in input order (`--tracker` argument position, then line), N = largest per-export count. Text and input position come from the kept copies.
- **Q3 join fallback (R3.3):** walk entries in (start, input order). Each takes the free successor with the smallest gap (0-120 s inclusive), ties by input order; if the best is taken it takes the next-best free one; none free means no successor. A claimed entry still picks its own successor, so chains form.
- **Q4 same-start order (R3.4):** input order.
- **Q15 unmatched-rate warning (R3.9):** one warning per output row, naming client and description; amount 0.00.
- **Q28 session_id (R3.6):** only needs to be non-empty, unique, and stable for identical inputs in identical order.

### 5.2 Elephant decisions ("your call" items)
- **Q5 seconds [Elephant]:** keep full precision; never truncate. The gap test is `0 <= next.start - prev.end <= 120 s`. Worked minutes stay whole because desktop times have no seconds and phone durations are whole minutes.
- **Q6 "30.0" [Elephant]:** accept a trimmed value matching `digits` or `digits.0+` with value > 0. Reject "29.5", "0", negatives, signs, exponents, underscores, non-ASCII digits, blank.
- **Q7 [Elephant]:** `start_iso` must contain a date and at least HH:MM; a date-only value is a bad row. Offsets and `Z` are dropped, not converted (R1.6).
- **Q8 [Elephant]:** desktop Start/End parsed with `%d/%m/%Y %H:%M` after trimming; single-digit day/month/hour accepted (stdlib behaviour, harmless).
- **Q9 header [Elephant]:** read as `utf-8-sig`; trim each header cell, compare case-insensitively, exact names in exact order; trailing empty header cells ignored. Anything else exits 2. A zero-byte file (no header) exits 2. A header-only file is valid with zero entries.
- **Q10 [Elephant]:** one NAME may mix format A and B files; each file is detected on its own.
- **Q11 [Elephant]:** missing or unreadable tracker/rates file, or a decode error, exits 2 with a message and writes nothing.
- **Q12 [Elephant]:** `--tracker` is split on the first `=`; no `=`, empty NAME or empty PATH exits 2 (argparse error). `--tracker`, `--rates`, `--out` are all required.
- **Q13 bad rates [Elephant]:** fatal. Wrong header, empty pattern (after normalising), non-numeric, NaN/Infinity or negative rate exits 2 with file and line. Reason: skipping a rule lets a broader later rule misprice a session silently. A header-only rates file is valid (every row unrated, with warnings).
- **Q14 [Elephant]:** one `normalise()` = Unicode NFC, trim, collapse whitespace runs to one space, casefold. It is applied to client/description keys and to rate patterns. Rules are the outer loop; a rule matches when its normalised pattern is a substring of the normalised client or the normalised description of the session's first entry.
- **Q16 [Elephant]:** NAME is an exact, case-sensitive string; every PATH under one NAME is an export of it.
- **Q17 [Elephant]:** the same PATH under two NAMEs is allowed with a warning (it will double bill). The same PATH twice under one NAME is harmless by the max-count rule.
- **Q18 [Elephant]:** blank client is a bad row (skip, warn). Blank description is kept: it is still real time.
- **Q19 [Elephant]:** fully blank lines skipped silently; wrong cell count is a bad row unless the extra cells are all empty.
- **Q20 [Elephant]:** line numbers count the header as line 1 and name the physical line where the record starts.
- **Q21 [Elephant]:** "argument order" is the position of each `--tracker NAME=PATH` argument, not grouped by NAME.
- **Q22 [Elephant]:** warnings go to stderr as `tsinvoice: warning: <path as given>:<line>: <reason>` for rows, then rate and overlap warnings in output-row order. Fatal errors are `tsinvoice: error: <message>`.
- **Q23 [Elephant]:** rounding is a ceiling to a multiple of 6: 12 stays 12, 13 becomes 18.
- **Q24 [Elephant]:** no valid entries writes a header-only CSV and exits 0.
- **Q25 [Elephant]:** all inputs are read and validated before writing; output goes to a temp file in the same directory and is moved into place with `os.replace`. An existing `--out` is overwritten; on exit 2 it is left untouched. `--out` equal to an input path is allowed (inputs are fully read first).
- **Q26 [Elephant]:** nothing on stdout. No summary line (YAGNI).
- **Q27 [Elephant]:** output is UTF-8 without BOM, `\n` line endings, `csv.QUOTE_MINIMAL`; minutes a bare integer; amount `Decimal` quantised to `0.01` with `ROUND_HALF_UP`, printed like `12.50`.
- **Q28 session_id [Elephant]:** sequential `S1`, `S2`, ... over joined rows in output order. Single-entry rows have a blank session_id.
- **Q29 overlap warning [Elephant]:** warn (output unchanged) when two output sessions with the same normalised client overlap in time (one starts before the other ends), within or across trackers. It flags the double billing the owner's rules allow without changing them.
- **Q30:** no summary line. **Q31:** NFC yes (in `normalise()`). **Q32 determinism:** same files and same arguments in the same order give byte-identical CSV and identical stderr.
- **Q33 [Elephant]:** the user is the freelancer at invoice time. Success: reruns are byte-identical; no real time is dropped without a warning; every skipped row, unrated row and overlap is on stderr.

### 5.3 Staging
1. `/egm-draft` from this brief, using the spec structure suggested by the structural lens (glossary, one subsection per pipeline stage, error/exit table, worked examples).
2. Carry the 39-case acceptance test matrix into the Verification Plan.
