# ADR 0008: Low-risk M features run the Lite flow by default

- **Status:** Accepted, 2026-10-25.
- **Deciders:** Tâm Mai.

## Context

The owner's goal for the plugin: state an intent, the agent does the rest, and the result is code a senior engineer would ship, with as few prompts and approvals as possible. Evals in a separate harness (2026-10-25, Sonnet sessions, setup excluded) compared plain Claude Code, the full M flow and a Lite prototype:

| Task | Plain | Full M | Lite |
|---|---|---|---|
| Greenfield planner CLI (Lite: 3 runs) | ~255k weighted input, 1 touch | ~2.09M (8.2x), 5 touches | 643–703k (2.5–2.8x), 2 touches |
| Brownfield: priorities on an existing planner | ~99k, 1 touch | ~774k (7.8x), 5 touches | ~380k (3.8x), 2 touches |

Every arm passed every hidden acceptance and regression test. The full flow's extra cost went to separate spec, checklist and plan documents, loading several bundled skills that stay in context, an execution-method question, per-task commits and reviews, two extra verify analysts and a top-tier review. None of it changed the hidden-test result on these tasks. The first Lite run surfaced one gap: after a post-verify review fix, the trust anchor flagged the edit, because the freshness hook stopped tracking after Stage 5.

## Decision

- **M with `Risk: low` defaults to the Lite flow** (`Flow: lite` in `state.md`). The user can ask for the full flow; high risk always gets it.
- **One document, one approval.** `spec.md` holds the requirements, an `Inferred` list (dropped unless kept), about 10 acceptance criteria, Non-Goals and 3–6 tasks. Stages 1 and 3 share its gate. No requirements checklist, no plan.md, no execution question.
- **Native build, test first,** with no bundled planning or execution skill loaded: the orchestrator section carries everything.
- **One fresh standard-tier verifier** (a second round after a FAIL; a second FAIL stops). Independence of verification is kept; the extra analysts are dropped.
- **One standard-tier review with named edges** (durable writes, error paths, loaded data), since it is the only second pair of eyes. Fixes are re-verified with an in-session full run, not a new verifier round. The freshness hook tracks Stages 5–6 on `Flow: lite` so that rerun is enforced, and the trust anchor accepts it.
- **One commit** for the feature, so one commit-time security review.
- **Size up** to the full M flow on a design decision the request doesn't settle, or on high risk.

### Alternatives considered

| Option | Why not |
|---|---|
| Keep the full M flow and trim pieces | each piece looked cheap alone; the cost was their sum plus loaded skill text |
| Drop the independent verifier too | the one check that doesn't trust the implementing session; it's kept |
| Plain Claude Code for M | no spec gate, no independent verification, no review: nothing a reviewer can audit |

## Consequences

- **Good:** low-risk M work costs a third to a half of the tokens and needs 2 touches instead of 5, with the same tested quality on the eval tasks.
- **Costs:** no top-tier review on low-risk M work; review fixes are verified by the implementing session, with the freshness hook as the check. `Flow:` is not anchored by the trust anchor, so switching a feature from full to lite mid-way is not flagged (spec 02, Known gaps). The evals are a handful of runs on two small tasks.
