---
name: writing-specs
description: Use when turning a feature request or a brainstorm into a written requirements spec (what and why, no implementation), before any design or planning. Writes the feature's spec.md and a spec-quality checklist.
---

`${CLAUDE_PLUGIN_ROOT}` is the sdlc plugin's folder. Claude Code fills it in; on other agents it stays as written, so use the installed plugin's folder instead: the one above this file that holds `scripts/` and `skills/`.

# Writing Specs

Paths: `<intents>` is the feature's documents folder, `<state>` its state file and `<docs>` the sdlc docs folder (`docs_dir`); `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py" paths <feature>` prints them for this repo's layout.

Adapted from GitHub Spec Kit's `specify` command (MIT, see NOTICE.md).

A spec says **what** users need and **why**. It never says how: no languages, frameworks, APIs or code structure. It is written so a non-technical stakeholder could approve it.

## Inputs

- The feature request, the user's answers to Define's blocking questions, and `<intents>/intent.md` (a feature started earlier may have `brainstorm.md` instead).
- `<docs>/constitution.md` if it exists (project principles; treat MUST rules as hard constraints).
- Template: `${CLAUDE_PLUGIN_ROOT}/templates/spec-template.md`

## Steps

1. **Name the feature.** If the orchestrator already chose the name, use it. Otherwise: `<yyyy-mm-dd>-<track>-<slug>`, or `<yyyy-mm-dd>-<track>-<ticket>-<slug>` when the request names a ticket (`2026-10-22-m-PROJ-123-month-filter`; a GitHub issue is `gh-42`). `<track>` is `s`, `m` or `l`, the track the feature starts on; a later size-up changes `Track:` in state, never the name (the state file, documents folder, branch and hook records all use it). Run on its own, use the track the work would get (`s` fix, `m` feature, `l` project). The date is today's, the same as `Started:`; the slug is 2–4 kebab-case words, action-noun where possible (`user-auth`, `fix-payment-timeout`), keeping technical terms (OAuth2, JWT). If `<intents>/` already exists and isn't the feature being resumed, add `-2` (then `-3`, …). The feature's branch and `knowledge/features/<name>.md` use the same name. The feature directory is `<intents>/`.
2. **Copy the template** to `<intents>/spec.md` and fill it, keeping section order and headings.
2a. **Intent:** the spec's first line links `intent.md` and the plan (`Intent: [intent.md](intent.md) · Plan: [plan.md](plan.md)`); don't repeat the request, answers or approaches here. Run on its own (no orchestrator) with no `intent.md`: write one first from `${CLAUDE_PLUGIN_ROOT}/templates/intent-template.md`.
3. **Extract** actors, actions, data, constraints from the request.
4. **Unclear points:** the orchestrator already asked the blocking questions, in one message, before this skill; never ask more here and never leave `[NEEDS CLARIFICATION]` markers. Their answers are `[clarified]`. Anything still open gets an informed guess from context and industry norms: under Assumptions if it adds no work, as an `[inferred]` FR or SC if it does. The user keeps or drops those at the gate. Run on its own (no orchestrator), ask the blocking questions yourself first, the same way: one message, only what changes what gets built.
5. **User scenarios** with acceptance scenarios (Given/When/Then). If no clear user flow exists, stop and say so.
6. **Functional requirements** `FR-001…`: each one testable, each tagged with its source: `[user]` (the user asked), `[clarified]` (a user answer settled it) or `[inferred]` (you added it). Be strict: "the user would probably want it" is `[inferred]`. Common inferred creep: admin/settings UI, audit logging, i18n, pagination, caching, rate limiting, bulk operations, export, notifications, configurability, "support for future X".
7. **Success criteria** `SC-001…`: measurable and technology-agnostic (time, volume, completion rate, satisfaction), each verifiable without knowing the implementation, with the same source tags. A load or scale number the user didn't give is `[inferred]`.
7a. **Non-goals:** list what this feature deliberately leaves out, including the obvious extensions a designer might add "while we're at it". This is what stops the design and tasks from adding them back.
8. **Key entities** if data is involved.
9. **Edge cases**: negative paths, empty/error states, limits.
10. **Failure modes:** list which of these apply to this change, and only those: concurrent use, scale or large inputs, persisted-data migration and compatibility, partial failure or a crash mid-write, untrusted input, I/O errors. Turn each that applies into a testable acceptance criterion (or success criterion), within the spec's ~10-criteria budget, and name them in a short `Failure modes` list so reviewers check them. None apply → say so in one line.

## Quality check

Write `<intents>/checklists/requirements.md`:

```markdown
# Spec Quality Checklist: <feature>

## Content Quality
- [ ] No implementation details (languages, frameworks, APIs)
- [ ] Focused on user value and business needs
- [ ] Readable by non-technical stakeholders
- [ ] All mandatory sections completed

## Requirement Completeness
- [ ] Requirements are testable and unambiguous
- [ ] Success criteria are measurable and technology-agnostic
- [ ] Acceptance scenarios defined for every user story
- [ ] Edge cases identified
- [ ] Failure modes that apply are listed, each an acceptance or success criterion
- [ ] Scope clearly bounded (in / out); Non-Goals section filled
- [ ] Every FR and SC has a source tag ([user] / [clarified] / [inferred])
- [ ] No future-proofing without a requirement: "extensible", "flexible", "scalable", "generic", "pluggable", "configurable", "future" only with a concrete, measurable need
- [ ] Assumptions add no work (anything that adds work is an FR with a source)
- [ ] Dependencies and assumptions listed

## Feature Readiness
- [ ] Every functional requirement has acceptance criteria
- [ ] User scenarios cover the primary flows
- [ ] No implementation details leak into the spec
```

Check the spec against each item:
- Failing items: fix the spec and re-check, up to 3 rounds. Anything still failing goes in the checklist notes, and you tell the user.

## Inferred requirements at the gate

The orchestrator's Define approval lists every `[inferred]` FR/SC on its own, separate from the rest of the spec:

```
I added these; none were in your request. Dropped unless you keep them:
- FR-004 log all security events — why I added it: <one line>
- SC-003 90% first-attempt completion — why: <one line>
Keep any? (e.g. "keep FR-004", or "none")
```

Kept → retag `[clarified]`. Dropped → delete it and add a line to Non-Goals (`No security-event logging (was FR-004 [inferred])`), and don't renumber (gaps in ids are fine). The spec leaves Define with no `[inferred]` tags.

## Done

Report: spec path, checklist result (x/y passing), the `[inferred]` list for the gate, and the next step: design (`sdlc:designing-solutions`) or the plan (`plan.md`, `sdlc:writing-plans`). The spec never carries tasks, files or Public Surface: those are the plan's.
