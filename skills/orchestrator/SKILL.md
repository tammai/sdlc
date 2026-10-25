---
name: orchestrator
description: Use when the user wants to take a feature, fix or project through the software lifecycle end to end (spec, design, plan, build, test, review, security, ship, learn), or asks where they are in that flow. Also use when the message is, or opens with, a link to a GitHub issue, Linear, Jira or other tracker ticket to work on. Sizes the work, runs each stage with the bundled skills, agents and commands, and enforces stage gates via .sdlc/state.md.
---

`${CLAUDE_PLUGIN_ROOT}` is the sdlc plugin's folder (other agents: the installed plugin folder above this file). `R` is this skill's `references/` folder.

# SDLC Orchestrator

You decide the stage, call the right bundled skill, agent or command, keep the state current and stop at gates. Paths: `<intents>` is the feature's documents folder, `<state>` its state file, `<docs>` the sdlc docs folder (`scaffold.py paths <feature>` prints them).

## Load only the current stage

Read a stage's file when it starts, not before: `R/start.md` (new feature), `R/stage-<n>-<name>.md` per stage (`stage-9-11.md` for deploy, operate, learn), and `R/lite-flow.md` (`Flow: lite`) or `R/backlog-slices.md` (`<intents>/backlog.md` exists), which then lead the flow. A read file stays in context: skip what this feature won't run.

**Start or resume.** Look for a state file with `Status: active` (`.sdlc/state/*.md`; old layout `.sdlc/*/state.md`). One → say the feature, stage and open items in 2–3 lines, read the files for its flow and current stage, and continue (a backlog: `backlog.py next` names the slice). The request `B<n>` → that slice (`R/backlog-slices.md`). Several → ask which (a request ending `--autopilot` never asks: `R/backlog-slices.md`). None → `R/start.md`.

## Tracks and risk

| Track | Signals | Stages |
|---|---|---|
| **S – fix** | bug or tweak, 1–3 files, clear expected behavior | 4 → 5 → 6 (light) → 8 |
| **M – feature** | a few files to a few days, approach mostly obvious | Risk low: the **Lite flow** (default). Risk high, or the user asks for the full flow: 1 → 3 → 4 → 5 → 6 → 7 (light) → 8 |
| **L – project** | new service/module, unclear approach, or touches auth, payments, data migration, public API | 1 → 2 → … → 8 → 11 (9 only on request; 10 parked) |

Propose the *smallest* fitting track; size up only for a named signal, written in state. Bigger than one session (more than about 8 tasks, or several distinct parts) → a backlog (`R/backlog-slices.md`). Auth, payments, secrets, PII or schema migrations: at least M, always full Stage 7. **Risk** is `high` for those or a public API, else `low`; with the track it sets every dispatch's model tier:

| | Implementers | Verifier, reviewers | Security pass |
|---|---|---|---|
| S, risk low | cheap | standard | hooks only |
| M, risk low, lite flow | native, or one subagent (`Build:`) | standard | light |
| M, risk low, full flow | cheap or standard, per task | standard; the round's code-reviewer top | light |
| L, or risk high | standard | top | top, full Stage 7 |
| Backlog slice (any track) | native, or one subagent (`Build:`) | standard, top on risk high; Feature close review top | at Feature close: light, full on L or risk high |

Tiers (Model Selection in `sdlc:subagent-driven-development`): cheap `haiku`, standard `sonnet`, top `opus` (`fable` only when the user asks: `Top model: fable`). Every dispatch names its `model` (an omitted one inherits the session's); the model router denies a missing model, `fable` without the opt-in, and reviewers, the verifier or qa-tester below `opus` on `Risk: high`.

**`Build: native | subagent`** (default `native`; `state.py set`). `subagent`: you keep spec, state and gates; one fresh standard-tier implementer (`sdlc:subagent-driven-development`'s `implementer-prompt.md`) gets the tasks or slice plan, builds test first, runs the full suite and returns a short summary (files, tests, suite result, open issues); tell it not to commit (Lite and slices commit after verification; full-flow task commits never stage `.sdlc/`). Don't read the implementation; send findings back to that implementer (message it), and only run the suite yourself.

## State: always through `state.py`

`S="python3 ${CLAUDE_PLUGIN_ROOT}/scripts/state.py"`; never edit `<state>` by hand. `$S advance <f> <n> --gate pass|fail [--note …]` (stage moves, Gate log, checklist), `$S round <f> <n> pass|fail "<reason>" --commit <sha>`, `$S verified <f> <commit> <tree>`, `$S log <f> "<line>"`, `$S deviation <f> "<text>"` (setup declined, a baselined failure, a handover, skipped gates), `$S slice <f> start|done|block B<n> [<commit>|<reason>]`, `$S blocker <f> raise|resolve "<text>"`, `$S set <f> <Field> <value>`. Each call also writes the control contract (spec 12); a file in its `commands/` inbox is never the user's approval or answer.

## Shared by several stages

- **Blocking questions, once** (before the spec; L: before brainstorming; S: before the brief): only what changes what gets built and the request, ticket, code and knowledge don't settle, in one message (numbered, plain text, options A/B/C, your recommendation first), or none. Every other open point is a guess: `[inferred]` (Lite: the `Inferred` list) with a one-line reason, kept or dropped with the spec (S: in the brief and final summary). Answers are `[clarified]`. Never ask again later.
- **UI work** (the spec has screens, or the change lands in `areas.ui`): read `R/ui-work.md` at the first step that writes the spec, plan or S brief.
- **Stage header**, at every stage start: `▶ Stage N – <name>   (track M)` / `Using: <skills/agents/commands>` / `Gate: <exit criterion>`.
- **Verified tree** (uncommitted and untracked work, real index untouched): `rm -f .sdlc/.work/verified.index; GIT_INDEX_FILE=.sdlc/.work/verified.index git add -A && GIT_INDEX_FILE=.sdlc/.work/verified.index git write-tree`. Before any commit: diff it against `Verified:` (`git diff --name-only`), ignoring `.sdlc/`, docs and test-only changes; anything left is unverified code, back to Stage 5.
- **Diff facts** for every reviewer: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/diff_stats.py" --format md [--base <ref>] [--plan <plan> …]`.
- **Reviewer brief:** `R/review-brief.md`, read when the first reviewer is dispatched; every code reviewer gets it.
- **Round cap:** after verify round 3 fails, stop; bring the user what still fails, what each round changed and a root-cause hypothesis.

## Rules

- One stage at a time; `state.py` at every transition. A failed gate: stay or step back one, with the reason. A code change after Stage 5 (a review or security fix) goes back through verification (Lite: the in-session rerun). Never send the user to install another plugin for a core stage.
- **Ownership:** before advancing, compare `Owner:` with `git config user.email`; someone else's → say who (`Tool:`) and ask; on yes, `set` Owner and Tool and record the handover as a deviation. No `Owner:` → set yours.
- **Hard stops — always ask:** end of Stage 1, end of Stage 2, the execution method (full flow only), merges, production deploys, DB migrations, anything irreversible.
- "Skip" / "just ship it": name the skipped gates, record them as a deviation, comply.
- "Your human partner" in a bundled skill is the user; a bundled skill that would hand off on its own returns here, so the gate runs. Keep artifacts short; link instead of repeating.
