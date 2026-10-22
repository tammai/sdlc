---
paths:
  - "tests/**/*"
---

# Tests

- Start shell scripts with `helpers.BASH`, never a bare `"bash"` — why: [bare bash is WSL on Windows](../../knowledge/gotchas/windows-bash-is-wsl.md)
- On Windows, also run the suite with a Python older than 3.15: 3.15 defaults to UTF-8 and hides cp1252 crashes — why: [Windows stdout encoding](../../knowledge/gotchas/windows-stdout-encoding.md)
