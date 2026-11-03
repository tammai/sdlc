---
type: gotcha
title: Review refuses heredocs, so a helper script reads a file
description: Why a script the agent calls during Review takes its structured input from a file written with the Write tool, not stdin from a heredoc or echo.
tags: [hooks, review, scripts]
updated: 2026-11-03
---

# Review refuses heredocs, so a helper script reads a file

## Symptom
A script that wanted JSON on stdin (`python3 x.py <<'EOF' … EOF`, or `echo '…' | python3 x.py`) can't be called in Review: `hooks/prove_budget.py` denies a heredoc, a subshell, `$(...)` and two slow steps chained, and says to use the Edit or Write tool.

## Cause
In Review (Stage 3) every command other than the project's own runs one plain step at a time under a 120 s kill. A heredoc is refused because it is how a file gets written around the file tools.

## Fix
Give the script a `--findings FILE`-style argument. The agent writes the file with the Write tool, then runs the script as one plain command (`scripts/review_report.py` does this). `tests/test_prove_budget.py` checks the call isn't denied.

## How to detect early
Any new script the flow runs in Review: read its usage line for stdin input, and check the call against the hook before writing the flow text.
