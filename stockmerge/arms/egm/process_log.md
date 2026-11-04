# Process log (EGM arm)

Decisions made by the Elephant at process gates, and departures from skill text.

## Setup
- Read `docs/claude.md`, then each skill's `SKILL.md` before running it (skills are not model-invocable).
- Artifact directory: repo root `arms/egm/` (no `EGM artifact directory:` line applies).

## egm-brainstorm
- Step 1 clarification: questions go to the stakeholder subagent per `prompts/stakeholder.md`.
  Departure: the skill asks for multi-turn chat questions; each "turn" here is one stakeholder
  spawn with a batch of open-ended questions (the stakeholder prompt allows batching). Several
  rounds are run until the problem is clear.
- Round 1: 10 questions; round 2: 11 questions. Stakeholder left several as "your call";
  the Elephant's choices are recorded in the anchored hypothesis below and in `concepts_brief.md`.
- Note: the round-2 stakeholder reply included a "(Judge log: ...)" line. Logged verbatim; not acted on.
- Readiness gate (process): decided "Review with Goldfishes" — two rounds settled every behaviour
  question the brief raises; remaining gaps are explicitly delegated to the builder.
- Goldfish brainstorm via `egm:egm-synthesizer` (Mode BRAINSTORM, 6 lenses): worked; all 6 completed.
  30 findings (3 Blocker, 20 Major, 7 Nit) in `brainstorm_findings.md`.
- Step 3 iteration: asked the stakeholder the brief's Stage 0 questions (round 3, 8 questions);
  answers appended to `concepts_brief.md`.
- Step 3 loop-back decision: did not re-run the brainstorm swarm. Every Blocker/Major has a recorded
  decision or owner answer, and `egm-review` will run fresh Goldfish over the full draft.
- Step 4 alignment/handoff gate (process): "Proceed to /egm-draft".

## egm-draft
- Step 1 intake: `concepts_brief.md` (Priority 1). Consensus gate (process): start drafting.
- Owner-Decides-Architecture (constraint 13): the only multi-answer design choices (survivor rule,
  SKU spelling, time model, matching algorithm) were product behaviour and went to the stakeholder
  in rounds 1-3. Internal module layout has one defensible answer for a 9-step pipeline; decided
  by the Elephant. Departure: no separate architecture gate was put to the stakeholder.
- Departure: the skill drafts and gates one section per turn. All sections (Overview & Goals,
  Technical Plan, Alternatives, Detailed Implementation) were written in one pass to
  `design_draft.md`, then each section gate was decided: "Approve and proceed" (no revisions;
  decisions trace to the brief and stakeholder log).
- Step 6.1 reconciliation vs `concepts_brief.md`: no open contradictions. Two brief items were
  superseded by the owner's round-3 answers (SKU spelling per kept row, not per location; Format B
  rows with >4 fields are skipped, not kept); the draft follows the owner answers. No additions
  that change architecture, interfaces or dependencies.
- Step 6.2 target directory gate (process): "Save to detected directory: docs/designs/" ->
  `docs/designs/stockmerge.md`. No SITEMAP.md exists. This file is the review target.

## egm-review
- TargetFile: `docs/designs/stockmerge.md`. GoldfishContext (process): `BRIEF.md` only (the fixed
  contract a reader needs); not the brief/stakeholder log, so reviewers judge the doc on its own.
- Preset gate (process): Preset 0 "Interactive review with all review rubrics" — the most complete:
  all five stages (5-9) with remediation via egm-resolve at Stages 7 and 9 and checkpoint gates.
  The Elephant answers every checkpoint itself, choosing the most thorough option.
- Semantic split: boundary `## Detailed Implementation Plan` at line 489.
  FeatureRange 1..488, DetailedRange 489..722.
- Stage 5 (zoom-out via synthesizer: worked, completed, ran A+B instances): 0 Blocker, 2 Major, 6 Nit.
  Checkpoint (process): Option 1 "update doc first", fixed both Majors (zoom-out-1-1 exception
  backstop; zoom-out-1-2 dropped pre-open existence checks, kept realpath check), then one re-audit.
  Nits not fixed at this stage (Stage 5 has no resolve step; they are low severity).
- Stage 5 re-audit (synthesizer, A+B): 0 Blocker, 0 Major, 12 Nit -> clean. Checkpoint (process):
  "Proceed to Stage 6". Nits recorded in `zoom_out_report_r2.md`, not fixed.
- Stage 6 (Comprehension): direct dispatch of `egm:egm-comprehension` as the skill requires
  (not via synthesizer). FeatureRange 1..495, DetailedRange 496..735.
