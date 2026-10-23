---
paths:
  - "scripts/**/*"
---

# Scripts

- A script that prints non-ASCII (`ensure_ascii=False`, emoji, arrows) calls `sys.stdout.reconfigure(encoding="utf-8")` first — why: [Windows stdout encoding](../../knowledge/gotchas/windows-stdout-encoding.md)
- Read a subprocess's output (git especially) with `encoding="utf-8", errors="replace"`, never `text=True`: the code page crashes on non-ASCII paths and bytes — why: [Windows stdout encoding](../../knowledge/gotchas/windows-stdout-encoding.md)
