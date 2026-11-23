# sdlc (advisory mode)

This repo uses sdlc's skills and agents as aids only (`"mode": "advisory"` in `.sdlc/config.json`). The team's own workflow decides how work is defined, reviewed and shipped; sdlc's hooks, gates and guardrails stay silent here.

- Use a skill or agent when it helps or when asked: brainstorming, test-driven development, systematic debugging, a code, security or UI review agent, QA.
- Don't start sdlc's flow (no change file or state file) unless the user asks for it; `/sdlc:setup mode full` turns it on.
