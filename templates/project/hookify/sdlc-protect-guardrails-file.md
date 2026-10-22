---
name: sdlc-protect-guardrails-file
enabled: true
event: file
action: block
conditions:
  - field: file_path
    operator: regex_match
    pattern: (^|[\\/])\.claude[\\/]hookify[\\/]sdlc-[^\\/]+\.md$
---

**Blocked: editing a plugin guardrail.** The `sdlc-*.md` rules keep the other guardrails honest, so Claude doesn't change or disable them. Ask the user to edit the file, or to delete the rule if it's wrong for this repo.
