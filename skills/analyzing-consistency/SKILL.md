---
name: analyzing-consistency
description: Use after the implementation plan is written and before coding starts, to check spec.md, design.md and plan.md against each other (and the constitution) for gaps, conflicts, ambiguity and uncovered requirements. Read-only.
---

# Analyzing Consistency

Adapted from GitHub Spec Kit's `analyze` command (MIT, see NOTICE.md).

**Read-only.** Do not edit any file. Produce a report, then offer fixes the user must approve.

The constitution (`.sdlc/constitution.md`, if present) is non-negotiable here: a conflict with a MUST principle is always CRITICAL, and the fix is to change the spec/design/plan, not to reinterpret the principle.

## 1. Load (only what you need)

- **spec.md:** overview, functional requirements (FR-), success criteria (SC-), user stories, edge cases
- **design.md** (+ data-model.md, contracts/): architecture choices, entities, constraints
- **plan.md:** task numbers, descriptions, files touched, tests per task
- **constitution:** MUST/SHOULD statements

If spec, design or plan is missing, stop and name the stage that should produce it.

## 2. Build the maps (internal)

- Requirement inventory keyed by FR-/SC- id. Include only success criteria that need buildable work (load tests, audit tooling); leave out business KPIs.
- User actions with their acceptance criteria.
- Task → requirement coverage (by explicit id or clear keyword match).

## 3. Detection passes (max 50 findings, summarize the rest)

- **Duplication:** near-duplicate requirements
- **Ambiguity:** vague adjectives without numbers; leftover TODO/???/placeholders
- **Underspecification:** requirements missing an object or measurable outcome; stories without acceptance criteria; tasks touching files/components the design never mentions
- **Constitution:** anything conflicting with a MUST; missing mandated gates
- **Coverage gaps:** requirements with no task; tasks with no requirement; performance/security/availability criteria with no task or test
- **Inconsistency:** the same concept named differently across files; entities in the design but not the spec (or reverse); task order that builds on something not yet built; contradictory requirements

## 4. Severity

- **CRITICAL:** constitution MUST violated, core artifact missing, or a baseline requirement with zero coverage
- **HIGH:** conflicting/duplicate requirement, ambiguous security or performance attribute, untestable acceptance criterion
- **MEDIUM:** terminology drift, missing non-functional coverage, underspecified edge case
- **LOW:** wording, minor redundancy

## 5. Report

```markdown
## Consistency Report

| ID | Category | Severity | Location | Summary | Recommendation |
|----|----------|----------|----------|---------|----------------|

**Coverage**
| Requirement | Has task? | Task numbers | Notes |

**Constitution issues:** …
**Unmapped tasks:** …
**Metrics:** requirements, tasks, coverage %, ambiguities, duplicates, critical count
```

Stable IDs prefixed by category letter (A1, C2…). Same inputs → same IDs.

## 6. Next actions

- Any CRITICAL → fix before implementation; name which stage to revisit (spec, design or plan).
- Only MEDIUM/LOW → may proceed; list suggested improvements.
- Ask: "Want concrete edits for the top N issues?" Apply nothing without a yes.
