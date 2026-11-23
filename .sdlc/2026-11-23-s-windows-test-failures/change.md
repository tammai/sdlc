# The test suite passes on Windows

## Why

**Request (verbatim):** "15 tests fail on this Windows machine -> work on it" (the todo: 15 tests fail on Windows on main c8fc4b5, Python 3.10, Git Bash, in `test_workbench` StopReviewEveryRepo/StopReviewRepo, `test_modes` and `test_scaffold`; CI on Linux passes them).

**Proof:** `tests/test_security_reminder.py` › `test_the_background_sdk_install_never_runs_in_the_project_folder` fails: the hook starts the background Agent SDK install with the project folder as its working directory.

**Root cause:** four causes, one of them in the plugin.
- **Plugin:** `_maybe_bootstrap_agent_sdk_async` (security_reminder_hook.py) starts `ensure_agent_sdk.py --now` detached, in the hook's cwd. On Windows a folder a running process sits in can't be deleted or renamed, for as long as the install runs. In the suite, the cleanup of the test's repo failed (WinError 32).
- **Tests:** the Stop review fixture ran the hook on Python 3.10 without `PYTHONUTF8=1`, which hooks.json always sets, so the `—` in the provenance banner reached stderr as cp1252 and the test's UTF-8 reader crashed (9 errors).
- **Tests:** git spells a repo root `C:/x` on Windows; five assertions compared it with `os.path`'s `C:\x` as text.
- **Tests:** `shutil.rmtree` can't delete git's read-only object files on Windows; a JSON refusal's escaped backslashes were matched as plain text.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| The background install starts in the plugin's state dir, with the project passed as `CLAUDE_PROJECT_DIR` (kept when already set) | the plugin folder | the installer already runs its own children in the state dir, and reads `CLAUDE_PROJECT_DIR` before its cwd |
| The Stop review fixture sets `PYTHONUTF8=1` | ASCII-only hook output, or `reconfigure` in the hook | every production path (sg-python.sh, the hooks.json fast path) sets it; the test should run the hook the same way |
| The fixture marks the install throttle as just spawned | a new environment switch | no test should start a real install; the throttle already exists |
| Compare repo roots as normalised paths in the tests | normalising `resolve_repo_root`'s result | the hook compares git's spelling with git's spelling and real paths with real paths; only the tests mixed them |
| One `rmtree` in `tests/helpers.py` that clears read-only files | `ignore_errors=True` | the test removes `.git` on purpose and needs it gone |

## Acceptance criteria

- **AC-001** The hook's background Agent SDK install never runs in the project folder, and still gets the project as `CLAUDE_PROJECT_DIR`.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_security_reminder.py › SecurityReminderTest.test_the_background_sdk_install_never_runs_in_the_project_folder | `python3 -m unittest discover -s tests -t tests -p test_security_reminder.py -k test_the_background_sdk_install_never_runs_in_the_project_folder` |

## Must never break

- The suite on Linux (CI) and the 15 tests named in the request, now passing on Windows.
- The installer still finds the session's repo (`_near_git_repo` reads `CLAUDE_PROJECT_DIR` first).

## Out of scope

- Hooks writing non-ASCII to stderr when started without `PYTHONUTF8` (not a path any host uses: Claude Code's commands set it).

## Review

No review ran: no trigger fired.
