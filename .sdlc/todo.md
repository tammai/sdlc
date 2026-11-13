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
- [ ] Workbench control files the agent can edit: setting `"write": true` or removing an entry in `workbench.json`, or `"workbench": false` in the workbench config, turns the read-only guard, the watch and the app commit review off; guard or watch those files (security-r7 SR7-M3) (2026-11-13)
- [ ] A fake `state.py pr <feature> <repo> <url>` during Ship turns an app repo's commit review off (only the URL's shape is checked); a done feature whose PR is never recorded owns that repo's commits forever (security-r7 SR7-M4, SR7-L2) (2026-11-13)
- [ ] The read-only watch's accept and baseline are protected by a text check only: a deliberate agent can still feed the hook a fake event, import it, or remove both files under another spelling; forged `refs/remotes` make a local commit look pushed; the trust anchor doesn't watch app repos' commands (security-r7 SR7-M1/M2, code-reviewer-r4 M-5/M-7) (2026-11-13)
- [ ] The guard denies reads that merely name the watch's files (`grep read-only-seeded`, a commit message): narrow it to writes and runs (security-r7 SR7-L4) (2026-11-13)
- [ ] `ship.py --waive-baseline` waives any `test: exit` failure without checking that `.sdlc/baseline.md` lists it (a new failing test, or a new `(root) test` failure, ships with the waiver); match the failures against the baseline's rows — 3.8.0 smoke test G (2026-11-13)
- [ ] Undoing a read-only change the user already accepted counts as a new change (the accepted baseline holds the change); consider accepting a return to the first look silently — 3.8.0 smoke test K (2026-11-13)
- [ ] After `/sdlc:upgrade` applies a merge to an edited guardrail, `/sdlc:eject` deletes it; the eject dialog offered to keep it but the report said it wasn't kept — 3.8.0 smoke test H (2026-11-13)

## Done

- [x] Update the Discover stage to always write down the complete intent and the brainstorming, in a form both a human and a machine can review easily — done: the spec's `## Intent` section (four-phases feature, Define) (2026-10-26)
