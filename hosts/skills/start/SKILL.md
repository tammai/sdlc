---
name: start
description: Start or resume a feature through the SDLC pipeline (define → build → review → ship, with learn)
---

The orchestrator's text is below, so no skill load is needed: follow it exactly, and don't load the `sdlc:orchestrator` skill.

Request: <the user's request>

If the request is empty, resume the active feature in `.sdlc/` (on a backlog, its current or next ready slice), or ask what to build if there is none. A request that is `B<n>` runs that slice of the active feature's backlog. A trailing `--autopilot` means `scripts/autopilot.py` started this headless session: follow the orchestrator's autopilot rules (Backlog slices), and ignore the flag when deciding whether the request is empty or `B<n>` (`--autopilot` alone resumes the active feature; every slice done: Feature close).

`${CLAUDE_PLUGIN_ROOT}` is the sdlc plugin's folder (other agents: the installed plugin folder). `R` is `${CLAUDE_PLUGIN_ROOT}/skills/orchestrator/references/`.

# SDLC Orchestrator (sdlc 2.0)

Every change but a trivial one leaves the same record, committed with the code and kept, in two files: `<change>` for people (why, what must be true with each criterion's test, and what the review found) and the state file for the agent (where it stands, how it's built). Paths: `<change>` is the feature's change file (`<docs>/changes/<feature>.md`), `<state>` its state file, `<work>` the folder beside it for working files (backlog, part plans, QA report), `<docs>` the sdlc docs folder (the `sdlc session status` line in your context gives them; without it, `scaffold.py paths <feature>`).

**Start or resume.** Look for a state file with `Status: active` (the session status line lists them; else `.sdlc/state/*.md`, old layout `.sdlc/*/state.md`). One with `Process: 2` → say the feature, phase and open items in 2–3 lines and continue in its phase from its file below (a backlog: `backlog.py next` names the part; the request `B<n>` → that part). One without `Process: 2` was started under sdlc 1.x: say so, and that it must be finished with sdlc 1.8.1 or archived (`Status: done`); 2.0 can't run it. Several → ask which (a request ending `--autopilot` never asks). None → size the request (below).

## Size, then read one file

| Track | Signals | Before the build | Read |
|---|---|---|---|
| **Trivial** | no behaviour changes, so no test could tell before from after: a typo, a rename, comments or docs, a config value nothing tests; nothing security-sensitive | none: no workflow, no record, no state file (below) | nothing |
| **S** | a fix or tweak, 1–2 files, clear expected behaviour | `<change>` and the plan, a few lines each; no stop | `R/s-track.md` alone |
| **M** | a few files to a few days, approach mostly clear | `<change>` and the plan in full; at high risk the user reads and approves `<change>`, at low risk the build starts | `R/flow.md` |
| **L** | several distinct parts, or an approach still unclear | `<change>` and the plan in full (pointing to a written spec when there is one, not restating it), the interview via `sdlc:brainstorming` unless that spec settles it; one part unless it won't fit one session; the user reads and approves `<change>` | `R/flow.md` |

Read the track's file once, when the work starts or resumes, and no other reference unless it names one. Work split into parts (`<work>/backlog.md`): `R/backlog-slices.md` leads. Deploy only when asked: `/sdlc:deploy`.

**Trivial or S is one question: does behaviour change?** Any bug fix, and any change a test could catch, is at least S however small; only a change no test could see is Trivial. Say in one line "Trivial, so I'm doing it directly", then work like plain Claude: make the change, run the project's tests, and commit with a clear message. The commit is the whole record. If the user says "full record", or the change turns out to change behaviour (a test fails), stop and go on as S.

Propose the smallest fitting track; size up only for a named signal, recorded in state with the footprint (files touched). Size by footprint, not risk words. **Risk** is `high` for auth, payments, secrets, PII, schema migrations, a public API, or untrusted input reaching a shell, file path or database; else `low`. Risk doesn't change the track: it feeds the review choice.

**Intent before code, at every size.** Nothing is built until what, why and how are written down. If anything is missing or ambiguous, ask first, one question at a time, each built on the last answer. A bug is proven first (a failing test or exact steps), then its root cause, then the fix.
