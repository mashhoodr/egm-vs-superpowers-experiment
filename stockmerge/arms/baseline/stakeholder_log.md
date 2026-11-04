# Stakeholder log

## Phase: requirements (round 1, before design)

### Questions
1. Duplicates: what makes two scans "the same scan"? Same location + same SKU + same timestamp + same quantity? Does it only count as a duplicate when the two rows come from different export files of the same location, or also when identical rows appear inside one file?
2. If the same location was exported by scanner 1 (Format A) and scanner 2 (Format B), can a scan appear in both, and should those be treated as duplicates? Are timestamps comparable exactly (Format A only has minutes, Format B has seconds)?
3. Units: Format A has `Unit` = `case`. How many items are in a case? Is it per SKU, and where does that number come from? Format B has no unit column — is `count` always single items?
4. SKU vs barcode: is Format B's `barcode` the same identifier as Format A's `SKU`? Any normalisation needed (case, whitespace, leading zeros)?
5. Moves: how should I recognise a move between locations? E.g. a negative at one location and a positive of the same SKU and same magnitude at another location within some time window? What window? Does the Format B `note` field indicate moves? What if several candidates could pair up?
6. What should `move_id` look like (format), and must both rows of a move share the same id?
7. Rules: what syntax is `pattern` — glob (e.g. `ABC-*`), regex, prefix? If several patterns match, which wins? What category for a SKU no rule matches?
8. Output row order — any preference? Should zero-quantity rows be kept?
9. Bad input (unknown header, unparseable date/qty, unknown unit, empty lines): fail the whole run with a non-zero exit, or skip the row with a warning?
10. Timezones: are both scanners' timestamps in the same local time?

### Answers
1. Two rows are the same scan when the location, the timestamp (to the minute), the quantity in single items and the SKU all match. Compare SKUs after normalising them. Identical rows inside one file are not duplicates: they are real separate scans, for example the same item scanned on two shelves. Across exports of the same location, match rows by count and keep the larger count. If export 1 has a row 2 times and export 2 has it 3 times, the inventory has it 3 times, not 5.

2. Yes. Two exports of the same location overlap, so a scan can appear in both, and those copies are duplicates. Compare timestamps to the minute. For Format B, drop the seconds and do not round them, so `14:30:59` becomes `14:30`.

3. A case is always 12 items. It is not per SKU, so `2,case` is 24 and `-1,case` is -12. Format B's `count` is always single items, even when the note says "case".

4. Yes, `barcode` and `SKU` are the same identifier. Normalise both: trim spaces, ignore case, and ignore leading zeros. `00123` and `123` are the same SKU, because scanner B drops the zeros.

5. A move is a negative scan at one location plus a positive scan at a different location, where:
   - the positive is exactly the opposite quantity in single items,
   - both are the same normalised SKU,
   - the two timestamps are at most 2 hours apart, inclusive.

   Ignore the `note` field completely. It tells you nothing about moves.

   Each row can be in at most one move. When a negative scan has several possible partners, pick the one closest in time. If that's a tie, pick the one that comes first in scan order: timestamp, then location name, then input order. Go through the negative scans in that same scan order.

6. Both rows of a move must share the same move_id, and it must not be empty. For the format: Your call — pick something reasonable and write down what you chose.

7. A pattern is a case-insensitive substring of the SKU. If several patterns match, the first matching rule in file order wins. A SKU that matches no rule gets the category `Uncategorised`.

8. Sort by location name, then normalised SKU, then timestamp, then the order the row appeared in its input. Zero-quantity rows: Your call — pick something reasonable and write down what you chose.

9. If a file's header matches neither format, exit with code 2, print a message, and write no output file. For a bad row (date that won't parse, quantity that isn't a whole number, unknown unit, blank SKU, empty line or anything else malformed), skip the row and print a warning to stderr naming the file and line. The run still succeeds with exit 0.

10. Yes. All timestamps from both scanners are shop local time.

UNCOVERED: Q6 (move_id format), Q8 (whether to keep zero-quantity rows). I also put empty lines under "malformed, skip with a warning" in Q9. That was my interpretation, not an explicit rule.

## Phase: requirements (round 2, before implementation)

### Questions
1. In the output `sku` column, what text should appear: the normalised SKU (trimmed, leading zeros removed, and upper-cased?) or the SKU as originally scanned? If original, which spelling when duplicates/variants differ?
2. Should rule patterns be matched against the normalised SKU or the raw scanned text (e.g. a pattern `00` or leading-zero patterns)?
3. For a move, may the positive scan (arrival) come before the negative scan (departure) in time, as long as they are within 2 hours of each other?
4. Are duplicates removed before moves are matched (so a duplicated departure only pairs once)?
5. A SKU made only of zeros (e.g. `000`): what is its normalised form — `0`, or is it invalid?

### Answers
1. Use the SKU as it was originally scanned, with only the outer spaces trimmed. Keep its case and its leading zeros. When duplicates spell it differently, use the spelling from the first occurrence, in `--location` argument order.

2. A pattern matches if it appears anywhere in the SKU, ignoring case. As for leading zeros, it's your call. Pick something reasonable and write down what you chose.

3. Yes. The two scans just need to be at most 2 hours apart, inclusive. Either one can come first.

4. Yes. The same scan showing up in two exports of one location counts as one scan, so it can only be part of one move. Identical rows inside a single export are different, though. They are separate real scans, so each one can pair on its own.

5. Your call. Pick something reasonable and write down what you chose.

(For the judge log, two answers were not covered by the key: Q2 on whether patterns match the raw or normalised SKU, and Q5 entirely. Q2's partial answer comes from the key's rule that a pattern is a case-insensitive substring match on the SKU.)
