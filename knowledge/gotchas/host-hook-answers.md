---
type: gotcha
title: Other agents read a hook's answer differently
description: Antigravity denies a tool call on `{}`; Cursor's allow skips approval; Codex and Antigravity send no exit code.
tags: [hooks, codex, cursor, antigravity]
updated: 2026-10-25
---

# Other agents read a hook's answer differently

## Symptom
On Antigravity, a probe hook printing `{}` blocked every tool call ("tool call denied by pre-tool hook"). On Cursor, a warning sent with `permission: "allow"` would have run a command the user is normally asked about.

## Cause
"No opinion" isn't the same output everywhere:
- **Antigravity** (CLI 1.4.7): `PreToolUse` needs a `decision`; none, or a failing hook, denies the call. `ask` is its usual permission check: allow-listed commands and workspace edits still run unasked. It rejects unknown output fields.
- **Cursor:** `permission: "allow"` approves the call outright; leave `permission` out to keep the user's approval.
- **Codex:** reads Claude Code's fields, but only on the events that take them.
- **Codex and Antigravity** send a command's output without its exit code (Antigravity's `error` is empty even on exit 3), so a test run counts as `unknown`.

## Fix
`hosts/hook.py`: never answer `allow`; Antigravity's tool calls get `ask` on no objection and on any error (`fallback`). Each host's output keeps to that host's documented fields.

## How to detect early
Capture real payloads first with a scratch plugin whose hook appends stdin to a file. Antigravity's hook contract ships inside `agy.exe` (search it for "Lifecycle Hooks"). Headless `agy -p` with permissions bypassed is blocked by the auto-mode classifier, so drive agy interactively in a terminal while the user approves.

## Related
- [What Claude Code sends hooks](hook-inputs.md)
- [ADR 0007](../../docs/adr/0007-multi-tool-adapters.md), spec 11
