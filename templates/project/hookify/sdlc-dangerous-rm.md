---
name: sdlc-dangerous-rm
enabled: true
event: bash
action: block
conditions:
  - field: command
    operator: regex_match
    pattern: \brm\s+(-\S*\s+)*-[a-z]*(rf|fr)[a-z]*\s+(-\S+\s+)*(/|~|\$HOME|\.\.?|\*|\.git)/?(\s|;|&|\||$)
---

**Blocked: recursive delete of a root, home, parent, wildcard or `.git` path.** Name the exact directory to remove (e.g. `rm -rf dist`), or ask the user to run it.
