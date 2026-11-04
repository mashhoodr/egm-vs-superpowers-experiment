# Stakeholder log

## Phase: egm-brainstorm, Step 1 (clarification), round 1

**Questions**
1. When the same account's exports overlap, what makes two rows "the same transaction"? Can the description, date, or amount of one transaction differ between two exports (e.g. truncated text, pending vs posted)?
2. Within a single export, can two genuinely separate transactions look identical (same date, description, amount — e.g. two identical coffees on one day)? If so, and two overlapping exports both contain that pair, how many should the ledger keep?
3. For credit-card (Format B) rows, which date should the ledger use — Transaction Date or Posting Date?
4. How should a transfer between my own accounts be recognised? Same amount with opposite sign in two different accounts — within how many days of each other? Should descriptions matter? Does paying the credit card from the current account count as a transfer?
5. If one outflow could match several possible inflows (ambiguous transfer), what should happen?
6. What category should transfer rows get, and what should a transfer_id look like?
7. How should rule patterns match descriptions — substring, case-insensitive, regex, whole word? If several rules match, which wins? What category do rows get when no rule matches?
8. What order should the output rows be in?
9. What should happen with bad input — an unrecognised header, an unparseable date or amount, a missing file, a malformed rules file? Fail the whole run, or skip and warn?
10. Should a run ever read or merge with an existing LEDGER.csv at --out, or always rebuild from the inputs and overwrite?
11. Is the Balance column in Format A useful for anything (e.g. checking for missing rows), or ignore it?
12. Can the same account NAME be given exports in both formats, and can two different account names point at the same file?

**Answers (verbatim)**

1. Two rows are the same transaction when the account, date, amount and normalised description all match. To normalise a description, trim the outer spaces, collapse any run of inner whitespace to one space, and ignore case. Nothing beyond that is tolerated. Truncated text, a different date or a different amount makes it a different transaction. Fuzzy description matching is out of scope.

2. Yes. Two £3.50 coffees on the same day in the same file are two real purchases, so keep both. Across exports of one account, match by count and keep the maximum, not the sum. If export 1 has the row 2 times and export 2 has it 3 times, the ledger has it 3 times.

3. Use Transaction Date and ignore Posting Date.

4. A transfer is an outflow in one account and an inflow of exactly the same absolute amount in a different account, with dates at most 3 days apart (inclusive). Descriptions play no part. Paying the credit card from the current account counts as a transfer if it meets that test.

5. Each row can be in at most one transfer. Work through the outflows in output order. Pair each outflow with the inflow closest in date. If two are equally close, pick the inflow that comes first in output order.

6. Both rows of a transfer get the category `Transfer` and the same non-empty transfer_id. Rules are not applied to transfer rows. On the exact format of the transfer_id: your call — pick something reasonable and write down what you chose.

7. A pattern matches if it is a case-insensitive substring of the description. No regex or whole-word matching. When several rules match, the first one in file order wins. Rows that match no rule get `Uncategorised`.

8. Sort by date, then account name, then the order the row appeared in its input. Where there are duplicates, keep the first occurrence by `--account` argument order. Use the original description text from that first occurrence with the outer spaces trimmed, and don't lowercase it. The same inputs in the same order must give byte-identical output.

9. 
   - **Unrecognised header:** if a file matches neither format, exit with code 2 and a message, and write no output file.
   - **Bad Format A row:** Debit becomes negative and Credit positive. If both are blank or the row is malformed, skip it and print a warning to stderr naming the file and line. The run still succeeds with exit 0.
   - **Anything else (a missing file, a malformed rules file):** your call — pick something reasonable and write down what you chose.

10. Always rebuild from the inputs. Incremental runs against an existing ledger are out of scope.

11. Your call — pick something reasonable and write down what you chose.

12. Same account name in both formats: your call — pick something reasonable and write down what you chose. Two different account names count as two different accounts, and different accounts never deduplicate against each other, even if they point at the same file.

## Phase: egm-brainstorm, Step 1 (clarification), round 2

