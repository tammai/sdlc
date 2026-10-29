---
type: gotcha
title: A subagent's prompt can't make it run a skill's slash command
description: Agent instructions that say "run /<skill> <command>" get skipped; point the agent at the skill's script or reference file instead.
tags: [agents, skills, impeccable]
updated: 2026-10-29
---

# A subagent's prompt can't make it run a skill's slash command

## Symptom
In the 2.1.0 live checks, `sdlc:ui-reviewer` was told to run `/impeccable audit` on the changed screens "every time". In two runs it ran `impeccable detect` and never ran the audit, without saying it had skipped it.

## Cause
`detect` is a launcher script the agent can call through Bash. `audit` is a command of the impeccable skill, and a slash command is something the user types, not a tool the subagent has. The agent treats the line as something it can't do and moves on.

## Fix
Name what the agent can actually run. For a script, give the launcher path. For a skill command, have the agent read the file the command loads (impeccable's `reference/audit.md`) and apply it, saying which parts to skip (its fix suggestions). After the change, the rerun reported `audit: none` with the files it checked. When you write any agent or skill text that depends on another plugin's skill, check that each step is a tool call or a file read.
