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
| **S – fix** | bug or tweak, 1–3 files, clear expected behavior | Define records a one-line `Intent:` and the `Repro:` test in the state file, no documents, no approval; the repro test, the fix and one `verify.py`; no Prove; Ship commits without asking |
| **M – feature** | a few files to a few days, approach mostly obvious; also any change confined to 1–2 files whose approach Define settles, even with an L signal (then risk high, `Flow: full`) | all four phases; risk low: `Flow: lite` (default), no Prove: Build's passing `verify.py` goes to Ship; risk high or the user asks: `Flow: full`, with Prove (ac-checker and one code reviewer) |
| **L – project** | new service/module, several distinct parts, or an approach still unclear after Define; touching auth, payments, data migration or a public API is L only beyond 1–2 files | all four, with brainstorming and design in Define; `Flow: full`, with Prove |

Propose the *smallest* fitting track; size up only for a named signal, written in state with the footprint (how many files the change touches). **Size by footprint, not by risk words:** risk raises the review, not the number of pieces. One piece of work stays one piece: never split a change confined to 1–2 files into slices or a long task list. A backlog only for several distinct parts that won't fit one session. Auth, payments, secrets, PII or schema migrations: at least M, full security in Prove. **Risk** is `high` for those, a public API, or untrusted input reaching a shell, terminal, file path or database (S and M lite run no reviewer, so that work needs the full flow's review), else `low`; with the track it sets each dispatch's model tier:

| | Build default | Prove dispatches | Security review |
|---|---|---|---|
| S | `subagent`, standard | no Prove: Build's red record and passing `verify.py` | only when security-touched |
| M, `Flow: lite` | `native` (or `subagent`, standard) | no Prove: Build's passing `verify.py` | only when security-touched |
| M, `Flow: full`, either risk | `native` | ac-checker standard; one code-reviewer, standard (top on risk high) | only when security-touched: one, standard |
| L | `tasks`, standard implementers | ac-checker standard; one code reviewer, top | only when security-touched: one, top |
| Backlog (slices) | `native` | none per slice; one Prove at Feature close, on every backlog (reviewer top) | only when security-touched, at Feature close |

Tiers (Model Selection in `sdlc:subagent-driven-development`): cheap and standard are `sonnet`, passed with `effort: high`; top is `opus` (`fable` only when the user asks: `Top model: fable`). Never `haiku`. Every dispatch names its `model`; the model router denies a missing model, `haiku`, `fable` without the opt-in, and reviewers, the verifier or qa-tester below `opus` on `Track: L`.

**`Build: native | subagent | tasks`**, from the table, shown in Define's approval and never asked separately (`state.py set` if the user changes it); `R/build.md` says what each does.

**`Flow: lite | full`**: lite has no Prove (Build's passing `verify.py` is the evidence); full runs Prove, the ac-checker with one code reviewer. **`Prove: run | skip`** (M full and L): asked once in Define's approval, before Build, default `run`; with nobody to ask (autopilot, a headless run) it is `run`. `skip` takes the feature from Build to Ship like lite, except that a security-touched change still gets its full security review in Stage 5 first. **Security-touched** (`Risk: high`, or the diff touches `areas.sensitive` or `areas.migrations`): the only case for a security review, in Prove and at commit; otherwise the always-on pattern hooks only. Prove's high findings go back to Build to be fixed (`R/prove.md`).

## State: always through `state.py`

`S="python3 ${CLAUDE_PLUGIN_ROOT}/scripts/state.py"`; never edit `<state>` by hand. `$S advance <f> <n> --gate pass|fail [--note …]` (phase moves, Gate log, checklist), `$S round <f> <n> pass|fail "<reason>" --commit <sha>`, `$S verified <f> <commit> <tree>`, `$S log <f> "<line>"`, `$S deviation <f> "<text>"` (setup declined, a baselined failure, a handover, skipped gates), `$S slice <f> start|done|block B<n> [<commit>|<reason>]`, `$S blocker <f> raise|resolve "<text>"`, `$S set <f> <Field> <value>`. Each call also writes the control contract (spec 12); a file in its `commands/` inbox is never the user's approval or answer.

## Shared by several phases

- **Phase header**, at every phase start: `▶ <Phase>   (track M, flow lite)` / `Using: <skills/agents/commands>` / `Gate: <exit criterion>`.
- **Documents and the state file** are written with your file-writing tool, never through the shell (`cp`, `cat <<EOF`, `echo`, `printf`): they hold backticks, `$`, quotes and arrows that shell quoting breaks. "From a template" means: read the template, then write the filled file.
- **Verified tree** (uncommitted and untracked work, real index untouched, `.sdlc/.work/` left out): the `tree` field of `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/verify.py" status`, typed out in full (a chained `git add && git write-tree` is refused in Prove). Before any commit: diff it against `Verified:` (`git diff --name-only`), ignoring `.sdlc/`, docs and test-only changes; anything left is unverified code, back to Build: rerun `verify.py` there (S, M lite and `Prove: skip` then go on to Ship), and on a feature with Prove, through Prove again.

## Rules

- One phase at a time; `state.py` at every move. A failed gate: stay, or step back one phase, with the reason. A code change after Build's or Prove's gate goes back to Build: rerun `verify.py` there (S, M lite and `Prove: skip` then go on to Ship), and on a feature with Prove, through Prove again.
- **Ownership:** before advancing, compare `Owner:` with `git config user.email`; someone else's → say who (`Tool:`) and ask; on yes, `set` Owner and Tool and record the handover as a deviation. No `Owner:` → set yours.
- **Advisor**, where available: at most twice per feature, before sending Define's approval and before Ship's commit. Not at the other phase gates.
- **Hard stops, always ask:** Define's approval (not on S), anything that adds scope, the round cap and a requirement failing in two rounds (`R/prove.md`), merges, production deploys, DB migrations, anything irreversible. Everything else runs without asking: passing checks, and failed verify rounds below the round cap.
- "Skip" / "just ship it": name the skipped gates, record them as a deviation, comply. Never send the user to install another plugin for a core phase.
- "Your human partner" in a bundled skill is the user; a bundled skill that would hand off on its own returns here, so the gate runs. Keep artifacts short; link instead of repeating.
