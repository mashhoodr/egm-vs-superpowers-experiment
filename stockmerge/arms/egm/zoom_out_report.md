# Goldfish Review Report

**Target:** `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers-p2/arms/egm/docs/designs/stockmerge.md` (`1-722`)

**Stage:** 5, Initial Zoom Out Review (round 1)
**GoldfishContext:** `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers-p2/arms/egm/BRIEF.md` (fixed contract)

## Reviewer Status

| Reviewer | Status |
| --- | --- |
| `egm-zoom-out` | completed (two independent instances, A and B, both returned full reports) |

**Severity breakdown:** 0 Blocker, 2 Major, 6 Nit.

**Overall verdict (both instances agree):** The design fixes the root problem and stays inside the fixed contract. The context is enough to follow it. The architecture is one straight pipeline of pure functions over a single record type, with I/O kept at the edges. It relies on the stdlib (argparse, csv, tempfile, os.replace, dataclasses) and does not hand-roll anything the stdlib already provides. Rules tagged `[owner]` were treated as settled.

## Prioritized Findings (Blockers -> Major -> Nits)

### zoom-out-1-1: G5 "never ends with an uncaught exception" is not backed by the design - Severity: Major
* **Reviewer Lens:** `egm-zoom-out` (A and B)
* **Affected Scope:** `Lines 47-49` (G5); `Lines 530-533` (readers.py plan); `Lines 622-628` (cli.main)
* **Discrepancy Description**: G5 promises the tool never ends with an uncaught exception. But `main` catches only `StockmergeError` (line 627), and `read_export` wraps only `UnicodeDecodeError`. These can all still escape as a traceback with a non-2 exit code:
  * `OSError` on open (permission denied, a directory, or a file deleted after the check)
  * `OSError` partway through a read
  * `csv.Error`, for example when a field exceeds the size limit
  * any unexpected `ValueError` or `KeyError` in steps 5-8
* **Rationale & Recommendation**: Make G5 true in one place. Add a single top-level handler in `main` that maps `OSError` and `csv.Error` (and, if desired, any other `Exception`) to `stockmerge: error: ...` and exit 2. The alternative is to drop the sentence from G5. Either is a one-line change. The goal and the plan must agree. See zoom-out-1-2, which relies on this handler.

### zoom-out-1-2: Step 2 path pre-checks duplicate open-time errors and add a race window - Severity: Major
* **Reviewer Lens:** `egm-zoom-out` (A and B; B rated it Major-leaning-Nit)
* **Affected Scope:** `Line 153` (pipeline step 2); `Lines 223-229` (R2.1, R2.2); `Lines 353-354` (messages table)
* **Discrepancy Description**: R2.1 checks that each input file and the rules file exist and are readable. Opening them in steps 3-4 already reports the same failures, before anything is written. R2.2's check that the `--out` folder exists repeats what `NamedTemporaryFile` in step 9 already raises, and R9.3 already turns that into exit 2 without touching `--out`, so G6 holds. These checks change no behaviour. They add a check-then-open (TOCTOU) race window, a pipeline stage, message-table rows and tests.
* **Rationale & Recommendation**: Remove R2.1 and the folder-exists half of R2.2. Let open-time `OSError` in steps 3, 4 and 9 go to the single handler from zoom-out-1-1. Keep only R2.2's `realpath` check that `--out` is not an input or the rules file. No other step gives that protection: without it, `os.replace` would overwrite an input after it was read.

### zoom-out-1-3: Builder-added diagnostics with no stated owner need - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A and B)
* **Affected Scope:** `Lines 216-221` (R1.4, R1.5); `Lines 242-246` (R3.4 leading-`0` pattern warning, R3.5 Move/Uncategorised category warning); `Line 541` (R4.2 empty-file / "no valid rows" warnings)
* **Discrepancy Description**: The design adds several warnings for possible user mistakes that the brief never asks for. Each costs code, a test and a README entry. Together they are speculative surface (YAGNI).
* **Rationale & Recommendation**: Keep R1.4. Location names that differ only by case or spaces silently turn off dedup and can create false moves, so that failure mode is real. Move R1.5, the R3.4 leading-`0` warning, R3.5 and the R4.2 empty-file warnings to Future Improvements, unless the owner confirms them.

