# sdlc guidebook

What the plugin is, how it works, and where things live. For "what do I do when…", see the [playbook](playbook.md). For "something is broken", see the [runbook](runbook.md). Install is in the [README](../README.md).

## The idea

`sdlc` is one Claude Code plugin that takes a piece of work from request to an open PR. An **orchestrator** skill runs it: it sizes the work, runs one phase at a time (Define, Build, Review, Ship), calls the bundled skills, subagents and commands for that phase, records progress in `.sdlc/state/<feature>.md`, and stops at **gates**. Nothing outside the plugin is needed for the core phases.

Its goal is the process, not code quality above plain Claude: a trustworthy record of each change, the same steps across a team, and easier review, onboarding and trace-back. Four ideas carry the design ([ADR 0020](adr/0020-sdlc-2-slim-process-core.md)):

1. **Intent before code.** Before any code, what, why and how are agreed and written down. The agent judges whether the request already makes them clear; if not, at any size, it asks, one question at a time. A bug is proven first, then its root cause found.
2. **The same record at every size.** Every change leaves two files: the change file for people (why, what must be true with each criterion's test, then what Review checked) and the feature's state file for the agent (where it stands, and how it's built: tasks, files, Public Surface, deviations). S fills each section in a few lines; M and L in full. A later session, a reviewer or a teammate months from now works from these two files alone.
3. **A builder like plain Claude.** The builder writes the code and its tests with no review agents during the build. `verify.py` checks that each acceptance criterion's test failed before its code and passes after it.
4. **Reviews the change needs, once.** After the build the agent recommends reviews from what actually changed. Each chosen review runs once, fresh: the code review on S and M is Claude Code's built-in `/code-review` (other agents, and L, use the plugin's reviewer), the rest on `opus`; its high findings go back to the builder.

## Project setup

Before the first feature, `/sdlc:setup` prepares the repo once; `/sdlc:start` offers it when a repo isn't set up. See [sdlc_setup_phase.svg](diagrams/sdlc_setup_phase.svg).

**The project's commands.** Setup records the repo's own `install`, `test`, `lint`, `typecheck` and `build` commands in `.sdlc/config.json`, exactly as the team runs them (`pnpm test`, `go test ./...`, `make lint`, …); a step the repo doesn't have is `null`. Everything that runs them reads them from there, so nothing in the plugin is stack-specific. A monorepo lists `packages`, each with a path, a stack and its own commands, run from its directory; a polyglot repo is several packages with different stacks.

**It adds no tooling you didn't ask for.** Setup never changes the product's manifest or dependencies: no new fields (`bin`, `engines`, `packageManager`, scripts), no new linter, formatter or devDependency, and no tool installed without asking.

- **Greenfield** (no source yet): a short stack interview, then a proposal you approve. The ecosystem's own generator builds the skeleton, plus the test runner and one passing smoke test. A linter, toolchain pinning and extra manifest fields are separate choices in the proposal, off unless you say yes.
- **Brownfield** (existing code): the commands the repo already uses, shown to you before they're written; a **baseline** of what already fails; an audit (conventions, git-history gotchas, decisions, area rules) drafted by explorer agents and written only as you approve each batch; existing AI configs (long CLAUDE.md, AGENTS.md, Cursor rules, ADRs) migrated into the three knowledge tiers, one diff per source.
- **Common steps, both modes:** policy rules (`.claude/rules/sdlc*.md`); hookify guardrails; sdlc lint snippets, only for a linter the project already has; a permission allowlist for the project's commands; sdlc and its companion plugins turned on in `.claude/settings.local.json`, this machine's file, never committed, so it isn't asked (companions such as `sdlc-extras` are listed in one line and added on request, and the companion skill Cloudflare's `security-audit` with its install command when it isn't installed, which sdlc never runs for you; a conflicting plugin such as superpowers is turned off for this repo only, with a warning, and spec-kit's files are reported, with removal asked); with your approval, a context diet (`/sdlc:context-diet`) for this project; a CI workflow from the recorded commands (asked first if the repo already has CI); the sdlc block in `AGENTS.md` when another agent (Codex, Cursor, Antigravity) uses the repo; `.gitignore` entries; a product doc (PRD: an existing one used as is, else drafted from a short interview or from the code with every guess marked "inferred, confirm", approved before it's written to `docs/sdlc/prd.md`); a constitution (with the default Simplicity principle); a design system (projects with UI); and the knowledge folder. The steps that write `.claude/` run only under Claude Code.

Setup runs on an `sdlc/setup` branch with one commit per step, resumes where it stopped, and ends by asking whether to open a PR or merge locally.

**Who owns which file.** Everything the plugin puts in a repo is tracked in `.sdlc/scaffold.lock.json` with a class that decides what an upgrade may do:

| Class | Examples | On upgrade |
|---|---|---|
| Generated | `.claude/rules/sdlc*.md` | regenerated |
| Seeded | `.claude/hookify/sdlc-*.md`, `.github/workflows/sdlc-verify.yml`, `sdlc-invariants.yml`, `.sdlc/ci/invariants.py`, `.sdlc/lint/*` | replaced only if you haven't edited it; otherwise you choose: merge, skip, or keep yours for good |
| Keyed merge | allowlist in `.claude/settings.json`, plugin-enablement keys in `.claude/settings.local.json`, `.gitignore` lines, the `<!-- sdlc:begin -->` block in `AGENTS.md` | only the entries the plugin added; your text around the block is never touched |
| Yours | the commands in `.sdlc/config.json`, `CLAUDE.md`, PRD, constitution, design system, `knowledge/`, baseline, your own rules | changed only by migrations you approve |

Files named `sdlc-*` belong to the plugin; everything else is yours.

**Upgrades.** When the plugin is newer than the repo's scaffold, `/sdlc:start` and `/sdlc:status` suggest `/sdlc:upgrade`, which never blocks your work. It runs on its own branch: regenerate, replace untouched files, walk you through edited ones, then apply versioned migrations one diff at a time (declined ones are asked again only with `--revisit`). The repo pins a minimum plugin version, so teammates on an older plugin get a warning. `/sdlc:eject` removes what the plugin owns and keeps your work.

### Setup with impeccable

A project with UI can hand its design work to the [impeccable](https://github.com/pbakaus/impeccable) skill, while sdlc keeps the record, the gates and the review verdict ([ADR 0021](adr/0021-impeccable-for-ui-design.md)). The choice is made in setup's `design-system` step and recorded as `design` in `.sdlc/config.json` (`builtin` or `impeccable`; no key means `builtin`).

```
/sdlc:setup
│
├─ detect … gitignore            (unchanged: commands, CI, rules, guardrails …)
│    └─ guardrails renders all sdlc-* guardrails, incl. sdlc-ui-hardcoded-values
│       (the mode isn't known yet)
│
├─ prd                            HARD STOP: approve the PRD
├─ constitution                   HARD STOP: approve it
│
├─ design-system                  (only if the project has UI)
│   ├─ 1. Recommend a mode from the PRD           HARD STOP: you choose
│   │      impeccable ← user-facing, no design system yet (web or native)
│   │      builtin    ← internal tool on a stock library, a design team's
│   │                   system, or offline / no third-party calls
│   │      + names impeccable.style's network call and the telemetry opt-outs
│   ├─ 2. scaffold.py design impeccable
│   │      ├─ records "design": "impeccable"
│   │      ├─ removes sdlc-ui-hardcoded-values (unchanged → deleted;
│   │      │   edited by your team → asks first)
│   │      └─ reports whether impeccable is installed
│   ├─ 3. Not installed → prints the install command, records builtin;
│   │      rerun the step once it is (sdlc never installs it)
│   ├─ 4. /impeccable init, told to read the PRD
│   │      └─ one round of product questions → PRODUCT.md, whose first line
│   │         links to the PRD (the PRD wins where they differ)
│   ├─ 5. Existing styles worth recording → /impeccable document → DESIGN.md;
│   │      none yet → DESIGN.md comes later, from impeccable's own process
│   └─ 6. docs/sdlc/design-system.md = a short pointer to DESIGN.md
│
├─ knowledge
└─ finalize                       HARD STOP: PR or local merge
```

What you end up with:

| File | Owner | Holds |
|---|---|---|
| `docs/sdlc/prd.md` | you | the product's source of truth |
| `PRODUCT.md` | impeccable | the design-relevant part, linking back to the PRD |
| `DESIGN.md` | impeccable | the design system, once a visual world exists |
| `docs/sdlc/design-system.md` | you | a pointer to `DESIGN.md` |
| `.sdlc/config.json` | you | `"design": "impeccable"` |
| `.claude/hookify/` | sdlc | every guardrail except `sdlc-ui-hardcoded-values`, whose job impeccable's detector hook does |

Each UI change afterwards:

| Phase | In impeccable mode |
|---|---|
| Define | `/impeccable shape`; you confirm the brief, which is copied into the state file's `## UI mapping` and its copy into the ACs |
| Build | built through impeccable; its detector hook reports after UI edits |
| Review | `sdlc:ui-reviewer` (opus) runs impeccable's `detect` and applies its `audit` checks (read from `reference/audit.md`) as evidence and writes the verdict; a missing `DESIGN.md` is Medium, not High |
| Ship | as usual |

impeccable missing when a step runs: the step says so in one line and runs builtin; `/sdlc:doctor` warns. A repo set up before 2.1 gets the same question from `/sdlc:upgrade` (migration `2.1.0-design-mode`); with no answer it stays builtin and nothing changes. Switch later with `scaffold.py design <mode>`, which also puts the UI guardrail back or takes it away.

## Tracks

| Track | Use when | Before the build | After the build |
|---|---|---|---|
| **S · fix** | a fix or tweak, 1–2 files, clear expected behaviour | the change file and the plan, a few lines each; no stop | the reviews a fixed trigger list names run (none by default), and it tells you |
| **M · feature** | a few files to a few days, approach mostly clear | the change file and the plan in full; you read and approve the change file | you pick from the recommended reviews |
| **L · project** | several distinct parts, or an approach still unclear | the same, with the interview run by `brainstorming` | you pick from the recommended reviews |

Every track runs the same four phases and leaves the same record; the track sets only the record's depth and where it stops for you. Size is the footprint (how many files the change touches), recorded on the state file's `Track:` line; the orchestrator proposes the smallest fitting track and sizes up only for a named signal. You can override the size at any time.

**Risk** is recorded apart from size: `Risk: high` for auth, payments, secrets, PII, schema migrations, a breaking change to a public API (removing or changing an exported signature, an HTTP endpoint, a CLI flag, or output the docs say programs read; adding a command, flag or field is `low`), or untrusted input reaching a shell, file path or database. It doesn't change the track; it feeds the review recommendation. A change is **security-touched** when `Risk: high`, or the diff touches `areas.sensitive` or `areas.migrations` in `.sdlc/config.json`: then a security review is recommended and the commit gets a model review; any other change has only the always-on pattern hooks.

**Models.** The build runs in your session on its model. Every review runs on `opus` at every size; the model router enforces it. Other dispatches use `sonnet` with `effort: high`; `haiku` is never used. Fable is used only if you ask ("use fable"), which sets `Top model: fable`. See [sdlc_tracks_full_stage_tree.svg](diagrams/sdlc_tracks_full_stage_tree.svg).

**Parts.** M or L work with several distinct parts that won't fit one session's context (never a 1–2-file change) gets a `backlog.md` of parts, approved with the other Define files; S never gets one. The state file's `## Tasks` outlines each part. Each part writes its `plan-B<n>.md`, is built, passes `verify.py` and is committed; parts run back to back without asking unless something adds scope or a hard stop comes up (per-part stops are opt-in: `Slice gates: plan, commit`). All parts land together: after the last one, **feature close** runs one Review over the whole branch, then Ship. When context runs low it stops at a part boundary and names the next one; `/clear` then `/sdlc:start` picks it up (`/sdlc:start B<n>` for a named part). **Autopilot** (`python3 <plugin>/scripts/autopilot.py <feature>` in a terminal, only when you ask) runs each part and then feature close in a fresh headless Claude Code session, taking Review's recommendation; it stops on a blocked part, a run that changed nothing, or a trust-anchor notice you haven't seen.

**Features started under 1.x.** A state file without `Process: 2` was started under sdlc 1.x. 2.0 can't run it: `/sdlc:start` says to finish it with sdlc 1.8.1 or archive it (`Status: done`), the hooks ignore it, and `/sdlc:upgrade` refuses until none is active.

## The four phases

| Phase | Produces | Gate |
|---|---|---|
| Define | the change file up to `## Review`, the state file's plan sections (and `backlog.md` for parts) | S: none, it says what it will do and goes on. M and L: **you approve once**. Every AC has a row in the change file's `## Acceptance tests`, out of scope is filled, the two files stand alone |
| Build | code, tests; each acceptance test's red record and a passing `verify.py` run (`.sdlc/.work/verify.json`); deviations written into the state file with `state.py deviation` | Every task done, `verify.py` passes (every AC's test recorded red and now passing, every drift recorded with what, why and effect) |
| Review | the change file's `## Review`: what was recommended and chosen, each review's verdict, the fixes, the tickets | `verify.py` passes on the current code; every chosen review's latest report ends `VERDICT: PASS`, or its highs are fixed (and re-verified) or waived by you; security-touched: no critical or high security finding, no secrets in the diff |
| Ship, with Learn | knowledge and `recurring-defects.md` lines, the final commit, the PR | Verified-tree check clean, Learn done, green locally and on CI (or you told what's red), PR open. **Never merged without you saying so** |

**Define's two files.** The change file, `docs/sdlc/changes/<feature>.md` (from `templates/change-template.md`), answers "why?" and "what must be true?" for a reader months later. `## Why`: the request verbatim, what the change is for and who it serves, why now, your own words where they matter. `## Decisions`: what was chosen and ruled out and why (on L the design too; there is no `design.md`), a bug's proof and root cause, and any proposals nobody asked for (dropped unless you keep them). Then acceptance criteria with ids (`AC-001` onward), and `## Acceptance tests`, the test that proves each one and a command that runs only it (`manual` with a reason when no test can); must-never-break lines; the failure modes that apply; and what's out of scope. Review adds `## Review` last; everything above it is fixed once Review starts. The state file's plan sections are the how, for the agent: how the build runs and why, the handoff, tasks naming their files, the Public Surface, and `## UI mapping` on UI work; `## Deviations` is written by `state.py deviation`. Each is written once, after the questions are settled.

**Asking.** If the request, a ticket, the code and `knowledge/` already say what, why and how, Define writes the files and goes on. If anything that would change what gets built is missing or ambiguous, it asks, one question at a time, each built on the last answer, and stops asking once it can write the files without guessing anything that matters. A bug gets a failing test (preferred) or exact steps first, then its root cause (`systematic-debugging`); the proving test becomes AC-001.

**Build** works like plain Claude, from the change file and the state file's plan sections. It writes every acceptance criterion's test, records them failing in one call (`verify.py red AC-001 AC-002 …`), then writes the code in batches, running only nearby tests; at the end it runs `verify.py` once (the verify plan, every AC's test, and plan drift). It works from the spec's must-never-break lines and failure modes too: a crash window in a write is must-fix when the spec says a killed process must not leave the system unusable. Drift never stops Build: each change from the plan is one `state.py deviation` line in the state file's `## Deviations`, "What: … Why: … Effect: …". How the build runs is Define's call, written in the state file: **inline** (default, this session), **parts in fresh sessions** (the work won't fit one context), or **parallel subagents** (only for truly independent parts).

**Review** is described [below](#review). **Ship** first runs **Learn**: a lesson goes into the right knowledge tier only when it isn't obvious from the code or the commit, linked from the Lessons filed line of the change file's `## Review`; each high finding fixed in Review that a reviewer could check next time gets a line in `recurring-defects.md`; nothing to learn is said in one line. Then `verify.py` green on that exact code, and one shell call that commits (code, tests, the change file and the state file, naming the record's path so `git blame` leads from a line to its why), pushes and opens the PR with git and `gh` (it links the change file); watch CI. CI red because of the code gets one fix, test first; still red, or red for a CI-only reason (a secret, a runner, a flaky test), and it tells you. It stops with the PR open: `PR <url> open, local and CI green; say "merge" to merge.` Without a remote it stops with the branch ready.

Internally each phase keeps a stage number, because the hooks read it: `Stage 1 – Define`, `Stage 4 – Build`, `Stage 5 – Review`, `Stage 8 – Ship`. A part rests at Stage 4 once committed. **Deploy** is not a phase: `/sdlc:deploy`, on request, uses the project's existing deploy path, asks your go-ahead before a production deploy or DB migration, runs a smoke test and writes `release.md`.

Each phase starts with a header:

```
▶ <Phase>   (track M, risk low)
  Gate: <exit criterion>
```

The whole loop, with hard stops, is in [sdlc_orchestrator_decision_tree.svg](diagrams/sdlc_orchestrator_decision_tree.svg); each track phase by phase, with its skills, subagents, hooks and gates, is in [sdlc_full_flow.svg](diagrams/sdlc_full_flow.svg).

### Hard stops

The orchestrator always asks you before: the build on high-risk M (approving the change file and the plan), the reviews on high-risk M (choosing from the recommendation), the same two on L when the agent's own checks leave a doubt (it reasons through them first and records why it went on: every requirement maps to an AC, no open questions, every decision settled by the request, spec, code or knowledge, nothing extra or irreversible), anything that adds scope, a reviewer and the builder disagreeing on a high finding, CI still red after one fix, merges, production deploys, DB migrations, and anything irreversible. Everything else runs without asking: a low-risk M shows its plan and builds (its Gate log says it wasn't stopped), and runs the reviews that fire, or none; interrupt at any time. The advisor, where the agent has one, is called only when the review step recommends it and it was chosen. If you say "skip" or "just ship it", it names the steps being skipped, records them under Deviations in `state.md`, then complies.

## Scope tracing

Every phase ties additions back to a request:

- **Proposals are dropped by default.** Define adds no hardening, options, config or tooling that neither the request nor an applicable failure mode calls for. Anything else it would add is listed under the change file's proposals not asked for and dropped unless you keep it.
- **The change file** has acceptance criteria a test can prove, each with its test, and an out-of-scope section.
- **The state file's plan sections** name each task's files and declare a **Public Surface** (every new export, endpoint, command, config key, env var, dependency). `verify.py` reports a changed file no task names as drift until it has a deviation line.
- **Review** runs `scripts/diff_stats.py --plan` to flag exports and dependencies missing from the Public Surface; unrequested public surface is high severity. Every reviewer also checks the spec's failure modes and the recurring-defects list (the plugin's seed plus the project's own).

## Verification

**`verify.py`.** Build's one command. `verify.py red AC-001 AC-002 …` records acceptance tests failing before their code; a test that passes, can't be found or can't run is refused, and then none of the batch is recorded. A passing full run prints the head and tree `state.py verified` takes. The full run (`verify.py` with no arguments) runs the project's verify plan (lint, typecheck, build, the full suite), each AC's test (from the change file's `## Acceptance tests`), and the drift check against the state file's tasks, Public Surface and deviations (a 1.x feature: `spec.md` and `plan.md`). `verify.py status` prints short JSON: Review and Ship reuse the last run only when it passed, both records agree and the code hasn't changed since (`reuse: true`).

**The freshness hook.** While `state.md` says `Current: Stage 5 – Review`, Review is the only phase with a hook that blocks you:

- any code change (by any tool, in a git repo) marks test results **stale**;
- a **full** test run, or a full `verify.py` run, marks them **fresh**. A run that names a test file, a pytest node id, a single Go package or a name filter doesn't count;
- finishing a turn while stale is blocked with "re-run tests".

The full run is the `test` command from `.sdlc/config.json`, with no extra arguments. In a monorepo freshness is per package: an edit under `services/api/` makes only `api` stale, and `cd services/api && <api's test command>` makes it fresh again; a file outside every package makes all of them stale. A root-level test command (e.g. `turbo run test`) counts for every package.

**Verify's records.** `verify.py` writes the freshness hook's copy of its own run (each AC's red record, a full run's tree and result) after every full or `red` run, beside its `.sdlc/.work/verify.json`, so a run counts whatever command spelling ran it. In Build and Review the hook also keeps the copy itself. It recognises the plugin's `verify.py` as the command itself, optionally after `cd <dir> &&`, with redirects ignored and followed only by `| tail`, `| head`, `| grep`, `| cat` or `; echo …`, and copies `verify.json`'s entry for that run only when its tree is the current code; when the exit code is verify.py's own (nothing piped or echoed after it), the entry must agree with it. A record that differs from the hook's copy is a trust-anchor notice. Codex, Cursor and Antigravity get the copy too (Codex and Antigravity commands arrive with `| cat` appended, which counts as a filter).

**The baseline.** `.sdlc/baseline.md` lists failures recorded at brownfield setup. `verify.py` doesn't read it yet: when only the test step fails and every failure is listed there, Build logs it and passes the gate ([spec 04 Known gaps](specs/04-verification.md#known-gaps)). Accepting a new failure into the baseline is your decision, recorded as a Deviation.

**Bounded commands.** In Review (Stage 5) the prove-budget hook (the name is kept from 1.x) runs every shell command other than the project's own under `timeout 120` and kills it there (exit 124, "could not verify within budget"); background runs, Monitor and the PowerShell tool are refused for such commands, so nothing is polled. Reviewers are read-only: they read code and diffs and may run the project's test command, and a suspicion that needs a probe is a finding.

## Review

Review starts from Build's passing `verify.py`; it doesn't rerun it unless the code changed.

1. **Recommend.** The agent looks at what actually changed (`diff_stats.py`: sensitive or migration paths, public interfaces, persisted data, UI files, size) and the spec's must-never-break lines, and recommends, each with a one-line reason:

   | Review | Recommended when |
   |---|---|
   | Security | security-touched, or untrusted input reaches a shell, file path or database |
   | Code, default | a declared Public Surface, a large diff (more than 5 source files or 300 added code lines), or L |
   | Code, high | `Risk: high`, or the spec names a crash mid-write or concurrent use as a failure mode |
   | UI | the diff touches `areas.ui`: always recommended |
   | Advisor | only where the agent has one, for a real judgment call the reviews can't settle |

   The code depth is the highest row that fires, from these facts, not judged. There's no lighter depth: `verify.py` already proves each acceptance test failed and now passes. A `manual` AC is checked by whichever review runs, or by the session when none does. Nothing fires (a low-risk M whose every AC was seen failing, then passing): no review, and the change goes from Build straight to Ship. At low risk what fires runs without asking; on high-risk M it stops and you pick another depth, or none; on L it runs them and stops only if it doubts the table fits. Autopilot and headless runs take the recommendation and log that they did.

   S doesn't use this table: it runs a fixed list and says what ran. Security when `Risk: high` or a changed path matches `areas.sensitive` or `areas.migrations`; UI when one matches `areas.ui`; code at default depth when the state file's Public Surface isn't `- none`; otherwise none.
2. **Run each chosen review once**, as a fresh agent on `opus`, never the context that wrote the code, all dispatched together. The code review is a `code-reviewer` with the shared brief at the chosen depth (low: correctness against each AC and must-never-break line; default: also silent failures, test gaps rated 1–10 with 8 or more high, simplifications and security basics; high: also a deeper pass on each failure mode). The security review is a `code-reviewer` with the security-only brief, plus the dependency audit and the security hooks' findings in the session. The UI review is the `ui-reviewer` with `design-system.md`, the spec and the diff. Each writes its report to `.sdlc/.work/findings/<feature>/`, ending `VERDICT: PASS` or `VERDICT: FAIL — <high ids>`.
3. **Act on the findings.** Each high goes back to Build, fixed with a failing test first, fixing the rule rather than the one instance; then `verify.py` again. Then the failed review runs again as the next round, 3 rounds at most; when round 3 still fails, the user decides (one more round, a waiver, or stop), and the review-rounds hook holds every edit and command until they reply. If the agent thinks a high is wrong, it brings you the finding and its case; a waiver is yours only. A medium or low that breaks an AC, a must-never-break line, the linked spec or a constitution rule is a high too, whatever the reviewer called it (the agent may raise a severity, never lower one); any other bug in code the change touched is fixed the same way, without asking; the rest become tickets in the change file's `## Review`.
4. **Record** `## Review` once, as the last section of the change file: what was recommended and why, what was chosen and by whom, each verdict, the high findings with their fixes, the tickets, the drift and `manual` ACs. Everything above it stays as Define wrote it; the trust anchor reports a change there. The end-of-Review message lists every deviation and `manual` AC, so you see them without opening the files.

The trust anchor gives a notice when a feature leaves Review without a passing full run of the current code, or while a review's latest report says `VERDICT: FAIL` that you didn't waive. You can ask for a QA round (`qa-tester`) any time; you decide what its failures mean.

## Building blocks

### Skills (`sdlc:` namespace)

| Group | Skills |
|---|---|
| Conductor | `orchestrator` |
| Set up | `setting-up-projects` (setup, upgrade, eject; its `references/trimming-context.md` backs `/sdlc:context-diet`) |
| Define | `brainstorming` (the interview on L, unless a written spec settles the design), `project-constitution` |
| Build | `test-driven-development`, `systematic-debugging` |
| Check | `verification-before-completion` (the review entry points are Review, `/sdlc:review-pr` and `/sdlc:code-review`) |
| Ship and learn | `managing-knowledge` (with the CLAUDE.md quality check that was `claude-md-improver`), `hookify` (with the rule syntax that was `writing-hook-rules`), `todo` |
| Orchestrator references (read when the flow needs them, not skills) | `using-git-worktrees.md`, `dispatching-parallel-agents.md`, `receiving-code-review.md`, `finishing-a-development-branch.md` |

### Subagents

| Agent | Used for |
|---|---|
| `code-explorer` | Brownfield setup's audit: trace existing code |
| `code-reviewer` | Review: the code review at default or high depth with the shared reviewer brief; the security review with the security-only brief |
| `ui-reviewer` | Review, when the diff touches UI files: design-system conformance, AI-slop styling, states, accessibility; screenshots on request |
| `qa-tester` | On request: runs the feature as a user would, without reading the code |
| `pr-test-analyzer`, `silent-failure-hunter` | `/sdlc:review-pr`, chosen by the diff |
| `sdlc-extras:comment-analyzer`, `sdlc-extras:type-design-analyzer`, `sdlc-extras:code-simplifier` | `/sdlc:review-pr`, chosen by the diff, when the `sdlc-extras` plugin is installed (skipped, and said so, otherwise) |
| `sdlc-extras:conversation-analyzer` | `/sdlc:hookify`: find behaviors worth preventing with hooks, when `sdlc-extras` is installed (otherwise the session does the analysis) |

### Commands

| Command | Does |
|---|---|
| `/sdlc:start [request]` | Start a feature, or resume the active one if the request is empty (`B<n>`: a named part) |
| `/sdlc:setup [what you're building]` | Set the repo up once (greenfield or brownfield); resumes if interrupted |
| `/sdlc:upgrade [--dry-run] [--revisit]` | Bring the repo's scaffold up to the installed plugin version |
| `/sdlc:eject` | Remove the plugin's files from the repo, keeping your work |
| `/sdlc:doctor` | Health check of the machine, the plugin and the repo, with a fix for each problem. Changes nothing |
| `/sdlc:status` | Setup state and version drift, then one line per feature: track, phase, last gate, open questions. Changes nothing |
| `/sdlc:deploy [feature] [environment]` | Deploy on request through the project's own deploy path, with your go-ahead before production or a DB migration |
| `/sdlc:prune [--older-than 45d]` | Delete the working files of merged, finished features; keeps the change file and state (1.x features: intent, spec, design, retro, and review on high risk). Asks first, one commit |
| `/sdlc:context-diet` | Propose turning off plugins and skills this project doesn't need, in `.claude/settings.local.json`, after you approve. Any repo, Claude Code only |
| `/sdlc:review-pr` | Local pre-PR review of the diff with the right agents for it |
| `/sdlc:code-review` | Review a GitHub PR (needs `gh`) |
| `/sdlc:commit`, `/sdlc:commit-push-pr`, `/sdlc:clean_gone` | Git helpers |
| `/sdlc:revise-claude-md`, `/sdlc:knowledge-audit` | Promote lessons; keep always-loaded context small |
| `/sdlc:hookify` | Turn repeated corrections into rules |
| `/sdlc-extras:ralph-loop`, `/sdlc-extras:cancel-ralph`, `/sdlc-extras:ralph-help` | Optional self-iterating loop for one well-specified task (`sdlc-extras` plugin) |
| `/sdlc-extras:hookify-list`, `/sdlc-extras:hookify-configure`, `/sdlc-extras:hookify-help` | List, toggle and explain hookify rules (`sdlc-extras` plugin) |

### Hooks

| Hook | Events | Does |
|---|---|---|
| hookify | PreToolUse, UserPromptSubmit, Stop | Evaluates rules from `.claude/hookify.*.local.md` (personal, git-ignored) and committed `.claude/hookify/*.md` (team). Rules warn or block |
| security-guidance | UserPromptSubmit, PostToolUse, Stop | Pattern warnings on edits; a model review at turn end and after `git commit` only while a security-touched feature is active (or with `SDLC_SECURITY_REVIEW=always`), and after `git push`. During a feature, build commits before Review are reviewed together with the next review-ready commit, and only a security-touched change gets the model review (any other is recorded as reviewed, no model call) ([spec 05](specs/05-security.md)) |
| verify-freshness | PostToolUse, PostToolUseFailure (Bash, PowerShell, edits), Stop | Stage 5 (Review): stale/fresh test tracking; Stages 4–5: its own copy of each `verify.py` run (which `verify.py` also writes itself), also inside a chained command, copied from `verify.json` when its tree is the current code, which Review's reuse checks ([above](#verification)) |
| prove-budget | PreToolUse (Bash, PowerShell, Monitor) | In Review (Stage 5; the name is kept from 1.x): a Bash command other than the project's own (`.sdlc/config.json` commands) is rewritten to run under `timeout -k 5 120`, with the tool timeout at 130 s; quick reads (`git status`/`log`/`diff`/`show`/`branch`/`remote`, `tail`, `head`, `cat`, `wc`, `ls`) run unwrapped and chain freely; Ship's one call (`ship.py` followed only by `git commit`, `git push`, `gh pr create`) runs whole; one that can't take the prefix (loops, subshells, two slow steps chained) is refused, as are `run_in_background`, Monitor and PowerShell for such commands; the project's own commands are untouched (with builtins like `cd` beside them and a pipe into a filter like `tail`; anything else chained after one is not one) |
| session-status | SessionStart | In a repo with `.sdlc/`: one line of context with the setup state, drift, the paths of a feature's change file, state file and work folder, the git remote, team rules and the active features, so Define and S need no `scaffold.py status` or `paths` call (Claude Code only; other agents run those) |
| model-router | PreToolUse (Agent, Task) | While a 2.0 feature is active: denies a dispatch that names no model or names `haiku`, asks for Fable without `Top model: fable`, or runs any review agent below Opus, at every size; logs every dispatch to `.sdlc/.work/dispatches.jsonl` |
| trust-anchor | Stop, UserPromptSubmit | Tells you when what verification trusts changes: Track, Risk, Top model, Base or Process; new baseline failures; changed commands; the change file above `## Review` (its criteria and tests) after Review began; a feature leaving Review without a passing full run of the current code, at every size, or while a review's latest `VERDICT: FAIL` isn't waived; a `verify.json` that disagrees with the hook's copy ("verify records disagree"). It blocks once; your next message accepts it. A change that only adds checks (Track up, Risk low → high) is shown without blocking |
| review-rounds | PreToolUse, UserPromptSubmit | After 3 review rounds whose latest verdict still fails (and you haven't waived it), denies every edit, command, subagent and skill but a reviewer's report and a test run, so the agent can only ask you: one more round, a waiver, or stop. Each message you send allows one more round; the highest round seen is kept, so deleting a report doesn't reset it |
| role-guard | PreToolUse (file tools) | Holds the plugin's agents to their role: reviewers (the `sdlc-extras:` ones too) and the code-explorer can't edit files but their report under `.sdlc/.work/findings/`; the qa-tester can't read or search code. Bash stays open to them |
| SessionStart | SessionStart | Creates a Python environment for the security reviewer on first run |

The hooks find their Python through `bash hooks/sg-python.sh`, which skips the Microsoft Store `python3` stub; once it has found one, each hook's command in `hooks.json` starts that Python directly, one process fewer per hook (with `SDLC_HOOK_TIMES=1` it also logs each hook's time to `.sdlc/.work/hook-times.jsonl`: runbook R10a); `/sdlc:doctor`'s "hook python" check runs it. The `sdlc-extras` plugin adds the Ralph loop's Stop hook, active only while a `/sdlc-extras:ralph-loop` runs.

In Codex, Cursor and the Antigravity CLI, `hosts/hook.py` runs hookify, verify-freshness, trust-anchor and review-rounds on the agent's own hook events (the last three act only on 2.0 features) (in Codex, once you trust them in `/hooks`; see [spec 11](specs/11-multi-agent.md)).

## Where things live

```
.sdlc/
  config.json              the project's commands (per package in a monorepo) and overrides on the plugin's defaults (yours)
  scaffold.lock.json       what the plugin placed, versions, migrations (machine-only)
  baseline.md              known failures from before setup (yours)
  state/<feature>.md       the agent's record: track, phase, the plan (tasks, Public Surface), gate log, deviations, open questions, and the path of the feature's change file
  state/<feature>/         the feature's work folder:
    backlog.md  plan-B<n>.md                          work split into parts (/sdlc:prune may delete the plans once merged)
    qa-report.md                                      when a QA round ran
    release.md                                        /sdlc:deploy
  state/<feature>.json, <feature>.events.jsonl   control contract for a runner or control app (git-ignored)
  lint/                    sdlc lint snippets your ESLint/Ruff config imports (seeded)
  ci/invariants.py         checks test reports, the baseline and active features' change files in CI (seeded)
  ci/contract-check.sh     the API contract check CI runs (multi-app repos that chose it; seeded)
  .work/                   scratch, git-ignored (verify record, freshness, dispatch log, trust anchor, QA runs)
docs/sdlc/                 docs_dir: the documents people read (default; setup asks when the repo publishes docs/)
  prd.md                   the product doc: problem, audience, goals, capabilities (yours)
  constitution.md          project principles (yours)
  design-system.md         the design system UI work follows (UI projects; yours)
  recurring-defects.md     defects Review found and Build fixed, one line each: Learn adds, Define and reviewers read
  changes/<feature>.md     the change file, the record for people: Define writes it, Review adds ## Review; kept
  intents/<feature>/       features from before sdlc 2.0: their intent, spec, plan and other documents
knowledge/                 tier 3, on-demand docs (index.md links everything)
.claude/rules/<area>.md    tier 2, loads when matching paths are touched (yours)
.claude/rules/sdlc*.md     plugin policy rules: workflow, code style, tests, migrations, sensitive areas, CI, UI (generated)
.claude/hookify/*.md       team hookify rules; sdlc-*.md are the plugin's guardrails (seeded)
.github/workflows/sdlc-verify.yml       CI generated from the commands in config (seeded)
.github/workflows/sdlc-invariants.yml   runs .sdlc/ci/invariants.py on pull requests and pushes (seeded)
CLAUDE.md                  tier 1, at most 60 lines (never touched by the plugin)
```

Each feature is named `<yyyy-mm-dd>-<s|m|l>-<slug>`, or `<yyyy-mm-dd>-<s|m|l>-<ticket>-<slug>` with a ticket (e.g. `2026-10-22-m-PROJ-123-month-filter`). The letter is the track it started on; a later size-up doesn't rename it. The branch uses the same name. Commit the state file, the change file `docs/sdlc/changes/<feature>.md` and the working files in `.sdlc/state/<feature>/` (`release.md` only if you want it); features from before sdlc 2.0 keep their documents in `docs/sdlc/intents/<feature>/`. A repo set up before 1.7.0 keeps everything in `.sdlc/<feature>/` until `/sdlc:upgrade` moves it; the hooks read both layouts meanwhile ([ADR 0006](adr/0006-split-sdlc-docs-from-machinery.md)).

### `state.md`

Resume depends on this file. The orchestrator looks for `.sdlc/state/*.md` with `Status: active`: one match resumes, several asks which, none starts a new feature. One without `Process: 2` was started under 1.x: it says to finish it with sdlc 1.8.1 or archive it.

```markdown
# <feature>
Status: active
Process: 2
Change: <change>   (this feature's record for people)
Track: S | M | L   (sized up because: <named signal, or "—">; footprint: <n> files)
Risk: low | high   (<signal: auth, payments, secrets, PII, migration, public API>)
Top model: opus   (fable only if you chose it)
Commands: test: `<test command>`   (monorepo: one per package; no setup: the detected command)
Started: <date>
Base: <commit the feature started from>
Owner: <git email of whoever advances it>
Tool: <claude-code | codex | cursor | antigravity>
Verified: <commit> tree <worktree tree at the last passing verify>
Slice: B<n>   Slice base: <commit>   Slice gates: none   (work split into parts only)
Current: Stage 1 – Define   (then Stage 4 – Build, Stage 5 – Review, Stage 8 – Ship)

## Stages            (1 Define, 4 Build, 5 Review, 8 Ship)
## How the build runs   (Define: inline, parts in fresh sessions or parallel subagents, and why)
## Handoff             (what the builder needs and wouldn't find in the code)
## Tasks               (numbered, each naming its files and ACs)
## Public Surface      (what the change adds that others can see, or - none)
## UI mapping          (UI work only)
## Gate log
## Deviations          (state.py deviation: "What: … Why: … Effect: …")
## Open questions
```

It is the agent's record of the change, beside the change file for people. The orchestrator writes this file once from the template and fills its plan sections once in Define, then never edits it by hand: `scripts/state.py` makes each change in one call and writes the control contract beside it ([spec 12](specs/12-control-contract.md)). Before advancing someone else's feature (`Owner:`), it asks and records the handover.

### Three-tier knowledge

| Tier | Where | Loads |
|---|---|---|
| 1 | `CLAUDE.md` (≤ 60 lines) | every session |
| 2 | `.claude/rules/<area>.md` with `paths:` | automatically, when matching files are touched |
| 3 | `knowledge/**.md` | on demand, via `knowledge/index.md` and links from tier 2 |

Learn, before the final commit, files a lesson in the right tier only when the feature found one that isn't obvious from the code or the commit, and links it from the Lessons filed line of the change file's `## Review`, so it ships in the same PR. A decision later features must follow (a library, a data shape, a boundary) becomes a record in `knowledge/decisions/`, which Define treats as a constraint. Something corrected twice and checkable by machine becomes a hookify rule instead of more text.

### Configuration

Setup writes `.sdlc/config.json`; it's yours to edit and holds only what differs from the plugin's defaults (`templates/project/config.defaults.json`, deep-merged, your values win, lists replace). Most teams only touch it to change a command.

| Key | Meaning |
|---|---|
| `commands` | `install`, `test`, `lint`, `typecheck`, `build` as the team runs them. `null` means the step doesn't apply |
| `packages` | Monorepo instead of `commands`: `[{"name", "path", "stack", "commands"}]`, each run from its path. A root `commands.test` (e.g. `turbo run test`) counts for every package |
| `project.kind` | `greenfield` or `brownfield`, set by setup |
| `project.profile`, `project.owners` | Multi-app repos: `lean` or `large` (the answer to "who works here"), and for `large` the CODEOWNERS entries (`{pattern: [handles]}`, in order) |
| `api_contract` | Multi-app repos with the contract check: `{"path", "spec"}` of the versioned API contract |
| `docs_dir` | Where the sdlc documents live (default `docs/sdlc`; `.sdlc` or another in-repo folder if `docs/` is published as a site). Without it a repo is on the old all-in-`.sdlc/` layout |
| `contract.required` | The commands every package must list, `null` allowed (default all five) |
| `verify.order` | Order of the verify steps (default lint, typecheck, build, test) |
| `areas.*` | Path patterns for the policy rules and reviewers: `source`, `ui`, `tests`, `migrations`, `sensitive`, `ci` |
| `ci` | `os` matrix (default `["ubuntu-latest"]`; add `"windows-latest"` if teammates develop on Windows) and toolchain versions (`node_version`, `java_version`, `dotnet_version`, `oasdiff_version`) for the generated workflow |
| `baseline` | Where the known-failures baseline lives (default `.sdlc/baseline.md`) |
| `min_plugin_version` | Teammates on an older plugin get a warning to update |

After changing commands or `ci`, run `/sdlc:upgrade` so the generated CI workflow follows. Don't edit `.sdlc/scaffold.lock.json` by hand. Why it's designed this way: [ADR 0001](adr/0001-project-setup-upgrade-eject.md), [ADR 0002](adr/0002-record-the-repos-own-commands.md), [ADR 0005](adr/0005-greenfield-monorepo-layout.md), [ADR 0006](adr/0006-split-sdlc-docs-from-machinery.md), [ADR 0007](adr/0007-multi-tool-adapters.md); the `scaffold.py` reference is in the [runbook](runbook.md#setup-upgrade-eject-internals).

## Glossary

| Term | Meaning |
|---|---|
| Phase | Define, Build, Review or Ship; each runs at one internal stage number (1, 4, 5, 8) that the hooks read |
| Gate | Exit criterion for a phase |
| Hard stop | A point where the orchestrator always asks you |
| Stale / fresh | Whether test results predate the latest code change |
| Part (slice) | One piece of work too big for one session, built, verified with `verify.py` and committed on its own; all parts land together |
| Feature close | The one Review over the whole branch, and Ship, after the last part |
| Record | the change file for people and the state file for the agent, both kept for good |
| `Process: 2` | The state-file line that marks a 2.0 feature; the hooks act only on those |
| Public Surface | Declared list of everything new that callers or users can see |
| Deviation | A step you chose to skip, or another departure, recorded in `state.md` with `state.py deviation` (Build's drift too) |
| Trust anchor | The hook that shows you changes to what verification trusts |
| Constitution | Project principles in `docs/sdlc/constitution.md`; breaking a MUST rule is a high review finding |
| Design system | `docs/sdlc/design-system.md`: the library, tokens, components and patterns UI work must use; checked by `ui-reviewer`. In impeccable mode (`design` in `.sdlc/config.json`, chosen at setup) it points at impeccable's `DESIGN.md`, Define plans UI with `/impeccable shape`, impeccable builds it, and `ui-reviewer` adds impeccable's `detect` and `audit` as evidence |
| Project commands | `install`, `test`, `lint`, `typecheck`, `build` in `.sdlc/config.json`, per package in a monorepo |
| Baseline | Failures that existed before setup, listed in `.sdlc/baseline.md` so they don't block new work |
| Scaffold version / drift | The plugin version a repo was set up or upgraded with; "behind" means `/sdlc:upgrade` has work to do |
| Generated / seeded | Plugin files that upgrades regenerate / replace only while you haven't edited them |
| Migration | A versioned change to files you own, applied only with your approval |
