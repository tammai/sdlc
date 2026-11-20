# ADR 0029: The review round cap is a repo setting the agent can only lower

- **Status:** Accepted, 2026-11-20. Amends [0023](0023-two-review-rounds.md) (its "the round-cap hook is unchanged" point). Records: `.sdlc/2026-11-20-m-review-rounds-config/change.md`; spec [03](../specs/03-scope-and-review.md) SCO-FR-030.
- **Deciders:** Tâm Mai.

## Context

The review-rounds hook stopped every feature after round 2 (`CAP = 2`). Some teams want one or two more automatic fix-and-check rounds before they're asked. The cap is a safety stop, though, and `.sdlc/config.json` is a file the agent can edit. A setting the agent could raise would let it buy its own rounds (the recurring defect "repo config relaxes a safety stop").

## Decision

1. **`review_rounds` in `.sdlc/config.json`**, a whole number from 2 to 5. Anything else, including a config that isn't a JSON object, counts as 2. Setup asks it (step `review-rounds`), and `/sdlc:setup review-rounds` changes it at any time. `scaffold.py review-rounds <n>` records it and refuses other values, using the hook's own check.
2. **Each feature's cap is a ceiling that only the user raises.** It starts at config's value at the feature's Base, follows config down whenever config is lower, and goes up only when the user types `/sdlc:setup review-rounds <n>`: the hook reads the number from that prompt, sets the ceiling for each active feature and writes it into config (atomically). Review rounds 2 to 4 found three routes around softer rules (min of now and Base, then max with the typed value); a ceiling closes the class rather than one route. So an edit the agent makes mid-feature can only lower the cap, and a raise needs no write the hook might deny while it holds the work (a first design, which watched config writes in the turn the command opened, lost raises, deadlocked while held and accepted the agent's earlier edit). A value the team committed before the feature started applies with no prompt, which a new clone, a worktree and a headless host all need.
3. **A grant allows rounds up to the one after the round it answered** (`allowed` in the store), whatever the cap does later: it never stacks on a raised cap, and a lowered config doesn't take it back. The command's own prompt sets the cap and isn't also a grant.

Ruled out: applying any raise on the user's next reply (the agent edits config, the user answers "stop", and the raise applies anyway); a local, uncommitted setting (the user chose a shared one); a range starting at 1, which would stop on round 1's findings, which the flow fixes without asking.

## Consequences

- With no key set, nothing changes. The default path makes no git call, and none runs before a feature's round 2.
- The hook's per-feature store (`review-rounds.json`) now also holds the ceiling, and grants as the last round they allow (a store from before converts on read). It is as forgeable by a shell write as the grants were (spec 03, Known gaps).
- Where the host never sends the user's prompt to hooks (headless Cursor), a raise only reaches features started after it is committed.
