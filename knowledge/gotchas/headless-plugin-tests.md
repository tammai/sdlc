---
type: gotcha
title: Headless live checks of the plugin
description: Why a headless `claude -p "/sdlc:start"` run on Windows loads no plugin, why planted hook state is cleared by the run's own prompt, and why a test repo has no sdlc at all after the run.
tags: [testing, hooks, windows]
updated: 2026-11-02
---

# Headless live checks of the plugin

## Symptom
- From Git Bash, `claude -p "/sdlc:start" --plugin-dir /c/...` runs, but the slash command isn't found or the plugin's hooks never fire.
- A check planted at the cap (review rounds already failed, a trust-anchor notice pending) never shows in the run: the agent goes on as if nothing were held.
- A later session in the test repo, started without `--plugin-dir` (a restart, a `/model` switch), runs no sdlc hook: a force push to main and a real-looking API key both go through.

## Cause
- Git Bash rewrites `/sdlc:start` and `/c/...` as Windows paths (MSYS path conversion). With conversion off, `--plugin-dir` then needs the Windows spelling.
- The run's prompt is a `UserPromptSubmit`, the user's reply. The trust anchor accepts pending notices on it, and `review_rounds.py` grants one more round on it, so state planted before the run is lifted before the first tool call.
- The `"sdlc@sdlc": false` the fix below sets stays in the repo's `.claude/settings.local.json`; without `--plugin-dir` nothing else loads sdlc there.

## Fix
- `MSYS_NO_PATHCONV=1 claude -p "/sdlc:start" --plugin-dir "C:/Users/.../sdlc" --model sonnet --effort high --permission-mode auto --output-format stream-json --verbose`; turn the installed `sdlc@sdlc` off in the test repo's `.claude/settings.local.json` so only the checkout loads, and set it back to `true` before using that repo in a normal session.
- To check a hold, plant the state one step short (rounds 1 and 2 of 3 failed, not 3) and let the run reach it itself; then `--resume <session id>` with the reply to check that the reply lifts it.

## How to detect early
In the stream-json transcript, a hook's deny shows as `PreToolUse:<tool> hook error: sdlc: …`; no such line where one was expected means the hook didn't run or its state was already lifted. From 2.4.1, `/sdlc:doctor` run from the installed plugin warns when `sdlc@sdlc` is `false` for the repo (`sdlc plugin` check).
