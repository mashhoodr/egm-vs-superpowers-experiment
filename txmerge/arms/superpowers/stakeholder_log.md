# Stakeholder log

## Phase: brainstorming

### Q1 (spawn 1)
**Q:** What will you do with the merged ledger once you have it (e.g. monthly spending review, import into another tool, tax), and what would make you say "this works" — what's the worst failure you want to avoid?

**A:** Your call — pick something reasonable and write down what you chose.

**Chosen:** Used for a monthly spending review. Worst failure = silently dropping a real transaction or double-counting (duplicate or transfer counted as spend). Prefer keeping an ambiguous row over losing it.

### Q2 (spawn 2)
**Q:** Duplicates across overlapping exports of the same account: when two exports both contain a row with the same date, description and amount, I plan to treat them as one transaction. But sometimes you genuinely make two identical purchases on one day (e.g. two £3.50 coffees at the same shop). How should the tool tell those apart from an export overlap? My proposal: within a single export file identical rows are all real; across files of the same account, keep the maximum count seen in any one file (so 2 coffees in file X and 2 in file Y => 2, not 4). Is that right, and does the same apply if a description differs slightly between exports (e.g. extra spaces or different capitalisation), or if the Balance column differs?

**A:** 1. Yes, that's right. Identical rows inside one export are all real purchases, so two £3.50 coffees on the same day in the same file count as two. Across exports of the same account, match by count and keep the highest count seen in any one file, not the sum. For example, 2 in file X and 3 in file Y gives 3.

On the differences you asked about:
- **Extra spaces or different capitalisation:** still the same transaction. Compare descriptions after trimming the ends, collapsing runs of whitespace inside to a single space, and ignoring case.
- **Balance column differs:** still the same transaction. A row counts as the same if account, date, amount and the normalised description match. Balance is not part of that check.

