---
type: gotcha
title: Writing a hooks module (sdlc-stepper)
description: What the validator, the test kit and the real UI each refuse or hide in sdlc-stepper, and how to see the real UI (a short window hides the band, positioned boxes paint over the flow, a plugin from a symlink isn't loaded).
tags: [plugins, sdlc-stepper, testing, ui]
updated: 2026-11-03
---

# Writing a hooks module (sdlc-stepper)

## Symptom
- `claude plugin validate` failed: `$ is passed to "refresh", which is not a function declared at the top of this file`.
- `claude plugin test`: `$.ui.mount: no implementation for ui.render`, because the band drew nothing; the fake `fs.*` hooks never matched a path.
- `tsc` (5.x on PATH) failed with hundreds of parse errors in the engine's `.d.ts`.
- The band showed, then hid, in a real terminal while every kit test passed.
- On the desktop, a layer positioned `absolute` (a background strip) painted over the content in the flow, so the content vanished; a `Box` border cost two whole text rows and its corner radius could not be set.
- A dev copy of the plugin made as a symlink into the checkout failed to load (`Path escapes plugin directory`).
- The bar's step text stayed `failing tests` while the transcript moved on.
- The bar showed nothing during Define and appeared only once it was done.
- A `skill.prompt` hook put "its skill.prompt hook was skipped" in the user's transcript.
- Running the plugin with `--plugin-dir` left an untracked `tsconfig.json` in the plugin folder.

## Cause
- The validator follows `$` only into functions declared at the top of the module (or imported from its own files), never a closure inside `register`.
- In a test, a relative path reaches the `fs.*` hooks resolved against the plugin's folder (`<plugin>/.sdlc/config.json`), and `.` arrives as the folder itself.
- The engine's types need TypeScript 7.
- The engine gives the band only the rows left above the prompt (`e.props.maxRows`) and hides a tree that doesn't fit, so a taller band vanishes first when the window is short or the prompt area grows. The kit mounts with a fixed `maxRows`, so it never shows this.
- A positioned box paints over every unpositioned one, whatever the order; borders and radius are the surface's (`borderStyle` is only a name).
- The step changed only on a tool the code knew; the model's own words arrive in `turn.step`'s result (`answer`).
- sdlc writes a feature's state file only at the end of Define (`state.py new`, in the call that moves to Build), so a bar that reads state files has nothing to read before then.
- A built-in module (`cc-plugin-sec-default`) runs ahead of a plugin's `skill.prompt` hook and sends the event past it; the engine says so in the transcript, once per skill load.
- The engine writes `tsconfig.json` and `.claude-plugin/types/` into any plugin folder it loads with `--plugin-dir`.

## Fix
- Helpers that touch `$` are top-level `async function f($: EngineInterface, …)`; a closure may call them.
- Fake files match by path tail, and the root is learnt from the first `exists` call (`plugins/sdlc-stepper/tests/stepper.test.tsx`, `repo()`).
- Type-check with a TypeScript 7 `tsc` and the tsconfig from the types file's header.
- Give the band a fallback by `maxRows` (the outline goes below 3 rows), and keep it short.
- For a shape the props can't give (pill, 2px border, exact padding), draw it as one SVG; a layer over another needs both layers `absolute`, the later one on top, with a 1px in-flow spacer for the height.
- To read the model's words, hook `turn.step` as an async generator (`const r = yield* next(e)`), only read `r.answer`, and call `$` from a top-level helper.
- Before the state file exists, show a draft: `/sdlc:start` on `prompt.submit` (`e.command?.name`) makes it, the agent's `Define · …` lines keep it, the state file replaces it, and a turn with no Define line drops it, so a trivial start leaves nothing. Don't hook `skill.prompt` for this.
- `tsconfig.json` in the stepper folder is ignored in `.gitignore`.
- A live preview of a plugin edit: a local marketplace under another name (`claude plugin marketplace add <dir>`) holding a real copy of the plugin (rsync it after each edit), the marketplace one disabled so only one band draws, and a restarted session (plugins load at start).

## How to detect early
In a test, stub what sits beneath the plugin (`ui.render`, `prompt.submit`, `turn.step` as an async generator returning `{ turnId, index, answer, toolUses: [], stopReason, usage }`, `turn.complete`), and call `$.turn.complete({ turnId, answer })`; `ui.render` must be stubbed too when a test expects the band absent. Run `claude plugin validate plugins/sdlc-stepper` and `claude plugin test plugins/sdlc-stepper` before anything else; CI runs both. They don't draw the real UI: run `claude` under `tmux new-session -d -x 120 -y 40`, read it with `tmux capture-pane -p`, and shrink it with `tmux resize-window -y <rows>` (the first start asks to trust a folder: answer it). A screenshot of the desktop app is the only check of its layout.
