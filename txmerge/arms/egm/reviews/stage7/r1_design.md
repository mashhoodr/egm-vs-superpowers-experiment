# Stage 7 R1 egm-design (completed): 0 Blocker, 4 Major, 13 Nit
M1 L251-289 no Risks & Mitigations; security missing (CSV formula injection); surviving-duplicate failure mode (truncated/changed rows double-count) missing.
M2 L87,161,174 --out can equal an input/rules file and silently replace it; refuse with exit 2.
M3 L161, L29 output-safety claim overstated: temp not cleaned up, no fsync, fixed temp name collisions, symlink --out, permissions.
M4 L254, L37 "fast enough, no index" unbacked; O(n*m); bucket inflows by amount or state a measured limit.
N5 ASCII digits / re.ASCII. N6 long amounts -> InvalidOperation -> treat as malformed. N7 split on first '=' in Tech Plan; repeated --rules/--out. N8 line_num captured before read. N9 bank preamble lines -> exit 2, list as limitation. N10 REASON texts for amount/both/neither/field count. N11 rule category 'Transfer' — warn? record. N12 U includes rule-assigned 'Uncategorised' — state. N13 check rules existence first (optional). N14 case-variant account names warn (optional). N15 Alt H reason. N16 no architectural alternative (streaming, SQLite). N17 headings nested under NFR (dup of structural M1).
