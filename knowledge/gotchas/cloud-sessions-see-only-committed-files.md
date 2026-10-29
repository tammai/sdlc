---
type: gotcha
title: Cloud sessions see only what's committed
description: A cloud session starts from a fresh clone, so settings.local.json and other uncommitted files never reach it.
tags: [settings, cloud, plugins, setup]
updated: 2026-10-29
---

# Cloud sessions see only what's committed

## Symptom
A repo set up with sdlc 2.0.1–2.2.0 ran in Claude Code on the web (or a routine) without sdlc or its companions turned on.

## Cause
Those versions wrote the plugin keys only to `.claude/settings.local.json`, which is never committed. A cloud session clones the repo, so it gets `.claude/settings.json` and the user's account settings, but no machine-local file.

## Fix
Anything a cloud session needs goes in a committed file, and committing it is the team's call, so setup asks (`enable-plugin --team`, 2.3.0). Settings that belong to one machine, such as turning a conflicting plugin off, stay local.
