# Requirement discovery scoring

Sources: `_judge/STAKEHOLDER.md` (K1–K13) and each arm's `stakeholder_log.md`.

## TL;DR

| Arm | Y | Partial | N | Questions | Any "Your call" (fully / partly) |
|-----|---|---------|---|-----------|----------------------------------|
| baseline | 10 | 3 | 0 | 18 (2 rounds) | 6 (2 / 4) |
| superpowers | 11 | 2 | 0 | 11 multi-part turns (Q10 has 6 sub-asks, Q11 has 2) | 4 (1 / 3) |
| egm | 12 | 1 | 0 | 32 (4 rounds) | 11 (9 / 2) |

No arm missed a policy outright. The differences are in the second clauses: K2's max-not-sum rule and K10's keep-first-occurrence rule.

Fairness: one real inconsistency between arms. Superpowers was told a lone entry's session_id is blank. Baseline asked the same thing and got "Your call" (see the fairness section below).

---

## Baseline

| K | Score | Evidence |
|---|-------|----------|
| K1 | Y | R1 Q1 |
| K2 | Partial | R2 Q1 drew "identical entries in one file are real". The max-not-sum count across exports was never drawn. |
| K3 | Y | R1 Q1 ("only between exports of the same tracker?") |
| K4 | Y | R1 Q9 |
| K5 | Y | R1 Q11, R1 Q8 (non-whole duration) |
| K6 | Y | R1 Q11 |
| K7 | Y | R1 Q4 (gap, normalised match), R2 Q2 (cross-tracker chains), R2 Q3 (tie-break), R1 Q5 (distinct id) |
| K8 | Y | R1 Q8, R2 Q5 |
| K9 | Y | R1 Q6, Q7 |
| K10 | Partial | Sort order (R1 Q10) and date (R1 Q9) drawn. Keep-first-occurrence by `--tracker` order was not drawn. |
| K11 | Y | R1 Q5 |
| K12 | Y | R1 Q5 ("stable across runs") |
| K13 | Partial | Only time zones and midnight came up (R1 Q9) |

- **Questions:** 18 (11 + 7). Six got "Your call". Fully uncovered: R2 Q6 (rates-file problems) and R2 Q7 (tracker-name case). Partly uncovered: R1 Q8 (seconds), R1 Q11 (missing rates file), R2 Q4 ("30.0") and R2 Q5 (single-entry session_id).
- **Best uncovered question:** R1 Q8, seconds in ISO times. It changes how the 2-minute continuation gap is measured. Runner-up: R2 Q7, whether "Desktop" and "desktop" are the same tracker. That one decides K1/K3 grouping, and only this arm asked it.
- **Stakeholder rule breaks:**
  - R1 A3 volunteered the continuation rule ("doesn't continue it either"). The question was about overlap merging only.
  - R2 A4 confirmed that Format A minutes are End minus Start. The key implies this but never states it. It's a mild ruling, and harmless.
  - R2 ended with a bracketed "Judge log" line, leaked to the builder. That breaks "don't comment".

## Superpowers

| K | Score | Evidence |
|---|-------|----------|
| K1 | Y | Q1 |
| K2 | Y | Q1 (in-file twins are real, plus the max count) |
| K3 | Y | Q2 |
| K4 | Y | Q6 |
| K5 | Y | Q4 (non-whole duration), Q7(a) |
| K6 | Y | Q7(b) |
| K7 | Y | Q3 (gap, chains), Q4 (overlap is no join), Q9 (one predecessor and one successor, smallest gap, input-order tie, cross-tracker) |
| K8 | Y | Q4, Q5 |
| K9 | Y | Q5 |
| K10 | Partial | Sort order (Q8) and date (Q3) drawn. Keep-first-occurrence by `--tracker` order was not drawn. |
| K11 | Y | Q3 |
| K12 | Y | Q8 |
| K13 | Partial | Time zones (Q6) and midnight (Q3) only |

- **Questions:** 11 multi-part turns. Four got "Your call". Fully uncovered: Q11 (encoding, date-only `start_iso`). Partly uncovered:
  - Q7: bad `--tracker` argument or path, bad rates file, output-file behaviour on other failures
  - Q8: session_id format, and stability when `--tracker` order changes
  - Q10: (b), (c) "30.0", (d) seconds, (e) empty pattern, (f) BOM and header spaces
