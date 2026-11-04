# Goldfish Review Report

**Target:** `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers-p3/arms/egm/docs/designs/tsinvoice.md` (`FeatureRange, lines 1-543`)

## Reviewer Status

| Reviewer | Status |
| --- | --- |
| `egm-design` | completed |
| `egm-structural` | completed |
| `egm-style` | completed |

## Findings Index

Severity totals after deduplication: 1 Blocker, 9 Major, 22 Nit. Merged findings list every source id.

| id | severity | scope | summary |
| --- | --- | --- | --- |
| egm-structural-1-1 / egm-design-1-1 | Blocker | Whole doc (between L442 and L516) | No Risks & Mitigations section; security not covered at all |
| egm-design-1-2 | Major | Open Questions L71-75; Decisions Log L414-440 | R1.12 (primary user, success criteria) has no decision; "Open Questions: None" is false |
| egm-design-1-3 | Major | Stage 2-3 L202-279; Fatal/Exit tables L377-398 | CSV dialect/strictness unspecified; unterminated quote silently eats rest of file; `csv.Error` unhandled |
| egm-design-1-4 | Major | Stage 3 L244-279 | No upper bound on numbers; timedelta/datetime overflow crashes; huge typos billed silently |
| egm-structural-1-2 / egm-style-1-16 (part) | Major | L528-541 | Additional Resources / Future Improvements are H3 under NFR; promote to H2 |
| egm-structural-1-3 | Major | Overview L20-23 vs Glossary, Stages 2-3 | Traceability claim broken: several designer rules lack [D] tags and log rows |
| egm-style-1-1 | Major | The Problem L34-38 | Duplicate definition and "kept and reported" summary contradict Stage 3/4 rules |
| egm-style-1-2 | Major | G6 L56 vs L231, Stage 4 | "Nothing silent" is absolute but blank records, dedupe and joins emit no message |
| egm-style-1-3 | Major | L207, 211, 239-242, 273, 275 | "empty" vs "blank" used for the same extra-cell check; changes a tested message |
| egm-style-1-4 | Major | L57, L142, L219, Stages 6/9 | "unpriced" / "unrated" / "no rate" synonym drift |
| egm-design-1-5 | Nit | Stage 9 L371-375 | Atomic write: temp cleanup, permissions (0600) and symlink behaviour unstated |
| egm-design-1-6 | Nit | L204-205, L223, L427 | Non-UTF-8 (cp1252/UTF-16) exports fail with an unclear message |
| egm-design-1-7 | Nit | G5 L54-55; L384, L391 | Locale-dependent OS error text weakens "identical stderr" promise |
| egm-design-1-8 | Nit | L215, Stage 6 L321-328 | Zero rate and unrated look identical in output; confirm intended |
| egm-design-1-9 | Nit | Stage 6 L321-323 | Substring pricing can match another client's rule via description |
| egm-design-1-10 | Nit | Glossary L85-88; L440 | NFC then casefold is not fully canonical caseless matching |
| egm-structural-1-4 / egm-style-1-11 | Nit | Stage 3 L244-279 | Field mapping bullet splits Format A/B bullets; bad-row table omits blank-value cases |
| egm-structural-1-5 / egm-style-1-9 | Nit | L214-216, 230, 328, 363-364 | Over-long / awkward line wraps; "So negative rates..." filler |
| egm-structural-1-6 | Nit | Non-Goals L61-69 | Non-Goals not numbered (NG1-n) like G1-G6 |
| egm-structural-1-7 | Nit | CUJs L108-157 | Uneven "When" lines (CUJ 1 command vs prose elsewhere) |
| egm-structural-1-8 | Nit | Decisions Log L414 | Document-wide log buried as last H3 of Technical Plan |
| egm-structural-1-9 | Nit | L25, L159 | Section names differ from standard ("Problem Statement", "Proposed Architecture") |
| egm-style-1-5 | Nit | L11 | "small command-line tool" is a judgement |
| egm-style-1-6 | Nit | L166 | "half-written or truncated" is redundant |
| egm-style-1-7 | Nit | L198 | "keeps it harmless" is subjective |
| egm-style-1-8 | Nit | CUJ 3 L131-133 | "; this is expected" adds nothing |
| egm-style-1-10 | Nit | L182/464-466, L215-216/429/494-497, L421/479-482 | Same rationale repeated in Stage, Log and Alternatives |
| egm-style-1-12 | Nit | Stage 8 L351-353 | "the two cases" implies completeness; same-PATH case is a third |
| egm-style-1-13 | Nit | Decisions Log L424, L440 | Redundant clause; vague "in the same spirit" |
| egm-style-1-14 | Nit | Alternatives L446, 458, 470, 481, 501 | Subjective words and jargon ("Simpler.", "YAGNI.", "costs nothing") |
| egm-style-1-15 | Nit | Alternative H L502-504 | Wrong reason for `round(1.005, 2)`; "Decimal is exact" overstated |
| egm-style-1-16 | Nit | NFR L518-521 | "simple scans" is subjective |

