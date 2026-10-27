# UI work (every size)

Read when the spec has screens or the change lands in `areas.ui`, at the step that writes the three files; it holds for every later phase of the feature.

- The spec names each screen's states (loading, empty, error, success) and its real copy. Look and layout come from `<docs>/design-system.md`, not from the spec.
- Before the build, map each changed screen to the components, tokens and patterns of `<docs>/design-system.md` in `plan.md`'s `## UI mapping` (S too: every size has a `plan.md`), so the builder and `sdlc:ui-reviewer` read it from a file. Anything the system lacks goes to the user first; an approved addition goes into `<docs>/design-system.md` before the build, logged with `state.py log`.
- Review: a diff touching `areas.ui` always gets the UI review recommended (`review.md`); on M and L the user can decline it, on S it runs. `sdlc:ui-reviewer` gets `<docs>/design-system.md`, the spec and the diff. Its high findings are off-system values or components, generic AI-slop styling, missing states and accessibility blockers.
