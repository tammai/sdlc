# A turn that keeps failing the same way in Build gets one nudge to debug

## Why

**Request (verbatim):** "stuck-turn nudge in Build (repeated same failure N=3 in one turn → one additionalContext note pointing at systematic-debugging, once per turn, silent under review cap and outside an active feature, no model call)", the second of the two changes taken from microsoft/TokenEconomizer's failure-loop guard (2026-11-19).

sdlc caps loops between phases (review rounds, the prove budget), but nothing notices a Build turn that re-runs the same failing command again and again. TokenEconomizer redirects such a turn once, never stops it, and uses a model judge; this keeps the redirect and drops the judge: the same failure three times in one turn is the signal.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| "The same failure" is a failed Bash or PowerShell call with the same command text and the same `error` text once digits and whitespace are evened out | the command alone; a model judge | the same command failing differently after an edit is progress; timings and counts in the output shouldn't split one failure in two; the request rules out a model call |
| A turn runs from one `UserPromptSubmit` to the next: the hook also listens there and starts the count over | reading the transcript for the last prompt | a transcript can be large and its format is internal; the prompt event is one small process |
| Counts live in `.sdlc/.work/stuck-turn.json`, keyed by session | the plugin's data folder | `.sdlc/.work/` is where the other per-repo hook state lives, already git-ignored |
| Claude Code only | Codex, Cursor, Antigravity through `hosts/hook.py` | Codex and Antigravity send no exit code, so a failure isn't seen; Cursor's prompt event may not fire (knowledge/gotchas/host-hook-answers.md) |
| Calls a subagent makes (`agent_type` set) are not counted | counting them | the nudge is for the main session's Build turn; a subagent's failures are its own |

## Acceptance criteria

- **AC-001** Given an active feature in Build, when the same failure arrives for the third time in one turn, then the hook answers with context naming `sdlc:systematic-debugging`; the first two answer nothing, and further repeats in that turn answer nothing (one nudge per turn); after the next prompt the count starts over and a third repeat nudges again.
- **AC-002** Given an active feature in Build, when the failures differ (another command, or another error beyond its digits), then they are counted apart and none nudges before its own third time.
- **AC-003** Given three same failures, then nothing is answered when no feature is active, when the active feature is not in Build, when the review round cap is holding the feature, or when the calls come from a subagent.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_stuck_turn.py › StuckTurnTest.test_third_same_failure_nudges_once_per_turn | `py -3.10 -m unittest discover -s tests -t tests -p test_stuck_turn.py -k test_third_same_failure_nudges_once_per_turn` |
| AC-002 | tests/test_stuck_turn.py › StuckTurnTest.test_different_failures_are_counted_apart | `py -3.10 -m unittest discover -s tests -t tests -p test_stuck_turn.py -k test_different_failures_are_counted_apart` |
| AC-003 | tests/test_stuck_turn.py › StuckTurnTest.test_silent_outside_build_under_cap_and_in_subagents | `py -3.10 -m unittest discover -s tests -t tests -p test_stuck_turn.py -k test_silent_outside_build_under_cap_and_in_subagents` |

## Must never break

- The hook never blocks or denies anything, and on any error it prints nothing and exits 0.
- The freshness and read-only-watch hooks on `PostToolUseFailure` work as before.

## Out of scope

- Other agents (Codex, Cursor, Antigravity) and failures of tools other than Bash and PowerShell.
- TokenEconomizer's learned turn-length envelope and its model judge.

## Review

No review ran: low risk, no trigger fired (Public Surface none, 2 source files, under 300 lines); every AC red then green (verify.py). Full suite by hand: 675 tests OK, Python 3.10 (the repo isn't set up for sdlc). Lessons filed: .claude/rules/tests.md, a test helper named fail swallows assertions (the red step caught it).
