# Big work and autopilot

## 19. A big feature becomes a backlog

Work with several distinct parts that won't fit one session, on M or L. Never on S, and never a change confined to 1–2 files.

1. **Define** writes `backlog.md` in the feature's work folder, `.sdlc/state/<feature>/`: one row per part (`B1`, `B2`, …, each something a test can see working) with its acceptance criteria, dependencies and size. The state file's `## Tasks` gives each part an outline. You approve them all at once.
2. **Each part:** the agent writes `plan-B<n>.md`, builds until `verify.py` passes, commits it, and updates the state file's `## Handoff` so a fresh session can pick up from the files. No review per part. Parts run back to back without asking.
3. **It stops** for a backlog change that adds scope, or at a hard stop. To look at each part, say so: it records `Slice gates: plan, commit` (either or both).
4. **Low context:** it stops at a part boundary with `B<n> done (<commit>). Next: B<m> <title>. Run /clear, then /sdlc:start.` `/sdlc:start B<n>` runs a named part once its dependencies are done.
5. **Feature close**, after the last part: all parts land together. One Review over the whole branch (the recommendation and your choice, as in [6](Everyday-work.md#6-choose-the-reviews-and-act-on-findings)), then Ship with Learn, which stops at the PR.

Long backlog and you'd rather not `/clear` by hand: [20](#20-run-a-backlog-on-autopilot).

## 20. Run a backlog on autopilot

It's opt-in, and not the Ralph loop ([11](#11-run-an-autonomous-loop)).

**In this session:** say `autopilot` (or "run the rest unattended"). The session runs every remaining slice back to back, then feature close, without asking: no slice gates, no stop at a slice boundary for context (each slice's commit and handoff carry it past compaction), and Review takes the agent's recommendation. A slice that would add scope is marked blocked and the run goes on with the others; a hard stop ends it. It doesn't offer the headless script instead, and needs no extra permissions beyond the session's own.

**Headless, one fresh session per slice** (Claude Code only). Run, in a terminal at the repo root:

```
python3 <plugin>/scripts/autopilot.py [--permission-mode <mode>] <feature>
```

The headless sessions need permission to edit files and run git, the project's commands and the plugin's scripts (`state.py`, `backlog.py`), which live outside the repo in the plugin's folder (add it to `permissions.additionalDirectories` if they're denied). Setup's allowlist covers only the project's own commands, so pass a `--permission-mode` or widen the allowlist. A session that is denied leaves its slice unchanged, and autopilot stops with `B<n> is still todo after its run`. The mode is handed to `claude` as given; autopilot never adds a permission-bypass flag.

Each session runs `/sdlc:start B<n> --autopilot`: it does one slice and ends, never asking. Anything that would ask (a scope change, a hard stop) marks the slice `blocked: <reason>` in `backlog.md` and adds an open question. Feature close's Review takes the agent's own recommendation and records that it did.

**It stops** on an open trust-anchor notice, a feature that isn't active, a blocked slice, nothing ready, a session that fails, a run that leaves its slice unchanged, or a feature close that doesn't reach Ship. It prints one JSON object naming the reason and the slices it ran. Fix the cause in a normal session (for a blocked slice, `/sdlc:start B<n>` and answer its question), then run the same command again.

**When it finishes,** feature close has run Review and Ship. The merge still waits for you: say merge in a normal session (`/sdlc:start`).

## 11. Run an autonomous loop

This is the Ralph loop: one task repeated in the current session. For running a backlog's slices in fresh sessions, see autopilot ([20](#20-run-a-backlog-on-autopilot)).

It comes with the optional companion plugin: `/plugin install sdlc-extras@sdlc`, then restart. For one well-specified task with a machine-checkable finish:

```
/sdlc-extras:ralph-loop "Make all tests in tests/export pass" --completion-promise "DONE" --max-iterations 15
```

Always set `--max-iterations`. Cancel with `/sdlc-extras:cancel-ralph`. Use it inside Build only; Review still runs afterwards.
