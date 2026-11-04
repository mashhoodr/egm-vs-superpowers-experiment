# Blind design review: stockmerge, design P vs design Q

Inputs read: `BRIEF.md`, `_judge/blind/design_P.md`, `_judge/blind/design_Q.md` only.
Three edge-case claims were checked against Python 3.13 (csv end-of-data in a quote, the `int()` digit limit, and how loose `fromisoformat` is).

## TL;DR

| Criterion | P | Q |
|---|---|---|
| 1. Completeness against the brief | **5** | 3 |
| 2. Unambiguity (byte-identical output) | **5** | 3 |
| 3. Implementability + test strategy | 4 | **4** |
| 4. Proportionality / readability | 2 | **3** |
| 5. Decision quality | **4** | 3 |
| **Total** | **20** | 16 |

- **Hand to an engineer tomorrow: P.** It is the only one of the two where the prose, the signatures and the tests agree. Expect to skim about a third of it.
- Q gets to working code faster, because the plan *is* the code. But its design section and its code disagree in several places (rules matching, rules parsing, bad-row handling). In those places the engineer has to guess which one is right.
- Reading time for a senior engineer: **P ≈ 60–75 min**. **Q ≈ 45–60 min** (about 10 min for the design part, the rest reviewing about 600 lines of code and tests).

---

## Scores with reasons

### 1. Completeness against the brief

**P: 5.** Every open behaviour is pinned down, each with a rule ID:
- **Duplicates:** R5.1–R5.6. Scan key, max-per-export count, first N in input order, and dedup before moves.
- **Units:** R4.9, with `CASE_SIZE = 12`.
- **Moves:** R6.1–R6.5. The ±120 min window is inclusive, the closest partner wins, ties go to scan order, the greedy limitation is stated, and move rows get category `Move` with rules skipped.
- **Rules:** R3.1–R3.5. Substring match on the normalised SKU, first match wins, a warning for patterns starting with `0`, and a warning when a rule's category collides with `Move`/`Uncategorised`.
- **Ordering:** R8.1, compared by code point and independent of locale.
- **Errors:** the "Messages and exit codes" table, the warning format and the summary line.
- **Determinism:** the NFR "Determinism" bullet and G4.

It also covers cases the brief only implies:
- an unclosed quote in a free-text note (R4.12)
- invalid UTF-8 handled per field (R4.1)
- `--out` naming an input (R2.2)
- zero quantities (R4.11)
- timezone offsets rejected so times stay naive (R4.6, Alternative D)

**Q: 3.** The core is covered: §5 dedup, §6 moves, §3 parsing, §7 output. The gaps:
- **Category of move rows is never stated in the design.** §6 is silent. It only shows up in `test_full_merge`, where move rows get *rule* categories (`back room,cola-1,6,Drinks,M1`).
- **`--out` equal to an input is not addressed.** The input is silently replaced on a successful run.
- **Unclosed quote in a note is not addressed.** `csv.reader` over the whole text joins the following lines into one field, so real scans after it vanish into a note or come back as one malformed row. That breaks brief item 1, "never lose a real scan".
- **A rule whose category is `Move`/`Uncategorised`** is not addressed.
- **No summary or count of what was skipped or removed.** The owner cannot see how many duplicates were dropped.
- **A non-UTF-8 file is fatal for the whole run.** That is a stated choice (Review Focus 4), so it counts as a trade-off rather than a gap.

### 2. Unambiguity

**P: 5.**
- Every regex, check order, error string, sort key and output byte detail is pinned (R4.8 `[+-]?[0-9]{1,9}`; the `parse_a_row` check order; R9.2).
- A full worked example gives the exact output bytes and the stderr summary.
- Two engineers following P would very likely produce byte-identical CSVs.
- One small inaccuracy: the R3.4 warning says a `0…` pattern "cannot match", but `001` does match inside `1001`.

