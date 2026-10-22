---
name: sdlc-reset-hard
enabled: true
event: bash
action: warn
conditions:
  - field: command
    operator: regex_match
    pattern: \bgit\s+(reset\s+--hard|clean\s+-\S*f|checkout\s+--\s+\.|restore\s+(--staged\s+)?\.(\s|$))
---

**Discards uncommitted work.** Check `git status` first and make sure nothing the user or another agent wrote is lost; prefer `git stash`.
