# UI work (every size)

Read when the spec has screens or the change lands in `areas.ui`, at the step that writes `<change>` and the plan; it holds for every later phase of the feature.

- The spec names each screen's states (loading, empty, error, success) and its real copy. Look and layout come from `<docs>/design-system.md`, not from the spec.
- Before the build, map each changed screen to the components, tokens and patterns of `<docs>/design-system.md` in the state file's `## UI mapping` (S too), so the builder and `sdlc:ui-reviewer` read it from a file. Anything the system lacks goes to the user first; an approved addition goes into `<docs>/design-system.md` before the build, logged with `state.py log`.
- Review: a diff touching `areas.ui` always gets the UI review recommended (`flow.md`'s Review, `s-track.md`); on M and L the user can decline it, on S it runs. `sdlc:ui-reviewer` gets `<docs>/design-system.md`, the spec and the diff. Its high findings are off-system values or components, generic AI-slop styling, missing states and accessibility blockers.

## impeccable mode (`scaffold.py design` says `impeccable`)

UI design work goes to the impeccable skill; sdlc keeps the record, the gates and the review verdict. `<docs>/design-system.md` points at `DESIGN.md`, which is the system the lines above mean.

- **Define:** run `/impeccable shape <screen or flow>` for the change's UI. Its brief is shown in chat only, so copy the confirmed brief into the state file's `## UI mapping`, and its states and real copy into `<change>`'s ACs. No `DESIGN.md` yet: map against the brief and the existing screens. Don't add a task to write it: impeccable writes `DESIGN.md` through its own process, when a change builds a new surface with it or when the user runs `/impeccable document`; with no styles yet that starts a multi-round design interview, too big to ride on a small change.
- **Build:** build the UI through impeccable (a new surface as an ordinary impeccable request, a refinement with its scoped command: `layout`, `typeset`, `harden`, `adapt`, `clarify`, …). Its detector hook reports after UI edits; fix what it reports like a failing check. sdlc doesn't install `sdlc-ui-hardcoded-values` in this mode.
- **Review:** the UI row fires as usual; `sdlc:ui-reviewer` reads the mode itself and adds impeccable's `detect` and `audit` as evidence. Don't run `critique` in Review: it asks the user questions and writes files.
- **impeccable missing here** (`scaffold.py design` says `"impeccable_installed": false`, or its launcher fails): say so in one line and follow the builtin lines above for this step, mapping against `DESIGN.md` if it exists, else the neighbouring screens (`design-system.md` is only a pointer in this mode); never install it.
