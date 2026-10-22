---
name: sdlc-sensitive-files
enabled: true
event: file
action: warn
conditions:
  - field: file_path
    operator: regex_match
    pattern: (^|[\\/])\.env(\.|$)|credential|secret|\.(pem|key|p12|pfx)$|(^|[\\/])id_(rsa|ed25519)
---

**Sensitive file.** Never write real secrets: use placeholders, keep the file git-ignored (except `.env.example`), and read secrets from the environment.