## Prioritized Findings (Blockers -> Major -> Nits)

### Missing Risks & Mitigations section; no security coverage - Severity: Blocker
* **Reviewer Lens:** `egm-structural` (Blocker), `egm-design` (Major); ids egm-structural-1-1, egm-design-1-1
* **Affected Scope:** Whole document; nothing between Alternatives Considered (L442) and Non-Functional Requirements (L516)
* **Discrepancy Description**: The feature-spec standard says the spec must identify failure modes, security implications, scalability limits and their mitigations. Risk content is scattered across Stage 8 (double billing), Stage 9 and Exit codes (atomic write), Alternatives G/I (mispricing) and NFR Performance (L518-521). Security is never mentioned. Implied risks with no home: spreadsheet formula injection (cells starting `=`, `+`, `-`, `@`), leftover `.tsinvoice-*` temp files after a hard kill, `--out` via symlink, substring rate over-match, encoding assumptions (UTF-8 only), no bound on entry length, quadratic scan size limit.
* **Rationale & Recommendation**: Add `## Risks & Mitigations` after Alternatives Considered. For each risk give failure mode, impact, mitigation or accepted limit: double billing (Stage 8 warning), mispricing (fatal bad rates rows; substring over-match), lost time from skipped rows (warnings), malformed CSV (see egm-design-1-3), overflow and implausible values (egm-design-1-4), partial output (temp + `os.replace`), encoding, scaling. Add a short security note: trusted local inputs, writes only `--out` and its temp file, no network or code execution; handle or explicitly accept formula injection and temp/symlink behaviour.

### R1.12 (primary user and success criteria) unrecorded - Severity: Major
* **Reviewer Lens:** `egm-design` (egm-design-1-2)
* **Affected Scope:** Open Questions L71-75; Decisions Log L414-440
* **Discrepancy Description**: L73 says every question is decided and L417 calls the Decisions Log authoritative, but R1.12 ("Your call — pick something reasonable and write down what you chose.") has no entry. No success criteria or acceptance signal beyond the contract.
* **Rationale & Recommendation**: Add a [D] row: primary user is the single freelancer owner running it about every two weeks. State measurable success: all BRIEF acceptance tests pass; every CUJ and worked example is a passing test; minute conservation (input minutes = output worked + deduped + skipped-row minutes, each skip warned); byte-identical reruns; no hand edits to the invoice.

### CSV parsing strictness unspecified; unterminated quote can silently drop the rest of an export - Severity: Major
* **Reviewer Lens:** `egm-design` (egm-design-1-3)
* **Affected Scope:** Stage 2 L202-219, Stage 3 L221-279, Fatal error messages L377-391, Exit codes L393-398, Glossary L96
* **Discrepancy Description**: In Python's default non-strict reader, an unclosed `"` consumes to EOF as one record; the spec yields one `expected 4 fields, got M` warning and every later entry vanishes unnamed, breaking BRIEF goal 1 and G6. `csv.Error` (e.g. 131072-char field limit) has no fatal/exit row, so it surfaces as a traceback with exit 1. Multi-line record line numbering depends on unstated `newline=''`.
* **Rationale & Recommendation**: Specify open/read settings (`newline=''`, `strict=True` or equivalent). Choose one behaviour and add to the tables: (a) any `csv.Error` is fatal `<path>: cannot read: <reason>`, exit 2; or (b) any record spanning multiple physical lines is a bad row with its own reason. Add a worked example with an unterminated quote.

