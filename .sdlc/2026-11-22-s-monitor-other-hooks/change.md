# The review-cap hold and the read-only watch cover Monitor commands

## Why

From `.sdlc/todo.md`: "Other hooks still name only Bash and PowerShell as shell tools, so a Monitor command skips them: the review-cap hold (`hooks/review_rounds.py` GUARDED), the freshness check (`hooks/verify_freshness.py` SHELL_TOOLS) and the read-only watch's per-call check (`hooks/read_only_watch.py` WRITERS; its turn-end check still catches the write); decide which should cover Monitor — left out of 2026-11-22-s-monitor-read-only-guard".

Proof: past the review cap, a Monitor call running `npm test && git commit -am x` isn't denied; a Monitor call that writes a read-only repo isn't reported until the turn ends (the AC tests fail).

## Decisions

- **Review-cap hold: covers Monitor.** It runs a shell command like Bash, so it's held the same way, and the project's own test command alone still runs.
- **Read-only watch, per call: covers Monitor** (PreToolUse, PostToolUse, PostToolUseFailure).
- **Freshness: doesn't.** A Monitor call is a background watch whose exit isn't the command's result, so counting it as a test run could mark stale code fresh; edits still mark it stale through the edit tools, and tests run through Bash.

## Acceptance criteria

- **AC-001** Past the cap, a Monitor command that commits is denied; the hooks.json entry for `review_rounds.py` matches Monitor.
- **AC-002** A Monitor call after which a read-only repo changed is blocked at once; the hooks.json entries for `read_only_watch.py` on PreToolUse, PostToolUse and PostToolUseFailure match Monitor.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_review_rounds.py › ReviewRoundsTest.test_a_monitor_command_is_held_at_the_cap_like_bash | `python3.10 -m unittest discover -s tests -t tests -p test_review_rounds.py -k test_a_monitor_command_is_held_at_the_cap_like_bash` |
| AC-002 | tests/test_workbench.py › ReadOnlyBackstop.test_a_monitor_call_that_writes_a_read_only_repo_is_seen_at_once | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_a_monitor_call_that_writes_a_read_only_repo_is_seen_at_once` |

## Must never break

- The other matchers in hooks.json (`stuck_turn.py` stays Bash|PowerShell); the review-rounds and workbench tests.

## Out of scope

- None.

## Review

Security review fires (Risk: high); deferred by the user to one review over all of the 2026-11-22 todo fixes at the end of the push.
