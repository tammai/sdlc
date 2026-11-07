---
type: gotcha
title: A rebased changelog entry can land in a released section
description: git puts an Unreleased note under the version released meanwhile, without a conflict
---

# A rebased changelog entry can land in a released section

A commit that adds a note under `## Unreleased`, rebased or merged onto a `main` where a release has since renamed that heading to `## <version> — <date>`, applies cleanly: git finds the surrounding lines in the released section and puts the note there. No conflict is shown, so the note ships as part of a version that never had it.

After any rebase or merge that touches `CHANGELOG.md`, read its top: each new note must sit under `## Unreleased` (or the version being released), never under a tag that already exists (`git tag -l 'sdlc--v*'`).

Seen in the 3.3.0 release: the local-merge note landed under 3.2.0's `### Changed`.
