---
name: sdlc-console-log
enabled: true
event: file
action: warn
conditions:
  - field: file_path
    operator: regex_match
    pattern: \.(ts|tsx|js|jsx|mjs|cjs|vue|svelte)$
  - field: new_text
    operator: regex_match
    pattern: \bconsole\.(log|debug)\(
---

**`console.log` added.** Remove debug output before finishing, or use the project's logger if it should ship.
