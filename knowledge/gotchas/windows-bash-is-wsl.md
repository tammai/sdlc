---
type: gotcha
title: A bare "bash" subprocess runs WSL on Windows
description: Why ralph tests failed with a mangled path, and how tests must start bash.
tags: [windows, tests, bash]
updated: 2026-10-22
---

# A bare "bash" subprocess runs WSL on Windows

## Symptom
A test that runs a `.sh` hook exits 127 with `/bin/bash: C:Usersprojectshooksstop-hook.sh: No such file or directory`: the backslashes are gone from the path.

## Cause
`subprocess.run(["bash", ...])` on Windows resolves through the Windows search order, which checks `C:\Windows\System32` before `PATH`. `System32\bash.exe` is WSL, which treats `\` as an escape. Git Bash, the bash the plugin's hooks target, only comes later on `PATH`.

## Fix
Start bash through `tests/helpers.py` → `BASH` (`shutil.which("bash")`, which follows `PATH` and finds Git Bash). Hooks themselves are unaffected: Claude Code runs them through its own shell.

## How to detect early
Run `python -c "import subprocess; print(subprocess.run(['bash','-c','uname'],capture_output=True,text=True).stdout)"`: `Linux` means WSL.

## Related
- [Non-ASCII output crashes Python scripts on Windows](windows-stdout-encoding.md)
