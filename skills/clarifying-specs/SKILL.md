---
name: clarifying-specs
description: Use after a spec exists and before design, to find the ambiguities that would change what gets built and resolve them with at most 5 targeted questions, writing each answer back into spec.md.
---

# Clarifying Specs

Paths: `<intents>` is the feature's documents folder, `<state>` its state file and `<docs>` the sdlc docs folder (`docs_dir`); `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py" paths <feature>` prints them for this repo's layout.

Adapted from GitHub Spec Kit's `clarify` command (MIT, see NOTICE.md).

Run before `sdlc:designing-solutions`. If the user wants to skip it (e.g. a spike), proceed but say rework risk goes up.

## 1. Load

`<intents>/spec.md` (if missing, run `sdlc:writing-specs` first — don't create a spec here) and `<docs>/constitution.md` if present.

## 2. Scan for gaps

Mark each category Clear / Partial / Missing (keep the map internal):

- **Scope & behavior:** core goals, success criteria, out-of-scope, roles
- **Domain & data:** entities, attributes, relationships, uniqueness, lifecycle/states, volume
- **UX flow:** critical journeys, error/empty/loading states, accessibility, localization
- **Non-functional:** performance targets, scale limits, reliability, observability, security & privacy, compliance
- **Integrations:** external services and their failure modes, formats, versioning
- **Edge cases:** negative paths, rate limits, concurrent edits
- **Constraints & trade-offs:** fixed tech constraints, rejected alternatives
- **Terminology:** canonical terms, conflicting synonyms
- **Completion signals:** testable acceptance criteria
- **Placeholders:** TODOs, vague adjectives ("fast", "robust", "intuitive") without numbers

## 3. Queue questions (max 5 in total)

Only questions whose answer changes architecture, data model, task breakdown, test design, UX behavior, ops readiness or compliance. Skip anything already answered, style preferences, and implementation-method questions. Rank by impact × uncertainty; cover the highest-impact categories first.

Each must be answerable by a 2–5 option choice, or a short answer (≤5 words).

## 4. Ask one at a time

```
**Question:** <full question ending in ?> (FR-xxx optional)
Why it matters: <one plain sentence>

**Recommended:** Option B – <1–2 sentence reason>

| Option | Description |
|---|---|
| A | … |
| B | … |
| Short | Your own answer (≤5 words) |

Reply with a letter, "yes" to take the recommendation, or your own short answer.
```

For short-answer questions give `**Suggested:** <answer> – <reason>` instead of a table.

Never preview upcoming questions. Stop when critical gaps are resolved, the user says done/stop, or 5 questions have been asked.

## 5. Write back after every answer

- Ensure `## Clarifications` → `### Session YYYY-MM-DD` exists; add `- Q: … → A: …`.
- Requirements the answer adds or settles are tagged `[clarified]`; an answer that confirms an `[inferred]` item retags it `[clarified]`, one that rejects it moves it to Non-Goals.
- Apply the answer where it belongs: functional → requirements; roles → user stories; data → entities; non-functional → measurable success criteria; edge case → edge cases; terminology → normalize the term everywhere.
- Replace contradicted text instead of leaving both versions. Save after each answer.
- Re-check `<intents>/checklists/requirements.md` if it exists: toggle only the boxes whose state changed.

## 6. Report

Questions asked/answered, sections touched, checklist before → after (e.g. 12/16 → 15/16), and any high-impact category still Partial/Missing listed as **Deferred** with a reason. Next step: design.

If nothing worth asking: say "No critical ambiguities worth formal clarification" and move on.
