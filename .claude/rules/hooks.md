---
paths:
  - "hooks/**/*"
  - "core/**/*"
---

# Hooks

- A hook stays silent outside the state it guards (no `.sdlc/` feature, wrong stage) and never blocks on its own error: catch, exit 0, no output.
- Deny or block with `hookSpecificOutput.permissionDecisionReason`; `systemMessage` only reaches the user.
- Output stays ASCII (plain `json.dumps`), or call `sys.stdout.reconfigure(encoding="utf-8")` first — why: [Windows stdout encoding](../../knowledge/gotchas/windows-stdout-encoding.md)
- Every behavior change gets a subprocess test through `tests/helpers.py` `run_hook`.
