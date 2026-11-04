# Requirement discovery scoring (p2)

Sources: `_judge/STAKEHOLDER.md` (K1–K13) and each arm's `stakeholder_log.md`.
Y means a question drew out the policy. Partial means part of it was drawn out, or it was only implied. N means it never came up.

## TL;DR

| Arm | Questions | "Your call" (full / partial) | Y | Partial | N |
|-----|-----------|------------------------------|---|---------|---|
| baseline | 15 | 1 / 3 | 9 | 3 | 1 |
| superpowers | 29 | 7 / 3 | 11 | 2 | 0 |
| egm | 29 | 9 / 3 | 11* | 1 | 1 |

\* EGM got all of K8 and the end of K7 without asking for them (see Fairness F1). If those answers are not counted, EGM scores 9 Y, 3 Partial, 1 N, the same as baseline.

## Coverage

| K | Policy | baseline | superpowers | egm |
|---|--------|----------|-------------|-----|
| K1 | Cross-export duplicate definition, SKU normalisation, quantity in eaches | Y (R1 Q1, Q2, Q4) | Y (1a Q2, Q4) | Y (R1 Q1, Q9) |
| K2 | In-file identical rows are real; take the max across exports | Y (R1 Q1) | Y (1a Q3, R2 Q1) | Y (R1 Q2, R2 Q1) |
| K3 | Different locations never deduplicate | Partial (only implied by "location must match" in K1) | Y (R2 Q5, borderline, see F4) | Y (R2 Q2) |
| K4 | Compare to the minute, seconds dropped, ignore note | Y (R1 Q2, Q3, Q5) | Y (1a Q4, 1b Q7) | Y (R1 Q4, Q7) |
| K5 | case = 12, bad rows skipped with a warning, exit 0 | Y (R1 Q3, Q9)¹ | Y (1a Q5, 1b Q5, R2 Q7) | Y (R1 Q3, Q8)¹ |
| K6 | Unknown header: exit 2, no output | Y (R1 Q9) | Y (1b Q5) | Y (R1 Q8) |
| K7 | Move definition, shared move_id, category `Move`, no rules on moves | Partial (category `Move` and "no rules on moves" never drawn out) | Partial (same gap) | Y* (R1 Q4, volunteered tail) |
| K8 | Move ambiguity, greedy order, tie-breaks | Y (R1 Q5 asked about several candidates) | Y (R2 Q2, R3 Q3) | Y* (volunteered in R1 Q4) |
| K9 | Rules: case-insensitive substring, first match wins, `Uncategorised` | Y (R1 Q7) | Y (1b Q1–Q3) | Y (R1 Q6) |
| K10 | Output order; keep first duplicate by `--location` order | Y (R1 Q8, R2 Q1) | Y (1b Q6) | Y (R1 Q10) |
| K11 | Output SKU is the original text, trimmed | Y (R2 Q1) | Y (1b Q4, R2 Q5) | Y (R2 Q3) |
| K12 | Determinism, byte-identical output | N | Y (1a Q7) | N |
| K13 | Out of scope / local time | Partial (time zones only) | Partial (time zones, pack sizes) | Partial (time zones, pack sizes) |

¹ The rule that Unit is matched ignoring case and outer spaces was not drawn out. Only superpowers asked it (R2 Q7).

## Question counts and uncovered answers

- **baseline**: 15 questions (R1 10, R2 5). One got a full "Your call": R2 Q5, the all-zeros SKU. Three got a partial one: R1 Q6 (move_id format), R1 Q8 (zero-quantity rows), R2 Q2 (do patterns match the raw or the normalised SKU).
- **superpowers**: 29 questions (1a 7, 1b 7, R2 10, R3 3, final 2). Seven got a full "Your call":
  - 1a Q1: the purpose of the output
  - R2 Q3: whether duplicates are removed before moves are matched
  - R2 Q4: whether location names are case-sensitive
  - R2 Q6: zero-quantity rows
  - R2 Q8: missing files, a bad rules header, a blank pattern
  - R2 Q10: `000`
  - final Q1: a rule pattern with leading zeros

  Three got a partial one: 1a Q7 (move_id format), R2 Q7 (how strict header detection is), R2 Q9 (accepting fractional seconds or offsets).