- **Best uncovered question:** Q11.1, a non-UTF-8 (Windows-1252) export. It's a realistic failure for two consumer apps. Runner-up: Q8, whether session_id stays the same when the `--tracker` order changes.
- **Stakeholder rule breaks:**
  - **Q10(a) ruled on uncovered ground:** "Only joined chains get a non-empty session_id, so a lone entry's session_id is blank." K7 only says chains get a non-empty, distinct id. It says nothing about singletons. Baseline R2 Q5 asked the same question and got "Your call". This is a cross-arm fairness problem (unless BRIEF.md specifies it; I didn't check, since BRIEF.md was outside the four files).
  - Q1 A volunteered K2's max-not-sum rule. Only in-file twins were asked about.
  - Q9 A extended the tie-break to "one entry could continue two earlier sessions". This follows from "work in start order", and egm got the same reading (R2 A3), so it's consistent.
  - Meta text leaked into answers: Q5 ("none uncovered"), Q8 ("I answered from the stakeholder rules… log as UNCOVERED"), Q7 and Q11 (judge notes).

## EGM

| K | Score | Evidence |
|---|-------|----------|
| K1 | Y | R1 Q1, Q10 |
| K2 | Y | R1 Q1 (in-file twins plus the max count) |
| K3 | Y | R1 Q1 |
| K4 | Y | R1 Q6 |
| K5 | Y | R1 Q11, R2 Q4 |
| K6 | Y | R1 Q11 |
| K7 | Y | R1 Q3, R2 Q2, Q3, R3 Q3, Q4 |
| K8 | Y | R1 Q5, R2 Q1, Q9 |
| K9 | Y | R1 Q4, R3 Q9 |
| K10 | Y | R1 Q9 (sort), R1 Q6/Q7 (date), R3 Q2 (keep first occurrences by `--tracker` order) |
| K11 | Y | R1 Q8, R3 Q1 |
| K12 | Y | R3 Q6 |
| K13 | Partial | Time zones, DST and midnight (R1 Q6, Q7), incremental runs (R3 Q6), fuzzy matching (volunteered in R1 A2). Currencies and GUI never came up. |

- **Questions:** 32 (12 + 10 + 9 + 1). Eleven got "Your call". Fully uncovered:
  - R1 Q12 (main user)
  - R2 Q5 (header strictness), Q6 (missing files, bad rates, bad `--tracker` argument), Q7 (tracker identity), Q8 (empty output), Q10 (overwrite, stdout)
  - R3 Q5 (broken rates row), Q7 (overlap double-billing warning), Q8 (blank client or description)

  Partly uncovered: R1 Q8 (session_id format) and R2 Q4 ("30.0", seconds).
- **Best uncovered question:** R3 Q7. The rules can bill the same time twice: an edited entry is kept twice, and work timed in both apps is kept twice. It asks whether to warn. It's a genuine billing-risk edge case outside the key. Runner-up: R3 Q8, blank client or description.
- **Stakeholder rule breaks:**
  - R1 A2 volunteered "There's no fuzzy matching" (K13). Nobody asked about fuzzy matching.
  - R1 A3 volunteered the start-order and smallest-gap tie-break. The question asked only about gap and match fields.
  - R3 A9 ("warn for each output row") ruled on per-row vs per-distinct warnings. K9 doesn't settle that; one warning per unmatched row is a reasonable reading, but it is a ruling.
  - R4 A1 ruled that an unclosed quote is one bad row and the run continues. This leans on K5 ("any unparseable row is skipped") and is defensible. But superpowers Q11.2 (date-only `start_iso`, arguably also "unparseable") got "Your call". The stakeholder was stricter there.
  - R3 ended with a "Log: … UNCOVERED" line, a small meta leak.

## Fairness issues (cross-arm)

1. **Single-entry session_id (material).** Superpowers Q10(a) was told "blank", while baseline R2 Q5 got "Your call" for the same question. egm never asked. If the graded output checks for a blank session_id on singletons, superpowers had an unearned answer. Check BRIEF.md: if it already says unjoined rows have a blank id, this goes away.
2. **"Unparseable" read inconsistently (minor).** egm R4 got a K5-based ruling on a malformed CSV quote. Superpowers Q11.2 got "Your call" for a date-only datetime.
3. **Consistent where it matters.** "30.0", seconds in ISO times, rates-file problems and the session_id format got "Your call" in every arm that asked.
4. **Volunteering (all arms, small).** Each arm got at least one unasked policy fragment: baseline K7, superpowers K2 max count, egm K7 tie-break and K13 fuzzy. This most helped superpowers on K2, which baseline never drew.
5. **Meta leakage (all arms).** Every arm's stakeholder emitted judge or UNCOVERED notes to the builder. It reveals nothing beyond the "Your call" replies, so the impact on fairness is low.
