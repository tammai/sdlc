# ADR 0016: Cut L's cost where it bought nothing

- **Status:** Accepted, 2026-10-27. Amends [ADR 0015](0015-prove-only-where-it-pays.md): Ship no longer asks on any track, and Prove runs one code reviewer and one security reviewer. Amends [ADR 0011](0011-track-cost.md): the advisor runs once per feature.
- **Deciders:** Tâm Mai.

## Context

The L eval on `ef7fabd` (`eval-the-sdlc` results `2026-10-27-sdlc-ef7fabd-2`, one run per arm) built concurrency, 50k-task scale, owners and import into a one-file Node CLI (about 300 changed lines):

| | Plain Claude | Plugin (L, full) |
|---|---|---|
| Hidden acceptance / regression | 11/11, 10/10 | 11/11, 10/10 |
| Blocking / major defects | 0 / 1 | 0 / 0 |
| Blind rubric | 3.60 | 4.20 |
| Human touches | 1 | 5 |
| Wall time | 18 min | 193 min |
| Tokens | 3.1M | 56.2M |

The quality gain came from review: the per-task reviews found 4 Important issues, and Prove fixed 7 more groups. The rest bought nothing measurable:
- Define wrote 10 files of about 750 lines.
- All 8 Build tasks edited the same file, so nothing ran in parallel.
- Old-vs-new comparison runs took about 65 minutes and found 0 mismatches. The plan said "at least 3,000 random databases", which became 38k `node` spawns.
- Concurrency tests were looped 20–30 times per task.
- There were 3 advisor calls, 6 Prove agents with two overlapping security reviews, and 3 extra touches: two Define answers and Ship's question.
- `verify.py status` reported "records disagree" because red runs made inside subagents never reached the hook's copy.

## Decision

1. **verify.py writes the hook's copy of its own run.** After every full or `red` run it records its entry in `.sdlc/.work/verify-freshness.json`, so a run counts whatever command spelling ran it. A later hand edit to either record still shows as "records disagree".
2. **Comparison proofs have a budget:** about 1,000 cases or 2 minutes, whichever comes first, calling both versions in one process where the code allows. They run once, in Build. Prove never reruns Build's own proof scripts unless the files they cover changed.
3. **Size by footprint.** A change confined to 1–2 files with a settled approach is M on `Flow: full` with risk high, even with an L signal. It is built as one piece in 1–3 tasks and never split into slices (the user's rule). L means new modules, several distinct parts, or an approach still unclear after Define. A backlog is only for several distinct parts that won't fit one session. On M full, the code reviewer is top tier when risk is high.
4. **One piece, lighter Define.** One-piece work writes three short files: `intent.md` (about 40 lines), a Lite-shape `spec.md` and a `plan.md` from the template. It has no design, no consistency check and no brainstorming, and its approval message stays under about 1,500 characters. `spec.md` stays because the written handoff is a design rule, and `verify.py` reads AC ids from it.
5. **Define is one exchange.** Questions ride in the approval message with pre-filled recommended answers, recorded as `[recommended]` in `intent.md` and turned into `[clarified]` after the reply. Brainstorming under the orchestrator asks nothing, and the choice of approach is in the approval.
6. **Ship doesn't ask on any track.** It commits on the feature branch and ends with `Branch <name> kept (<commit>); say "merge" or "PR" to go further.` Merging, pushing, a PR and a deploy still wait for the user's word.
7. **One code reviewer and one security reviewer in Prove.** The code reviewer gets a one-pass brief covering correctness, silent failures and test gaps (rated 1–10, 8 or more is high), plus security basics unless a security review runs. It replaces the silent-failure-hunter and pr-test-analyzer on L. Full security, only when the change is security-touched, is one more code reviewer with a security-only brief.
8. **Advisor once per feature,** before Ship's commit; in Define only when stuck on a real decision.
9. **One flakiness loop,** at most about 10 runs over the timing-sensitive tests at the end of Build, never per task.

## Consequences

- The eval session expects l-team at 50–60 min, about $10–12 and 2 touches, with 0 blocking or major defects and a rubric of at least 4.0. The k-docs campaigns measure it.
- **Not yet measured:** whether Prove's single review catches what the removed per-task reviews caught on L: a hostile import owner, an endless wait on an unwritable directory, an AC test missing one case, and an endless acquire loop.
- `hooks/verify_freshness.py` still parses verify.py commands. That is now redundant, and it is kept because it costs nothing.
- The silent-failure-hunter, pr-test-analyzer and feature-reviewer agents remain for `/sdlc:review-pr` and on request.
