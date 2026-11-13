# Todo

## Open

- [ ] Let a project configure which sdlc stages run, e.g. skip the security review or the PR/CI step — not built yet; stage gates are fixed today in the orchestrator (2026-10-25)
- [ ] Add a Definition of Done to the setup step so the agent knows when a job is done — not built yet (2026-10-25)
- [ ] Add a team mode to the orchestrator: when active, role-based agents drive the sdlc stages — not built yet (2026-10-25)
- [ ] Add an advisory-only use case: the sdlc skills and agents as aids, with no hooks, gates or guardrails, for projects that already have a workflow that would conflict; setup asks which mode to use — not built yet; related to the configurable-stages item above (2026-10-26)
- [ ] `hooks/gitutil.py` (path list) and `hooks/verify_freshness.py` (`is_code_file`) also test `rel.startswith("..")`, so a project path like `..hidden/` reads as outside the project; use the segment check role_guard now uses — left out of the role_guard fix (2026-11-05)

- [ ] H1: `verify.py full()` passes an acceptance test that ran zero tests (`Ran 0 tests … OK`, `[no tests to run]`); treat NOT_RUNNABLE/NOT_FOUND output as did-not-run, as `red_one()` does — whole-plugin review, session sdlc-f2, left out of the workbench branch by the user's choice (2026-11-13)
- [ ] H2: upgrade overwrites a file the user merged (the merged file's hash is stored as if unedited; next upgrade lands it in replace); store the pure render's hash per entry and replace only when disk matches it — whole-plugin review (2026-11-13)
- [ ] H3: the committed lock file's `template` field is trusted (absolute or `../` paths copy any local file into the repo on upgrade); allow only `builtin:*` or a path under templates/ with realpath inside the plugin, generated destinations limited to shipped files — whole-plugin review (2026-11-13)
- [ ] The Stop security review can't see uncommitted changes in a workbench's gitignored app repos (app-repo commits are reviewed at commit time since the workbench fix); make the Stop review take branched repos' diffs — whole-plugin review H4 remainder (2026-11-13)
- [ ] Whole-plugin review mediums and lows outside the workbench, M1–M21 and L1–L11 (lazy-fetch in reporesolve's nested-repo scan, red records not pinning the Run command, bold backlog IDs in state.py, PowerShell commits unreviewed, ReDoS in security patterns and area globs, sg-python cache, doctor on object `packages`, Cursor's bare python3, hookify-list globs, find-polluter.sh, doc contradictions): the list and repro folders are in session sdlc-f2's report — whole-plugin review (2026-11-13)

## Done

- [x] Update the Discover stage to always write down the complete intent and the brainstorming, in a form both a human and a machine can review easily — done: the spec's `## Intent` section (four-phases feature, Define) (2026-10-26)
