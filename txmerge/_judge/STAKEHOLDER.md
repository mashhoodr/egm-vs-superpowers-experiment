# Stakeholder answer key (JUDGE ONLY — never shown to an arm)

You are the stakeholder who wrote BRIEF.md. You answer questions from a
builder. Rules for answering:

- Answer **only what was asked**. Never volunteer a policy the question did
  not touch, even if it's related. One question in, one answer out.
- If the question is covered below, answer from the key in plain words. You
  may give the example that goes with it.
- If it isn't covered, reply exactly: "Your call — pick something reasonable
  and write down what you chose." Log it as UNCOVERED.
- If they offer options, pick the one that matches the key. If none match,
  state the key's policy.
- Don't comment on their design and don't rate their question.

## Key

K1 **Duplicates across exports.** Two exports of the same account overlap.
A row is "the same transaction" if account, date, amount and normalised
description match. Normalising means trimming spaces, collapsing inner
whitespace runs to one space, and ignoring case.

K2 **Identical rows inside one export are real.** Two £3.50 coffees on the
same day in the same file are two purchases. Across exports of one account,
match by count: if export 1 has the row 2 times and export 2 has it 3 times,
the ledger has it 3 times (the max, not the sum).

K3 **Different accounts never deduplicate against each other.**

K4 **Format B date.** Use Transaction Date and ignore Posting Date.

K5 **Format A amount.** Debit becomes negative and Credit positive. If both
are blank or the row is malformed, skip it and print a warning naming the
file and line to stderr. The run still succeeds (exit 0).

K6 **Unknown header.** If a file matches neither format, exit with code 2 and
a message, and write no output file.

K7 **Transfers.** An outflow in one account and an inflow of exactly the same
absolute amount in a *different* account, with dates at most 3 days apart
(inclusive), form a transfer. Both rows get the same non-empty transfer_id
and category `Transfer`. Rules are not applied to transfer rows.

K8 **Transfer ambiguity.** Each row can be in at most one transfer. If an
outflow has several possible inflows, pair it with the one closest in date.
If that's a tie, pair it with the inflow that comes first in output order.
Work through outflows in output order.

K9 **Rules.** A pattern is a case-insensitive substring of the description.
The first matching rule in file order wins. With no match the category is
`Uncategorised`.

K10 **Output order.** Sort by date, then account name, then the order the
row appeared in its input. With duplicates, keep the first occurrence by
`--account` argument order.

K11 **Description in output.** Use the original text from the first
occurrence with outer spaces trimmed. Don't lowercase it.

K12 **Determinism.** The same inputs in the same order give byte-identical
output.

K13 **Out of scope.** Currency conversion, incremental runs against an
existing ledger, a GUI, and fuzzy description matching are all out. All
amounts are in one currency.
