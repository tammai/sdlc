# ADR 0012: An enforced Prove budget, and M full without QA

- **Status:** Accepted, 2026-10-26; amended by [ADR 0013](0013-build-proves-prove-judges.md) (the red-green run on Base and the fresh re-verifier are gone: Build records each test red, and Prove reuses its verify run). Amends [ADR 0011](0011-track-cost.md): the 2-minute command limit is now enforced by a hook, which 0011 rejected, and M full drops the qa-tester and the fresh re-verifier.
- **Superseded in part** by [ADR 0020](0020-sdlc-2-slim-process-core.md): the red-green run on Base and M full's checkers are gone. Still current: the enforced command cap and the no-polling rule, now applied in Review, and the read-only reviewer.
- **Deciders:** Tâm Mai.

## Context

Eval rounds 12–13 on planner-team (M full, Sonnet at high effort, plugin at ADR 0011) put Prove at about 40–50 minutes, against a 12–15 minute target:

- the budget was instructions only and wasn't followed: r12's qa-tester spent 18.7 minutes on its own commands against a 10-minute budget, and single commands ran 3.7–7.4 minutes against a 2-minute limit;
- agents started runs in the background and polled them (`until grep -q …; do sleep 3; done`), and each poll is a new command, so a per-command limit never applies;
- the verifier's red-green run on Base ran the feature's new 50k-task scale tests against the old quadratic code, which took 7.4 minutes to fail;
- the code reviewer ran a 3.7-minute fuzz script of its own;
- QA was round 1's critical path (24 minutes; the reviewer took 4.8);
- M full always ran a second, fresh verifier after fixes, even when every finding came from the reviewer.

0011 rejected a hook because it "can't tell a project command from a probe". It can: the project's own commands are recorded in `.sdlc/config.json` (ADR 0002), so anything else is not one.

## Decision

- **Command cap, enforced:** while a feature is in Stage 5, a PreToolUse hook (`hooks/prove_budget.py`) applies to every caller (the session, the verifier and the reviewers). A Bash command that isn't one of the project's own (`commands` and `packages[].commands`: install, build, lint, typecheck, test; extra arguments and a leading `cd <dir> &&` allowed) is killed at 120 s. At its own `timeout` Claude Code doesn't kill a command but moves it to the background, where an agent can poll it (checked live on 2.1.310), so lowering the tool `timeout` alone isn't enough. The hook rewrites the command instead: `timeout -k 5 120 <command>` for a single step (each command of one pipeline; a leading `cd`, `export`, `echo` and the like stay as they are), which the user's permission rules still match through the wrapper (checked live: an allow-listed `python` ran unprompted and was killed with exit 124). Anything else (two timed steps, loops, subshells, `$(…)`, `&`) is denied with the reason: split it into separate calls. The tool `timeout` becomes 130 s, past the kill, so the command is never backgrounded. The hook answers with `updatedInput` and no permission decision. Where no `timeout` binary exists (macOS without coreutils), it only lowers the tool `timeout` to 120 s. Exit code 124 is "could not verify within budget" for the verifier and the qa-tester: a gap, never a pass.
- **No polling:** the same hook denies `run_in_background` for those commands, the Monitor tool for them, and the PowerShell tool for them (use Bash, where they are killed at the limit), each with a one-line reason. With nothing non-project in the background, BashOutput and TaskOutput can only reach the project's own runs, so they stay open.
- **Bounded red-green:** the verifier runs the red-green check on Base through the project's test command with a 30 s per-test timeout (`--test-timeout=30000`, or the stack's equivalent). A test that times out on Base counts as failing there. Running it through the project's command keeps it exempt from the cap, since many slow tests at 30 s each can exceed 120 s.
- **Read-only reviewer:** the code-reviewer reads code, diffs and history and may run the project's test command. It writes and runs no scripts of its own. A suspicion that needs a probe is a finding for the verifier or the user.
- **M full:** the verifier, one light code-reviewer, a ui-reviewer on UI diffs, and full security only on auth, payments, secrets, PII and migrations. No qa-tester. Without QA in the round, the verifier may write its 5 probes.
- **M full re-verification:** the full suite in the session, which includes the fixes' new failing-first tests, logged as on Lite. A fresh verifier runs only when the verifier itself failed a requirement or a fix touched files outside the findings.
- **L and Feature close:** unchanged. L had no qa-tester before this ADR either; Feature close keeps its own.

### Alternatives considered

- **Deny over-long commands instead of lowering them.** That costs a round-trip on every one. It would be needed only if `updatedInput` without a decision skipped the permission check, and it doesn't.
- **Only lower the tool `timeout`.** Built first and rejected after a live check: at the limit the command moves to the background, so a long probe just becomes a run to poll.
- **Wrap what can't take the prefix in `bash -c`.** Built and rejected after a security review: permission rules then see `bash`, not the command, so a user's deny rule (`Bash(curl:*)`) no longer matches, and an allow-all mode would run it.
- **Answer `allow` with the rewritten input.** Rejected: `allow` skips the user's permission prompt for every non-project command in Prove.
- **Keep QA on M full, time-boxed by the hook.** Rejected for now: QA's 24 minutes came from many short commands, which a per-command cap doesn't bound. Eval rounds r12 and r13 will show whether QA found anything the verifier and reviewer missed.

## Consequences

- M full gives up black-box probing, and its fixes are no longer checked by a fresh agent, as on M lite already.
- A compound non-project command (a loop, two chained probes) is refused, so agents split it into calls. A command the splitter misreads (for example an escaped quote inside double quotes) is refused too, never rewritten blind.
- A probe chained after a project command (`npm test; node probe.js`) counts as the project's own and escapes the cap. The 10-minute total per agent is still an instruction.
- On other hosts (Codex, Cursor, Antigravity) the cap stays an instruction: `hosts/hook.py` leaves this hook out, since their command payloads haven't been checked for a timeout or background field to change.
- Target, not yet evaluated: on planner-team (M full, at least 3 runs), Prove's median wall-clock is at most 15 minutes, hidden tests are held level with the paired baseline, and no Prove tool call outside the project's own commands runs longer than 120 s.