**Questions**
1. In a Format A row, what if both Debit and Credit have a value? Is that a skip-and-warn malformed row, or should the amount be Credit minus Debit?
2. Can amounts contain anything besides digits, a decimal point, a minus sign and thousands separators — e.g. currency symbols like £, parentheses for negatives, or a trailing "CR"? Can Format B amounts have thousands separators too?
3. What should happen to a Format B row with a bad date or unparseable amount — the same skip-and-warn as Format A?
4. Should rows with an amount of exactly 0.00 be kept in the ledger? Can a zero-amount row ever be part of a transfer?
5. In the transfer rule, "dates at most 3 days apart": is that calendar days between the two rows' ledger dates (so the 1st and the 4th match, the 1st and the 5th don't)?
6. A refund on the credit card is an inflow (positive). Could that be wrongly paired as the other side of a transfer with an unrelated outflow of the same amount from the current account within 3 days? Is that acceptable, or should anything stop it?
7. Should header detection be exact, or tolerate things like a byte-order mark, surrounding spaces, or different capitalisation in the header row? What about blank lines in the files?
8. In the rules file, what should happen with a blank pattern, a blank category, or a rule whose category is literally `Transfer`?
9. Should the tool print anything on success (e.g. a summary of rows read, duplicates dropped, transfers found), or stay silent?
10. If the same file path is given twice for the same account, should anything special happen, or does the normal duplicate rule (keep the maximum count) handle it?

**Answers (verbatim)**

1. Your call — pick something reasonable and write down what you chose.

2. Your call — pick something reasonable and write down what you chose.

3. Your call — pick something reasonable and write down what you chose.

4. Your call — pick something reasonable and write down what you chose.

5. Yes. The limit is inclusive, so two rows dated the 1st and the 4th can match, and rows dated the 1st and the 5th can't.

6. Yes, it would pair. An outflow in one account and an inflow of exactly the same absolute amount in a different account, dated at most 3 days apart, count as a transfer. Nothing else stops that pairing.

7. Your call — pick something reasonable and write down what you chose.

8. Your call — pick something reasonable and write down what you chose.

9. Your call — pick something reasonable and write down what you chose.

10. Nothing special happens. The normal rule covers it: across exports of one account, rows are matched by count and the ledger keeps the maximum count, not the sum.

## Phase: egm-brainstorm, Step 3 (iteration after Goldfish brainstorm review), round 3

**Questions**
1. Some banks write `0.00` in the unused Debit or Credit column instead of leaving it blank. Should a Debit or Credit of `0.00` count as blank (so `0.00` debit + `25.00` credit is a normal +25.00 row), or as filled (so the row is malformed and skipped)?
2. Should a rule pattern be matched against the description as written (outer spaces trimmed), or against the whitespace-collapsed version, so the pattern `costa coffee` also matches `COSTA  COFFEE` with two spaces?
3. If a later export has more copies of a transaction than an earlier one (export 1 has it twice, export 2 three times), the ledger keeps three. Should all three use the description text from the first-ever occurrence, or may the third keep its own text from export 2 (they can only differ in case or spacing)?
4. If two different account names point at the same file, the file's own rows could pair with each other as transfers (an outflow and an equal inflow within 3 days, now in "different accounts"). Is that acceptable as a consequence of the names-are-accounts rule?

**Answers (verbatim)**

1. Your call. Pick something reasonable and write down what you chose. (UNCOVERED)

2. Match against the description as written, with outer spaces trimmed. A pattern is a case-insensitive substring of that description. Inner whitespace is not collapsed for rule matching.

3. All three copies use the description text from the first-ever occurrence, with outer spaces trimmed and the original case kept (not lowercased).

4. Your call. Pick something reasonable and write down what you chose. (UNCOVERED)

## Phase: egm-review Stage 7 (critic loop round 3, finding design-3-1)

**Question**
1. In your current-account CSV exports, are amounts with thousands separators wrapped in quotes (e.g. `"1,250.00"`), or can they appear unquoted (e.g. `01/03/2026,RENT,1,250.00,,5,000.00`), which makes the row split into extra columns? If unquoted ones can happen, should the tool try to repair such rows, or skip them with a warning like any other malformed row?

**Answer (verbatim)**
1. On whether exports always quote amounts that have thousands separators: your call. Pick something reasonable and write down what you chose. If a row does split into extra columns, don't try to repair it. Treat it like any other malformed row: skip it and print a warning to stderr that names the file and line. The run still succeeds.
