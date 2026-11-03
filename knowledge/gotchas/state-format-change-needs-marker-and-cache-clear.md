---
type: gotcha
title: Changing what a state-file field means
description: Why a renumbered stage needs a new Process marker, and why the migration also clears the trust anchor's remembered stage.
tags: [state, hooks, migration]
updated: 2026-11-03
---

# Changing what a state-file field means

## Symptom
Renumbering the phases (1, 4, 5, 8 to 1 to 4, sdlc 3.0) would have made an old `Current: Stage 4` (Build) read as Ship by the new hooks, and a migrated feature would have shown a phantom "went from Stage 5 to Stage 3" notice.

## Cause
- The hooks read the number, not the name, and keyed on `Process: 2`, which said nothing about which numbering a file used.
- `.sdlc/.work/trust-anchor.json` is git-ignored and remembers each feature's last stage, so it still holds the old number after the state file is rewritten.

## Fix
- Bump `Process:` with the meaning (`sdlc_layout.PROCESS`), so hooks ignore and `state.py` refuses a file in the old form instead of misreading it.
- Make the migration a script (`state.py migrate`), not prose: rewrite the files, drop the runtime store's entry for each migrated feature, refresh the contract snapshot.
- A shared check that lives in users' repos (`templates/project/ci/invariants.py`) must read both forms until its repo is migrated.

## How to detect early
Grep for the old values in `hooks/`, `scripts/`, `templates/` and the git-ignored stores under `.sdlc/.work/` before calling a format change done. Number the next ADR from `docs/adr/README.md` on the branch you merge to: 0021 was taken by another branch.
