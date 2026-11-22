# A committed lock can't make upgrade copy a file from outside the plugin

## Why

From `.sdlc/todo.md`: "H3: the committed lock file's `template` field is trusted (absolute or `../` paths copy any local file into the repo on upgrade); allow only `builtin:*` or a path under templates/ with realpath inside the plugin, generated destinations limited to shipped files — whole-plugin review (2026-11-13)".

`.sdlc/scaffold.lock.json` is committed, so anyone who can change the repo can change it, and cloning a repo isn't consent (`knowledge/gotchas/repo-config-is-untrusted.md`). Proof: a lock entry whose `template` is an absolute path, a `../` path or a link out of `templates/` is read by `render_source`. The next upgrade then writes that file's text (an SSH key, a token) into the repo, where a commit takes it away. Root cause: `render_source` and `template_exists` join any string onto the plugin root and open it.

## Decisions

- **One check, `template_problem()`, on every route a template name arrives by:** the lock read back from disk, and the `render`, `record --template` and `preview` arguments. A template is one of the plugin's: a known `builtin:` name (`builtin:ci:<package>` with a plain package name), or a relative path under `templates/` with no `..` segment, whose resolved path (after links) is still inside the plugin's `templates/` folder. The rule runs on both the written and the resolved form, and a path on another drive counts as outside.
- **No recorded or rendered file under `.git/`** (the first segment, in any case): an overwrite there would touch git's own hooks and config.
- **Ruled out:** limiting generated destinations to a fixed list of shipped files, as the todo suggested. Setup renders generated files to many legitimate places (`.claude/rules/sdlc*.md`, `.github/workflows/sdlc-*.yml`, `.github/CODEOWNERS`, the monorepo READMEs, `.sdlc/ci/`), so a list would break real repos. Inside the work tree, whoever can commit the lock can commit the destination file itself. What the lock adds is reach outside the repo, which the template check closes, and into `.git/`, which the destination check closes.

## Acceptance criteria

- **AC-001** A lock entry whose template is an absolute path, a `../` path, a `templates/../` path, a link from `templates/` to a file outside, an unknown `builtin:` name or a plugin file outside `templates/` is refused, and the message names the entry. Nothing is written. The same templates given to `render` or `record --template` are refused too.
- **AC-002** `render` to a destination under `.git/` (any case, with or without `./`) is refused and writes nothing, and a lock entry under `.git/` is refused.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_scaffold.py › ScaffoldTest.test_a_lock_template_outside_the_plugins_templates_is_refused | `python3.10 -m unittest discover -s tests -t tests -p test_scaffold.py -k test_a_lock_template_outside_the_plugins_templates_is_refused` |
| AC-002 | tests/test_scaffold.py › ScaffoldTest.test_nothing_is_recorded_or_rendered_under_git | `python3.10 -m unittest discover -s tests -t tests -p test_scaffold.py -k test_nothing_is_recorded_or_rendered_under_git` |

## Must never break

- Every template the skills render (`templates/project/...` and the `builtin:` ones, `builtin:ci:<name>` included) still renders and upgrades as before: the rest of `test_scaffold` passes.
- A lock entry without a template (a file recorded by hand) is still accepted.

## Failure modes

- Untrusted input reaching a file path: the lock and the CLI arguments both go through the one check, on the written and the resolved path.
- A containment check across Windows drives: `commonpath`'s `ValueError` counts as outside.

## Out of scope

- The convention entries' templates, which `convention_updates` already checks against the conventions the plugin renders.

## Review

- **Fired:** security, because `Risk: high` (untrusted input reaching a file path). It ran without stopping, as S does: `sdlc:code-reviewer` on opus.
- **Round 1, FAIL:** S-1 (high) the `.git` rule saw only the written path's first segment. A committed link `x -> .git`, the Windows aliases (`.git.`, `GIT~1`, NTFS streams) and a nested `sub/.git` all passed. Fixed: every segment of the written and the resolved path is checked, and upgrade and eject list such an entry as outside. S-3, S-4, S-5 and F-1 were fixed too: a guarded symlink, test gaps, record normalising its template, a doubled check.
- **Round 2, FAIL:** R2-1 (high) the AC-001 test expected Windows' native `templates\project\ci.yml` refused from the CLI. The user granted round 3. Fixed: one CLI normaliser (`cli_template`) for render, record and preview, which refuses a blank name. Also fixed: R2-2, R2-4, R2-6, R2-7, F-2 and F-3 (upgrade.md's Outside step).
- **Round 3, PASS.** Its lows are tickets, none a bug: `guardrails --render` reports a guardrail whose folder links into `.git` as kept rather than outside (nothing is written); the Windows separator case is skipped rather than asserted; the invariants-loop `.git` check has no test; `_templates_base`'s cache ignores a `PLUGIN_ROOT` patched in-process.
- **Tickets in `.sdlc/todo.md`:** S-2 (a `generated` lock entry can overwrite or delete an untracked local file), R2-3 (the AGENTS.md, .gitignore and settings writers follow a committed link) and R2-5 (HFS+ ignorable code points, unconfirmed). All three predate this change.
- **Decision kept:** no fixed list of generated destinations (see Decisions). S-2 is the real remainder of that idea.
