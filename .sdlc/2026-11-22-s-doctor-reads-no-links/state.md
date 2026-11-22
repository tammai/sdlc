# 2026-11-22-s-doctor-reads-no-links
Status: done
Process: 3
Track: S   (footprint: 2 files)
Risk: high
Top model: opus
Base: fe4aa0a
Owner: 3235400+tammai@users.noreply.github.com
Tool: claude-code
Verified: fe4aa0a tree 6eab0af6619841cc31e802bcbd0b92a5bbda1d33
Current: Stage 4 – Ship

## Tasks
1. **Doctor reads no committed file through a link out of the repo** — AC-001
   - Files: `scripts/doctor.py`, `tests/test_doctor.py`

## Public Surface
- none

## Gate log
- 2026-11-22 Stage 1: pass
- 2026-11-22 full suite: OK, 5 skipped (python3.10); verify PASS
- 2026-11-22 Stage 2: pass — security r1, r2 fixed; r3 deferred to the end-of-push review

## Deviations
- 2026-11-22 setup What: the repo isn't set up for sdlc (the plugin's own repo). Why: as earlier features here. Effect: the full suite runs by hand on Python 3.10.
- 2026-11-22 scripts/doctor.py repo_text NOT_READ REPLACE_LINK What: module helpers behind doctor's one containment check on committed files it reads. Why: AC-001 (one reader for every open). Effect: internal to doctor; no public surface.
- 2026-11-22 tests/test_doctor.py scripts/doctor.py What: AC-001 widened to the .sdlc/.work freshness files, AC-002 added (unreadable files warn, in-repo links followed); helper join_fixes, NOT_READ_FIX, not_read. Why: security review r1 H1, M1. Effect: doctor never reads a committed file through a link out of the repo or crashes on an unreadable one.
- 2026-11-22 scripts/scaffold.py repo_text team_rules area_rules agents_block; tests/test_scaffold.py What: the one guarded reader moved to scaffold and used by its readers of CLAUDE.md, rules and hookify rules; AC-003 added; freshness state's shape checked. Why: security review r2 H1, M1 (user chose one more fix round). Effect: footprint 4 files; an unreadable or linked-out file is skipped or reported, never a traceback.
- 2026-11-22 review What: round 3 skipped, Why: the user deferred review to one pass over all todo fixes at the end of the one-day push, Effect: this commit ships unreviewed after round 2's fixes until that pass.
- 2026-11-22 order AC-002 AC-003 What: their red step ran after the code, with scripts/ put back to Base. Why: they came from reviews r1 and r2 and were first seen failing by hand. Effect: same proof.

## Open questions
-
