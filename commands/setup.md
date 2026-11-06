---
description: Sets up this repo for sdlc (new or existing), covering commands, rules, guardrails, CI, constitution, knowledge. Runs on a branch and resumes if interrupted.
argument-hint: "[what you're building, for a new repo] | design"
---

Use the `sdlc:setting-up-projects` skill now.

- Arguments are `design`: run only the design step (switch between builtin and impeccable, or finish turning impeccable on), **Revisiting it** in the skill's `references/design-mode.md`.
- Otherwise run **Setup** (or resume it if `scaffold.py status` says `in_progress`). Always run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py" host` first, even when the session status line says `setup complete`: that line doesn't show which agents set the repo up, and `joining: true` means **Join** (the skill's Which flow table). Only when it isn't joining and the project is already set up, say so and point to `/sdlc:upgrade`, `/sdlc:start`, or `/sdlc:setup design` to change the design mode.

Context from the user: $ARGUMENTS
