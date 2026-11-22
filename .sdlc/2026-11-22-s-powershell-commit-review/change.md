# A commit or push through the PowerShell tool gets the commit security review

## Why

From `.sdlc/todo.md`: "A `git commit`/`git push`/`gt` run through the PowerShell tool gets no commit security review: the `if: Bash(git*commit*)` entries sit under `matcher: "Bash"` only (`hooks/hooks.json:125`); add PowerShell — whole-plugin review M/L, recovered from the todo line (2026-11-20)".

Proof: `hooks.json` routes commit and push calls to the review only for the Bash tool, and `security_reminder_hook.py` dispatches the commit review only when `tool_name == "Bash"`. So on Windows, where Claude Code runs commands through its PowerShell tool, a commit is never reviewed. Root cause: both places name the Bash tool alone.

## Decisions

- Add a `PowerShell` PostToolUse entry with the same three `if` patterns (`git*commit*`, `git*push*`, `gt *`), and dispatch on `tool_name in ("Bash", "PowerShell")`. The commit and push regexes read the command text, which is the same `git` invocation in either shell. Ruled out: one entry with `matcher: "Bash|PowerShell"`, since an `if` names a single tool.

## Acceptance criteria

- **AC-001** A `git commit` run through the PowerShell tool reaches the commit review: a second spawn for the same call is de-duplicated, as it is for Bash.
- **AC-002** `hooks.json` routes PowerShell `git*commit*`, `git*push*` and `gt *` calls to the hook, and keeps the Bash ones.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_security_reminder.py › SecurityReminderTest.test_a_commit_through_powershell_reaches_the_commit_review | `python3.10 -m unittest discover -s tests -t tests -p test_security_reminder.py -k test_a_commit_through_powershell_reaches_the_commit_review` |
| AC-002 | tests/test_security_reminder.py › SecurityReminderTest.test_hooks_json_routes_powershell_commits_and_pushes_to_the_review | `python3.10 -m unittest discover -s tests -t tests -p test_security_reminder.py -k test_hooks_json_routes_powershell_commits_and_pushes_to_the_review` |

## Must never break

- Bash commits and pushes are reviewed as before.
- Other PowerShell commands spawn nothing new: the `if` patterns keep them out.

## Out of scope

- Whether the PowerShell tool's `tool_response` carries git's output in the same field as Bash's. The commit review's success check reads it, and an unrecognised shape skips the review the way an unrecognised Bash one does. It needs a Windows run (smoke I).

## Review

No review ran: no trigger fired (low risk, no Public Surface, no sensitive path).
