# tsinvoice

Merge overlapping timesheet exports into priced, invoice-ready sessions. See BRIEF.md for the contract
and stakeholder_log.md for the product answers.

    python -m tsinvoice merge --tracker desk=a.csv --tracker phone=b.csv --rates rates.csv --out sessions.csv

## Rules (from the stakeholder)
- Duplicate = same tracker + start + end + client + description (whitespace-collapsed, case-insensitive).
  Only between exports of one tracker; repeats inside one file are real work. Per key we keep as many
  copies as the single file holding the most.
- Continuation = same client + description, next start 0-2 min after previous end, any tracker, any chain
  length. Start order; smallest gap wins, ties by input order.
- Minutes = sum of entry durations (gaps unbilled), rounded up to a multiple of 6 per session.
- Rate = first rates row whose pattern is a case-insensitive substring of client or first description;
  none -> 0.00 + stderr warning. Amount half-up to cents.
- ISO offsets dropped (wall-clock). Date = session start date. Sort: client (normalised), start, input order.
- Unknown header -> exit 2, no output. Bad rows -> skipped with file:line warning.

## My calls (stakeholder said "your call")
- Seconds in timestamps are truncated to the minute.
- `duration_minutes` like `30.0` counts as whole; `30.5`, `0`, negatives are skipped.
- Single-entry sessions have a blank session_id (per contract). Joined: `S-` + 12 hex of a SHA-256 over the
  constituent entries, `-2`, `-3` suffix on a collision.
- Missing/unreadable rates file or bad rates header -> exit 2, no output. Bad rates rows (blank pattern,
  non-numeric or negative rate) are skipped with a warning.
- Tracker NAME compared exactly (case-sensitive, outer spaces trimmed).
- Output is written atomically (temp file + rename).
