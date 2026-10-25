# Stage 2 · Design (L track, or M when the approach isn't obvious)

- `sdlc:designing-solutions` → `design.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md` (dispatches `sdlc:code-explorer` and `sdlc:code-architect` agents)
- **Gate (user approves):** every FR/SC maps to the design; every Complexity Tracking row (new module, layer, abstraction, dependency, service, config key, store, UI component, variant or token) cites a requirement; nothing in Non-Goals is designed in; chosen approach + one rejected alternative recorded; constitution check passes.
- UI design-system additions: once the user approves a new component, variant or token here, add it to `<docs>/design-system.md` before Stage 4 and log it (`state.py log`), so the implementer and `sdlc:ui-reviewer` work from the updated system.
