# Slice B1 plan: batched intent questions

Spec FR-01–02, AC 1 · Backlog B1 · Instructed only: no structural tests; checks are `claude plugin validate .` and the existing suite.

## Tasks

1. `skills/orchestrator/SKILL.md` §1, Lite step 1 and the §4 S bullet: before the spec (L: before brainstorming; S: before the brief), one message with only the blocking questions, or none; the rest become `Inferred` / `[inferred]` items with a reason (S: brief and final summary). Stage 1 gate drops `[NEEDS CLARIFICATION]`; `clarifying-specs` only on request. (FR-01, FR-02)
2. `skills/writing-specs/SKILL.md`: no clarification markers; batch answers are `[clarified]`, the rest `[inferred]` or Assumptions. (FR-02)
3. `skills/brainstorming/SKILL.md` "Look Before You Ask": one paragraph — answers from the Stage 1 batch are known; don't re-ask. (FR-02)
4. Docs: spec 02 (new ORC-FR), README gates, guidebook specs bullet, playbook M/L steps, CHANGELOG; stale-docs audit for "[NEEDS CLARIFICATION]", "Maximum 3", "clarifying-specs".

## Public Surface

- none (skill text only)
