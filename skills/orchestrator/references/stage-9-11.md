# Stages 9–11 · Deploy, Operate, Learn

## 9 · Deploy (any track, only when the user asks)
- Use the project's existing deploy path (scripts, CI job, platform CLI). Platform integrations: `integrations.md`.
- Write `<intents>/release.md`: version, environment, steps run, smoke test, rollback command.
- **Gate:** explicit user go-ahead before any production deploy or DB migration; smoke test passes.

## 10 · Operate (parked: no track runs it)
- Skipped on every track until the team has a monitoring process; strike it out in state. Run it only if the user asks.
- Agree a watch window and 1–3 signals (error rate, a key metric, latency). Check them with whatever monitoring the project has (`integrations.md`).
- **Gate:** signals within threshold for the window, or a rollback/fix ticket.

## 11 · Learn (L track; M every few features)
1. `<intents>/retro.md`: what worked, what to change next time (3–5 bullets). This is history; it is not loaded by future sessions.
2. Promote durable lessons with `sdlc:managing-knowledge` (3-tier loading). Use `/sdlc:revise-claude-md` to gather candidates from the session; the skill decides the tier:
   - tier 1 `CLAUDE.md` (≤ 60 lines): only what nearly every task needs
   - tier 2 `.claude/rules/<area>.md` with `paths:`: loads automatically when matching files are touched
   - tier 3 `knowledge/**.md` (OKF): linked from `knowledge/index.md` and from the tier-2 rule
   Always add `knowledge/features/<feature>.md` linking spec, design and retro.
3. A defect review found that has come up before (in this feature or earlier ones): add one line to `<docs>/recurring-defects.md` (create it from the shape in `recurring-defects.md`), so every later reviewer checks it.
4. Corrected twice and mechanically checkable → `/sdlc:hookify` (`sdlc:writing-hook-rules` for syntax), not more text.
5. Constitution changed in practice? → `sdlc:project-constitution` to amend.
6. CLAUDE.md over 60 lines → run the audit in `sdlc:managing-knowledge`.
- **Gate:** every promoted lesson is linked from `knowledge/index.md` or a tier-2 rule; CLAUDE.md ≤ 60 lines; `state.py set <f> Status done`.
