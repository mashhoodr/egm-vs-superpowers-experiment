# Requirement discovery scoring

Sources: `_judge/STAKEHOLDER.md` (key K1–K13) and the three `arms/*/stakeholder_log.md` files.

## TL;DR

| Arm | Y | Partial | N | Questions | "Your call" items |
|---|---|---|---|---|---|
| baseline | 9 | 1 (K5) | 3 (K11, K12, K13) | 14 in 1 round | 3 (1 whole question, 2 sub-parts) |
| superpowers | 10 | 1 (K5) | 2 (K12, K13) | 7 prompts (about 20 sub-questions) | 5 (1 whole, 4 sub-parts) |
| egm | 11 | 1 (K13) | 1 (K12) | 24 in 4 rounds | 15 sub-parts (6 whole questions) |

- No arm asked about determinism (K12).
- No arm asked an explicit scope question, so K13 surfaced only once, as a side remark to EGM.
- Fairness: one clear inconsistency, which went in EGM's favour (EGM R3 Q6). Two smaller stretches. Details below.

## Coverage tables

Y means a question drew out the policy. Partial means some of it came out. N means nothing did. The cell gives the question that drew it out.

| Key | baseline | superpowers | egm |
|---|---|---|---|
| K1 duplicate identity + normalisation | Y (Q1, Q3) | Y (Q2) | Y (R1 Q1–2) |
| K2 within-file real, max-count across | Y (Q2) | Y (Q2) | Y (R1 Q1) |
| K3 accounts never dedup | Y (Q13) | Y (Q6.3) | Y (R2 Q6, R2 Q3) |
| K4 Transaction Date | Y (Q4) | Y (Q6.1) | Y (R1 Q3) |
| K5 sign + skip/warn/exit 0 | Partial: skip and warn only, sign never asked (Q12) | Partial: skip and warn only, sign never asked (Q6.2) | Y (R1 Q8, R2 Q2 sign) |
| K6 unknown header → exit 2 | Y (Q12) | Y (Q6.2) | Y (R1 Q8) |
| K7 transfer definition | Y (Q5, Q7, Q8) | Y (Q3, Q4) | Y (R1 Q4) |
| K8 transfer ambiguity | Y (Q6) | Y (Q3) | Y (R1 Q5) |
| K9 rules | Y (Q9, Q10) | Y (Q5) | Y (R1 Q6) |
| K10 output order + first-occurrence | Y (Q11) | Y (Q4) | Y (R1 Q7) |
| K11 output description text | N | Y (Q4) | Y (R2 Q1, R4 Q1) |
| K12 determinism | N | N | N |
| K13 out of scope | N (Q14 catch-all → "Your call") | N | Partial (R1 Q2: fuzzy matching only) |

## Uncovered questions

**baseline: 3 items.** Transfer_id format (Q7 part), missing file (Q12 part), and "anything else?" (Q14, the whole question).
- Best edge case: **a missing input file (Q12).** It is the only substantive uncovered question. Silently skipping the file would lose transactions.

**superpowers: 5 items.** Purpose and worst failure (Q1, the whole question), transfer_id format (Q4), whether rules apply to inflows (Q5), missing file (Q6), and `0.00` in the unused Debit/Credit column (Q7.1).
- Best edge case: **`0.00` written in the unused column (Q7.1).** This is a realistic bank-export quirk. It decides whether a whole class of rows gets dropped as "both filled".

**egm: 15 items.** Transfer_id, missing file, Balance column, Format B separators/currency, zero amounts, original vs normalised text for rule matching, blank pattern lines, missing or bad rules file, warn/refuse on a repeated path, input quirks (BOM, blank lines, quoted commas), success summary, whether the same path twice counts as two exports, amounts with more than 2 decimals or a negative cell, dates without leading zeros, and `--out` equal to an input.
- Best edge case: **`--out` pointing at an input export or the rules file (R4 Q2).** It is a real data-loss path that the key ignores.
- Runners-up: zero amounts (R2 Q4) and amounts with more than 2 decimals (R3 Q2).

## Fairness issues (stakeholder broke its rules)

1. **EGM R3 Q6 contradicts R2 Q5, and the new answer is not in the key. This favours EGM.**
   - In R2 Q5, the question "should a rule match the original or the normalised description?" was logged UNCOVERED ("Your call").
   - In R3 Q6, the same question got a firm policy: "match against the description as written, trimmed only. Collapsing inner whitespace is part of the duplicate test, not the rules."
   - K9 says only "case-insensitive substring of the description". The stakeholder invented the trimmed-only rule and handed EGM a decision that the other arms had to make alone.
   - Fix: treat the R3 Q6 answer as UNCOVERED when scoring EGM's spec, and don't penalise other arms that chose differently.

2. **Superpowers Q7.2 stretched the key. The effect on the arm is mixed.** An unclosed quote that breaks CSV parsing of the rest of the file was answered as a per-row malformed case under K5 ("carry on, skip the row, exit 0"). The key only covers malformed *rows*, and this case is arguably file-level. It should probably have been "Your call". Superpowers then had to build line-at-a-time parsing to honour it.

3. **Minor volunteering. Neutral because the policy was asked elsewhere in the same round or is consistent across arms.**
   - Baseline Q12 and EGM R1 Q8: the "both Debit and Credit **blank**" rule was added when the question only named "both filled".
   - EGM R1 Q4: `transfer_id` and category `Transfer` were stated before they were asked. EGM R1 Q6 asked about the category anyway.
   - Superpowers Q3: "No matching inflow → normal spending" was asked. It is a fair inference from K7.

4. **Same ruling in all three arms, not in the key.** "Both Debit and Credit filled = malformed" was ruled the same way in all three arms. The key only names "both blank or malformed", but the ruling was consistent, so there is no fairness impact.

5. **Baseline Q14** ("any other behaviours?") got "Your call". The rule against volunteering was applied correctly. It is also why baseline missed K11–K13 rather than being told them.
