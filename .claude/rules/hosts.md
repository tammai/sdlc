---
paths:
  - "hosts/**/*"
  - "scripts/hosts.py"
---

# Other agents (hosts/)

- Never answer `allow` for another agent, and check what its "no opinion" output is before adding one: Antigravity denies on `{}` — why: [host hook answers](../../knowledge/gotchas/host-hook-answers.md)
- Capture a host's real hook payloads before adapting to them; forum posts and docs have been wrong.