### No upper bound on numeric fields; overflow crashes, typos billed silently - Severity: Major
* **Reviewer Lens:** `egm-design` (egm-design-1-4)
* **Affected Scope:** Stage 3 Format A/B rows L244-261; bad-row reasons table L269-279
* **Discrepancy Description**: `duration_minutes` like `99999999999` passes digit and >0 checks, then `start + timedelta(...)` raises `OverflowError`; Format B starts near 9999-12-31 likewise. Neither is a bad-row reason, so the run crashes (exit 1), against R1.11. A year typo in a desktop End yields a 525,600-minute session priced with no signal, at odds with G6.
* **Rationale & Recommendation**: Map overflow to `invalid duration_minutes` / `invalid end` bad rows. Add a non-fatal warning for any entry or session over a fixed limit (e.g. 24 hours), recorded as [D] with fixed message text.

### Additional Resources and Future Improvements nested under NFR - Severity: Major
* **Reviewer Lens:** `egm-structural` (egm-structural-1-2), `egm-style` (part of egm-style-1-16)
* **Affected Scope:** L528-541
* **Discrepancy Description**: Two H3s follow `## Non-Functional Requirements` with only a horizontal rule (L528), so structurally they are NFR children though they are not requirements.
* **Rationale & Recommendation**: Promote both to H2.

### Traceability claim broken by untagged designer rules - Severity: Major
* **Reviewer Lens:** `egm-structural` (egm-structural-1-3)
* **Affected Scope:** Overview L20-23 vs Glossary and Stages 2-3
* **Discrepancy Description**: The Overview says every rule is cited to an R-number or [D], with the Decisions Log authoritative. Untagged designer rules: NFC in "Normalised text" (L85; has log row L440 but no inline tag), blank-record skipping incl. `,,,` and blank lines before header (L89-92), same PATH twice counts as two exports (L82), extra cells allowed only if empty (L211, L239), case-insensitive trimmed rates header (L206-207; log row L425 covers export headers only), zero rate allowed (L215), touching end-to-start is not overlap (L345).
* **Rationale & Recommendation**: Tag each with inline **[D]** and add a log row, or narrow the claim at L20-23.

### The Problem misstates duplicate and bad-row rules - Severity: Major
* **Reviewer Lens:** `egm-style` (egm-style-1-1)
* **Affected Scope:** L34-38
* **Discrepancy Description**: "identical to one in another export" ignores Stage 4's normalised client/description match and max-count rule. "Anything the rules cannot decide safely is kept and reported" is vague and wrong for bad rows, which Stage 3 skips.
* **Rationale & Recommendation**: Say "matches (after normalising client and description) one in another export of the same tracker." Replace the last sentence with actual behaviours: bad rows skipped with warning; unrated sessions kept at 0.00 with warning; overlapping same-client sessions kept with warning.

### G6 "Nothing silent" is absolute but not true - Severity: Major
* **Reviewer Lens:** `egm-style` (egm-style-1-2)
* **Affected Scope:** G6 L56 vs L231 and Stage 4
* **Discrepancy Description**: Blank records are "skipped silently" (L231); dedupe removals and joins produce no message.
* **Rationale & Recommendation**: Retitle G6 measurably (e.g. "Warn on data problems"), scope it to the listed cases, and state that blank records, dedupe removals and joins are silent.

### "empty" vs "blank" for the extra-cell check - Severity: Major
* **Reviewer Lens:** `egm-style` (egm-style-1-3)
* **Affected Scope:** L207, L211, L239-242, L273, L275
* **Discrepancy Description**: "allowed only if empty" (L207, L239) vs "only if blank" (L273); Glossary defines blank as empty after trimming, so a whitespace-only cell passes one wording and fails the other, changing whether the tested `expected N fields, got M` fires.
* **Rationale & Recommendation**: Use one term (e.g. "blank (empty after trimming)"), defined once in the Glossary, everywhere.

### "unpriced" / "unrated" / "no rate" synonym drift - Severity: Major
* **Reviewer Lens:** `egm-style` (egm-style-1-4)
* **Affected Scope:** L57 (G6), L142 (CUJ 4), L219, Stage 6, Stage 9 item 3
* **Discrepancy Description**: Same state named several ways; reader cannot tell if they differ.
* **Rationale & Recommendation**: Use "unrated session" throughout (matches warning text "no rate") and add it to the Glossary.

### Atomic-write details missing - Severity: Nit
* **Reviewer Lens:** `egm-design` (egm-design-1-5)
* **Affected Scope:** Stage 9 L371-375
* **Discrepancy Description**: Temp-file cleanup on failure unstated; `mkstemp`/`NamedTemporaryFile` create 0600 files, silently tightening `--out` permissions; `os.replace` replaces a symlinked `--out` rather than writing through.
* **Rationale & Recommendation**: Name the API, require unlink on failure, state intended permissions and symlink behaviour.

