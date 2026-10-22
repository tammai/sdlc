---
name: sdlc-protect-guardrails-bash
enabled: true
event: bash
action: block
conditions:
  - field: command
    operator: regex_match
    pattern: (\b(rm|mv|cp|ln|tee|truncate|shred)\b|\bgit\s+(rm|mv|checkout|restore)\b|\b(sed|perl)\s+(\S+\s+)*?(-[a-z]*i[a-z]*|--in-place)|(^|[^0-9&])>(?!&))[^;&|\n]*\.claude[\\/]hookify([\\/]sdlc-|[\\/]?\*|[\\/]?["']?(\s|;|&|\||\)|$))
---

**Blocked: changing or removing the plugin guardrails** (`.claude/hookify/sdlc-*.md`). Claude doesn't edit the rules that constrain it. Ask the user to do it.
