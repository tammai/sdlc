---
type: gotcha
title: Review agents can't run plugin scripts
description: A fact a review needs from a script (a config-derived path, a mode) is worked out by the orchestrator and named in the review's prompt.
tags: [review, agents, orchestrator]
updated: 2026-11-17
---

# Review agents can't run plugin scripts

## Symptom
A review instruction says "when `scaffold.py objects` says `on: true`, read the file it prints", and the code reviewer
either breaks its own rule by running the script or skips the check (3.12.0's domain-model review, round 2).

## Cause
`agents/code-reviewer.md`'s Read-Only section allows reading code, diffs and git history and running the project's
own test command, nothing else. `review-brief.md` and the agent prompts are read by that reviewer.

## Fix
The orchestrator, which may run commands in Review, works the fact out once and puts it in each review's prompt
(`flow.md` Review step 2: "the objects file is `<path>` … or `none`"). The reviewer reads what the prompt names, and
never re-derives it from repo config, which would also skip the path rules the script applies.

## How to detect early
Grep review instructions (`review-brief.md`, `agents/*reviewer*.md`) for `python3` or `scripts/`: any command there
other than the project's tests is one the code reviewer can't run.