### zoom-out-1-4: Categorisation and sorting live in the writer, contradicting the pipeline diagram - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A and B)
* **Affected Scope:** `Lines 168-171` (diagram steps 7-8); `Lines 601-604` (writer.build_rows); `Lines 504-522` (model.py)
* **Discrepancy Description**: The diagram shows "categorise" and "sort" as their own stages. The plan does both inside `writer.build_rows`, so the output module depends on `rules.categorise` and business logic sits in the output layer. Separately, `Scan.ident` and `input_order()` return the same `(arg_index, record_no)` tuple.
* **Rationale & Recommendation**: Make categorisation (and row-building) its own function, for example in `rules.py` or a small pipeline function called from `cli.py`. Then `writer.py` only formats and writes, and the diagram matches the plan. Keep either `ident` or `input_order`, not both.

### zoom-out-1-5: `Warnings` collector class conflicts with print-as-collected behaviour - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A and B)
* **Affected Scope:** `Lines 520-522` (class Warnings); `Lines 625-626` (cli.main)
* **Discrepancy Description**: `model.py` defines a collector that stores warning strings in order. But `cli.main` prints each warning to stderr "as it is collected". The two passages describe two mechanisms for one job, and they read as contradictory.
* **Rationale & Recommendation**: Choose one. Either pass a plain `warn(path, line, reason)` callable that writes to stderr into the readers and the rules loader, or use a plain list that the CLI prints at the end. If collecting is needed (for example, to count warnings for the summary line), say so.

### zoom-out-1-6: `Scan.path` and `Scan.line` are carried but never used - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A and B)
* **Affected Scope:** `Line 190` (record-type table); `Line 511` (model.py Scan)
* **Discrepancy Description**: The fields exist "for warnings", but every row-level warning is raised in step 4, where the parser still has the path and the line number. Steps 5-9 never warn per row, and the output does not include these fields.
* **Rationale & Recommendation**: Drop `path` and `line` from `Scan`, or name the later step that needs them.

### zoom-out-1-7: Implementation detail leaks into the rules spec (and, per B, into the plan) - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A: rules section; B: implementation plan)
* **Affected Scope:** `Lines 200-345` (Rules, e.g. R2.2 `os.path.realpath`, R4.5 `datetime.strptime`, R9.3 `os.replace`); `Lines 514, 537-540, 552-556, 605-609` (Detailed Implementation Plan one-liners)
* **Discrepancy Description**: The R-rules are a behaviour spec, which is the right altitude, but some of them name specific stdlib calls. Instance B also flagged code-level detail in the Detailed Implementation Plan: the normalisation expression, `line_num + 1` arithmetic, regex-then-`strptime` on 19 chars, and the full `NamedTemporaryFile` arguments. Instance A judged the plan's detail acceptable for a section with that name.
* **Rationale & Recommendation**: State the rules as behaviour, for example "the `--out` path must not resolve to any input file", and leave the calls to the implementation plan. Optionally trim the plan to responsibilities, signatures and data flow, since the R-rules and tests already pin the behaviour. The reviewers disagreed on the plan part, so it is low priority.

### zoom-out-1-8: `[owner]` decisions are not traceable from the brief, notably R6.3 `Move` category - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A)
* **Affected Scope:** `Lines 73-78` (Open Questions); `Lines 478-480` (Additional Resources); R6.3 / G2; all `[owner]` tags
* **Discrepancy Description**: Every `[owner]` decision points to `concepts_brief.md` and `stakeholder_log.md`, which a reader who has only BRIEF.md cannot see. R6.3 gives move rows the category `Move` and skips the rules. That departs from the brief's literal "Everything categorised by my rules".
* **Rationale & Recommendation**: Cite the owner's answer for R6.3 inline, in a short quote or one line, so the approved departure from the contract is visible in the design itself.

## Deliberately Not Flagged (both instances)

* One output row per scan rather than totals per SKU per location: the fixed contract requires it, and the R8.1 sort order covers grouping.
* Grouping positives by `(sku_norm, qty_each)` for move matching: this is the natural way to express the rule, not premature optimisation.
* Temp file plus `os.replace` (R9.3): minimal, stdlib, and needed for G6.
* `[owner]` rules R5.4 (max-N dedup) and R6.2 (greedy move matching): settled by the owner.
