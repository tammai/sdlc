---
type: gotcha
title: Writing a hooks module (sdlc-stepper)
description: Why claude plugin validate refused a helper that took $, why the test kit's fake files were never found, and which tsc checks the module.
tags: [plugins, sdlc-stepper, testing]
updated: 2026-11-03
---

# Writing a hooks module (sdlc-stepper)

## Symptom
- `claude plugin validate` failed: `$ is passed to "refresh", which is not a function declared at the top of this file`.
- `claude plugin test`: `$.ui.mount: no implementation for ui.render`, because the band drew nothing; the fake `fs.*` hooks never matched a path.
- `tsc` (5.x on PATH) failed with hundreds of parse errors in the engine's `.d.ts`.

## Cause
- The validator follows `$` only into functions declared at the top of the module (or imported from its own files), never a closure inside `register`.
- In a test, a relative path reaches the `fs.*` hooks resolved against the plugin's folder (`<plugin>/.sdlc/config.json`), and `.` arrives as the folder itself.
- The engine's types need TypeScript 7.

## Fix
- Helpers that touch `$` are top-level `async function f($: EngineInterface, …)`; a closure may call them.
- Fake files match by path tail, and the root is learnt from the first `exists` call (`plugins/sdlc-stepper/tests/stepper.test.tsx`, `repo()`).
- Type-check with a TypeScript 7 `tsc` and the tsconfig from the types file's header.

## How to detect early
Run `claude plugin validate plugins/sdlc-stepper` and `claude plugin test plugins/sdlc-stepper` before anything else; CI runs both.
