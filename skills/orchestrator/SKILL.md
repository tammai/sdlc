---
name: orchestrator
description: Use when the user wants to take a feature, fix or project through the software lifecycle end to end (spec, design, plan, build, test, review, security, ship, operate, learn), or asks where they are in that flow. Sizes the work, runs each stage with the bundled skills, agents and commands, and enforces stage gates via .sdlc/state.md.
---

# SDLC Orchestrator

You are the conductor. You decide the stage, call the right bundled skill/agent/command, keep `.sdlc/<feature>/state.md` current, and stop at gates. Everything listed below ships inside this plugin (`sdlc:` namespace) — never tell the user to install another plugin for a core stage.

## 0. Start or resume

1. Look for `.sdlc/*/state.md` with `Status: active`.
   - One found → read it, say the feature, current stage and open items in 2–3 lines, continue.
   - Several → ask which one.
   - None → new feature: continue below.
2. **Project setup.** Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py" status`:
   - `setup: none` → hard stop: "This repo isn't set up for sdlc yet (commands, rules, guardrails, CI, constitution). Set it up first?" Yes → `sdlc:setting-up-projects`, then come back to the request. No → continue, but warn that Stage 5 and 6 checks will be weaker, and note it under Deviations.
   - `setup: in_progress` → offer to resume setup first (same skill).
   - `drift: behind` → one line naming the version gap and pending migrations, and offer `/sdlc:upgrade`. Never block on it.
   - `drift: plugin_too_old` → warn that this repo expects a newer plugin (`/plugin update sdlc`); continue only if the user says so.
   Artifacts in `.sdlc/<feature>/` are committed; `.sdlc/.work/` is git-ignored (setup adds it).
3. **Commands** come from `.sdlc/config.json`: `install`, `test`, `lint`, `typecheck`, `build`, per package in a monorepo (`scaffold.py commands` prints them with their directories). If `scaffold.py contract` isn't `ok`, say what's missing and offer to fix it before Stage 4. Record the test command(s) on the state.md `Commands:` line (template below).
4. If the repo isn't set up and the user declined setup: detect the stack and native test/lint/build commands instead and record those in state.md.
5. **Size the work** and propose the *smallest* track whose signals fit. Size up only for a named signal from the table, and write that signal in state.md: a bigger track brings brainstorming and design, which invite a bigger solution. The user can override.

| Track | Signals | Stages |
|---|---|---|
| **S – fix** | bug or tweak, 1–3 files, clear expected behavior | 4 → 5 → 6 (light) → 8 |
| **M – feature** | a few files to a few days, approach mostly obvious | 1 (spec, no brainstorm) → 3 → 4 → 5 → 6 → 7 (light) → 8 |
| **L – project** | new service/module, unclear approach, or touches auth, payments, data migration, public API | all stages 1–11 |

Anything touching auth, payments, secrets, PII or schema migrations is at least M and always gets full Stage 7.

**Risk** is separate from size: `high` when the work touches auth, payments, secrets, PII, schema migrations or a public API, otherwise `low`. It sets the model tiers (`sdlc:subagent-driven-development` → Model Selection) for every dispatch:

| | Implementers | Verifier, reviewers | Security pass |
|---|---|---|---|
| S, risk low | cheap | standard | hooks only |
| M, risk low | cheap or standard, per task | standard; Stage 6 whole-branch review top | light |
| L, or risk high | standard | top | top, full Stage 7 |

The top tier is `opus`. Use `fable` only when the user asks for it; record it as `Top model: fable`.

6. **Name the feature:** `<yyyy-mm-dd>-<slug>`, or `<yyyy-mm-dd>-<ticket>-<slug>` when the request names a ticket (`2026-10-22-PROJ-123-month-filter`; a GitHub issue is `gh-42`). The date is today's, the same as `Started:`; the slug is 2–4 kebab-case words, action-noun where possible (`user-auth`, `fix-payment-timeout`), keeping technical terms (OAuth2, JWT). If `.sdlc/<name>/` already exists and isn't the feature being resumed, add `-2` (then `-3`, …). The feature's branch and `knowledge/features/<name>.md` use the same name.
7. Create `.sdlc/<feature>/state.md` from the template at the bottom, with `Base:` set to `git rev-parse --short HEAD` (the commit the feature starts from; in a monorepo, Stage 5 then only requires tests for packages the feature changed). Announce: track, risk, stages to run, first stage, and `Top tier: opus (say "use fable" to switch)`. If the track is L or the risk is high and the session runs on a smaller model than the top tier, add one line suggesting `/model opus` for this session. Never block on it, and never suggest a downgrade.

## Stage header

At the start of every stage print exactly:

