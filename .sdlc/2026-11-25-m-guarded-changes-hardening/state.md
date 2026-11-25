# 2026-11-25-m-guarded-changes-hardening
Status: done
Process: 3
Change: .sdlc/2026-11-25-m-guarded-changes-hardening/change.md   (this feature's record for people)
Track: M   (sized up because: —; footprint: 5 files)
Risk: low
Top model: opus   (fable only if the user chose it)
Commands: test: (none recorded)
Started: 2026-11-25
Base: 5bafdf9
Owner: tammai.it@gmail.com
Tool: claude-code
Verified: 5bafdf9 tree a699a8a831959c22b66aa381675f1bef16be4bba
Current: Stage 4 – Ship

## Stages
- [x] 1 Define   — the change file, the plan sections below
- [x] 2 Build
- [ ] 3 Review   — the change file's ## Review
- [ ] 4 Ship     — PR: (Learn: knowledge, recurring-defects.md)

## How the build runs
inline: this session builds it, one part

## Handoff
- items(): hooks/guarded_changes.py:321; allow matching: main() ~446; verify.guarded_failures: scripts/verify.py:557

## Tasks
1. **Dependency sources, suppressions, manifests, plain move, unreadable Base** — AC-001 AC-002 AC-003 AC-004 AC-005
   - Files: `hooks/guarded_changes.py`
2. **What an Allow covers** — AC-006
   - Files: `hooks/guarded_changes.py`
3. **Errors reported as not checked** — AC-007
   - Files: `scripts/verify.py`
4. **Tests, docs and todo** — AC-001 AC-002 AC-003 AC-004 AC-005 AC-006 AC-007
   - Files: `tests/test_guarded_hardening.py`, `CHANGELOG.md`, `docs/adr/0032-opt-in-guards.md`, `docs/wiki/Limitations.md`, `.sdlc/todo.md`

## Public Surface
- none

## Test lock
- `tests/test_guarded_hardening.py` sha256:6e4b5237b1841a5048a9192e0f38278532d0dffa43d83a4215ab671aafa2043e

## Gate log
- 2026-11-25 Stage 1: pass — plan not stopped for approval: low-risk M
- 2026-11-25 Stage 2: pass — no review: no trigger fired

## Deviations
- 2026-11-25 hooks/guarded_changes.py source_part What: new helper giving the source-relevant text of a manifest or config. Why: AC-001. Effect: internal.
- 2026-11-25 Base What: moved from 455d245 to 5bafdf9. Why: PR #142 merged into main under this feature's uncommitted work. Effect: drift and the test lock compare against the merge.

## Open questions
-
