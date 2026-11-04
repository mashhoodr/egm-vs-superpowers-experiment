# Stakeholder log

## Phase: egm-brainstorm, Step 1 (clarification) — round 1

**Questions**
1. Duplicates: when the same account has two exports with overlapping dates, what makes two rows "the same transaction"? And how should we treat a case where one export genuinely contains two identical rows on the same day (same date, description and amount, e.g. two coffees) — and the other export also overlaps that day?
2. Do descriptions of the same transaction ever differ between two exports of the same account (spacing, capitalisation, truncation), or do amounts/dates shift (e.g. a card transaction whose posting date changes)? How should that be handled?
3. For the credit card format (B), which date should go in the output `date` column: Transaction Date or Posting Date?
4. Transfers: how do you recognise a transfer between your own accounts? For example, how far apart can the two sides' dates be, must the amounts match exactly, and does a credit-card payment from the current account count as a transfer?
5. If a transfer could match more than one candidate on the other side (e.g. two identical £100 movements), what should happen? And what should `transfer_id` look like?
6. Rules: how should a `pattern` match a description (substring, case sensitivity, wildcard/regex)? If several rules match, which wins? What category should a row get when no rule matches? And what category, if any, should transfer rows get?
7. What order should the rows in the output ledger be in?
8. What should happen with bad input — an unrecognised header, an unparseable date or amount, a Format A row with both Debit and Credit filled, a missing file? Fail the whole run, skip the row with a warning, or something else?

**Answers**
1. Two rows are the same transaction when the account, date and amount match exactly and the descriptions match after normalising. Normalising means trimming leading and trailing spaces, collapsing any run of inner whitespace to one space, and ignoring case. Identical rows inside one export are real: two £3.50 coffees on the same day in the same file are two purchases. When the other export overlaps that day, match by count and take the max, not the sum. If export 1 has the row 2 times and export 2 has it 3 times, the ledger has it 3 times.

2. Differences in spacing and capitalisation are absorbed by the normalisation above. Beyond that, matching is exact. A truncated description, a different amount or a different date makes it a different row. Fuzzy description matching is out of scope.

3. Use Transaction Date and ignore Posting Date.

4. A transfer is an outflow in one account and an inflow of exactly the same absolute amount in a different account. The two dates can be at most 3 days apart, and 3 counts. A credit-card payment from the current account counts when it meets those conditions: an outflow on the current account and a matching inflow on the card account. Both rows get the same non-empty transfer_id and the category `Transfer`.

5. Each row can be in at most one transfer. Work through the outflows in output order. If an outflow has several possible inflows, pair it with the one closest in date. If that's a tie, pair it with the inflow that comes first in output order. On what `transfer_id` should look like: Your call — pick something reasonable and write down what you chose. (It just has to be non-empty and shared by both rows of the pair.)

6. A pattern matches when it is a case-insensitive substring of the description. It is a plain substring, with no wildcards or regex. When several rules match, the first matching rule in file order wins. With no match the category is `Uncategorised`. Transfer rows get the category `Transfer`, and rules are not applied to them.

7. Sort by date, then account name, then the order the row appeared in its input. Where there are duplicates, keep the first occurrence by `--account` argument order.

8. These cases have different answers:
   - **Unrecognised header:** if a file matches neither format, exit with code 2 and a message, and write no output file.
   - **Unparseable date or amount, or a Format A row with both Debit and Credit filled:** that row is malformed. Skip it and print a warning to stderr naming the file and line. The run still succeeds with exit code 0. A Format A row with both Debit and Credit blank is handled the same way.
   - **Missing file:** Your call — pick something reasonable and write down what you chose.

Not covered by my answers (UNCOVERED): the `transfer_id` format in Q5 and the missing-file behaviour in Q8.

## Phase: egm-brainstorm, Step 1 (clarification) — round 2

**Questions**
1. When duplicates collapse to one row, which export's description text should appear in the ledger (the descriptions may differ in spacing/case)? Should the output description be the original text or the normalised one?
2. In Format A, Debit becomes a negative amount and Credit a positive one — is that right? Is the Balance column used for anything (e.g. checking for missing rows), or ignored? Can Format B amounts also carry thousands separators or currency symbols?
3. For a transfer, can the inflow side be dated before the outflow side (e.g. the card shows the payment a day before the current account does)? And can a transfer ever be between two exports that use the same account NAME, or only between different NAMEs?
4. Should rows with an amount of exactly zero be kept, dropped, or treated as malformed?
5. Rules file details: should a rule pattern be matched against the original description or the normalised one (whitespace collapsed)? What about a blank pattern line, or a rules file with only a header — and what if the rules file is missing or has the wrong header?
6. If the same file path is given twice for one account (or the same file for two different accounts), what should happen?
7. Input file quirks: should we expect a UTF-8 byte-order mark, blank lines, trailing whitespace in headers, or quoted fields with commas? Anything else about the files that you know to be messy?
8. Should the tool print anything on success (for example a summary of rows read, duplicates removed, transfers linked, uncategorised count), and where — stdout or stderr?

