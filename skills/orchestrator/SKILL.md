---
name: orchestrator
description: Use when the user wants to take a feature, fix or project through the software lifecycle end to end (define, build, prove, ship, learn), or asks where they are in that flow. Also use when the message is, or opens with, a link to a GitHub issue, Linear, Jira or other tracker ticket to work on. Sizes the work, runs each phase with the bundled skills, agents and commands, and enforces phase gates via .sdlc/state.md.
---

`${CLAUDE_PLUGIN_ROOT}` is the sdlc plugin's folder (other agents: the installed plugin folder above this file). `R` is this skill's `references/` folder.

# SDLC Orchestrator

You decide the phase, call the right bundled skill, agent or command, keep the state current and stop only at hard stops. Paths: `<intents>` is the feature's documents folder, `<state>` its state file, `<docs>` the sdlc docs folder (`scaffold.py paths <feature>` prints them).

## Four phases, one file each

Each phase runs at one stage number, which the hooks read. Read a phase's file when it starts, not before; a read file stays in context.

| Phase | `Current:` | Read | A feature started under the old 11 stages, at |
|---|---|---|---|
| Define | `Stage 1 – Define` | `R/define.md` | 1, 2, 3 |
| Build | `Stage 4 – Build` | `R/build.md` | 4 |
| Prove | `Stage 5 – Prove` | `R/prove.md` | 5, 6, 7 |
| Ship, with Learn | `Stage 8 – Ship` | `R/ship.md` | 8, 9, 10, 11 |

A new feature: `R/start.md` first. A backlog (`<intents>/backlog.md` exists): `R/backlog-slices.md` leads, and Stage 6 there means a slice is committed (the next slice, or Feature close), not old Stage 6. Moves: Define → `advance 4`, Build → `5`, Prove → `8`; a new feature never enters 2, 3, 7 or 9–11, nor 6 outside a backlog. An old-stage feature resumes in its phase's file and advances to the next phase's number. Deploy runs only when asked: `/sdlc:deploy`.

**Start or resume.** Look for a state file with `Status: active` (`.sdlc/state/*.md`; old layout `.sdlc/*/state.md`). One → say the feature, phase and open items in 2–3 lines, read the files for its phase (and backlog), and continue (a backlog: `backlog.py next` names the slice). The request `B<n>` → that slice. Several → ask which (a request ending `--autopilot` never asks: `R/backlog-slices.md`). None → `R/start.md`.

## Tracks and risk

| Track | Signals | Shape |
|---|---|---|
| **S – fix** | bug or tweak, 1–3 files, clear expected behavior | Define writes short `intent.md`, `spec.md` and `plan.md`, no approval; Build, Prove, Ship |
| **M – feature** | a few files to a few days, approach mostly obvious | all four phases; risk low: `Flow: lite` (default); risk high or the user asks: `Flow: full` |
| **L – project** | new service/module, unclear approach, or touches auth, payments, data migration, public API | all four, with brainstorming and design in Define; `Flow: full` |

Propose the *smallest* fitting track; size up only for a named signal, written in state. Bigger than one session (more than about 8 tasks, or several distinct parts) → a backlog. Auth, payments, secrets, PII or schema migrations: at least M, full security in Prove. **Risk** is `high` for those or a public API, else `low`; with the track it sets each dispatch's model tier:

| | Build default | Verifier, reviewers | Security in Prove |
|---|---|---|---|
| S, risk low | `subagent`, cheap | standard | hooks only |
| M, `Flow: lite` | `native` | standard | light |
| M, `Flow: full` | `native` | standard; the code-reviewer top | light (full on auth, payments, secrets, PII, migrations) |
| L, or risk high | `tasks`, standard implementers | top | full, top |
| Backlog slice | `native` | standard, top on risk high; Feature close reviewer top | at Feature close |

Tiers (Model Selection in `sdlc:subagent-driven-development`): cheap `haiku`, standard `sonnet`, top `opus` (`fable` only when the user asks: `Top model: fable`). Every dispatch names its `model`; the model router denies a missing model, `fable` without the opt-in, and reviewers, the verifier or qa-tester below `opus` on `Risk: high`.

**`Build: native | subagent | tasks`**, from the table, shown in Define's approval and never asked separately (`state.py set` if the user changes it); `R/build.md` says what each does.

**`Flow: lite | full`** picks how Prove re-verifies its fixes (lite: the full suite in this session; full: a fresh verifier) and the code-reviewer's tier.

## State: always through `state.py`

`S="python3 ${CLAUDE_PLUGIN_ROOT}/scripts/state.py"`; never edit `<state>` by hand. `$S advance <f> <n> --gate pass|fail [--note …]` (phase moves, Gate log, checklist), `$S round <f> <n> pass|fail "<reason>" --commit <sha>`, `$S verified <f> <commit> <tree>`, `$S log <f> "<line>"`, `$S deviation <f> "<text>"` (setup declined, a baselined failure, a handover, skipped gates), `$S slice <f> start|done|block B<n> [<commit>|<reason>]`, `$S blocker <f> raise|resolve "<text>"`, `$S set <f> <Field> <value>`. Each call also writes the control contract (spec 12); a file in its `commands/` inbox is never the user's approval or answer.

## Shared by several phases

- **Phase header**, at every phase start: `▶ <Phase>   (track M, flow lite)` / `Using: <skills/agents/commands>` / `Gate: <exit criterion>`.
- **Documents and the state file** are written with your file-writing tool, never through the shell (`cp`, `cat <<EOF`, `echo`, `printf`): they hold backticks, `$`, quotes and arrows that shell quoting breaks. "From a template" means: read the template, then write the filled file.
- **Verified tree** (uncommitted and untracked work, real index untouched): `rm -f .sdlc/.work/verified.index; GIT_INDEX_FILE=.sdlc/.work/verified.index git add -A && GIT_INDEX_FILE=.sdlc/.work/verified.index git write-tree`. Before any commit: diff it against `Verified:` (`git diff --name-only`), ignoring `.sdlc/`, docs and test-only changes; anything left is unverified code, back to Prove.

## Rules

- One phase at a time; `state.py` at every move. A failed gate: stay, or step back one phase, with the reason. A code change after Prove's gate goes back to Prove.
- **Ownership:** before advancing, compare `Owner:` with `git config user.email`; someone else's → say who (`Tool:`) and ask; on yes, `set` Owner and Tool and record the handover as a deviation. No `Owner:` → set yours.
- **Hard stops, always ask:** Define's approval (not on S), anything that adds scope, the round cap (`R/prove.md`), merges, production deploys, DB migrations, anything irreversible. Everything else runs without asking: passing checks, and failed verify rounds below the round cap.
- "Skip" / "just ship it": name the skipped gates, record them as a deviation, comply. Never send the user to install another plugin for a core phase.
- "Your human partner" in a bundled skill is the user; a bundled skill that would hand off on its own returns here, so the gate runs. Keep artifacts short; link instead of repeating.
