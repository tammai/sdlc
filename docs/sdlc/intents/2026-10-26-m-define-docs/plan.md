# Plan: Define writes what, why and how to files

**Intent:** [intent.md](intent.md) · **Spec:** [spec.md](spec.md) · **Build:** native

## Tasks

1. **Plan template and Define** — FR-001, FR-002, FR-003, FR-006
   - Files: `templates/plan-template.md` (new), `skills/orchestrator/references/define.md`, `start.md` (state template line)
   - Test first: none (instruction text; the testing rule makes it instructed only)
   - Then: Define writes intent, spec (what only) and plan on every track; the approval lists all three; the self-contained rule
   - Run: `python3 -m unittest discover -s tests -t tests`
2. **Build, Prove, slices, UI** — FR-004, FR-005, FR-006
   - Files: `references/build.md`, `prove.md`, `review-brief.md`, `backlog-slices.md`, `ui-work.md`, core `SKILL.md`
   - Then: build from `plan.md` and write deviations back; `--plan plan.md`; the slice outline in Define, `plan-B<n>.md` at slice start
3. **Bundled skills** — FR-002, FR-003
   - Files: `skills/writing-specs/SKILL.md` (no tasks or surface), `skills/writing-plans/SKILL.md` (no execution question under the orchestrator), `templates/spec-template.md` (plan link)
4. **Docs** — AC 6
   - Files: guidebook, playbook, README, specs 02 and 03, ADR 0010, CHANGELOG, `sdlc_full_flow.svg` and `sdlc_tracks_full_stage_tree.svg` labels; stale-docs audit
   - Run: `python3 scripts/hosts.py check`, `claude plugin validate .`, the suite

## Public Surface

- file `templates/plan-template.md` — FR-003

## Review Focus

- A resumed full-flow feature at old Stage 3 that already has a `plan.md`: Define must reuse it, not overwrite it.
- `writing-plans` run on its own (no orchestrator) must still ask its execution question.

## Deviations
