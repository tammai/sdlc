# Changelog

Versions follow the `version` in `.claude-plugin/plugin.json`. Repos record the version they were set up or upgraded with; `/sdlc:upgrade` brings them forward.

## Unreleased

### Changed
- `/sdlc:start` with a GitHub issue, Linear or Jira link now reads the ticket before sizing the work (`gh issue view` or the tracker's MCP server) and uses it as the request. If the ticket can't be read, it asks for the text instead of guessing from the URL. A ticket link pasted on its own, without `/sdlc:start`, now starts the orchestrator too.
- The plugin and marketplace descriptions now match the README: S/M/L sizing, up to 11 gated stages, a fresh verifier, design-system-aware UI review and any stack or monorepo. New keywords: `orchestrator`, `monorepo`, `claude-code-plugin`.

## 1.7.1 — 2026-10-23

No migration. Only the role guard changed: the suite covers it, and a headless smoke run checked that the plugin loads as 1.7.1 and that the guard still holds a live verifier to its report. 1.7.0's full smoke test covers the rest.

### Fixed
- The role guard no longer lets the verifier or qa-tester write a report through a path containing `~` or `:`. On Windows, a short name like `WORK~1` could reach `.sdlc/.work/` by another spelling.

## 1.7.0 — 2026-10-23

Migration: `1.7.0-artifact-layout` (moves existing repos; `/sdlc:upgrade` previews it first).

Smoke test passed 2026-10-23 in headless Sonnet sessions on Windows (parts A–E, G, H). Brownfield setup first went past its command approval, which is fixed below and passed on rerun. Known issue: after `/sdlc:eject`, the trust-anchor hook recreates an untracked `.sdlc/.work/` at the end of that session; delete it.

### Changed
- sdlc documents now live with your project docs. The constitution, the design system and each feature's brainstorm, spec, design, plan and reports go to `docs/sdlc/` (features in `docs/sdlc/intents/<date>-<ticket>-<slug>/`). `.sdlc/` keeps only what the plugin runs on: config, lock, baseline, CI and lint snippets, scratch, and one state file per feature in `.sdlc/state/`. If your repo publishes `docs/` as a site (Docusaurus, MkDocs, VitePress, Sphinx, Starlight), setup and upgrade ask where the documents should go instead, `.sdlc` included, and record it as `docs_dir`.
- `/sdlc:upgrade` moves an existing repo with `git mv`, so history follows the files. It shows the moves first and warns about features still in progress, whose open branches will see the renames. Until you upgrade, everything keeps working on the old layout, and `/sdlc:status` and `/sdlc:doctor` remind you.

### Fixed
- Brownfield setup now stops and waits after proposing the commands, and after each audit batch, before writing anything. It used to record the commands and area rules first and report afterwards. A skipped audit writes no area rules.

### Added
- Setting up a new repo with two or more apps (say web, an API and mobile) now builds one monorepo: `apps/` for the apps, `packages/` for shared code, `docs/` for BA, QA and design files, and `infras/` if you want it. Setup asks who will work in the repo. A large team with separate roles also gets CODEOWNERS, a CI workflow per app that runs only when that app or shared code changes, and a release runbook with per-app tags. A solo developer or small team gets one CI workflow.
- When one app serves an API another uses, the contract lives in `packages/api-contract/` with a folder per version (`v1/`, `v2/`). Merging a version to `main` publishes it. If you agree, CI fails a pull request that breaks or removes a published version (oasdiff, OpenAPI only). Additions are fine, and a breaking change goes in a new version folder. Each app generates its own client from the version it uses.
- Spec templates have a **References** line for linking the BA specs, test cases and designs a feature builds on.

## 1.6.1 — 2026-10-23

No migration. `/sdlc:upgrade` regenerates the CI workflow with the Node 24 action pins.

The release smoke test was skipped at the maintainer's request. The changes were checked by the suite (207 tests) and `claude plugin validate .`.

### Changed
- An S-track fix goes to one implementer subagent on the cheap tier (standard on high risk) instead of the session, so it no longer runs at your session model's price.
- When a feature starts on the S track, or M with low risk, in an Opus or Fable session, the orchestrator suggests `/model sonnet` once. It never blocks; reviewers and the verifier keep their own models.
- The execution method you pick at the end of Stage 3 has one name everywhere: **native** (you implement in the session) or **subagent-driven**. The orchestrator, playbook, README and diagrams used to call native execution "inline".
- Stage 10 (Operate) is parked: no track runs it until there's a monitoring process to back it. Stage 9 (Deploy) runs on any track only when you ask, so the L track now ends at PR and CI, then Learn.
- The CI workflow setup generates pins actions that run on Node 24 (`checkout@v7`, `setup-node@v7`, `setup-go@v7`, `setup-java@v6`, `setup-dotnet@v6`, `setup-uv@v10`); the old pins drew GitHub's Node 20 deprecation warning. Existing repos get it from `/sdlc:upgrade`, which regenerates the workflow.

### Fixed
- Design-system additions no longer dead-end in review. A new component, variant or token approved in Stage 2 goes into `.sdlc/design-system.md` before Stage 4, and the ui-reviewer's "Proposed design-system changes" go to you in Stage 6: accept one and it's added to the system, decline it and the code uses an existing token. Before, an approved addition stayed out of the file and the reviewer flagged it as off-system.
- UI work that skips Stage 2 (S, or an M with an obvious approach) still maps each screen to the design system before Stage 4, in plan.md (M) or the Gate log (S), and asks you about anything the system lacks.
- The trust anchor also tells you when an active feature's `state.md` is deleted, or the feature is marked done before Stage 8.
- The test suite passes on Windows CI: tests read script output as UTF-8, and the missing-`python3` test is skipped where Windows finds `python3.exe` beside the interpreter.

## 1.6.0 — 2026-10-23

No migration. Repos set up earlier get a `/sdlc:doctor` warning that their commands were never run, until `/sdlc:upgrade` (or `scaffold.py run-commands`) runs them once.

The release smoke test was skipped at the maintainer's request. The changes were checked by the suite and by live headless sessions on 2026-10-23: an M feature through Stage 8 in a brownfield monorepo, and probes of the role guard, a failing full run, a trust-anchor notice and the model router (see the PRD). The new CI workflow first runs on this push.

### Added
- A trust-anchor hook tells you when what verification relies on changes during a feature: `Risk:`, `Track:` or `Top model:` changed, `baseline.md` gaining failures, the commands changing, `spec.md` changing after Stage 5 began, or leaving Stage 5 with code that changed since the last full test run. Claude stops once to explain; your next message accepts it. It makes these visible, it can't prevent them.
- When a feature has `contracts/`, the verifier checks each declared interface against the build.
- `/sdlc:status`, and the first feature started in a repo, list the repo's own hookify rules (anything in `.claude/hookify/` not named `sdlc-*`) with what they do. A cloned repo's rules reach Claude, so you see them before relying on them.
- `scaffold.py run-commands` runs the recorded commands and keeps each exit in the lock; setup uses it, so a command that can't even start no longer passes setup. `/sdlc:doctor` warns on a set-up repo whose commands were never run (repos set up earlier: run it once).
- A role-guard hook holds the plugin's own agents to their role, using the `agent_type` Claude Code now passes to hooks: reviewers can't edit files, the verifier writes only its report, the baseline and its red-green worktree, and the qa-tester can't read or search the code. They keep Bash, so this covers the file tools only.
- The model router logs every dispatch during a feature to `.sdlc/.work/dispatches.jsonl`, with the stage it happened in; the Stage 5 gate only counts a verdict from an `sdlc:verifier` dispatched in Stage 5.
- CI for the plugin itself: the test suite on Linux and Windows and `claude plugin validate`, on every push to main and every PR. Its first run happens at the next push; check it then.

### Fixed
- The freshness hook never saw a full test run that failed: Claude Code reports a non-zero exit as `PostToolUseFailure`, which the hook didn't listen to. In a brownfield repo with a baselined failure, running the package's test command could never make it fresh. A red run now counts, and each scope records whether its last run passed, failed or was piped (unknown).
- The freshness hook's own errors are no longer invisible: it leaves `.sdlc/.work/verify-freshness.error`, and `/sdlc:doctor` warns about it. Doctor's freshness line also reads the per-package state again (it always said fresh).
- `Verified:` now records the worktree tree as well as the commit, so Stage 8's check works when the verified work wasn't committed yet (found by the 1.5.0 smoke test).
- Gate-log, round and deviation lines go at the end of their section, in time order.

### Changed
- The `qa-tester` is no longer part of Stage 5: it runs only when you ask for a QA round, and its result isn't part of any gate. Its blindness to the code was instructions only, and in its one live run it found nothing the verifier missed, so it didn't earn its cost on every M and L round. Use your own independent agents for this kind of testing, or ask for an on-demand round.

## 1.5.0 — 2026-10-23

No migration: nothing a project owns changed. `/sdlc:upgrade` refreshes the generated files as usual.

Release smoke test passed on 2026-10-23 on Windows (headless sessions on sonnet, the checkout loaded with `--plugin-dir`, every must item and the monorepo should item, at e126e4a, about $4).

### Known issues
- When a feature's work is uncommitted at the Stage 5 gate, `Verified:` gets a commit plus "working tree", which Stage 8's check can't diff against.
- New gate-log lines go at the top of their section, so the log isn't in time order.

### Added
- Setup can add the sdlc marketplace and `enabledPlugins` to `.claude/settings.json` (`scaffold.py enable-plugin`, asked first) so teammates who trust the repo are offered the plugin. Keys you already set are left alone, and eject removes only what setup added. Repos set up earlier can run `scaffold.py enable-plugin` by hand.
- Stage 5 has a `qa-tester` agent on M and L tracks. It never sees the code, runs the feature against the spec's scenarios and edge cases the way a user would, and writes `qa-report.md`. A failed scenario fails the round. The model router holds it to `opus` on `Risk: high`.
- The verifier checks red-green: in a throwaway worktree with the feature's code put back to `Base:`, the feature's tests must fail. A test that still passes doesn't count as evidence.
- A later verify round reruns the qa-tester only when non-test code changed since its last PASS.
- `analyzing-consistency` maps each acceptance scenario to a named test in the plan and flags a scenario with none as HIGH.
- `/sdlc:prune` deletes the working files (plan, reports, review, checklists) of features marked done on the main branch 45+ days ago, after showing the list and asking. Spec, design, retro and state stay; git history keeps the rest.

### Changed
- One whole-branch review per feature: under the orchestrator, the execution skills skip their own final review and Stage 6 does it, with the plan's Review Focus and the Rulings made during Stage 4. A live run had spent two top-tier reviews on the same diff.
- Features are named `<yyyy-mm-dd>-<slug>`, with the ticket key after the date when the request names one (`2026-10-22-PROJ-123-month-filter`, `gh-42` for a GitHub issue). A name already in `.sdlc/` gets `-2`, so a new feature never writes into an old one's folder. The branch and knowledge entry use the same name.
- Verified code stays verified to the PR: `state.md` records the `Verified:` commit at the Stage 5 gate, the simplifier runs before the Stage 6 reviewers instead of after, a code fix in Stage 7 goes back to Stage 5 like one in Stage 6, and Stage 8 goes back to Stage 5 if non-test code changed since `Verified:`.
- `code-reviewer`, `comment-analyzer`, `pr-test-analyzer`, `silent-failure-hunter` and `type-design-analyzer` no longer have Edit or Write tools.
- The orchestrator adds each `state.md` line under its own heading; appending had put deviations under Open questions.

### Fixed
- `diff_stats.py` crashed on Windows when the diff had characters outside the code page (found by a live Stage 6 run); it now reads git output and writes its report as UTF-8.
- The verify-freshness hook switched itself off silently in a repo under a folder with non-ASCII characters in its name, because it decoded git's paths with the Windows code page. It now reads git output as UTF-8, and so does `/sdlc:doctor`.
- Stage 6 picked reviewers from `git diff --name-only`, which lists only unstaged changes, so on a branch whose tasks were committed only `code-reviewer` ran. `diff_stats.py` now uses the feature's `Base:` commit and lists every changed file, and `/sdlc:review-pr` and the reviewers work from that.
- The README no longer calls plan consistency machine-checked: `analyzing-consistency` is a skill.

## 1.4.0 — 2026-10-22

Release smoke test passed on 2026-10-22 on Windows (headless sessions, every must item, at 46a3365); the freshness fixes after it (f04c3d6, c60dff5) were checked by the suite and a real Stage 5 session.

### Known issues
- With the official `security-guidance` plugin also installed, Claude sees each security warning twice.
- The brownfield setup reference puts `packages` under `project` in `.sdlc/config.json`; `scaffold.py` reads it from the top level.
- Allowlist entries `Bash(<command>:*)` also allow extra arguments to the test command; exact matches would be tighter.
- The generated CI workflow defaults to Node 22 whatever version the repo pins.

### Added
- **UI follows the design system** ([spec 10](docs/specs/10-ui-design-system.md), [ADR 0004](docs/adr/0004-ui-follows-the-design-system.md)): setup records the project's design system in `.sdlc/design-system.md` (pointing at the existing library and tokens, or a mainstream library plus minimal tokens when there is none). A new `sdlc-ui.md` rule (scoped by the new `areas.ui`) and the `sdlc-ui-hardcoded-values` guardrail apply it while writing; the new `sdlc:ui-reviewer` checks every UI diff in Stage 6 for off-system values and components, AI-slop styling, missing states and accessibility, with screenshots only when you ask. `/sdlc:doctor` warns when a UI repo has no design system. Existing repos: `/sdlc:upgrade` adds the rule and guardrail, and migration `1.4.0-design-system` writes the design system.

### Security
- **Guardrails:** `sdlc-dangerous-rm` now catches `rm -rf /*`, `~/*`, `./*`, `../..`, `"$HOME"`, `${HOME}`, quoted targets and split or long flags. `sdlc-force-push-main` now catches pushes after `git -C`/`-c`, `-fu`, line continuations, branch deletion and `--mirror`.
- **Guardrails can't be switched off by the agent:** new `sdlc-protect-guardrails-file` and `sdlc-protect-guardrails-bash` block edits, moves and deletes of `.claude/hookify/sdlc-*.md`. Existing repos get them from `/sdlc:upgrade`.
- **Secrets:** blocked in notebook cells and Bash commands too (`sdlc-secret-values-bash`), and the key formats now include `sk-proj-`, `github_pat_`, Stripe live keys and Google API keys.
- **Hookify engine:** rules load from the project root even when a hook starts in a subdirectory; a `block` rule on a prompt now blocks it; broken rules (unknown event, action or operator, invalid regex, no frontmatter) are reported in the hook output and by `/sdlc:doctor` instead of being skipped silently; a BOM, blank first line or capitalised `Block`/`Bash` no longer disarms a rule; a regex that runs over 1 s is skipped; rule messages are capped at 2000 characters.
- **Other:** the reviewer SDK is installed at a pinned version; `/sdlc:ralph-loop` rejects a multi-line `--completion-promise` and warns when no session id is available.

### Changed
- **Model tiers are named:** cheap = `haiku`, standard = `sonnet`, top = `opus`. Skills used to say "the most capable available model", which could resolve to Fable. Fable is now used only when you ask for it (`Top model: fable` in `state.md`), and fix-loop escalation stops at the top tier.
- **Risk sets the models:** the orchestrator records `Risk: low | high` next to `Track:`, and every dispatch picks its model from track and risk. A small change to auth, payments, secrets, PII, migrations or a public API still gets top-tier review.
- **Model router hook:** while a feature is active, a subagent dispatch is denied if it names no model, asks for Fable without your opt-in, or runs a reviewer below Opus on a high-risk feature. Forks are exempt (they always use the session model).
- **Upgrades add new plugin files:** `/sdlc:upgrade` now installs policy rules and guardrails that are new in the installed version (an "add" step), so repos set up earlier get them. Files you handed back with "keep mine" (`forget`) are remembered and never re-added; a file of yours with the same name is never overwritten.
- **Monorepo verify:** the orchestrator records the commit a feature starts from (`Base:` in `state.md`); in Stage 5 only packages changed since then need their tests rerun. Without a base, every package does, as before.

### Fixed
- **`sdlc-sensitive-files`** now matches Windows paths (`C:\proj\.env`, `.ssh\id_rsa`); the pattern only accepted `/`.
- **Upgrades on Windows:** `scaffold render` writes LF, so `upgrade-plan` no longer lists every unchanged seeded file as "replace". Repos set up on Windows show one spurious "replace" per file on the first upgrade after this.
- **Line endings on Windows:** plugin files checked out with CRLF (git's `core.autocrlf`) no longer count as hand-edited. `/sdlc:doctor` stops warning about them, and `/sdlc:upgrade` overwrites them instead of asking you to review each one. File hashes ignore CRLF versus LF.
- **Stage 5 freshness:** a test command whose own flags look like a name filter (unittest's `-t .`) now counts as a full run. It never did, so Stage 5 blocked every turn end for such packages. Only arguments added after the test command are checked for filters now, so a run piped through `grep -t` counts too. A filter or test file after a redirect (`npm test 2>/dev/null -t login`) is no longer missed.
- **`/sdlc:doctor`** no longer crashes with `UnicodeEncodeError` when its output goes to a non-UTF-8 console or pipe (cp1252 on Windows); it writes UTF-8.
- **Setup and upgrade on Windows:** `scaffold.py` no longer crashes with `UnicodeEncodeError` on non-ASCII output (rendered rules, migration summaries, paths); it writes UTF-8.
- **`/sdlc:doctor`** fails when `python3` is missing or doesn't run (the hooks start with it and fail open without it) and warns when `jq` is missing (the ralph-loop stop hook needs it).
- Greenfield setup no longer creates or edits `CLAUDE.md`; the knowledge pointer lives in `.claude/rules/sdlc.md`.
- `/sdlc:doctor` no longer warns about the plugin's own policy rules (e.g. `sdlc-migrations.md`) matching no files yet, and explains that the security reviewer's environment is only built when the security hooks receive credentials.
- `/sdlc:eject` removes the `.sdlc/.work/` scratch folder along with its `.gitignore` line.
- Setup reports a step it skips as not applicable (with the reason) when it skips it, not only in the final report.

## 1.3.0 — 2026-10-22

### Added
- **Project setup:** `/sdlc:setup` for new and existing repos. Records the repo's own commands in `.sdlc/config.json` (per package in a monorepo), a known-failures baseline, a deep audit into knowledge and area rules, policy rules, guardrails, lint snippets, an allowlist, generated CI, constitution and knowledge. Runs on a branch, resumable.
- **Upgrades and removal:** `/sdlc:upgrade` (regenerate plugin files, ask before touching edited ones, versioned migrations) and `/sdlc:eject`. File ownership is tracked in `.sdlc/scaffold.lock.json`.
- **`/sdlc:doctor`:** read-only health check of machine, plugin and repo, with a fix per problem.
- **Scope tracing:** `[user]`/`[clarified]`/`[inferred]` requirement tags and Non-Goals in specs (inferred items dropped unless kept); Complexity Tracking for every design addition; task `Requirements:` lines and a Public Surface section in plans; `diff_stats.py --plan` flags undeclared surface in review.
- **Conventions:** policy rules (`.claude/rules/sdlc-*.md`: workflow, code style, tests, migrations, sensitive areas, CI), 11 hookify guardrails (dangerous `rm`, force-push to main, secrets, narrating/history/long comments, suppressions, focused tests, `console.log`), ESLint and Ruff snippets, and `diff_stats.py` facts in every review.
- **Verification:** baseline-aware verifier (fails only on new failures); freshness tracked per package; config-driven test commands.
- **Docs:** guidebook, playbook, runbook, diagrams, CONTRIBUTING; ADRs (`docs/adr/`), a PRD and numbered capability specs with each requirement tied to the test that proves it (`docs/prd.md`, `docs/specs/`); marketplace manifest.

### Changed
- `/sdlc:start` routes to setup when a repo isn't set up and reports version drift; `/sdlc:status` shows setup state.
- Track sizing defaults to the smallest track that fits; sizing up names its signal.
- Default constitution template includes a Simplicity principle.

### Fixed
- Hookify: `new_text` now covers `Write`; new `not_regex_match` operator; warnings reach Claude (`additionalContext`) and blocks say why (`permissionDecisionReason`); committed team rules in `.claude/hookify/*.md`; no more duplicate evaluation after each tool call.
- Ralph loop: stop hook no longer crashes on a state file missing a field.
- Verify freshness: catches edits made outside Edit/Write (worktree fingerprint), single-file and single-package runs, and redirects like `2>&1`.

## 1.2.0

First version: orchestrator with S/M/L tracks and 11 gated stages; vendored skills, agents and commands from Superpowers, GitHub Spec Kit and Anthropic's plugins under the `sdlc:` namespace; fresh verifier per round with the Stage 5 freshness hook; 3-tier knowledge; security-guidance, hookify and ralph-loop hooks; hook test suite.
