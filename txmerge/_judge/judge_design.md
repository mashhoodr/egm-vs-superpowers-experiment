# Blind design review: txmerge, P vs Q

Inputs read: `BRIEF.md`, `_judge/blind/design_P.md`, `_judge/blind/design_Q.md`. Nothing else was opened.

## TL;DR
- **P** is the stronger spec. It pins down almost every behaviour down to the byte, and its own sections agree with each other. It is also about twice the size it needs to be.
- **Q** is compact and comes with ready-to-paste TDD code and a hand-traced end-to-end fixture. But the code contradicts Q's own spec in at least seven places, including the promised atomic write.
- **I would hand P to an engineer tomorrow**, after cutting it down. An engineer following Q's code would ship behaviour that its spec says is wrong.

## Scores

| Criterion | P | Q |
|---|---|---|
| 1. Completeness against brief | 5 | 3 |
| 2. Unambiguity (byte-identical across teams) | 5 | 2 |
| 3. Implementability + test strategy | 4 | 4 |
| 4. Proportionality / readability | 2 | 4 |
| 5. Decision quality | 4 | 3 |
| **Total** | **20** | **16** |

## 1. Completeness

**P (5).**
- *Definitions* fixes the meaning of export, account (case-sensitive, untrimmed), input position (start line, counting blank lines), description vs normalised description, duplicate key, and output order.
- *Stage 2* sets out:
  - an exact amount grammar (ASCII digits, comma grouping, 1–2 decimals, sign allowed only in Format B);
  - date grammar for both formats;
  - the order in which checks run, and which single reason gets reported;
  - field-count checks, zero normalisation (`-0.00` becomes `0.00`), and empty descriptions.
- *Stage 3* covers rules-file edge cases: a header-only file is valid, and blank pattern, blank category or wrong arity each give a warning and the row is skipped.
- *Stage 6* covers transfers: inclusive window, closest date first, then output-order tie-break, greedy pairing, `T0001` IDs widening past 9999, and zero amounts never pairing.
- *Stage 8* and the *Errors, warnings and exit codes* table give exact stderr text for every fatal and non-fatal case, plus a summary line.
- It also handles `--out` aliasing an input file, a symlinked `--out`, and an `=` inside the PATH.

**Q (3).**
- *Behaviour* covers the main brief items: max-count dedup, the transfer rule, first-match categorisation, and byte-identical output.
- It leaves these open:
  - exact warning and error text (only a loose `WARNING: <file>:<line>: <reason>`);
  - what happens with rules rows that have more than 2 cells;
  - whether skipped rules rows produce a warning;
  - blank lines *before* the header;
  - which line number is reported for multi-line rows;
  - the rounding mode (it appears only in code, as `ROUND_HALF_UP`);
  - what happens to amounts with more than 2 decimals on input;
  - any run summary.

## 2. Unambiguity

**P (5).**
- Every output byte is specified: UTF-8 without BOM, `\n`, `QUOTE_MINIMAL`, `f"{amount:.2f}"` after quantising at parse time, and the transfer_id format.
- Every message string is given in full in the errors table and again in *Detailed Implementation Plan* (`formats.py`, `rules.py`, `cli.py`). Regexes are written out (`parse_date_dmy`, `parse_amount`).
- Two engineers working from P should produce identical ledgers and identical stderr.
- The only stated non-determinism is Unicode casefold tables across Python versions, and G4 discloses it honestly.

**Q (2).** The spec and the code disagree, so an engineer has to pick one. The contradictions:

| Topic | Q spec says | Q code does |
|---|---|---|
| CSV parsing (*Parsing*) | "parsed one physical line at a time with a strict `csv` reader… quoted fields cannot span lines… malformed quote spoils only its own line" | `csv.reader(fh)`, non-strict, over the whole file. Multi-line fields are accepted, the reported line is the row's *end* line, and `csv.Error` is not caught, so it exits 1 with a traceback |
| Zero handling, Format A (*Parsing*) | "A column holding zero counts as blank… both present but zero → keep `0.00`" | `if debit and credit: raise "both… set"`, so `0.00` plus a value is rejected; zero is never treated as blank |
| Amount grammar (*Parsing*, error table) | regex `[+-]?(\d+(\.\d*)?\|\.\d+)`; "exponents (`1e5`)… unparseable" | `Decimal(cleaned)` accepts `1e5`, `1_000`, `1,2,3`→123, `12.345`; `test_format_amount` even asserts `1E+3` formats |
| Rules, empty category (*Categorisation*) | "empty pattern or an empty category are ignored" | only a blank pattern is checked; an empty category becomes a real category `""` |
| Malformed rules CSV (*Categorisation*) | "strict `csv` → exit 2" | non-strict reader, no `csv.Error` handling |
| Atomic write (*Writing*) | "temp file beside the target and `os.replace`d… never leaves a partial or truncated output" | `writer.py` opens `path` with mode `"w"` directly; there is no temp file |
| Oversized amount (error table) | "exit 2, stderr message, no output" | `quantize` raises `InvalidOperation` in the writer, which is not caught: traceback, exit 1, and a truncated output file |
| Error prefix | "argparse-style usage error" for a bad rules header | prints `error: …` and returns 2. Warnings use `WARNING:` and errors use `error:`, and neither format is specified |

## 3. Implementability

**P (4).**
- *Detailed Implementation Plan* lists 17 files, each with function signatures and step-by-step behaviour. Six phases each end with the tests green.
- The test list is thorough, and every Decision Log entry is cross-referenced to a test (*Verification Plan*).
- The reference-scan property test for the amount index (`test_transfers.py`) is a good idea.
- Weaknesses:
  - There is no test code. Every test is written as prose.
  - The CUJ-1 expected ledger is "worked out by hand… never pasted from a run", but the design never supplies it. The engineer has to derive it.

