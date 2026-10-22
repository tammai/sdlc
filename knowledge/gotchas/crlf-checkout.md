---
type: gotcha
title: CRLF checkouts break exact-match edits
description: Why a scripted replace finds nothing in a Windows checkout, and how to edit safely.
tags: [windows, editing]
updated: 2026-10-22
---

# CRLF checkouts break exact-match edits

## Symptom
A scripted string replace (Python `str.replace`, an assert on `count`) finds 0 matches for text that is plainly in the file.

## Cause
With `core.autocrlf=true`, files check out with CRLF line endings; a multi-line `old` string written with `\n` never matches. `sed -i` from Git Bash also rewrites the file with LF.

## Fix
Normalise to `\n` before matching and write back with the file's own line endings; after `sed -i`, restore CRLF. The repo stores LF, so `git diff` stays clean either way.

## How to detect early
`file <path>` reports "with CRLF line terminators".

## Related
- [runbook R10](../../docs/runbook.md#r10-hooks-error-on-windows-or-with-an-odd-python)
