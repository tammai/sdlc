---
type: gotcha
title: Tests point CLAUDE_PLUGIN_ROOT at a fake plugin
description: Why a script must import its sibling modules from its own file's location, not from CLAUDE_PLUGIN_ROOT.
tags: [scripts, tests]
updated: 2026-10-23
---

# Tests point CLAUDE_PLUGIN_ROOT at a fake plugin

## Symptom
A script that imports a sibling module via `os.path.join(PLUGIN_ROOT, "hooks")` works in a real session but fails with `ModuleNotFoundError` in `tests/test_scaffold.py`.

## Cause
`ScaffoldTest` sets `CLAUDE_PLUGIN_ROOT` to a temp dir holding only fake templates, a fake `plugin.json` and fake config defaults, so tests control versions and templates. `scaffold.py`'s `PLUGIN_ROOT` follows that variable, and the fake tree has no `hooks/`.

## Fix
Import code from the script's own location: `os.path.dirname(os.path.dirname(os.path.abspath(__file__)))`. Keep `PLUGIN_ROOT` for data the tests swap out (templates, defaults, the version). `scaffold.py`, `prune.py` and `diff_stats.py` load `hooks/sdlc_layout.py` this way.

## How to detect early
Run `tests/test_scaffold.py` after adding an import to a script; `test_doctor.py` and `test_project_templates.py` use the real plugin root and won't catch it.
