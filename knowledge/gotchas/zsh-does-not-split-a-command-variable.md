---
type: gotcha
title: zsh doesn't split a variable that holds a command
description: Why `S="python3 …/scaffold.py"; $S status` failed on macOS, and the form that works in bash and zsh.
tags: [skills, shell, macos]
updated: 2026-11-03
---

# zsh doesn't split a variable that holds a command

## Symptom
`S="python3 ${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py"` then `$S status`: `zsh: no such file or directory: python3 /…/scaffold.py`. It worked in bash.

## Cause
bash splits an unquoted `$S` into words; zsh does not, so the whole string is one command name. An unquoted path with spaces broke it in bash too.

## Fix
Name a function and put its name in the variable, so the expansion is one word and the quotes live in the function: `sdlc_scaffold() { python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py" "$@"; }; S=sdlc_scaffold`. Define it in every shell call that uses it: the Bash tool keeps no shell state between calls. `tests/test_setup_skill_shell.py` runs the skill's own lines in bash and zsh.

## How to detect early
Run a skill's documented shell lines under `zsh -c`, not only bash.
