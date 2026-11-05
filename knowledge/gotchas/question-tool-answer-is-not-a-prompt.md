---
type: gotcha
title: A question-tool answer is not a prompt
description: AskUserQuestion answers fire no UserPromptSubmit, so a gate lifted by "the user's next prompt" stays a typed reply.
tags: [hooks, claude-code, orchestrator]
updated: 2026-11-05
---

# A question-tool answer is not a prompt

## Symptom
3.2.0 routes every orchestrator stop through `AskUserQuestion`. Two gates can't move there: the review round cap (`hooks/review_rounds.py`) and a trust-anchor notice (`hooks/trust_anchor.py`) lift only on `UserPromptSubmit`.

## Cause
An `AskUserQuestion` answer comes back to the agent as the tool's result inside the same turn. It never fires `UserPromptSubmit`, so a hook waiting for "the user's next prompt" stays shut. Lifting those gates on the tool's `PostToolUse` instead would open them to the agent: the tool's input has an `answers` field the caller can fill, so the answer isn't proof that a person replied. A prompt is the only signal the agent can't fake.

## Fix
Keep a hook gate that needs a person on a typed reply, and say so where the asking rule lists its exceptions (`skills/orchestrator/SKILL.md` **Asking**, mirrored in `commands/start.md`; `flow.md` Review step 3). Everything else asks through the question tool.