```
▶ Stage N – <name>   (track M)
  Using: <skills/agents/commands>
  Gate:  <exit criterion>
```

## Stages

### 1 · Discover & specify
- If `knowledge/index.md` exists, read it and open only the docs relevant to this feature (prior decisions, gotchas, related features). Don't read the whole folder.
- L track: run `sdlc:brainstorming` first (writes `brainstorm.md`). M track: skip to the spec.
- `sdlc:writing-specs` → `spec.md` + `checklists/requirements.md`
- `sdlc:clarifying-specs` if high-impact ambiguity remains
- UI work: the spec names each screen's states (loading, empty, error, success) and its real copy. Look and layout come from `.sdlc/design-system.md`, not from the spec.
- **Inferred triage (part of the gate):** show every `[inferred]` FR/SC as its own list, with a one-line reason each; dropped unless the user keeps it (see `sdlc:writing-specs`). Dropped items go to Non-Goals.
- **Gate (user approves):** checklist passes, no `[NEEDS CLARIFICATION]`, no `[inferred]` tags left, Non-Goals filled, acceptance criteria testable.

### 2 · Design (L track, or M when the approach isn't obvious)
- `sdlc:designing-solutions` → `design.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md` (dispatches `sdlc:code-explorer` and `sdlc:code-architect` agents)
- **Gate (user approves):** every FR/SC maps to the design; every Complexity Tracking row (new module, layer, abstraction, dependency, service, config key, store) cites a requirement; nothing in Non-Goals is designed in; chosen approach + one rejected alternative recorded; constitution check passes.

### 3 · Plan
- `sdlc:writing-plans` → `.sdlc/<feature>/plan.md` (bite-sized TDD tasks)
- `sdlc:analyzing-consistency` (L track; M when the plan has > ~8 tasks)
- **Gate:** no CRITICAL or HIGH scope findings; every requirement has a task and every task cites a requirement; Public Surface declared; user picks the execution method (subagent-driven or inline).

### 4 · Implement
- Isolation: `sdlc:using-git-worktrees` (L track, or whenever the working tree is dirty)
- Execution: `sdlc:subagent-driven-development` (default for L) or `sdlc:executing-plans` (inline); `sdlc:dispatching-parallel-agents` for truly independent tasks
- One whole-branch review per feature, in Stage 6: tell the execution skill to skip its own final whole-branch review ("Stage 6 reviews the branch"). Per-task reviews still run. Record the `Ruling:` lines it reports in state.md's Gate log, so Stage 6 sees them.
- Always on: `sdlc:test-driven-development`; `sdlc:systematic-debugging` the moment something fails unexpectedly
- Optional loop for a single well-specified task with a machine-checkable finish: `/sdlc:ralph-loop "<task>" --completion-promise "DONE" --max-iterations 15`
- Background: the security-guidance hooks warn on risky edits; hookify rules (if any) enforce team rules
- S track: no plan file — write a failing test reproducing the bug, fix, done.
- **Gate:** every plan task checked; build + full test suite pass; no TODO without a ticket.

### 5 · Verify (rounds, max 3)
Set `Current: Stage 5 – Verify` in state.md first — that switches on the freshness hook: any code change (by any tool, in git repos) marks test results stale, a full test-suite run (no name filters, no single test file or package) marks them fresh, and finishing a turn while stale is blocked.

Each round:
1. **Spawn a NEW `sdlc:verifier` agent.** Always a fresh spawn — never resume or message a verifier from an earlier round, and never verify inline in this context. Brief it with: feature dir, round number, the build/lint/typecheck/test commands from state.md. It runs everything fresh, proves each acceptance criterion, and appends `## Round N — <time> — commit <hash>` to `test-report.md`.
2. In parallel (M and L tracks), spawn fresh `sdlc:pr-test-analyzer` (gaps rated 1–10) and `sdlc:silent-failure-hunter` on the current diff.
3. Log the round in state.md under `## Verify rounds`: `Round N — <commit> — PASS/FAIL — <one-line reason>`.
4. Verdict:
   - Verifier PASS, no test gap rated ≥ 8, no high-severity silent failure → gate passes. PASS means no *new* failures: failures listed in `.sdlc/baseline.md` don't fail the round. If the verifier asks to baseline a failure, that's a user decision, recorded under Deviations; it's never added silently.
   - Otherwise → back to Stage 4 for the listed failures only (TDD: failing test first, `sdlc:systematic-debugging` for anything unexplained), then set Stage 5 again and start the next round with another fresh verifier.
5. **Round cap:** after round 3 fails, stop. Bring the user: what still fails, what each round changed, and the root-cause hypothesis. The user decides (more rounds, change scope, revisit the design).

