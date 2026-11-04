# Stage 9 R2 egm-implementation-readiness (completed): 0 Blocker, 2 Major, 5 Nit
M1 conftest `run` fixture importing txmerge.cli at module level breaks Phases 2-5; import inside fixture body.
M2 \r quoting checked only on 3.13 (same as style M1; Elephant verified on 3.11.14).
Nits: read_ledger import mechanism; write fixture parent dirs + relative path test; Phase 1 pytest exits 5 with no tests; pytest>=7.0 for pythonpath; D1/D11 not tagged.
