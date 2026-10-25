# Slice B3 plan: feature close

Spec FR-09, AC 6 · Backlog B3.

## Tasks

1. `scripts/diff_stats.py`: `--plan` repeats; the union of the plans' Public Surface is declared — test `test_feature_close_checks_the_union_of_every_slice_plans_surface`. (FR-09)
2. Orchestrator "Backlog slices" step 8, `▶ Feature close`: whole-branch verifier round, one top-tier review with every slice plan, Stage 7, Stage 8 hard stop, Stage 11 on L. (FR-09)
3. Docs: spec 02 ORC-FR-024, spec 03 SCO-FR-015, guidebook, CHANGELOG.

## Public Surface

- `diff_stats.py --plan` repeatable — FR-09
