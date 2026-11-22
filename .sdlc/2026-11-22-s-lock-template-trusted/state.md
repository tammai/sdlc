# 2026-11-22-s-lock-template-trusted
Status: done
Process: 3
Track: S   (footprint: 2 files)
Risk: high   (untrusted input (committed lock) reaching a file path)
Top model: opus
Base: 3d769dc
Owner: 3235400+tammai@users.noreply.github.com
Tool: claude-code
Verified: 3d769dc tree c37535732614eaf1ccdc8c90f7ab778b0528af26
Current: Stage 4 – Ship

## Tasks
1. **One template and destination check on every route** — AC-001 AC-002
   - Files: `scripts/scaffold.py`, `tests/test_scaffold.py`

## Public Surface
- none

## Gate log
- 2026-11-22 Stage 1: pass
- 2026-11-22 full suite: OK on Python 3.10
- 2026-11-22 Stage 2: pass — security review: 3 rounds, PASS

## Deviations
- 2026-11-22 setup What: the repo isn't set up for sdlc (the plugin's own repo). Why: as earlier features here. Effect: the full suite runs by hand on Python 3.10.
- 2026-11-22 tests/test_stack_blueprints.py What: the concurrent-save fixture's template t1 becomes templates/project/t1.md. Why: the new check refuses a template outside templates/; the test is about merging, not template names. Effect: one fixture line.
- 2026-11-22 scripts/scaffold.py template_problem, git_internal, BUILTINS What: module helpers behind the one check. Why: AC-001 and AC-002. Effect: internal to scaffold.py; no CLI or config surface changes.
- 2026-11-22 scripts/scaffold.py _git_segment, git_internal(root), cmd_record, cmd_upgrade_plan, eject_plan; tests/test_scaffold.py, tests/test_stack_blueprints.py What: the .git rule checks every segment of the written and the resolved path (links, .git. and .git trailing space, GIT~1, NTFS streams, nested .git); upgrade and eject list such an entry as outside; record normalises its template like render; the AC tests cover every form, guarded links, and the save route. Why: security review r1 S-1, S-3, S-4, S-5, F-1. Effect: S-2 (untracked local files) is a todo.
- 2026-11-22 scripts/scaffold.py cli_template, _templates_base, cmd_preview, cmd_upgrade_plan add lists; skills/setting-up-projects/references/upgrade.md; tests/test_scaffold.py What: one CLI normaliser for render, record and preview that refuses a blank name; the add and invariants lists list a destination in a .git folder as outside; the templates base is cached; upgrade.md's Outside names .git; the AC-001 test accepts the backslash form from the CLI on Windows only, directory symlinks pass target_is_directory. Why: security review r2 R2-1, R2-2, R2-4, R2-6, R2-7, F-2, F-3 (the user chose one more fix round). Effect: R2-3 and R2-5 are todos.

## Open questions
-
