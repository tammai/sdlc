# ADR 0020: sdlc 2.0, the slim process core

- **Status:** Accepted, 2026-10-28. Supersedes the Prove parts of ADRs [0013](0013-build-proves-prove-judges.md) through [0019](0019-model-security-review-only-for-security-touched-work.md): Prove and its rounds, Lite/Full, `Prove: run|skip`, the verifier, the ac-checker and the relay. Keeps [0012](0012-enforced-prove-budget.md)'s command budget (now in Review), 0013's record (`verify.py`, red first) and 0019's security gate.
- **Deciders:** Tâm Mai. Design: `docs/sdlc/intents/2026-10-28-l-slim-process-core/brainstorm.md`.

## Context

Evals against plain Claude Code showed no gain in code quality:
- The heavy flow (`ef7fabd`) matched plain Claude at 10–18x the time and tokens.
- The lighter flows (`d67f0fc`, `0c0ab35`) were cheaper but failed a crash-safety hidden test that plain Claude passed 8 of 8 times.

The user set the plugin's goal as process value, not quality above plain Claude: a trustworthy record of each change, the same process across a team, predictable steps, and easier review, onboarding and trace-back. Code quality only needs to stay no worse than plain Claude's, at a bounded cost.

## Decision

1. **The same record at every size**, split by lifetime:
   - `intent.md`: why, decisions, bug proof and root cause. Kept.
   - `spec.md`: acceptance criteria, each with its test (`## Acceptance tests`), must-never-break lines, out of scope. Kept.
   - `review.md`: recommended and chosen reviews, verdicts, fixes, tickets, lessons filed. Kept.
   - `plan.md`: how the build runs, tasks, handoff, deviations. A working file `/sdlc:prune` may delete once merged.
2. **Intent before code.** The agent judges whether what, why and how are clear. If anything is missing or ambiguous, at any size, it asks first, one question at a time. A bug is proven first, then its root cause, then the fix. S doesn't stop before the build; on M and L the user reads and approves intent, spec and plan.
3. **The builder works like plain Claude:** no review agents during the build. Tests are recorded failing first (`verify.py red`). The builder works from the must-never-break lines and failure modes, not only the acceptance list; a crash window in a write is must-fix. How the build runs (inline, parts in fresh sessions, or parallel subagents) is the agent's call, written in `plan.md` before the build.
4. **Reviews are recommended after the build:**
   - The options are security; code at low, default or high depth; UI (always when `areas.ui` is touched); the advisor where available; or none.
   - S runs the recommendation. M and L ask. Autopilot and headless runs take the recommendation.
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
