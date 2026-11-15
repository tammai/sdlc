# 2026-11-15-s-write-probe-and-merge-helper
Status: done
Process: 3
Track: S   (footprint: 3 files)
Risk: low
Top model: opus
Base: 5eb7c97
Owner: tammai.it@gmail.com
Tool: claude-code
Verified: 5eb7c97 tree 567ac1ded30ad70a583f120deeff3597454a3ebb
Current: Stage 4 – Ship

## Tasks
1. **Write probe instead of os.access, shared merge helper** — AC-001
   - Files: `scripts/scaffold.py`, `tests/test_stack_blueprints.py`, `CHANGELOG.md`

## Public Surface
- none

## Gate log
- 2026-11-15 Stage 1: pass
- 2026-11-15 Stage 2: pass — no review: no trigger fired

## Deviations
- 2026-11-15 scripts/scaffold.py check_writable check_config Project._merge_onto_disk What: the write probe, the config check and the shared merge helper as named functions. Why: the Decisions rows. Effect: none outside scaffold.py.

## Open questions
-
