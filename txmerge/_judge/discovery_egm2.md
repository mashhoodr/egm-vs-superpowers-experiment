# Discovery score: egm2

Source: `arms/egm2/stakeholder_log.md` (4 rounds: R1 12 Qs, R2 10 Qs, R3 4 Qs, Stage-7 1 Q).
Strictness matches the baseline and superpowers scoring. A policy counts as **Y** only if a question the team asked drew it out. Policy the stakeholder volunteered earns no credit.

**Score: 11 Y, 1 Partial, 1 N (27 questions)**

## 1. Coverage

| Key | Policy | Score | Drawn out by |
|-----|--------|-------|--------------|
| K1 | Dedup identity + normalisation | Y | R1 Q1 |
| K2 | Identical rows real; max count across exports | Y | R1 Q2 (also R2 Q10) |
| K3 | Different accounts never dedup | Y | R1 Q12 (two names, same file) |
| K4 | Format B uses Transaction Date | Y | R1 Q3 |
| K5 | Format A sign; skip+warn malformed, exit 0 | Y | R1 Q9 ("unparseable amount... skip and warn?"). The sign mapping in the answer was volunteered, but the skip/warn/exit-0 core was asked for. |
| K6 | Unknown header: exit 2, no output | Y | R1 Q9 |
| K7 | Transfer definition, 3 days inclusive, category, no rules | Y | R1 Q4, Q6; R2 Q5 |
| K8 | Transfer ambiguity / tie-breaks | Y | R1 Q5 |
| K9 | Rules: case-insensitive substring, first wins, Uncategorised | Y | R1 Q7 |
| K10 | Output order + first occurrence by `--account` order | Y | R1 Q8 |
| K11 | Description text: first occurrence, trimmed, case kept | Y | R3 Q3. It was first volunteered in R1 A8, then asked about directly. |
| K12 | Byte-identical determinism | N | Never asked. Only volunteered in R1 A8. |
| K13 | Out of scope (currency, incremental, GUI, fuzzy) | Partial | R1 Q10 drew out "incremental is out" and R1 Q1 touched fuzzy matching. Currency was not drawn out: R2 Q2 asked about currency symbols and got "Your call". GUI was never asked. |

## 2. Question counts

- **Total:** 27 questions (12 + 10 + 4 + 1).
- **Fully "Your call" (10):** R1 Q11, R2 Q1, Q2, Q3, Q4, Q7, Q8, Q9, R3 Q1, Q4.
- **Partly "Your call" (4):** R1 Q6 (transfer_id format), R1 Q9 (missing file, malformed rules file), R1 Q12 (one name given both formats), Stage-7 Q1 (whether amounts are quoted).
- **Total "Your call" answers:** 14 (10 full, 4 partial). 13 questions were fully answered from the key.

## 3. Best uncovered question

**R3 Q1: is a `0.00` in the unused Debit/Credit column blank or filled?**
This is real bank-export behaviour. It decides whether a common row shape counts as a normal row or as a malformed one under K5. The key's "both blank" test doesn't settle it, and if it's handled wrong, valid rows get dropped silently.

Runners-up:
- R2 Q1: Debit and Credit both filled.
- R3 Q4: two account names pointing at one file, so the file's rows pair with each other as transfers. This is a K3 × K7 interaction.
- R2 Q4: zero-amount rows taking part in transfers.

## 4. Stakeholder rule breaks

**Volunteered policy that wasn't asked for:**
- **R1 A8.** The question asked only about output order. The answer also gave K11 (description text) and K12 (determinism). This is the clearest break, and the only reason K12 appears in the log at all.
- **R1 A9.** The question asked about bad input. The answer added the K5 sign convention ("Debit becomes negative and Credit positive").
- **R1 A6.** The question asked about the category and transfer_id. The answer added "Rules are not applied to transfer rows" (part of K7).
- **R1 A1 (minor).** The answer added "Fuzzy description matching is out of scope". This is arguably a response to the "truncated text" sub-question.

**Policy invented beyond the key:**
- **R3 A2.** The stakeholder said to match rules against the description "with outer spaces trimmed" and that "inner whitespace is not collapsed". K9 says only "case-insensitive substring of the description" and says nothing about trimming or collapsing for rules. The correct reply was to restate K9 and call the rest "Your call". This is the one real deviation from the key.
- **R3 A3 (mild extension).** "All three copies use the first-ever occurrence's text" stretches K10/K11's "first occurrence" to cover extra copies that only exist in a later export. It's a defensible reading, but the key doesn't state it.
- **Derived from the key, acceptable:**
  - R1 A4: a card payment counts as a transfer.
  - R1 A12: "even if they point at the same file".
  - R2 A6: refund pairing.
  - Stage-7 A1: don't repair split rows, skip them.

## Comparison

| Arm | Y | Partial | N | Questions |
|-----|---|---------|---|-----------|
| baseline | 9 | 1 | 3 | 14 |
| superpowers | 10 | 1 | 2 | ~20 sub-questions |
| **egm2** | **11** | **1** | **1** | **27** |

egm2's extra coverage comes from K11 (asked about in R3) and from the rounds after the review, which produced the most edge cases outside the key. Its only N, K12, was never asked.