**Answers**
1. Use the original text from the first occurrence, keeping the first occurrence in `--account` argument order. Trim the spaces at the start and end, but don't lowercase it and don't collapse the inner spaces. The normalised form is only for deciding whether two rows match.

2. Yes, Debit becomes negative and Credit becomes positive. Balance column: Your call — pick something reasonable and write down what you chose. Format B thousands separators or currency symbols: Your call — pick something reasonable and write down what you chose.

3. Yes. The two dates only have to be at most 3 days apart, inclusive, so the inflow can come first. A transfer must be between two different accounts. An outflow and an inflow in the same account are never a transfer.

4. Your call — pick something reasonable and write down what you chose.

5. A rule matches if its pattern is a case-insensitive substring of the description. The first matching rule in file order wins, and a row with no match gets `Uncategorised`. So a rules file with only a header leaves every non-transfer row `Uncategorised`. Original vs normalised description, blank pattern lines, and a missing rules file or one with the wrong header: Your call — pick something reasonable and write down what you chose.

6. Same file twice for one account: within one account, rows match across exports by count, and the ledger keeps the higher count, not the sum. So the repeat adds no extra rows. Same file for two different accounts: different accounts never deduplicate against each other, so each account gets its own copy of the rows. Whether to warn or refuse in either case: Your call — pick something reasonable and write down what you chose.

7. Your call — pick something reasonable and write down what you chose.

8. Your call — pick something reasonable and write down what you chose.

Coverage: the key covered none of these, so they are logged as UNCOVERED:
- Q2: Balance column
- Q2: Format B separators and currency symbols
- Q4: zero amounts
- Q5: original vs normalised text for matching
- Q5: blank pattern lines
- Q5: rules file missing or with the wrong header
- Q6: whether to warn or refuse
- Q7: input file quirks
- Q8: success summary

The other parts were answered from the key.

## Phase: egm-brainstorm, Step 3 (iterate on Goldfish objections) — round 3

**Questions**
1. Duplicates with max-count: export 1 (first --account argument) has a row twice and export 2 has the same row three times, so the ledger keeps three. Which physical rows should those three be — the two from export 1 plus one copy from export 2 (keeping that copy's own description text and its position in export 2), or something else? Should "export" mean each --account argument, even when the same path is given twice?
2. Amounts with more than 2 decimal places (e.g. 12.345): round them (and how), or treat the row as malformed? And a negative number inside a Format A Debit or Credit cell — malformed, or accepted?
3. Dates written without leading zeros (e.g. 1/2/2026 in Format A, 2026-1-2 in Format B): accept them, or treat the row as malformed?
4. Can one account NAME mix a Format A export and a Format B export? If yes, should their rows dedup against each other like any other exports of that account?
5. If a file has a valid header but every row is malformed (or it has no rows at all), should the run still succeed with exit 0, writing the remaining rows?
6. Should rule patterns be compared with the description after collapsing inner whitespace (so "coffee shop" matches "COFFEE  SHOP"), or against the description as written (trimmed only)?

**Answers**
1. Keep the first occurrences, taken in `--account` argument order. Each copy inside one export is a real purchase, and across exports of one account you keep the max count, not the sum. So the ledger keeps the two rows from export 1 plus one copy from export 2 that has its own description text, trimmed of outer spaces but not lowercased. Order the output by date, then account name, then where the row appeared in its input. On whether the same path given twice counts as two exports: your call — pick something reasonable and write down what you chose.

2. Your call — pick something reasonable and write down what you chose.

3. Your call — pick something reasonable and write down what you chose.

4. The test for "the same transaction" uses only account, date, amount and normalised description. Normalised means trimmed, inner whitespace collapsed to one space, and case ignored. The file's format isn't part of it. So yes: rows under the same account name dedup against each other whatever format they came from.

5. Yes. Skip each malformed row and print a warning to stderr that names the file and line. The run still succeeds with exit 0 and writes the rest.

6. A rule pattern is a case-insensitive substring of the description. Match it against the description as written, trimmed only. Collapsing inner whitespace is part of the duplicate test, not the rules.

## Phase: egm-review Stage 7 (resolve, round 1) — round 4

**Questions**
1. Some bank descriptions may start with characters such as `=`, `+`, `-` or `@`. If you open the ledger in a spreadsheet, those cells can be treated as formulas. Should the ledger write descriptions exactly as the bank gave them (trimmed), or alter such descriptions (for example by prefixing an apostrophe) to stop spreadsheets running them?
2. If `--out` points at the same file as one of the input exports or the rules file, should the tool refuse (exit with an error, changing nothing) or go ahead and overwrite it?

**Answers**
1. Write descriptions as the bank gave them. Use the original text from the first occurrence with the outer spaces trimmed, and don't alter it in any other way. That means no apostrophe prefix and no lowercasing.

2. Your call — pick something reasonable and write down what you chose.

(Note for caller: Q2 is UNCOVERED by the key. Q1 was answered from the description-in-output policy, since the "exactly as given, trimmed" option matches it.)
