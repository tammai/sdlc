# ADR 0017: A thin main session, kept-alive stage agents, one record file

- **Status:** Accepted, 2026-10-27. Amends [ADR 0016](0016-cut-l-cost-where-it-bought-nothing.md):
  - one-piece M builds in a kept-alive agent, not in the main session;
  - the advisor doesn't run once Prove has;
  - M's Prove is one checker.
  
  Built before it was measured, at the user's request.
- **Deciders:** Tâm Mai.

## Context

On the `ef7fabd` L run, the main session's context per turn grew from stage to stage, and every turn re-read all of it:

| Stage | Context per turn |
|---|---|
| Define | 121k |
| Build | 249k |
| Prove | 368k |
| Ship | 440k (one turn at 825k) |

Ship's single advisor call read 414k tokens. Prove's fix pass resumed an implementer that still carried two hours of Build context. Ship wrote three reports, a feature note and a decision note, most of it repeating the commit and the design.

## Decision

1. **Relay** (`skills/orchestrator/references/relay.md`).
   - **When it runs:** on M and L, in an interactive Claude Code session.
   - **The main session** reads the relay and the core, never the phase files. It passes paths, runs `advance`, `round` and `verified`, and shows the user what an agent hands it.
   - **On M,** a kept-alive maker agent does Define and Build.
   - **On L,** a Define agent and then one Build agent per part do the work, the parts one after another. `verify.py`'s records are single files that parallel agents would overwrite.
   - **Stage agents** are resumed with `SendMessage`, not re-spawned. Each ends every turn with one line: `DISPATCH:`, `ASK:`, `QUESTION:`, `STATUS:` or `DONE:`.
   - **Dispatching:** stage agents can't start agents, so they ask the main session to dispatch for them.
   - **Where it doesn't run:** S, autopilot, headless runs, Codex, Cursor and Antigravity keep the in-session flow. Whether a `claude -p` session is woken when a background agent finishes is unverified.
2. **Paths, not contents.** Reviewers write their report under `.sdlc/.work/findings/`; the role guard allows them that folder and nothing else. `ac-checker` and `code-reviewer` gain the Write tool for it.
3. **The maker fixes Prove's findings.** It knows the design, so it breaks fewer of the design's rules. Reviewers stay fresh every round.
4. **M's checker.** M's Prove is one fresh `code-reviewer` that also reads each AC beside its test, reading the diff once.
   - Tier: standard, top on risk high.
   - The trust anchor accepts it as M's Stage 5 evidence. L and Feature close keep a separate `ac-checker`.
5. **`plan.md` opens with `## Handoff to Build`.** It lists:
   - decisions and their reasons;
   - rejected options;
   - facts found in the code;
   - what must not break;
   - the builder's open calls;
   - risks, each with its proof.
   
   Anything the user said that changes what gets built goes under Decisions, or it doesn't count.
6. **No advisor once Prove has run.** The pre-commit call stays on S, M lite and `Prove: skip`.
7. **One record file.** Prove's rounds, tickets, fixes and security findings all go in `review.md`.
   - The `sdlc-invariants` CI check reads `review.md`'s rounds and falls back to `test-report.md` on older features.
   - Prune keeps `review.md` on `Risk: high`.
   - Learn writes only lessons that aren't obvious from the code, the commit or the design. L no longer writes `knowledge/features/<f>.md`.

## Consequences

- **Not run live.** The first relay run's transcript has to show the relay lines working before a campaign relies on it. If an agent ends without one, the main session has nothing to act on.
- **Expected saving:** roughly 25–30M main-session cache reads on l-team. That estimate came from the 8-task `ef7fabd` run, so on `46b85d0` (one-piece M) it may be smaller.
- **Context limit:** a maker kept alive through Define, Build and fixes carries its own context. After `/clear` or in a new session, a fresh one starts from the files, beginning at `## Handoff to Build`.
- **Unmeasured:** whether one standard-tier checker on M at risk low catches what a separate ac-checker plus a reviewer would.
