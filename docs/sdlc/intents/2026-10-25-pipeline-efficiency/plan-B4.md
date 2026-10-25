# Slice B4 plan: one commit security review per review-ready diff

Spec FR-05, AC 6 · Backlog B4. Claude Code only (the other agents don't run the security review).

## Tasks

1. `hooks/sdlc_review_gate.py` `decide(repo_root, shas, reviewed)` → `{defer, shas, range, active}`: defer before Stage 5 of the one active feature whose `Base:` is an ancestor of HEAD; from Stage 5, the commit plus every unreviewed commit since `Base:` (at most 30) as one net diff `range`; otherwise the SHAs as given — tests `tests/test_sdlc_review_gate.py` (build commits deferred, then covered with every hunk; no feature, unchanged; a `Base:` outside the history defers nothing). (FR-05)
2. `hooks/security_reminder_hook.py` (vendored): ask the gate after the SHAs are known; a deferred commit exits before anything is recorded as reviewed; a range is reviewed as one `git diff`; no amend-delta review while the gate applies. Patch recorded in `NOTICE.md`.
3. Docs: spec 05 SEC-FR-009, CONTRIBUTING, CHANGELOG.

## Public Surface

- module `hooks/sdlc_review_gate.py` (`decide`) — FR-05
