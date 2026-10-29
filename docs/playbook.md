# sdlc playbook

Situation-by-situation plays. Each says what to type, what the agent does, which files appear and where you decide. Concepts are in the [guidebook](guidebook.md); failures are in the [runbook](runbook.md).

A feature's change file goes in `<docs>/changes/<feature>.md` (`<docs>` is `docs/sdlc` unless setup chose another folder), its state in `.sdlc/state/<feature>.md` and its working files (backlog, part plans, QA report) in `.sdlc/state/<feature>/`. Feature names look like `2026-10-26-m-csv-export`: date, the track it started on, slug.

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
| Build something too big for one session | [19](#19-a-big-feature-becomes-a-backlog) |
| Run a backlog's slices unattended | [20](#20-run-a-backlog-on-autopilot) |
| Change auth, payments, secrets, PII or migrations | [4](#4-change-something-risky) |
| Pick up where you left off, or pause | [5](#5-resume-or-check-status) |
| Something feels broken | `/sdlc:doctor`, then the [runbook](runbook.md#health-check) procedure it names |
| Choose the reviews, or act on their findings | [6](#6-choose-the-reviews-and-act-on-findings) |
| Get unblocked when a turn won't finish | [7](#7-the-stop-hook-says-re-run-tests) |
| Understand a "Verification anchors changed" stop | [21](#21-the-trust-anchor-stopped-me) |
| Answer review comments | [8](#8-handle-review-feedback) |
| Skip process on purpose | [9](#9-skip-a-gate-deliberately) |
| Merge and deploy | [10](#10-merge-and-deploy) |
| Let Claude iterate alone on one small task | [11](#11-run-an-autonomous-loop) |
| Stop repeating the same correction | [12](#12-turn-a-correction-into-a-rule) |
| Keep CLAUDE.md and per-call context small | [13](#13-keep-always-loaded-context-small) |
| Clean up finished features | [18](#18-clean-up-finished-features) |

## 1. Fix a bug (S track)

**Type:** `/sdlc:start fix: export button 500s when the report is empty` (or paste a GitHub issue, Linear or Jira link).

1. **Define:** the agent sizes it S (a fix or tweak, 1–2 files, clear expected behaviour). If what, why or how isn't clear, it asks first, one question at a time. It proves the bug before proposing a fix (a failing test, or exact steps and what they show), then finds the root cause. It writes the change file (the proof and the cause; the proving test is AC-001) and the state file's tasks and Public Surface, a few lines each, with the tests in the same turn. No stop: it says in a line or two what it will do and why.
2. **Build:** in the session, like plain Claude. One call moves it to Build and records the proving test failing (`state.py sync && state.py advance 4 && verify.py red AC-001`), then the fix, then `verify.py` once at the end.
3. **Review:** the agent recommends the reviews the change needs (often none for a small, covered fix) and runs them without stopping, telling you what ran and why ([6](#6-choose-the-reviews-and-act-on-findings)).
4. **Ship:** Learn files a lesson only if it isn't obvious from the code or the commit, and a decision later features must follow in `knowledge/decisions/`, then the final commit on a feature branch, push, PR and CI. It stops with the PR open.

**You decide:** the merge. Anything that adds scope also stops it.

**If the bug is bigger:** when the fix needs more files than expected or the approach is unclear, the agent says so and sizes up to M, which needs your approval before the build.

## 2. Add a feature (M track)

**Type:** `/sdlc:start add CSV export to the reports page`

1. **Define:** if anything that would change what gets built is unclear, the agent asks first, one question at a time, each built on your last answer. Then it writes the record, once: the change file (what it's for, why now, the decisions with what was ruled out and why; about 10 or fewer acceptance criteria numbered `AC-001` onward, each with its test in `## Acceptance tests`; out of scope; must-never-break lines and failure modes) and the state file's plan sections (how the build runs, the tasks with their files, the Public Surface listing everything new others can see).
2. **You read and approve.** One message with the path to the change file, the approach and what was ruled out, each acceptance criterion with its test (`manual` ones apart, with their reasons), how the build runs (inline, parts in fresh sessions, or parallel subagents) and any extras the agent would drop unless you keep them. Reply "approved", or change anything.
3. **Build:** from the files, in the session by default. Every criterion's test, then one `verify.py red AC-001 AC-002 …` to record them failing, then the code. `verify.py` once at the end runs the checks, every criterion's test and the drift check. Changes from the plan go in the state file's `## Deviations` (`state.py deviation`, "What: … Why: … Effect: …"); they never stop the build.
4. **Review:** the agent recommends reviews from what actually changed (security, code at default or high depth, UI, advisor, or none), each with a reason, and **stops for you to choose**. Each chosen review runs once, fresh: in Claude Code the code review on S and M is the built-in `/code-review`, every other review (and every review in other agents) on `opus` ([6](#6-choose-the-reviews-and-act-on-findings)).
5. **Ship:** Learn, then the final commit, push, PR and CI. It stops with the PR open; the merge waits for your word.

**Good habits:** state what's out of scope up front; answer the questions briefly; challenge any addition you didn't ask for at the approval, not after the code exists. Too big for one session? See [19](#19-a-big-feature-becomes-a-backlog).

## 3. Build a new service or module (L track)

**Type:** `/sdlc:start build an invoicing service with PDF output`

1. **Define:** `brainstorming` runs the interview, one question at a time, and its design becomes the change file's Why and Decisions. It may offer a browser visual companion (needs Node). There is no separate design document. The criteria, their tests and the state file's plan sections follow, full.
2. **You read and approve** the change file (and `backlog.md` if the work is split into parts, [19](#19-a-big-feature-becomes-a-backlog)), with how the build runs.
3. **Build:** as the state file's `## How the build runs` says: inline, one part per fresh session, or parallel subagents for truly independent parts. No review agents during the build.
4. **Review:** the recommendation, then your choice; each chosen review runs once on `opus`; high findings go back to Build, each fixed with a failing test first.
5. **Ship:** Learn, the final commit, push, PR and CI. Deploy only when you ask ([10](#10-merge-and-deploy)).

**You decide:** Define's approval, the reviews, merge, deploy, migrations.

## 4. Change something risky

Auth, payments, secrets, PII, schema migrations, a breaking change to a public API: the work gets `Risk: high`. Adding a command, flag or field, or an optional field to stored data, isn't breaking: that's `low`. Risk doesn't change the track; it feeds the review recommendation. A change is **security-touched** when `Risk: high`, or the diff touches `areas.sensitive` or `areas.migrations` in `.sdlc/config.json`. Keep those lists right: a sensitive path they miss gets no security review. Every review runs on `opus`, at every size; the model-router hook denies a cheaper one.

1. While you build, the security hooks warn on risky edits and review the diff at turn end. The commit review runs after `git commit`: on a feature branch, build commits wait and are reviewed together with the next review-ready commit. A feature's change that isn't security-touched gets no model review; it is recorded as reviewed. Address each finding, or acknowledge it with a reason.
2. After the build, the agent recommends a **security review** for a security-touched change: a `code-reviewer` with the security-only brief (injection, authz, secrets, SSRF, XSS, unsafe deserialization, dependency risk), plus the dependency audit. On M and L you can still decline it; on S it runs. On a backlog it runs once, at feature close.
3. Gate: no critical or high finding open, no secrets in the diff; recorded in the change file's `## Review`.
4. DB migrations and production deploys are hard stops. Say go explicitly.

Deeper scanners (Claude Security, Semgrep and others, not bundled): `skills/orchestrator/references/integrations.md`.

## 5. Resume or check status

- `/sdlc:status`: one line per feature (track · phase · last gate), open questions and deviations, and whether the repo's scaffold is behind the plugin. Changes nothing.
- `/sdlc:start` with no argument resumes the one feature with `Status: active`, in its phase. Several active: it asks which.

A new session needs no re-explaining: the state file and the change file carry everything.

**A feature started under sdlc 1.x** (its state file has no `Process: 2`) can't run on 2.0: `/sdlc:start` says so. Finish it with sdlc 1.8.1, or archive it (`Status: done`).

**Someone else's feature:** the state file names its `Owner:` and `Tool:`. Before advancing a feature you don't own, the agent asks, then records the handover as a deviation.

**Pause a feature:** tell the agent to pause it. It runs `state.py set <feature> Status paused`, so `/sdlc:start` stops picking it up. The trust anchor reports the change once ([21](#21-the-trust-anchor-stopped-me)). Ask it to set `active` again to resume. Don't edit the state file by hand.

## 6. Choose the reviews and act on findings

After Build's passing `verify.py`, the agent looks at what actually changed and recommends, each with a one-line reason:

| Review | Recommended when |
|---|---|
| Security | `Risk: high`, or the diff touches `areas.sensitive` or `areas.migrations`, or untrusted input reaches a shell, file path or database |
| Code, high | the spec has must-never-break lines or failure modes, a public interface changed, or the diff is large |
| Code, default | a typical M or L change |
| UI | the diff touches `areas.ui`: always recommended |
| Advisor | only where the agent has one, for a real open judgment call |
| None | a small, contained, fully tested change touching nothing above |

**S:** it runs the recommendation and tells you. **M and L:** it stops and you pick (take it, add, drop). **Autopilot or headless:** it takes the recommendation and logs that it did.

Each chosen review runs **once**, as a fresh agent on `opus`, and ends its report with `VERDICT: PASS` or `VERDICT: FAIL — <ids>`.

- **High findings** go back to Build, each fixed with a failing test first, then `verify.py` again. The review isn't rerun: the fixes are proven by their tests and the full suite.
- **You disagree, or the agent does:** a high finding the agent thinks is wrong comes to you with its case. Only you can waive one, recorded as a deviation.
- **Medium and low** findings that are bugs in code the change touched (wrong behaviour, a crash, an unhandled error, a missing test) are fixed too, test first, without asking you. The rest (improvements, code the change didn't touch) are ticketed in the change file's `## Review`.

**A failure that existed before your change:** `verify.py` doesn't read `.sdlc/baseline.md`. When only the test step fails and every failure is listed there, the agent logs it and passes the gate. A new failure is reported; baselining it is your call, recorded as a deviation.

**`verify.py` keeps failing in Build:** the agent debugs it (`systematic-debugging`) and fixes the code or the test. A test that passes before its code exists is refused by `verify.py red`; make it assert the new behaviour, and the change goes in the state file's `## Deviations`. Don't ask it to rerun until green.

**A QA round** (`qa-tester`, runs the feature as a user would, without reading the code) is available on request; its report is `qa-report.md` in the feature's work folder, `.sdlc/state/<feature>/`.

## 7. The stop hook says "re-run tests"

Cause: you are in Review (`Current: Stage 5`) and code changed after the last full test run, or there hasn't been one. Fix: run the **full** suite: the `test` command from `.sdlc/config.json` (in a monorepo, the stale package's own, from its directory; the message names it), or the `test:` command in the state file. A filtered run, a single file or a single package doesn't count.

Changes under `.sdlc/`, `knowledge/`, `.claude/`, `docs/` or the sdlc docs folder, and `.md`, `.mdx`, `.txt` or `.rst` files, don't make results stale. A misbehaving hook: [runbook R4](runbook.md#r4-blocked-at-stop-with-re-run-tests).

## 8. Handle review feedback

Use `sdlc:receiving-code-review`: check each comment against the code before agreeing, push back with evidence when it's wrong, fix the rest.

| Source | Command |
|---|---|
| Local, before the PR | `/sdlc:review-pr` (picks agents for the diff; the comment, type and simplifier agents need the `sdlc-extras` plugin) |
| Spec versus implementation | Review's code review, from the change file and the state file's plan sections |
| On the GitHub PR | `/sdlc:code-review` |

Severity rules: unrequested public surface (an export, file, endpoint, option, config key or dependency not in the state file's Public Surface, with no stated reason) is **high**. Code-style issues (comments, naming, formatting) are fixed in passing, never high. Other medium and low findings are fixed when they're bugs in the change, else go to the change file's `## Review` as tickets.

## 9. Skip a gate deliberately

Say `skip` or `just ship it`. The agent will:

1. name the gates being skipped,
2. record them as a deviation in the state file,
3. comply.

Hard stops (merge, production deploy, migrations, anything irreversible) still wait for your explicit word. Skipping a gate is allowed; skipping silently is not.

## 10. Merge and deploy

1. **Ship:** Learn, then one shell call with git and `gh` commits on a feature branch (code, tests, the change file and the state file), pushes and opens a PR that links the change file. The agent watches CI: red because of the code, it fixes it once (failing test first) and pushes again; still red, or red for a CI reason (a missing secret, a runner problem, a flaky test), it stops and tells you. Without a remote, it stops with the branch ready.
2. **It stops at the PR:** `PR <url> open, local and CI green; say "merge" to merge.` **The agent never merges without you saying so.** On "merge", the `finishing-a-development-branch.md` reference merges and cleans up worktrees; `/sdlc:clean_gone` prunes merged local branches when asked.
3. **Deploy** is a separate request: `/sdlc:deploy [feature] [environment]`.
   - It warns if the feature hasn't reached Ship, and continues only on your word.
   - It uses the project's existing deploy path (scripts, a CI job, the platform CLI). None: it says so and stops.
   - Before production or a migration it shows the environment, version, steps, migration and rollback command, and waits for your yes. A routine staging deploy doesn't.
   - It runs a smoke test. A failure: it offers the rollback, and a production rollback needs another yes.
   - It writes `release.md` in the feature's work folder (version, environment, steps, smoke result, rollback) and commits it only if you ask.

## 11. Run an autonomous loop

This is the Ralph loop: one task repeated in the current session. For running a backlog's slices in fresh sessions, see autopilot ([20](#20-run-a-backlog-on-autopilot)).

It comes with the optional companion plugin: `/plugin install sdlc-extras@sdlc`, then restart. For one well-specified task with a machine-checkable finish:

```
/sdlc-extras:ralph-loop "Make all tests in tests/export pass" --completion-promise "DONE" --max-iterations 15
```

Always set `--max-iterations`. Cancel with `/sdlc-extras:cancel-ralph`. Use it inside Build only; Review still runs afterwards.

## 12. Turn a correction into a rule

If you've corrected the same thing twice **and** a pattern in a command, file edit, prompt or stop can catch it, write a hookify rule instead of more prose.

1. `/sdlc:hookify` with a description, or with no arguments to scan the session for candidates (with `sdlc-extras` installed, its `conversation-analyzer` agent does the scan).
2. Rules live in `.claude/hookify/<name>.md` (committed, team) or `.claude/hookify.<name>.local.md` (personal, git-ignored).
3. A rule has an `event` (`bash`, `file`, `stop`, `prompt`, `all`), an `action` (`warn` or `block`) and conditions. Syntax: the `sdlc:hookify` skill's `references/rule-syntax.md`.
4. With `sdlc-extras` installed, `/sdlc-extras:hookify-list` shows what's active and `/sdlc-extras:hookify-configure` turns rules on or off. Without it, edit `enabled:` in the rule file.

Start with `warn`. Move to `block` once the pattern has no false positives.

## 13. Keep always-loaded context small

- `CLAUDE.md` over about 60 lines: `/sdlc:knowledge-audit` proposes moves (file → tier, with a reason) and shows the line count before and after. Nothing is applied without your OK.
- After a feature, `/sdlc:revise-claude-md` collects lessons from the session and files each in the right tier.
- Every call also carries every enabled plugin's skills, agents and commands. `/sdlc:context-diet` estimates the cost per source and, after your OK, turns off what this project doesn't use (this project only), including the standalone copies of plugins sdlc bundles. Personal skills can only be moved into the projects that use them; synced claude.ai plugins are managed in claude.ai. Check `/context` in a new session for the real numbers.
- Rule of thumb: tier 1 (`CLAUDE.md`) only what nearly every task needs; area guidance in tier 2 (`.claude/rules/` with `paths:`); everything else in tier 3, linked from `knowledge/index.md`.

## 14. Adopt sdlc in an existing repo

1. Install the plugin ([runbook](runbook.md#install)).
2. Commit or stash your work, then `/sdlc:setup`. It detects brownfield and works on a `sdlc/setup` branch, one commit per step.
3. **Commands:** it records the commands you already use (`pnpm test`, `make lint`, `./gradlew build`, …) in `.sdlc/config.json`, per package in a monorepo. A missing step stays `null`. It doesn't touch your manifest, dependencies or tooling. You approve the list.
4. **Baseline:** it runs them and records what already fails in `.sdlc/baseline.md`. Features are judged only on new failures. A failing install or build stops setup.
5. **Audit:** explorer agents draft conventions, gotchas from git history, decisions and per-area rules. You approve, edit or drop each item.
6. **Existing AI config** (long `CLAUDE.md`, `AGENTS.md`, Cursor rules, ADRs): one migration diff per source; originals stay unless you say delete.
7. **The rest:** rules, guardrails, lint snippets (only for a linter you already have), allowlist, a product doc (PRD; yours if you have one, else drafted and approved), constitution, a design system (UI projects only: first who does the design work, sdlc's builtin system or impeccable, recommended from the PRD), knowledge. Turning sdlc on for this repo isn't asked: it goes in `.claude/settings.local.json`, your machine's file, never committed, and setup names the companion plugins it can add too (`sdlc-extras`; skipped for sdlc itself, and said so, when the session runs sdlc from a directory with `--plugin-dir`), and the companion skill Cloudflare's `security-audit` with its install command, for a full security audit on request (sdlc never installs or runs it unasked). The context diet is asked first ([13](#13-keep-always-loaded-context-small)). Existing CI is left alone (it points out steps that differ from the recorded commands); a repo without CI is offered a workflow, and every repo the `sdlc-invariants` check.
8. At the end: PR or local merge, your choice. Then `/sdlc:start` a small S fix to see the loop end to end.

Interrupted? Run `/sdlc:setup` again; it resumes from the last finished step.

## 15. Start a new project

1. Create an empty repo (README and LICENSE are fine) and run `/sdlc:setup what you're building`.
2. Answer a few stack questions. It proposes the stack, layout, generator and the commands per package, plus optional extras (a linter, formatter, toolchain pinning), each off unless you say yes. **You approve before anything is generated.** No auth, database or infra "for later" unless you asked.
3. The ecosystem's own generators build the skeleton, plus strict types, a test runner and one passing test per package. Every command must pass.
4. CI: `.github/workflows/sdlc-verify.yml` from the same commands, with `sdlc-invariants.yml` beside it to check the shared sdlc files. Windows teammates: set `"ci": {"os": ["ubuntu-latest", "windows-latest"]}` in `.sdlc/config.json`.
5. The common steps as in [14](#14-adopt-sdlc-in-an-existing-repo). No baseline: nothing fails yet.
6. PR or local merge, then `/sdlc:start` the first feature.

**Several apps** (web, an API, mobile): one monorepo, with `apps/<name>/` per app, `packages/` for shared code, `docs/` for BA, QA and design files, and `infras/` only if you say yes. It asks who will work in the repo. Separate roles get CODEOWNERS, one CI workflow per app and a release runbook (`docs/runbooks/releasing.md`); a solo developer or small team gets one workflow. When one app serves an API another uses, the contract goes in `packages/api-contract/v1/`, and if you agree, CI blocks breaking changes to published versions. Details: `skills/setting-up-projects/references/monorepo.md`.

## 16. Upgrade after a plugin update

`/sdlc:start` and `/sdlc:status` tell you when the repo's scaffold is behind the installed plugin. Nothing breaks if you wait; you miss the new rules and fixes.

1. Finish or pause in-flight features if you can. **Upgrading to 2.0:** a feature started under 1.x must be finished with sdlc 1.8.1, or archived (`Status: done`), first; the upgrade names each one and refuses until none is left ([ADR 0020](adr/0020-sdlc-2-slim-process-core.md), [runbook R20](runbook.md#r20-upgrade-to-20-with-a-1x-feature-in-progress)).
2. `/sdlc:upgrade --dry-run` shows the plan: files added, regenerated, replaced, edited by you, deleted by you, no longer shipped, and migrations.
3. `/sdlc:upgrade` runs it on a `sdlc/upgrade-<from>-<to>` branch. A new CI workflow is asked about first. For each plugin file you edited you choose: **apply** the proposed merge, **skip** this time, or **keep mine** (the plugin stops managing it). An edited guardrail (`.claude/hookify/sdlc-*.md`) you apply yourself: Claude is blocked from editing the rules that constrain it.
4. Each migration is shown as a diff. Declined ones aren't asked again; `/sdlc:upgrade --revisit` brings them back.
5. PR or local merge. The repo now records the minimum plugin version, so teammates on an older plugin are told to update.

## 17. Remove sdlc from a repo

`/sdlc:eject` shows a dry run first. It removes the plugin's own files (generated rules, unedited guardrails, CI workflow and lint snippets, the allowlist, plugin-enablement and `.gitignore` entries it added, the sdlc block in `AGENTS.md`, the lock) and keeps `.sdlc/config.json`, the PRD, the constitution, design system, knowledge, baseline, area rules and every feature's change file (older features: their documents) and state. Edited plugin files are asked about one by one. On a `sdlc/eject` branch it fixes imports that would point at deleted files, runs the verify commands, then asks PR or local merge. Uninstall the plugin afterwards (`/plugin uninstall sdlc`) if you're done with it.

## 18. Clean up finished features

Every feature keeps its working files after it ships. Old plans and reports describe code that has since changed, and agents searching the repo can be misled by them.

1. `/sdlc:prune` lists features marked done on the main branch 45+ days ago (`--older-than 90d` to change that), with the files that would go: the parts' `plan-B<n>.md`, `qa-report.md`, and 1.x features' `plan.md`, reports and checklists.
2. Pick which to prune. The change file and the state file stay (1.x features keep intent, spec, design, retro and state, and `review.md` only on high risk).
3. It commits the deletions in one commit. Git history keeps everything.

## 19. A big feature becomes a backlog

Work with several distinct parts that won't fit one session, on M or L. Never on S, and never a change confined to 1–2 files.

1. **Define** writes `backlog.md` in the feature's work folder, `.sdlc/state/<feature>/`: one row per part (`B1`, `B2`, …, each something a test can see working) with its acceptance criteria, dependencies and size. The state file's `## Tasks` gives each part an outline. You approve them all at once.
2. **Each part:** the agent writes `plan-B<n>.md`, builds until `verify.py` passes, commits it, and updates the state file's `## Handoff` so a fresh session can pick up from the files. No review per part. Parts run back to back without asking.
3. **It stops** for a backlog change that adds scope, or at a hard stop. To look at each part, say so: it records `Slice gates: plan, commit` (either or both).
4. **Low context:** it stops at a part boundary with `B<n> done (<commit>). Next: B<m> <title>. Run /clear, then /sdlc:start.` `/sdlc:start B<n>` runs a named part once its dependencies are done.
5. **Feature close**, after the last part: all parts land together. One Review over the whole branch (the recommendation and your choice, as in [6](#6-choose-the-reviews-and-act-on-findings)), then Ship with Learn, which stops at the PR.

Long backlog and you'd rather not `/clear` by hand: [20](#20-run-a-backlog-on-autopilot).

## 20. Run a backlog on autopilot

Autopilot runs each slice in a fresh headless Claude Code session, then feature close. It's opt-in and Claude Code only. It is not the Ralph loop ([11](#11-run-an-autonomous-loop)).

**Run, in a terminal at the repo root:**

```
python3 <plugin>/scripts/autopilot.py [--permission-mode <mode>] <feature>
```

The headless sessions need permission to edit files and run git, the project's commands and the plugin's scripts (`state.py`, `backlog.py`). Setup's allowlist covers only the project's own commands, so pass a `--permission-mode` or widen the allowlist. A session that is denied leaves its slice unchanged, and autopilot stops with `B<n> is still todo after its run`. The mode is handed to `claude` as given; autopilot never adds a permission-bypass flag.

Each session runs `/sdlc:start B<n> --autopilot`: it does one slice and ends, never asking. Anything that would ask (a scope change, a hard stop) marks the slice `blocked: <reason>` in `backlog.md` and adds an open question. Feature close's Review takes the agent's own recommendation and records that it did.

**It stops** on an open trust-anchor notice, a feature that isn't active, a blocked slice, nothing ready, a session that fails, a run that leaves its slice unchanged, or a feature close that doesn't reach Ship. It prints one JSON object naming the reason and the slices it ran. Fix the cause in a normal session (for a blocked slice, `/sdlc:start B<n>` and answer its question), then run the same command again.

**When it finishes,** feature close has run Review and Ship. The merge still waits for you: say merge in a normal session (`/sdlc:start`).

## 21. The trust anchor stopped me

The trust anchor watches what verification relies on. When something weakens it, the turn stops once with `⚠ Verification anchors changed: … Your next message accepts it.` The agent tells you what changed and why, and doesn't undo it on its own.

It reports, per active feature:

- `Track:` down, `Risk:` high → low, `Top model:`, `Base:` or `Process:` changed;
- a failing test added to `.sdlc/baseline.md`, or commands in `.sdlc/config.json` changed since `Base:`;
- the change file edited above `## Review` (its criteria and tests) after Review started;
- leaving Review without a passing full run of the current code, at every size, or with code changed since that run;
- leaving Review while a review's latest report says `VERDICT: FAIL`, unless you waived it;
- `verify records disagree`: `.sdlc/.work/verify.json` differs from the freshness hook's copy of the run, or is missing or damaged while the hook holds one;
- a feature stopping being active other than by finishing (a pause, a deleted state file);
- a damaged trust-anchor record.

Only 2.0 features (`Process: 2`) are watched; a 1.x feature is finished on 1.8.1.

**What to do:** read it. If the change is right, carry on: your next message accepts it. If not, say so and ask the agent to put it back.

A change that only adds checks (Track up, Risk low → high) shows `Stricter process: …` and doesn't stop you.

Autopilot won't start a session while a notice is open; its JSON `stopped` reason quotes the notice. Read it, send any message in a normal session to accept it, then run autopilot again.

## Who decides what

**Hard stops.** The agent always stops and asks:

| Decision | Owner |
|---|---|
| Define's approval on M and L: the change file, the plan (and backlog), how the build runs | You |
| Which reviews run after the build, on M and L | You |
| Anything that adds scope | You |
| A reviewer and the agent disagreeing on a high finding | You |
| CI still red after one fix | You |
| Merge (Ship stops with the PR open) | You |
| Production deploy | You |
| DB migration | You |
| Anything irreversible | You |

**Also yours:**

| Decision | Owner |
|---|---|
| Running setup, the stack, the recorded commands | You approve |
| Each audit batch, each AI-config migration | You approve, edit or drop |
| Upgrade: edited plugin files, new workflows, migrations | You choose per file / per migration |
| PR or local merge after setup, upgrade, eject | You |
| Adding a failure to the baseline | You, recorded as a deviation |
| Waiving a high finding | You, recorded as a deviation |
| Design-system changes a reviewer proposes | You |
| Accepting a trust-anchor notice | You, with your next message |
| Skipping a gate | You, recorded as a deviation |

**The agent's calls:**

| Decision | Owner |
|---|---|
| Track and risk | The agent proposes; you can override |
| Whether to ask before writing the record | The agent judges; it asks when what, why or how isn't clear |
| How the build runs (inline, parts, parallel) | The agent, written in the state file; on M and L shown at the approval |
| Which reviews to run on S | A fixed trigger list (`s-track.md` step 5); none unless one fires |
| Which reviews to run on autopilot and headless runs | The agent's recommendation |
| Verify verdict | The latest `verify.py` run on the current code |
| Fixing high findings, and one CI fix | The agent, without asking |