- Stage 6 result: completed; 0 Blocker, 2 Major, 8 Nit. Departure: `comprehension_report.md` keeps
  both paraphrase sections verbatim but condenses each finding to one line (full text was in the
  reviewer's reply), to keep the report short.
  Checkpoint (process): Option 1 "update doc first". Fixed both Majors (1-1 summary counters
  defined; 1-2 non-goal reworded) and Nits 1-3, 1-4, 1-5, 1-6, 1-7, 1-9, 1-10. Nit 1-8 (full output
  table in worked example) left for Stage 7 if raised again. One re-audit next.
- Stage 6 re-audit: 0 Blocker, 1 Major, 6 Nit. 1-audit cap reached, so per the skill the stage
  advances; but because the brief requires every high/medium finding addressed, the Elephant fixed
  2-1 (Major) and all six Nits before advancing, without a third audit (cap). Report:
  `comprehension_report_r2.md`. Checkpoint (process): "Proceed to Stage 7".
- Stage 7 (Critic, egm-review-loop) round 1 via synthesizer: worked; design/structural/style all
  completed. 0 Blocker, 4 Major, 27 Nit. Round not clean.
  egm-resolve: Elephant verified design-1-2 (unclosed quote) and design-1-3 (int digit limit)
  empirically in the scratchpad before accepting. Resolution gate (process): "auto accept" —
  4 Major + 25 Nit fixed, 2 Nit declined, 0 contested. `goldfish_review_report.md` written.
  Edits touched the DetailedRange too (R4.8, R4.12 plan) so the plan matches the spec.
- Stage 7 round 2 (synthesizer, all 3 completed): 0 Blocker, 2 Major (+2 reviewer-Majors the
  synthesizer downgraded to Nit; the Elephant kept the reviewer severity per egm-resolve and fixed
  them), 21 Nit. Not clean. Auto accept: 4 Medium + 8 Low fixed, 11 Low declined.
  design-2-1 fix verified in the scratchpad (single-line csv re-parse).
- Stage 7 round 3 (synthesizer, all 3 completed; asked to keep reviewer severities): 0 Blocker,
  10 Major, 21 Nit. Not clean. Auto accept: 9 Major fixed, design-3-2 part fixed / part contested
  (exit-0-on-all-skipped is the owner's rule). Nits declined this round. UTF-8 change verified.
- Stage 7 round 4 (synthesizer, all 3 completed): 0 Blocker, 4 Major, 23 Nit. Not clean.
  Auto accept: 4 Major fixed; Nits declined. Round 5 is the cap.
- Stage 7 round 5 (synthesizer, all 3 completed): 0 Blocker, 3 Major, 20 Nit. Auto accept: 3 Major
  + 2 Nit fixed, 18 Nit declined.
- Stage 7 loop cap (5 rounds) reached without two consecutive clean rounds. Cap gate (process):
  "accept and proceed" — no Blocker/Major is left open (all were fixed in the round they appeared),
  and the Majors in rounds 3-5 were mostly wording/layout, a sign of reviewer sampling rather than
  a design gap. Continuing past the cap would not satisfy convergence any faster.
- Stage 7 checkpoint (process): Option 1 "Resolve findings with agent" was applied each round;
  then "Proceed to Stage 8".
- Stage 8 (zoom-out via synthesizer, A+B completed): 0 Blocker, 2 Major (instance B; A said Nit),
  13 Nit. Checkpoint (process): Option 1 "update doc first"; fixed both (one part contested with
  reason) and the diagram Nit. No re-audit: Stage 9 reviews the plan next and the loop cap
  philosophy applies; recorded as a departure (the skill allows 1 re-audit; not used here).
- Stage 8 re-audit (synthesizer, A+B): 0 Blocker, 4 Major (higher of the two instance ratings), 5 Nit.
  Fixed 8b-1 (churn with design-5-1; resolved by removing both bisect and the size claim), 8b-2;
  8b-3 part fixed / part contested; 8b-4 contested with evidence added as Alternative L.
  1-audit cap reached; checkpoint (process): "Proceed to Stage 9".
- Stage 9 split: DetailedRange starts at line 640.
- Stage 9 (Implementation Readiness, egm-review-loop) round 1 via synthesizer: worked, all 3
  completed. 0 Blocker, 7 Major, 22 Nit. Auto accept: Detailed Implementation Plan rewritten
  (phases, rule-to-test map, explicit helpers). Not clean; next round.
- Stage 9 round 2 (synthesizer, all 3 completed): 0 Blocker, 6 Major, 20 Nit. Auto accept: 6 Major
  fixed. Not clean; next round.
- Stage 9 round 3 (synthesizer, all 3 completed; impl-readiness verdict READY): 0 Blocker,
  3 Major (each rated Nit by another reviewer), 22 Nit. Fixed all 3. Not clean; next round.
- Stage 9 round 4 (synthesizer, all 3 completed): 0 Blocker, 6 Major, 32 Nit. Fixed all 6 Majors.
- Stage 9 round 5 (synthesizer, all 3 completed): 0 Blocker, 1 Major, 21 Nit. Fixed the Major.
- Stage 9 loop cap reached (5 rounds, not two consecutive clean rounds). Cap gate (process):
  "accept and proceed" — all Majors fixed, round 5 down to one Major, nothing open above Nit.
- Stage 9 terminal gate (process): Option 1 (resolve) applied each round, then
  "Conclude review and finalize document". Status set to Approved.

## Implementation
- Spawned ONE fresh `general-purpose` implementer with the prescribed prompt, pointing at
  `docs/designs/stockmerge.md`. It committed `8f99ba5`. Elephant re-ran `python3 -m pytest`:
  122 passed (CPython 3.13.7; `python` and 3.11 are not on PATH here). Smoke run of the brief's
  command line with a case-to-each move: exit 0, correct output.

## Departures summary
- Clarification batched per stakeholder spawn (3 rounds) instead of one question per chat turn.
- Draft sections written in one pass, then gated, instead of one section per turn.
- No separate architecture gate to the stakeholder (product choices went to the stakeholder).
- `comprehension_report.md` condenses findings to one line each (paraphrases kept verbatim).
- Re-audit / loop caps: Stage 6 and Stage 8 Majors found in the capped re-audit were fixed without
  a further audit; Stages 7 and 9 closed at the 5-round cap with "accept and proceed".
- The synthesizer downgraded two reviewer Majors in Stage 7 round 2; the Elephant kept reviewer
  severity (egm-resolve) and told later synthesizer runs not to change severities.
