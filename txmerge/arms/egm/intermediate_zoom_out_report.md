# Stage 8: Intermediate Zoom Out Report

**Target:** `docs/designs/txmerge.md` (full file) · Reviewer: `egm-zoom-out` (completed) · Prior: `zoom_out_report.md` · Verdict: PASS with changes (0 Blocker, 1 Major, 6 Nit)

1. **Major** (L112, L167-180, L193-194, L300-302, D15/D21/D27, L425-426, L472, L475): Stage 8 output safety grew beyond the root need (symlink following, dangling-link creation, read-only refusal D27, mkstemp+chmod+umask dance, fsync and durability paragraph, concurrent-runs row). Regression against the Stage 5 disposition (plain `open()` so umask applies). Reduce to: refuse `--out` = input; write temp with plain open; os.replace; remove temp on failure.
2. Nit (L161, L286-287, L307, L418): amount index returned without a decision entry; size target unsourced. Keep scan or log the index.
3. Nit (L294-308): risk table repeats Alternatives/Decision Log.
4. Nit (L308): `0.00` unused-cell data loss outweighs power-loss mechanics; stakeholder question for a future round.
5. Nit (L188, L345, L140/L397, L386, L425): implementation detail in Technical Plan/errors table (131072 limit, zero normalisation twice).
6. Nit (L434, L112): `--out` overlap check should run in Stage 1 before reading inputs.
7. Nit (L484): coverage requirement range out of date (D17-D27).

## Elephant disposition
Applied 1 (Stage 8 reduced; D21, D27 removed; temp file `OUT.<pid>.txmerge-tmp` opened with `open(..., "x")` so umask applies and names do not collide; no fsync; durability out of scope as a Non-Goal; symlink at `--out` replaced by a regular file), 2 (index kept, logged as D28 with its stated cost; size line kept as an expectation), 5 (131072 limit removed from table and D24; zero normalisation kept in both places and CONTESTED: negating `0.00` in `parse_a` yields `-0.00`, so `parse_amount` alone cannot normalise it), 6 (`--out` overlap check moved to Stage 1), 7.
Declined: 3 (feature-spec standard requires Risks & Mitigations; rows cite their source), 4 (stakeholder round 1 Q8 already says a Format A row with both cells filled is malformed; risk row and M count make it visible).
