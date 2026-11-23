---
type: gotcha
title: Other agents read a hook's answer differently
description: Antigravity denies a tool call on `{}`; Cursor's allow skips approval; Codex and Antigravity send no exit code; headless Cursor may skip prompt and Stop hooks.
tags: [hooks, codex, cursor, antigravity]
updated: 2026-11-19
---

# Other agents read a hook's answer differently

## Symptom
On Antigravity, a probe hook printing `{}` blocked every tool call ("tool call denied by pre-tool hook"). On Cursor, a warning sent with `permission: "allow"` would have run a command the user is normally asked about.

## Cause
"No opinion" isn't the same output everywhere:
- **Antigravity** (CLI 1.4.7): `PreToolUse` needs a `decision`; none, or a failing hook, denies the call. `ask` is its usual permission check: allow-listed commands and workspace edits still run unasked. It rejects unknown output fields.
- **Cursor:** `permission: "allow"` approves the call outright; leave `permission` out to keep the user's approval.
- **Codex:** reads Claude Code's fields, but only on the events that take them.
- **Codex and Antigravity** send a command's output without its exit code (Antigravity's `error` is empty even on exit 3), so a test run counts as `unknown`. Never parse one out of the output: Codex's `Exit code:` envelope is only on `apply_patch`, so on a command it's the command's own text, and a command could fake a pass.

### Reported by TokenEconomizer, not re-checked here
From the "Verified agent behaviour" and "Known limitations" sections of microsoft/TokenEconomizer's `docs/PLUGIN.md` (MIT, commit 4a04fe4, 2026-11-18). Check one live before building on it.
- **Cursor** (`cursor-agent` 2026.11.05, `--trust -p`, macOS): `sessionStart`, `postToolUse`, `afterShellExecution` and `sessionEnd` fired; `beforeSubmitPrompt` and `stop` were registered but never fired, and `postToolUseFailure` wasn't exercised. If that holds, sdlc's Cursor prompt and Stop hooks (the review-cap lift, the freshness and trust-anchor checks at turn end) don't run in a headless Cursor run. The interactive app wasn't tested. An `additional_context` reply to `postToolUse` reaches the model.
- **Cursor on Windows** runs hook commands through PowerShell, so sdlc's `python3 "${CURSOR_PLUGIN_ROOT}/…"` command is untested there (already on the todo list as "Cursor's bare python3").
- **Codex:** releases before 0.141.0 install a plugin but never run its hooks (0.131.0, 0.135.0 and 0.140.0 tried). `PostToolUse` `additionalContext` reaches the model (0.153.1). `continue: false` on `PostToolUse` doesn't stop a turn. Codex turns a plugin's `commands/` folder into skills of its own, which listed every command twice beside the plugin's skills. A `$` mention in `codex exec` matches only the full `<plugin>:<skill>` name. A project's `.codex/config.toml` is read only in a trusted project. A `CODEX_HOME` under `/tmp` breaks Codex's sandbox (`codex-linux-sandbox: No such file`). Codex runs the plugin version it cached at install (`~/.codex/plugins/cache/<marketplace>/<plugin>/<version>`), even from a local-path marketplace: a live check against 3.2.1 guarded nothing until `codex plugin add sdlc@sdlc` cached 3.14 (0.154.0, 2026-11-23). A Codex run from a Claude Code shell inherits `CLAUDECODE` and the rest; only `CLAUDE_PROJECT_DIR` mattered, and `hosts/hook.py` drops it.
- **Antigravity** (`agy` 1.5.1 and 1.5.2): `PostToolUse` carries no tool result, and a matcher of `"*"` never matches. A payload leaves out a zero (`invocationNum` 0 is absent on a prompt's first model call). There is no `SessionEnd`, and calls a subagent makes aren't in the transcript. In `injectSteps`, a `systemMessage` at `SessionStart` persists; an `ephemeralMessage` is dropped after the turn.

## Fix
`hosts/hook.py`: never answer `allow`; Antigravity's tool calls get `ask` on no objection and on any error (`fallback`). Each host's output keeps to that host's documented fields.

## How to detect early
Capture real payloads first with a scratch plugin whose hook appends stdin to a file. Antigravity's hook contract ships inside `agy.exe` (search it for "Lifecycle Hooks"). Headless `agy -p` with permissions bypassed is blocked by the auto-mode classifier, so drive agy interactively in a terminal while the user approves.

## Related
- [What Claude Code sends hooks](hook-inputs.md)
- [ADR 0007](../../docs/adr/0007-multi-tool-adapters.md), spec 11