### Non-UTF-8 exports fail with an unclear message - Severity: Nit
* **Reviewer Lens:** `egm-design` (egm-design-1-6)
* **Affected Scope:** L204-205, L223, Decisions Log L427
* **Discrepancy Description**: cp1252 / UTF-16 desktop exports are plausible; exit 2 is defensible but message is generic.
* **Rationale & Recommendation**: Record the assumption under Risks; consider a specific message on UTF-16 BOM advising re-export.

### Locale-dependent OS error text vs G5 - Severity: Nit
* **Reviewer Lens:** `egm-design` (egm-design-1-7)
* **Affected Scope:** G5 L54-55; Fatal error messages L384, L391
* **Discrepancy Description**: `<OS reason>` (strerror) varies by locale/platform, contradicting "identical stderr".
* **Rationale & Recommendation**: Scope G5 to exit-0 runs or exclude OS reason text explicitly.

### Zero rate indistinguishable from unrated in output - Severity: Nit
* **Reviewer Lens:** `egm-design` (egm-design-1-8)
* **Affected Scope:** L215; Stage 6 L321-328
* **Discrepancy Description**: A rate-0 rule writes `0.00` without warning, same as an unrated row except on stderr.
* **Rationale & Recommendation**: Add a sentence confirming this is intended (e.g. pro-bono clients).

### Substring pricing can match another client's rule - Severity: Nit
* **Reviewer Lens:** `egm-design` (egm-design-1-9)
* **Affected Scope:** Stage 6 L321-323
* **Discrepancy Description**: Owner rule (R1.4), but because description is matched too, client Beta with "call with Acme" is priced by an earlier "acme" rule.
* **Rationale & Recommendation**: Note the limit in Risks and README guidance (specific rules first; avoid short patterns).

### Unicode normalisation order not fully canonical - Severity: Nit
* **Reviewer Lens:** `egm-design` (egm-design-1-10)
* **Affected Scope:** Glossary L85-88; Decisions Log L440
* **Discrepancy Description**: NFC then casefold can produce non-NFC output; canonical caseless form is NFC(casefold(NFC(x))).
* **Rationale & Recommendation**: Adopt the canonical form or accept the gap explicitly.

### Field mapping bullet placement and blank-value reasons - Severity: Nit
* **Reviewer Lens:** `egm-structural` (egm-structural-1-4), `egm-style` (egm-style-1-11)
* **Affected Scope:** Stage 3 L244-261; bad-row table L269-279
* **Discrepancy Description**: The Field mapping bullet (L248, L251-253) sits between Format A and Format B bullets and holds the blank Start / `start_iso` / `duration_minutes` reason rules, which the table's "When" column omits.
* **Rationale & Recommendation**: Keep Format A/B bullets adjacent; add "blank" to the relevant When cells.

### Line wrapping and filler - Severity: Nit
* **Reviewer Lens:** `egm-structural` (egm-structural-1-5), `egm-style` (egm-style-1-9)
* **Affected Scope:** L214-216, L230, L328, L363-364
* **Discrepancy Description**: Lines exceed the ~80-column wrap; L363-364 split "on / stdout"; "So negative rates are rejected" opens with filler.
* **Rationale & Recommendation**: Re-wrap; write "Negative rates are rejected; `-0` cannot occur."

### Non-Goals unnumbered - Severity: Nit
* **Reviewer Lens:** `egm-structural` (egm-structural-1-6)
* **Affected Scope:** L61-69
* **Discrepancy Description**: Goals are G1-G6 and cited; Non-Goals cannot be cited the same way.
* **Rationale & Recommendation**: Number as NG1-NGn.

### Uneven CUJ "When" lines - Severity: Nit
* **Reviewer Lens:** `egm-structural` (egm-structural-1-7)
* **Affected Scope:** L108-157
* **Discrepancy Description**: CUJ 1 gives the full command; CUJs 2-6 use prose.
* **Rationale & Recommendation**: Use one form throughout.

### Decisions Log placement - Severity: Nit
* **Reviewer Lens:** `egm-structural` (egm-structural-1-8)
* **Affected Scope:** L414; references L22-23, L74-75
* **Discrepancy Description**: A document-wide record is the last H3 of Technical Plan.
* **Rationale & Recommendation**: Optionally promote to H2 after Technical Plan.

