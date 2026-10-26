# ADR 0011: Fewer agents per track and a bounded Prove

- **Status:** Accepted, 2026-10-26. Amends [ADR 0010](0010-four-phases.md): a failed re-verification no longer gets a fresh verifier round without limit, and the checkers per track shrink.
- **Deciders:** Tâm Mai.

## Context

On the planner-team eval, rounds 8–10 (M track), the plugin took 4–7x the baseline's wall-clock (83–186 min against 13–26) and about 6x its tokens. Most of it was Prove:

- verifier and QA spent 60–75% of their time on throwaway probe scripts (soak loops of 20–40 repetitions, one command at the 600 s timeout), while the project's suite took under a minute;
- the verifier and QA probed the same things, and three reviewers and QA reported the same bug;
- r8 ran five verifier rounds that all passed, and r9's later rounds chased ever narrower edge cases without converging;
- the advisor ran 10–11 times per run (baseline: 2).

Black-box probes found the baseline as robust as the plugin. The plugin's one measured quality win came from the spec and the tests-first build.

## Decision

- **Models:** Sonnet at high effort is the base. No Haiku: the cheap tier is Sonnet. Opus stays the top tier. The model router denies `haiku`, and its Opus floor for reviewers, the verifier and qa-tester now applies on `Track: L` only.
- **S:** built and verified in one place (the implementer, or the session), repro test first. Prove dispatches nothing; the session runs the full suite once. The trust anchor counts that passing full run as Stage 5 on Track S.
- **M, `Flow: lite`:** Prove is one fresh verifier. No reviewer, QA or UI reviewer. Fixes are re-verified in the session.
- **M, `Flow: full`, either risk:** one Sonnet code-reviewer whose brief covers correctness, silent failures and security replaces the Opus reviewer and the silent-failure-hunter. QA, UI review, full security on sensitive areas (now on Sonnet) and a fresh re-verifier stay.
- **L:** unchanged, apart from the model and Prove rules.
- **Bounded Prove:** verifier and QA run every non-project command with a 2-minute limit, and 10 minutes in total per agent per round. Anything unproven is "could not verify within budget" and goes to the user. With QA in the round, the verifier writes no probes. At most 5 probes, planted states over repetition. A probe that finds a defect becomes a failing test in the project's suite.
- **Convergence:** the same requirement failing in two rounds stops Prove and goes to the user. The 3-round cap stays.
- **Advisor:** at most twice per feature, before Define's approval and before Ship.

### Alternatives considered

- **Keep the Opus floor on M at risk high.** Rejected by the user: the eval showed no quality gain from the extra review, and full security still runs on sensitive areas.
- **A hook that enforces the 2-minute budget.** Not done: the hook can't tell a project command from a probe. The budget is instruction only, and the eval transcripts check it.

## Consequences

- S and M lite give up defects only reviewers catch (in r10: escape-sequence injection, a silent hang). Risk sizing is the mitigation: untrusted input reaching a terminal, shell, file path or database sets risk high, which means the full flow with review and security.
- A budget too tight for a timing criterion is reported, never passed silently.
- Not yet evaluated. The target on planner-team: at most 2x baseline wall-clock and 2.5x its tokens, with hidden tests and blind-review defects held level.
