---
type: gotcha
title: What Claude Code sends hooks, checked live
description: A failed Bash call is PostToolUseFailure; subagent calls carry agent_type; updatedInput alone keeps permissions.
tags: [hooks, claude-code]
updated: 2026-10-26
---

# What Claude Code sends hooks, checked live

## Symptom
A hook on `PostToolUse` Bash never sees a command that exits non-zero, so the freshness hook ignored every failing full test run (a baselined failure kept a package stale forever).

## Cause
A non-zero exit arrives as `PostToolUseFailure`, with `error` ("Exit code 1") and `is_interrupt`, and no `tool_response`. Tool calls made inside a subagent fire the same hooks, with `agent_type` (`sdlc:<agent>` for this plugin's agents, `general-purpose` otherwise) and `agent_id`; calls from the main session have neither.

A Bash call's `tool_input` carries `command`, `description`, `timeout` (ms, when given) and `run_in_background`. A PreToolUse hook can return `hookSpecificOutput.updatedInput` with no `permissionDecision`: the call runs with the new input and the user's permission rules still decide (checked live on 2.1.310: a lowered `timeout` reached PostToolUse, and an unallowed `touch` was still refused in `-p`). `updatedInput` replaces the whole input, so copy every field. Adding `permissionDecision: "allow"` would skip the permission prompt.

## Fix
Register a hook that cares about failures on `PostToolUseFailure` too (`hooks/hooks.json`). Key role checks on `agent_type` (`hooks/role_guard.py`). Change a call's input with `updatedInput` alone (`hooks/prove_budget.py`). The exit is the tests' only when nothing runs after them: `| tail` or `; echo $?` report their own (`verify_freshness.exit_is_the_tests`).

## How to detect early
Log raw hook input with a throwaway `--settings` file in a scratch repo and run one headless session (`claude -p … --settings`), as done on 2026-10-23; then check the plugin's own registrations in a `--plugin-dir` session.

## Related
- [Windows stdout encoding](windows-stdout-encoding.md)
