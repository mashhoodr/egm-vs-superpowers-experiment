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

K1 **Duplicates across exports.** Two exports of the same location overlap.
A row is "the same scan" if location, timestamp, quantity in eaches and
normalised SKU match. Normalising means trimming spaces, ignoring case, and
ignoring leading zeros (`00123` and `123` are the same SKU; scanner B drops
them). Quantity is compared after case conversion, so `1 case` in Format A
and `12` in Format B are the same quantity.

K2 **Identical rows inside one export are real.** Two scans of 6 cans of the
same SKU at the same minute in the same file are two scans (two shelves).
Across exports of one location, match by count: if export 1 has the row 2
times and export 2 has it 3 times, the inventory has it 3 times (the max,
not the sum).

K3 **Different locations never deduplicate against each other.**

K4 **Timestamps and the note column.** Compare timestamps to the minute.
Format B seconds are dropped, not rounded (`14:30:59` is `14:30`). Ignore
Format B's `note` column entirely: `count` is always single items, even if
the note says "case".

K5 **Format A quantity.** `each` is taken as-is; `case` means 12 items, so
`2,case` is 24 and `-1,case` is -12. Unit is matched ignoring case and outer
spaces. If the quantity isn't a whole number, the unit is anything else, the
SKU is blank, the timestamp doesn't parse, or the row is otherwise malformed
(either format), skip it and print a warning naming the file and line to
stderr. The run still succeeds (exit 0).

K6 **Unknown header.** If a file matches neither format, exit with code 2 and
a message, and write no output file.

K7 **Moves.** A negative scan at one location and a positive scan of exactly
the opposite quantity in eaches, for the same (normalised) SKU, at a
*different* location, with timestamps at most 2 hours apart (inclusive), form
a move. Both rows get the same non-empty move_id and category `Move`. Rules
are not applied to move rows.

K8 **Move ambiguity.** Each row can be in at most one move. If a negative scan
has several possible partners, pair it with the one closest in time. If
that's a tie, pair it with the one that comes first in scan order (timestamp,
then location name, then input order). Work through negative scans in that
same scan order.

K9 **Rules.** A pattern is a case-insensitive substring of the SKU. The first
matching rule in file order wins. With no match the category is
`Uncategorised`.

K10 **Output order.** Sort by location name, then normalised SKU, then
timestamp, then the order the row appeared in its input. With duplicates,
keep the first occurrence by `--location` argument order.

K11 **SKU in output.** Use the original text from the first occurrence with
outer spaces trimmed. Don't change its case and keep its leading zeros.

K12 **Determinism.** The same inputs in the same order give byte-identical
output.

K13 **Out of scope.** Different pack sizes per SKU, prices or stock value,
checking against an expected stock list, incremental runs against an
existing inventory, time zones, a GUI, and fuzzy SKU matching are all out.
All timestamps are shop local time.
