# Stage 6: Comprehension Report

**Target:** `docs/designs/txmerge.md` (FeatureRange 1-284, DetailedRange 285-415) · Reviewer: `egm-comprehension` (completed)

### What this proposes
`txmerge`, a stdlib-only Python CLI that merges several bank CSV exports (Format A current account, Format B card) into one sorted ledger CSV, through an eight-stage in-memory pipeline: parse arguments; read exports detecting format from header; read rules; dedup per account (key = account, date, amount, normalised description; keep largest single-export count, first N by (export index, line)); sort by (date, account, export index, line); greedy transfer pairing (each outflow in output order with the closest unpaired same-absolute-amount inflow in a different account within 3 days; category `Transfer`, ID `T0001`...); categorise others by first case-insensitive substring rule else `Uncategorised`; write via temp file + rename. Malformed row: `PATH:LINE` warning, exit 0. Fatal input/rules/output problem: exit 2, existing ledger untouched. Internal bug: exit 1.

### How the existing system works, per this document
No existing code. Today the user has overlapping CSV exports with duplicated transactions, card payments double-counted as spending and income, and no categories. Fixed contract from BRIEF.md; behaviour rules from the stakeholder log.

### Findings
1. **Major** (L26 vs L147, L276, L387): G2 says *every* outflow with a matching inflow is paired; greedy pairing means an outflow can stay unpaired when an earlier one took the inflow. Reword G2.
2. Nit (L253-259): "S/E" tag undefined in the legend; [B] unused.
3. Nit (L185): Alternative B quotes "never lose a real transaction" as G1 wording; it is BRIEF item 1.
4. Nit (L214): Alternative G "sort position undefined" is vague.
5. Nit (L164, L323): `[FOUND]` brackets literal or placeholder?
6. Nit (L326): "normalise zero" overloads the term "normalise".
7. Nit (L168, L334): rules-row warning reasons not given.
8. Nit (L77, L162-168): PATH as typed or resolved?
9. Nit (L119-155): no Stage 3 (rules) subsection.
10. Nit (L3, L415): "EGM arm", "Elephant", "Drafted with EGM" undefined.

Paraphrase matches the brief and stakeholder log on every behavioural point; the only mechanism gap is finding 1.

## Elephant disposition
Applied 1-9. Declined 10 (metadata; the template footer is required by egm-draft).

## Re-audit (round 2, cap reached)
Reviewer `egm-comprehension` (completed): 0 Blocker, 1 Major, 7 Nit.
1. Major: errors table and `formats.detect` give different messages for an empty input file. **Fixed** (table now has a separate empty-file row).
2. Nit: rules-file error row mixed two messages. **Fixed** (split into two rows).
3. Nit: G2 uses "output order" before Definitions. **Fixed** (pointer added).
4. Nit: no Stage 1 / Stage 5 subsections. **Fixed** (pointer sentence).
5. Nit: Decision Log legend hard to scan. **Fixed** (list).
6. Nit: EGM metadata terms undefined. Declined (template provenance).
7. Nit: summary "read R" vs parsed. **Fixed** ("parsed R", counts defined in table).
8. Nit: coverage claim unverifiable; D13/D16 tests. **Fixed** (scope reworded; D13 covered by subprocess stdout check; D16 exempt).
Paraphrase still matches stakeholder intent. 1-audit cap reached; residual: none open above Nit.
