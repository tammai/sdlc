---
name: sdlc-secret-values
enabled: true
event: file
action: block
conditions:
  - field: new_text
    operator: regex_match
    pattern: (sk-ant-[a-z0-9_-]{20,}|sk-[a-z0-9]{32,}|gh[pousr]_[a-z0-9]{30,}|AKIA[0-9A-Z]{16}|xox[baprs]-[a-z0-9-]{10,}|-{5}BEGIN [A-Z ]*PRIVATE KEY)
---

**Blocked: this looks like a real secret** (API key, token or private key). Use an environment variable or the secret manager, and a placeholder in code and examples.
