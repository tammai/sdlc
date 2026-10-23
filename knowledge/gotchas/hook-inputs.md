---
type: gotcha
title: What Claude Code sends hooks, checked live
description: A failed Bash call is PostToolUseFailure, not PostToolUse; subagent calls carry agent_type.
tags: [hooks, claude-code]
updated: 2026-10-23
---

# What Claude Code sends hooks, checked live

## Symptom
A hook on `PostToolUse` Bash never sees a command that exits non-zero, so the freshness hook ignored every failing full test run (a baselined failure kept a package stale forever).

## Cause
A non-zero exit arrives as `PostToolUseFailure`, with `error` ("Exit code 1") and `is_interrupt`, and no `tool_response`. Tool calls made inside a subagent fire the same hooks, with `agent_type` (`sdlc:<agent>` for this plugin's agents, `general-purpose` otherwise) and `agent_id`; calls from the main session have neither.

## Fix
Register a hook that cares about failures on `PostToolUseFailure` too (`hooks/hooks.json`). Key role checks on `agent_type` (`hooks/role_guard.py`). The exit is the tests' only when nothing runs after them: `| tail` or `; echo $?` report their own (`verify_freshness.exit_is_the_tests`).

## How to detect early
Log raw hook input with a throwaway `--settings` file in a scratch repo and run one headless session (`claude -p … --settings`), as done on 2026-10-23; then check the plugin's own registrations in a `--plugin-dir` session.

## Related
- [Windows stdout encoding](windows-stdout-encoding.md)
