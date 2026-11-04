# Stakeholder log

## Phase: requirements (before design/implementation)

### Questions
1. Duplicates: when is a row in one export "the same transaction" as a row in another export of the same account? Is matching on (date, amount, description) right, or should anything else (e.g. balance, posting date) be considered?
2. If one export contains two identical rows (same date, amount, description — e.g. two coffees the same day), should both be kept? And if an overlapping export also has those two rows, should the result have exactly two?
3. Descriptions can differ slightly between exports (extra whitespace, case). Should those still be treated as duplicates?
4. For credit card (Format B) rows, which date should the ledger use: Transaction Date or Posting Date? Can the posting date differ for the same transaction between exports?
5. Transfers: how should I recognise a transfer between your own accounts? Equal-and-opposite amounts in two different accounts within some number of days? What window? Should descriptions matter?
6. If a transfer outflow has more than one possible matching inflow (or vice versa), how should it be paired, or should it be left unlinked?
7. What should a transfer row's `category` be, and what should `transfer_id` look like (any format, or something specific)? Should both legs share the same id?
8. Is paying off the credit card from the current account a transfer?
9. Rules: how does `pattern` match — case-insensitive substring, regex, glob, exact? If several rules match, which wins? What category for rows with no match?
10. Should rules apply to transfer rows too, or are transfers excluded from categorisation?
11. Output row order?
12. What should happen on bad input: unknown header, unparseable date/amount, a row with both Debit and Credit filled, missing file?
13. If the same file path is passed twice for the same account, or the same rows appear under two different account names, what should happen?
14. Are there any other behaviours you care about that I haven't asked about?

### Answers
1. Two rows are the same transaction when the account, date, amount and description all match. Neither balance nor posting date counts.

2. Yes, keep both. Two £3.50 coffees on the same day in one file are two separate purchases. Across overlapping exports of the same account, match by count and take the max, not the sum. So if both exports have the row twice, the result has exactly two. If one export has it 2 times and the other 3 times, the ledger has it 3 times.

3. Yes, they're still duplicates. To normalise a description: trim leading and trailing spaces, collapse runs of whitespace inside it to a single space, and ignore case.

4. Use Transaction Date and ignore Posting Date completely. Whether it differs between exports doesn't matter.

5. A transfer is an outflow in one account plus an inflow of exactly the same absolute amount in a different account, with dates no more than 3 days apart (3 days counts). Descriptions play no part.

6. A row can belong to at most one transfer. Go through the outflows in output order. If an outflow has more than one possible inflow, pair it with the one closest in date. If two are equally close, pick the inflow that comes first in output order.

7. Set the category to `Transfer`. Both legs get the same transfer_id, and it must not be empty. The id format is your call. Pick something reasonable and write down what you chose.

8. Yes. If the payment meets the transfer rule, it's a transfer: an outflow from the current account and an inflow of the same absolute amount on the card account, no more than 3 days apart.

9. A pattern matches if it appears anywhere in the description, ignoring case. If several rules match, the first one in file order wins. Rows that match no rule get `Uncategorised`.

10. Transfers are left out. Don't apply rules to transfer rows.

11. Sort by date, then account name, then the row's position in its input file. When rows are duplicates, keep the first occurrence by `--account` argument order.

12.
- **Unknown header** (a file that matches neither format): exit with code 2 and a message, and write no output file.
- **Bad date or amount, both Debit and Credit filled, or both blank:** treat it as a malformed row. Skip it and print a warning to stderr that names the file and line. The run still succeeds with exit 0.
- **Missing file:** your call. Pick something reasonable and write down what you chose.

13. Same file passed twice for the same account: the overlap rule applies, so rows match by count using the max and nothing is doubled. Same rows under two different account names: different accounts never deduplicate against each other, so both sets stay.

14. Your call. Pick something reasonable and write down what you chose.

(Log: UNCOVERED — Q7 id format, Q12 missing file, Q14.)
