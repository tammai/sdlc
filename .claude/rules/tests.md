---
paths:
  - "tests/**/*"
---

# Tests

- Start shell scripts with `helpers.BASH`, never a bare `"bash"` — why: [bare bash is WSL on Windows](../../knowledge/gotchas/windows-bash-is-wsl.md)
- Run the suite on Python 3.10 only (`py -3.10 -m unittest discover -s tests -t tests`), not the default `python3` as well: below 3.15 it shows the cp1252 crashes 3.15's UTF-8 default hides — why: [Windows stdout encoding](../../knowledge/gotchas/windows-stdout-encoding.md)
- On Windows, run it from Git Bash, not PowerShell: there `bash` is WSL's, and the ralph, contract-check, doctor and launcher tests fail with `No such file or directory` — why: [bare bash is WSL on Windows](../../knowledge/gotchas/windows-bash-is-wsl.md)
- Never name a test helper after a `unittest.TestCase` method (`fail`, `run`, `debug`): every assertion reports through `self.fail`, so a helper called `fail` swallows each failure and the test passes with no code behind it (found when a red step said the new tests passed before the hook existed, 2026-11-19)
