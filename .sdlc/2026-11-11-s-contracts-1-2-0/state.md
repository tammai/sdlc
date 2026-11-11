# 2026-11-11-s-contracts-1-2-0
Status: done
Process: 3
Track: S   (footprint: 12 files)
Risk: low
Top model: opus
Base: c9b5f82
Owner: 3235400+tammai@users.noreply.github.com
Tool: claude-code
Verified: c9b5f82 tree 6d8d97b6395b4763d748e6b9d54fba8a5a34325a
Current: Stage 4 – Ship

## Tasks
1. **Re-vendor contracts 1.2.0** — AC-001
   - Files: `scripts/contracts/v1/CONTRACTS.md`, `scripts/contracts/v1/MANIFEST`, `scripts/contracts/v1/acceptance-manifest.schema.json`, `scripts/contracts/v1/contracts.py`, `scripts/contracts/v1/cost-line.schema.json`, `scripts/contracts/v1/criteria-lock.schema.json`, `scripts/contracts/v1/departures.schema.json`, `scripts/contracts/v1/finding.schema.json`, `scripts/contracts/v1/test_contracts.py`, `tests/test_contracts_vendor.py`, `CHANGELOG.md`, `.sdlc/2026-11-11-s-contracts-1-2-0/change.md`

## Public Surface
- none

## Gate log
- 2026-11-11 Stage 1: pass
- 2026-11-11 Stage 2: pass — no review: no trigger fired

## Deviations
- 2026-11-11 setup What: this repo has no .sdlc/config.json (scaffold.py status: setup none, layout legacy), so no test command is recorded. Why: the plugin's own repo has always run sdlc without setup (e.g. 2026-11-08-l-spec-backed-mode). Effect: verify.py runs the AC test; the full suite is run by hand with CONTRIBUTING.md's command (unittest discover -s tests -t tests, Python 3.10 and 3.9-compatible python3).

## Open questions
-
