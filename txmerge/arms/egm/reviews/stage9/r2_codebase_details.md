# Stage 9 R2 egm-codebase-details (completed): 0 Blocker, 2 Major, 12 Nit
M1 \r quoting only checked on 3.13; require pytest on 3.11 (Elephant verified 3.11.14 quotes).
M2 "repository root" ambiguous (reviewer assumed outer git root; arms/egm is its own git repo); name it; subprocess cwd from __file__.
Nits: Phase 1 pytest exit 5; detect None order / name clash; temp removal error masking; samefile error names p; pytest>=7.0; read_ledger import; write parent dirs + chdir; [D21] withdrawn; [D1] untagged; help strings; import sys; field_size_limit.
