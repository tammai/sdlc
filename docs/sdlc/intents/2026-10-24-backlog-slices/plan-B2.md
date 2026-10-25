# Slice B2 plan: backlog and the slice loop

Spec FR-03–08, FR-11, AC 2–5, 8, 9 · Backlog B2.

## Tasks

1. `scripts/backlog.py` `next` / `check` — test `tests/test_backlog.py` (next ready slice; open dependency refused). (FR-07)
2. `hooks/trust_anchor.py`: on `Flow: lite`, leaving Stage 6 with code changed since the last full run is a notice — tests `test_lite_flow_next_slice_after_a_full_run_is_not_a_notice`, `test_lite_flow_leaving_stage_6_with_an_untested_fix_is_a_notice`. (FR-11)
3. `templates/backlog-template.md`; orchestrator: backlog decision in Stage 3 and Lite step 1, a "Backlog slices" section (slice loop, gates, overflow stop, proposals), §0 resume through `backlog.py`, state lines `Slice:`, `Slice base:`, `Slice gates:`. The backlog lives in the orchestrator, not in vendored `writing-plans`, so the Lite path loads no planning skill. (FR-03–06, FR-08)
4. `commands/start.md`: a leading `B<n>` starts that slice; rebuild `hosts/skills/` with `scripts/hosts.py`. (FR-07)
5. Docs: spec 02 (trust anchor, ORC-FR-024/025), README, guidebook, playbook, CHANGELOG, CONTRIBUTING layout and "Original" list.

## Public Surface

- script `scripts/backlog.py` (`next`, `check`) — FR-07
- template `templates/backlog-template.md` — FR-03
- state lines `Slice:`, `Slice base:`, `Slice gates:` — FR-05, FR-06
- `/sdlc:start B<n>` argument — FR-07
