---
type: gotcha
title: A question-tool answer is not a prompt
description: AskUserQuestion fires no UserPromptSubmit and the agent can pre-fill answers; gates trust a Pre-recorded call's PostToolUse.
tags: [hooks, claude-code, orchestrator]
updated: 2026-11-12
---

# A question-tool answer is not a prompt

## Symptom
A hook gate that waits for "the user's next prompt" (`hooks/review_rounds.py`, `hooks/trust_anchor.py`) stays shut when the user answers an `AskUserQuestion` dialog. 3.2.0 to 3.6.1 handled this by making those two gates typed replies, which users found easy to miss.

## Cause
An `AskUserQuestion` answer comes back as the tool's result inside the same turn, so it never fires `UserPromptSubmit`. The tool's input also has an `answers` field the caller can fill. A PostToolUse hook alone therefore can't tell the user's pick from one the agent wrote.

## Fix
`hooks/user_answer.py` runs on PreToolUse for AskUserQuestion. It denies a call whose `answers` is already filled and records the `tool_use_id` of every other call. The gates then run on PostToolUse for AskUserQuestion and accept an answer (`user_answer.answered`) only when its id was recorded and the question's header names the gate (`Review cap`, `Trust anchor`). Checked under Claude Code 2.1.322: PreToolUse sees `tool_input` without `answers` on a clean call and with them on a pre-filled one, and PostToolUse carries the user's pick in both `tool_input.answers` and `tool_response.answers`. Other hosts don't wire this, so the gates there stay typed replies.
