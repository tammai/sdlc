# ADR 0020: sdlc 2.0, the slim process core

- **Status:** Accepted, 2026-10-28. Supersedes the Prove parts of ADRs [0013](0013-build-proves-prove-judges.md) through [0019](0019-model-security-review-only-for-security-touched-work.md): Prove and its rounds, Lite/Full, `Prove: run|skip`, the verifier, the ac-checker and the relay. Keeps [0012](0012-enforced-prove-budget.md)'s command budget (now in Review), 0013's record (`verify.py`, red first) and 0019's security gate.
- **Deciders:** Tâm Mai. Design: `docs/sdlc/intents/2026-10-28-l-slim-process-core/brainstorm.md`.

## Context

Evals against plain Claude Code showed no gain in code quality:
- The heavy flow (`ef7fabd`) matched plain Claude at 10–18x the time and tokens.
- The lighter flows (`d67f0fc`, `0c0ab35`) were cheaper but failed a crash-safety hidden test that plain Claude passed 8 of 8 times.

The user set the plugin's goal as process value, not quality above plain Claude: a trustworthy record of each change, the same process across a team, predictable steps, and easier review, onboarding and trace-back. Code quality only needs to stay no worse than plain Claude's, at a bounded cost.

## Decision

1. **The same record at every size**, split by reader, both kept and committed with the code (amended for RC3: it was four files, `intent.md`, `spec.md`, `plan.md` and `review.md`):
   - The change file, `<docs>/changes/<feature>.md`, for people: why, decisions, a bug's proof and root cause; acceptance criteria, each with its test (`## Acceptance tests`), must-never-break lines, failure modes, out of scope; and last, `## Review`: recommended and chosen reviews, verdicts, fixes, tickets, lessons filed. What's above `## Review` is fixed once Review starts.
   - The state file, for the agent: where the change stands (phase, gates, deviations, open questions) and, from Define, how it's built (how the build runs, handoff, tasks with their files, public surface). Scripts and hooks parse it.
   One file per reader instead of four: a reviewer or teammate reads one page, the agent writes less, and the scripts keep their tables.
2. **Intent before code.** The agent judges whether what, why and how are clear. If anything is missing or ambiguous, at any size, it asks first, one question at a time. A bug is proven first, then its root cause, then the fix. S and low-risk M don't stop before the build (amended: the eval of 1ad52f8 showed the stop only ever took the agent's own proposal; a low-risk M records in its Gate log that it wasn't stopped); on high-risk M and on L the user reads and approves the change file.
3. **The builder works like plain Claude:** no review agents during the build. Tests are recorded failing first (`verify.py red`). The builder works from the must-never-break lines and failure modes, not only the acceptance list; a crash window in a write is must-fix. How the build runs (inline, parts in fresh sessions, or parallel subagents) is the agent's call, written in the state file before the build.
4. **Reviews are recommended after the build:**
   - The options are security; code at default or high depth (amended: low depth only re-proved what `verify.py` proves, each AC's test red then green; a `manual` AC is checked by whichever review runs); UI (always when `areas.ui` is touched); the advisor where available; or none.
   - S runs a fixed trigger list instead of judging (high risk, a sensitive, migration or UI path, or a declared public surface; otherwise none), so the same input gets the same process. A low-risk M uses the same kind of list (amended: one opus reviewer alone took longer than plain Claude's whole M task): nothing fires, no review, since every AC was seen failing then passing; what fires runs without asking. High-risk M and L ask. Autopilot and headless runs take the recommendation.
   - Ship is one command (`scripts/ship.py`, then the commit, push and PR in the same call), so it is one turn on every track.
   - Each review runs once, on opus. High findings are fixed test-first, at the rule, not the instance. A disagreement goes to the user.
5. **Learn before merge.** Lessons are distilled into the project's knowledge before the final commit, so they ship with the change.
6. **Green twice, then stop at the PR.** The full suite passes locally and on CI. The agent fixes a red CI run once, then asks. It merges only on the user's word.
7. **Four phases at stages 1, 4, 5 and 8** (Define, Build, Review, Ship), so the hooks keep reading numbers. `Process: 2` marks a 2.0 feature. The hooks act only on those, and `state.py` and the upgrade refuse 1.x features: they are finished on 1.8.1 first.
8. **Every typed command keeps its name.** Codex, Cursor and Antigravity keep working.
9. **Read a file only when the context doesn't already hold it,** and ask the scripts for short answers instead of opening files.

## Consequences

- **Removed:**
  - the Prove phase, its rounds and its round cap;
  - Lite/Full and `Prove: run|skip`;
  - the verifier, ac-checker and code-architect agents and the relay;
  - the skills writing-specs, clarifying-specs, designing-solutions, analyzing-consistency, executing-plans, subagent-driven-development and writing-plans;
  - `design.md`.
- **Limits against plain Claude on the same task**, in both time and tokens (the user's own reading time not counted):
  - S: 1.2x;
  - M: 1.5x;
  - L: 2x.
- **Unmeasured until the eval session runs the release candidate:** the limits above, and whether quality holds without Prove.
