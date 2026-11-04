# Stakeholder log

## Phase: requirements (round 1)

### Questions
1. What counts as a duplicate? Must two entries match exactly (client, description, start, end/duration), or is the same client + same start time enough? Can the same entry appear in both apps (e.g. desktop and phone) and count as a duplicate, or are duplicates only between exports of the same tracker?
2. If a later export of the same tracker has an entry with the same start but a different end (I edited it), which wins — the longer one, the later export, or keep both?
3. If two entries for the same client overlap in time but aren't identical (e.g. 10:00-11:00 and 10:30-11:30), what should happen? Merge into the union 10:00-11:30, keep both, or something else?
4. Continuation: how big a gap between one entry ending and the next starting still counts as "continued"? Does the description have to match, or only the client? Is the client matched case-insensitively / ignoring whitespace?
5. For a joined session, what description should it get (first entry's, concatenated, other)? And what should session_id look like (any format OK as long as it's stable across runs)?
6. Rates: what is a pattern — plain substring, glob like `acme*`, or regex? Case-sensitive? If several patterns match, which wins (first in file, most specific, highest rate)? If none match, should the tool fail, price at 0, or skip the row?
7. Is a pattern matched against client OR description (either one matches), and for a joined session, which description is used for matching?
8. Rounding: how should minutes be rounded (seconds in ISO times, fractional duration_minutes) — round to nearest, up, down, or bill increments like 6/15 minutes? Round per entry or per final session? Amount rounding: half-up to cents?
9. Timezones: Format A times have no zone; Format B ISO may include an offset (e.g. +05:00 or Z). How should I relate them — treat Format A as local in some zone, or convert everything to one zone? Which date goes in the output for a session crossing midnight?
10. Output ordering: sorted by date, then client, then start time? Anything else?
11. Bad input (unknown header, unparsable row, end before start, missing rates file): fail with a non-zero exit code and message, or skip bad rows with a warning?

### Answers
1. Two entries are a duplicate only if the tracker, start, end and client and description all match. For format B, end means start plus duration. Compare client and description after trimming spaces, collapsing runs of inner whitespace to one space, and ignoring case. The same client and start time is not enough. An entry that shows up in both apps is not a duplicate. Different trackers never deduplicate against each other, so duplicates only happen between exports of the same tracker.

2. Keep both. A different end means it isn't the same entry, so neither one replaces the other.

3. Keep both. Only exact matches count as duplicates. 10:30–11:30 doesn't start at or just after 10:00–11:00's end, so it doesn't continue it either.

4. The gap can be 0 to 2 minutes, inclusive. The next entry must start at the previous one's end or up to 2 minutes after it. The description has to match as well as the client. Both are compared after trimming spaces, collapsing inner whitespace to one space, and ignoring case.

5. Use the first entry's description: the original text from its first occurrence, with outer spaces trimmed and not lowercased. session_id can be any format, as long as it's non-empty and different for each session. The same inputs in the same order must give byte-identical output, so yes, it has to be stable across runs.

6. A pattern is a plain substring, matched case-insensitively. If several patterns match, the first one in file order wins. If none match, still output the row with an amount of `0.00`, and print a warning to stderr that names the client and description.

7. Either one. A pattern matches if it's a substring of the client or of the description. For a joined session, use the session's first entry's description.

8. If `duration_minutes` isn't a whole number above zero, skip that row. Seconds in ISO times: your call — pick something reasonable and write down what you chose. A session's minutes are the sum of its entries' durations, and gaps between joined entries aren't billed. Round each session up to the next multiple of 6 minutes, after joining, never per entry. For example, 09:00–09:07 continued by 09:07–09:14 is 14 minutes, billed as 18. The amount is minutes ÷ 60 × hourly_rate, rounded half-up to 2 decimals.

9. Treat `start_iso` as local wall-clock time. If it has an offset or `Z`, drop it and don't convert. Time zones are out of scope, and so is splitting sessions at midnight. The output date is the date the session started.

10. No. Sort by client (normalised), then session start time, then input order (`--tracker` argument order, then line number). Date isn't a sort key.

11. Unknown header: exit with code 2 and a message, and write no output file. Unparsable rows, and rows whose end is blank, unparsable or not after start: skip the row, print a warning naming the file and line to stderr, and still exit 0. Missing rates file: your call — pick something reasonable and write down what you chose.

Not covered: seconds in ISO times (part of Q8) and a missing rates file (part of Q11).

## Phase: requirements (round 2)

### Questions
1. If the very same row appears twice inside ONE export file (not across two exports), is that a duplicate to remove, or real repeated time to keep?
2. Can a continuation chain run across trackers and through several entries (desktop 09:00-10:00, phone 10:01-10:30, desktop 10:31-11:00 all become one session)? Should two exact copies of an entry from different trackers (same client/description/start/end) be kept as two separate sessions, or can they join each other?
3. If two candidate entries could both continue the same entry (e.g. two different entries both starting at 10:00 after one ending at 10:00), how should that be resolved?
4. duration_minutes like "30.0" — whole (keep) or not (skip)? And Format A entries: are their minutes simply End minus Start?
5. A session that is a single entry (not joined): session_id blank, right? And is a row's "minutes" in the output the billed (rounded-up-to-6) minutes, with amount computed from those billed minutes?
6. Rates file problems: a row whose hourly_rate isn't a number, or an empty pattern — skip with a warning, or fail? Must the --rates file exist (fail with exit 2 if missing)?
7. Is the tracker NAME compared case-sensitively ("Desktop" vs "desktop" same tracker or not)?

### Answers
1. Real repeated time, keep both. Two identical entries in the same file are two separate pieces of work. For example, two 09:00–09:30 "Standup" entries for the same client in one export both stay.

2. Yes, a chain can cross trackers and run through any number of entries. Your desktop → phone → desktop example becomes one session. Two exact copies from different trackers are both kept, because different trackers never deduplicate against each other. They can't continue each other, though. An entry only continues another if it starts at that entry's end or up to 2 minutes after it. A twin starts at the same time as its copy, not at its end.

3. Go through entries in start order. Each entry has at most one predecessor and one successor. When an entry has several possible successors, take the one with the smallest gap. On a tie, take the one that comes first in input order: --tracker argument order, then line.

4. "30.0": Your call — pick something reasonable and write down what you chose. Format A: yes, an entry's minutes are End minus Start.

5. Single-entry session_id: Your call — pick something reasonable and write down what you chose. Minutes: yes. Each session is rounded up to the next multiple of 6 after joining, never per entry. The amount is the billed minutes ÷ 60 × hourly_rate, rounded half-up to 2 decimals. For example, 09:00–09:07 continued by 09:07–09:14 is 14 minutes, billed as 18.

6. Your call — pick something reasonable and write down what you chose.

7. Your call — pick something reasonable and write down what you chose.

[Judge log, not for the builder: these were UNCOVERED and got the fallback reply: Q4 "30.0", Q5 single-entry session_id, Q6 both parts (bad rates rows; missing --rates file), Q7 tracker-name case.]

> Builder note: the bracketed line above was emitted by the stakeholder subagent despite its instructions; logged verbatim as required. It only restates which answers were "your call".
