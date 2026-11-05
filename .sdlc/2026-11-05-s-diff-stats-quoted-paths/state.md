# 2026-11-05-s-diff-stats-quoted-paths
Status: done
Process: 3
Track: S   (footprint: 4 files)
Risk: low
Top model: opus
Base: f951499
Owner: 
Tool: claude-code
Verified: f951499 tree 02f71eca09d03be483a959f3851989900c2c3802
Current: Stage 4 – Ship

## Tasks
1. **Keep file names with spaces and non-ASCII whole** — AC-001 AC-002 AC-003
   - Files: `scripts/diff_stats.py`, `hooks/verify_freshness.py`, `tests/test_diff_stats.py`, `tests/test_verify_freshness.py`

## Public Surface
- none

## Gate log
- 2026-11-05 Stage 1: pass
- 2026-11-05 Stage 2: pass — no review: no trigger fired

## Deviations
- 2026-11-05 scripts/diff_stats.py What: added module helpers unquote() and nul_names(), not listed as surface. Why: drift reads every new top-level def as an export; they are private helpers used only inside diff_stats.py. Effect: no public API change; callers of collect() and parse_diff() see the same signatures.
- 2026-11-05 Suite What: ran tests on Python 3.15 (python3), not 3.10; sdlc setup none, so verify runs only the AC tests. Why: py -3.10 calls need approval in this unattended run; repo has no .sdlc/config.json. Effect: the full suite was run separately on 3.15; cp1252 issues 3.10 would show are covered by the existing non-UTF-8 locale test.

## Open questions
-
