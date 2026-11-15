---
type: gotcha
title: Writing a user's file safely on Windows
description: Why os.access says a protected file is writable, what an atomic replace loses, and why an OS lock can't guard a repo shared with WSL.
tags: [windows, scaffold, files]
updated: 2026-11-15
---

# Writing a user's file safely on Windows

## Symptom
`scaffold.py` replaced a file the user had protected with a Windows ACL deny rule; a mutex built on `msvcrt.locking` / `fcntl.flock` let a WSL session and a Windows session write the lock at once (3.9.0 review rounds, ADR 0027).

## Cause
- `os.access(path, os.W_OK)` on Windows checks only the read-only attribute, never the ACL.
- Write-temp-then-`os.replace` makes a new file: it drops the old one's owner, ACL and hard links (mode and symlinks need keeping by hand).
- Windows and WSL processes don't see each other's OS file locks, so a lock only guards sessions on one side.

## Fix
Probe writability by opening the file `r+b` and closing it (`scaffold.check_writable`); keep mode and write through a symlink in `_write_atomic`; detect concurrent saves by re-reading and merging at save time instead of locking (ADR 0027).

## How to detect early
Test on a file with `icacls <f> /deny "%USERNAME%:(W)"` (Git Bash: `MSYS_NO_PATHCONV=1`, or `/deny` becomes a path) and on a path on another drive (`os.path.relpath` raises across drives).