### Q3 (spawn 3)
**Q:** Transfers between your own accounts: how should the tool decide that an outflow in one account and an inflow in another are the same transfer? My proposal: same absolute amount, opposite signs, different accounts, dates within a few days of each other (how many days?). When several candidates qualify (e.g. two £100 transfers in the same week), pair the closest dates first, ties broken deterministically. Does the description need to look like a transfer (e.g. contain "transfer"/"payment"), or is amount+date enough? Is paying off the credit card from the current account a transfer? And what if an outflow has no matching inflow (e.g. the other account wasn't exported) — leave it as normal spending, or flag it?

**A:** 1. Transfers:
- **Matching:** It's a transfer when an outflow in one account has an inflow of exactly the same absolute amount in a different account.
- **Days:** The two dates can be at most 3 days apart, counting the 3rd day.
- **Several candidates:** Each row can be in only one transfer. Go through the outflows in output order. Pair each outflow with the inflow closest to it in date. If two inflows are equally close, take the one that comes first in output order.
- **Description:** It doesn't matter. Amount, date and different accounts are enough. The description doesn't need to say "transfer" or "payment".
- **Credit card payoff:** Yes. Paying the card from the current account counts if it meets the same rule: same amount, opposite direction, different accounts, at most 3 days apart.
- **No matching inflow:** Leave it as normal spending. It isn't a transfer, so treat it like any other row.

### Q4 (spawn 4)
**Q:** Output ledger layout: in what order should rows appear in the output CSV (e.g. by date, then account, then something else)? What should `transfer_id` look like (e.g. `T0001`, a hash, something else) and how is it numbered? What should the `category` column hold for transfer rows — blank, "Transfer", or still the rule-based category? And when duplicate rows across exports have slightly different descriptions (e.g. different spacing/case), which description text goes into the output?

**A:** 1. **Row order:** Sort by date, then by account name, then by the order the row appeared in its input file.

   **`transfer_id` format and numbering:** Your call — pick something reasonable and write down what you chose.

   **`category` on transfer rows:** `Transfer`. The rules don't apply to transfer rows.

   **Description for duplicates:** Use the original text from the first occurrence, where "first" follows the `--account` argument order. Trim the outer spaces and leave the case as it is; don't lowercase it.

**Chosen (transfer_id):** `T0001`, `T0002`, ... (zero-padded to 4, widening if needed), numbered in the order pairs are formed (outflows walked in output order). Both rows of a pair share the id.

### Q5 (spawn 5)
**Q:** Categorisation rules file (`pattern,category`): how should a pattern match a description — case-insensitive substring, exact match, regex, wildcard? If several rules match one description, which wins (first in the file, longest pattern, something else)? What category should a non-transfer row get when no rule matches (blank, "Uncategorised", something else)? Do rules apply to incoming money (refunds, salary) the same as to spending?

**A:** 1. A pattern matches if it appears anywhere in the description, ignoring case (a case-insensitive substring match). If several rules match, the first one in the file wins. If no rule matches, the category is `Uncategorised`. On whether incoming money and spending get treated the same: your call — pick something reasonable and write down what you chose.

**Chosen (direction):** Rules apply identically to inflows and outflows (a refund from TESCO is categorised like TESCO spend), so a review can net them.

### Q6 (spawn 6)
**Q:**
1. For credit card exports (Transaction Date, Posting Date), which date should go into the ledger — the transaction date or the posting date? And should duplicate/transfer matching use that same date?
2. What should happen with bad input: a file whose header matches neither format, a row with an unparseable date or amount, a current-account row where both Debit and Credit are filled (or both blank), or a missing file? Should the tool stop with an error (non-zero exit, nothing written), or skip the bad row with a warning and carry on?
3. If the same file path is passed twice, or two different account names point at overlapping data, is there anything special you want, or treat them as given?

**A:**
1. Use the Transaction Date and ignore the Posting Date completely. The Posting Date isn't used anywhere, so duplicate matching and transfer matching also run on the Transaction Date.

2. It depends on the problem:
   - **Header matches neither format:** stop. Exit with code 2, print a message, and write no output file.
   - **Bad row (both Debit and Credit blank, or a malformed row such as both filled or an unparseable date or amount):** skip the row. Print a warning to stderr that names the file and line number, then carry on. The run still succeeds with exit 0.
   - **Missing file:** Your call — pick something reasonable and write down what you chose.

3. Treat them as given; the normal rules cover both cases.
   - **Different account names:** they never deduplicate against each other, even if the data overlaps.
   - **Same file under the same account twice:** the usual duplicate rule applies. A row matching on account, date, amount and normalised description appears in the ledger as many times as the highest count in any one export, not the total across exports. So passing the file twice doesn't double anything.

**Chosen (missing file):** same as unknown header — exit 2, message on stderr, no output file written. A missing export silently ignored would lose real transactions.

## Phase: writing-plans / implementation

(no questions)

## Phase: subagent-driven development — final review fixes

### Q7 (spawn 7)
**Q:**
1. Some current-account exports write `0.00` in the unused column instead of leaving it blank (e.g. Debit `12.50`, Credit `0.00`). Should a zero in one column count as "blank" (so the row is a normal £12.50 debit), or as "both filled" (so the row is skipped with a warning)?
2. If an input file is damaged — e.g. a description has an opening double-quote that is never closed, so the CSV can't be parsed reliably past that point — should the tool stop with an error (non-zero exit, no output) or carry on?

**A:**
1. Your call. Pick something reasonable and write down what you chose.

2. Carry on. A malformed row is skipped, not fatal. Print a warning to stderr that names the file and the line, skip the row, and let the run succeed (exit 0).

**Chosen (1):** a zero in one column counts as blank; the non-zero column decides the amount. Both zero → a 0.00 row is kept (never drop a row the bank listed).
**Applied (2):** exports are parsed one physical line at a time in strict CSV mode, so a broken quote costs only its own line (warned + skipped), never the lines after it.

