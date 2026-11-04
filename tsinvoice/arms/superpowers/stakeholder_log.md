# Stakeholder log

## Phase: Brainstorming (clarifying questions)

### Q1
**Q:** When should two entries count as the same piece of work (a duplicate to remove)? For example: must the client, description, start and end all match exactly, or is it enough that two entries for the same client overlap in time? And if the very same entry appears twice inside a single export file, is that a duplicate or two real sessions?

**A:** 1. Overlapping in time is not enough. Two entries are the same entry only when the tracker, start, end, client and description all match. Client and description are compared after normalising: trim the spaces at both ends, collapse any run of whitespace inside to one space, and ignore case. For format B, the end is the start plus the duration. If the same entry appears twice inside a single export, those are two real sessions, not a duplicate. For example, two 09:00–09:30 "Standup" entries for the same client in the same file are two pieces of work. Across exports of one tracker, match by count. If export 1 has the entry 2 times and export 2 has it 3 times, the output has it 3 times. That is the max, not the sum.

### Q2
**Q:** You said a duplicate needs the same tracker. So what should happen when entries from two different trackers (desktop and phone) cover the same or overlapping time for the same client — e.g. desktop has 10:00–11:00 "Design" and phone has 10:00–11:00 "design", or desktop 10:00–11:00 and phone 10:30–11:30? Keep both in full, merge them into one session covering the union of the time, or something else? And same question for two partly overlapping (not identical) entries inside one tracker.

**A:** 1. Keep both, in full, every time. Entries from two different trackers never deduplicate against each other. So desktop 10:00–11:00 "Design" and phone 10:00–11:00 "design" are both kept, even though they match apart from case. Desktop 10:00–11:00 and phone 10:30–11:30 are also both kept. Don't merge them into one session covering the union of the time.

Inside one tracker, two entries count as the same entry only if start, end, and the normalised client and description all match exactly. Normalised means outer spaces trimmed, runs of inner spaces collapsed to one, and case ignored. Two entries that only partly overlap don't match that way, so they aren't duplicates. Keep both in full and don't merge them.

### Q3
**Q:** About joining entries you continued ("back to back"): when should two entries be joined into one session? Specifically: how big a gap between the end of one entry and the start of the next still counts as a continuation (exactly zero, or up to some number of minutes)? Do the client and the description both have to match (and compared how), or only the client? Can a chain of three or more entries join into one session? And what happens to the joined session's description and date — e.g. if it crosses midnight?

**A:** 1. Join Q onto P when Q starts exactly at P's end or up to 2 minutes after it, with 2 minutes itself included. The client and the description must both match after normalising: trim the spaces at each end, collapse runs of inner whitespace to one space, and ignore case. Chains of any length join into one session, which is one output row. The joined session uses the client and description of its first entry: the original text, trimmed at the ends, not lowercased. Its `date` is the date the session started. Don't split a session at midnight; that is out of scope, so a session that crosses midnight keeps its start date.

### Q4
**Q:** For a joined session, how are its minutes counted: the sum of the entries' own durations, or the wall-clock span from the first start to the last end (which would also bill the gaps of up to 2 minutes)? And how are fractional minutes handled — format B's duration_minutes can be a decimal like 12.5, and a session's minutes must be a whole number in the output: round (which way, and is a half rounded up or to even), truncate, and is the rounding done per entry or once on the session total? Also: if an entry starts before the previous matching entry has ended (they overlap, e.g. one from each app), should they be joined, or kept as separate rows?

**A:** 1. Minutes: a session's minutes are the sum of its entries' own durations. Gaps between joined entries are not billed, so it is not the wall-clock span.

Fractional minutes: a format B row whose duration_minutes isn't a whole number above zero (e.g. 12.5) is a bad row. Skip it, print a warning to stderr naming the file and line, and let the run still succeed. So durations are always whole numbers.

Rounding: round each session up to the next multiple of 6 minutes. Do this once, on the session total after joining, never per entry. Example: 09:00–09:07 continued by 09:07–09:14 is 14 minutes, billed as 18.

Overlap: don't join them. An entry continues another only if it starts exactly at the previous entry's end or up to 2 minutes after it (inclusive). An entry that starts before the previous one has ended doesn't qualify, so they stay as separate rows.

