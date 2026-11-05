# Shipping and gates

## 9. Skip a gate deliberately

Say `skip` or `just ship it`. The agent will:

1. name the gates being skipped,
2. record them as a deviation in the state file,
3. comply.

Hard stops (merge, production deploy, migrations, anything irreversible) still wait for your explicit word. Skipping a gate is allowed; skipping silently is not.

## 10. Merge and deploy

1. **Ship:** Learn, then one shell call with git and `gh` commits on a feature branch (code, tests, the change file and the state file), pushes and opens a PR that links the change file. The agent watches CI: red because of the code, it fixes it once (failing test first) and pushes again; still red, or red for a CI reason (a missing secret, a runner problem, a flaky test), it stops and tells you. Without a remote, it stops with the branch ready.
2. **It stops at the PR:** `PR <url> open, local and CI green; say "merge" to merge.` **The agent never merges without you saying so.** On "merge", the `finishing-a-development-branch.md` reference merges and cleans up worktrees; `/sdlc:clean-gone` prunes merged local branches when asked.
3. **Deploy** is a separate request: `/sdlc:deploy [feature] [environment]`.
   - It warns if the feature hasn't reached Ship, and continues only on your word.
   - It uses the project's existing deploy path (scripts, a CI job, the platform CLI). None: it says so and stops.
   - Before production or a migration it shows the environment, version, steps, migration and rollback command, and waits for your yes. A routine staging deploy doesn't.
   - It runs a smoke test. A failure: it offers the rollback, and a production rollback needs another yes.
   - It writes `release.md` in the feature's work folder (version, environment, steps, smoke result, rollback) and commits it only if you ask.

## 21. The trust anchor stopped me

The trust anchor watches what verification relies on. When something weakens it, the turn stops once with `⚠ Verification anchors changed: … Your next message accepts it.` The agent tells you what changed and why, and doesn't undo it on its own.

It reports, per active feature:

- `Track:` down, `Risk:` high → low, `Top model:`, `Base:` or `Process:` changed;
- a failing test added to `.sdlc/baseline.md`, or commands in `.sdlc/config.json` changed since `Base:`;
- the change file edited above `## Review` (its criteria and tests) after Review started;
- leaving Review without a passing full run of the current code, at every size, or with code changed since that run;
- leaving Review while a review's latest report says `VERDICT: FAIL`, unless you waived it;
- `verify records disagree`: `.sdlc/.work/verify.json` differs from the freshness hook's copy of the run, or is missing or damaged while the hook holds one;
- a feature stopping being active other than by finishing (a pause, a deleted state file);
- a damaged trust-anchor record.

Only current features (`Process: 3`) are watched.

**What to do:** read it. If the change is right, carry on: your next message accepts it. If not, say so and ask the agent to put it back.

A change that only adds checks (Track up, Risk low → high) shows `Stricter process: …` and doesn't stop you.

Autopilot won't start a session while a notice is open; its JSON `stopped` reason quotes the notice. Read it, send any message in a normal session to accept it, then run autopilot again.

## Who decides what

**Hard stops.** The agent always stops and asks:

| Decision | Owner |
|---|---|
| Define's approval on high-risk M (and L on doubt): the change file, the plan (and backlog), how the build runs | You |
| Which reviews run after the build, on M and L | You |
| Anything that adds scope | You |
| A reviewer and the agent disagreeing on a high finding | You |
| CI still red after one fix | You |
| Merge (Ship stops with the PR open) | You |
| Production deploy | You |
| DB migration | You |
| Anything irreversible | You |

**Also yours:**

| Decision | Owner |
|---|---|
| Running setup, the stack, the recorded commands | You approve |
| Each audit batch, each AI-config migration | You approve, edit or drop |
| Upgrade: edited plugin files, new workflows, migrations | You choose per file / per migration |
| PR or local merge after setup, upgrade, eject | You |
| Adding a failure to the baseline | You, recorded as a deviation |
| Waiving a high finding | You, recorded as a deviation |
| Design-system changes a reviewer proposes | You |
| Accepting a trust-anchor notice | You, with your next message |
| Skipping a gate | You, recorded as a deviation |

**The agent's calls:**

| Decision | Owner |
|---|---|
| Track and risk | The agent proposes; you can override |
| Whether to ask before writing the record | The agent judges; it asks when what, why or how isn't clear |
| How the build runs (inline, parts, parallel) | The agent, written in the state file; shown at the approval when there is one |
| Which reviews to run on S | A fixed trigger list (`s-track.md` step 5); none unless one fires |
| Which reviews to run on autopilot and headless runs | The agent's recommendation |
| Verify verdict | The latest `verify.py` run on the current code |
| Fixing high findings, and one CI fix | The agent, without asking |
