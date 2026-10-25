# sdlc playbook

Situation-by-situation plays. Each says what to say or run, what the orchestrator does, and where you decide. Concepts are in the [guidebook](guidebook.md); failures are in the [runbook](runbook.md).

## Quick map

| You want to… | Play |
|---|---|
| Start a brand-new project | [15](#15-start-a-new-project) |
| Adopt sdlc in an existing repo | [14](#14-adopt-sdlc-in-an-existing-repo) |
| Update after a plugin release | [16](#16-upgrade-after-a-plugin-update) |
| Remove sdlc from a repo | [17](#17-remove-sdlc-from-a-repo) |
| Fix a bug | [1](#1-fix-a-bug-s-track) |
| Add a feature | [2](#2-add-a-feature-m-track) |
| Build something new or unclear | [3](#3-build-a-new-service-or-module-l-track) |
| Change auth, payments, secrets, PII or migrations | [4](#4-change-something-risky) |
| Pick up where you left off | [5](#5-resume-or-check-status) |
| Something feels broken | `/sdlc:doctor`, then the [runbook](runbook.md#health-check) procedure it names |
| Get out of a failing Verify | [6](#6-verify-keeps-failing) |
| Get unblocked when a turn won't finish | [7](#7-the-stop-hook-says-re-run-tests) |
| Answer review comments | [8](#8-handle-review-feedback) |
| Skip process on purpose | [9](#9-skip-a-gate-deliberately) |
| Merge and deploy | [10](#10-merge-and-deploy) |
| Let Claude iterate alone on a small task | [11](#11-run-an-autonomous-loop) |
| Stop repeating the same correction | [12](#12-turn-a-correction-into-a-rule) |
| Keep CLAUDE.md small | [13](#13-keep-always-loaded-context-small) |
| Clean up finished features | [18](#18-clean-up-finished-features) |

## 1. Fix a bug (S track)

**Say:** `/sdlc:start fix: export button 500s when the report is empty`

1. The orchestrator proposes S: bug, few files, clear behavior. Stages run 4 → 5 → 6 (light) → 8. No spec, design or plan file.
2. Stage 4: one implementer subagent on the cheap tier writes a failing test that reproduces the bug, then the fix. The session doesn't write the fix itself, so it costs the same on any session model. If something fails unexpectedly, `systematic-debugging` takes over.
3. Stage 5: a fresh `verifier` runs the full suite. The repro test must be among its evidence.
4. Stage 6: `code-simplifier`, then `code-reviewer`, both given `diff_stats.py` facts.
5. Stage 8: PR and CI.

**You decide:** the merge. Nothing else stops you.

**If the bug turns out bigger** (touches auth, spreads past 3 files, unclear cause): say so. The orchestrator names the signal in `state.md` and moves to M.

## 2. Add a feature (M track)

**Say:** `/sdlc:start add CSV export to the reports page`

Low-risk M work runs the **Lite flow**: you approve one `spec.md` with its task list, keep or drop its `Inferred` items, and the rest (native build, one verifier, one review, light security, one commit) runs on its own. You decide merge, PR or keep at the end. Say "use the full flow" for the steps below; high-risk M work always gets them.

1. Stages 1 → 3 → 4 → 5 → 6 → 7 (light) → 8. Stage 2 joins if the approach isn't obvious.
2. **Stage 1:** `writing-specs` produces `spec.md`. Read the `[inferred]` list the orchestrator shows. Each item is dropped unless you keep it, so keep only what you actually want. **You approve** the spec.
3. **Stage 2 (when it runs):** read the Complexity Tracking table. Anything that doesn't cite a requirement should come out. **You approve** the design.
4. **Stage 3:** check the Public Surface section: it's everything new that others can see. **You pick** subagent-driven (default for larger plans) or native execution.
5. Stages 4–8 run on their own unless a gate fails.

**Bigger than one session?** The spec comes with a `backlog.md` of slices; approve both at once. Slices then run back to back and commit one by one. If the session runs low it stops at a slice boundary and names the next one: `/clear`, then `/sdlc:start`. Want to look at each slice first? Say so, and it records `Slice gates: plan, review, commit`. Long backlog, and you'd rather not `/clear` by hand? Run `python3 <plugin>/scripts/yolo.py <feature>` in a terminal: a fresh headless session per slice, then feature close, stopping at your merge decision or at the first blocked slice.

**Good habits:** state non-goals up front; answer the one batch of blocking questions (if any) concisely; challenge any addition you didn't ask for before approving the spec, not after the code exists.

## 3. Build a new service or module (L track)

**Say:** `/sdlc:start build an invoicing service with PDF output`

1. Stages 1–8 and 11 (Stage 9 only when you ask; Stage 10 is parked). Stage 1 begins with `brainstorming` (writes `brainstorm.md`); it may open a visual companion that needs Node.
2. Design dispatches `code-explorer` and `code-architect`. Expect options: minimal, minimal plus one named extension, pragmatic. Minimal is recommended unless it fails a named requirement.
3. Stage 4 uses a git worktree and subagent-driven development: a fresh implementer per task, a task review after each.
4. Stage 7 is full. Stage 11 writes `retro.md` and promotes lessons.

**You decide:** spec, design, execution method, merge, deploy, migrations.

## 4. Change something risky

Auth, payments, secrets, PII, schema migrations: the work is **at least M** and **always gets full Stage 7**. `state.md` records `Risk: high`, so the verifier and reviewers run on `opus` (the model-router hook enforces it).

1. Expect the security-guidance hooks to warn on risky edits while you build (pattern warnings, diff review at turn end, a background review after `git commit` and `git push`). Address every finding they raise, or acknowledge it with a reason.
2. Stage 7 adds an explicit pass: `feature-reviewer` and `code-reviewer` with a security-only brief (injection, authz, secrets, SSRF, XSS, unsafe deserialization, dependency risk) plus the stack's dependency audit.
3. Gate: no critical or high finding open, no secrets in the diff; written to `security.md`.
4. DB migrations and production deploys are hard stops. Say go explicitly.

For deeper scanning, see `skills/orchestrator/references/integrations.md`. Claude Security isn't bundled for licensing reasons.

## 5. Resume or check status

- `/sdlc:status`: one line per feature (track · stage · last gate), plus open questions and deviations. Read-only.
- `/sdlc:start` with no argument: resumes the single feature whose `state.md` says `Status: active`. If several are active it asks which.

New session, same feature: nothing to re-explain. The state file and artifacts carry it.

**Someone else's feature:** the state file names its `Owner:` and `Tool:`. Before advancing a feature you don't own, the orchestrator asks, then records the handover under Deviations.

**Pause a feature:** set `Status:` in its `state.md` to something other than `active` (for example `paused`) so `/sdlc:start` stops picking it up; set it back to resume.

## 6. Verify keeps failing

Each round, a **new** verifier runs everything fresh, so flaky results show up as flaky, not as pass-after-retry.

| Round | What happens |
|---|---|
| 1–2 fail | Back to Stage 4 for the listed failures only: failing test first, `systematic-debugging` for anything unexplained. Then Stage 5 again with another fresh verifier |
| 3 fails | The orchestrator stops and brings you: what still fails, what each round changed, a root-cause hypothesis |

**A failure that existed before your change:** if it's listed in `.sdlc/baseline.md` it doesn't fail the round. If it isn't, the verifier reports it as new and may ask to baseline it; that's your call, recorded as a Deviation. Baseline items that now pass are removed automatically.

**A QA round you asked for failed a scenario but the tests pass:** the tests prove something other than what the spec says. If you send it back to Stage 4, write a failing test that reproduces the qa-tester's steps first. **A scenario marked "not run":** add the missing run step to `quickstart.md` or check it yourself.

**"Doesn't prove the change":** that test passes with your code put back to `Base:`, so it can't be the evidence for a criterion. Make it assert the new behavior, or point the criterion at a test that does.

**Your options at the cap:** allow more rounds, narrow the scope, or revisit the design. Pick one; the orchestrator records it in the gate log. Don't ask it to rerun until green: retried-until-green tests are an explicit gate violation.

## 7. The stop hook says "re-run tests"

Cause: you are in Stage 5 and code changed after the last full test run (or no full run happened). Fix: run the **full** suite: the `test` command from `.sdlc/config.json` (in a monorepo, the stale package's own, from its directory; the message names it), or the `test:` command in `state.md`. A filtered run, single file or single package doesn't count.

If the change was only to docs (`.md`, `.sdlc/`, `knowledge/`, `docs/`) it doesn't mark results stale. For a hook that misbehaves, see [runbook R4](runbook.md#r4-blocked-at-stop-with-re-run-tests).

## 8. Handle review feedback

Use `sdlc:receiving-code-review`: verify each comment against the code before agreeing, push back with evidence when it's wrong, fix the rest.

| Source | Command |
|---|---|
| Local, before the PR | `/sdlc:review-pr` (picks agents based on the diff) |
| Plan versus implementation | `sdlc:requesting-code-review` |
| On the GitHub PR | `/sdlc:code-review` |

Severity rules to know: unrequested public surface (an export, file, endpoint, option, config key or dependency not in the spec or plan with no stated reason) is **high**. Comment noise is **medium** and fixed in Stage 6, not ticketed.

## 9. Skip a gate deliberately

Say `skip` or `just ship it`. The orchestrator will:

1. name the gates being skipped,
2. record them under **Deviations** in `state.md`,
3. comply.

It does not skip hard stops that protect irreversible actions without your explicit word. Skipping a gate is allowed; skipping silently is not.

## 10. Merge and deploy

1. Stage 8: `finishing-a-development-branch` offers merge, PR or keep, and cleans up worktrees. `/sdlc:commit-push-pr` opens the PR with links to `spec.md`, `test-report.md` and, if a QA round ran, `qa-report.md`. `/sdlc:clean_gone` prunes merged local branches afterward.
2. **CI must be green. The orchestrator never merges without you saying so.**
3. Stage 9 (any track, on request): uses the project's existing deploy path. It writes `release.md` (version, environment, steps run, smoke test, rollback command). You give the go-ahead before production or a migration. The smoke test must pass.
4. Stage 10 (parked: no track runs it for now): check the agreed signals for the watch window. Out of threshold means a rollback or fix ticket.

## 11. Run an autonomous loop

For one well-specified task with a machine-checkable finish:

```
/sdlc:ralph-loop "Make all tests in tests/export pass" --completion-promise "DONE" --max-iterations 15
```

Always set `--max-iterations`. Cancel with `/sdlc:cancel-ralph`. Use it inside Stage 4 only; it doesn't replace gates, Verify still runs afterward.

## 12. Turn a correction into a rule

If you've corrected the same thing twice **and** a pattern in a command, file edit, prompt or stop event can catch it, write a hookify rule instead of more prose.

1. `/sdlc:hookify` with a description, or with no arguments to have `conversation-analyzer` scan the session for candidates.
2. Rules live in `.claude/hookify/<name>.md` (committed, team) or `.claude/hookify.<name>.local.md` (personal, git-ignored).
3. A rule has `event` (`bash`, `file`, `stop`, `prompt`, `all`), `action` (`warn` or `block`), and conditions with a `field`, `operator` and `pattern`. Syntax details are in `sdlc:writing-hook-rules`.
4. `/sdlc:hookify-list` shows what is active; `/sdlc:hookify-configure` enables or disables rules.

Start with `warn`. Move to `block` once the pattern has no false positives.

## 13. Keep always-loaded context small

- `CLAUDE.md` over about 60 lines: run `/sdlc:knowledge-audit`. It proposes moves (file → tier, with a reason) and shows the line count before and after. Nothing is applied without your OK.
- After a stage, `/sdlc:revise-claude-md` collects candidate lessons from the session and routes each to the right tier.
- Rule of thumb: tier 1 is only what nearly every task needs; area-specific guidance goes to tier 2 with `paths:`; everything else is tier 3, linked from `knowledge/index.md`.

## 14. Adopt sdlc in an existing repo

1. Install the plugin (see the [runbook](runbook.md#install)).
2. Commit or stash your work, then run `/sdlc:setup`. It detects brownfield on its own and works on a `sdlc/setup` branch.
3. **Commands:** it records the commands you already use (`pnpm test`, `make lint`, `./gradlew build`, …) in `.sdlc/config.json`, per package in a monorepo. Missing steps stay `null` rather than being invented. You approve the list.
4. **Baseline:** it runs lint, typecheck, build and tests and records what already fails in `.sdlc/baseline.md`. Read it: features will only be judged on new failures. A failing install or build stops setup instead.
5. **Audit:** explorer agents draft conventions, gotchas from git history, decisions and per-area rules. You approve, edit or drop each item; nothing is written otherwise.
6. **Existing AI config** (long CLAUDE.md, AGENTS.md, Cursor rules, ADRs): one migration diff per source; originals stay unless you say delete.
7. Rules, guardrails, lint snippets, allowlist, constitution and knowledge follow, plus an optional step that adds the sdlc marketplace and `enabledPlugins` to `.claude/settings.json` so teammates are offered the plugin. Existing CI is left alone (it points out steps that differ from the recorded commands); a repo without CI is offered a workflow generated from them.
8. At the end: open a PR or merge locally, your choice. Then `/sdlc:start` a small S fix to see the loop end to end.

Interrupted? Run `/sdlc:setup` again; it resumes from the last finished step.

## 15. Start a new project

1. Create an empty repo (README and LICENSE are fine) and run `/sdlc:setup what you're building`.
2. Answer a few stack questions; it proposes the stack, layout and the commands per package. **You approve before anything is generated.** It keeps to what the first feature needs: no auth, database or infra "for later" unless you asked.
3. The ecosystem's own generators build the skeleton, plus strict types, a test runner, a linter and one passing test per package. Every command must pass.
4. CI (`.github/workflows/sdlc-verify.yml`) is generated from the same commands, with `sdlc-invariants.yml` next to it to check the shared sdlc files. Windows teammates: set `"ci": {"os": ["ubuntu-latest", "windows-latest"]}` in `.sdlc/config.json`.
5. Rules, guardrails, constitution and knowledge as in [14](#14-adopt-sdlc-in-an-existing-repo). No baseline: nothing fails yet.

**Several apps** (web, an API, mobile): setup builds one monorepo, with `apps/<name>/` for each app, `packages/` for shared code, `docs/` for BA, QA and design files, and `infras/` only if you say yes. It asks who will work in the repo. A large team with separate roles gets CODEOWNERS, one CI workflow per app and a release runbook (`docs/runbooks/releasing.md`). A solo developer or small team gets one workflow. When one app serves an API another uses, the contract goes in `packages/api-contract/v1/`. Merging a version publishes it, and if you agree, CI blocks breaking changes to published versions. Each app generates its client from the version it uses. Details: `skills/setting-up-projects/references/monorepo.md`.
6. PR or local merge, then `/sdlc:start` the first feature.

## 16. Upgrade after a plugin update

`/sdlc:start` and `/sdlc:status` tell you when the repo's scaffold is behind the installed plugin. Nothing breaks if you wait; you just miss the new rules and fixes.

1. Finish or pause in-flight features if you can; the upgrade warns if one is past Stage 3.
2. `/sdlc:upgrade --dry-run` to see the plan: files regenerated, files replaced, files you edited, migrations.
3. `/sdlc:upgrade` runs it on a `sdlc/upgrade-<from>-<to>` branch. For each plugin file you edited you choose: **apply** the proposed merge, **skip** this time, or **keep mine** (the plugin stops managing that file).
4. Each migration is shown as a diff. Declined ones are recorded and not asked again; `/sdlc:upgrade --revisit` brings them back.
5. PR or local merge. The repo now pins the minimum plugin version, so teammates on an older plugin get a warning to update.

## 17. Remove sdlc from a repo

`/sdlc:eject` shows a dry run first. It removes the plugin's own files (generated rules, unedited guardrails, CI workflow and lint snippets, the allowlist, plugin-enablement and `.gitignore` entries it added, the sdlc block in `AGENTS.md`, the lock) and keeps your specs, knowledge, constitution, commands, baseline and area rules. Edited plugin files are asked about one by one. It also fixes imports that would point at deleted files, runs the verify commands, and asks PR or local merge. Uninstall the plugin afterwards if you're done with it.

## 18. Clean up finished features

`.sdlc/` keeps every feature's folder. Old plans and test reports describe code that has since changed, and agents searching the repo can be misled by them.

1. `/sdlc:prune` lists merged features marked done 45+ days ago (`--older-than 90d` to change that) and what would go: plan, test and QA reports, review, checklists.
2. Pick which to prune. Spec, design, retro and state stay, and so does security.md on high-risk features.
3. It commits the deletions in one commit. Anything you need later is in git history.

## Who decides what

| Decision | Owner |
|---|---|
| Running setup, stack choice, the recorded commands | You approve |
| Each audit batch, each AI-config migration | You approve, edit or drop |
| Upgrade: edited plugin files, migrations | You choose per file / per migration |
| Adding a failure to the baseline | You, recorded as a Deviation |
| PR or local merge after setup, upgrade, eject | You |
| Track size | Orchestrator proposes, you can override |
| Spec, design | You approve |
| Execution method | You pick |
| Verify verdict | The fresh verifier, never the orchestrator |
| After three failed Verify rounds | You |
| Merge, production deploy, DB migration | You |
| Skipping a gate | You, recorded as a Deviation |
