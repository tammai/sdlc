# Stage 1 · Discover & specify

- If `knowledge/index.md` exists, read it and open only the docs relevant to this feature (prior decisions, gotchas, related features). Don't read the whole folder.
- The core's **blocking questions, once**, before anything else is written.
- L track: run `sdlc:brainstorming` next (writes `brainstorm.md`); it builds on the answers and spends its questions on approaches. M track: go to the spec.
- `sdlc:writing-specs` → `spec.md` + `checklists/requirements.md`
- `sdlc:clarifying-specs` only when the user asks for it
- UI work: `ui-work.md`.
- **Inferred triage (part of the gate):** show every `[inferred]` FR/SC as its own list, with a one-line reason each; dropped unless the user keeps it (see `sdlc:writing-specs`). Dropped items go to Non-Goals.
- Bigger than one session: the backlog comes with the spec on M (`backlog-slices.md`).
- **Gate (user approves):** checklist passes, no `[inferred]` tags left, Non-Goals filled, acceptance criteria testable. Then `state.py advance <f> <next stage> --gate pass`.
