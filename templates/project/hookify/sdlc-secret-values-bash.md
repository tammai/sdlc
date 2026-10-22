---
name: sdlc-secret-values-bash
enabled: true
event: bash
action: block
conditions:
  - field: command
    operator: regex_match
    pattern: (sk-ant-[a-z0-9_-]{20,}|sk-proj-[a-z0-9_-]{20,}|sk-[a-z0-9]{32,}|gh[pousr]_[a-z0-9]{30,}|github_pat_[a-z0-9_]{30,}|[rs]k_live_[a-z0-9]{20,}|AIza[0-9a-z_-]{35}|AKIA[0-9A-Z]{16}|xox[baprs]-[a-z0-9-]{10,}|-{5}BEGIN [A-Z ]*PRIVATE KEY)
---

**Blocked: this command contains what looks like a real secret** (API key, token or private key), which would land in shell history and logs. Read it from an environment variable or the secret manager instead.
