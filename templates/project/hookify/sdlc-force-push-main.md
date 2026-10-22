---
name: sdlc-force-push-main
enabled: true
event: bash
action: block
conditions:
  - field: command
    operator: regex_match
    pattern: \bgit(\s+(-[Cc]\s+\S+|--(git-dir|work-tree|namespace|exec-path)\s+\S+|--?\S+))*\s+push\b((?=(\\\n|[^;&|\n])*(\s--force(-with-lease)?\b|\s-[a-z]*f[a-z]*(\s|$)|\s\+\S|\s--delete\b|\s:\S))(?=(\\\n|[^;&|\n])*\b(main|master)\b)|(?=(\\\n|[^;&|\n])*\s--mirror\b))
---

**Blocked: force-push to, deletion of, or mirror-push over main/master** (including `--force-with-lease`). Rewriting shared history needs the user to do it themselves.
