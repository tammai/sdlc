---
name: sdlc-force-push-main
enabled: true
event: bash
action: block
conditions:
  - field: command
    operator: regex_match
    pattern: \bgit\s+push\b(?=.*(\s--force(-with-lease)?\b|\s-f\b|\s\+\S))(?=.*\b(main|master)\b)
---

**Blocked: force-push to main/master** (including `--force-with-lease`). Rewriting shared history needs the user to do it themselves.
