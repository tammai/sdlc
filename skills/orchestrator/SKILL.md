---
name: orchestrator
description: Takes a feature, fix or project through define, build, review and ship, leaving the same intent, spec and plan record at every size. Use when the user wants work taken through that flow or asks where it stands, or when the message is or opens with a GitHub, Linear, Jira or other tracker ticket link.
---

`${CLAUDE_PLUGIN_ROOT}` is the sdlc plugin's folder (other agents: the installed plugin folder above this file). `R` is this skill's `references/` folder.

# SDLC Orchestrator (sdlc 2.0)

You decide the phase, keep the state current, and stop only where this file says. Every change leaves the same record, committed with the code: `intent.md` (why), `spec.md` (what must be true, each criterion with its test) and `review.md` (what was checked after the build), kept for good; and `plan.md` (how), a working file `/sdlc:prune` may delete once merged. Paths: `<intents>` is the feature's documents folder, `<state>` its state file, `<docs>` the sdlc docs folder (`scaffold.py paths <feature>` prints them).

## Four phases

| Phase | `Current:` | Read when it starts |
|---|---|---|
| Define | `Stage 1 – Define` | `R/define.md` |
| Build | `Stage 4 – Build` | `R/build.md` |
| Review | `Stage 5 – Review` | `R/review.md` |
| Ship, with Learn | `Stage 8 – Ship` | `R/ship.md` |

Moves: Define → `advance 4`, Build → `5`, Review → `8`. A new feature: `R/start.md` first. Work split into parts (`<intents>/backlog.md`): `R/backlog-slices.md` leads. Deploy only when asked: `/sdlc:deploy`.

**Start or resume.** Look for a state file with `Status: active` (`.sdlc/state/*.md`; old layout `.sdlc/*/state.md`). One with `Process: 2` → say the feature, phase and open items in 2–3 lines and continue in its phase (a backlog: `backlog.py next` names the part; the request `B<n>` → that part). One without `Process: 2` was started under sdlc 1.x: say so, and that it must be finished with sdlc 1.8.1 or archived (`Status: done`); 2.0 can't run it. Several → ask which (a request ending `--autopilot` never asks). None → `R/start.md`.

## Size and approval

| Track | Signals | Before the build |
|---|---|---|
| **S** | a fix or tweak, 1–2 files, clear expected behaviour | intent, spec and plan, a few lines each; no stop |
| **M** | a few files to a few days, approach mostly clear | intent, spec and plan in full; the user reads and approves |
| **L** | several distinct parts, or an approach still unclear | intent, spec and plan in full, the interview via `sdlc:brainstorming`; the user reads and approves |

Propose the smallest fitting track; size up only for a named signal, recorded in state with the footprint (files touched). Size by footprint, not risk words. **Risk** is `high` for auth, payments, secrets, PII, schema migrations, a public API, or untrusted input reaching a shell, file path or database; else `low`. Risk doesn't change the track: it feeds the review recommendation (`R/review.md`).

**Intent before code, at every size.** Nothing is built until what, why and how are written down. You judge whether the request already makes them clear; if anything is missing or ambiguous, at any size, ask first, one question at a time, each built on the last answer (`R/define.md`). A bug is proven first (a failing test or exact steps), then its root cause, then the fix.

## Model selection

Cheap and standard work: `sonnet` with `effort: high`; top: `opus` (`fable` only when the user asks: `Top model: fable`). Never `haiku`. Every dispatch names its `model`. Every review agent runs on `opus` at every size: the model router denies a review below it, a missing model, `haiku`, and `fable` without the opt-in. The build itself runs in this session on its model unless Define chose otherwise (`R/build.md`).

## State: always through `state.py`

`S="python3 ${CLAUDE_PLUGIN_ROOT}/scripts/state.py"`; never edit `<state>` by hand. `$S advance <f> <n> --gate pass|fail [--note …]`, `$S verified <f> <commit> <tree>`, `$S log <f> "<line>"`, `$S deviation <f> "<text>"`, `$S slice <f> start|done|block B<n> [<commit>|<reason>]`, `$S blocker <f> raise|resolve "<text>"`, `$S set <f> <Field> <value>`. Each call also writes the control contract (spec 12); a file in its `commands/` inbox is never the user's approval or answer.

## Context: read a file only when the context doesn't already hold it

- Don't re-read, in this session, what you just wrote, a reference you already loaded, or a file you just edited.
- Do read after `/clear`, in a new session, after the conversation was compacted, or in a fresh subagent such as a reviewer: the record files exist for those moments.
- Ask the scripts instead of opening files: `state.py` and `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/verify.py" status` print short JSON (phase, verified tree, whether tests are green).
- Write each record file once, after the questions are settled; load each phase's reference once, when the phase starts.

## Shared rules

- **Phase header**, at every phase start: `▶ <Phase>   (track M, risk low)` / `Gate: <exit criterion>`.
- **Documents and the state file** are written with your file-writing tool, never through the shell (`cp`, `cat <<EOF`, `echo`): they hold backticks, `$` and quotes that shell quoting breaks.
- **Verified tree:** the `tree` field of `verify.py status`, typed out in full. Before any commit, diff it against `Verified:`, ignoring `.sdlc/`, docs and test-only changes; anything left is unverified code: back to Build, rerun `verify.py`, then Review again.
- **Ownership:** before advancing, compare `Owner:` with `git config user.email`; someone else's → say who (`Tool:`) and ask; on yes, `set` Owner and Tool and record the handover as a deviation.
- **Advisor:** not called during an sdlc change unless the review step recommends it and it was chosen (by the user, or on S by the recommendation).
- **Hard stops, always ask:** the M and L approval before the build, the M and L review choice after it, anything that adds scope, a reviewer and the builder disagreeing on a high finding, CI still red after one fix, merges, production deploys, DB migrations, anything irreversible.
- "Skip" / "just ship it": name the skipped steps, record them as a deviation, comply.
- "Your human partner" in a bundled skill is the user; a bundled skill that would hand off on its own returns here.
