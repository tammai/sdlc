---
name: project-constitution
description: Use when setting up or amending a project's non-negotiable engineering principles (testing, security, architecture, review and release rules) that every spec, design and plan must comply with. Writes .sdlc/constitution.md.
---

# Project Constitution

Adapted from GitHub Spec Kit's `constitution` command and template (MIT, see NOTICE.md).

The constitution is the short list of rules every feature must follow. Specs, designs and plans are checked against it; a MUST violation blocks the pipeline. Keep it to what the team genuinely enforces.

## Create or amend

1. If `.sdlc/constitution.md` exists, load it (amending). Otherwise start from `${CLAUDE_PLUGIN_ROOT}/templates/constitution-template.md`.
2. Gather values from the user's input first, then from the repo (README, CLAUDE.md, CI config, lint/test setup, existing docs). Ask only for what you can't infer — at most a few questions, with suggested answers.
3. Fill every placeholder. Each principle gets:
   - a short name,
   - concrete rules written with MUST / SHOULD (no vague "should be clean"),
   - one line of rationale.
   Typical areas: test-first and coverage expectations, security (secrets, input validation, auth), architecture boundaries, code review, observability, versioning and breaking changes, simplicity/YAGNI. Number of principles is flexible; drop template sections you don't need.
4. **Versioning** (semantic):
   - MAJOR: a principle removed or redefined incompatibly
   - MINOR: a principle or section added, or guidance materially expanded
   - PATCH: wording, typos, clarifications
   Dates in ISO format. Ratified date stays fixed; Last Amended = today when anything changes.
5. Prepend a sync report as an HTML comment: version old → new, principles added/changed/removed, follow-ups (e.g. "update CLAUDE.md testing section").
6. Check consistency: does CLAUDE.md or the orchestrator's gates contradict a principle? List what needs updating; don't silently edit other files.
7. Write `.sdlc/constitution.md`. Before writing, confirm no `[PLACEHOLDER]` tokens remain unless deliberately deferred (list those in the report).

## Report

New version and why that bump, files flagged for follow-up, and a suggested commit message, e.g. `docs: amend constitution to v1.2.0 (add observability principle)`.
