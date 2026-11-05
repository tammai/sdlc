# 2026-11-05-s-diff-stats-dependency-names
Status: done
Process: 3
Track: S   (footprint: 2 files)
Risk: low
Top model: opus
Base: f951499
Owner: 
Tool: claude-code
Verified: f951499 tree 1befd95ef8d89028e309f1d135bb4cf070aa18a0
Current: Stage 4 – Ship

## Tasks
1. **Name go.mod one-line requires and bare pip names** — AC-001 AC-002
   - Files: `scripts/diff_stats.py`, `tests/test_diff_stats.py`

## Public Surface
- none

## Gate log
- 2026-11-05 Stage 1: pass
- 2026-11-05 Stage 2: pass — no review: no trigger fired

## Deviations
- 2026-11-05 setup What: repo has no .sdlc/config.json; ran without /sdlc:setup. Why: unattended run, nobody to ask. Effect: plugin default commands.
- 2026-11-05 suite What: full suite ran on python3 3.15, not py -3.10; 6 test_ralph_stop failures. Why: the py launcher needs approval in this unattended run; the same 6 fail on unchanged main. Effect: 3.10-only syntax and cp1252 crashes not checked by this run; CI covers them.
- 2026-11-05 CHANGELOG.md, docs/specs/03-scope-and-review.md What: Unreleased Fixed entry and the two new tests on SCO-FR-014. Why: CONTRIBUTING stale-docs audit. Effect: footprint 4 files, docs only.

## Open questions
-
