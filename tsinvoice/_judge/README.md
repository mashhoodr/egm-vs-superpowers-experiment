# Judge kit: `tsinvoice` (problem 3, judge only)
- Module: `tsinvoice`, run as `python -m tsinvoice merge --tracker NAME=PATH ... --rates RATES.csv --out SESSIONS.csv`; key in `STAKEHOLDER.md` (K1–K13).
- Env var: `TSINVOICE_ROOT` = arm repo root (defaults to `reference/`, which passes 18/18).
- Tests: `TSINVOICE_ROOT=arms/<arm> python3 -m pytest -q -p no:cacheprovider _judge/hidden_tests`
- Probe: `python3 -I _judge/robustness_probe.py arms/<arm>` (reference: `_judge/reference`).
