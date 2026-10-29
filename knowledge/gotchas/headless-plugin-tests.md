---
type: gotcha
title: Headless live checks of the plugin
description: Why a headless `claude -p "/sdlc:start"` run on Windows loads no plugin, and why planted hook state is cleared by the run's own prompt.
tags: [testing, hooks, windows]
updated: 2026-10-29
---

# Headless live checks of the plugin

## Symptom
- From Git Bash, `claude -p "/sdlc:start" --plugin-dir /c/...` runs, but the slash command isn't found or the plugin's hooks never fire.
- A check planted at the cap (review rounds already failed, a trust-anchor notice pending) never shows in the run: the agent goes on as if nothing were held.

## Cause
- Git Bash rewrites `/sdlc:start` and `/c/...` as Windows paths (MSYS path conversion). With conversion off, `--plugin-dir` then needs the Windows spelling.
- The run's prompt is a `UserPromptSubmit`, the user's reply. The trust anchor accepts pending notices on it, and `review_rounds.py` grants one more round on it, so state planted before the run is lifted before the first tool call.

## Fix
- `MSYS_NO_PATHCONV=1 claude -p "/sdlc:start" --plugin-dir "C:/Users/.../sdlc" --model sonnet --effort high --permission-mode auto --output-format stream-json --verbose`; turn the installed `sdlc@sdlc` off in the test repo's `.claude/settings.local.json` so only the checkout loads.
- To check a hold, plant the state one step short (rounds 1 and 2 of 3 failed, not 3) and let the run reach it itself; then `--resume <session id>` with the reply to check that the reply lifts it.

## How to detect early
In the stream-json transcript, a hook's deny shows as `PreToolUse:<tool> hook error: sdlc: …`; no such line where one was expected means the hook didn't run or its state was already lifted.
