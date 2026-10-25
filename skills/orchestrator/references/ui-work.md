# UI work (any track and flow)

Read when the spec has screens or the change lands in `areas.ui`, at the first step that writes the spec, plan or S brief; it holds for every later stage of the feature.

- The spec names each screen's states (loading, empty, error, success) and its real copy. Look and layout come from `<docs>/design-system.md`, not from the spec.
- Without Stage 2 (S, Lite, or M with an obvious approach): before the build, map each changed screen to the components, tokens and patterns of `<docs>/design-system.md`. M: a `UI mapping` section in the plan (Lite: in the spec's Tasks); S: one `state.py log` line, carried into the implementer's brief. Anything the system lacks goes to the user first; an approved addition goes into `<docs>/design-system.md` before the build, logged, so the implementer and `sdlc:ui-reviewer` work from the updated system.
- Review: also dispatch `sdlc:ui-reviewer`, on every track and flow, with `<docs>/design-system.md`, the spec and the diff (the UI bullets in `stage-6-review.md` give severity, the visual check and proposed design-system changes).
