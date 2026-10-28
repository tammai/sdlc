# ADR 0015: Prove only where it pays

- **Status:** Accepted, 2026-10-27. Amends [ADR 0013](0013-build-proves-prove-judges.md): Prove no longer runs on S or on M with `Flow: lite`, a backlog gets one Prove at Feature close instead of one per slice, and Prove's high findings are fixed back in Build. Amends [ADR 0014](0014-lighter-s-and-a-companion-plugin.md): S has no Prove step at all (it already dispatched nothing), and a security review runs only on a security-touched change, in Prove and at commit.
- **Superseded in part** by [ADR 0020](0020-sdlc-2-slim-process-core.md): Prove and skipping it are gone. Still current: the security review only for security-touched work, and high findings fixed back in Build, test first.
- **Deciders:** Tâm Mai.

## Context

The stage-1 S-task eval (ADR 0014) found quality equal to a plain Claude run: hidden tests 100% in both arms, rubric 4.80 in both, no blocking or major defects. The plugin cost 11.7x the tokens and 7.9x the agent time. ADR 0014 cut S's documents and Ship's question; what remained on every track was Prove and review:

- on S, Prove was a stage that dispatched nothing and only confirmed the `verify.py` run Build had just made;
- on M lite, Prove was one ac-checker reading tests that Build had already recorded red and then green, plus an in-session dependency audit;
- every Prove ran a "light" security pass (the dependency audit) and every review-ready commit got a model security review, whatever the change touched;
- a backlog ran a Prove round per slice, then another over the whole branch at Feature close.

That eval measured S. For M lite, the user directed the same cut, unmeasured on M: ADR 0013 recorded that the one measured quality gain came from the spec and the tests-first build, which Build's red-first tests and `verify.py` keep. Reviews and security passes stay where the change is risky or large.

## Decision

1. **No Prove on S and M lite.** Build's passing `verify.py` goes straight to Ship: `state.py verified` with the tree from `verify.py status`, then `state.py advance <f> 8 --gate pass`. The trust anchor accepts that passing run as the evidence on S, M with `Flow: lite`, and `Prove: skip`, and still reports M full or L reaching Ship without Stage 5.
2. **Prove is skippable on M full and L, before Build.** Define's approval shows `Prove: run`; the user can answer skip, recorded with `state.py set <f> Prove skip`. The default is `run`, and an autopilot or headless run, with nobody to ask, keeps `run`. `Prove` is a trust-anchor field: run → skip after the anchor was taken is a notice the user accepts; skip → run only adds checks and passes.
3. **Security review only when the change is security-touched:** `Risk: high`, or the diff since `Base:` touches `areas.sensitive` or `areas.migrations` (the plugin's defaults plus whatever `.sdlc/config.json` adds; paths compared case-folded), or `.sdlc/config.json` has an uncommitted edit. Then Prove runs full security (security-brief `feature-reviewer` and `code-reviewer`, plus the dependency audit in the session), and the commit-time model review runs. For any other active feature's commit, `hooks/sdlc_review_gate.py` returns `skip`: the commits are recorded as reviewed and no model is called. A commit touching the hooks, agent instructions or config, `.sdlc/config.json` or CI is never skipped; the state file is not on that list, since every Ship and slice commit carries it. A security-touched change on `Prove: skip` still goes to Stage 5 for its full security review alone, before Ship. The always-on pattern hooks (edit warnings, the turn-end review, secret blocking) still run. The old light security, a dependency audit on every Prove, is gone.
4. **One Prove per split feature.** A feature split into slices gets no Prove per slice: each slice is built, passes `verify.py` and is committed. Prove runs once, at Feature close, on every backlog whatever its flow, unless `Prove: skip`; then the last slice goes to Ship.
5. **Findings go back to Build.** Prove's high findings move the feature back to Build (`state.py advance <f> 4`), where they are fixed together, each with a failing test first, and `verify.py` passes again. Then one re-verification in Prove: `verify.py status` (reused) and a fresh ac-checker on the ACs that failed. No second reviewer round.
6. **No per-task review on L.** `Build: tasks` runs one implementer per task and no reviewer: Prove at the end is the only review (decided by the user after the planner-team L round, where each task waited on an Opus review, a fix round and a re-review).

## Alternatives considered

- **Keep M lite's ac-checker.** Rejected by the user: Build has already recorded each test red and green. Its value on M was never measured; this is the user's direction, not an eval result.
- **Keep light security (a dependency audit) on every Prove.** Rejected: a change that touches no sensitive or migration area is left to the pattern hooks; the audit now runs with full security only.
- **Ask about skipping Prove at Build's end, once the result is known.** Rejected: the choice would be made after seeing the code, by the agent that wrote it. Asking at Define's approval keeps it the user's decision, made before the work.
- **Per-slice Prove, without the reviewer.** Rejected: Feature close already reads every AC and reviews the whole branch; per-slice rounds re-read the same tests.

## Consequences

- S and M lite end in Build's `verify.py` and a commit. They never enter Stage 5, so the freshness hook's block and the prove-budget limit don't apply to them; Ship's verified-tree check catches code changed after that run and sends it back to Build to rerun `verify.py`.
- M lite gives up the ac-checker's reading of tests: a test that runs and passes but asserts the wrong thing is caught only by red-first (it must fail before its code) on M lite and S. On M full and L, the ac-checker and review still catch it, unless the user chose `Prove: skip`.
- The security of a change that isn't security-touched rests on the always-on pattern hooks and the turn-end review; no model reviews the commit.
- Whether a change is security-touched comes from `Risk:` in the state file and `areas.sensitive` and `areas.migrations` in `.sdlc/config.json`. Both must be right: a sensitive path the config doesn't list, or `Risk: low` on risky work, skips the security review. The plugin's default areas always apply and the config can only add to them, so a project can't narrow them, but a project-specific sensitive path must be added.
- `Prove: skip` doesn't drop security: a security-touched change on skip still gets Prove's full security review, alone, and the commit-time review.
- Every backlog runs one Prove, at Feature close, though it runs `Flow: lite`: a feature too big for one session gets one whole-branch check whatever its track.
- Target, not yet evaluated: S and M lite within ADR 0011's 2x agent time and 2.5x tokens of a plain run, with hidden tests held level.