**Q: 3.** If both engineers copy Q's code they will match each other. If they implement from Q's *design* text, they will not. The design and the code contradict each other:
- **Rules matching.** Design §4 says the pattern is tested against `sku_key` **and** the casefolded `sku_text`, so that `00123` patterns still match. Task 3 `categorise(key, rules)` and Task 6 `render` test **only** `sku_key`.
- **Rules parsing.** §4 says rules are "parsed one physical line at a time, with trailing empty fields tolerated, like the export readers". Task 3 does neither: `next(reader, [])` does not skip blank lines before the header, and `len(fields) != 2` rejects a trailing comma.
- **Format B time shape.** The §3 table says `YYYY-MM-DDTHH:MM[:SS[.fff]][offset]`, but the code uses `datetime.fromisoformat`. That also accepts `20260305T143012` and `2026-03-05T14`, which was confirmed by running both. How loose it is depends on the Python version, so the behaviour is not pinned down.
- **Quantity regex.** `\d+` matches non-ASCII digits, and `int()` accepts them. That is unstated behaviour.
- **Bad-row list vs code.** §3 lists "a quantity too long to parse" and "a field the CSV parser rejects" as bad rows. The code catches neither:
  - `int()` on more than 4300 digits raises `ValueError`, which is not `BadRow`, so the run ends in a traceback.
  - `csv.Error` (for example a field over the 131072-character default limit) is not caught either, so that also ends in a traceback.

### 3. Implementability and test strategy

**P: 4.**
- Phases P1–P6 each have a checkpoint.
- Every function has its signature and algorithm in "Target Files".
- A **rule-to-test map** turns every rule ID into concrete input → expected cases, and the coverage gate counts the cases.
- E2E runs through a subprocess, and an in-process backstop test is spelled out.
- Loses a point because there is no code: the engineer still writes all of it, and the test files are pointers to the map rather than written-out tests.

**Q: 4.**
- The most directly implementable of the two: complete module code and complete pytest files, written test-first in seven tasks.
- The expected counts are right: I checked the test counts (5/7/6/10/6) and the `test_full_merge` expected output by hand.
- Loses a point because the given code carries the bugs in §2 above. The tests do not cover the design's own claims: no test for the double match on `sku_text`, the too-long quantity or the csv-error paths. An engineer who "just makes the tests pass" ships the contradictions.

### 4. Proportionality and readability

**P: 2.** About 1,060 lines of dense prose for a tool of about 500 lines. The bloat:
- 12 Alternatives (A–L), several of them trivial (I: `\r\n` vs `\n`; H: writing without a temp file)
- a 12-row Risks table
- decision tags on every bullet
- links to `concepts_brief.md`/`stakeholder_log.md`
- over-engineering for the scope:
  - preserving umask/copymode on `--out`
  - symlink policy
  - hard-link `samefile` checks
  - a check that location names can be encoded as UTF-8
  - typo warnings for near-identical location names (R1.4/R1.5)

The rule-ID structure does make it easy to navigate.

**Q: 3.** The design part (§1–§9, about 140 lines) is about the right size and easy to read. The plan then adds process noise:
- the "For agentic workers: REQUIRED SUB-SKILL" banner
- checkboxes
- "Run test to verify it fails / Expected: FAIL with ModuleNotFoundError" steps
- seven `git commit` blocks

Most of its length is code, which is useful but is an implementation rather than a design.

### 5. Decision quality

**P: 4.**
- Trade-offs are stated with reasons and attributed to the owner or the builder.
- Strict ISO parsing over `fromisoformat` is argued on correctness (aware vs naive datetimes crashing the comparison).
- Rules are matched on the normalised SKU so the category does not depend on which scanner read it.
- Each physical line is one record so an unclosed quote cannot hide scans, with the alternatives weighed (Alt K).
- Invalid UTF-8 is skipped per field to avoid losing scans (Alt L).
- Loses a point for spending effort on low-value hardening, as listed above.

