---
paths:
  - "tests/**/*"
---

# Tests

- Start shell scripts with `helpers.BASH`, never a bare `"bash"` — why: [bare bash is WSL on Windows](../../knowledge/gotchas/windows-bash-is-wsl.md)
- Run the suite on Python 3.10 only (`py -3.10 -m unittest discover -s tests -t tests`), not the default `python3` as well: below 3.15 it shows the cp1252 crashes 3.15's UTF-8 default hides — why: [Windows stdout encoding](../../knowledge/gotchas/windows-stdout-encoding.md)
