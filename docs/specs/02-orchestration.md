# Spec 02: Orchestration

The orchestrator takes a request through the lifecycle: sizes it, runs one stage at a time with the bundled pieces, records progress in `.sdlc/<feature>/state.md`, and stops at gates.

**Entry points:** `/sdlc:start [request]`, `/sdlc:status` · **Source:** `skills/orchestrator/SKILL.md`, `commands/start.md`, `hooks/model_router.py`

## User scenarios

1. **Start a feature.** Given a set-up repo with no active feature, when the user runs `/sdlc:start add CSV export`, then the orchestrator proposes a track with its reason, creates `state.md`, and announces the stages and the first one.
2. **Resume.** Given one `state.md` with `Status: active`, when the user runs `/sdlc:start` with no argument, then it summarizes feature, stage and open items in 2–3 lines and continues. Given several, it asks which.
3. **Repo not set up.** Given no `.sdlc/config.json`, when the user starts work, then it stops and offers setup; if declined, it continues with detected commands and records a Deviation.
4. **Skip a gate.** Given a gate in progress, when the user says "skip" or "just ship it", then it names the gates being skipped, records them under Deviations, and complies.

## Requirements

| ID | Requirement | Guarantee |
|---|---|---|
| ORC-FR-001 | On start, find `.sdlc/*/state.md` with `Status: active`: one → resume; several → ask; none → new feature. | `[instructed]` orchestrator §0 |
| ORC-FR-002 | Run `scaffold.py status` first: not set up → hard stop offering setup; setup in progress → offer to resume; behind → one line and offer `/sdlc:upgrade` without blocking; plugin too old → warn and continue only on the user's word. | `[instructed]` orchestrator §0; status output `[enforced]` test_scaffold › test_drift |
| ORC-FR-003 | Commands come from `.sdlc/config.json` (per package in a monorepo); if the contract isn't ok, say what's missing before Stage 4. Without setup, detect native commands and record them in `state.md`. | `[instructed]` orchestrator §0 |
| ORC-FR-004 | Propose the smallest track whose signals fit: **S** (bug or tweak, 1–3 files) runs 4 → 5 → 6 light → 8; **M** (a few files to a few days) runs 1 → 3 → 4 → 5 → 6 → 7 light → 8, plus 2 if the approach isn't obvious; **L** (new service, unclear approach, auth/payments/migration/public API) runs all 11. Sizing up names its signal in `state.md`. The user can override. | `[instructed]` orchestrator §0 |
| ORC-FR-005 | Work touching auth, payments, secrets, PII or schema migrations is at least M and always gets the full Stage 7. | `[instructed]` orchestrator §0; also in the generated `sdlc-sensitive.md` and `sdlc-migrations.md` rules |
| ORC-FR-006 | Each stage starts by printing its header: stage, track, what it uses, its gate. | `[instructed]` orchestrator "Stage header" |
| ORC-FR-007 | One stage at a time; `state.md` updated at every transition (stage, gate result, artifact paths). | `[instructed]` orchestrator "Rules" |
| ORC-FR-008 | Hard stops, always asking the user: end of Stage 1, end of Stage 2, execution method, merges, production deploys, DB migrations, anything irreversible. | `[instructed]` orchestrator "Rules" |
| ORC-FR-009 | A failed gate means stay in the stage or step back one, with the reason written in `state.md`. | `[instructed]` orchestrator "Rules" |
| ORC-FR-010 | Stage gates: **1** checklist passes, no `[NEEDS CLARIFICATION]`, no `[inferred]`, Non-Goals filled, testable criteria, user approves · **2** every FR/SC mapped, every Complexity Tracking row cites a requirement, no Non-Goal designed in, chosen and rejected approach recorded, constitution ok, user approves · **3** no CRITICAL/HIGH scope findings, requirements ↔ tasks traced both ways, Public Surface declared, user picks execution · **4** tasks done, build and full suite pass, no TODO without a ticket · **5** see [verification](04-verification.md) · **6** no unresolved high-severity finding · **7** no critical/high open, no secrets in the diff · **8** CI green, user merges · **9** user go-ahead, smoke test · **10** signals within threshold or a rollback/fix ticket · **11** lessons linked, `CLAUDE.md` ≤ 60 lines, `Status: done`. | `[instructed]` orchestrator §1–11 |
| ORC-FR-011 | Artifacts go to `.sdlc/<feature>/` (committed); scratch to `.sdlc/.work/` (git-ignored). | `[instructed]`; `.gitignore` entry added by setup `[enforced]` test_scaffold › test_gitignore_merges_and_only_removes_its_own_lines |
| ORC-FR-012 | Bundled skills that hand off to the next skill on their own return to the orchestrator instead, so the gate runs; "your human partner" in vendored skills means the user. | `[instructed]` orchestrator "Rules" |
| ORC-FR-013 | `state.md` follows the template: Status, Track (with size-up signal), Risk, Top model, Commands, Started, Base (the commit the feature started from), Current; sections Stages, Verify rounds, Gate log, Deviations, Open questions. | `[instructed]` orchestrator template; parsed by the freshness hook and doctor `[enforced]` test_doctor › test_feature_state |
| ORC-FR-014 | Risk is recorded apart from size (`high` for auth, payments, secrets, PII, schema migrations, public API) and, with the track, sets each dispatch's model tier: cheap `haiku`, standard `sonnet`, top `opus`. `fable` only when the user chooses it (`Top model: fable`); escalation stops at the top tier. | `[instructed]` orchestrator §0, subagent-driven-development Model Selection |
| ORC-FR-015 | While a feature is active, a subagent dispatch is denied, with the reason Claude sees, when it names no model, names `fable` without `Top model: fable` in every active `state.md`, or runs code-reviewer, feature-reviewer, ui-reviewer, verifier or qa-tester below `opus` on `Risk: high`. Forks are exempt; no active feature or a hook error never blocks. | `[enforced]` test_model_router › test_dispatch_naming_a_tier_goes_ahead, test_fable_without_the_users_opt_in_is_denied, test_qa_tester_below_opus_is_denied_on_high_risk, test_dispatch_without_a_model_is_denied, test_fable_with_the_users_opt_in_goes_ahead, test_high_risk_floor_applies_to_reviewers_only, test_forks_are_exempt, test_no_active_feature_is_silent |
| ORC-FR-016 | A new feature is named `<yyyy-mm-dd>-<slug>`, or `<yyyy-mm-dd>-<ticket>-<slug>` when the request names a ticket (a GitHub issue is `gh-<n>`); an existing `.sdlc/<name>/` that isn't being resumed gets `-2`, `-3`, …; the branch and `knowledge/features/<name>.md` use the same name. | `[instructed]` orchestrator §0, writing-specs |

## Edge cases

- Several active features → ask which (doctor warns: test_doctor › test_feature_state).
- A paused feature (`Status:` other than `active`) is not picked up by `/sdlc:start`.
- The S track has no spec, design or plan file.

## Non-goals

- Running stages in parallel; managing several features in one turn.
- Choosing the track without the user being able to override.
- Mirroring stages or plan tasks into Claude Code's native task list. `state.md` is the tracker; the task tools are off by default on current models (Claude Code ≥ 2.1.268) and can't be read by hooks or doctor.

## Known gaps

- Apart from the model router (ORC-FR-015), every orchestration rule is `[instructed]`: nothing mechanically prevents skipping a stage or a hard stop. The user's approval at hard stops is the control.