**Q: 3.**
- Some good, reasoned calls:
  - dedup before moves
  - architecture choice over a single script or SQLite, stated in one line
  - the rules double match, whose cost Q states honestly, though the code then does not implement it
  - the k-th kept copy taken from the first export with at least k copies, which is arguably more faithful than P's "first N in input order"
- Weaker spots:
  - making a non-UTF-8 file fatal discards a whole run over one byte
  - accepting and *discarding* timezone offsets silently compares mixed-offset scans as wall-clock time
  - several choices are stated without reasons: `M1` vs zero-padding, case-insensitive headers, rule categories on move rows

---

## Where one specifies and the other is ambiguous or wrong

| Topic | P | Q |
|---|---|---|
| Category of move rows | `Move`, rules not applied (R6.3, quoting the owner) | Not stated in the design; the test implies rule categories. **Direct divergence: acceptance-test risk for one of them.** |
| Which copies dedup keeps (counts 2 vs 3) | e1[0], e1[1], **e2[0]** (first N in input order, R5.4) | e1[0], e1[1], **e2[2]** (k-th copy from the first export with ≥k). Divergent. The output differs only when `sku_text` spellings or positions differ. |
| `move_id` format | `M0001` (R6.4) | `M1` (§6). Divergent. |
| Header case | Exact, case-sensitive (R4.2) | Case-insensitive (§3) |
| Unclosed quote in a note | Each line is one record; following scans kept (R4.12; verified that csv returns the fields in non-strict mode) | Unaddressed; following lines are swallowed |
| Invalid UTF-8 | Skip only rows whose *read* fields are affected (R4.1) | Whole file fatal |
| Timezone offsets / ISO variants | Rejected; strict regex (R4.6) | Accepted, offset discarded; `fromisoformat` is looser than the design's own table |
| Very long quantity | 9-digit limit, row skipped (R4.8) | Design says bad row; code raises `ValueError` and the run ends in a traceback |
| csv field-size or parse errors | Field limit raised; backstop exits 2 (R4.12, G5) | Design says bad row; code does not catch it, so the run ends in a traceback |
| `--out` equals an input | Exit 2 before reading (R2.2) | Unaddressed; the input is overwritten |
| Rules matching on SKU text with zeros | Normalised only, plus a warning (R3.4) | Design says normalised **or** raw; code only normalised (internal contradiction) |
| Rules file: blank lines and trailing commas | Same reader as exports (R3.2) | Design says yes; code says no (internal contradiction) |
| Rule category `Move`/`Uncategorised` | Warning (R3.5) | Unaddressed |
| Stderr summary / counts | Fixed parseable line, `W = R − S − D` | None |
| ASCII-only digits | Yes, `[0-9]` | `\d` (Unicode digits accepted) |
| Output folder missing | Exit 2, `--out` untouched | Same, with a test (`test_missing_output_directory_exits_2`) |
| Ready-to-run code and tests | No (signatures + test map) | **Yes** |

## Recommendation

Hand **P** to an engineer, with an instruction to skip Alternatives, Risks & Limits and the umask/symlink/R1.4–R1.5 hardening on the first pass. It is the one document where a reader can trust every sentence: the rule IDs, the test map and the worked example agree with each other.

Q would get a first commit out faster. But Q would need a pre-flight fix-up before handover:
- reconcile §4 with Task 3
- decide the category for move rows
- handle unclosed quotes, `ValueError` and `csv.Error`
- guard `--out` against naming an input

Once those were fixed, Q would arguably be the better package.

## Estimated reading time (senior engineer, reading properly)

- **P:** about 60–75 min. About 1,060 lines of dense, rule-by-rule prose plus a large test map, all of which has to be held in mind at once.
- **Q:** about 45–60 min. The design section takes about 10 min. Reviewing the roughly 600 lines of module and test code critically, which is needed to find the contradictions above, takes the rest.
