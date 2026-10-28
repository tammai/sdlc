---
type: gotcha
title: Hooks that judge a Bash command by its text
description: Commit review needs `git commit` in the visible command; parsing agent-written chains for the budget breaks on ordinary spellings.
tags: [hooks, claude-code]
updated: 2026-10-28
---

# Hooks that judge a Bash command by its text

## Symptom
- Moving Ship's commit into `scripts/ship.py` would have skipped the commit security review entirely: the commit happens, but no review runs.
- Review's budget hook refused the documented one-call Ship (`ship.py … && git commit -F …`) in the 2.0 evals, costing a turn each time.

## Cause
- The commit review (`hooks/security_reminder_hook.py`) decides by matching `git commit` in the Bash call's `command`, then reads the SHA from its output; a commit made inside a script never matches. Its sdlc gate (`hooks/sdlc_review_gate.py`) reviews only while a feature is active, read from the working tree at PostToolUse, so setting `Status: done` in the same call used to switch the review off.
- `hooks/prove_budget.py` parses the command to decide what to time out, and refuses what it can't parse. Agents write ordinary chains it can't: a backtick in a commit message, a leading `cd`, a trailing `| tail`.

## Fix
- Keep `git commit` in the command the agent runs; a script may prepare everything before it (`ship.py`, then `&& git commit -F .sdlc/.work/commit-msg.txt`). The gate counts the commit that takes a feature from active to done as that feature's (`_finished_by`), so Ship can commit `Status: done` with the change.
- Don't widen a command parser to fit what agents type: move the work out of the guarded state instead (a reviewed change advances to Stage 8 when it writes `## Review`, so Ship runs outside Review's budget), and take free text out of the command (`ship.py` reads the commit subject from the change file).
