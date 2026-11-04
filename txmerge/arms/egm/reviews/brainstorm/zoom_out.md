# Brainstorm Goldfish: egm-zoom-out (summary of raw report)
1. Major: pipeline stage order unstated (parse -> dedup per account -> sort -> link transfers -> rules -> write).
2. Major: which physical copies survive max-count dedup unstated; rule: keep first N occurrences in input order, N = largest per-export count.
3. Major: byte format unpinned: UTF-8 no BOM, explicit line endings, >2-decimal amounts malformed (not rounded).
4. Major: failure atomicity: build ledger in memory, open --out only after all validation; existing file untouched on exit 2.
5. Nit: two plain parse functions, no format registry; strptime accepts single-digit day/month — decide deliberately.
6. Nit: match rules on normalised description (consistent with dedup).
7. Nit: success summary is YAGNI; omit or fixed single line.
8. Nit: empty file = unrecognised header; negative Debit/Credit malformed; empty Format B amount malformed; split --account on first '='; empty NAME/PATH exit 2; account sort is case-sensitive ordinal; same file under two names can self-pair as transfer — accept.
9. Nit: confirms cuts (no balance reconciliation, no fuzzy, no regex, greedy transfers).
