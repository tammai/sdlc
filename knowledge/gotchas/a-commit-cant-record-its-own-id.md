---
type: gotcha
title: A commit can't record its own ID
description: Why writing a part's commit ID into backlog.md took a second commit and went stale on amend, and what to record instead.
tags: [scripts, backlog, git]
updated: 2026-11-03
---

# A commit can't record its own ID

## Symptom
Each backlog part ended in two commits (the part, then "marking the row done"), and a part whose commit was amended left an ID in `backlog.md` that no longer existed (2.4.2 smoke test).

## Cause
`state.py slice done B<n> <commit>` wrote the ID after the commit, so the row changed after it: a second commit, or an amend that changes the ID it just recorded. A file can't hold the ID of the commit that contains it.

## Fix
Record the fact, not the ID: `slice done B<n>` before the commit, so the row goes into the part's own commit, and name the part in the commit message so `git log --grep B<n>` finds it.

## How to detect early
A tracked file that a script updates with `git rev-parse HEAD` right after a commit: it will always need another one.