### Section names differ from standard - Severity: Nit
* **Reviewer Lens:** `egm-structural` (egm-structural-1-9)
* **Affected Scope:** L25, L159
* **Discrepancy Description**: "The Problem" and "Technical Plan (Architecture)" vs standard's "Problem Statement" / "Proposed Architecture" (standard lists are non-exhaustive examples).
* **Rationale & Recommendation**: Rename only if exact alignment is wanted.

### Subjective "small" - Severity: Nit
* **Reviewer Lens:** `egm-style` (egm-style-1-5)
* **Affected Scope:** L11
* **Discrepancy Description**: "small command-line tool" is a judgement.
* **Rationale & Recommendation**: Drop "small" or say "single-user, stdlib-only CLI".

### Redundant "half-written or truncated" - Severity: Nit
* **Reviewer Lens:** `egm-style` (egm-style-1-6)
* **Affected Scope:** L166
* **Discrepancy Description**: Two words for one idea.
* **Rationale & Recommendation**: "a partially written `--out`".

### Subjective "keeps it harmless" - Severity: Nit
* **Reviewer Lens:** `egm-style` (egm-style-1-7)
* **Affected Scope:** L198
* **Discrepancy Description**: Judgement rather than mechanism.
* **Rationale & Recommendation**: "the max-count rule in Stage 4 removes the repeated entries."

### Filler in CUJ 3 - Severity: Nit
* **Reviewer Lens:** `egm-style` (egm-style-1-8)
* **Affected Scope:** L131-133
* **Discrepancy Description**: "; this is expected" adds nothing.
* **Rationale & Recommendation**: End the sentence at "for each pair".

### Rationale repeated across sections - Severity: Nit
* **Reviewer Lens:** `egm-style` (egm-style-1-10)
* **Affected Scope:** Bad-rates-row reasoning L215-216 / L429 / Alt G L494-497; seconds truncation L421 / Alt E L479-482; "Nothing after Phase 1 knows the format" L182 / Alt C L464-466
* **Discrepancy Description**: Same reasoning stated two or three times.
* **Rationale & Recommendation**: State once in the Decisions Log; point to it from Stages and Alternatives.

### "the two cases" implies completeness - Severity: Nit
* **Reviewer Lens:** `egm-style` (egm-style-1-12)
* **Affected Scope:** Stage 8 L351-353
* **Discrepancy Description**: Same PATH under two NAMEs is a third double-billing case (warned in Stage 1).
* **Rationale & Recommendation**: Write "two cases where ..." or list all three, pointing to Stage 1.

### Decisions Log wording - Severity: Nit
* **Reviewer Lens:** `egm-style` (egm-style-1-13)
* **Affected Scope:** L424, L440
* **Discrepancy Description**: L424 "loses nothing and avoids dropping real time" is redundant; L440 "in the same spirit" is vague.
* **Rationale & Recommendation**: Keep one clause at L424; at L440 say "adds NFC as a step before the owner's trim/collapse/case rule (R1.1)".

### Subjective words and jargon in Alternatives - Severity: Nit
* **Reviewer Lens:** `egm-style` (egm-style-1-14)
* **Affected Scope:** L446, L458, L470, L481, L501
* **Discrepancy Description**: "simpler single loop", "Simpler.", "YAGNI.", "contrived cases", "costs nothing".
* **Rationale & Recommendation**: Replace with concrete facts (e.g. "one loop instead of two phases"; "no `Decimal` import"; "A third format is a non-goal"; "datetime arithmetic handles seconds with no extra code").

### Incorrect rounding rationale in Alternative H - Severity: Nit
* **Reviewer Lens:** `egm-style` (egm-style-1-15)
* **Affected Scope:** L502-504
* **Discrepancy Description**: `round(1.005, 2)` gives 1.0 because 1.005 is stored as 1.00499..., not because of half-to-even; "`Decimal` ... is exact" overstates (division by 60 can repeat before `quantize`).
* **Rationale & Recommendation**: "Binary floats cannot represent 1.005 exactly, so `round(1.005, 2)` gives 1.0. `Decimal` with `ROUND_HALF_UP` gives the decimal half-up result the owner specified."

### Subjective "simple scans" - Severity: Nit
* **Reviewer Lens:** `egm-style` (egm-style-1-16)
* **Affected Scope:** NFR L518-521
* **Discrepancy Description**: "simple scans" is a judgement.
* **Rationale & Recommendation**: "linear scans per group; O(n^2) within a client or client+description group".
