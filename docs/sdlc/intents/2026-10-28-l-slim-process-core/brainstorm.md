# sdlc 2.0: the slim process core

Status: approved 2026-10-28 · Branch `slim/process-core` (from main `4825a0d`) · 2026-10-28

## Intent and why

The plugin's goal is **process value**, not code quality above plain Claude:

- a trustworthy record of each change;
- the same process across a team;
- predictable steps;
- easier review, onboarding and trace-back.

Evals so far showed no quality gain over plain Claude:

- The heavy flow (`ef7fabd`) matched plain Claude's quality at 10-18x the time and tokens.
- The light flows (`d67f0fc`, `0c0ab35`) were cheaper but failed a crash-safety hidden test that plain Claude passed 8/8.

2.0 keeps what gives the process value and cuts what only added agents and rounds.

The record is read at four moments:

1. **Before build:** the user agrees on what will be done.
2. **After build:** a reviewer checks what was built against what was agreed.
3. **Later review.**
4. **Long-term trace-back:** someone, often months later, needs to know why the code is the way it is.

## Goals

1. **Intent before code.** Before any code, the agent and the user agree on what, why and how, and the agent has written it down.
   - The agent judges whether the request already makes these clear. If it does, the agent writes them down and goes ahead.
   - If anything is missing or ambiguous, at any size, the agent asks first, one question at a time, each built on the last answer.
2. **Bugs are proven first.** The agent shows the bug exists (a failing test, or exact steps and what they show), finds the root cause, then proposes the fix.
   - The proving test becomes the fix's acceptance test.
   - Bugs follow the same approval rule as features (goal 4).
3. **Same record shape at every size.** Every change has `intent.md`, `spec.md` and `plan.md` with fixed sections.
   - `intent.md` answers "why?" for a reader months later: what the change is for and who it serves, why now, the user's own words where they matter, the decisions with what was ruled out and why, and a bug's proof and root cause.
   - `spec.md` says what must be true: acceptance lines with AC ids, each naming its test; out of scope; must-never-break lines and failure modes.
   - `plan.md`: the parts in order with their status; a handoff section; a review section.
   - On S they are a few lines each; on M and L they are full.
4. **Approval.**
   - **S:** no stop before the build.
   - **M and L:** the user reads the full intent, spec and plan and approves the build. They stay as the record.
5. **Durable long work.**
   - Large work is split into parts. Each part ends with its tests passing, one commit, its status marked done in `plan.md`, and the handoff updated.
   - After `/clear` or a new session, `/sdlc:start` resumes at the next part from the files alone.
   - All parts land together. Parts exist for context and resumption, not for shipping separately.
6. **Builder like plain Claude.** The builder writes the code and its tests. There are no per-task reviewers and no Prove rounds.
   - The builder works from the spec's must-never-break lines and failure modes, not only from the acceptance list.
   - A crash window in a write is must-fix when the spec says a killed process must not leave the system unusable: a file or lock created and then written, or a write and then a rename.
7. **Reviews are the agent's recommendation, made after the build.**
   - **Options:** a security review; a code review at low, default or high depth; UI design-system review; advisor; or none. Each comes with a reason based on what actually changed (see Approaches).
   - **S:** the agent runs what it recommends and tells the user.
   - **M and L:** the agent stops and the user decides.
   - **Autopilot and headless runs:** they run the recommendation and record that they did.
   - Each review runs once. Its high findings go back to the builder, each fixed with a failing test first. Disagreements go to the user.
   - The record's review section lists what was recommended, what was chosen, and what was found, fixed and ticketed.
8. **Learn before merge.** As the last step before the final commit, the agent distills any non-obvious lesson into the project's knowledge, so it ships in the change and the PR reviewer sees it.
   - The knowledge goes in the existing tiers: CLAUDE.md, a path-scoped rule, or `knowledge/`.
   - Fixed defects go into `recurring-defects.md`.
   - If there's no lesson, the agent writes nothing and says so in one line.
