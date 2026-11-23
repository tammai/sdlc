# Mode tickets: reads that can't block, an accepted mode told at once, the no-notice paths named

## Why

Four tickets left by the security reviews of `2026-11-23-l-configurable-stages` (ADR 0030), from `.sdlc/todo.md`:
- R3-L2: "`_inside` checks a file is regular, then opens it, so a FIFO swapped in between can still win; open with O_NONBLOCK and fstat the descriptor".
- R3-L5: "the session status line is built at SessionStart only, so a mode or skip accepted mid-session shows stale until the next session".
- R4-L4: "Spec 02's Known gaps should name the mode/skip paths that count without a notice".
- R3-L1: "on Codex (no CLAUDE_PROJECT_DIR) a nested repo with its own `.sdlc` may decide the mode if the hook payload's cwd follows the agent's `cd`; probe a live Codex session".

Proof: AC-001's test opens a FIFO when the path checks are bypassed (it hangs); AC-002's test sees no context after the reply that accepts a skip.

R3-L1 was probed live on 2026-11-23 with Codex 0.154 (sdlc refreshed in its cache): an outer full-mode repo and a nested advisory repo, both with the dangerous-rm guardrail. `cd sub && rm -rf node_modules` and the same command with the shell tool's `workdir` set to `sub` were both denied. The payload's cwd stays the session's folder, so the nested repo never decides. Closed with no code change.

## Decisions

- One `sdlc_scopes.open_regular` opens non-blocking and checks the descriptor (`fstat`), used by every read of a repo file through `_inside` and the trust anchor's records. Ruled out: keeping the path check alone, which races.
- The trust anchor's reply that accepts a mode or skips adds a context line naming what the hooks now enforce (`effective`, after the record is written; security review SEC-4), because the session status line is built once per session. Ruled out: rebuilding the status line on every prompt, which costs a git call per prompt.
- Spec 02's Known gaps names both no-notice paths (a deleted record lets HEAD decide; a hand-written accepted entry counts).

## Acceptance criteria

- **AC-001** Reading the mode never waits on a FIFO, even when it was swapped in after the path checks.
- **AC-002** The user's reply that accepts a mode or skip tells the agent the new mode and skips in the reply's context.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_modes.py › ModesTest.test_a_file_swapped_for_a_fifo_after_the_check_is_never_waited_on | `python3.10 -m unittest discover -s tests -t tests -p test_modes.py -k test_a_file_swapped_for_a_fifo_after_the_check_is_never_waited_on` |
| AC-002 | tests/test_modes.py › ModesTest.test_an_accepted_mode_change_reaches_the_agent_at_once | `python3.10 -m unittest discover -s tests -t tests -p test_modes.py -k test_an_accepted_mode_change_reaches_the_agent_at_once` |

## Must never break

- Every committed-file reader still reads a regular file inside the repo as before (`test_sdlc_layout`, `test_doctor`).

## Review

Security review fired (Risk: high), run once over both changes of branch `2026-11-23-todo-mode-tickets` (`2026-11-23-s-mode-tickets`, `2026-11-23-s-rewake-unchanged-finding`), on opus.

- **Round 1 FAIL:**
  - SEC-1, high: the drop ignored the vulnerable code. Fixed: file, category, code and diff must all match.
  - SEC-2: a hash outlived the turn. Fixed: a stored finding carries its turn.
  - SEC-4: the acceptance line named what was shown, not what's enforced. Fixed: it's built from `effective`, after the write.
  - SEC-3: Windows text mode. Fixed: `O_BINARY`.
- **Round 2 PASS:**
  - M-1: a fix reverted in the same turn was dropped. Fixed test first: a reviewed file that isn't flagged clears its stored hash.
  - L-1: fixed; a subagent's findings carry no hash.
  - L-4: the test now asserts the message.
  - M-2 and L-3 (unconfirmed) are tickets in `.sdlc/todo.md`.
- **Reports:** `.sdlc/.work/findings/2026-11-23-todo-mode-tickets/security-r1.md` and `security-r2.md`.
- **Tests:** full suite on Python 3.10. No lesson filed.
