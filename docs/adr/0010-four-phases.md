# ADR 0010: Four phases instead of eleven stages

- **Status:** Accepted, 2026-10-26; amended by [ADR 0011](0011-track-cost.md) and by [ADR 0014](0014-lighter-s-and-a-companion-plugin.md) (S writes no Define files, and Ship doesn't ask on S and `Flow: lite`). Amends [ADR 0008](0008-lite-flow-for-low-risk-m.md) and [ADR 0009](0009-cheaper-pipeline-and-control-contract.md): Lite's shape becomes every track's default, and verify, review and security run as one round.
- **Deciders:** Tâm Mai.

## Context

In evals 8–10 (planner task) the plugin matched plain Claude on quality, with no blocking or major blind defects against 1–2 major for plain. It cost 5–6x more: 107–160 min of agent time against 20–26, 7.7–8.0M weighted tokens against 1.3M, and 4–5 human touches against 1. The cost came from the stage transitions:

- each of 11 stages was a gate, loaded its own instructions and waited for the one before;
- verify, review and security were 60% of wall-clock, run in sequence, and every fix restarted the chain;
- plan added a gate with no measured gain on M;
- deploy and operate ran on no track by default but sat in every state file;
- learn ran only on L.

Two of the touches were avoidable: a trust-anchor confirmation right after the user approved a Lite → full switch, and the build-method question.

## Decision

- **Four phases, each at one stage number:** Define (1), Build (4), Prove (5), Ship (8). Learn is a small step inside Ship. A new feature never enters 2, 3, 7 or 9–11; a backlog slice rests at 6 once committed, as before, because autopilot and the trust anchor read 8 as feature close having reached Ship.
- **Stage numbers kept (option a).** The hooks read only the number, so none of them changes, except that the trust anchor no longer blocks a stricter change (Track up, Risk low → high, Flow lite → full); it shows it instead. Features started under the old stages resume in the phase their number maps to. No upgrade migration is needed.
- **Define:** one approval covers intent, spec, plan (or backlog), design and `Build:`. Every track writes `intent.md` (why), `spec.md` (what) and `plan.md` (how: tasks, Public Surface), so that nothing the build needs lives only in the conversation (amended the same day: the plan first moved into the spec, then came back as its own file on every track, for role agents that hand work over through files; amended by ADR 0014: S writes none of the three and records `Intent:` and `Repro:` in its state file).
- **Prove:** verifier, reviewers and security checks run in one parallel round. A failed re-verification gets a fresh verifier round; only the round cap stops.
- **Ship:** Learn adds Prove's fixed defects to `recurring-defects.md`, which Define and every reviewer read.
- **Deploy** becomes `/sdlc:deploy`. **Operate** is removed and kept as a reference.
- The contract snapshot gains `phase`; the renamed stage names bump `contract_version` to 2.
- The full gate mapping is in the feature spec: [four-phases spec](../sdlc/intents/2026-10-26-four-phases/spec.md).

### Alternatives considered

| Option | Why not |
|---|---|
| New phase identifiers in `Current:` (option b) | rewrites five hooks, the CI template and the dispatch log format and needs a state migration, all to gain nicer numbers |
| Drop S's code reviewer ("S: verifier only") | weakens a check S has today; it runs in the same round, so it costs tokens but no wall-clock |
| Plan as its own phase with its own gate | a gate with no measured quality gain; the plan is now written in Define and approved with the spec, at no extra stop |

## Consequences

- **Expected:** less agent time (no sequential Prove, fewer transitions, no plan gate), fewer weighted tokens (four phase files, no Deploy or Operate text), and fewer touches (no build-method question or second trust-anchor stop, no ask after a fixable failed round). Hidden tests and blind defects are held level by keeping every check, plus Learn on every feature.
- **Costs:**
  - Two approvals become one on L and on designed M, so a design is approved together with its spec.
  - The skill-text changes are instructed, not tested; the evals are the check.
  - The freshness hook's Lite Stage 6 case stays for in-flight features only.
