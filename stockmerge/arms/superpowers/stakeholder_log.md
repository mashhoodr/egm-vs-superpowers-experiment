# Stakeholder log

## Phase: Brainstorming — round 1a

**Q1.** What will you use the merged inventory for once you have it (e.g. reconciling against your stock system, spotting shrinkage, reordering)? Who reads it?
**A1.** Your call. Pick something reasonable and write down what you chose.

**Q2.** What makes two scan rows "the same scan" (a duplicate)? For example: same location, same SKU, same timestamp and same quantity? Must they come from different export files, or can a single file contain duplicates of itself?
**A2.** Two rows are the same scan when the location, the timestamp, the quantity in single items and the SKU all match. Compare the SKU after trimming spaces, ignoring case and ignoring leading zeros, so `00123` and `123` are the same SKU (scanner B drops the zeros). Compare the quantity after converting cases, so `1 case` in Format A and `12` in Format B are the same quantity. Duplicates only happen between different exports of the same location. A single file never duplicates itself.

**Q3.** If one export file contains two identical rows (same time, SKU, qty), are those two real scans or one duplicated scan?
**A3.** They are two real scans. For example, two scans of 6 cans of the same SKU in the same minute in one file means two shelves.

**Q4.** Can a Format A export and a Format B export of the same location overlap and duplicate each other? Format A timestamps are to the minute and Format B to the second — how should they be compared?
**A4.** Yes. Two exports of the same location can overlap, and that includes a Format A export and a Format B export. Compare timestamps to the minute. Drop the seconds from Format B rather than rounding them, so `14:30:59` counts as `14:30`.

**Q5.** For Format A rows with Unit = case, how many single items are in a case? Is it the same for every SKU, or per SKU, and where would that number come from?
**A5.** A case is 12 single items, and that holds for every SKU. It is a fixed number, so `2,case` is 24 and `-1,case` is -12. Different pack sizes per SKU are out of scope.

**Q6.** How do you recognise a move between locations: a negative quantity of a SKU at one location and the matching positive quantity at another? Must the quantities match exactly, and how close together in time must they be?
**A6.** Yes. It is a move when one location has a negative scan and a different location has a positive scan of the same SKU (compared the same way as for duplicates). The quantities must be exact opposites in single items, and the two timestamps can be at most 2 hours apart, with exactly 2 hours still counting.

**Q7.** What should the move_id look like (any format, e.g. M1, M2...) and should it be stable between runs?
**A7.** The format is your call, as long as both rows of a move get the same non-empty move_id. Write down what you chose. It must be stable: the same inputs in the same order must give byte-identical output.

## Phase: Brainstorming — round 1b

**Q1.** In the rules file (pattern,category), what kind of pattern is it: an exact SKU, a prefix, a wildcard/glob like `ABC-*`, or a regular expression?
**A1.** It's a case-insensitive substring of the SKU. A pattern matches if it appears anywhere in the SKU, ignoring case. It isn't an exact match, a prefix, a glob or a regex.

**Q2.** If a SKU matches more than one rule, which category wins (first rule in the file, most specific, something else)?
**A2.** The first rule in the file that matches wins.

**Q3.** If a SKU matches no rule, what category should the row get (blank, a word like "uncategorised", or should it be an error)?
**A3.** The category is `Uncategorised`.

**Q4.** Should SKUs be normalised before matching and output, e.g. trimming spaces, upper-casing, or stripping leading zeros from barcodes?
**A4.** Yes for matching: trim spaces, ignore case and ignore leading zeros, so `00123` and `123` are the same SKU (scanner B drops the zeros). For output, no: use the original text from the first occurrence with only the outer spaces trimmed. Keep its case and its leading zeros.

**Q5.** What should happen with a bad input row (unparseable date, non-numeric quantity, unknown unit) or a file whose header matches neither format: stop with an error, or skip the row and carry on? Should anything be reported?
**A5.** For a bad row in either format, skip it and print a warning to stderr that names the file and the line, then carry on. The run still succeeds with exit code 0. A bad row includes a quantity that isn't a whole number, an unknown unit, a blank SKU, a timestamp that doesn't parse, or any other malformed row. If a file's header matches neither format, stop with exit code 2 and a message, and don't write any output file.

**Q6.** In what order should output rows be written?
**A6.** Sort by location name, then normalised SKU, then timestamp, then the order the row appeared in its input. When there are duplicates, keep the first occurrence according to the order of the `--location` arguments.

**Q7.** Do the Format B `note` values mean anything the tool should act on (for example notes about moves or cases), or are they ignored?
**A7.** They're ignored entirely. Format B's `count` is always single items, even if the note says "case".

## Phase: Brainstorming — round 2

**Q1.** Duplicates across exports when counts differ: export 1 of "shop floor" has the same scan (same minute, SKU, qty) twice, and export 2 of "shop floor" has it once. How many rows should be kept: 2 (the most any single export shows), 3, or 1?
**A1.** Keep 2. Identical rows inside one export are real scans, for example two shelves. Across exports of the same location, match by count and take the most any single export shows, not the sum. Export 1 has it twice and export 2 has it once, so the inventory has it twice.

