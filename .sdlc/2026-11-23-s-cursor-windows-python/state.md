# 2026-11-23-s-cursor-windows-python
Status: done
Process: 3
Track: S   (footprint: 3 files)
Risk: low
Top model: opus
Base: c8fc4b5
Owner: tammai.it@gmail.com
Tool: claude-code
Verified: c8fc4b5 tree 2736ef2e8867908559819732e1e9a5e5f7eb88a5
Current: Stage 4 – Ship

## Tasks
1. **One sh/PowerShell command and hook.ps1 for Cursor on Windows** — AC-001
   - Files: `scripts/hosts.py`, `hosts/cursor/hook.ps1`, `hosts/cursor/hooks.json`, `tests/test_hosts.py`

## Public Surface
- none

## Gate log
- 2026-11-23 Stage 1: pass
- 2026-11-23 Stage 2: pass — no review: no trigger fired

## Deviations
- 2026-11-23 Task 1 What: the code was written while finding Cursor's behaviour live, before the record; the red step ran against HEAD's hosts.py with hook.ps1 set aside. Why: the payload piping was only found by trying candidates in Cursor. Effect: AC-001 red recorded on the old code as usual.

## Open questions
-
