# Stage 7 · Security

- Already running: security-guidance hooks (Claude Code: pattern warnings on edits, diff review at turn end, agentic review on `git commit`/`git push`). Address every finding they raise.
- Explicit pass (full Stage 7: L, or risk high): dispatch `sdlc:feature-reviewer` and `sdlc:code-reviewer` with a security-only brief (injection, authz, secrets, SSRF, XSS, unsafe deserialization, dependency risk). Run the stack's dependency audit (`npm audit --omit=dev`, `pip-audit`, …).
- "Light" (M track): hook findings + dependency audit only.
- Deeper scans (optional, not bundled): see `integrations.md`.
- A code change made to fix a security finding sends the feature back to Stage 5, as in Stage 6.
- **Gate:** no critical/high open; no secrets in the diff → `<intents>/security.md`. Then `state.py advance <f> 8 --gate pass`.
