# Judge kit for `stockmerge` (problem 2)
Module: `stockmerge` (reference at `reference/stockmerge/`). Env var: `STOCKMERGE_ROOT` = repo root under test.
Key: `STAKEHOLDER.md` (K1–K13). Tests: `STOCKMERGE_ROOT=/path/to/arm python3 -m pytest -q -p no:cacheprovider _judge/hidden_tests`
Probe: `python3 -I _judge/robustness_probe.py /path/to/arm` (10 beyond-key cases).
Reference self-check: run the pytest command with no env var set; expect 18 passed.
