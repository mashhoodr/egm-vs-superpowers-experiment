# Stakeholder log

## Phase: egm-brainstorm, Step 1 (clarification), round 1

**Q1.** When the same location is exported twice and the exports overlap, what exactly makes two scans "the same scan"? For example: same location, same SKU, same timestamp and same quantity? Does it matter if one copy came from scanner 1 and the other from scanner 2?
**Q2.** Inside a single export file, if two rows are identical (same time, SKU, quantity), are they a duplicate to remove or two real scans to keep?
**Q3.** Format A has a `Unit` of `each` or `case`. How many single items are in a case? Is it the same for every SKU, and where should the tool get that number from?
**Q4.** How should the tool recognise that stock moved from one location to another, rather than being lost at one and found at another? What has to match (SKU, quantity, time, notes) and how close in time do the two scans need to be?
**Q5.** What should a `move_id` look like, and how should it be numbered?
**Q6.** In the rules file, what does `pattern` mean: an exact SKU, a prefix, a wildcard like `ABC-*`, or a regular expression? If a SKU matches several rules, which wins? And what category should a SKU get if no rule matches?
**Q7.** Do the two scanners record time in the same timezone/clock, and is a Format A time (to the minute) ever meant to be compared with a Format B time (to the second)?
**Q8.** What should happen with bad input: an unknown header, a malformed row, a bad date, a non-whole quantity, a `--location` without `=`, a missing file? Stop with an error, or skip and warn?
**Q9.** Should SKUs/barcodes be normalised before comparing (trim whitespace, upper/lower case, leading zeros)?
**Q10.** In what order should rows appear in the output file?

**Answers (verbatim):**

1. Two rows are the same scan when all four of these match: location, timestamp (compared to the minute), quantity counted in single items, and SKU after normalising. It doesn't matter which scanner a row came from. A Format A row of `1 case` and a Format B row of `12` are the same quantity, so they can match.

2. Keep both. Identical rows inside one export are two real scans, for example the same item counted on two shelves.

3. A case is 12 items, and that's true for every SKU. Different pack sizes per SKU are out of scope. Use 12 as a fixed number, so `2,case` is 24 and `-1,case` is -12.

4. A move is a negative scan at one location plus a positive scan of exactly the opposite quantity (in single items) at a *different* location. The SKU must be the same after normalising, and the two timestamps must be at most 2 hours apart, with exactly 2 hours counting. Ignore notes completely. Both rows get the same move_id and the category `Move`, and the rules are not applied to move rows. Each row can belong to only one move. If a negative scan has several possible partners, pick the one closest in time. If that's a tie, pick the one that comes first in scan order: timestamp, then location name, then input order. Go through the negative scans in that same scan order.

5. Both rows of a move must have the same move_id, and it must not be empty. Beyond that, your call — pick something reasonable and write down what you chose.

6. A pattern is a substring of the SKU, matched ignoring case. It isn't exact, prefix, wildcard or regex. If a SKU matches several rules, the first matching rule in file order wins. If no rule matches, the category is `Uncategorised`.

7. Yes, the two scanners use the same clock. All timestamps are shop local time, and time zones are out of scope. Format A and Format B times are compared with each other, to the minute. Format B seconds are dropped, not rounded, so `14:30:59` is `14:30`.

8.
   - **Unknown header** (the file matches neither format): stop with exit code 2 and a message, and write no output file.
   - **Malformed row, bad date or non-whole quantity**, in either format: skip the row and print a warning to stderr naming the file and line. The run still succeeds with exit 0. The same applies to a blank SKU or a Format A unit other than `each` or `case`.
   - **`--location` without `=`, and a missing file**: your call — pick something reasonable and write down what you chose.

9. Yes, before comparing. Trim spaces, ignore case and ignore leading zeros. `00123` and `123` are the same SKU, because scanner B drops leading zeros.

10. Sort by location name, then normalised SKU, then timestamp, then the order the row appeared in its input. When there are duplicates, keep the first occurrence by `--location` argument order.

## Phase: egm-brainstorm, Step 1 (clarification), round 2

**Q1.** Dedup counting: suppose export 1 of "shop floor" contains a scan twice (two real scans on two shelves) and export 2 of "shop floor" contains that same scan once. How many rows should the output keep: two (the most copies seen in any one export), three, or one? And if export 2 contained it three times?
**Q2.** Are duplicates only ever looked for between different files of the same location name, or also between files of different location names?
**Q3.** In the output `sku` column, should the SKU be written as normalised (no leading zeros, one fixed case) or as it appeared in the input? If the kept row's original spelling differs from another copy, which spelling wins?
**Q4.** For a move, must the negative scan come before the positive scan in time, or can the positive scan come first (within the 2 hours)?
**Q5.** Are duplicates removed before moves are matched, so a duplicated scan can't create two moves?
**Q6.** Rules matching: is the substring matched against the normalised SKU (leading zeros removed) or the SKU as written? For example, does pattern `00ab` match SKU `00ABC`?
**Q7.** What should happen to a row with quantity 0?
**Q8.** Are location names compared exactly as typed on the command line (so "Shop Floor" and "shop floor" are two locations), and written to the output exactly as typed?
**Q9.** Rules file problems: what if its header is wrong, a pattern is blank, or a category is blank? Stop with an error, or skip and warn?
**Q10.** If the same file PATH is given twice for the same location, should it be treated as two exports (and so fully deduplicated), or as an error?
**Q11.** Should a positive scan with no matching negative (or a negative with no partner) keep the category from the rules and a blank move_id?