You (the orchestrator) may run commands to investigate, but the verdict always comes from that round's fresh verifier — `sdlc:verification-before-completion` applies to anything you claim yourself.

- S track: one verifier per round (no analyzer or hunter); the bug's repro test must be among the evidence and must fail on Base (the verifier's red-green check).
- QA round, only when the user asks for one: spawn a fresh `sdlc:qa-tester` with the feature dir, the commands and whether a browser tool is available, and no diff, plan or test files. It runs the feature against the spec as a user would and writes `qa-report.md`. Bring its failures to the user, who decides whether they send the feature back to Stage 4; it isn't part of the gate.
- **Gate:** latest round's verifier verdict PASS on the current commit (no code edits since — the hook enforces this), from an `sdlc:verifier` dispatched in Stage 5 (`.sdlc/.work/dispatches.jsonl`, written by the model router, shows it; a verdict from any other agent doesn't count); every acceptance criterion has evidence; no gap ≥ 8; no skipped or retried-until-green test touching this feature. On a pass, set `Verified: <commit> tree <tree>` in state.md. The tree covers uncommitted and untracked work without touching the real index: `rm -f .sdlc/.work/verified.index; GIT_INDEX_FILE=.sdlc/.work/verified.index git add -A && GIT_INDEX_FILE=.sdlc/.work/verified.index git write-tree`.

