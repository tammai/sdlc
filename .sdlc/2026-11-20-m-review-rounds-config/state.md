# 2026-11-20-m-review-rounds-config
Status: done
Process: 3
Change: .sdlc/2026-11-20-m-review-rounds-config/change.md   (this feature's record for people)
Track: M   (sized up because: —; footprint: 9 files)
Risk: low
Top model: opus   (fable only if the user chose it)
Commands: test: (none recorded)
Started: 2026-11-20
Base: 9c4ec97
Owner: 3235400+tammai@users.noreply.github.com
Tool: claude-code
Verified: 9c4ec97 tree 832e37d7982ede7dcd6577d76fd308cdc3accf5d
Current: Stage 4 – Ship

## Stages
- [x] 1 Define   — the change file, the plan sections below
- [x] 2 Build
- [x] 3 Review   — the change file's ## Review
- [ ] 4 Ship     — PR: (Learn: knowledge, recurring-defects.md)

## How the build runs
inline: this session builds it, one part

## Handoff
- hook flow: main() loads store, capped(), grants on reply; apply the cap before capped() so a raise isn't also a grant: hooks/review_rounds.py:79
- stuck_turn.py:36 calls review_rounds.capped(root, review_rounds.load(root)): keep that signature
- scaffold.py puts hooks/ on sys.path (scripts/scaffold.py:32), so it imports review_rounds.configured

## Tasks
1. **Configurable cap in the hook** — AC-002 AC-003 AC-004
   - Files: `hooks/review_rounds.py`, `tests/test_review_rounds.py`
2. **review-rounds subcommand** — AC-001
   - Files: `scripts/scaffold.py`, `tests/test_scaffold.py`
3. **Setup step and command argument** — AC-005
   - Files: `skills/setting-up-projects/SKILL.md`, `commands/setup.md`
4. **Docs that restate the cap** — AC-002
   - Files: `skills/orchestrator/references/flow.md`, `docs/specs/03-scope-and-review.md`, `docs/wiki/Review.md`, `docs/wiki/Hooks.md`, `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`

## Public Surface
- command `scaffold.py review-rounds [n]` — AC-001
- config `review_rounds` — AC-002

## Test lock
- `tests/test_review_rounds.py` sha256:20c11eacf7afe32d433ef84052c72276e771ade17f11bb09773c7661e1caf8b5
- `tests/test_scaffold.py` sha256:eeaaad1dc4498671ae93a9f7c311edde59b06fdec7545ee15e020ad428696ebd

## Gate log
- 2026-11-20 Stage 1: pass — plan not stopped for approval: low-risk M; guard design chosen by the user
- 2026-11-20 full suite: 679 tests OK (5 skipped), Python 3.10
- 2026-11-20 Stage 2: pass
- 2026-11-20 review: ran code (Public Surface not none), not asked: low risk
- 2026-11-20 Stage 2: pass
- 2026-11-20 Stage 2: pass
- 2026-11-20 Stage 2: pass
- 2026-11-20 Stage 2: pass
- 2026-11-20 Stage 2: pass
- 2026-11-20 Stage 2: pass
- 2026-11-20 Stage 3: pass
- 2026-11-20 full suite: 698 tests OK (5 skipped), Python 3.10, after round 6 fixes

## Deviations
- 2026-11-20 setup What: the repo isn't set up for sdlc (the plugin's own repo). Why: as earlier features here. Effect: the full suite runs by hand on Python 3.10.
- 2026-11-20 docs/wiki/Configuration.md docs/wiki/Commands.md hosts/skills/setup/SKILL.md What: config key row, setup argument, regenerated host copy. Why: stale-docs audit and hosts.py check. Effect: docs only.
- 2026-11-20 hooks/review_rounds.py configured, cap_in_force, capped; scripts/scaffold.py cmd_review_rounds What: module helpers behind the command and config key; capped gains an optional cap argument. Why: AC-001 to AC-004; scaffold imports configured for one range check. Effect: stuck_turn.py's two-argument capped call is unchanged; no new public surface beyond the planned command and key.
- 2026-11-20 test-change tests/test_review_rounds.py What: AC-002/003/004 tests now raise the cap with the user's /sdlc:setup review-rounds prompt (a plain reply no longer raises it), assert the exact deny phrase, and a new test covers a value committed at Base. Why: review r1 findings 1, 2, 4, 5, 6 changed the raise rule. Effect: same ACs, stricter tests.
- 2026-11-20 hooks/review_rounds.py cap_in, cap_for What: replace cap_in_force and review-cap.json; the cap is bounded by config at Base unless the user's command raised it; capped takes the prompt, not a cap. Why: review r1 high findings. Effect: no new file; stuck_turn's call unchanged. docs/adr/0029-configurable-review-round-cap.md docs/adr/0023-two-review-rounds.md docs/adr/README.md skills/orchestrator/references/s-track.md skills/orchestrator/references/review-brief.md: ADR and stale wording from review r1.
- 2026-11-20 test-change tests/test_review_rounds.py What: the cap is set by the number in the user's /sdlc:setup review-rounds <n> prompt; tests for grants kept across a raise, an agent lowering, a committed value below the git top level. Why: review r2 R1-R5. Effect: same ACs.
- 2026-11-20 hooks/review_rounds.py user_set, cap_for, capped What: the window design is gone; the prompt's number is kept per feature as set; git show uses ./ paths; grants carried as min(granted, old+granted-cap); no cap work before round 2. Why: review r2 R1-R7 (the user chose one more fix round). Effect: SET also accepts /setup and $sdlc-setup (R8).
- 2026-11-20 test-change tests/test_review_rounds.py What: tests for the hook writing the typed cap to config, a later lower value lowering it, grants kept across cap changes, an over-long number. Why: review r3 T1, T2, T5, T7. Effect: same ACs.
- 2026-11-20 hooks/review_rounds.py record_in_config, read_config, cap_for; hooks/trust_anchor.py; tests/test_trust_anchor.py What: the hook writes the typed cap into config; cap = min(now, max(Base, typed)); grants stored as allowed (old granted converts); git timeout gives the stricter cap; trust_anchor reads Base files with ./ paths, with a test below the git top level. Why: review r3 T1, T2, T4, T5, T7, T8 (the user chose one more fix round). Effect: T3 and T6 are tickets, named in spec 03 Known gaps.
- 2026-11-20 test-change tests/test_review_rounds.py What: ceiling tests (no climb back, typed forms, no-feature write, Base unreadable, unwritable config); bad-value test asserts the ceiling. Why: review r4 U1, U3, U4, U6. Effect: same ACs.
- 2026-11-20 hooks/review_rounds.py at_base, cap_for, record_in_config; scripts/scaffold.py cmd_review_rounds What: a per-feature ceiling replaces min/max of now, Base and typed; config written via temp file and os.replace, errors caught; deny reason names the command exception; scaffold accepts ASCII digits only. Why: review r4 U1-U4, U7 (the user chose one more fix round). Effect: U5 docs fixed.
- 2026-11-20 test-change tests/test_review_rounds.py What: tests for a lower value before round 2, a float in config, a mid-edit read; the chmod test skips as root; the bad-value test reads a readable 2 first. Why: review r5 V1, V4, V5, V7. Effect: same ACs.
- 2026-11-20 hooks/review_rounds.py config_cap, cap_for, record_in_config; commands/setup.md What: the ceiling is tracked on every call; an unreadable config holds 2 for that call only; the typed cap is written with scaffold.write_json (link, mode, Windows retry, temp under .sdlc/.work); equality via configured(); setup text says what to do while held. Why: review r5 V1-V6 (the user chose one more fix round). Effect: the hook imports scaffold only on the typed command.
- 2026-11-20 hooks/review_rounds.py say, record_in_config, cap_for, capped; commands/setup.md; tests/test_review_rounds.py What: round 6's mediums and lows fixed test first without another round: no ceiling stored from an unreadable first read, a typed cap reaches paused features, an out-of-range typed number is named and not granted, an unsaved typed cap is reported, setup says to commit with no active feature and words the held case by the next denied call. Why: review r6 (PASS) W1-W6. Effect: W7 stays a known gap.
- 2026-11-20 test-change tests/test_review_rounds.py What: four tests for round 6's W1, W3, W5, W6 (new tests; the AC tests are unchanged). Why: review r6. Effect: same ACs.

## Open questions
-
