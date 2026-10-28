---
name: project-constitution
description: Writes or amends a project's constitution, the non-negotiable engineering principles (testing, security, architecture, review, release) every spec, design and plan must follow. Use when setting up or changing those rules.
---

`${CLAUDE_PLUGIN_ROOT}` is the sdlc plugin's folder. Claude Code fills it in; on other agents it stays as written, so use the installed plugin's folder instead: the one above this file that holds `scripts/` and `skills/`.

# Project Constitution

Paths: `<change>` is the feature's change file (its record for people), `<state>` its state file (the agent's), `<work>` the folder beside it for working files (backlog, part plans, QA report) and `<docs>` the sdlc docs folder (`docs_dir`); `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py" paths <feature>` prints them for this repo's layout (`intents` is a pre-2.0 feature's documents folder).

Adapted from GitHub Spec Kit's `constitution` command and template (MIT, see NOTICE.md).

The constitution is the short list of rules every feature must follow. Specs, designs and plans are checked against it; a MUST violation blocks the pipeline. Keep it to what the team genuinely enforces.

## Create or amend

1. If `<docs>/constitution.md` exists, load it (amending). Otherwise start from `${CLAUDE_PLUGIN_ROOT}/templates/constitution-template.md`.
2. Gather values from the user's input first, then from the repo (README, CLAUDE.md, CI config, lint/test setup, existing docs). Ask only for what you can't infer — at most a few questions, with suggested answers.
3. Fill every placeholder. Each principle gets:
   - a short name,
   - concrete rules written with MUST / SHOULD (no vague "should be clean"),
   - one line of rationale.
   Typical areas: test-first and coverage expectations, security (secrets, input validation, auth), architecture boundaries, code review, observability, versioning and breaking changes, simplicity/YAGNI. Number of principles is flexible; drop template sections you don't need, except **V. Simplicity**, which is the sdlc default: keep it unless the user explicitly opts out (record that in the report).
4. **Versioning** (semantic):
   - MAJOR: a principle removed or redefined incompatibly
   - MINOR: a principle or section added, or guidance materially expanded
   - PATCH: wording, typos, clarifications
   Dates in ISO format. Ratified date stays fixed; Last Amended = today when anything changes.
5. Prepend a sync report as an HTML comment: version old → new, principles added/changed/removed, follow-ups (e.g. "update CLAUDE.md testing section").
6. Check consistency: does CLAUDE.md or the orchestrator's gates contradict a principle? List what needs updating; don't silently edit other files.
7. Write `<docs>/constitution.md`. Before writing, confirm no `[PLACEHOLDER]` tokens remain unless deliberately deferred (list those in the report).

## Report

New version and why that bump, files flagged for follow-up, and a suggested commit message, e.g. `docs: amend constitution to v1.2.0 (add observability principle)`.