9. **Green twice, then stop at the PR.**
   - Nothing merges unless the full suite is green locally (the last `verify.py` run, on the final code including the learn step's edits) and on CI for the pushed commit.
   - After pushing, the agent watches CI. If CI is red because of the code, it fixes it once, with a failing test first, and pushes again. If CI is still red, it asks the user.
   - A CI-only failure (secrets, a runner problem, a flaky test) is reported, never worked around in code.
   - The agent stops with the PR open. It merges only when the user says so. Without a remote, it stops with the branch ready.
10. **Traceable.** Each commit message names the record's path, so `git blame` leads from a line to its spec and plan.

## Non-goals

- Beating plain Claude on code quality.
- Shipping parts of a change separately.
- Fixing a CI problem by changing code.

## Anti-goals (a failure even if everything works)

Wall-clock time or tokens over these limits against plain Claude on the same task:

| Size | Limit, in both time and tokens |
|---|---|
| S | 1.2x |
| M | 1.5x |
| L | 2x |

The user's own time spent reading and approving is not counted.

## Constraints

- **Every command people type keeps its name and works.** Ease of use comes before token footprint (`/sdlc:setup`, `/sdlc:upgrade`, `/sdlc:eject`, `/sdlc:start`, `/sdlc:status`, `/sdlc:doctor`, `/sdlc:review-pr`, `/sdlc:code-review`, `/sdlc:hookify`, `/sdlc:knowledge-audit`, `/sdlc:revise-claude-md`, `/sdlc:commit`, `/sdlc:commit-push-pr`, `/sdlc:clean_gone`, `/sdlc:prune`, `/sdlc:context-diet`, `/sdlc:deploy`).
- **Codex, Cursor and Antigravity keep working,** through `hosts/hook.py` and the generated host files.
- **2.0 replaces 1.x for everyone,** as the next major version.
  - Existing repos upgrade with `/sdlc:upgrade` and a migration.
  - A change already in progress finishes on the version it started with (user). The plugin is installed per machine, so this means: finish in-progress changes before installing 2.0 (release notes say so). If 2.0 finds a change at an old stage, `/sdlc:start` and `/sdlc:upgrade` stop and tell the user to reinstall 1.8.1 to finish it. 2.0 carries no copy of the old flow (user, on the agent's recommendation).
- The always-on deterministic guards stay on: secret blocking, the pattern warnings, the push security review, the freshness hook and the trust anchor.
- Testing rule: one test per user-visible behaviour, at the lowest level that proves it. Hostile-input matrices only for tier L work (auth, payments, personal data).

## Approaches

**A. Cut the current plugin down in place.**
- The smallest steps, and the tests keep running throughout.
- Against: the flow's text is spread across the orchestrator, its references and about a dozen skills. Earlier edits by subtraction kept leaving stale rules behind.

**B. Rebuild from scratch.**
- The cleanest result.
- Against: it re-proves setup, upgrade, the hooks and three agent hosts that already work and are tested (331 tests).

**C. Keep the base, rewrite the flow (chosen by the user).**
- **Kept as is:** the hooks, `verify.py`, `state.py`, setup/upgrade/eject, doctor, hookify, the multi-agent adapters and every command.
- **Rewritten from this document:** the orchestrator skill and its phase references.
- **Then:** the skills, agents, hooks and docs that only the old flow used are deleted, and an upgrade migration is added.
- **Why chosen:** the flow is where the cost and the confusion live. The base is where the working, tested parts are.

## Decided by the user

Intent before code, with the agent judging when to ask; questions one at a time.

| Topic | Decision |
|---|---|
| Bugs | Prove, then find the cause, then propose the fix. Same approval rule as features. |
| Approval | S skips the stop before the build; M and L read and approve the full spec and plan. |
| Record | Same shape at every size, read at the four moments. |
| Long work | Split into parts that resume after a clear; all parts land together. |
| Builder | Like plain Claude, with no review agents during the build. |
| Reviews | Recommended by the agent after the build: security, code (low/default/high) or none. S runs them; M and L ask. |
| Learn | Knowledge distilled before the merge or PR. |
| CI | Green locally and on CI. The agent fixes red once, then asks. |
| Merge | Stop at the PR; merge only on the user's word. |
| Limits | Time and token limits of 1.2x / 1.5x / 2x. |
| Agents | Codex, Cursor and Antigravity stay supported. |
| Release | Replace 1.x. In-progress changes finish on the old flow. |

## Decided after the builder check

- **In-progress changes at upgrade:** finish them on 1.8.1 before installing 2.0; 2.0 stops on an old-stage change and says so (see Constraints).
- **Design system stays as it works today (user):**
  - Setup writes `design-system.md`, pointing at the theme, components and tokens.
  - The spec names each screen's states (loading, empty, error, success) and its real copy.
  - Before a UI build, each changed screen is mapped to existing components and tokens in `plan.md`'s `## UI mapping`. Since every size now has a `plan.md`, S writes it there too, not in the state file.
  - Anything the system lacks goes to the user first. An approved addition goes into `design-system.md` before the code.
  - `ui-work.md` carries over, rewritten only where it names Prove.
- **Skills only the old flow used are deleted:** writing-specs, clarifying-specs, designing-solutions, analyzing-consistency, executing-plans, subagent-driven-development, writing-plans, and the code-architect agent. Kept, also callable by name: brainstorming (the new flow's interview), test-driven-development, systematic-debugging, verification-before-completion, todo, managing-knowledge, hookify. On L, design decisions go into `intent.md`'s decisions section; there is no `design.md`.

## The agent's calls (for the user to check)

- **Red-first testing stays:** `verify.py` keeps checking that each acceptance line's test was recorded failing before its code and passing after, and the drift check. "Builder like plain Claude" means no review agents during the build, not dropping test-first. The acceptance-to-test table stays in `plan.md` (`## Acceptance tests`), where `verify.py` reads it; `spec.md`'s acceptance lines carry the AC ids.
- **Parts vs backlog:** parts are status lines in `plan.md`, used on M or L when the work won't fit one session. The existing backlog stays as a queue of separate changes (each its own record) that autopilot runs unattended, so `/sdlc:start B<n>` keeps working; slice-specific Stage 6 resting points go.
- **Review options:** the plugin's own `code-reviewer` agent with three brief variants (low: correctness only; default: today's one-pass brief; high: plus a deeper pass on failure modes), which works on every supported agent. Security review is the `code-reviewer` with the security-only brief, plus the dependency audit. The advisor is offered only where the agent has one.
- **Eval:** a later, separate step; this build ends at a release candidate. In measuring the limits, waiting on CI and the push aren't counted (plain Claude doesn't push); agent time runs to local green and the PR.

- **UI check:** the design-system review (today's ui-reviewer) becomes one of the reviews the agent can recommend after the build. It always recommends it when the diff touches `areas.ui`, so on M and L the user can still decline it; on S it runs.
- **Advisor:** one of the recommendable reviews, not a habit call. The orchestrator tells the model not to call it otherwise during an sdlc change.
- **Model tiers:** the builder runs on the session's model. Every review runs on the top tier (opus); the model router keeps enforcing that.
- **What the review recommendation is based on:** what the diff touched (sensitive or migration paths, public interfaces, concurrency, persisted data, UI files), how big it is, and the spec's must-never-break lines.
- **Removed from the flow:**
  - the Prove phase and its rounds;
  - the verifier, the ac-checker and the qa-tester;
  - the relay and its stage agents;
  - per-task review in subagent-driven development;
  - the advisor's fixed pre-Ship call;
  - the fixed reviewer matrix by track.

  They are deleted unless something kept still uses them. The qa-tester stays available on request if cheap to keep.
- **Size (S/M/L):** keeps today's footprint rule. 1-2 files is S unless risky, which is M. The track only sets the record's depth and whether there's a stop before the build.
- **`plan.md` parts:** the agent splits by context size, not by feature slice. One part should fit a session comfortably.
- **One CI fix attempt** before asking.
- **State file:** keeps tracking phase, part, Base and the record's paths. Phases become Define → Build → Review → Ship (Learn inside Ship).

## Left to the builder

- **Exact file and section names** inside the rewritten references, as long as `spec.md` and `plan.md` keep the fixed sections above.
- **How `state.py` names the new phases,** and the migration's wording.
- **Hooks that only served the removed phases:**
  - `prove_budget.py`;
  - parts of `verify_freshness.py`, `trust_anchor.py` and `model_router.py` that check Prove-only things.

  Each is either adapted to the new Review step or removed, with its spec rows updated.
- **Which docs and diagrams to rewrite and which to delete:** README, guidebook, playbook, prd, specs and the SVGs.
- **ADRs:** a new ADR records this 2.0 decision and names the ADRs it supersedes.

## Done means

- Every goal above is described in the orchestrator and its references, and none of the removed parts is left in any doc or flow.
- Full suite green on Python 3.10; `claude plugin validate .` passes for both plugins; `scripts/hosts.py check` reports nothing stale.
- An upgrade from 1.8.x to 2.0 is shown on a scratch repo: it refuses while a change is in progress, and works once none is.
- A release candidate is ready for the eval session, which then runs 2.0 against plain Claude for the limits and the quality bar (separate step).
