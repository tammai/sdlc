---
name: knowledge-audit
description: Audits CLAUDE.md, .claude/rules and knowledge/ against the 3-tier budget and proposes moves to keep always-loaded context small.
---

Use the `sdlc:managing-knowledge` skill and run its **Audit** section on this repo. If `knowledge/` doesn't exist yet, run its **Set up** section first.

Show the proposed moves (file → tier, with one-line reasons) and the CLAUDE.md line count before → after. Apply only what the user approves, then update `knowledge/index.md` and `knowledge/log.md`.
