# Spec 09: Autonomous loop

Let Claude iterate on one well-specified task with a machine-checkable finish, without the user prompting each round.

**Entry points:** `/sdlc:ralph-loop`, `/sdlc:cancel-ralph`, `/sdlc:ralph-help`; optional in Stage 4 · **Source:** `scripts/setup-ralph-loop.sh`, `hooks/stop-hook.sh`, `commands/ralph-*.md` (vendored from Anthropic's ralph-loop plugin, patched)

## User scenarios

1. **Loop to done.** Given `/sdlc:ralph-loop "make the parser tests pass" --completion-promise "DONE" --max-iterations 15`, when Claude ends a turn without `<promise>DONE</promise>`, then the same prompt is fed back and the iteration count goes up; when the promise appears, the loop ends.
2. **Cap.** Given `--max-iterations 5`, when the fifth iteration ends, then the loop stops.

## Requirements

| ID | Requirement | Guarantee |
|---|---|---|
| LOOP-FR-001 | No active loop (no `.claude/ralph-loop.local.md`) → the stop hook does nothing. | `[enforced]` test_ralph_stop › test_no_loop_is_noop |
| LOOP-FR-002 | An active loop blocks the stop, feeds the original prompt back and increments the iteration. | `[enforced]` › test_active_loop_blocks_and_feeds_prompt_back |
| LOOP-FR-003 | A loop started in another session never blocks this one. | `[enforced]` › test_other_session_is_not_blocked |
| LOOP-FR-004 | The exact completion promise in the last assistant message ends the loop; a different promise doesn't. | `[enforced]` › test_completion_promise_ends_loop, test_wrong_promise_continues |
| LOOP-FR-005 | Reaching `max_iterations` ends the loop. | `[enforced]` › test_max_iterations_ends_loop |
| LOOP-FR-006 | A corrupt or incomplete state file stops the loop and removes the file instead of crashing. | `[enforced]` › test_corrupt_state_stops_loop; test_ralph_stop › test_setup_rejects_a_multiline_promise |
| LOOP-FR-007 | Use only for a single, well-specified task with a machine-checkable finish; always set `--max-iterations`; `/sdlc:cancel-ralph` stops a running loop. | `[instructed]` orchestrator §4, runbook R6 |

## Non-goals

- Replacing the staged flow; running several loops in one session.
