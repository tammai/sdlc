# ADR 0009: A cheaper pipeline, a control contract, and fewer commit reviews

- **Status:** Accepted, 2026-10-26. Amends [ADR 0008](0008-lite-flow-for-low-risk-m.md): the Lite flow's verify and review now run as one parallel round, with the qa-tester in a single-session feature.
- **Deciders:** Tâm Mai.

## Context

Evals of the full M flow (round 2, planner task) showed where cost and time went: the main session was 71% of weighted tokens, its context growing with every loaded skill (58k at the first call, 169k at the end); 60% of wall-clock came after the build, all sequential (verifier, fixes, simplifier, a 190 s top-tier review, fixes, re-verify); about 15 turns were hand edits to `state.md`; each of 7 commits got its own top-tier security review. Setup added a `globals` devDependency and a `bin` field the blind review penalised. A control app and a headless runner are planned, and need to follow a feature without reading the pipeline's internals.

## Decision

- **Load only the current stage.** The orchestrator skill is a ~1,000-word core plus one reference file per stage (and the Lite flow, the slice loop, UI work and the reviewer brief), each read when first needed. Most of the main context comes from bundled skills, so this is a modest saving on its own.
- **Build in a subagent, as an option.** `Build: subagent` hands the build to one implementer that returns a summary; `native` stays the default until the evals compare them.
- **One parallel round.** On the review-ready commit the verifier, the code reviewer and (on M) the qa-tester, plus the silent-failure-hunter on the full flow, run together; all findings are fixed together, then one re-verification. No simplifier pass: simplifications are findings. The qa-tester replaces `pr-test-analyzer` on M (the evals' hidden-test misses are behaviour a black-box run catches; the analyzer's findings were test gaps only).
- **Production edges up front.** Specs list the failure modes that apply as acceptance criteria; every reviewer checks them and a recurring-defects list that projects extend at Stage 11.
- **State through one script.** `state.py` makes each state change in one call and writes a git-ignored control contract beside the state file (`<feature>.json`, `<feature>.events.jsonl`, a reserved `commands/` inbox the engine never executes). `state.md` stays the committed record.
- **One commit security review per review-ready diff (Claude Code).** The vendored commit review asks `hooks/sdlc_review_gate.py`: while one feature is active on a feature branch, a commit before Stage 5 is deferred (not reviewed, not recorded), and the next commit from Stage 5 on is reviewed with every unreviewed commit since `Base:` as one net diff. Because the state file is writable by the agent being reviewed, deferral is bounded: never for a commit touching hooks, agent instructions or sdlc config; not after 10 unreviewed commits, counted from the branch point (which `Base:` can't move); never on the default branch itself. A widened review that drops files records only the commits that triggered it. The push review is unchanged.
- **Setup leaves the product alone.** No manifest fields or dev tooling the project doesn't have, unless the user agrees.

### Alternatives considered

| Option | Why not |
|---|---|
| Keep sequential verify → simplify → review | the evals' largest wall-clock cost, for no change in hidden-test results |
| Commit the contract files | parallel slices in worktrees would conflict on an append-only file; `state.json` is derived anyway (the user's veto) |
| Turn the commit review off under the workflow | removes a control instead of right-sizing it; the push review alone misses unpushed work |
| A hook-owned anchor outside the repo for the deferral cap | the hook's own records live in `.git`, which the agent can write too; failing closed on the default branch and capping from the branch point is the practical bound |

## Consequences

- **Good:** fewer main-session tokens (less skill text, the build optionally out of context), less wall-clock after the build, no bookkeeping turns, one security review per diff on feature branches, specs that name production edges, and a contract a runner can read.
- **Costs:**
  - The deferral changes vendored security behaviour; its limits come from the repo, which the agent can write (spec 05, Known gaps).
  - On the default branch, or a repo without a remote that works on `main`, the security review is still per commit, so FR-05's saving needs a feature branch.
  - A widened review still goes through the 30-file prioritiser.
  - `state.json` lags a hand edit of `state.md` until the next `state.py` call.
  - Every skill-text change (the split, the round, setup) is instructed, not tested; the evals are the check.
