---
type: gotcha
title: Hardening an agent-writable record with a command-text guard doesn't converge
description: Each review round found new routes past a guard on .sdlc/.work records, and fixes added keys that broke more; cut scope instead.
tags: [hooks, review, guards]
updated: 2026-11-25
---

# Hardening an agent-writable record with a command-text guard doesn't converge

## Symptom
In `2026-11-25-m-approval-hardening`, review rounds 2–6 each failed with 4–5 highs. They fell into two groups:
- **New routes past the guard.** A guard on writes to `.sdlc/.work/approvals.json` let through PowerShell or host-mapped globs that match dot folders, a junction, a `subst` drive, a glob through an in-repo link and a dangling symlink.
- **Bugs a fix added.** Per-repo approval keys, added for namesakes in nested repos, broke typed `approve`, dialog matching and 3.16's records.

## Cause
Two causes, one per group:
- **The guard.** It reads command text and paths, an open set of spellings, to protect a file the agent can write anyway. That is the recurring defect "a guard that reads command text is the only line".
- **The scope.** Each fix widened the design (fail-closed rules, keys, a namesake refusal), and the next round reviewed the new code.

## Fix
After a second failed round whose highs come from the last round's fixes, stop fixing and propose cutting scope.
- Drop the text guard. Keep the record notice-level, as `docs/wiki/Limitations.md` says.
- Put the state that matters where a hand edit or a wipe doesn't reach it by accident. Here that was the tracked state file's `Approval floor:` line, written in the same step as the state change.
- Leave rare cases (nested-repo namesakes) as todos.

Round 7 passed once the change was back to that core.
