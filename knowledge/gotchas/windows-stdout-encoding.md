---
type: gotcha
title: Non-ASCII output crashes Python scripts on Windows
description: Why doctor and scaffold printed nothing on Windows, and how output must be written.
tags: [windows, scripts, hooks, encoding]
updated: 2026-10-22
---

# Non-ASCII output crashes Python scripts on Windows

## Symptom
A script prints nothing and exits 1; stderr ends in `UnicodeEncodeError: 'charmap' codec can't encode character`. Tests that parse its output fail with an empty string or a JSON decode error.

## Cause
On Windows, Python encodes stdout to a pipe or console with the locale code page (cp1252), not UTF-8. Any character outside it (✅, →, ≤) raises while printing. `json.dumps(..., ensure_ascii=False)` and emoji or arrows in Markdown output trigger it.

## Fix
Call `sys.stdout.reconfigure(encoding="utf-8")` before printing, as `scripts/doctor.py` and `scripts/scaffold.py` do. Claude Code reads hook and script output as UTF-8. Plain `json.dumps` (ASCII escapes) is safe without it.

## How to detect early
Run the script with `PYTHONIOENCODING=cp1252`; a test that sets it reproduces the crash on any OS (`test_doctor` › test_markdown_output, `test_scaffold` › test_non_ascii_output_survives_a_non_utf8_pipe).

## Related
- [CRLF checkouts break exact-match edits](crlf-checkout.md)