### Q5
**Q:** About the rates file (`pattern,hourly_rate`): what kind of pattern is it — a plain substring, a shell-style wildcard like `Acme*`, or a regular expression — and is matching case-sensitive? Does it match against the client, the description, or either one? When several patterns match the same session, which rate wins (first row in the file, the most specific/longest pattern, or something else)? What should happen when no pattern matches a session? And is the amount computed from the rounded-up billed minutes, and how is it rounded to 2 decimals (half up, or banker's rounding)?

**A:** 1. Every one of these is answered by the stakeholder's rules (none uncovered):
- **Pattern type:** A plain substring. It is not a wildcard or a regular expression.
- **Case:** Matching ignores case.
- **What it matches:** Either the client or the description. A match on either one counts.
- **Several matches:** The first matching row in the file wins.
- **No match:** The amount is `0.00` and the row still goes in the output. A warning naming the client and description goes to stderr.
- **Amount:** Billed minutes ÷ 60 × hourly_rate, using the minutes after rounding up to the next multiple of 6. Round the amount half-up to 2 decimals, not banker's rounding.

### Q6
**Q:** About time zones: format A times (`DD/MM/YYYY HH:MM`) have no time zone, while format B's `start_iso` may carry one (e.g. `2026-03-02T09:00:00Z` or `+05:00`) or may not. How should these be lined up when comparing and joining entries — for instance, is format A your local time, and what is that zone? If a format B time has an offset, should it be converted to that zone, or should the clock time be used as written? And should the output `date` be taken in that local zone?

**A:** 1. Use the clock time as it is written, everywhere. Treat both formats as local wall-clock time. You don't need to pick a zone for format A, because time zones aren't part of this project. If a format B `start_iso` has a UTC offset or a `Z`, drop it and don't convert. For example, `2026-03-02T09:00:00Z` and `2026-03-02T09:00:00+05:00` both mean 09:00 on 02/03/2026. The end is that start plus `duration_minutes`. Compare and join entries on those clock times. The output `date` is the date the session started, read from that same clock time.

### Q7
**Q:** About bad input, beyond the fractional-duration case: what should happen for (a) a format A row whose End is before or equal to its Start, or whose dates can't be parsed, or that has missing fields; (b) a file whose header matches neither format A nor format B; (c) a tracker path that doesn't exist, or a `--tracker` argument not in NAME=PATH form; (d) a rates file with a bad header or a non-numeric hourly_rate? For each: skip the row with a warning and carry on, or stop the whole run with a non-zero exit code (and what code)? Should the output file be written at all when the run fails?

**A:** 1.
(a) Skip the row and keep going. That covers an End that's blank, can't be parsed, or isn't after Start (so equal counts too), and any other row that can't be parsed, missing fields included. Print a warning to stderr that names the file and the line. The run still succeeds with exit 0.
(b) Stop the run with exit code 2 and a message. Don't write an output file.
(c) Your call — pick something reasonable and write down what you chose.
(d) Your call — pick something reasonable and write down what you chose.
On writing the output file when the run fails: for an unknown header, write no output file. For the other failures, it's your call — pick something reasonable and write down what you chose.

---
Note for the caller only, not part of the stakeholder's answer: these parts were UNCOVERED and got the fixed fallback reply: 1(c), 1(d), and output-file behaviour for any failure other than an unknown header.

**Decision (mine, for the "your call" parts):** (c) and (d) are fatal: message to stderr, exit code 2, no output file. Any fatal error leaves no output file (and does not touch an existing one) — all inputs are validated and processed before the output is written.

### Q8
**Q:** About the output file: in what order should the session rows be written (e.g. by client then start time, or by date then start time, and how are ties broken)? And for a joined session, what should the `session_id` look like — is there a required format (for example a hash of the joined entries, or a readable id built from client and start time), and must it stay the same when I re-run with the same inputs or when the order of the --tracker arguments changes?

**A:** I answered from the stakeholder rules. The question had several parts, so I answered each one separately. Here is the reply to give the builder:

1. Row order: Sort by client (normalised), then by session start time. Break any remaining ties by input order: --tracker argument order first, then line number.

session_id format: It must be non-empty and distinct for each session. Beyond that: "Your call — pick something reasonable and write down what you chose."

Re-running with the same inputs: The same inputs given in the same order must produce byte-identical output, so the session_id must stay the same.

Changing the order of the --tracker arguments: "Your call — pick something reasonable and write down what you chose."

Not covered by the stakeholder rules (log as UNCOVERED):
- The exact format of session_id.
- Whether session_id has to stay the same when the --tracker order changes.

**Decision (mine):** session_id = `s-` + first 12 hex chars of SHA-256 over the session's canonical content (each member entry's tracker name, start, end, normalised client, normalised description, in chronological order). It depends only on content, so it is stable across re-runs and across --tracker order changes. If two joined sessions have identical content, the later one in output order gets a `-2`, `-3`, ... suffix so ids stay distinct.

### Q9
**Q:** When joining continued entries, sometimes more than one entry could continue the same session — e.g. a session ends at 10:00 and two matching entries (say one from each app, or two identical ones in the same file) both start at 10:00–10:02. Which one joins the session and what happens to the other: does it start a new session of its own, or do both join? Similarly, if one entry could continue two different earlier sessions that end at the same time, which one does it join? And is duplicate removal always done before joining?

