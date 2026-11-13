# 2026-11-13-l-workbench
Status: active
Process: 3
Change: .sdlc/2026-11-13-l-workbench/change.md   (this feature's record for people)
Track: L   (sized up because: several distinct parts across setup, hooks, verify, ship and CI; footprint: 30 files)
Risk: high   (untrusted input: a committed workbench.yaml names folders and clone URLs that reach git and file paths)
Top model: opus   (fable only if the user chose it)
Commands: test: (none recorded)
Started: 2026-11-13
Base: 58acb2e
Owner: 3235400+tammai@users.noreply.github.com
Tool: claude-code
Verified: 9fb2d64 tree a0defd24108b1a648a4c85f2e253706026a382f0
Slice: B8   Slice base: 9388559   Slice gates: none
Current: Stage 2 – Build

## Stages
- [x] 1 Define   — the change file, the plan sections below
- [x] 2 Build
- [ ] 3 Review   — the change file's ## Review
- [ ] 4 Ship     — PR: (Learn: knowledge, recurring-defects.md)

## How the build runs
parts in fresh sessions, because seven parts across the core won't fit one context (backlog.md)

## Handoff
- Approved design and user answers: change.md Why/Decisions; product-rebuild's repos.yaml is kept apart (detect by config key workbench: true)
- Two scope parsers today: scripts/scaffold.py:555 scopes() and hooks/verify_freshness.py:141 load_scopes(); root commands.test is dropped by the first, honoured by the second
- Nested-repo routing: hooks/sdlc_layout.py:43 target_repo returns None whenever the session root has .sdlc/ (line 51); _sdlc_repo_inside at :72; tests in tests/test_session_above_repo.py
- hooks/reporesolve.py already scans nested repos for commit review (SCAN_MAX_DEPTH 3)
- This repo has no .sdlc/config.json: verify.py runs only AC tests; run the full suite by hand: python3.10 -m unittest discover -s tests -t tests

## Tasks
1. **B1 One scope parser; root test beside packages; brownfield doc** — AC-001 AC-002 AC-003
   - Files: `hooks/sdlc_scopes.py`, `scripts/scaffold.py`, `hooks/verify_freshness.py`, `skills/setting-up-projects/references/brownfield.md`, `tests/test_workbench.py`
2. **B2 Workbench manifest, detection, add/remove, doctor** — AC-004 AC-005 AC-006
   - Files: `hooks/sdlc_scopes.py`, `scripts/scaffold.py`, `scripts/doctor.py`, `tests/test_workbench.py`
3. **B3 Routing, read-only guard, no features in app repos** — AC-007 AC-008 AC-009
   - Files: `hooks/sdlc_layout.py`, `hooks/role_guard.py`, `hooks/pretooluse.py`, `scripts/state.py`, `tests/test_workbench.py`
4. **B4 One feature across repos** — AC-010 AC-011 AC-012
   - Files: `scripts/state.py`, `scripts/verify.py`, `hooks/verify_freshness.py`, `scripts/diff_stats.py`, `tests/test_workbench.py`
5. **B5 Ship across repos** — AC-013 AC-014
   - Files: `scripts/ship.py`, `tests/test_workbench.py`
6. **B6 App CI and contract check** — AC-015
   - Files: `scripts/scaffold.py`, `tests/test_workbench.py`
7. **B7 Setup reference, ADR, wiki, changelog** — AC-016
   - Files: `skills/setting-up-projects/references/workbench.md`, `skills/setting-up-projects/SKILL.md`, `skills/setting-up-projects/references/greenfield.md`, `docs/adr/0025-workbench-for-multi-app-projects.md`, `docs/adr/README.md`, `docs/wiki/Project-setup.md`, `docs/wiki/Configuration.md`, `docs/wiki/Where-things-live.md`, `CHANGELOG.md`, `tests/test_workbench.py`

## Public Surface
- command `scaffold.py workbench add|remove` — AC-005
- config `workbench` — AC-004
- config `workbench.yaml` — AC-004
- command `ship.py --status` — AC-014

## Gate log
- 2026-11-13 Stage 1: pass — plan self-approved (L): (1) each design goal maps to AC-001–016 and each AC to the design; (2) no open questions; (3) every decision is the user's answer or a call listed in the approved design; (4) no unasked proposal, nothing irreversible
- 2026-11-13 scope added by the user during B1: preferred stacks as part B8 (AC-017); Go stack chosen: Gin + oapi-codegen + pgx/v5 + sqlc + golang-migrate
- 2026-11-13 tests: per part, only the affected test modules on Python 3.10; the full suite once before Review (user's choice)
- 2026-11-13 handoff B2: hooks/sdlc_scopes.py has is_workbench/manifest/workbench_scopes (WORKBENCH_SCOPE '(workbench)'); B3 routes guards via them; scaffold.scopes() doesn't yet return workbench scopes (B4 wires verify/freshness)
- 2026-11-13 handoff B3: sdlc_layout.target_repo routes from a workbench root; role_guard.read_only_problem (via pretooluse) guards write:false repos; sdlc_scopes.workbench_of marks an app repo and state.py new refuses there. B4 next: per-repo branch/base in state.py, verify per touched repo, freshness per app scope (scaffold.scopes still doesn't return workbench scopes)
- 2026-11-13 handoff B4: state.py repo <f> <name> branches a writable repo (workbench branch name, from its default branch) or records a read-only commit under ## Repos (sdlc_scopes.feature_repos parses it); verify.repo_failures runs each branched repo's plan; freshness scopes per repo (scope_dir). Gap for B5: verify.py's recorded tree and HEAD are the workbench's only (app repos are gitignored), so ship must check and commit each branched repo itself
- 2026-11-13 handoff B5: ship.py stages each branched repo (repos in merge order, commit-msg-<repo>.txt, pr-<repo>.md); state.py pr records PRs under ## PRs; ship.py --status warns on out-of-order merges (SDLC_GH for tests). verify records each branched repo's tree and drift counts app-repo files. B6 next: builtin:ci for a consuming app checks out the workbench (scaffold.py generate_ci)
- 2026-11-13 handoff B6: scaffold.workbench_checkout adds the workbench branch/checkout/contract-copy steps to an app's builtin:ci when the parent workbench lists it as a consumer. B7 next: references/workbench.md, setup routing, ADR 0025, wiki, CHANGELOG, stale-docs audit (describe state.py repo/pr, ship.py --status, WORKBENCH_TOKEN, the app back-reference)
- 2026-11-13 handoff B7: references/workbench.md, ADR 0025, wiki, CHANGELOG and the stale-docs audit are done. B8 next: references/stacks.md (workbench.md's stack step already points to it), greenfield.md proposes from it
- 2026-11-13 handoff B8: every part done; next is Feature close: the full suite once on Python 3.10, then advance 3 and Review over the whole branch (diff_stats --base 58acb2e with the state file and every plan-B*.md)
- 2026-11-13 review: ran code, security (L, Public Surface, Risk high), self-chosen: L
- 2026-11-13 Stage 2: pass
- 2026-11-13 decision: PR bodies link the other repos and their feature branches, not their PR URLs (the PRs don't exist when ship.py writes the bodies); AC-013's 'linking the others' read that way, documented in workbench.md (review round 1 M8)
- 2026-11-13 review round 1 fixes: 11 tests (ReviewRound1* plus the AC-002 and AC-015 tests) seen failing on 9fb2d64 in a worktree, then passing
- 2026-11-13 review round 2: FAIL (code R2-H1 R2-H2, security S9 S10); user chose one more fix round (Review cap)
- 2026-11-13 scope changed by the user in Review: keep the monorepo as a full option; greenfield with two or more apps asks monorepo or workbench, recommending by team (user's pick)
- 2026-11-13 review round 3: both reviewers PASS; S16, S17, R3-M2 raised to high (writes into a read-only repo get through, a must-never-break line); user chose fix all, then one more security check (Review cap)

## Deviations
- 2026-11-13 setup What: went on with setup none (no .sdlc/config.json). Why: the plugin's own repo has always run sdlc without setup (e.g. 2026-11-08-l-spec-backed-mode). Effect: verify.py runs the AC tests; the full suite is run by hand with python3.10 -m unittest discover -s tests -t tests.
- 2026-11-13 tests/test_scaffold.py What: an unnamed package's contract entry is keyed by its path, not '?'. Why: AC-001 names a package without a name after its path in the one shared parser. Effect: test_contract_monorepo_packages expects the 'nowhere' key.
- 2026-11-13 hooks/sdlc_scopes.py exports norm, packages, root_commands, scopes What: the shared parser's functions, used by scaffold.py and verify_freshness.py. Why: AC-001's one parser for scripts and hooks; packages raises ValueError on malformed config instead of crashing later. Effect: internal API only, no user-facing surface.
- 2026-11-13 docs/wiki/Configuration.md What: the packages row says root commands beside packages run in verify and CI. Why: AC-002 changed that behaviour. Effect: docs only.
- 2026-11-13 B8 What: new part B8, preferred stacks (skills/setting-up-projects/references/stacks.md, greenfield.md, workbench.md, tests/test_workbench.py), AC-017. Why: the user asked for it mid-build and chose to add it here. Effect: one more part after B7.
- 2026-11-13 skills/setting-up-projects/references/greenfield.md What: the root commands.test line says it runs in verify and CI. Why: AC-002 changed that behaviour. Effect: docs only.
- 2026-11-13 workbench.json What: the manifest is workbench.json, not workbench.yaml. Why: the plugin is stdlib-only Python with no YAML parser, and a hand-rolled YAML subset would be a parser over untrusted input. Effect: same fields and location; change.md and backlog.md now say workbench.json.
- 2026-11-13 B2 internal functions What: sdlc_scopes.is_workbench, check_name, manifest, workbench_scopes; scaffold.cmd_workbench (behind the planned scaffold.py workbench command, which also gained 'list'); doctor.check_workbench. Why: AC-004–006; is_workbench needs the manifest too (need_manifest=False only for the command writing the first entry) so a config key alone never switches modes. Effect: internal API; the user-facing surface is the planned workbench command and config key.
- 2026-11-13 B3 docs/specs/06-guardrails-and-conventions.md, docs/specs/03-scope-and-review.md, docs/wiki/Hooks.md What: GRD-FR-016 and SCO-FR-026 route from a workbench too; new GRD-FR-033 for the read-only guard; the wiki's hookify and role-guard rows say both. Why: they restated the routing rule B3 changed (AC-007, AC-008). Effect: docs only.
- 2026-11-13 B3 hooks/sdlc_scopes.py workbench_of; role_guard.written, read_only_problem, hits/shell_write folders mode What: internal helpers behind AC-008 and AC-009; sdlc_scopes.py is the one file B3 adds to its plan. Why: state.py and the guard read an app repo's back-reference and the manifest through the shared parser. Effect: internal API only.
- 2026-11-13 B3 hooks/role_guard.py bundle_problem What: its tool dispatch moved into written(), which read_only_problem shares; behaviour unchanged. Why: one write check for recorded tests and read-only repos (AC-008). Effect: internal only; test_recorded_tests passes unchanged.
- 2026-11-13 B4 hooks/sdlc_scopes.py repo_line, feature_repos, REPOS_HEADING What: the state file's new ## Repos section (<name>: branch <b> base <sha> | <name>: read <sha>), parsed once for state.py, verify.py, the freshness hook and diff_stats.py. Why: AC-010–012 all read which repos a feature touched. Effect: an optional state section; no Process bump (no existing field changes meaning).
- 2026-11-13 B4 command state.py repo What: the per-repo branch step is a state.py subcommand, repo FEATURE NAME, which also records a read-only repo's commit. Why: AC-010 and AC-012 each need a call that records the repo; one command covers both. Effect: a new state.py subcommand (CTL-FR-009).
- 2026-11-13 B4 docs/specs/04-verification.md, docs/specs/03-scope-and-review.md, docs/specs/12-control-contract.md What: VER-FR-055, SCO-FR-031, CTL-FR-009. Why: the specs list each enforced behaviour with its test. Effect: docs only.
- 2026-11-13 B4 verify.repo_failures, verify_freshness.feature_state, initial_workbench_state, scope_dir, diff_stats.moved_read_only, state.git_run, default_branch, record_repo What: internal helpers behind AC-010–012. Why: per-repo verify, freshness and moved-repo facts. Effect: internal only.
- 2026-11-13 B4 hooks/verify_freshness.py feature_base What: reads the state through the new feature_state(); same result. Why: initial_workbench_state reads ## Repos from the same text. Effect: internal only.
- 2026-11-13 B5 ship.py commits in each repo What: ship.py stages each branched repo and writes its message and PR body; the caller runs each git -C <repo> commit, as for the workbench. Why: AC-013 says ship commits in each repo, but the commit stays in the caller's command so the commit review and the user's permission rules see every one (ship.py's own rule). Effect: AC-013's test runs the commit from ship.py's output.
- 2026-11-13 B5 command state.py pr What: records a repo's PR URL under ## PRs, which ship.py --status reads. Why: AC-014's 'PRs recorded in the state file' needs a writer; gh pr create runs in the caller's command. Effect: a new state.py subcommand.
- 2026-11-13 B5 hooks/sdlc_scopes.py PRS_HEADING, pr_name, feature_prs, merge_order, must_follow; scripts/verify.py branched_repos, repo_changes, repo_trees; ship.ship_repos, pr_state, status What: internal helpers behind AC-013–014; verify.py and sdlc_scopes.py weren't in B5's file list. Why: closes B4's gap (the verified run covers each branched repo's tree; drift counts app-repo files) and gives ship one merge order. Effect: internal; env SDLC_GH (tests only) points --status at a gh stand-in.
- 2026-11-13 B5 docs/specs/02-orchestration.md What: ORC-FR-044. Why: the spec lists each enforced behaviour with its test. Effect: docs only.
- 2026-11-13 B6 scaffold.workbench_checkout, WORKBENCH_REPO What: the app CI's workbench steps, rendered when the app's back-reference is a plain repo name and the workbench above lists it as a consumer; read from the parent workbench.json, so the contract role is recorded once. Why: AC-015. Effect: internal; an app CI rendered outside its workbench gets no checkout step.
- 2026-11-13 B6 docs/specs/01-setup-upgrade-eject.md What: SET-FR-051. Why: the spec lists each enforced behaviour with its test. Effect: docs only.
- 2026-11-13 B7 CONTRIBUTING.md, README.md, docs/prd.md, docs/specs/01-setup-upgrade-eject.md What: the stale-docs audit: layout tree (sdlc_scopes.py, workbench.md, ship.py), README and PRD shape lines, spec 01 source and decisions lines, SET-FR-017 narrowed, SET-FR-052. Why: CLAUDE.md's stale-docs audit after a feature. Effect: docs only.
- 2026-11-13 B8 CONTRIBUTING.md, CHANGELOG.md, docs/wiki/Project-setup.md, docs/specs/01-setup-upgrade-eject.md What: stacks.md in the layout tree, a changelog line, the wiki's greenfield line, SET-FR-053. Why: the stale-docs audit. Effect: docs only.
- 2026-11-13 skills/orchestrator/references/flow.md skills/orchestrator/references/review-brief.md What: Build, Review and Ship steps for a workbench (state.py repo before the first change in a repo, per-repo diffs, per-repo commit/push/PR and state.py pr). Why: review round 1 H1, the orchestrator never reached the per-repo machinery. Effect: workbench features follow the per-repo flow; single-repo flow unchanged.
- 2026-11-13 hooks/role_guard.py unbranched_problem, hooks/pretooluse.py What: a write into a writable workbench repo that no active feature has branched is denied, naming state.py repo. Why: review round 1 H1 backstop, so a first edit can't land on the repo's checked-out default branch. Effect: setup and no-active-feature sessions stay open.
- 2026-11-13 scripts/scaffold.py workbench clone, _clone_into, _ignore, _workbench_clone What: scaffold.py workbench clone [<name>] clones listed repos that are missing, from the manifest URLs; doctor's hint names it with no URL. Why: review round 1 H2/S4, a fresh clone of the workbench couldn't bring its repos back and doctor put an untrusted URL in a shell line. Effect: new subcommand action.
- 2026-11-13 hooks/sdlc_scopes.py check_url, repo_dir, ignored_name, branched_repos, read_only_names, workbench_root, check_pr_url, RESERVED What: shared checks for clone URLs, repo folders (links out refused, reserved and case-folded names), gitignore spellings, writable branch lines, the lenient read-only list, the workbench root above a cwd and PR URLs. Why: review round 1 S2-S4, S6, S8, H6, M4, M6, M9; one check on every path. Effect: stricter manifest validation.
- 2026-11-13 scripts/scaffold.py verify_plan What: only a root commands.test beside packages runs; root install/lint/typecheck/build keep not running. Why: review round 1 H3, the must-never-break line allows only the root test; AC-002's test assertion changed to match. Effect: existing monorepos behave as before apart from the root test.
- 2026-11-13 scripts/ship.py check_repos What: every workbench refusal (manifest, non-writable branch line, wrong branch, listed folder not gitignored) happens before the state moves. Why: review round 1 M1, M5, S2. Effect: ship_repos takes the checked list.
- 2026-11-13 Public Surface What: the surface as built is workbench.json (not workbench.yaml), scaffold.py workbench list|add|remove|clone, state.py repo and pr, ship.py --status, the WORKBENCH_TOKEN secret and the SDLC_GH test seam. Why: review round 1 fix-in-passing; state.py has no command to rewrite ## Public Surface and the state file is never hand-edited. Effect: this line is the current list.
- 2026-11-13 hooks/role_guard.py KEYWORDS, substitutions, segments subshell markers What: the shell guard reads commands behind ( ) { } ! and shell keywords, inside $( ) and backticks, with a subshell's cd ending with it; >& file counts as a redirect; cmd's cd /d is followed. Why: review round 2 R2-H1/S9, the class (where a command starts and which folder it runs in), not one more pattern. Effect: guarded writes in grouped or nested forms are denied; nothing else changes.
- 2026-11-13 hooks/role_guard.py read_only_problem fails closed What: a workbench.json that isn't JSON with a repos list guards every non-reserved, non-dot folder of the workbench until it is fixed; sdlc_scopes.read_only_names skips reserved names. Why: review round 2 S13, R2-L2. Effect: writes into app folders are denied while the manifest is broken.
- 2026-11-13 scripts/ship.py pr_state(url, cwd) and check_repos What: gh runs in the repo's own folder (a bare PR number names that repo's PR); any untracked git repo inside the workbench that isn't gitignored is refused before the state moves; suggested commands are shell-quoted. Why: review round 2 S10, R2-M2, S11. Effect: internal.
- 2026-11-13 hooks/sdlc_scopes.py check_branch, repo_dir What: ## Repos branch names are limited to letters, digits, . _ - / (state.py repo refuses another workbench branch name); repo_dir refuses any link, a sibling repo too. Why: review round 2 S11, S12. Effect: stricter state parsing; internal.
- 2026-11-13 scripts/diff_stats.py scan, feature_state, branched_repos What: collect also scans each app repo the feature branched against its recorded base, paths prefixed with the repo folder and references counted inside it. Why: review round 2 R2-M1, the review choice and Public Surface check never saw app code. Effect: diff_stats output includes app-repo files.
- 2026-11-13 scripts/scaffold.py workbench add/clone, scripts/state.py record_repo, scripts/verify.py repo_failures, skills/orchestrator/references/flow.md What: add gitignores before it clones; clone keeps going past a failed repo and reports it (exit 1); a default branch with a / is matched whole; a not-run prefix is no longer doubled; flow.md records a read-only repo before its first read. Why: review round 2 R2-M2, R2-L5, R2-L1, fix in passing, R2-H2. Effect: as listed.
- 2026-11-13 change.md Why/Decisions/Design/AC-016, skills/setting-up-projects/references/greenfield.md monorepo.md workbench.md SKILL.md, docs/adr/0005 0025 README, docs/specs/01 (SET-FR-017/052, new SET-FR-054), docs/wiki/Project-setup.md, CHANGELOG.md, README.md, CONTRIBUTING.md What: the workbench is an option beside the monorepo, not its replacement; setup asks which layout and recommends by team; ADR 0025 extends ADR 0005. Why: the user's request in Review. Effect: docs and setup routing only; no code changed.
- 2026-11-13 hooks/role_guard.py lex, _lex, TooDeep, shell_write dialect What: segments and substitutions became one lexer per shell (sh, PowerShell, cmd): comments, escapes, line continuations and here-doc bodies are never commands; substitutions run inline as subshells; case patterns close nothing; PowerShell's backtick is its escape and its ( ) stay in the words; cmd escapes with ^; nesting past 24 is denied. Why: review round 3 S16, R3-M2 (raised to high), R3-M1, S18, R3-L1, the class being each shell's own syntax. Effect: fewer false denials (a heredoc commit body) and no hidden writes in these forms.
- 2026-11-13 hooks/sdlc_scopes.py guarded_workbench, workbench_root(guarded) What: the write guards also act where workbench.json sits beside a .sdlc/config.json that can't be read as an object. Why: review round 3 S17 (raised to high). Effect: a broken config never turns the guards off.
- 2026-11-13 scripts/scaffold.py workbench add, _ignore; scripts/ship.py status What: add refuses an existing non-repo folder before it writes the ignore line and rolls the line back when the clone is refused (a crash still leaves it); --status reads a full PR URL without the repo's clone. Why: review round 3 R3-L3, R3-L4. Effect: as listed.

## Open questions
-
