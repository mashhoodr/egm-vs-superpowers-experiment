# Stage 5: Initial Zoom Out Report

**Target:** `docs/designs/txmerge.md` (full file) · Reviewer: `egm-zoom-out` (completed) · Verdict: PASS with nits (0 Blocker, 0 Major, 8 Nit)

1. Nit (L11, L43): links to BRIEF/stakeholder_log/concepts_brief are relative to the wrong folder; use `../../`.
2. Nit (L87): "each stage takes a list and returns a list; only the first reads files" is untrue (rules read in stage 3; stages 6–7 mutate in place).
3. Nit (L246, L347): amount index for transfers is premature optimisation; use a linear scan or call it a readability choice.
4. Nit (L155, L235–239, L354): `NamedTemporaryFile` creates mode 0600, so the ledger loses normal umask permissions; document or fix.
5. Nit (L173–239): Alternatives A–G only restate stakeholder answers; merge them.
6. Nit (L291–363): module split acceptable; optionally inline exit constants / fold csvio into formats.
7. Nit (L315, L324–326, L354): grammar stated twice (Technical Plan and Implementation Plan) could drift; make one normative.
8. Nit (L149–151, L334–335): concepts_brief D17 (rule category literally `Transfer` allowed, no special meaning) was dropped.

## Elephant disposition
Applied: 1, 2, 3 (linear scan), 4 (temp file opened with plain `open()` so umask applies), 7 (Implementation Plan now points at the Technical Plan as normative and the two copies were checked equal), 8.
Declined: 5 (egm-draft requires carrying the brief's Alternatives Weighed into Alternatives Considered), 6 (module per stage maps decisions to tests).
