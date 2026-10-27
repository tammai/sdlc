# sdlc playbook

Situation-by-situation plays. Each says what to type, what the agent does, which files appear and where you decide. Concepts are in the [guidebook](guidebook.md); failures are in the [runbook](runbook.md).

A feature's documents go in `<docs>/intents/<feature>/` (`<docs>` is `docs/sdlc` unless setup chose another folder) and its state in `.sdlc/state/<feature>.md`. Feature names look like `2026-10-26-m-csv-export`: date, the track it started on, slug.

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
| Get out of failing verify rounds | [6](#6-verify-keeps-failing) |
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

1. **Define:** the agent sizes it S (bug, 1–3 files, clear expected behaviour) and writes no documents. It records two lines in the state file: `Intent:` (the bug and the expected behaviour) and `Repro: <test file> › <test name> | <command>` (the repro test, which `verify.py` treats as AC-001). No approval.
2. **Build:** one implementer subagent (`sonnet`, high effort) writes a failing test that reproduces the bug and records it failing with `verify.py red AC-001`, then the fix, then runs `verify.py`, and reports both results. The session doesn't write the fix itself.
3. **No Prove:** the fix was built and verified in one place. The passing `verify.py` run, with the repro test recorded red, is recorded as `Verified:` and the feature goes to Ship. A FAIL goes back to the implementer.
4. **Ship:** Learn files a lesson only if it isn't obvious from the code or the commit, then one commit on a feature branch (created off the default branch if needed). Nothing is pushed or merged; the agent reports the branch and commit without asking.

**You decide:** whether to push, open a PR or merge; ask for it. Anything that adds scope also stops it.

**If the bug is bigger:** the implementer stops with BLOCKED when the fix needs more than 3 files, touches auth, payments, secrets, PII or migrations, or the cause stays unclear. The feature moves to M and goes back to Define, which now needs your approval.

## 2. Add a feature (M track)

**Type:** `/sdlc:start add CSV export to the reports page`

1. **Define:** one exchange. `intent.md` (why, 2–3 approaches, the recommended one), `spec.md` (requirements, about 10 or fewer acceptance criteria numbered `AC-001` onward, non-goals, failure modes) and `plan.md` (it starts with `## Handoff to Build`: your decisions with their reasons, what was rejected, what was found in the code, what must not break; then 3–6 tasks, each with its files, first test, command and requirement, an `## Acceptance tests` table naming the test that proves each criterion, plus a Public Surface section listing everything new others can see). If the approach isn't obvious, `design.md` and its set come too.
2. **You approve once.** The message lists the three paths, each question that changes the build with its recommended answer already filled in, the recommended approach and the alternatives, every `[inferred]` item (each dropped unless you keep it), the tasks, the Public Surface, each acceptance criterion with its test (`manual` ones apart, with their reasons) and `Build: native`. Reply to change any of them: another approach, keep an inferred item, `Build: subagent`.
3. **Build:** native, from `plan.md`. Per acceptance criterion: the test, `verify.py red AC-nnn` to record it failing, then the code. `verify.py` once at the end runs the checks, every criterion's test and the drift check. Changes from the plan are written under its `## Deviations` with what, why and effect; they never stop the build, and the end of Prove lists them.
4. **No Prove** on `Flow: lite`: Build's passing `verify.py` is the evidence, recorded as `Verified:`, and the feature goes to Ship. No checker or reviewer runs; the security hooks still warn on risky edits.
5. **Ship:** Learn, then one commit on a feature branch, reported without asking. Push, PR and merge wait for you to ask.

Low-risk M work runs `Flow: lite`, as above. Say "use the full flow" to get `writing-specs` with its checklist, `writing-plans`, and a Prove round: one fresh code-reviewer on `opus` that reads each criterion beside its test and reviews with a one-pass brief (correctness, silent failures, test gaps and security basics) and a ui-reviewer on UI work. High findings go back to Build, fixed failing test first, then one re-verification (`verify.py`, and a fresh checker on any criterion that failed). At the approval you can answer "skip Prove" (`Prove: skip`): the feature then goes from Build to Ship like Lite (a security-touched change still gets Prove's security pass alone). High-risk M work always gets it, and so does a spec that needs a design decision the request doesn't settle. A change confined to 1–2 files with a settled approach stays M, with `Risk: high` and `Flow: full` if an L signal applies, and is built as one piece (1–3 tasks), never sliced; Define then writes the three files short, with no design or consistency check.

**What you see in Claude Code.** On M and L the main session stays thin and shows you what a kept-alive Define agent and Build agent hand it (their questions, status lines, the approval message verbatim); it writes Prove's checker briefs and spawns the checkers (on `opus`) itself, and goes by their VERDICT lines alone. Your reply goes to the agent, and a decision it settles lands under `## Handoff to Build` in `plan.md`, because the Build agent knows only what is written. S, autopilot and the other agents run in the session as before.

**Good habits:** state non-goals up front; answer the questions briefly; challenge any addition you didn't ask for at the approval, not after the code exists. Too big for one session? See [19](#19-a-big-feature-becomes-a-backlog).

## 3. Build a new service or module (L track)

**Type:** `/sdlc:start build an invoicing service with PDF output`

1. **Define**, `Flow: full`: `brainstorming` writes `intent.md` and asks you nothing: it recommends an approach with the alternatives beside it, and you pick in the approval. It may offer a browser visual companion (needs Node).
2. The design (`designing-solutions`) dispatches `code-explorer` and `code-architect` and writes `design.md`, `research.md`, `data-model.md`, `contracts/` and `quickstart.md`. Expect options: minimal, minimal plus one named extension, pragmatic. Minimal is recommended unless it fails a named requirement. `writing-plans` writes `plan.md`; `analyzing-consistency` checks every requirement has a task. One approval covers it all, with `Build: tasks`.
3. **Build:** a git worktree and a fresh implementer per task, with no review per task: Prove is the only review.
4. **Prove** (unless you chose `Prove: skip` at the approval): Build's `verify.py` run, the ac-checker, one top-tier code-reviewer with a one-pass brief (it covers silent failures and test gaps too), and full security when the change is security-touched, in one round; high findings go back to Build, then one re-verification.
5. **Ship:** Learn also writes `retro.md`. Deploy only when you ask ([10](#10-merge-and-deploy)).

**You decide:** Define's approval, merge, deploy, migrations.

## 4. Change something risky

Auth, payments, secrets, PII, schema migrations: the work is **at least M**, `Risk: high`, so it runs the full flow, and Prove runs **full security**. A security review runs only on such a **security-touched** change: `Risk: high`, or a diff touching `areas.sensitive` or `areas.migrations` in `.sdlc/config.json`. Keep those lists right: a sensitive path they miss gets no security review. On L the reviewers run on the top tier, and the model-router hook denies a cheaper one; on M they run on `sonnet`, and full security is a standard-tier pass.

1. While you build, the security hooks warn on risky edits and review the diff at turn end. The commit review runs after `git commit`: on a feature branch, build commits wait and are reviewed together once Prove starts. A feature's change that isn't security-touched gets no model review; it is recorded as reviewed. Address each finding, or acknowledge it with a reason.
2. Prove adds one more `code-reviewer` with a security-only brief (injection, authz, secrets, SSRF, XSS, unsafe deserialization, dependency risk), in the same round, plus the dependency audit. On a backlog this runs once, at feature close. If you chose `Prove: skip`, a security-touched change still gets this pass in Prove, alone.
3. Gate: no critical or high finding open, no secrets in the diff; written to `review.md`'s `## Security` section.
4. DB migrations and production deploys are hard stops. Say go explicitly.

Deeper scanners (Claude Security, Semgrep and others, not bundled): `skills/orchestrator/references/integrations.md`.

## 5. Resume or check status

- `/sdlc:status`: one line per feature (track · phase · last gate), open questions and deviations, and whether the repo's scaffold is behind the plugin. Changes nothing.
- `/sdlc:start` with no argument resumes the one feature with `Status: active`, in its phase. Several active: it asks which.

A new session needs no re-explaining: the state file and the three documents carry everything.

**Someone else's feature:** the state file names its `Owner:` and `Tool:`. Before advancing a feature you don't own, the agent asks, then records the handover as a deviation.

**Pause a feature:** tell the agent to pause it. It runs `state.py set <feature> Status paused`, so `/sdlc:start` stops picking it up. The trust anchor reports the change once ([21](#21-the-trust-anchor-stopped-me)). Ask it to set `active` again to resume. Don't edit the state file by hand.

## 6. Verify keeps failing

Each round judges a `verify.py` run on the current code: Build's, reused when nothing changed since, or a new one. A **new** checker (M: the code reviewer; L: an ac-checker) reads the tests each round. Rounds happen only in Prove, on M full, L and a backlog's feature close (S and M lite have none: a failing `verify.py` stays in Build). A feature planned before ADR 0013, with no `## Acceptance tests`, still gets a new verifier each round.

| Round | What happens |
|---|---|
| Fails | Back to Build: the agent fixes the listed failures, failing test first, `systematic-debugging` for anything unexplained, runs `verify.py`, then re-verifies in Prove without asking: a fresh checker on the criteria that failed |
| The same requirement fails in two rounds | It stops and brings you what still fails, what each round changed and a root-cause hypothesis |
| Round 3 fails | The same stop |

**A failure that existed before your change:** if `.sdlc/baseline.md` lists it, it doesn't fail a verifier round (features planned before ADR 0013); `verify.py` doesn't read the baseline yet, so on newer features it fails verify. If not, it's reported as new and the agent may ask to baseline it; that's your call, recorded as a deviation. Baseline items that now pass are removed automatically.

**"Could not verify within budget":** the verifier (old plans) and the qa-tester run every command that isn't the project's own with a 2-minute limit (a hook enforces it in Claude Code), and get 10 minutes per round. A criterion or scenario they couldn't settle in that time comes to you; it is never counted as passed. Run it yourself, or say how to make it quicker.

**A qa-tester scenario failed but the tests pass:** the tests prove something other than the spec. It's a finding like any other, fixed with a failing test that reproduces the steps. Only one that needs a new requirement comes to you. **"Not run":** the qa-tester lacked something it needed (a tool, a browser) and never installs anything. The reason is in `qa-report.md`: provide it, or check the scenario yourself. A scenario it couldn't work out how to run is a finding instead: the quickstart is missing a step.

**"Doesn't prove" a criterion:** the checker (on M the code reviewer) read the test and found it wouldn't catch the behaviour missing (it asserts too little, or something else). Make it assert the new behaviour; the change goes under the plan's `## Deviations`. A test that passes before its code exists is refused earlier, by `verify.py red` in Build. (Old plans: the verifier says this when the test also passes on `Base:`.)

**When it stops:** allow more rounds, narrow the scope, or revisit the design. Don't ask it to rerun until green: retried-until-green tests fail the gate.

## 7. The stop hook says "re-run tests"

Cause: you are in Prove (`Current: Stage 5`, or Stage 6 on `Flow: lite`) and code changed after the last full test run, or there hasn't been one. Fix: run the **full** suite: the `test` command from `.sdlc/config.json` (in a monorepo, the stale package's own, from its directory; the message names it), or the `test:` command in the state file. A filtered run, a single file or a single package doesn't count.

Changes under `.sdlc/`, `knowledge/`, `.claude/`, `docs/` or the sdlc docs folder, and `.md`, `.mdx`, `.txt` or `.rst` files, don't make results stale. A misbehaving hook: [runbook R4](runbook.md#r4-blocked-at-stop-with-re-run-tests).

## 8. Handle review feedback

Use `sdlc:receiving-code-review`: check each comment against the code before agreeing, push back with evidence when it's wrong, fix the rest.

| Source | Command |
|---|---|
| Local, before the PR | `/sdlc:review-pr` (picks agents for the diff; the comment, type and simplifier agents need the `sdlc-extras` plugin) |
| Plan versus implementation | Prove's code review, from the plan and spec |
| On the GitHub PR | `/sdlc:review-pr <PR number or URL>` |

Severity rules: unrequested public surface (an export, file, endpoint, option, config key or dependency not in the plan's Public Surface, with no stated reason) is **high**. Comment noise is **medium** and fixed in Prove, not ticketed. Other medium and low findings go to `review.md` as tickets.

## 9. Skip a gate deliberately

Say `skip` or `just ship it`. The agent will:

1. name the gates being skipped,
2. record them as a deviation in the state file,
3. comply.

Hard stops (push, PR, merge, production deploy, migrations, anything irreversible) still wait for your explicit word. Skipping a gate is allowed; skipping silently is not.

## 10. Merge and deploy

1. **Ship:** Learn and one commit on a feature branch first. On every track that's where it stops, with `Branch <name> kept (<commit>); say "merge" or "PR" to go further.`: ask for a push, PR or merge when you want one. The `finishing-a-development-branch.md` reference handles it and cleans up worktrees. The `commit-push-pr.md` reference opens a PR that links `spec.md`, `review.md` and, if the qa-tester ran, `qa-report.md`. `/sdlc:clean_gone` prunes merged local branches afterwards.
2. **CI must be green. The agent never merges without you saying so.**
3. **Deploy** is a separate request: `/sdlc:deploy [feature] [environment]`.
   - It warns if the feature hasn't reached Ship, and continues only on your word.
   - It uses the project's existing deploy path (scripts, a CI job, the platform CLI). None: it says so and stops.
   - Before production or a migration it shows the environment, version, steps, migration and rollback command, and waits for your yes. A routine staging deploy doesn't.
   - It runs a smoke test. A failure: it offers the rollback, and a production rollback needs another yes.
   - It writes `release.md` (version, environment, steps, smoke result, rollback) and commits it only if you ask.

## 11. Run an autonomous loop

This is the Ralph loop: one task repeated in the current session. For running a backlog's slices in fresh sessions, see autopilot ([20](#20-run-a-backlog-on-autopilot)).

It comes with the optional companion plugin: `/plugin install sdlc-extras@sdlc`, then restart. For one well-specified task with a machine-checkable finish:

```
/sdlc-extras:ralph-loop "Make all tests in tests/export pass" --completion-promise "DONE" --max-iterations 15
```

Always set `--max-iterations`. Cancel with `/sdlc-extras:cancel-ralph`. Use it inside Build only; Prove, where the track has one, still runs afterwards.

## 12. Turn a correction into a rule

If you've corrected the same thing twice **and** a pattern in a command, file edit, prompt or stop can catch it, write a hookify rule instead of more prose.

1. `/sdlc:hookify` with a description, or with no arguments to scan the session for candidates (with `sdlc-extras` installed, its `conversation-analyzer` agent does the scan).
2. Rules live in `.claude/hookify/<name>.md` (committed, team) or `.claude/hookify.<name>.local.md` (personal, git-ignored).
3. A rule has an `event` (`bash`, `file`, `stop`, `prompt`, `all`), an `action` (`warn` or `block`) and conditions. Syntax: the `sdlc:hookify` skill's `references/rule-syntax.md`.
4. With `sdlc-extras` installed, `/sdlc-extras:hookify-list` shows what's active and `/sdlc-extras:hookify-configure` turns rules on or off. Without it, edit `enabled:` in the rule file.

Start with `warn`. Move to `block` once the pattern has no false positives.

## 13. Keep always-loaded context small

- `CLAUDE.md` over about 60 lines: `/sdlc:managing-knowledge audit` proposes moves (file → tier, with a reason) and shows the line count before and after. Nothing is applied without your OK.
- After a feature, `/sdlc:managing-knowledge lessons` collects lessons from the session and files each in the right tier.
- Every call also carries every enabled plugin's skills, agents and commands. `/sdlc:context-diet` estimates the cost per source and, after your OK, turns off what this project doesn't use (this project only), including the standalone copies of plugins sdlc bundles. Personal skills can only be moved into the projects that use them; synced claude.ai plugins are managed in claude.ai. Check `/context` in a new session for the real numbers.
- Rule of thumb: tier 1 (`CLAUDE.md`) only what nearly every task needs; area guidance in tier 2 (`.claude/rules/` with `paths:`); everything else in tier 3, linked from `knowledge/index.md`.

## 14. Adopt sdlc in an existing repo

1. Install the plugin ([runbook](runbook.md#install)).
2. Commit or stash your work, then `/sdlc:setup`. It detects brownfield and works on a `sdlc/setup` branch, one commit per step.
3. **Commands:** it records the commands you already use (`pnpm test`, `make lint`, `./gradlew build`, …) in `.sdlc/config.json`, per package in a monorepo. A missing step stays `null`. It doesn't touch your manifest, dependencies or tooling. You approve the list.
4. **Baseline:** it runs them and records what already fails in `.sdlc/baseline.md`. Features are judged only on new failures. A failing install or build stops setup.
5. **Audit:** explorer agents draft conventions, gotchas from git history, decisions and per-area rules. You approve, edit or drop each item.
6. **Existing AI config** (long `CLAUDE.md`, `AGENTS.md`, Cursor rules, ADRs): one migration diff per source; originals stay unless you say delete.
7. **The rest:** rules, guardrails, lint snippets (only for a linter you already have), allowlist, constitution, a design system (UI projects only), knowledge. Two steps are asked first: adding the sdlc marketplace and `enabledPlugins` to `.claude/settings.json` so teammates are offered the plugin (skipped, and said so, when the session runs sdlc from a directory with `--plugin-dir` rather than the installed copy), and the context diet ([13](#13-keep-always-loaded-context-small)). Existing CI is left alone (it points out steps that differ from the recorded commands); a repo without CI is offered a workflow, and every repo the `sdlc-invariants` check.
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

1. Finish or pause in-flight features if you can; the upgrade warns if one is in Build or later.
2. `/sdlc:upgrade --dry-run` shows the plan: files added, regenerated, replaced, edited by you, deleted by you, no longer shipped, and migrations.
3. `/sdlc:upgrade` runs it on a `sdlc/upgrade-<from>-<to>` branch. A new CI workflow is asked about first. For each plugin file you edited you choose: **apply** the proposed merge, **skip** this time, or **keep mine** (the plugin stops managing it). An edited guardrail (`.claude/hookify/sdlc-*.md`) you apply yourself: Claude is blocked from editing the rules that constrain it.
4. Each migration is shown as a diff. Declined ones aren't asked again; `/sdlc:upgrade --revisit` brings them back.
5. PR or local merge. The repo now records the minimum plugin version, so teammates on an older plugin are told to update.

## 17. Remove sdlc from a repo

`/sdlc:eject` shows a dry run first. It removes the plugin's own files (generated rules, unedited guardrails, CI workflow and lint snippets, the allowlist, plugin-enablement and `.gitignore` entries it added, the sdlc block in `AGENTS.md`, the lock) and keeps `.sdlc/config.json`, the constitution, design system, knowledge, baseline, area rules and every feature's documents and state. Edited plugin files are asked about one by one. On a `sdlc/eject` branch it fixes imports that would point at deleted files, runs the verify commands, then asks PR or local merge. Uninstall the plugin afterwards (`/plugin uninstall sdlc`) if you're done with it.

## 18. Clean up finished features

Every feature keeps its documents folder. Old plans and reports describe code that has since changed, and agents searching the repo can be misled by them.

1. `/sdlc:prune` lists features marked done on the main branch 45+ days ago (`--older-than 90d` to change that), with the files that would go: `plan.md`, the slices' `plan-B<n>.md`, `test-report.md` (older features), `qa-report.md`, `review.md`, `checklists/`.
2. Pick which to prune. Intent, spec, design, retro and state stay, and so do `review.md` (its `## Security` section) and an older `security.md` on high-risk features.
3. It commits the deletions in one commit. Git history keeps everything.

## 19. A big feature becomes a backlog

Work with several distinct parts that won't fit one session, on M or L. Never on S, and never a change confined to 1–2 files.

1. **Define** writes `backlog.md` next to the three files: one row per vertical slice (`B1`, `B2`, …) with its requirements, acceptance criteria, dependencies and size. `plan.md` gives each slice an outline. You approve them all at once. The feature runs `Flow: lite` from here, whatever the track. On L or high-risk M, the approval message comes with a `Flow: full → lite` trust-anchor notice; your approval accepts it.
2. **Each slice:** the agent writes `plan-B<n>.md` (3–6 tasks), builds natively until `verify.py` passes, then commits it. No Prove per slice. Slices run back to back without asking.
3. **It stops** for a backlog change that adds scope, or at a hard stop (and in feature close's Prove, at the round cap or when a requirement fails in two rounds). To look at each slice, say so: it records `Slice gates: plan, commit` (either or both).
4. **Low context:** it stops at a slice boundary with `B<n> done (<commit>). Next: B<m> <title>. Run /clear, then /sdlc:start.` `/sdlc:start B<n>` runs a named slice once its dependencies are done.
5. **Feature close**, after the last slice: on every backlog, whatever its flow, one Prove round over the whole branch (every acceptance criterion, one top-tier code-reviewer, qa-tester, and full security when the branch is security-touched), unless you chose `Prove: skip`; then Ship with Learn, which keeps the branch until you say merge or PR.

Long backlog and you'd rather not `/clear` by hand: [20](#20-run-a-backlog-on-autopilot).

## 20. Run a backlog on autopilot

Autopilot runs each slice in a fresh headless Claude Code session, then feature close. It's opt-in and Claude Code only. It is not the Ralph loop ([11](#11-run-an-autonomous-loop)).

**Run, in a terminal at the repo root:**

```
python3 <plugin>/scripts/autopilot.py [--permission-mode <mode>] <feature>
```

The headless sessions need permission to edit files and run git, the project's commands and the plugin's scripts (`state.py`, `backlog.py`). Setup's allowlist covers only the project's own commands, so pass a `--permission-mode` or widen the allowlist. A session that is denied leaves its slice unchanged, and autopilot stops with `B<n> is still todo after its run`. The mode is handed to `claude` as given; autopilot never adds a permission-bypass flag.

Each session runs `/sdlc:start B<n> --autopilot`: it does one slice and ends, never asking. Anything that would ask (the round cap, a requirement failing twice, a scope change, a hard stop) marks the slice `blocked: <reason>` in `backlog.md` and adds an open question.

**It stops** on an open trust-anchor notice, a feature that isn't active, a blocked slice, nothing ready, a session that fails, a run that leaves its slice unchanged, or a feature close that doesn't reach Ship. It prints one JSON object naming the reason and the slices it ran. Fix the cause in a normal session (for a blocked slice, `/sdlc:start B<n>` and answer its question), then run the same command again.

**When it finishes,** feature close has run and kept the branch. To go further, say merge or PR in a normal session: `/sdlc:start`.

## 21. The trust anchor stopped me

The trust anchor watches what verification relies on. When something weakens it, the turn stops once with `⚠ Verification anchors changed: … Your next message accepts it.` The agent tells you what changed and why, and doesn't undo it on its own.

It reports, per active feature:

- `Track:` down, `Risk:` high → low, `Flow:` full → lite, `Prove:` run → skip, `Top model:` or `Base:` changed;
- a failing test added to `.sdlc/baseline.md`, or commands in `.sdlc/config.json` changed since `Base:`;
- `spec.md` edited after Prove started;
- skipping Prove, or leaving it with code changed since the last full test run (a checker, an ac-checker or on M the code reviewer, on a passing full run of the current code counts as Prove; on S, M lite and `Prove: skip`, that passing run alone);
- `verify records disagree`: `.sdlc/.work/verify.json` differs from the freshness hook's copy of the run, or is missing or damaged while the hook holds one;
- on `Flow: lite`, stopping outside Build and Prove with untested code;
- a feature stopping being active other than by finishing (a pause, a deleted state file);
- a damaged trust-anchor record.

**What to do:** read it. If the change is right, carry on: your next message accepts it. If not, say so and ask the agent to put it back.

A change that only adds checks (Track up, Risk low → high, Flow lite → full, Prove skip → run) shows `Stricter process: …` and doesn't stop you. On a backlog feature, leaving Lite still stops once.

Autopilot won't start a session while a notice is open; its JSON `stopped` reason quotes the notice. Read it, send any message in a normal session to accept it, then run autopilot again.

## Who decides what

**Hard stops.** The agent always stops and asks:

| Decision | Owner |
|---|---|
| Define's approval: approach, spec, plan (and backlog, design), `Build:` (not on S) | You |
| Anything that adds scope | You |
| What next after three failed verify rounds, or a requirement failing in two | You |
| Push, PR or merge (Ship asks on `Flow: full`, L and a backlog's feature close; on S and Lite it commits on a branch and you ask) | You |
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
| Verify verdict | The latest `verify.py` run on the current code and the latest fresh checker (on S, M lite and `Prove: skip`, `verify.py` alone; old plans: the latest fresh verifier) |
| Fixing findings and re-running verify below the round cap | The agent, without asking |
