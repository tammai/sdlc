# Slice B3 plan: the review loop

Spec FR-04, FR-07, FR-08, FR-09, AC 5, 8 · Backlog B3. Instructed only (skill and agent text).

## Tasks

1. `references/stage-5-verify.md`, `stage-6-review.md`, `lite-flow.md` steps 3–4, `backlog-slices.md`: one parallel round (verifier + reviewer, qa-tester on M, silent-failure-hunter on the full flow, pr-test-analyzer only on L, ui-reviewer on UI diffs), fixes together, one re-verification; no simplifier pass. (FR-04, FR-07)
2. `agents/qa-tester.md`: runs in the M verify round; runtime files under `.sdlc/.work/qa/`. (FR-07)
3. `skills/writing-specs` step 10 and checklist, `templates/spec-template.md`, Lite spec: Failure modes as criteria. (FR-08)
4. `references/review-brief.md` cites failure modes, recurring defects and simplifications; `references/recurring-defects.md` seeded from the evals; Stage 11 appends to `<docs>/recurring-defects.md`. (FR-09)
5. Docs: specs 02 (ORC-FR-030), 03 (SCO-FR-026), 04 (VER-FR-005/031/034), guidebook, playbook, CHANGELOG.

## Public Surface

- reference files `review-brief.md` (changed), `recurring-defects.md` (new); project file `<docs>/recurring-defects.md` (optional) — FR-09
- spec section `Failure modes` — FR-08
