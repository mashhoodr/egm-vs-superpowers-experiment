# Comprehension Report (Stage 6)

**Target:** `docs/designs/tsinvoice.md` (FeatureRange 1-501, DetailedRange 502-744). Reviewer: `egm-comprehension` (spawned directly, no standard). Status: completed.

## What this proposes
`tsinvoice` is a Python 3.11 command-line tool that uses only the standard library. Its one sub-command, `merge`, reads CSV exports from two time-tracking apps: Format A from the desktop app and Format B from the phone app. Several exports can belong to one named tracker, and each export's format is detected from its header.

1. **Phase 1 reads everything first.** It reads and checks every input file. Command-line or whole-file problems stop the run with exit 2 and write nothing. Bad rows are skipped, each with a warning.
2. **Phase 2 is a pure pipeline:**
   - Remove exact duplicates inside each tracker. Keep the first N copies in input order, where N is the largest count of that entry in any single export.
   - Join entries with the same normalised client and description when the next one starts 0 to 120 seconds after the previous one ends. Joining uses a greedy walk in start order: smallest gap first, then input order, and only entries not yet claimed as a successor.
   - Round each session up to a multiple of 6 minutes. Price it with the first matching substring rate rule, using `Decimal` and half-up rounding.
   - Sort, give joined sessions `S1..Sn`, and warn about same-client sessions whose times overlap.
3. **Output is written safely.** It goes to a temp file, which is then moved over `--out` with `os.replace`. Warnings are printed to stderr afterwards in a fixed order.

## How the existing system works, per this document
Nothing exists yet. This is a new project, and the document plans 13 new files. "Today" the owner cleans up overlapping exports and split entries by hand, which either drops worked time or bills it twice. The only fixed constraints come from outside the document: the CLI shape, the input headers, the rates header and the output header in BRIEF.md, plus the owner's answers in stakeholder_log.md, which the document cites as R1.n, R2.n and R3.n.

## Findings

Overall, the document holds together. I could paraphrase every section. Its project-specific terms are defined in the Glossary or inline: tracker, export, entry, input order, line number, gap, session, first entry, worked and billed minutes, the R-citations and [D]. Every CUJ and worked example I traced, including the A/B/C claimed-successor case and the 2-plus-3 max-count case, gives the stated result under Stages 4-8. The gaps below are places where two careful implementers could still produce different behaviour.

**comprehension-1-1**
- Severity: Major
- Affected lines: 185-189 (Stage 1), 644-645 (cli.main)
- Gap: The duplicate-PATH warning text is fixed (`<path> is given for trackers <name1> and <name2>`), but the document never says which names fill `<name1>` and `<name2>`, or what "once per extra NAME" means when a path repeats under several names.
  - Example: with `A=x.csv`, `B=x.csv`, `C=x.csv`, the second warning could be "A and C" or "B and C".
  - Example: with `A=x.csv`, `B=x.csv`, `A=x.csv`, the detailed rule "a PATH seen before under a different NAME" would fire a second time on the final `A`, giving "B and A" or "A and B". Stage 1's "once per extra NAME" suggests it should not fire at all.
  - Stderr is meant to be byte-stable (G5) and testable, so this matters.
- Recommendation: Define it exactly. For example: `<name1>` is the first NAME the PATH appeared under; a warning is printed the first time each new NAME appears with that PATH; repeating an already-seen (PATH, NAME) pair prints nothing. Add one worked example with three names.

**comprehension-1-2**
- Severity: Nit
- Affected lines: 219-236, 244-254 (Stage 3 and the bad-row reason table)
- Gap: The reason texts are "fixed text, used in tests", but two things are unspecified:
  - The order of checks when a row fails more than one. Examples: wrong cell count and blank client; blank client and invalid start; invalid start and blank End.
  - What M counts in `expected N fields, got M`: all cells, or cells up to the last non-empty one. "Wrong non-empty cell count" does not settle it.
- Recommendation: State the check order (for example: cell count, then client, then start, then end or duration) and define M as the raw cell count of the record.

**comprehension-1-3**
- Severity: Nit
- Affected lines: 199, 219 (Stages 2 and 3), 561-562 (`_records`)
- Gap: The Stages say "fully blank lines" are skipped. The detailed plan, which the document says yields to the Stages, also drops records whose cells are all blank, such as `,,,` or `" , "`. The Stages do not say whether those count as "fully blank". The document also does not say what happens when blank lines come before the header: is the first blank record taken as the header (exit 2), or skipped?
- Recommendation: Define "fully blank line" in the Glossary as a record with no cells, or with only whitespace cells. State whether leading blank lines are skipped before the header row is chosen.

**comprehension-1-4**
- Severity: Nit
- Affected lines: 201-203 (Stage 2), 572-573 (read_rates)
- Gap: "A finite decimal number" is not defined. The detailed plan's `Decimal(cell.strip())` accepts `1e2`, `+5`, `1_000` and `-0`, while the duration rule (lines 233-235) explicitly rejects signs, exponents and underscores. A reader cannot tell whether the difference is deliberate. Also, `-0` passes the "not negative" check and would print an amount of `-0.00`.
- Recommendation: Give the accepted rate grammar explicitly (for example `^[0-9]+(\.[0-9]+)?$`), or say that anything `Decimal` accepts is allowed and how `-0` is handled.

**comprehension-1-5**
- Severity: Nit
- Affected lines: 85-87 (Glossary, "Normalised text")
- Gap: The definition says normalised text is "used for all comparisons". But header detection uses a trim plus lowercase comparison (Stage 3, `_header_key`), tracker NAMEs are compared as exact case-sensitive strings (line 80), and the duplicate-PATH check compares raw path strings. A reader taking the Glossary literally would normalise all of these.
- Recommendation: Narrow it to "used for comparing client, description and rate patterns".

**comprehension-1-6**
- Severity: Nit
- Affected lines: 504, 716-718
- Gap: "All paths are relative to the repository root", but the document never says where the root is. The links `../../BRIEF.md` imply it is the folder two levels above `docs/designs/` (the arm folder), and `pythonpath = ["."]` depends on that. A fresh reader has to infer it.
- Recommendation: State it explicitly: "the repository root is the directory containing BRIEF.md; `tsinvoice/` and `tests/` are created there".

**comprehension-1-7**
- Severity: Nit
- Affected lines: 3, 742-744
- Gap: "EGM Elephant" and "Drafted with EGM" are project-specific terms that are never explained. They do not affect implementation.
- Recommendation: Spell out EGM once or drop the shorthand.

No Blockers. Implementing from this document alone is feasible. comprehension-1-1 is the one gap likely to produce stderr that differs between implementations.
