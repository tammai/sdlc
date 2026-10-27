# ADR 0014: A lighter S, and a companion plugin for niche parts

- **Status:** Accepted, 2026-10-27. Amends [ADR 0010](0010-four-phases.md): S no longer writes `intent.md`, `spec.md` and `plan.md`, and Ship no longer stops to ask on S and `Flow: lite`. Amends [ADR 0013](0013-build-proves-prove-judges.md): Codex, Cursor and Antigravity now get the hook's copy of a verify run, and S's one acceptance test comes from the state file. Amended by [ADR 0015](0015-prove-only-where-it-pays.md): S has no Prove step at all, and a security review (in Prove and at commit) runs only on a security-touched change.
- **Deciders:** Tâm Mai.

## Context

The stage-1 eval ran the S task (a one-line fix plus one test) three times per arm. Quality was equal: hidden tests 100% in both arms, no blocking or major defects, rubric 4.80 in both. The plugin cost 11.7x the tokens, 7.9x the agent time and 2 human touches against 1.

- Every run stopped at Ship to ask about the commit. Each time the agent offered options and recommended the same one: commit on a new branch.
- S still wrote `intent.md`, `spec.md`, `plan.md` and `test-report.md` for a change of one line.
- One run ran `verify.py` chained (`cd … && python3 …/verify.py; echo exit=$?`, `… | tail -40`). The freshness hook matched only the bare command, kept no copy, and the agent spent a turn explaining a false "skipped Prove" notice.

The audit of the plugin itself found 4,643 tokens loaded on every turn, across 61 components. The official marketplace highlights plugins at 2,000 or less. Part of that was niche: the Ralph loop, hookify's list, configure and help commands, four review and analysis agents most sessions never call, and several components doing the same job (three ways into code review, two into knowledge, two into context trimming). Three vendored skill descriptions (`brainstorming`, `test-driven-development`, `systematic-debugging`) fired on almost any request.

## Decision

- **S writes no documents.** Define records two lines in the state file with `state.py set`, with no approval:
  - `Intent:` the bug and the expected behaviour, one line;
  - `Repro: <test file> › <test name> | <command>`: the repro test Build writes first.

  `verify.py` reads the `Repro:` line as AC-001 when there is no `plan.md`, and skips the drift check. Prove writes no `test-report.md` on S. Ship's Learn files a lesson only when there is one.
- **Ship doesn't ask on S and `Flow: lite`.** It commits on a feature branch, creating one off the default branch when needed, pushes and merges nothing, and reports the branch and commit in one line. It asks only when the user wants a push, a PR, a merge or a deploy. `Flow: full` and L still stop and ask.
- **A companion plugin, `sdlc-extras`,** in the same marketplace (`plugins/sdlc-extras/`). It holds:
  - `/sdlc-extras:ralph-loop`, `cancel-ralph` and `ralph-help`, with the Ralph Stop hook and its setup script;
  - hookify's `list`, `configure` and `help` commands;
  - the `conversation-analyzer`, `type-design-analyzer`, `comment-analyzer` and `code-simplifier` agents.

  Core keeps the hookify engine, `/sdlc:hookify` and `writing-hook-rules`. `/sdlc:hookify` and `/sdlc:review-pr` use the companion's agents when it is installed and say so when it isn't. The role guard covers `sdlc-extras:` reviewers. The legacy `verifier` stays in core for features started before ADR 0013.
- **One entry point per job.** The duplicates become reference files:
  - `requesting-code-review` → `skills/executing-plans/references/` (`requesting-code-review.md`, `code-reviewer.md`). Entry points: Prove, `/sdlc:review-pr` (local diff), `/sdlc:code-review` (GitHub PR).
  - `claude-md-improver` → `skills/managing-knowledge/references/claude-md-improver.md`. Entry point: `managing-knowledge`.
  - `trimming-context` → `skills/setting-up-projects/references/trimming-context.md`. Entry points: `/sdlc:context-diet` and setup.
- **Smaller listings.** Long agent descriptions are shortened, and the three vendored skill descriptions say what each does and when, scoped to the orchestrator's phases.
- **Bug fixes from the same eval:**
  - the freshness hook recognises the plugin's `verify.py` as the command itself, optionally after `cd <dir> &&`, with redirects ignored and followed only by `| tail`, `| head`, `| grep`, `| cat` or `; echo …`, and copies `verify.json`'s entry for that run when its tree is the current code; when the exit code is verify.py's own it must agree. A command that only mentions verify.py, or rewrites its record after running it, is not recorded;
  - the Verified tree comes from `verify.py status`'s `tree` field;
  - setup and upgrade untrack files committed under the plugin's ignore lines;
  - `scaffold.py enable-plugin` skips when the running plugin isn't Claude Code's installed copy (`--plugin-dir`, or not installed), so a session never loads two;
  - every hook starts through `hooks/sg-python.sh`, and `/sdlc:doctor` checks that launcher ("hook python");
  - the contributor `CLAUDE.md` moved to `.claude/CLAUDE.md`, and `plugin.json` has `homepage` and `repository`, so `claude plugin validate --strict` passes.

### Alternatives considered

- **Keep S's three files, shorter.** Rejected: on a one-line fix the expected behaviour is the repro test. The files restated it, and writing them was a large part of S's cost.
- **`disable-model-invocation` on the niche parts instead of moving them.** Rejected for commands and agents: they would still be listed, and the Ralph Stop hook would still run on every turn end. Used in spirit for the duplicates, which became reference files that load only when their entry point reads them.
- **Retire the verifier now.** Rejected: features planned before ADR 0013 still need it. It goes once those plans have aged out.
- **Ask at Ship on every track, with a recommended default.** Rejected: on S and lite the agent recommended the same safe step every time, and a local branch commit is easy to undo.
- **An icon in this change.** Deferred on purpose: the first icon submitted becomes the permanent listing icon.

## Consequences

- S is a repro test, the fix, one `verify.py` and a commit. Its record is the state file's `Intent:` and `Repro:` lines and the commit. Features started before this keep their files.
- "Files, not the agent's head" (ADR 0010) now applies to M and L only. On S the state file is the whole hand-off.
- S and lite end with a local commit the user hasn't seen. Nothing leaves the machine without the user asking.
- Users who want the Ralph loop, hookify's list, configure and help commands, or the four extra review agents install `sdlc-extras@sdlc` beside `sdlc@sdlc`. Without it, `/sdlc:review-pr` skips those three reviewers and says so, and `/sdlc:hookify` does the conversation analysis itself.
- The companion's version is bumped with sdlc's at each release.
- On Codex, Cursor and Antigravity the freshness hook now keeps its copy, so `verify.py status` can reuse a run there too.
- Known gaps:
  - on S, drift isn't checked (no plan names the files);
- Target, not yet evaluated: S at most 2x the plain run's agent time and 2.5x its tokens with one touch (ADR 0011's target), and the always-on listing under 2,000 tokens.