**Q (4).**
- It gives copy-paste code and tests in six TDD tasks, with a run/fail/implement/pass/commit loop per task.
- `test_cli.py::EXPECTED` comes with a written trace. I checked the trace: it is correct for the fixture.
- Weaknesses:
  - The code is the defect carrier listed in section 2. The tests pass while the spec is violated, because none of them test the contradicted behaviours (zero-as-blank, exponent rejection, a write that leaves the old file intact, strict CSV).
  - `test_unwritable_out_exits_2` only covers a missing directory.

## 4. Proportionality

**P (2).**
- Roughly 580 lines of design for a tool of about 500 lines. That includes 12 "Alternatives Considered" entries, of which A–G only restate stakeholder answers, a 27-row Decision Log, and a 15-row Risks table.
- Several facts appear three times, in the narrative, the Decision Log and the Risks table. Examples: the `0.00` both-filled rejection, and the false transfer when one file is passed under two account names.
- There is process residue:
  - "Status: Approved";
  - "following links was removed at Stage 8 review";
  - `Drafted with [redacted]`;
  - "Verified by the design author on CPython 3.11.14 and 3.13.7".
- It is precise but tiring to read. About 40% could go without losing any decision.

**Q (4).**
- The spec part is about 95 lines and reads in five minutes.
- The plan is long only because it contains the actual code, which is a reasonable use of the space.
- Noise: the "REQUIRED SUB-SKILL" banner, a per-task commit ritual, and a spec path pointing at `docs/[redacted]/specs/...`.

## 5. Decision quality

**P (4).**
- Reasons are stated in the Decision Log and Alternatives sections. The strongest decisions:
  - D24: strict CSV, because non-strict mode silently swallows rows;
  - H: reject more than 2 decimals rather than round silently;
  - I: no encoding fallback;
  - K: atomic write;
  - D18: refuse an `--out` that overwrites an input.
- Questionable: rejecting Format A rows where the unused column holds `0.00` is a common bank export pattern. That choice runs against the brief's "never lose a real transaction", even with a warning and the M count. The Risks table admits the problem but accepts it.
- Failing the whole run on a single non-UTF-8 byte is also harsh. It is defensible, and it is disclosed.

**Q (3).**
- The decisions themselves are often user-friendly:
  - zero counts as blank;
  - line-level CSV isolation;
  - "silently skipping an export could lose transactions";
  - three approaches compared up front.
- But the reasoning is thin, mostly one-line *(our choice)* tags, and the best decisions were never carried into the code.
- Rewriting every surviving duplicate to the first occurrence's text is a legitimate choice, but no reason is given for it.

## Which to hand an engineer tomorrow
**P.**
- An engineer can build from it without asking a question. Its numbered stages, plan and tests agree with each other, and the output and messages are fully specified.
- Before handing it over I would cut the Alternatives A–G section and the duplicate Risks/Decision rows, and add the CUJ-1 expected ledger as a literal.
- Q looks faster to start because the code is already written. Following that code would ship:
  - a non-atomic writer;
  - traceback exits (exit 1) where the spec promises exit 2;
  - accepted exponent amounts;
  - rejected `0.00` rows that the spec says to keep.
- The engineer would have to reconcile the spec and the code first, and that is design work Q left unfinished.

## Specified in one, ambiguous or wrong in the other

**P specifies, Q leaves open or gets wrong:**
- **Output file safety:** temp file plus `os.replace`, with an existing ledger left untouched on failure. Q's spec claims this too, but its code writes directly.
- **Strict CSV:** P implements it and maps `csv.Error` to exit 2. Q claims strictness, does not implement it, and lets `csv.Error` crash.
- **Amount grammar:** P's is exact (rejects `1e3`, `NaN`, `12.345`, `.50`, `1,2,3`, non-ASCII digits, 40-digit numbers). Q's spec regex is not what its code enforces.
- **Quantising:** P quantises to 2 decimals at parse time, so dedup keys and transfer amounts match what is printed. Q compares unrounded Decimals: `100.004` will not pair with `100.00`, yet both print as `100.00`.
- **Messages:** P gives the exact warning, error and summary text. Q gives loose prefixes and a Python-list `repr` for the bad-header message.
- **Line numbers:** P reports the start line of a multi-line row. Q reports the end line, and its spec says such rows cannot exist.
- **Rules rows:** P warns on wrong arity, blank pattern and blank category. Q silently accepts more than 2 cells and empty categories.
- **Blank lines before the header:** P skips them. Q treats the file as having an unrecognised header.
- **`--out` aliasing an input file, and a symlinked `--out`:** P handles both. Q handles neither.
- **Exit codes:** P uses exit 1 for internal defects and exit 2 for user errors. In Q, uncaught exceptions also exit 1, but by accident.
- **Run summary:** P prints an M/D/T/U summary line so that dropped rows are visible. Q has none.

**Q specifies, P does not or differs:**
- **Hand-computed end-to-end ledger:** Q provides it, with a trace. P only promises one.
- **Zero in the unused Format A column:** Q's spec treats it as blank, which is the friendlier choice, though it is not implemented. P rejects the row.
- **Text of surviving duplicates:** Q gives every survivor the first occurrence's text. P keeps each copy's own text and attributes that to the stakeholder. These are opposite decisions, and each is explicit within its own design.
- **Account NAME:** Q strips whitespace from NAME. P uses it exactly as typed. Both are explicit.
- **Large transfer test:** Q has a 20,000-row `T10000` test that forces the amount index to stay fast. P covers the same ground with a reference-scan equivalence test, but has no scale test.
