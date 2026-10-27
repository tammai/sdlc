# UI work (any track and flow)

Read when the spec has screens or the change lands in `areas.ui`, at the step that writes `intent.md` and the spec; it holds for every later phase of the feature.

- The spec names each screen's states (loading, empty, error, success) and its real copy. Look and layout come from `<docs>/design-system.md`, not from the spec.
- Without a design (S, or M with an obvious approach): before the build, map each changed screen to the components, tokens and patterns of `<docs>/design-system.md`. It goes in `plan.md`'s `## UI mapping` (S has no plan: put it in the state file as `state.py log <f> "UI mapping: …"`), so the implementer and `sdlc:ui-reviewer` read it from a file. Anything the system lacks goes to the user first; an approved addition goes into `<docs>/design-system.md` before the build, logged, so the implementer and `sdlc:ui-reviewer` work from the updated system.
- Review: also dispatch `sdlc:ui-reviewer` in Prove (M full, L, and a backlog's Feature close; S, M lite and `Prove: skip` have no Prove), with `<docs>/design-system.md`, the spec and the diff (`prove.md`'s UI step gives severity, the visual check and proposed design-system changes).
