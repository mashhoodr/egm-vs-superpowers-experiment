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

K1 **Duplicates across exports.** Two exports of the same tracker overlap.
An entry is "the same entry" if tracker, start, end and the normalised client
and description all match (for format B, end is start plus duration).
Normalising means trimming spaces, collapsing inner whitespace runs to one
space, and ignoring case.

K2 **Identical entries inside one export are real.** Two 09:00–09:30 "Standup"
entries for the same client in the same file are two pieces of work. Across
exports of one tracker, match by count: if export 1 has the entry 2 times and
export 2 has it 3 times, the output has it 3 times (the max, not the sum).

K3 **Different trackers never deduplicate against each other.**

K4 **Format B time.** Take `start_iso` as local wall-clock time. If it carries
a UTC offset or `Z`, drop it and don't convert. The end is start plus
`duration_minutes`.

K5 **Bad rows.** In format A, if End is blank, unparseable, or not after Start,
skip the row; in format B, if `duration_minutes` isn't a whole number above
zero, skip it. Any unparseable row is skipped the same way. Print a warning
naming the file and line to stderr. The run still succeeds (exit 0).

K6 **Unknown header.** If a file matches neither format, exit with code 2 and
a message, and write no output file.

K7 **Continued entries.** After deduplication, entry Q continues entry P if
they have the same normalised client and description and Q starts at P's end
or up to 2 minutes after it (inclusive). The trackers don't matter: same app
or the other one. Chains of any length join into one session, which is one
output row with a non-empty session_id, distinct per session. Each entry has at most one predecessor and one successor.
Work through entries in start order; if an entry has several possible
successors, take the one with the smallest gap, and on a tie the one that
comes first in input order (`--tracker` argument order, then line).

K8 **Minutes and rounding.** A session's minutes are the sum of its entries'
durations; a gap between joined entries isn't billed. Round each session up to
the next multiple of 6 minutes, after joining, never per entry. Example:
09:00–09:07 continued 09:07–09:14 is 14 minutes, billed as 18.

K9 **Rates.** A pattern is a case-insensitive substring of the client or of
the description. The first matching rule in file order wins. Amount is
minutes ÷ 60 × hourly_rate, rounded half-up to 2 decimals. With no match the
amount is `0.00`, the row is still output, and a warning naming the client
and description goes to stderr.

K10 **Output order.** Sort by client (normalised), then session start time,
then input order (`--tracker` argument order, then line). `date` is the date
the session started. With duplicates, keep the first occurrence by
`--tracker` argument order.

K11 **Text in output.** Client and description come from the session's first
entry, original text from the first occurrence with outer spaces trimmed.
Don't lowercase them.

K12 **Determinism.** The same inputs in the same order give byte-identical
output.

K13 **Out of scope.** Time zones and daylight saving, currencies (all rates
are in one currency), splitting sessions at midnight, incremental runs against
an earlier invoice, a GUI, and fuzzy description matching are all out.