**A:** 1. Only one entry joins. An entry can have at most one predecessor and at most one successor, so two entries can never both continue the same session.
   - **Which one joins:** go through entries in start order. When an entry has several possible successors, take the one with the smallest gap after its end. If the gaps tie, take the one that comes first in input order: `--tracker` argument order first, then line number. Which app each entry came from doesn't matter.
   - **The other one:** it doesn't join that session. It stays separate. It can still continue something else if it qualifies.
   - **One entry that could continue two earlier sessions ending at the same time:** the same rule applies from the other side. Entries are processed in start order, so the earlier session gets first pick and takes it. If that's still a tie, first in input order wins. The entry joins only that one session.
   - **Duplicate removal:** yes, always first. Joining only happens after deduplication.

### Q10 (write-back of understanding, per brainstorming "Write back your understanding")
**Q:** Here is my understanding so far; please correct anything wrong. What you told me: duplicates only within one tracker NAME, exact match on start, end and normalised client+description, counted by max-per-export; different trackers never dedupe; overlaps never merge; continuation = same normalised client and description, next start 0–2 min after previous end, one predecessor/successor each, smallest gap then input order; minutes = sum of entry durations, rounded up to a multiple of 6 per session; rate = first rates row whose pattern is a case-insensitive substring of client or description, else 0.00 with a warning; amount half-up; clock times as written; bad rows skipped with a stderr warning; unknown header exits 2 with no output; output sorted by normalised client then start then input order. My assumptions, which you have not told me — please confirm or correct each: (a) a single, un-joined entry is also a session and is rounded up to a multiple of 6 the same way, with blank session_id; (b) for a joined session, the rate is chosen by matching against the first entry's client and description; (c) a format B duration like "30.0" is accepted as 30, but "12.5", "0", "-5" or "abc" are bad rows; (d) seconds in a format B start_iso (e.g. 09:00:30) are kept as written, so gaps and ends can include seconds; (e) a pattern row in the rates file with an empty pattern is ignored rather than matching everything; (f) leading/trailing spaces in header names and a UTF-8 byte-order mark at the start of a file are tolerated.

**A:** 1. Your summary is correct as you stated it. I have nothing to correct.

(a) Yes. Rounding applies to every session after joining, never to a single entry within a session, so a lone entry rounds up to the next multiple of 6 the same way. Only joined chains get a non-empty session_id, so a lone entry's session_id is blank.

(b) Your call — pick something reasonable and write down what you chose.

(c) The rule is that `duration_minutes` must be a whole number above zero. So "12.5", "0", "-5" and "abc" are bad rows: skip them and warn on stderr. Whether "30.0" counts as the whole number 30 is your call — pick something reasonable and write down what you chose.

(d) Your call — pick something reasonable and write down what you chose.

(e) Your call — pick something reasonable and write down what you chose.

(f) Your call — pick something reasonable and write down what you chose.

UNCOVERED log: (b), (c) for "30.0" only, (d), (e), (f).

**Decisions (mine):** (b) yes, the first entry's original client and description. (c) "30.0" accepted as 30 (any number with zero fractional part, > 0). (d) seconds kept; the 0–2 minute gap is 0–120 seconds inclusive. (e) empty-pattern rows are ignored with a stderr warning. (f) both tolerated (read as utf-8-sig, header cells stripped).

## Phase: Subagent-driven development (after final whole-branch review)

### Q11
**Q:** 1. If one of the export files is not valid UTF-8 (for example a Windows app saved it as Windows-1252, so "Café" has a byte the UTF-8 decoder rejects), should the whole run stop with exit code 2 and no output, or should the tool read that file anyway (e.g. falling back to Windows-1252) and print a warning?
2. If a format B row's `start_iso` is a date with no time (e.g. `2026-03-02`), should it be treated as midnight on that day, or is it a bad row to skip with a warning?

**A:** 1. Your call — pick something reasonable and write down what you chose.

2. Your call — pick something reasonable and write down what you chose.

(For the judge log: both questions are UNCOVERED. The key says nothing about file encoding. Its time rules cover offsets and `Z` on `start_iso`, and say unparseable rows are skipped, but they don't say whether a date with no time counts as unparseable.)

**Decisions (mine):** 1. Fall back: decode as UTF-8 (BOM tolerated); if that fails, decode the file as Windows-1252 and print `warning: <path>: not valid UTF-8, read as Windows-1252`. If it fails both, fatal exit 2. Applies to tracker files and the rates file. 2. Bad row (skip + warning): the brief says `start_iso` is an ISO 8601 *datetime*, so a time part is required.
