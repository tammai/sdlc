# sdlc guidebook

What the plugin is, how it works, and where things live. For "what do I do when…", see the [playbook](playbook.md). For "something is broken", see the [runbook](runbook.md). Install is in the [README](../README.md).

## The idea

`sdlc` is one Claude Code plugin that takes a piece of work from request to shipped and learned-from. An **orchestrator** skill runs it: it sizes the work, runs one phase at a time (Define, Build, Prove, Ship), calls the bundled skills, subagents and commands for that phase, records progress in `.sdlc/state/<feature>.md`, and stops at **gates**. Nothing outside the plugin is needed for the core phases.

Four ideas carry the design:

1. **Smallest process that fits.** Work is sized S, M or L. The orchestrator picks the smallest track that fits and sizes up only for a named signal, because a bigger track brings brainstorming and design, which invite a bigger solution.
2. **Gates, not vibes.** Every phase has an exit criterion. A failed gate means stay in the phase or step back one. Most gates the orchestrator checks itself; a few are **hard stops** where you decide.
3. **Independent checking.** Build produces the evidence with `verify.py` (each acceptance criterion's test recorded failing before its code, then passing). On M full and L the context that wrote the code never judges or reviews it: a fresh checker subagent reads each test against its criterion (on M the one code reviewer does it in its review pass; on L an `ac-checker`), and review uses separate reviewer agents. S and M lite have no Prove: Build's passing `verify.py` is the evidence and goes to Ship ([ADR 0015](adr/0015-prove-only-where-it-pays.md)).
4. **Nothing stays in the conversation.** On M and L, Define writes everything the build needs into three files (`intent.md`, `spec.md`, `plan.md`), so a fresh agent can build from them alone. On S the state file's `Intent:` and `Repro:` lines are the whole hand-off ([ADR 0014](adr/0014-lighter-s-and-a-companion-plugin.md)).

## Project setup

Before the first feature, `/sdlc:setting-up-projects` prepares the repo once; `/sdlc:start` offers it when a repo isn't set up. See [sdlc_setup_phase.svg](diagrams/sdlc_setup_phase.svg).

**The project's commands.** Setup records the repo's own `install`, `test`, `lint`, `typecheck` and `build` commands in `.sdlc/config.json`, exactly as the team runs them (`pnpm test`, `go test ./...`, `make lint`, …); a step the repo doesn't have is `null`. Everything that runs them reads them from there, so nothing in the plugin is stack-specific. A monorepo lists `packages`, each with a path, a stack and its own commands, run from its directory; a polyglot repo is several packages with different stacks.

**It adds no tooling you didn't ask for.** Setup never changes the product's manifest or dependencies: no new fields (`bin`, `engines`, `packageManager`, scripts), no new linter, formatter or devDependency, and no tool installed without asking.

- **Greenfield** (no source yet): a short stack interview, then a proposal you approve. The ecosystem's own generator builds the skeleton, plus the test runner and one passing smoke test. A linter, toolchain pinning and extra manifest fields are separate choices in the proposal, off unless you say yes.
- **Brownfield** (existing code): the commands the repo already uses, shown to you before they're written; a **baseline** of what already fails; an audit (conventions, git-history gotchas, decisions, area rules) drafted by explorer agents and written only as you approve each batch; existing AI configs (long CLAUDE.md, AGENTS.md, Cursor rules, ADRs) migrated into the three knowledge tiers, one diff per source.
- **Common steps, both modes:** policy rules (`.claude/rules/sdlc*.md`); hookify guardrails; sdlc lint snippets, only for a linter the project already has; a permission allowlist for the project's commands; with your approval, the sdlc marketplace and `enabledPlugins` in `.claude/settings.json` so teammates are offered the plugin; with your approval, a context diet (`/sdlc:context-diet`) for this project; a CI workflow from the recorded commands (asked first if the repo already has CI); the sdlc block in `AGENTS.md` when another agent (Codex, Cursor, Antigravity) uses the repo; `.gitignore` entries; a constitution (with the default Simplicity principle); a design system (projects with UI); and the knowledge folder. The steps that write `.claude/` run only under Claude Code.

Setup runs on an `sdlc/setup` branch with one commit per step, resumes where it stopped, and ends by asking whether to open a PR or merge locally.

**Who owns which file.** Everything the plugin puts in a repo is tracked in `.sdlc/scaffold.lock.json` with a class that decides what an upgrade may do:

| Class | Examples | On upgrade |
|---|---|---|
| Generated | `.claude/rules/sdlc*.md` | regenerated |
| Seeded | `.claude/hookify/sdlc-*.md`, `.github/workflows/sdlc-verify.yml`, `sdlc-invariants.yml`, `.sdlc/ci/invariants.py`, `.sdlc/lint/*` | replaced only if you haven't edited it; otherwise you choose: merge, skip, or keep yours for good |
| Keyed merge | allowlist and plugin-enablement keys in `.claude/settings.json`, `.gitignore` lines, the `<!-- sdlc:begin -->` block in `AGENTS.md` | only the entries the plugin added; your text around the block is never touched |
| Yours | the commands in `.sdlc/config.json`, `CLAUDE.md`, constitution, design system, `knowledge/`, baseline, your own rules | changed only by migrations you approve |

Files named `sdlc-*` belong to the plugin; everything else is yours.

**Upgrades.** When the plugin is newer than the repo's scaffold, `/sdlc:start` and `/sdlc:status` suggest `/sdlc:setting-up-projects upgrade`, which never blocks your work. It runs on its own branch: regenerate, replace untouched files, walk you through edited ones, then apply versioned migrations one diff at a time (declined ones are asked again only with `--revisit`). The repo pins a minimum plugin version, so teammates on an older plugin get a warning. `/sdlc:setting-up-projects eject` removes what the plugin owns and keeps your work.

## Tracks

| Track | Use when | Phases |
|---|---|---|
| **S · fix** | bug or tweak, 1–3 files, clear expected behavior | Define writes no documents: a one-line `Intent:` and the `Repro:` test in the state file, with no approval; Build builds and verifies in one place; no Prove; Ship commits on a feature branch without asking |
| **M · feature** | a few files to a few days, approach mostly obvious; also any change confined to 1–2 files whose approach Define settles, even with an L signal (then `Risk: high`, `Flow: full`) | risk low: `Flow: lite` (default), Define, Build, Ship: no Prove, Build's passing `verify.py` goes to Ship; risk high or on request: `Flow: full`, all four, Prove with one checker: a code reviewer that also reads each AC beside its test |
| **L · project** | new service or module, several distinct parts, or an approach still unclear after Define; auth, payments, data migration or a public API is L only beyond 1–2 files | all four, with brainstorming and design in Define; `Flow: full`, with Prove |

Size is the footprint (how many files the change touches), recorded on the state file's `Track:` line; risk raises the review, not the number of pieces. Anything touching auth, payments, secrets, PII or schema migrations is at least M, with `Risk: high`, so it runs the full flow; a change confined to 1–2 files with a settled approach stays M and is built as one piece (1–3 tasks), never sliced. A security review runs only when the change is **security-touched**: `Risk: high`, or the diff touches `areas.sensitive` or `areas.migrations` in `.sdlc/config.json`. Then Prove runs full security and the commit gets a model review; any other change has only the always-on pattern hooks. You can override the size at any time.

**Skipping Prove.** On M full and L, Define's approval shows `Prove: run`; answer skip and it records `Prove: skip`, and the feature goes from Build to Ship like Lite, except that a security-touched change still goes to Prove for its full security review alone. The default is `run`, and autopilot or a headless run keeps it. The trust anchor watches the field: run → skip after it was set is a notice you accept once.

**Lite and full.** Every track has the same shape: one approval (none on S), one build, one Prove round on M full, L and a backlog's feature close (none on S, a single-session Lite feature or `Prove: skip`), one commit. On every track Ship commits on a feature branch and reports `Branch <name> kept (<commit>); say "merge" or "PR" to go further.` without asking. `Flow: lite` is the default for M with `Risk: low` and for any backlog feature, because evals showed the old full M flow costing several times the tokens and more approvals for the same hidden-test results ([ADR 0008](adr/0008-lite-flow-for-low-risk-m.md)). On Lite the orchestrator writes the spec and plan itself and there is no Prove: Build's passing `verify.py` goes to Ship ([ADR 0015](adr/0015-prove-only-where-it-pays.md)). On full, `writing-specs` (with a checklist) and `writing-plans` write them, and Prove runs one fresh read-only code-reviewer (`opus`) with a one-pass brief covering each AC's test beside its criterion, correctness, silent failures, test gaps and security basics; findings go back to Build, then one re-verification. There is no qa-tester on M full ([ADR 0012](adr/0012-enforced-prove-budget.md)). A Lite feature sizes up to full when the spec needs a design decision the request doesn't settle, or risk turns out high.

**Backlog slices.** M or L work with several distinct parts that won't fit one session (never a 1–2-file change) gets a `backlog.md` of vertical slices, approved with the other Define files; S never gets one. `plan.md` then outlines each slice. Each slice writes its `plan-B<n>.md`, builds natively, passes `verify.py`, and is committed; there is no Prove per slice. Slices run back to back without asking until the round cap, a backlog change that adds scope, or a hard stop; per-slice stops are opt-in (`Slice gates: plan, commit`). After the last slice, **feature close** runs one Prove round over the whole branch on every backlog, whatever its flow, unless `Prove: skip`, then Ship. When context runs low it stops at a slice boundary and names the next one; `/clear` then `/sdlc:start` picks it up (`/sdlc:start B<n>` for a named slice). **Autopilot** (`python3 <plugin>/scripts/autopilot.py <feature>` in a terminal, only when you ask) runs each slice and then feature close in a fresh headless Claude Code session, up to a kept branch; it stops on a blocked slice, a run that changed nothing, or a trust-anchor notice you haven't seen.

**Risk and models.** Risk is recorded apart from size: `Risk: high` for auth, payments, secrets, PII, schema migrations, a public API, or untrusted input reaching a shell, terminal, file path or database (S and M lite have no Prove, so no reviewer). Track and risk pick each subagent's model tier and Prove's checkers: the cheap and standard tiers are both `sonnet`, dispatched with `effort: high`; the top tier is `opus`. `haiku` is never used. Every code review is on `opus`, on every track and risk (an M feature's checker and the security reviewer included; the model router enforces it); the other reviewers, the verifier and the qa-tester run on `opus` only on L (the ac-checker stays on the standard tier). Fable is used only if you ask ("use fable"), which sets `Top model: fable`. The session's model is yours; the start announcement may suggest `/model opus` or `/model sonnet` once, never blocking. See [sdlc_tracks_full_stage_tree.svg](diagrams/sdlc_tracks_full_stage_tree.svg).

**Why Prove is bounded.** On planner-team eval rounds 8–10 the plugin took 4–7x the baseline's wall-clock time and about 6x its tokens, mostly from unbounded verifier and QA probing and from repeated fresh-verifier rounds, with no measured quality gain from that work. The target is at most 2x the time and 2.5x the tokens, with hidden-test results and blind-review defects held level. That is not yet evaluated ([ADR 0011](adr/0011-track-cost.md)). So S dispatched no checkers, M lite one verifier, M full one code review; every checker has a time budget and a probe cap; and a requirement that fails twice stops the loop and goes to you ([Verification](#verification)). In eval rounds 12–13 that budget, given as instructions only, was not followed: single commands ran 4–7 minutes, background runs were polled in loops, and M full's Prove still took 40–50 minutes with QA on the critical path. So a hook now enforces the per-command limit, and M full drops QA and the second verifier ([ADR 0012](adr/0012-enforced-prove-budget.md)). Most of what remained was Prove re-executing what Build had just done: the verifier rebuilt, reran the suite and checked out Base for red-green. So Build now proves each acceptance criterion with `verify.py`, and Prove reuses that run and only judges whether each test proves its criterion ([ADR 0013](adr/0013-build-proves-prove-judges.md)). The S-task eval then found quality equal to a plain run at 11.7x the tokens, so S and M lite dropped Prove, Prove became skippable on M full and L, and security reviews run only on security-touched changes ([ADR 0015](adr/0015-prove-only-where-it-pays.md)).

## The four phases

| Phase | Produces | Gate |
|---|---|---|
| Define | `intent.md`, `spec.md`, `plan.md` on M and L (S: `Intent:` and `Repro:` lines in the state file); `backlog.md` when sliced; on the full flow `checklists/requirements.md`; `design.md` and its set when a design runs | **You approve once** (not on S). No `[inferred]` tags left, acceptance criteria testable, every requirement has a task, the three files stand alone |
| Build | code, tests; each acceptance test's red record and a passing `verify.py` run (`.sdlc/.work/verify.json`); deviations written into `plan.md` | Every task done, `verify.py` passes (every AC's test recorded red and now passing, every drift recorded with what, why and effect), no TODO without a ticket |
| Prove (M full and L with `Prove: run`; max 3 failed rounds) | `review.md` (rounds, `## Tickets`, `## Fixed`, `## Security` when security-touched), `qa-report.md` (when the qa-tester runs); features started earlier keep `test-report.md` and `security.md` | `verify.py` passes on the current code (reused from Build or rerun) and a fresh checker passes every AC (M: the code reviewer; L: an ac-checker; features planned before ADR 0013: a fresh verifier PASS), every acceptance criterion has a test that failed before its code and passes now, or is `manual` with its reason, no unresolved high finding, no test gap rated 8+, security-touched: no critical or high security finding, no secrets in the diff |
| Ship, with Learn | `recurring-defects.md` lines (L: `retro.md`), one commit on a feature branch; every track reports it and stops there, and merge or PR waits for your word | Verified-tree check clean, Learn done, CI green. **Never merged without you saying so** |

**Define's three files** (M and L). `intent.md` is the why: the request verbatim, questions and answers, the approaches weighed, the chosen one and why, and how it works at design level (M: about a page; L: written by `brainstorming`). `spec.md` is the what: requirements and acceptance criteria, no files or tasks. `plan.md` is the how: it starts with `## Handoff to Build` (decisions with reasons, rejected options, facts found in the code, what must not break, the builder's choices, each risk with the check that proves it; anything you say that changes what gets built goes under Decisions, or it doesn't count), then tasks with their files, first test, command and requirement, plus `## Acceptance tests` (the test that proves each `AC-nnn`, or `manual` with a reason), Public Surface, UI mapping, Review Focus and Deviations. Reviewers read `intent.md` first. A change confined to 1–2 files with a settled approach (**one piece**) writes the same three files short: `intent.md` of about 40 lines, a Lite-shape `spec.md` and a `plan.md` of 1–3 tasks, with no design, consistency check or brainstorming, and an approval message under about 1,500 characters. **S** writes none of them: `state.py set` records `Intent:` (the bug and the expected behaviour, one line) and `Repro: <test file> › <test name> | <command>`, which `verify.py` reads as AC-001; with no plan, drift isn't checked, and with no Prove there is no `review.md`.

**Build** works from `plan.md` (a slice: `plan-B<n>.md`), never from memory, and proves its own work: per acceptance criterion it writes the test, records it failing with `verify.py red AC-nnn`, then writes the code, running only nearby tests; at the end it runs `verify.py` once (the verify plan, every AC's test, and plan drift), after at most one repeat loop (about 10 runs) over timing-sensitive tests, never a flakiness loop per task, and never a sleep loop waiting on a command. With Prove ahead it first checks its own diff against the checker's one-pass list and fixes what it finds, to save a Prove round; the fresh checker still judges. A proof that new code matches old on generated inputs has a budget of about 1,000 cases or 2 minutes, runs once in Build, and Prove doesn't rerun it unless the files it covers changed. With no Prove (S, Lite, `Prove: skip`) that passing run is recorded as `Verified:` and the feature goes to Ship; Prove's high findings come back here to be fixed. Drift never stops Build: each is recorded under `## Deviations` with What:, Why: and Effect:, and the end of Prove lists it. `Build:` is `native` (in the session), `subagent` (one fresh implementer) or `tasks` (subagent-driven development, one fresh implementer per task, no per-task review: Prove is the only review), taken from the track (S `subagent`, M `native`, L `tasks`) and shown in Define's approval; change it in your reply.

**Prove**, on M full and L, judges Build's evidence in one parallel round on one commit ([Verification](#verification)). **Relay.** In an interactive Claude Code session (`relay.md`). On M the main session is the maker: it does Define and Build itself, asks you directly, runs Prove from `prove.md` with the relay's brief and moves, and fixes Prove's highs itself ([ADR 0018](adr/0018-m-maker-in-the-main-session.md)). On L it stays thin: it reads `relay.md`, not the phase files, passes paths, runs `advance`, `round` and `verified`, and shows you what the agents hand it; kept-alive agents (`general-purpose`, resumed with `SendMessage`: a Define agent on `opus`, a Build agent per part on `sonnet`) do Define and Build, each ending its turn with a `DISPATCH:`, `ASK:`, `QUESTION:`, `STATUS:` or `DONE:` line. On both, only a checker judges Prove: the main session writes the checkers' briefs from fixed text plus paths (and the changed-file list), spawns them fresh (every code review on `opus`; on M one checker, a code reviewer, never resumed), and reads only the `VERDICT:` line that ends each report in `.sdlc/.work/findings/<feature>/`. It runs the round and advance moves from those lines before any report is opened. The maker fixes every high finding, never downgrades or waives one (a waiver is yours), and logs the round in `review.md` with the checkers' verdicts. The trust anchor gives a notice when a feature leaves Stage 5 while the latest round has a report that isn't PASS. L parts run one after another. S, autopilot, headless runs and Codex, Cursor and Antigravity keep the in-session flow ([ADR 0017](adr/0017-thin-main-session-and-stage-agents.md)). **Learn**, in Ship, is small: the defects Prove fixed go to `recurring-defects.md`, and a lesson is filed only when it isn't obvious from the code, the commit or the design.

Internally each phase keeps a stage number, because the hooks read it: `Stage 1 – Define`, `Stage 4 – Build`, `Stage 5 – Prove`, `Stage 8 – Ship`. A backlog slice rests at Stage 6 after its commit. A feature started under the old 11 stages resumes in the phase its number maps to ([ADR 0010](adr/0010-four-phases.md)). **Deploy** is not a phase: `/sdlc:deploy`, on request, uses the project's existing deploy path, asks your go-ahead before a production deploy or DB migration, runs a smoke test and writes `release.md`.

Each phase starts with a header:

```
▶ <Phase>   (track M, flow lite)
  Using: <skills/agents/commands>
  Gate:  <exit criterion>
```

The whole loop, with hard stops, is in [sdlc_orchestrator_decision_tree.svg](diagrams/sdlc_orchestrator_decision_tree.svg); each track (S, M lite, M full, L) phase by phase, with its skills, subagents, hooks and gates, is in [sdlc_full_flow.svg](diagrams/sdlc_full_flow.svg).

### Hard stops

The orchestrator always asks you before: Define's approval (not on S), anything that adds scope, the round cap (3 failed rounds), a requirement that fails in two rounds, any push, PR or merge (Ship commits on a feature branch on every track and reports it; the merge or PR waits for your word), production deploys, DB migrations, and anything irreversible. Everything else runs without asking, including failed verify rounds below the cap. Where an advisor is available, the orchestrator consults it once, before Ship's commit, only on a feature with no Prove (S, M lite, `Prove: skip`; after an independent Prove it adds little), and in Define only when stuck on a real decision the files can't settle. If you say "skip" or "just ship it", it names the gates being skipped, records them under Deviations in `state.md`, then complies.

## Scope tracing

Every phase ties additions back to a request:

- **Questions ride in the approval.** Define is one exchange: a question that changes what gets built comes in the approval message with a recommended answer already filled in (`[recommended]` in `intent.md`, `[clarified]` after your reply). Under the orchestrator `brainstorming` asks you nothing; the choice of approach is in the approval. Define asks first only when a wrong guess would mean rewriting most of the documents. Every other open point is a guess tagged `[inferred]`, which you keep or veto at the approval. `clarifying-specs` runs only when you ask.
- **Specs** tag each requirement `[user]`, `[clarified]` or `[inferred]` (Lite: an `Inferred` list) and have a Non-Goals section. At the approval, `[inferred]` items are listed on their own and **dropped unless you keep them**; dropped ones move to Non-Goals.
- **Designs** keep a Complexity Tracking table: every new module, layer, abstraction, dependency, service, config key or store cites a requirement or comes out.
- **Plans** tie each task to a requirement and declare a **Public Surface** (every new export, endpoint, command, config key, env var, dependency).
- **Review** runs `scripts/diff_stats.py --plan` to flag exports and dependencies missing from the Public Surface; unrequested public surface is high severity. Every reviewer also checks the spec's failure modes and the recurring-defects list (the plugin's seed plus the project's own). It's the feature's only whole-branch review, and simplifications are findings like any other.

## Verification

**The freshness hook.** While `state.md` says `Current: Stage 5 – Prove` (on `Flow: lite`, also Stage 6), Prove is the only phase with a hook that blocks you:

- any code change (by any tool, in a git repo) marks test results **stale**;
- a **full** test run, or a full `verify.py` run, marks them **fresh**. A run that names a test file, a pytest node id, a single Go package or a name filter doesn't count;
- finishing a turn while stale is blocked with "re-run tests".

The full run is the `test` command from `.sdlc/config.json`, with no extra arguments. In a monorepo freshness is per package: an edit under `services/api/` makes only `api` stale, and `cd services/api && <api's test command>` makes it fresh again; a file outside every package makes all of them stale. A root-level test command (e.g. `turbo run test`) counts for every package.

**Verify's records.** `verify.py` writes the freshness hook's copy of its own run (each AC's red record, a full run's tree and result) after every full or `red` run, beside its `.sdlc/.work/verify.json`, so a run counts whatever command spelling ran it (a subagent's `verify.py; git status` too). In Build and Prove the hook also keeps the copy itself. It recognises the plugin's `verify.py` as the command itself, optionally after `cd <dir> &&`, with redirects ignored and followed only by `| tail`, `| head`, `| grep`, `| cat` or `; echo …`, and copies `verify.json`'s entry for that run only when its tree is the current code; when the exit code is verify.py's own (nothing piped or echoed after it), the entry must agree with it. `verify.py status` lets Prove reuse the last run only when it passed, both records agree and the code hasn't changed since. A record that differs from the hook's copy is a trust-anchor notice. Codex, Cursor and Antigravity get the copy too (Codex and Antigravity commands arrive with `| cat` appended, which counts as a filter).

**The baseline.** Failures listed in `.sdlc/baseline.md` (recorded at brownfield setup) don't fail a round on a feature planned before ADR 0013: the verifier fails only on **new** failures, removes baseline items that now pass, and never adds any. `verify.py` doesn't read the baseline yet, so on newer features a baselined failure in the suite fails it ([spec 04 Known gaps](specs/04-verification.md#known-gaps)). Accepting a new failure into the baseline is your decision, recorded as a Deviation.

**The round.** Prove runs on M full and L with `Prove: run`, and on every backlog once, at feature close (unless `Prove: skip`). On the review-ready commit, the orchestrator runs `verify.py status`: it reuses Build's passing run, or reruns `verify.py` once in the session (a FAIL goes back to Build). Then it dispatches the track's checkers at once, each fresh:

| Track | AC checker | Code reviewer | Also | Security, when security-touched |
|---|---|---|---|---|
| M, `Flow: full`, either risk | none: the code reviewer does it | one, top, also reads each AC beside its test | ui-reviewer on UI | one, top |
| L | standard | one, top | ui-reviewer on UI | one, top |
| Feature close (every backlog) | standard, every AC | one, top, `Base..HEAD` | qa-tester; ui-reviewer on UI | one, top |

The one code reviewer on every track gets a one-pass brief (on M it also reads each AC beside its test and is M's only checker): correctness; silent failures; test gaps (a behaviour or failure mode the spec implies that no test would catch, rated 1–10, 8 or more is high); and security basics unless a security review runs. The `ui-reviewer` joins on a UI diff. The `ac-checker` reads each acceptance criterion beside the test `plan.md` names for it and says whether the test would catch the behaviour missing; it runs nothing. A `manual` criterion is read against the change and reported as "checked by reading, not by a test". The round goes to `review.md` (a feature started earlier keeps `test-report.md`): the verify result, the checker's line per AC, the `manual` ACs and every drift. A feature whose `plan.md` has no `## Acceptance tests` (planned before [ADR 0013](adr/0013-build-proves-prove-judges.md)) keeps the old round: a fresh `verifier` runs everything, proves each criterion and checks red-green on `Base:`. Security runs only when the change is security-touched (`Risk: high`, or the diff since `Base:` touches `areas.sensitive` or `areas.migrations`): one more `code-reviewer` with a security-only brief (top tier, like every code review), plus the dependency audit and the security hooks' findings in the session, all written to `review.md`'s `## Security` section.

**Bounded checks.** The verifier (old plans) and the qa-tester run every command that isn't the project's own with a 2-minute limit, and get 10 minutes each per round. In Claude Code the prove-budget hook enforces the limit for everyone in Stage 5: the command runs under `timeout 120` and is killed there (exit 124, "could not verify within budget"), and background runs, Monitor and the PowerShell tool are refused for it, so nothing is polled. The verifier's red-green run on Base has a per-test timeout, and a test that times out there counts as failing. Code reviewers are read-only: they read code and diffs and may run the project's test command, and a suspicion that needs a probe is a finding. Whatever they can't prove is "could not verify within budget": it goes to you and is never counted as passed. With a qa-tester in the round the verifier writes no probes; without one it writes at most 5, and the qa-tester at most 5 of its own. Probes prefer planted states and fixed kill points to repetition, repeat at most 5 times, and stop once a gap reproduces in an area. Probe scripts live in `.sdlc/.work/probes/` (verifier) or `.sdlc/.work/qa/` (qa-tester); a defect a probe found becomes a failing test in the project's suite before the fix.

**Fix in Build, then re-verify once.** Any high finding sends the feature back to Build, where all of them are fixed together, each with a failing test first, and `verify.py` passes again; medium and low go to `review.md` as tickets, and fixed high findings are listed under `## Fixed` in `review.md` for Learn. An AC whose test doesn't prove it gets a better test, recorded in `## Deviations`. Then one re-verification in Prove: `verify.py status` (Build's run, reused), and a fresh checker on the ACs that failed (only when one did). Old plans re-verify L and full-flow fixes with a fresh verifier. A re-verification that fails is fixed and checked again without asking you, with two stops: the same requirement failing in two rounds, and round 3 failing. Then the orchestrator brings you what still fails, what each round changed, and a root-cause hypothesis. You can ask for a QA round any time; outside Prove's rounds you decide what its failures mean.

## Building blocks

### Skills (`sdlc:` namespace)

| Group | Skills |
|---|---|
| Conductor | `orchestrator` |
| Set up | `setting-up-projects` (setup, upgrade, eject; `/sdlc:setting-up-projects` runs it; its `references/trimming-context.md` backs `/sdlc:context-diet`) |
| Specify and design | `brainstorming`, `writing-specs`, `clarifying-specs`, `designing-solutions`, `project-constitution` |
| Plan and build | `writing-plans`, `analyzing-consistency`, `subagent-driven-development`, `executing-plans`, `test-driven-development`, `systematic-debugging` |
| Check | `verification-before-completion` (requesting a review is a reference in `executing-plans`; the entry points are Prove, `/sdlc:review-pr`) |
| Ship and learn | `managing-knowledge` (with the CLAUDE.md quality check that was `claude-md-improver`), `writing-hook-rules`, `todo` |
| Orchestrator references (read when the flow needs them, not skills) | `using-git-worktrees.md`, `dispatching-parallel-agents.md`, `receiving-code-review.md`, `finishing-a-development-branch.md`, `commit-push-pr.md`, `clean-gone.md`, `github-pr-review.md` |

### Subagents

| Agent | Used for |
|---|---|
| `code-explorer`, `code-architect` | Define's design: trace existing code, propose architectures |
| `ac-checker` | Prove on L and feature close (on M the code reviewer does this): reads each acceptance criterion beside its test and says whether the test proves it; runs nothing, edits nothing but its report |
| `verifier` | Prove for features planned before ADR 0013 (no `## Acceptance tests`), or on request: fresh, independent verification, including red-green, within a time budget |
| `code-reviewer` | Prove on M full, L and feature close: the round's one code review, with the shared reviewer brief and a one-pass brief (correctness, silent failures, test gaps, security basics); again with a security-only brief when the change is security-touched |
| `qa-tester` | Prove at feature close, or on request: runs the feature as a user would, without reading the code |
| `ui-reviewer` | Prove on M full, L and feature close, when UI files change: design-system conformance, AI-slop styling, states, accessibility; screenshots on request |
| `sdlc-extras:comment-analyzer`, `sdlc-extras:type-design-analyzer`, `sdlc-extras:code-simplifier` | `/sdlc:review-pr`, chosen by the diff, when the `sdlc-extras` plugin is installed (skipped, and said so, otherwise) |
| `sdlc-extras:conversation-analyzer` | `/sdlc:hookify`: find behaviors worth preventing with hooks, when `sdlc-extras` is installed (otherwise the session does the analysis) |

### Commands

| Command | Does |
|---|---|
| `/sdlc:start [request]` | Start a feature, or resume the active one if the request is empty (`B<n>`: a named slice) |
| `/sdlc:setting-up-projects [what you're building]` | Set the repo up once (greenfield or brownfield); resumes if interrupted |
| `/sdlc:setting-up-projects upgrade [--dry-run] [--revisit]` | Bring the repo's scaffold up to the installed plugin version |
| `/sdlc:setting-up-projects eject` | Remove the plugin's files from the repo, keeping your work |
| `/sdlc:doctor` | Health check of the machine, the plugin and the repo, with a fix for each problem. Changes nothing |
| `/sdlc:status` | Setup state and version drift, then one line per feature: track, phase, last gate, open questions. Changes nothing |
| `/sdlc:deploy [feature] [environment]` | Deploy on request through the project's own deploy path, with your go-ahead before production or a DB migration |
| `/sdlc:prune [--older-than 45d]` | Delete the working files of merged, finished features; keeps intent, spec, design, retro and state. Asks first, one commit |
| `/sdlc:context-diet` | Propose turning off plugins and skills this project doesn't need, in `.claude/settings.local.json`, after you approve. Any repo, Claude Code only |
| `/sdlc:review-pr [PR number or URL]` | Local pre-PR review of the diff with the right agents for it, or a review of a GitHub PR (needs `gh`) |
| `/sdlc:commit`, `/sdlc:commit-push-pr`, `/sdlc:clean_gone` | Git helpers |
| `/sdlc:managing-knowledge lessons`, `/sdlc:managing-knowledge audit` | Promote lessons; keep always-loaded context small |
| `/sdlc:hookify` | Turn repeated corrections into rules |
| `/sdlc-extras:ralph-loop`, `/sdlc-extras:cancel-ralph`, `/sdlc-extras:ralph-help` | Optional self-iterating loop for one well-specified task (`sdlc-extras` plugin) |
| `/sdlc-extras:hookify-list`, `/sdlc-extras:hookify-configure`, `/sdlc-extras:hookify-help` | List, toggle and explain hookify rules (`sdlc-extras` plugin) |

### Hooks

| Hook | Events | Does |
|---|---|---|
| hookify | PreToolUse, UserPromptSubmit, Stop | Evaluates rules from `.claude/hookify.*.local.md` (personal, git-ignored) and committed `.claude/hookify/*.md` (team). Rules warn or block |
| security-guidance | UserPromptSubmit, PostToolUse, Stop | Pattern warnings on edits; a model review at turn end and after `git commit` only while a security-touched feature is active (or with `SDLC_SECURITY_REVIEW=always`), and after `git push`. During a feature, build commits before Prove are reviewed together with the next review-ready commit, and only a security-touched change gets the model review (any other is recorded as reviewed, no model call) ([spec 05](specs/05-security.md)) |
| verify-freshness | PostToolUse, PostToolUseFailure (Bash, PowerShell, edits), Stop | Stage 5 (on `Flow: lite`, also Stage 6): stale/fresh test tracking; Stages 4–5: its own copy of each `verify.py` run (which `verify.py` also writes itself), also inside a chained command, copied from `verify.json` when its tree is the current code, which Prove's reuse checks ([above](#verification)) |
| prove-budget | PreToolUse (Bash, PowerShell, Monitor) | In Prove (Stage 5): a Bash command other than the project's own (`.sdlc/config.json` commands) is rewritten to run under `timeout -k 5 120`, with the tool timeout at 130 s; one that can't take the prefix (loops, subshells, chained commands) is refused, as are `run_in_background`, Monitor and PowerShell for such commands; the project's own commands are untouched (with builtins like `cd` beside them and a pipe into a filter like `tail`; anything else chained after one is not one) |
| model-router | PreToolUse (Agent, Task) | While a feature is active: denies a dispatch that names no model or names `haiku`, asks for Fable without `Top model: fable`, or runs a reviewer, the verifier or the qa-tester below Opus on `Track: L`; logs every dispatch to `.sdlc/.work/dispatches.jsonl` |
| trust-anchor | Stop, UserPromptSubmit | Tells you when what verification trusts changes: Track, Risk, Flow, Top model, Base or Prove; new baseline failures; changed commands; the spec after Prove began; untested code leaving Prove (an ac-checker, or on M the code reviewer, on a passing full run of the current code counts as Stage 5, and on S, M lite and `Prove: skip` that passing run alone); a `verify.json` that disagrees with the hook's copy ("verify records disagree"). It blocks once; your next message accepts it. A change that only adds checks (Track up, Risk low → high, Flow lite → full, Prove skip → run) is shown without blocking, except Flow lite → full on a backlog feature |
| role-guard | PreToolUse (file tools) | Holds the plugin's agents to their role: reviewers (the `sdlc-extras:` ones too), the ac-checker and Define's code-explorer and code-architect can't edit files but their report under `.sdlc/.work/findings/`, the verifier writes only its report, the baseline, its red-green worktree and its probe scripts, the qa-tester can't read or search code. Bash stays open to them |
| SessionStart | SessionStart | Creates a Python environment for the security reviewer on first run |

The hooks find their Python through `bash hooks/sg-python.sh`, which skips the Microsoft Store `python3` stub; once it has found one, each hook's command in `hooks.json` starts that Python directly, one process fewer per hook (with `SDLC_HOOK_TIMES=1` it also logs each hook's time to `.sdlc/.work/hook-times.jsonl`: runbook R10a); `/sdlc:doctor`'s "hook python" check runs it. The `sdlc-extras` plugin adds the Ralph loop's Stop hook, active only while a `/sdlc-extras:ralph-loop` runs.

In Codex, Cursor and the Antigravity CLI, `hosts/hook.py` runs hookify, verify-freshness and trust-anchor on the agent's own hook events (in Codex, once you trust them in `/hooks`; see [spec 11](specs/11-multi-agent.md)).

## Where things live

```
.sdlc/
  config.json              the project's commands (per package in a monorepo) and overrides on the plugin's defaults (yours)
  scaffold.lock.json       what the plugin placed, versions, migrations (machine-only)
  baseline.md              known failures from before setup (yours)
  state/<feature>.md       track, phase, gate log, deviations, open questions, and the feature's Docs: folder
  state/<feature>.json, <feature>.events.jsonl   control contract for a runner or control app (git-ignored)
  lint/                    sdlc lint snippets your ESLint/Ruff config imports (seeded)
  ci/invariants.py         checks test reports, the baseline and specs of active features in CI (seeded)
  ci/contract-check.sh     the API contract check CI runs (multi-app repos that chose it; seeded)
  .work/                   scratch, git-ignored (verify record, freshness, dispatch log, trust anchor, QA runs)
docs/sdlc/                 docs_dir: the documents people read (default; setup asks when the repo publishes docs/)
  constitution.md          project principles (yours)
  design-system.md         the design system UI work follows (UI projects; yours)
  recurring-defects.md     defects Prove fixed, one line each: Learn adds, Define and reviewers read
  intents/<feature>/
    intent.md  spec.md  plan.md                       Define, M and L
    backlog.md  plan-B<n>.md                          backlog features
    design.md  research.md  data-model.md  contracts/  quickstart.md  checklists/   design and full flow
    review.md  qa-report.md                                                     Prove (older features: test-report.md, security.md)
    retro.md  release.md                              Ship (L), /sdlc:deploy
knowledge/                 tier 3, on-demand docs (index.md links everything)
.claude/rules/<area>.md    tier 2, loads when matching paths are touched (yours)
.claude/rules/sdlc*.md     plugin policy rules: workflow, code style, tests, migrations, sensitive areas, CI, UI (generated)
.claude/hookify/*.md       team hookify rules; sdlc-*.md are the plugin's guardrails (seeded)
.github/workflows/sdlc-verify.yml       CI generated from the commands in config (seeded)
.github/workflows/sdlc-invariants.yml   runs .sdlc/ci/invariants.py on pull requests and pushes (seeded)
CLAUDE.md                  tier 1, at most 60 lines (never touched by the plugin)
```

Each feature is named `<yyyy-mm-dd>-<s|m|l>-<slug>`, or `<yyyy-mm-dd>-<s|m|l>-<ticket>-<slug>` with a ticket (e.g. `2026-10-22-m-PROJ-123-month-filter`). The letter is the track it started on; a later size-up doesn't rename it. The branch uses the same name. Commit the state file and everything under `docs/sdlc/intents/<feature>/`. A repo set up before 1.7.0 keeps everything in `.sdlc/<feature>/` until `/sdlc:setting-up-projects upgrade` moves it; the hooks read both layouts meanwhile ([ADR 0006](adr/0006-split-sdlc-docs-from-machinery.md)).

### `state.md`

Resume depends on this file. The orchestrator looks for `.sdlc/state/*.md` with `Status: active`: one match resumes, several asks which, none starts a new feature.

```markdown
# <feature>
Status: active
Docs: <intents>   (this feature's documents folder)
Track: S | M | L   (sized up because: <named signal, or "—">)
Risk: low | high   (<signal: auth, payments, secrets, PII, migration, public API, untrusted input>)
Flow: lite | full   (lite: M with risk low unless you asked for full, or any backlog feature)
Prove: run   (M full and L: run | skip, your choice at Define's approval; autopilot or headless: run)
Build: native | subagent | tasks   (the track's default, shown at Define's approval)
Top model: opus   (fable only if you chose it)
Commands: test: `<test command>`   (monorepo: one per package; no setup: the detected command)
Started: <date>
Base: <commit the feature started from>
Owner: <git email of whoever advances it>
Tool: <claude-code | codex | cursor | antigravity>
Verified: <commit the Prove gate passed on> tree <worktree tree at that gate>
Slice: B<n>   Slice base: <commit>   Slice gates: none   (backlog features only)
Intent: <the bug and the expected behaviour, one line>   (S only)
Repro: <test file> › <test name> | <command>   (S only: AC-001 for verify.py)
Current: Stage 1 – Define   (then Stage 4 – Build, Stage 5 – Prove, Stage 8 – Ship)

## Stages            (1 Define, 4 Build, 5 Prove, 8 Ship)
## Verify rounds
## Gate log
## Deviations
## Open questions
```

The orchestrator writes this file once from the template, then never edits it by hand: `scripts/state.py` makes each change in one call and writes the control contract beside it ([spec 12](specs/12-control-contract.md)). Before advancing someone else's feature (`Owner:`), it asks and records the handover.

### Three-tier knowledge

| Tier | Where | Loads |
|---|---|---|
| 1 | `CLAUDE.md` (≤ 60 lines) | every session |
| 2 | `.claude/rules/<area>.md` with `paths:` | automatically, when matching files are touched |
| 3 | `knowledge/**.md` | on demand, via `knowledge/index.md` and links from tier 2 |

`retro.md` is history and is not loaded by later sessions. Learn files a lesson in the right tier only when the feature found one that isn't obvious from the code, the commit or the design. Something corrected twice and checkable by machine becomes a hookify rule instead of more text.

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

After changing commands or `ci`, run `/sdlc:setting-up-projects upgrade` so the generated CI workflow follows. Don't edit `.sdlc/scaffold.lock.json` by hand. Why it's designed this way: [ADR 0001](adr/0001-project-setup-upgrade-eject.md), [ADR 0002](adr/0002-record-the-repos-own-commands.md), [ADR 0005](adr/0005-greenfield-monorepo-layout.md), [ADR 0006](adr/0006-split-sdlc-docs-from-machinery.md), [ADR 0007](adr/0007-multi-tool-adapters.md); the `scaffold.py` reference is in the [runbook](runbook.md#setup-upgrade-eject-internals).

## Glossary

| Term | Meaning |
|---|---|
| Phase | Define, Build, Prove or Ship; each runs at one internal stage number (1, 4, 5, 8) that the hooks read |
| Gate | Exit criterion for a phase |
| Hard stop | A point where the orchestrator always asks you |
| Round | One verification pass in Prove: the verify evidence and a new AC checker each time (old plans: a new verifier); it stops after 3 fail |
| Stale / fresh | Whether test results predate the latest code change |
| Slice | One vertical piece of a backlog feature, built, verified with `verify.py` and committed on its own (Prove runs once, at feature close) |
| Feature close | The whole-branch Prove round and Ship after a backlog's last slice |
| Public Surface | Declared list of everything new that callers or users can see |
| Complexity Tracking | Design table that ties every addition to a requirement |
| Deviation | A gate you chose to skip, or another departure, recorded in `state.md` |
| Trust anchor | The hook that shows you changes to what verification trusts |
| Constitution | Project principles in `docs/sdlc/constitution.md`, checked in Define |
| Design system | `docs/sdlc/design-system.md`: the library, tokens, components and patterns UI work must use; checked by `ui-reviewer` |
| Project commands | `install`, `test`, `lint`, `typecheck`, `build` in `.sdlc/config.json`, per package in a monorepo |
| Baseline | Failures that existed before setup; Prove fails only on new ones |
| Scaffold version / drift | The plugin version a repo was set up or upgraded with; "behind" means `/sdlc:setting-up-projects upgrade` has work to do |
| Generated / seeded | Plugin files that upgrades regenerate / replace only while you haven't edited them |
| Migration | A versioned change to files you own, applied only with your approval |
