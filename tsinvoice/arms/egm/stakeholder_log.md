# Stakeholder log

## Phase: egm-brainstorm, Step 1 (clarification), round 1

### Questions
1. When should two entries count as the same entry (a duplicate from overlapping exports)? For example: same tracker with identical client, description, start and end; or the same work recorded in both apps; or entries whose times overlap but don't match exactly. What would you want to happen in each case?
2. If an entry appears in two exports of the same tracker but with different details (say, the end time was edited, or the description was fixed later), what should the tool do?
3. When you continue a piece of work (in the other app or the same one), how close together do the two entries have to be to count as one session? Do they need the same client? The same description?
4. How should a rate pattern be matched against the client and description — exact text, substring, wildcard, regular expression? Case-sensitive or not? What if several patterns match, or none match?
5. How should minutes be rounded to a whole number, and how should the amount be rounded to 2 decimals?
6. Times in the desktop export have no timezone. Phone ISO times might include an offset (like +05:00 or Z). How should times from the two apps be compared and which date should be printed?
7. If a session runs past midnight, which date should the row get? Should it be split?
8. When entries are joined into one session, what should the description be, and what should the session_id look like?
9. In what order should the output rows be sorted?
10. Client names may differ slightly between the two apps (case, extra spaces). Should those be treated as the same client?
11. What should happen with bad rows: unparseable dates, end before start, zero or negative duration, missing fields, or a file whose header matches neither format?
12. Who is the main user and how will you know this tool is working well for you?

### Answers (verbatim)
1. Two entries are the same entry only when they come from the same tracker and their start, end, client and description all match. Compare client and description after trimming spaces, collapsing runs of inner whitespace to one space and ignoring case. For the phone format, the end is start plus duration_minutes.
   - Same tracker with identical client, description, start and end in two overlapping exports: it's a duplicate, so keep one. Match by count: if export 1 has it twice and export 2 has it three times, output it three times (the larger count, not the sum). Identical entries inside one export are separate pieces of work and all stay.
   - The same work recorded in both apps: never deduplicate. Different trackers never dedupe against each other.
   - Times that overlap but don't match exactly: not the same entry. Keep both.

2. If any of those details differ, it's not the same entry, so both are kept. There's no fuzzy matching.

3. Q continues P when Q starts at P's end or up to 2 minutes after it, inclusive. They must have the same client and the same description, both compared after normalising. It doesn't matter which app either entry came from. Chains of any length join into one session. Work through entries in start order. If an entry has several possible successors, take the one with the smallest gap. On a tie, take the one that comes first in input order (--tracker argument order, then line).

4. Case-insensitive substring, matched against the client or the description. If several patterns match, the first rule in file order wins. If none match, the amount is 0.00, the row is still output, and a warning naming the client and description goes to stderr.

5. A session's minutes are the sum of its entries' durations. Gaps between joined entries aren't billed. Round each session up to the next multiple of 6 minutes, after joining and never per entry. For example, 09:00–09:07 continued by 09:07–09:14 is 14 minutes, billed as 18. The amount is minutes ÷ 60 × hourly_rate, rounded half-up to 2 decimals.

6. Treat the phone start_iso as local wall-clock time. If it has an offset or Z, drop it and don't convert. Then compare it directly with the desktop times. The printed date is the date the session started. Time zones and daylight saving are out of scope.

7. The row gets the date the session started. Don't split it, since splitting at midnight is out of scope.

8. The description (and client) come from the session's first entry. Use the original text from its first occurrence with outer spaces trimmed, and don't lowercase it. The session_id must be non-empty and different for each session. On its exact format: "Your call — pick something reasonable and write down what you chose." (UNCOVERED)

9. Sort by client (normalised), then session start time, then input order (--tracker argument order, then line).

10. Yes. Client names that differ only in case or spacing are the same client: trim, collapse inner whitespace and ignore case. Output keeps the original text from the first occurrence, trimmed.

11. Bad rows are skipped, each with a warning to stderr naming the file and line, and the run still succeeds (exit 0):
   - Desktop format: skip the row if End is blank, can't be parsed, or isn't after Start.
   - Phone format: skip the row if duration_minutes isn't a whole number above zero.
   - Any other row that can't be parsed (bad dates, missing fields) is skipped the same way.
   - A file whose header matches neither format is different: exit with code 2, print a message, and write no output file.

12. "Your call — pick something reasonable and write down what you chose." (UNCOVERED)

## Phase: egm-brainstorm, Step 1 (clarification), round 2

### Questions
1. The output `minutes` column: is it the billed minutes after rounding up to a multiple of 6 (e.g. 18), or the raw worked minutes (e.g. 14)? And is the amount always computed from the number printed in `minutes`?
2. When a later entry starts before an earlier one ends (overlapping times, same client and description), is that a continuation that should be joined, or two separate sessions?
3. Joining chains: once an entry has been joined as the successor of one entry, can another entry also claim it? And if two earlier entries could both be continued by the same later entry, which one gets it?
4. Phone format: if `duration_minutes` is something like "30.0" or "29.5", or start_iso has seconds (e.g. 09:00:30), how should those be handled?
5. How exact must the header row be to detect a format — e.g. extra spaces, different letter case, a byte-order mark at the start, extra columns, or columns in a different order?
6. What should happen if a tracker file or the rates file doesn't exist, or the rates file has a bad row (missing pattern, non-numeric rate, wrong header)? What should happen if a --tracker argument isn't in NAME=PATH form?
7. Do two different tracker NAMEs always count as different trackers, even if they are the same format? And do several paths with the same NAME always count as exports of one tracker?
8. If all inputs produce no valid entries, should an output file with just the header be written?
9. Should a single (not joined) entry also be rounded up to a multiple of 6 minutes?
10. Can the output file path be the same as an existing file — overwrite it silently? And should the tool print anything to stdout on success?

