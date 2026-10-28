# ADR 0013: Build proves, Prove judges

- **Status:** Accepted, 2026-10-27. Amends [ADR 0011](0011-track-cost.md) and [ADR 0012](0012-enforced-prove-budget.md): the verifier round in Prove, its red-green check on Base and the fresh re-verifier are replaced by Build's recorded evidence, reused in Prove, and a small agent that reads each acceptance test against its criterion. Amended by [ADR 0014](0014-lighter-s-and-a-companion-plugin.md): the hook copies `verify.json`'s entry for a run it recognises (the command itself, after `cd … &&`, followed only by output filters or `; echo`), so other hosts get a copy too; S's AC-001 is the state file's `Repro:` line. Amended by [ADR 0015](0015-prove-only-where-it-pays.md): S and M lite have no Prove (Build's passing `verify.py` goes to Ship), a backlog gets one Prove at Feature close instead of one per slice, and Prove's findings are fixed back in Build before the one re-verification.
- **Superseded in part** by [ADR 0020](0020-sdlc-2-slim-process-core.md): Prove, the ac-checker and its re-verification are gone. Still current: `verify.py`, red before code, drift recorded and never a stop, and the hook's own copy of each run.
- **Deciders:** Tâm Mai.

## Context

Eval rounds 8–13 on planner-team put the plugin at several times the plain run's wall-clock and tokens, mostly in Prove. ADRs 0011 and 0012 bounded Prove, but the waste sits between Build and Prove: Prove re-executes what Build just did.

- the verifier rebuilt, relinted and reran the full suite that Build had just run;
- its red-green check made a second checkout at Base, reinstalled there and ran the new tests against the old code;
- each reviewer rebuilt its own picture of the change;
- the one measured quality gain came from the spec and the tests-first build, not from Prove's probing.

Anthropic's [AI-native SDLC playbook](https://claude.com/resources/articles/the-ai-native-sdlc-playbook) answers this the same way: the agent verifies its own work through one command, deterministic checks run first, a model is called only to judge, and every stage leaves a file the next one reads.

## Decision

- **One command, `scripts/verify.py`.** It runs the project's verify plan (lint, typecheck, build, the full suite, per package), then checks every `AC-nnn` in `spec.md` against `plan.md`'s new `## Acceptance tests` table: a row for each, the test file exists, a red run is recorded, and the row's command passes now. A `manual` row needs its reason in the Run cell and is reported as "checked by reading, not by a test". Its record is `.sdlc/.work/verify.json`.
- **Red before code.** `verify.py red AC-nnn` runs the AC's test before its code is written and records it failing. A test that passes, is missing, or can't run (exit 126, 127, or pytest's 5) is refused. This replaces the Base worktree, its reinstall and the red-green run.
- **Drift, recorded, never a stop.** `verify.py` fails on a changed file no task or acceptance test names, a task whose files didn't change, or an export or dependency the Public Surface doesn't list, until `## Deviations` has a line naming it with What:, Why: and Effect:. Build decides and goes on; the end of Prove lists every drift.
- **Build:** per AC, write the test, `verify.py red`, then the code; run only nearby tests while coding; `verify.py` once at the end.
- **The hook's own copy.** In Stage 4 or 5 the freshness hook records each `verify.py` run of this project and feature (red per AC; a full run's tree and result), skipping interrupted runs and runs without a worktree tree. A full verify counts as a full test run. `verify.py status` reuses the last pass only when it passed, the hook's copy agrees and the code is unchanged.
- **Prove judges.** `verify.py status`, then reuse or rerun once in the session. A fresh `sdlc:ac-checker` (standard tier, read-only, runs nothing) reads each AC beside its named test and says whether the test proves it. It replaces the verifier on M lite, M full, L, slices and Feature close. The reviewers per track are unchanged (M full's light reviewer, L's reviewers, Feature close's qa-tester).
- **Re-verification:** always in the session, `verify.py`, plus a fresh ac-checker on the ACs that failed only. No fresh verifier round. The stops hold: the same AC failing in two rounds, or round 3 failing, goes to the user.
- **Trust anchor:** Stage 5 counts as passed when an `sdlc:ac-checker` was dispatched in it and the last full run passed on the current code. A new notice, "verify records disagree", fires when `verify.json` and the hook's copy differ, or `verify.json` is missing or malformed while the hook holds a run.
- **S:** unchanged, except its repro test is recorded red with `verify.py red AC-001` and the build ends with `verify.py`.
- **Old plans** (no `## Acceptance tests`) keep the verifier round, so features in flight need no migration. The verifier agent stays for them and on request.

### Alternatives considered

- **A hook that parses each test runner's per-test output to record red and green.** Rejected: fragile across stacks. `verify.py` runs the named test itself and reads only its exit code.
- **Records written by the script alone, honest by convention.** Rejected on Claude Code: an agent can edit `verify.json`. A second copy kept by the hook makes an edit visible. It stays the rule on other hosts.
- **Keep the verifier round, fed with Build's evidence.** Rejected: its cost was rerunning what Build ran. Judging whether a test proves its criterion needs only reading, which a smaller agent does without running anything.

## Consequences

- Prove runs at most one `verify.py` and one small reading agent per round, plus the track's reviewers. Probing, the Base checkout and the fresh re-verifier are gone for new features.
- Every AC is proven by a named test that failed before its code and passes now, or is listed apart as `manual`.
- Known gaps:
  - a red record shows the test failed at that time; it doesn't prove the AC's code was absent then;
  - both record files are agent-writable, so tampering is evident (a notice), not prevented;
  - on Codex and Antigravity the hook keeps no copy (their payloads append `| cat`, which it doesn't match), so `status` never reuses and Prove reruns `verify.py` (amended by ADR 0014: the hook now accepts `| cat` as an output filter, so they get a copy too);
  - `verify.py` doesn't read `.sdlc/baseline.md`: a project with known failures fails verify until the session checks them against the baseline by hand;
  - the prove-budget hook counts the plugin's own `verify.py`, run alone, as a project command, so it isn't killed at 120 s; anything chained after it is;
  - ADR 0012's gap stands: a probe chained after a project command (`npm test; node probe.js`) escapes the 120 s cap.
- Target, not yet evaluated: on planner-team (M, at least 3 runs), Prove at most 5 minutes median, and hidden tests and blind-review defects no worse than the paired baseline.