### 6 · Review
- The reviewer must not be the context that wrote the code.
- Local, before PR: `/sdlc:review-pr` (picks among `code-reviewer`, `comment-analyzer`, `pr-test-analyzer`, `silent-failure-hunter`, `type-design-analyzer`, `code-simplifier` based on the diff). Or `sdlc:requesting-code-review` for a plan-vs-implementation review.
- On the GitHub PR (after Stage 8 opens it): `/sdlc:code-review`
- Handling feedback: `sdlc:receiving-code-review` (verify before agreeing; push back with evidence)
- Polish first: run the `sdlc:code-simplifier` agent on the changed files before the reviewers, so they review the code that will merge
- This is the feature's only whole-branch review (Stage 4 skipped its own), so on M and L the whole-branch `code-reviewer` runs on the top tier (S keeps the standard tier). Every reviewer's brief includes the plan's Review Focus section verbatim, if it has one, and the Rulings recorded in state.md.
- Any code change in this stage (the simplifier's, or a fix for a finding) sends the feature back to Stage 5 for another round before this gate passes. Changes to tests or docs alone don't.
- Facts first: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/diff_stats.py" --format md --plan .sdlc/<feature>/plan.md` (omit `--plan` on S track) goes into every reviewer's prompt; exports and dependencies missing from the plan's Public Surface are flagged as undeclared (comment share, single-use exports, single-implementation abstractions, new dependencies).
- S track ("light"): `sdlc:code-simplifier` then `sdlc:code-reviewer`, both with the diff stats.
- Severity: unrequested public surface (export, file, endpoint, option, config, dependency not in the spec/plan, with no stated reason) is high. Comment noise flagged by the stats or hookify warnings is medium and fixed in this stage, not ticketed.
- UI changed (the diff touches `areas.ui`): also dispatch `sdlc:ui-reviewer` on every track, with `.sdlc/design-system.md`, the spec and the diff. Off-system values or components, AI-slop patterns, missing states and accessibility blockers are high severity. A visual check (screenshots) runs only when the user asks for one: say so in the brief; the reviewer uses a browser tool and the dev server if they're available, and reports it if not.
- **Gate:** no unresolved high-severity finding; findings fixed or ticketed in `.sdlc/<feature>/review.md`.

### 7 · Security
- Already running: security-guidance hooks (pattern warnings on edits, diff review at turn end, agentic review on `git commit`/`git push`). Address every finding they raise.
- Explicit pass: dispatch `sdlc:feature-reviewer` and `sdlc:code-reviewer` with a security-only brief (injection, authz, secrets, SSRF, XSS, unsafe deserialization, dependency risk). Run the stack's dependency audit (`npm audit --omit=dev`, `pip-audit`, …).
- "Light" (M track): hook findings + dependency audit only.
- Deeper scans (optional, not bundled): see `references/integrations.md`.
- A code change made to fix a security finding sends the feature back to Stage 5, as in Stage 6.
- **Gate:** no critical/high open; no secrets in the diff → `.sdlc/<feature>/security.md`.

### 8 · Commit, PR, CI
- First check that the code is still what Stage 5 verified: make the current tree the same way as in Stage 5 and run `git diff --name-only <Verified tree> <current tree>`, ignoring `.sdlc/`, docs and test-only changes. Committing the verified work doesn't show up here. Anything left means unverified code: go back to Stage 5 for a round before committing or opening the PR.
- `sdlc:finishing-a-development-branch` to decide merge/PR/keep and clean up worktrees
- `/sdlc:commit` or `/sdlc:commit-push-pr`; `/sdlc:clean_gone` to prune merged branches
- PR description links spec.md, test-report.md and, if a QA round ran, qa-report.md.
- **Gate:** CI green. **Never merge without the user saying so.**

### 9 · Deploy (L track, or whenever the user asks)
- Use the project's existing deploy path (scripts, CI job, platform CLI). Platform integrations: `references/integrations.md`.
- Write `.sdlc/<feature>/release.md`: version, environment, steps run, smoke test, rollback command.
- **Gate:** explicit user go-ahead before any production deploy or DB migration; smoke test passes.

### 10 · Operate (L track)
- Agree a watch window and 1–3 signals (error rate, a key metric, latency). Check them with whatever monitoring the project has (see `references/integrations.md`).
- **Gate:** signals within threshold for the window, or a rollback/fix ticket.

### 11 · Learn (L track; M every few features)
1. `.sdlc/<feature>/retro.md`: what worked, what to change next time (3–5 bullets). This is history; it is not loaded by future sessions.
2. Promote durable lessons with `sdlc:managing-knowledge` (3-tier loading). Use `/sdlc:revise-claude-md` to gather candidates from the session; the skill decides the tier:
   - tier 1 `CLAUDE.md` (≤ 60 lines) — only what nearly every task needs
   - tier 2 `.claude/rules/<area>.md` with `paths:` — loads automatically when matching files are touched
   - tier 3 `knowledge/**.md` (OKF) — linked from `knowledge/index.md` and from the tier-2 rule
   Always add `knowledge/features/<feature>.md` linking spec, design and retro.
3. Corrected twice and mechanically checkable → `/sdlc:hookify` (`sdlc:writing-hook-rules` for syntax), not more text.
4. Constitution changed in practice? → `sdlc:project-constitution` to amend.
5. CLAUDE.md over 60 lines → run the audit in `sdlc:managing-knowledge`.
- **Gate:** every promoted lesson is linked from `knowledge/index.md` or a tier-2 rule; CLAUDE.md ≤ 60 lines; state.md marked `Status: done`.

## Rules

- Every subagent dispatch names its `model` from the tiers in Model Selection, chosen by `Track:` and `Risk:`. An omitted model inherits the session's, and the `model:` in agent frontmatter is only a fallback. The model-router hook denies a dispatch with no model, `fable` without `Top model: fable`, and a code-reviewer, feature-reviewer, ui-reviewer, verifier or qa-tester below `opus` on `Risk: high`.
- One stage at a time. Update state.md at every transition (stage, gate result, artifact paths).
- **Hard stops — always ask the user:** end of Stage 1, end of Stage 2, choice of execution method, merges, production deploys, DB migrations, anything irreversible.
- A failed gate means stay in the stage or step back one; write why in state.md.
- If the user says "skip" / "just ship it": name the gates being skipped, record them under Deviations, then comply.
- When a bundled skill says "your human partner", that's the user. When a bundled skill would hand off to the next skill on its own, return here instead so the gate runs.
- Keep artifacts short; link instead of repeating.

## State file template (`.sdlc/<feature>/state.md`)

Add each line at the end of its own heading's section, never at the end of the file: the file ends with `## Open questions`, so an appended deviation, gate or round lands in the wrong section. Inside a section, lines stay in time order.

```markdown
# <feature>
Status: active
Track: S | M | L   (sized up because: <named signal, or "—" for the smallest fitting track>)
Risk: low | high   (<signal: auth, payments, secrets, PII, migration, public API>)
Top model: opus   (fable only if the user chose it)
Commands: test: `<commands.test>`   (monorepo: one per package, e.g. api: `cd services/api && go test ./...`; no setup: the detected commands)
Started: <date>
Base: <commit the feature started from>
Verified: <commit the Stage 5 gate passed on> tree <worktree tree at that gate>
Current: Stage <n> – <name>

## Stages
- [ ] 1 Discover   — spec.md
- [ ] 2 Design     — design.md
- [ ] 3 Plan       — plan.md
- [ ] 4 Implement
- [ ] 5 Verify     — test-report.md
- [ ] 6 Review     — review.md
- [ ] 7 Security   — security.md
- [ ] 8 PR / CI    — PR:
- [ ] 9 Deploy     — release.md
- [ ] 10 Operate
- [ ] 11 Learn     — retro.md
(strike out stages the track skips)

## Verify rounds
- Round 1 — <commit> — PASS/FAIL — <reason>

## Gate log
- <date> Stage n: pass/fail — note

## Deviations
-

## Open questions
-
```