- **egm**: 29 questions (R1 10, R2 11, R3 8). Nine got a full "Your call":
  - R2 Q5: whether duplicates are removed before moves are matched
  - R2 Q6: whether patterns match the raw or the normalised SKU
  - R2 Q7: zero-quantity rows
  - R2 Q8: whether location names are case-sensitive
  - R2 Q9: rules-file errors
  - R2 Q10: the same path given twice
  - R3 Q6: a byte-order mark or CRLF line endings
  - R3 Q7: `5.0` and `+5`
  - R3 Q8: unpadded dates

  Three got a partial one: R1 Q5 (move_id format), R1 Q8 (`--location` without `=`, missing files), R3 Q4 (totals). R3 Q2 was flagged as an interpretation rather than "Your call" (see F3).

## Best uncovered question (a real edge case outside the key)

- **baseline**: R2 Q2. Should rule patterns match the raw SKU or the normalised one? This is a real conflict between K1's leading-zero normalisation and K9's substring match. The runner-up is R2 Q5, the all-zeros SKU (`000`).
- **superpowers**: final Q1. A rule `00123,Drinks`: should it match `123`? This is the same K1/K9 conflict, asked with a concrete example. R2 Q4, whether location names are case-sensitive, is also a good catch.
- **egm**: R3 Q7. Is `5.0` or `+5` a whole number? It is the one parse ambiguity in K5's "isn't a whole number" rule that changes which rows survive. R2 Q6 (the K1/K9 conflict) and R2 Q10 (the same path given twice) are also good.

## Fairness issues (the stakeholder broke its own rules)

- **F1 (EGM was helped, high impact).** EGM R1 Q4 asked only "what has to match and how close in time". The answer also gave away all of K8 (one move per row, closest partner, the full tie-break chain, greedy order) and the end of K7 (category `Move`, no rules on move rows). Baseline had to ask about multiple candidates. Superpowers needed two rounds (R2 Q2, R3 Q3) to get the same information. No arm drew out the end of K7 except EGM, and EGM got it without asking.
- **F2 (baseline was helped, high impact).** Baseline R2 Q4 asked whether duplicates are removed before moves are matched. It got "Yes", plus an extrapolation that in-file identical rows can each pair on their own. The key says neither. Superpowers (R2 Q3) and EGM (R2 Q5) asked the same question and got "Your call". This is an inconsistent ruling, and it should have been "Your call" for everyone.
- **F3 (minor).** EGM R3 Q2 asked whether a SKU gets one spelling or a spelling per row. The key doesn't cover this. The stakeholder made its own call ("the copy you actually kept") instead of saying "Your call". It did flag this as UNCOVERED.
- **F4 (minor volunteering).** These answers went a little beyond the question:
  - Baseline R1 Q1 asked whether in-file identical rows are duplicates. The answer also gave the cross-export max-by-count rule, which EGM (R2 Q1) and superpowers (R2 Q1) had to ask for separately.
  - Superpowers R2 Q5 asked where the first occurrence is taken from. The answer added "different locations never deduplicate" (K3).
  - Superpowers 1b Q6 and EGM R1 Q10 asked only about output order. Both answers added the "keep first duplicate by `--location` order" clause. Both arms got it, so this is neutral between them.
- **Consistent across arms (no issue):** zero-quantity rows, case-sensitive location names, rule patterns with leading zeros, `000`, the unquoted comma in the note (skip as malformed), either order within the 2-hour window, the minute-truncated window, and which copies survive deduplication.

## Bottom line

Coverage of the key is close between superpowers and EGM. Superpowers is the only arm that reached K12 and the Unit case-insensitivity rule. EGM's apparent lead on K7 and K8 comes from F1, not from its questions. Baseline asked half as many questions, missed K12 and K3, and gained one ruling (F2) that the other arms were refused. Before comparing the arms on their outputs, F1 and F2 should be fixed or noted, because they affect move detection (K7/K8) and the dedupe-before-moves behaviour.
