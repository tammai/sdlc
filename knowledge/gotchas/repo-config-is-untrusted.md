---
type: gotcha
title: A repo's .sdlc/config.json can't decide what runs without asking
description: Anything sdlc acts on without a question (plugins to enable or disable) comes from the plugin's shipped defaults, never the committed repo config.
tags: [security, scaffold, settings]
updated: 2026-10-28
---

# A repo's .sdlc/config.json can't decide what runs without asking

## Symptom
In the first cut of 2.0.1, `enable-plugin` read `companions` from the merged config (the plugin's defaults plus the repo's `.sdlc/config.json`). Since it no longer asks, a repo could list `{"id": "x@evil", "source": …, "default": true}` and setup would turn that plugin on, so its code would run in Claude Code. The commit security review flagged it as high.

## Cause
`.sdlc/config.json` is committed: whoever can change the repo can change it, and cloning a repo isn't consent to its plugins. Its overrides are fine for things a person reviews (commands, areas) or that a question guards. Writing settings without asking is not one of those.

## Fix
`companions()` and `conflicts()` in `scripts/scaffold.py` read only `templates/project/config.defaults.json` under `PLUGIN_ROOT`, and require a `name@marketplace` id. Apply the same rule to any new no-question action: its inputs come from the plugin, or a question guards it.
