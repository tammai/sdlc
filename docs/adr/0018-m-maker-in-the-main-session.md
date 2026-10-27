# ADR 0018: On M the main session is the maker

- **Status:** Accepted, 2026-10-27. Amends [ADR 0017](0017-thin-main-session-and-stage-agents.md): on M, Define and Build run in the main session, not in a kept-alive maker agent. L is unchanged.
- **Deciders:** Tâm Mai, on the eval session's proposal.

## Context

ADR 0017 moved M's Define and Build into a kept-alive `general-purpose` agent on sonnet, so the main session stayed thin. A subagent gets a shorter system prompt and only its brief. It loses the harness prompt and the user's CLAUDE.md rules as the conversation reinforces them, Define's reasoning first-hand, and direct questions to the user (every one was an `ASK:` or `QUESTION:` hop).

The context cost that 0017 avoided sits mostly elsewhere. On the `ef7fabd` run the main session was about 120k after Define and 250k in Build, much of it from coordinating 8 subagents, which one-piece M no longer does. The expensive growth (370–440k per turn) came in Prove and Ship. With the checker as a fresh subagent and Ship short, that growth is still avoided.

## Decision

1. **M, interactive Claude Code:** the main session does Define and Build itself (`define.md`, `build.md`) and fixes the checker's highs itself, each with a failing test first.
2. **Prove is unchanged.** The main session reads `prove.md` (evidence, security, the `review.md` round shape, the stop rules) with `relay.md`'s Prove section for the brief, dispatch and moves: one fresh checker on opus every round, never resumed. Its brief is the fixed text plus paths and the changed-file list, nothing else. Only the checker writes the `VERDICT:` line.
3. **The maker is now also the verdict reader,** so the moves come mechanically from the `grep` of the VERDICT lines, before any report is opened, and the trust anchor still gives a notice when a feature leaves Stage 5 while the latest round has a FAIL. The maker may not downgrade or waive a high; a disagreement goes to the user.
4. **`## Handoff to Build` stays:** it is the written record, and the checker reads `plan.md`.
5. **L, S, backlogs, autopilot, headless runs and the other agents:** unchanged.

## Consequences

- M's Define and Build run on the session's model, not on sonnet.
- The main session's context on M grows through Define and Build (about 120–250k on the `ef7fabd` numbers), then stays flat through Prove and Ship.
- The proof that a FAIL still sends the round back is the trust anchor's existing test (`test_a_checker_fail_verdict_blocks_ship_whatever_the_maker_says`): no hook knows who the maker is, so nothing new is enforced.
- Unmeasured until the next l-team and M runs.
