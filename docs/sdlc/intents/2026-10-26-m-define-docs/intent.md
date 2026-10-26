# Intent: Define writes what, why and how to files

## Intent and why

**Request (verbatim)**: "i dont want anything in the agent's head. the docs after define stage should be writen down to file and answer what, why, how. because later we will implement the multi agents as a teams, so each one has a role and communicating via writen files." Follow-up: "all three for S, option a for slices".

Role agents will later hand work to each other only through files. Today, on Lite and S, the "how" lives in the spec's Tasks list or in the building session's head. A builder agent with no conversation couldn't pick it up, and the spec mixes what with how, against `writing-specs`' own rule.

## Questions and answers

- Same three files on S, or one `intent.md` with What and How sections? → all three, tiny.
- Slices: every detailed slice plan written in Define, or `plan.md` with a per-slice outline and `plan-B<n>.md` written at slice start? → the outline, option (a).

## Approaches considered

| Approach | Trade-offs |
|---|---|
| A: `intent.md` (why), `spec.md` (what) and `plan.md` (how) on every track, sized by track | one fixed set for every role; costs one more short file on S and Lite |
| B: what and how as sections of one file on S and Lite | fewer files, but each role has to know which section to read, and the set differs by track |
| C: bring back `plan.md` only on the full flow and L | cheapest, but S and Lite keep the how in the head or mixed into the spec |

## Chosen approach and why

A. It's the user's call: role agents need one file per question on every track. Approval stays a single stop, and S still has none.

## The chosen approach in detail

- **`spec.md`** goes back to what/why only: requirements, criteria, non-goals, failure modes, no files or code structure.
- **`plan.md`** holds the how: tasks (files, the first test, the command, the FR), Public Surface, UI mapping and Review Focus.
  - Lite and S: from `templates/plan-template.md`, written by the orchestrator.
  - Full flow and L: written by `sdlc:writing-plans`, which returns without asking for an execution method.
- **Self-contained:** a fresh agent must be able to build from the three files alone.
- **Build** follows `plan.md` and writes any deviation back into it.
- **Prove's surface check** reads `plan.md` (`plan-B<n>.md` per slice).
- **Backlog:** `plan.md` gives a how-outline per slice; each slice's detailed `plan-B<n>.md` is written as it starts.

## Goals, non-goals, constraints

- Goals: what/why/how all on file after Define, on every track; one approval.
- Non-goals: building the team mode itself; writing every slice's detailed plan in Define; changing prune (it still deletes `plan.md` from finished features; git keeps it).
- Constraints: no new stop; the hooks and `diff_stats.py` stay as they are.

## Calls made, and what's left to the builder

- Calls: the plan template mirrors `writing-plans`' headings, so `diff_stats --plan` reads either; `analyzing-consistency` stays on L and backlogs only.
- Left: nothing.