### Answers (verbatim)
1. The `minutes` column is the billed figure, rounded up after joining. In your example it's 18, not 14. And yes, the amount is always worked out from that billed number: minutes ÷ 60 × hourly rate, rounded half-up to 2 decimals.

2. They're two separate sessions. An entry only continues an earlier one if it starts exactly when the earlier one ends, or up to 2 minutes after (2 minutes counts). An entry that starts before the earlier one ends doesn't qualify.

3. No, it can't be claimed twice. Each entry has at most one predecessor and one successor. Work through the entries in order of start time. The earlier-starting entry picks its successor first, so it gets the shared later entry. When an entry has several possible successors, it takes the one with the smallest gap. On a tie, it takes the one that comes first in input order: `--tracker` argument order, then line number.

4. `duration_minutes` must be a whole number above zero. If it isn't, skip the row, print a warning to stderr naming the file and line, and still exit 0. So "29.5" gets skipped. For "30.0" and for a start time with seconds: Your call — pick something reasonable and write down what you chose.

5. Your call — pick something reasonable and write down what you chose.

6. Your call — pick something reasonable and write down what you chose.

7. Your call — pick something reasonable and write down what you chose.

8. Your call — pick something reasonable and write down what you chose.

9. Yes. A single entry is its own session, and every session is rounded up to the next multiple of 6 minutes.

10. Your call — pick something reasonable and write down what you chose.

## Phase: egm-brainstorm, Step 3 (iteration on Goldfish objections), round 3

### Questions
1. You said a session's client and description come from its first entry, and also that client names keep "the original text from the first occurrence". If "Acme" appears in one session and "ACME" starts a later session, should the later row print "ACME" (its own first entry) or "Acme" (the first time that client appears anywhere in the input)?
2. When duplicates are reduced to the larger count (say export 1 has an entry twice, export 2 three times), which copies are the ones kept — does it matter which export they come from (for example for input order, or if the copies differ only in letter case or spacing)?
3. When entry P's best successor has already been taken by an earlier-starting entry, should P then take its next-best free successor (if one is within 2 minutes), or have no successor? And can an entry that has been taken as a successor still pick its own successor, so chains form?
4. When several entries start at the same moment, in what order should they be considered for joining?
5. If a row in the rates file is broken (empty pattern, rate not a number, negative rate), should the tool skip that rule with a warning, or stop with an error?
6. Will your invoices quote the session_id, so that it should stay the same when you rerun with a newer, bigger set of exports? Or does it only need to be unique and stable for identical inputs?
7. The rules can bill the same time twice: an entry edited between exports (09:00–10:00, later 09:00–10:30) is kept as two entries, and work timed in both apps is kept twice. Do you want the tool to warn about sessions for the same client that overlap in time, or to stay silent?
8. Should a row with a blank client, or a blank description, be skipped with a warning or kept?
9. When a session gets no matching rate, should the warning appear once per output row or once per distinct client and description?

### Answers (verbatim)
1. Use "ACME". The client and description come from that session's own first entry. "First occurrence" only matters when one entry is duplicated: you print the text from the copy you kept, with outer spaces trimmed. Don't lowercase it.

2. Yes, it matters. Keep the first occurrences in `--tracker` argument order, then line order. In your example that means export 1's two copies, plus one copy from export 2 to reach three. The text and input position come from the copies you kept.

3. An entry can have only one predecessor and one successor. Go through entries in start order. Each entry takes the closest possible successor (smallest gap) that is still free, and on a tie the one that comes first in input order. If its best successor is already taken, it takes the next-best free one within 2 minutes. If none is free, it has no successor. Yes, an entry that was taken as a successor still picks its own successor, so chains form. A chain of any length becomes one session.

4. Use input order: `--tracker` argument order, then line.

5. Your call. Pick something reasonable and write down what you chose.

6. It only needs to be non-empty, different for each session, and the same when the inputs are the same and in the same order. I won't be rerunning against an earlier invoice.

7. Your call. Pick something reasonable and write down what you chose.

8. Your call. Pick something reasonable and write down what you chose.

9. Warn for each output row. The row is still output with amount `0.00`, and its warning names the client and description.

Log: questions 5, 7 and 8 were not covered (UNCOVERED).

## Phase: egm-review, Stage 8 re-audit (resolving finding zoom-out-4-1), round 4

### Questions
1. If an export file has a quote character that is opened and never closed (for example a description starting with `"` and no closing `"`), a CSV reader will treat every following line of that file as part of one giant field, so all the later rows in that file would be lost behind a single "bad row" warning. Should the tool skip that as one bad row and carry on (exit 0), or stop with an error (exit 2) so you fix and re-export the file?

### Answers (verbatim)
1. Skip it as one bad row and carry on. Print a warning to stderr that names the file and the line, and the run still succeeds with exit 0. Don't stop with exit 2 for this.
