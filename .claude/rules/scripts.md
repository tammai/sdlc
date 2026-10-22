---
paths:
  - "scripts/**/*"
---

# Scripts

- A script that prints non-ASCII (`ensure_ascii=False`, emoji, arrows) calls `sys.stdout.reconfigure(encoding="utf-8")` first — why: [Windows stdout encoding](../../knowledge/gotchas/windows-stdout-encoding.md)
