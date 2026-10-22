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
6. **Functional requirements** `FR-001…`: each one testable.
7. **Success criteria** `SC-001…`: measurable and technology-agnostic (time, volume, completion rate, satisfaction), each verifiable without knowing the implementation.
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
- [ ] Scope clearly bounded (in / out)
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

## Done

Report: spec path, checklist result (x/y passing), and the next step — `sdlc:clarifying-specs` if ambiguity remains in high-impact areas, otherwise design (`sdlc:designing-solutions`).
