# Glossary

| Term | Meaning |
|---|---|
| Phase | Define, Build, Review or Ship; each runs at one internal stage number (1, 2, 3, 4) that the hooks read |
| Gate | Exit criterion for a phase |
| Hard stop | A point where the orchestrator always asks you |
| Stale / fresh | Whether test results predate the latest code change |
| Part (slice) | One piece of work too big for one session, built, verified with `verify.py` and committed on its own; all parts land together |
| Feature close | The one Review over the whole branch, and Ship, after the last part |
| Record | the change file for people and the state file for the agent, both kept for good |
| `Process: 3` | The state-file line that marks a current feature; the hooks act only on those |
| Public Surface | Declared list of everything new that callers or users can see |
| Deviation | A step you chose to skip, or another departure, recorded in `state.md` with `state.py deviation` (Build's drift too) |
| Trust anchor | The hook that shows you changes to what verification trusts |
| Constitution | Project principles in `docs/sdlc/constitution.md`; breaking a MUST rule is a high review finding |
| Design system | `docs/sdlc/design-system.md`: the library, tokens, components and patterns UI work must use; checked by `ui-reviewer`. In impeccable mode (`design` in `.sdlc/config.json`, chosen at setup) it points at impeccable's `DESIGN.md`, Define plans UI with `/impeccable shape`, impeccable builds it, and `ui-reviewer` adds impeccable's `detect` and `audit` as evidence |
| Project commands | `install`, `test`, `lint`, `typecheck`, `build` in `.sdlc/config.json`, per package in a monorepo |
| Baseline | Failures that existed before setup, listed in `.sdlc/baseline.md` so they don't block new work |
| Scaffold version / drift | The plugin version a repo was set up or upgraded with; "behind" means `/sdlc:upgrade` has work to do |
| Generated / seeded | Plugin files that upgrades regenerate / replace only while you haven't edited them |
| Migration | A versioned change to files you own, applied only with your approval |
