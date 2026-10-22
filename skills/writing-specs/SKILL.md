---
name: writing-specs
description: Use when turning a feature request or a brainstorm into a written requirements spec (what and why, no implementation), before any design or planning. Writes .sdlc/<feature>/spec.md and a spec-quality checklist.
---

# Writing Specs

Adapted from GitHub Spec Kit's `specify` command (MIT, see NOTICE.md).

A spec says **what** users need and **why**. It never says how: no languages, frameworks, APIs or code structure. It is written so a non-technical stakeholder could approve it.

## Inputs

- The feature request, and `.sdlc/<feature>/brainstorm.md` if Stage 1 started with brainstorming.
- `.sdlc/constitution.md` if it exists (project principles; treat MUST rules as hard constraints).
- Template: `${CLAUDE_PLUGIN_ROOT}/templates/spec-template.md`

## Steps

1. **Name the feature.** 2–4 word kebab-case slug, action-noun where possible (`user-auth`, `fix-payment-timeout`). Keep technical terms (OAuth2, JWT). The feature directory is `.sdlc/<slug>/`. If the orchestrator already chose a slug, use it.
2. **Copy the template** to `.sdlc/<slug>/spec.md` and fill it, keeping section order and headings.
3. **Extract** actors, actions, data, constraints from the request.
4. **Unclear points:** make an informed guess from context and industry norms, and record it under Assumptions. Mark `[NEEDS CLARIFICATION: <specific question>]` only when the choice changes scope or UX, several reasonable readings exist, and no sensible default does. **Maximum 3 markers.** Priority: scope > security/privacy > UX > technical detail.
5. **User scenarios** with acceptance scenarios (Given/When/Then). If no clear user flow exists, stop and say so.
6. **Functional requirements** `FR-001…`: each one testable, each tagged with its source: `[user]` (the user asked), `[clarified]` (a user answer settled it) or `[inferred]` (you added it). Be strict: "the user would probably want it" is `[inferred]`. Common inferred creep: admin/settings UI, audit logging, i18n, pagination, caching, rate limiting, bulk operations, export, notifications, configurability, "support for future X".
7. **Success criteria** `SC-001…`: measurable and technology-agnostic (time, volume, completion rate, satisfaction), each verifiable without knowing the implementation, with the same source tags. A load or scale number the user didn't give is `[inferred]`.
7a. **Non-goals:** list what this feature deliberately leaves out, including the obvious extensions a designer might add "while we're at it". This is what stops Stage 2 and 3 from adding them back.
8. **Key entities** if data is involved.
9. **Edge cases**: negative paths, empty/error states, limits.

## Quality check

Write `.sdlc/<slug>/checklists/requirements.md`:

```markdown
# Spec Quality Checklist: <feature>

## Content Quality
- [ ] No implementation details (languages, frameworks, APIs)
- [ ] Focused on user value and business needs
- [ ] Readable by non-technical stakeholders
- [ ] All mandatory sections completed

## Requirement Completeness
- [ ] No [NEEDS CLARIFICATION] markers remain
- [ ] Requirements are testable and unambiguous
- [ ] Success criteria are measurable and technology-agnostic
- [ ] Acceptance scenarios defined for every user story
- [ ] Edge cases identified
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
- Failing items (other than clarifications): fix the spec and re-check, up to 3 rounds. Anything still failing goes in the checklist notes, and you tell the user.
- Remaining `[NEEDS CLARIFICATION]` markers: present all of them (max 3) together, each as:

  **Question N: <topic>** — context (quote the spec line), what we need to know, then a table of options A/B/C/Custom with the implication of each. Wait for answers ("Q1: A, Q2: Custom – …"), write them into the spec, re-check.

## Inferred requirements at the gate

The orchestrator's Stage 1 gate lists every `[inferred]` FR/SC on its own, separate from the rest of the spec:

```
I added these; none were in your request. Dropped unless you keep them:
- FR-004 log all security events — why I added it: <one line>
- SC-003 90% first-attempt completion — why: <one line>
Keep any? (e.g. "keep FR-004", or "none")
```

Kept → retag `[clarified]`. Dropped → delete it and add a line to Non-Goals (`No security-event logging (was FR-004 [inferred])`), and don't renumber (gaps in ids are fine). The spec leaves Stage 1 with no `[inferred]` tags.

## Done

Report: spec path, checklist result (x/y passing), the `[inferred]` list for the gate, and the next step — `sdlc:clarifying-specs` if ambiguity remains in high-impact areas, otherwise design (`sdlc:designing-solutions`).