**Q2.** Moves with several candidates: if one negative scan could pair with two different positive scans (or the reverse), which pairing wins? Can a single scan belong to more than one move?
**A2.** Each row can be in at most one move. If a negative scan has several possible partners, pair it with the one closest in time. If two are equally close, pair it with the one that comes first in scan order: timestamp, then location name, then input order. Work through the negative scans in that same scan order.

**Q3.** Are duplicates removed before moves are detected (so a duplicated negative scan can only form one move)?
**A3.** Your call — pick something reasonable and write down what you chose.

**Q4.** Are location names compared exactly as typed, or are "Shop Floor" and "shop floor" the same location? What is written in the output's location column?
**A4.** Your call — pick something reasonable and write down what you chose.

**Q5.** The output SKU is "the original text from the first occurrence". First occurrence of that normalised SKU across the whole run, or within each location? And "first" by the order of `--location` arguments then row order?
**A5.** The SKU comes from the first occurrence of that scan, ordered by `--location` argument order. Different locations never deduplicate against each other. Write the original text with outer spaces trimmed, keep its case, and keep its leading zeros.

**Q6.** A scan with quantity 0: keep it as a row, or drop it?
**A6.** Your call — pick something reasonable and write down what you chose.

**Q7.** How strict is header detection: must the header match exactly, or should extra spaces, different letter case, or a UTF-8 BOM be tolerated? Should the Format A Unit value be case-insensitive (`Case`, `EACH`)?
**A7.** Yes, match the Format A Unit value ignoring case and outer spaces, so `Case` and ` EACH ` are both fine. On how strict header detection should be: your call — pick something reasonable and write down what you chose.

**Q8.** What should happen if an input path or the rules file does not exist or cannot be read, or the rules file has the wrong header? What about a rules row with a blank pattern?
**A8.** Your call — pick something reasonable and write down what you chose.

**Q9.** Can Format B timestamps carry a timezone offset or fractional seconds (e.g. `2026-03-05T14:30:12.5` or `...+05:00`), and if so how should they be treated?
**A9.** Time zones are out of scope. Treat all timestamps as shop local time. Seconds are dropped, not rounded, and we compare to the minute, so a fraction of a second doesn't matter. On whether to accept those forms at all: your call — pick something reasonable and write down what you chose.

**Q10.** A SKU made only of zeros (`000`): what is it after ignoring leading zeros — the same as `0`?
**A10.** Your call — pick something reasonable and write down what you chose.

## Phase: Brainstorming — round 3

**Q1.** "Shop floor" has two exports, given in this --location order: export 1 has a scan twice, export 2 has the same scan three times (same minute, SKU, qty). We keep 3 rows. Which rows are they: all three from export 2 (the export with the most), or export 1's two plus one extra from export 2 (each copy taken from the first export, in --location order, that has that many)? This decides which SKU spelling (e.g. `00123` vs `123`) and input position each kept row gets.
**A1.** Export 1's two rows plus one extra from export 2. The inventory keeps the highest count any single export has (3 here), and each kept copy comes from the first export in --location order that has that many. So rows 1 and 2 come from export 1, and the third comes from export 2, with that export's SKU text and input position.

**Q2.** For moves, is "closest in time" and the 2-hour window measured on the minute-truncated timestamps (seconds dropped), the same as for duplicates?
**A2.** Yes. Timestamps are compared to the minute everywhere. For Format B, seconds are dropped, not rounded (`14:30:59` counts as `14:30`).

**Q3.** When working through negative scans to pair them, is it a simple one-pass greedy pairing (each negative, in scan order, takes its closest still-unpaired positive), even if a different overall pairing would link more moves?
**A3.** Yes, a simple one-pass greedy pairing. Go through the negative scans in scan order: timestamp, then location name, then input order. Each negative pairs with its closest still-unpaired positive partner. If two partners are equally close, it takes the one that comes first in that same scan order. Each row can be in at most one move, and you don't need to search for a pairing that links more moves overall.

## Phase: Subagent-driven development — final review follow-up

**Q1.** A rule's pattern contains leading zeros, e.g. a rule `00123,Drinks` copied from a scanner A SKU. SKUs are compared ignoring leading zeros, so `00123` and `123` are the same SKU. Should that rule match SKU `00123` and also `123`? Should leading zeros be ignored in the pattern itself, or should the pattern be matched against the SKU as written?
**A1.** Your call. Pick something reasonable and write down what you chose.

**Q2.** In a Format B row, if the free-text note contains an unquoted comma (e.g. `2026-03-05T14:30:12,ABC,4,moved, from back`), should the row still count as a scan (treat everything after the third comma as the note), or be skipped as a bad row?
**A2.** Skip it as a bad row. A row with an extra unquoted comma doesn't have the right shape, so print a warning to stderr naming the file and line number, then carry on. The run still succeeds (exit 0).