**Answers (verbatim):**

1. Keep two rows. Two identical scans in one export are two real scans, from two shelves. Between exports of the same location, match by count and take the highest count, not the total. If export 2 had it three times, keep three.

2. Only between exports with the same location name. Files from different locations are never deduplicated against each other.

3. Write it as it appeared in the input. Use the text from the first occurrence with the outer spaces trimmed, and keep its case and leading zeros. The first occurrence follows the order of the `--location` arguments, so the copy from the earliest location argument sets the spelling.

4. Either one can come first. The only timing rule is that the two scans are at most 2 hours apart, and exactly 2 hours counts.

5. Your call — pick something reasonable and write down what you chose.

6. Your call — pick something reasonable and write down what you chose.

7. Your call — pick something reasonable and write down what you chose.

8. Your call — pick something reasonable and write down what you chose.

9. Your call — pick something reasonable and write down what you chose.

10. Your call — pick something reasonable and write down what you chose.

11. Yes. A row that isn't part of a move gets its category from the rules, or `Uncategorised` if no rule matches. Its move_id stays blank, since only move rows get one.

(Judge log: UNCOVERED = Q5, Q6, Q7, Q8, Q9, Q10.)

## Phase: egm-brainstorm, Step 3 (iteration on Goldfish objections), round 3

**Q1.** Dedup survivors: for a scan that appears in several exports of one location, we plan to keep the highest per-export count N, taking the first N copies in input order (all copies from the earliest `--location` argument first, then extra copies from later ones). Is that what you want?
**Q2.** Output `sku` spelling: you said the first occurrence by `--location` order sets the spelling. Is that one spelling per normalised SKU across the whole output (all locations), or chosen separately for each location? Or should every row keep its own spelling?
**Q3.** Moves: is the 2-hour window measured on times cut to the minute (so 10:00:59 and 12:00:30 count as 2 hours apart), or on the full times with seconds? And is the move tie-break "closest in time" also measured to the minute?
**Q4.** The output is one row per kept scan, not a total per SKU per location. Is that right, or do you also want totals?
**Q5.** A Format B row with an unquoted comma in the note gives more than 4 fields. Keep the row (the note is ignored anyway) or skip it as malformed with a warning?
**Q6.** Might exports start with a UTF-8 byte-order mark (as Excel often writes) or use Windows line endings? Should those be accepted?
**Q7.** Is a quantity written as `5.0` a whole number to accept, or a malformed row to skip? What about `+5`?
**Q8.** Format A dates: will they always be zero-padded (`05/03/2026 09:05`), or should `5/3/2026 9:05` also be accepted?

**Answers (verbatim):**

1. Yes. When one scan appears in several exports of the same location, the inventory holds it as many times as the highest count in any single export (the max, not the sum). The copies you keep are the first ones by `--location` argument order. For example, if export 1 has the row 2 times and export 2 has it 3 times, keep 3: both from export 1, plus one from export 2.

2. Each output row uses the SKU text from the copy you actually kept. For a deduplicated scan, that is the first occurrence by `--location` order. Trim outer spaces, but don't change the case and keep the leading zeros. (UNCOVERED: the key doesn't say whether rows of the same SKU must share one spelling. I read "the first occurrence" as the surviving copy of each scan.)

3. Cut to the minute. All timestamp comparisons are to the minute, and seconds are dropped, not rounded. So 10:00:59 is 10:00 and 12:00:30 is 12:00, which is exactly 2 hours apart, and the window includes 2 hours. The "closest in time" tie-break is also measured on minute-cut times.

4. Yes, one row per kept scan. On totals: "Your call — pick something reasonable and write down what you chose." (UNCOVERED)

5. Skip it as malformed, print a warning to stderr naming the file and line, and keep going. The run still exits 0.

6. "Your call — pick something reasonable and write down what you chose." (UNCOVERED)

7. "Your call — pick something reasonable and write down what you chose." (UNCOVERED. The key only says a quantity that isn't a whole number is skipped with a warning. It doesn't say whether `5.0` or `+5` counts as one.)

8. "Your call — pick something reasonable and write down what you chose." (UNCOVERED. The key only says a timestamp that doesn't parse means the row is skipped with a warning. It doesn't say whether unpadded dates must parse.)
