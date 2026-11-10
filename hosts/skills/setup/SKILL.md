---
name: setup
description: Sets up this repo for sdlc (new or existing), covering commands, rules, guardrails, CI, constitution, knowledge. Runs on a branch and resumes if interrupted.
---

Use the `sdlc:setting-up-projects` skill now.

- Arguments are `design`: run only the design step (switch between builtin and impeccable, or finish turning impeccable on), **Revisiting it** in the skill's `references/design-mode.md`.
- Arguments are `deploy`: run only the `deploy` step (record or change the deploy target, the environments and the runbook), as the skill's `/sdlc:setup deploy` sentence says; in a repo not set up yet, run **Setup**, which asks it.
- Otherwise run **Setup** (or resume it if `scaffold.py status` says `in_progress`). Always run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py" host` first, even when the session status line says `setup complete`: that line doesn't show which agents set the repo up, and `joining: true` means **Join** (the skill's Which flow table). Only when it isn't joining and the project is already set up, say so and point to `/sdlc:upgrade`, `/sdlc:start`, `/sdlc:setup design` to change the design mode, or `/sdlc:setup deploy` to record how it deploys.

Context from the user: <the user's request>
