# A Monitor command meets the read-only guard

## Why

From `.sdlc/todo.md`: "The Monitor tool runs a shell command but never reaches `role_guard.read_only_problem` (pretooluse.py's matcher lists only Bash, PowerShell and the edit tools), so in a workbench a Monitor call can write a read-only repo or the watch's files; add Monitor to the matcher and judge its command as sh — code review C12 of 2026-11-22-m-watch-guard-reads, predates it; `hooks/hooks.json`".

Proof: in a workbench with a read-only `specs/`, `pretooluse.py` allows a Monitor call whose command is `echo hi > specs/a.md` (the AC-001 test fails), and `hooks.json` never runs `pretooluse.py` for Monitor (the AC-002 test fails). Root cause: two places name only Bash and PowerShell as shell tools: the PreToolUse matcher, and `role_guard.written()`, which parses a command only for those two tools.

## Decisions

- Add `Monitor` to the matcher of the PreToolUse entry that runs `pretooluse.py`, and have `role_guard.written()` parse a Monitor `command` in the `sh` dialect (Monitor runs it in the session's shell, as Bash does). One check in `written()` covers every guard built on it: the read-only repo, the unbranched repo and the recorded acceptance tests.
- Hookify rules keep `event: all` for Monitor. Ruled out: treating it as `bash`, since the rule engine reads the `command` field for the Bash tool only, so that would change which user rules apply with no gain here.

## Acceptance criteria

- **AC-001** A Monitor call whose command writes into a read-only repo, or names the watch's files, is denied by `pretooluse.py`; one that reads the repo, or loops on a file elsewhere, is allowed.
- **AC-002** The `hooks.json` PreToolUse entry that runs `pretooluse.py` matches Monitor, and still matches Bash, PowerShell and the edit tools.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_workbench.py › WorkbenchGuards.test_a_monitor_command_meets_the_read_only_guard | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_a_monitor_command_meets_the_read_only_guard` |
| AC-002 | tests/test_workbench.py › WorkbenchGuards.test_hooks_json_sends_monitor_to_the_read_only_guard | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_hooks_json_sends_monitor_to_the_read_only_guard` |

## Must never break

- Bash, PowerShell and edit-tool calls are judged as before.
- A Monitor call outside a workbench, or one that writes nowhere guarded, is allowed with no output change.

## Out of scope

- The other hooks that list shell tools by name (`review_rounds.py` GUARDED, `verify_freshness.py`, `read_only_watch.py` WRITERS): the watch still catches a Monitor write after the fact; whether the review-cap hold and freshness should cover Monitor is a separate question, filed as a todo.

## Review

No review ran: no trigger fired (low risk, no Public Surface, no sensitive path).
