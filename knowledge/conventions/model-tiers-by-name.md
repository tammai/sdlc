---
type: convention
title: Name model tiers, never "the most capable model"
description: How skills, agents and commands say which model a subagent runs on.
tags: [skills, agents, models]
updated: 2026-10-28
---

# Name model tiers, never "the most capable model"

Say *cheap*, *standard* or *top tier* and point at Model selection in `skills/orchestrator/SKILL.md`, which maps cheap and standard to `sonnet` and top to `opus` (no `haiku`: the model router denies it, ADR 0011). Every review runs on `opus`. Fable is used only when the user opts in (`Top model: fable` in `state.md`).

**Why:** "the most capable available model" and "one tier above" resolved to Fable, which the user never asked for. The `model_router.py` hook now denies such dispatches during an active feature, but outside one only the wording protects.

- Good: "dispatch the review on the top tier (see Model selection)."
- Bad: "dispatch the final review on the most capable available model."

## Related
- [ORC-FR-014, ORC-FR-015](../../docs/specs/02-orchestration.md)
