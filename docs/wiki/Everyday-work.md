# Everyday work

## 1. Fix a bug (S track)

**Type:** `/sdlc:start fix: export button 500s when the report is empty` (or paste a GitHub issue, Linear or Jira link).

1. **Define:** the agent sizes it S (a fix or tweak, 1–2 files, clear expected behaviour). If what, why or how isn't clear, it asks first, one question at a time. It proves the bug before proposing a fix (a failing test, or exact steps and what they show), then finds the root cause. It writes the change file (the proof and the cause; the proving test is AC-001) and the state file's tasks and Public Surface, a few lines each, with the tests in the same turn. No stop: it says in a line or two what it will do and why.
2. **Build:** in the session, like plain Claude. One call moves it to Build and records the proving test failing (`state.py sync && state.py advance 2 && verify.py red AC-001`), then the fix, then `verify.py` once at the end.
3. **Review:** the agent recommends the reviews the change needs (often none for a small, covered fix) and runs them without stopping, telling you what ran and why ([6](#6-choose-the-reviews-and-act-on-findings)).
4. **Ship:** Learn files a lesson only if it isn't obvious from the code or the commit, and a decision later features must follow in `knowledge/decisions/`, then the final commit on a feature branch, push, PR and CI. It stops with the PR open.

**You decide:** the merge. Anything that adds scope also stops it.

**If the bug is bigger:** when the fix needs more files than expected or the approach is unclear, the agent says so and sizes up to M, which asks for your approval before the build when it's high-risk.

## 2. Add a feature (M track)

**Type:** `/sdlc:start add CSV export to the reports page`

1. **Define:** if anything that would change what gets built is unclear, the agent asks first, one question at a time, each built on your last answer. Then it writes the record, once: the change file (what it's for, why now, the decisions with what was ruled out and why; about 10 or fewer acceptance criteria numbered `AC-001` onward, each with its test in `## Acceptance tests`; out of scope; must-never-break lines and failure modes) and the state file's plan sections (how the build runs, the tasks with their files, the Public Surface listing everything new others can see).
2. **You read and approve.** One message with the path to the change file, the approach and what was ruled out, each acceptance criterion with its test (`manual` ones apart, with their reasons), how the build runs (inline, parts in fresh sessions, or parallel subagents) and any extras the agent would drop unless you keep them. It asks in a question dialog: approve, or change something.
3. **Build:** from the files, in the session by default. Every criterion's test, then one `verify.py red AC-001 AC-002 …` to record them failing, then the code. `verify.py` once at the end runs the checks, every criterion's test and the drift check. Changes from the plan go in the state file's `## Deviations` (`state.py deviation`, "What: … Why: … Effect: …"); they never stop the build.
4. **Review:** the agent recommends reviews from what actually changed (security, code at default or high depth, UI, advisor, or none), each with a reason, and **stops for you to choose**. Each chosen review runs once, fresh: in Claude Code the code review on S and M is the built-in `/code-review`, every other review (and every review in other agents) on `opus` ([6](#6-choose-the-reviews-and-act-on-findings)).
5. **Ship:** Learn, then the final commit, push, PR and CI. It stops with the PR open; the merge waits for your word.

**Good habits:** state what's out of scope up front; answer the questions briefly; challenge any addition you didn't ask for at the approval, not after the code exists. Too big for one session? See [19](Big-work-and-autopilot.md#19-a-big-feature-becomes-a-backlog).

## 3. Build a new service or module (L track)

**Type:** `/sdlc:start build an invoicing service with PDF output`

1. **Define:** `brainstorming` runs the interview, one question at a time, and its design becomes the change file's Why and Decisions. It may offer a browser visual companion (needs Node). There is no separate design document. The criteria, their tests and the state file's plan sections follow, full.
2. **You read and approve** the change file (and `backlog.md` if the work is split into parts, [19](Big-work-and-autopilot.md#19-a-big-feature-becomes-a-backlog)), with how the build runs.
3. **Build:** as the state file's `## How the build runs` says: inline, one part per fresh session, or parallel subagents for truly independent parts. No review agents during the build.
4. **Review:** the recommendation, then your choice; each chosen review runs once on `opus`; high findings go back to Build, each fixed with a failing test first.
5. **Ship:** Learn, the final commit, push, PR and CI. Deploy only when you ask ([10](Shipping-and-gates.md#10-merge-and-deploy)).

**You decide:** Define's approval, the reviews, merge, deploy, migrations.

## 4. Change something risky

Auth, payments, secrets, PII, schema migrations, a breaking change to a public API: the work gets `Risk: high`. Adding a command, flag or field, or an optional field to stored data, isn't breaking: that's `low`. Risk doesn't change the track; it feeds the review recommendation. A change is **security-touched** when `Risk: high`, or the diff touches `areas.sensitive` or `areas.migrations` in `.sdlc/config.json`. Keep those lists right: a sensitive path they miss gets no security review. Every review runs on `opus`, at every size; the model-router hook denies a cheaper one.

1. While you build, the security hooks warn on risky edits and review the diff at turn end. The commit review runs after `git commit`: on a feature branch, build commits wait and are reviewed together with the next review-ready commit. A feature's change that isn't security-touched gets no model review; it is recorded as reviewed. Address each finding, or acknowledge it with a reason.
2. After the build, the agent recommends a **security review** for a security-touched change: a `code-reviewer` with the security-only brief (injection, authz, secrets, SSRF, XSS, unsafe deserialization, dependency risk), plus the dependency audit. On M and L you can still decline it; on S it runs. On a backlog it runs once, at feature close.
3. Gate: no critical or high finding open, no secrets in the diff; recorded in the change file's `## Review`.
4. DB migrations and production deploys are hard stops. Say go explicitly.

Deeper scanners (Claude Security, Semgrep and others, not bundled): `skills/orchestrator/references/integrations.md`.

## 5. Resume or check status

- `/sdlc:status`: one line per feature (track · phase · last gate), open questions and deviations, and whether the repo's scaffold is behind the plugin. Changes nothing.
- `/sdlc:start` with no argument resumes the one feature with `Status: active`, in its phase. Several active: it asks which.

A new session needs no re-explaining: the state file and the change file carry everything.

**Someone else's feature:** the state file names its `Owner:` and `Tool:`. Before advancing a feature you don't own, the agent asks, then records the handover as a deviation.

**Pause a feature:** tell the agent to pause it. It runs `state.py set <feature> Status paused`, so `/sdlc:start` stops picking it up. The trust anchor reports the change once ([21](Shipping-and-gates.md#21-the-trust-anchor-stopped-me)). Ask it to set `active` again to resume. Don't edit the state file by hand.

## 6. Choose the reviews and act on findings

After Build's passing `verify.py`, the agent looks at what actually changed and recommends, each with a one-line reason:

| Review | Recommended when |
|---|---|
| Security | `Risk: high`, or the diff touches `areas.sensitive` or `areas.migrations`, or untrusted input reaches a shell, file path or database |
| Code, high | the spec has must-never-break lines or failure modes, a public interface changed, or the diff is large |
| Code, default | a typical M or L change |
| UI | the diff touches `areas.ui`: always recommended |
| Advisor | only where the agent has one, for a real open judgment call |
| None | a small, contained, fully tested change touching nothing above |

**S:** it runs the recommendation and tells you. **M and L:** it stops and you pick (take it, add, drop). **Autopilot or headless:** it takes the recommendation and logs that it did.

Each chosen review runs **once**, as a fresh agent on `opus`, and ends its report with `VERDICT: PASS` or `VERDICT: FAIL — <ids>`.

- **High findings** go back to Build, each fixed with a failing test first, then `verify.py` again. Then round 2 checks only the fixes: the review that failed runs again on just the files they touched, confirming each finding is gone and no fix added a bug; anything new elsewhere is a ticket. **When round 2 still fails,** the agent stops and asks you (one more fix round, a waiver, or stop), and a hook holds every edit and command until you reply. Each reply allows one more round.
- **You disagree, or the agent does:** a high finding the agent thinks is wrong comes to you with its case. Only you can waive one, recorded as a deviation.
- **Medium and low** findings that are bugs in code the change touched (wrong behaviour, a crash, an unhandled error, a missing test) are fixed too, test first, without asking you. The rest (improvements, code the change didn't touch) are ticketed in the change file's `## Review`.

**A failure that existed before your change:** `verify.py` doesn't read `.sdlc/baseline.md`. When only the test step fails and every failure is listed there, the agent logs it and passes the gate. A new failure is reported; baselining it is your call, recorded as a deviation.

**`verify.py` keeps failing in Build:** the agent debugs it (`systematic-debugging`) and fixes the code or the test. A test that passes before its code exists is refused by `verify.py red`; make it assert the new behaviour, and the change goes in the state file's `## Deviations`. Don't ask it to rerun until green.

**A QA round** (`qa-tester`, runs the feature as a user would, without reading the code) is available on request; its report is `qa-report.md` in the feature's work folder, `.sdlc/state/<feature>/`.

## 7. The stop hook says "re-run tests"

Cause: you are in Review (`Current: Stage 3`) and code changed after the last full test run, or there hasn't been one. Fix: run the **full** suite: the `test` command from `.sdlc/config.json` (in a monorepo, the stale package's own, from its directory; the message names it), or the `test:` command in the state file. A filtered run, a single file or a single package doesn't count.

Changes under `.sdlc/`, `knowledge/`, `.claude/`, `docs/` or the sdlc docs folder, and `.md`, `.mdx`, `.txt` or `.rst` files, don't make results stale. A misbehaving hook: [runbook R4](Troubleshooting.md#r4-blocked-at-stop-with-re-run-tests).

## 8. Handle review feedback

Use `sdlc:receiving-code-review`: check each comment against the code before agreeing, push back with evidence when it's wrong, fix the rest.

| Source | Command |
|---|---|
| Local, before the PR | `/sdlc:review-pr` (picks agents for the diff; the comment, type and simplifier agents need the `sdlc-extras` plugin) |
| Spec versus implementation | Review's code review, from the change file and the state file's plan sections |
| On the GitHub PR | `/sdlc:code-review` |

Severity rules: unrequested public surface (an export, file, endpoint, option, config key or dependency not in the state file's Public Surface, with no stated reason) is **high**. Code-style issues (comments, naming, formatting) are fixed in passing, never high. Other medium and low findings are fixed when they're bugs in the change, else go to the change file's `## Review` as tickets.
