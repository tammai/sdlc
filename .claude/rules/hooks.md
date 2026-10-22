---
paths:
  - "hooks/**/*"
  - "core/**/*"
---

# Hooks

- A hook stays silent outside the state it guards (no `.sdlc/` feature, wrong stage) and never blocks on its own error: catch, exit 0, no output.
- Deny or block with `hookSpecificOutput.permissionDecisionReason`; `systemMessage` only reaches the user.
- Every behavior change gets a subprocess test through `tests/helpers.py` `run_hook`.
