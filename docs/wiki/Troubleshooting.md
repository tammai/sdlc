# Troubleshooting

State changes go through `scripts/state.py` (`python3 <plugin>/scripts/state.py <command> <feature> …`); it updates the state file and the control contract together. Below, `state.py` means that call.

## R1. Plugin won't load or components are missing

1. Open `/plugin` and confirm `sdlc` is installed and enabled. If not, install it (see [Install](Install.md)).
2. Slash commands use the `sdlc:` prefix. If `/sdlc:start` isn't found, restart the session after installing or updating.
3. Still missing after a restart: update the marketplace and reinstall the plugin from `/plugin`.
4. Maintainers: run `claude plugin validate .` in the plugin repo and read the first error; check `.claude-plugin/plugin.json` and `hooks/hooks.json` are valid JSON.

## R2. First session is slow or the security reviewer is unavailable

Cause: the SessionStart hook builds a venv with the Claude Agent SDK in the background, and only when the security hooks receive credentials (a Claude Code sign-in, or `ANTHROPIC_API_KEY`). Without credentials the model reviews are skipped and the venv is never built; pattern warnings still work. A session closed before the build finishes cancels it.

1. Keep a signed-in session open for the first start to finish (timeout is 180 s).
2. If it failed, check network access to the Python package index, then start a new session to retry.
3. To rebuild from scratch: remove `agent-sdk-venv` from the security state directory (see [Where things live](Where-things-live.md#by-path); `/sdlc:doctor` prints it) and start a new session.
4. The venv lives outside the plugin, so it survives plugin updates.

## R3. Security hook is too noisy or too slow

1. Identify which part is firing: edit pattern warnings, turn-end review, or commit/push review. The turn-end and commit reviews run only while a security-touched feature is active (ADR 0019). While a feature is active, the commit review runs once per review-ready diff (from Review on), not on every build commit, and only on a security-touched change (`Risk: high`, or a diff touching `areas.sensitive` or `areas.migrations`); any other is recorded as reviewed with no model call. If a sensitive path gets no review, add it to `areas.sensitive` in `.sdlc/config.json`.
2. Turn off only that part with the matching variable from the table above.
3. Prefer fixing the finding. If it's a false positive you'll see again, tell the reviewer why in the response (acknowledged findings are fine) rather than disabling the hook.
4. `SECURITY_GUIDANCE_DISABLE=1` is a last resort; record it with `state.py deviation`.

## R4. Blocked at Stop with "re-run tests"

The verify-freshness hook is active only while an active feature (`Process: 3`) says `Current: Stage 3 – Review`, at every size.

1. Run the **full** test command: `commands.test` from `.sdlc/config.json` (monorepo: the stale package's own, from its `path`; the block message names it), or the `test:` command in the state file's `Commands:` line. A filtered run, single test file, pytest node id or single Go package doesn't count.
2. Make sure no code changed after that run. Formatters, `sed -i` and subagents count as changes; the hook compares the worktree against the tree recorded at the last full run.
3. Edits to `.md`, `.mdx`, `.txt`, `.rst` and anything under `.sdlc/`, `knowledge/`, `.claude/`, `docs/` don't mark results stale.
4. If the recorded test command is wrong, fix `commands.test` (or the package's) in `.sdlc/config.json`, or the `Commands:` line for a repo without setup. A changed config command raises a trust-anchor notice ([R19](#r19-a-trust-anchor-notice-stops-the-turn)).
5. If the freshness state itself is wrong, delete `.sdlc/.work/verify-freshness.json`; the next full run recreates it.
6. The hook never fails the session on its own error: it writes `.sdlc/.work/verify-freshness.error`, which doctor reports and the next clean run removes. If it blocks wrongly, run the hook tests ([runbook](../runbook.md#run-the-tests)) and open an issue with the transcript and that file.

## R5. `verify.py` gives different answers each time

1. Don't retry until green. A test that passes after failing is flaky, and a retried-until-green test doesn't pass the gate.
2. Run the failing test a few times in isolation (at most 5 repeats; its row's command in the change file's `## Acceptance tests` runs just that test) and record the results in the change file's `## Review`.
3. Fix or quarantine the flaky test with your approval, and record it with `state.py deviation`.

## R6. Ralph loop won't stop

The Ralph loop comes with the optional `sdlc-extras` plugin.

1. `/sdlc-extras:cancel-ralph`. It reports the iteration it stopped at.
2. If the command fails, delete `.claude/ralph-loop.local.md` by hand; the stop hook then lets the session end.
3. Always start loops with `--max-iterations`.
4. A malformed state file (missing frontmatter field) no longer crashes the hook; delete it if it keeps looping.

## R7. A hookify rule doesn't fire, or fires too much

1. Is the file in the right place? `.claude/hookify.<name>.local.md` (personal) or `.claude/hookify/<name>.md` (team), under the folder the session started in. A session started above the repo (a workbench of repos) also gets the repo's rules for a file tool on a path in it, or a command that starts with `cd <repo>` (or `git -C <repo>`, or runs with its cwd there), but only when that folder has no `.sdlc/` and the repo has `.sdlc/config.json`; `bash -c "cd ..."` and scripts don't count.
2. Frontmatter: `enabled: true`, a valid `event` (`bash`, `file`, `stop`, `prompt`, `all`), `action` (`warn` or `block`).
3. Parser limits: never put `---` inside a pattern (write `-{3}`), keep each `pattern:` on its own line, don't quote patterns. Matching is case-insensitive.
4. Fields: bash rules use `command`; file rules use `file_path`, `new_text` (falls back to `content` on Write), `old_text` or `content`; prompt rules use `user_prompt`. Operators: `regex_match`, `not_regex_match`, `contains`, `not_contains`, `equals`, `starts_with`, `ends_with`.
5. All conditions in a rule must match for it to trigger. Warnings reach Claude as context; block reasons appear as the permission-denied reason.
6. With `sdlc-extras` installed, `/sdlc-extras:hookify-list` to see what's active and `/sdlc-extras:hookify-configure` to toggle; otherwise read and edit `enabled:` in the rule files.
7. Over-firing: narrow the pattern or add a condition; switch `block` to `warn`.

## R8. `/sdlc:start` picks the wrong feature, or says there are several

1. `/sdlc:status` shows every feature, its phase and status.
2. A finished feature: `state.py set <feature> Status done`. One you're not working on now: `state.py set <feature> Status paused`. Pausing raises a trust-anchor notice once ([R19](#r19-a-trust-anchor-notice-stops-the-turn)).
3. Answer the "which one" prompt if it still asks.

## R9. A state file is missing, stale or wrong

The state file is `.sdlc/state/<feature>.md`; beside it, git-ignored, `state.py` writes the control contract (`<feature>.json`, `<feature>.events.jsonl`), derived from it.

1. A wrong field: `state.py set <feature> <Field> <value>` (Status, Track, Risk, Top model, Base, Owner, Tool, Slice gates, Process). Changing Track, Risk, Top model, Base or Process raises a trust-anchor notice ([R19](#r19-a-trust-anchor-notice-stops-the-turn)).
2. A wrong phase: `state.py advance <feature> <n>` without `--gate`, where `<n>` is 1 Define, 2 Build, 3 Review or 4 Ship (a backlog feature stays at 2 between parts).
3. A hand edit, or a missing or damaged `.json`: `state.py sync <feature>` rewrites the contract from the state file. `state.py` refuses a state file without `Status:` and `Current: Stage <n> – <name>`, and one without `Process: 3`.
4. A lost state file: it held half the record (the plan sections: how the build runs, handoff, tasks, Public Surface, deviations); git history usually has it. Otherwise write a new one from the template in `skills/orchestrator/references/flow.md` (S: `s-track.md`), rewrite its plan sections from the change file and the diff (or `verify.py`'s drift check fails), tick the phases the change file shows done (`## Acceptance tests` filled: Define; `## Review` written: Review), set `Current:` to the next phase's stage, then `state.py sync <feature>` and `state.py deviation <feature> "state file reconstructed"`.

## R10. Hooks error on Windows or with an odd Python

`hooks/sg-python.sh` probes `python3`, `python` and `py -3`, skipping the Microsoft Store stub, and forces UTF-8. It remembers the interpreter it chose, and where that name resolved, in `sdlc-hook-python` in the plugin's data folder (else `~/.cache/sdlc/`, never a shared temp folder; a file the user doesn't own is ignored), so later hooks skip the probes; it probes again when that name resolves elsewhere or is gone. Under Claude Code it also writes `sdlc-hook-python.fast` there, the interpreter's path, which each hook's command in `hooks.json` starts directly without the launcher; while that path exists, a PATH change doesn't reach it. Delete both files to force a fresh probe. If the security hook still fails, run `bash hooks/sg-python.sh -c "import sys; print(sys.version)"` to see which interpreter it chose. Every hook in `hooks/hooks.json` starts through it, so one working Python 3 serves them all. Doctor's "hook python" row runs the launcher; when it fails, install Python 3 from python.org (not the Microsoft Store) and, on Windows, Git Bash. The Ralph loop's hook (`sdlc-extras`) runs under bash.

## R10a. Hooks feel slow

Set `SDLC_HOOK_TIMES=1` in the session's environment (for one project: `"env": {"SDLC_HOOK_TIMES": "1"}` in `.claude/settings.local.json`) and restart the session. Each hook then appends `{"t", "hook", "event", "tool", "ms", "rc"}` to the project's `.sdlc/.work/hook-times.jsonl` (only where `.sdlc/` exists): the script name, the hook event and tool, its wall-clock time including the launcher, and its exit code. The security review after a commit, push or Stop runs in the background (`asyncRewake`), so its time doesn't hold up a tool call. It sends every hook through the launcher (no direct start) plus one more bash, so the times include that; turn it off after measuring. It needs bash 5 or newer (`EPOCHREALTIME`): macOS's stock `/bin/bash` is 3.2 and logs nothing, so put a newer bash first on `PATH` (`brew install bash`). Total time per hook and event: `python3 -c "import json,collections; c=collections.Counter(); [c.update({(e['hook'], e['event']): e['ms']}) for e in map(json.loads, open('.sdlc/.work/hook-times.jsonl'))]; print(c.most_common())"`.

## R11. A gate is blocking and you disagree

A gate is a phase's exit check; it is a decision, not a fault. Say `skip` or `just ship it`: the orchestrator names the skipped gates, records them with `state.py deviation`, and continues. See [playbook 9](Shipping-and-gates.md#9-skip-a-gate-deliberately).

Hard stops are different: they always wait for your answer and aren't skipped. They are the approval before the build and the review choice after it on high-risk M (on L only when the agent's own checks leave a doubt), anything that adds scope, a reviewer and the builder disagreeing on a high finding, CI still red after one fix, merge, production deploy, DB migrations, and anything irreversible.

## R12. Setup stopped halfway

1. Run `/sdlc:setup` again. It reads `completed_steps` from the lock and continues with the next step on the same `sdlc/setup` branch.
2. Config or lock won't parse: fix the JSON, or restore it from git, then rerun.
3. Want a clean restart instead: delete the branch, then `python3 <plugin>/scripts/scaffold.py init --kind <greenfield|brownfield> --force` and rerun setup.
4. "Working tree not clean": commit or stash first; setup won't mix its commits with your changes.

## R13. A project command is missing, wrong, or its tool isn't installed

1. `/sdlc:doctor` (repo · commands, command tools, commands run) or `python3 <plugin>/scripts/scaffold.py contract` shows, per package, which required commands are missing and which tools aren't on PATH.
2. Commands live in `.sdlc/config.json`: `commands` for one project, `packages[].commands` per package. Use what the team already runs; set a step to `null` if it doesn't apply to that stack.
3. A tool not found: install it the way the project expects (the lockfile and toolchain files say which version), or fix the command.
4. Then `scaffold.py run-commands` runs them once and records the result, and `/sdlc:upgrade` makes the generated CI workflow follow (or review its diff if you edited the workflow). During a feature, changed commands raise a trust-anchor notice ([R19](#r19-a-trust-anchor-notice-stops-the-turn)).

## R14. An upgrade won't overwrite a file, or keeps asking about it

1. That file is seeded and you edited it, so the upgrade refuses to overwrite it (`scaffold.py render --if-unchanged` exits 2). This is on purpose.
2. Pick **apply** to take the proposed merge, **skip** to be asked next time, or **keep mine**: `scaffold.py forget <path>` makes it yours for good and upgrades stop asking.
3. A deleted plugin file is offered for restore once; declining forgets it.

## R15. A migration was declined and you want it after all

`/sdlc:upgrade --revisit` lists skipped migrations with the reason you gave and offers each again. `scaffold.py migrations --revisit` shows the same list without changing anything.

## R16. `verify.py` blames the feature for an old failure, or the baseline looks wrong

1. Check `.sdlc/baseline.md`: failing tests by file › name, lint/type errors as counts per rule and file. A count that went **up** counts as new.
2. No baseline in a brownfield repo: rerun `/sdlc:setup`'s baseline step.
3. A pre-existing failure missing from the baseline: adding it is your decision. Add it with a note and record it with `state.py deviation` naming the test; nothing adds items on its own. A baseline that gains a failure during a feature raises a trust-anchor notice ([R19](#r19-a-trust-anchor-notice-stops-the-turn)).
4. `verify.py` doesn't read the baseline: a baselined failure fails it. When only the test step fails and every failure is listed there, Build logs it with `state.py log` and passes the gate; nothing checks that mechanically yet ([spec 04 Known gaps](../specs/04-verification.md#known-gaps)). Ship needs `ship.py <feature> --waive-baseline` for the same case, which refuses unless `.sdlc/baseline.md` lists a failing test and only the test step failed, and logs the waiver.

## R17. Eject left something behind or broke the build

1. `scaffold.py eject` (dry run) shows what it would still remove; edited plugin files are only deleted when you say so.
2. Imports into deleted files (`eslint.sdlc.mjs` in `eslint.config.*`, `extend = ".sdlc/lint/ruff.sdlc.toml"` in `pyproject.toml`) should have been offered as diffs. If not, remove them by hand and rerun the verify commands.

## R18. A subagent dispatch is denied by the model router

The hook checks Agent/Task dispatches only while a feature (`Process: 3`) has `Status: active`; the deny reason says which check failed. Every dispatch, denied or not, is logged to `.sdlc/.work/dispatches.jsonl`.

1. **No model:** the dispatch must name `sonnet` or `opus` (Model selection in `sdlc:orchestrator`). Commands that launch agents, such as `/sdlc:review-pr`, name one too. Exempt: forks, and impeccable's own agents (`impeccable-*`), which impeccable spawns without a model.
2. **Fable:** used only on your request. `state.py set <feature> "Top model" fable` on every active feature (one active feature without it keeps Fable denied). This raises a trust-anchor notice ([R19](#r19-a-trust-anchor-notice-stops-the-turn)).
3. **Haiku:** denied everywhere; the cheap tier is `sonnet`. Pass `effort: high` with it.
4. **Reviewer below Opus:** every review agent (code-reviewer, feature-reviewer, ui-reviewer, qa-tester, pr-test-analyzer, silent-failure-hunter; the security review is a code-reviewer) needs `opus` (or `fable`), on every track and risk. Name `opus` in the dispatch.
5. Forks are never checked: they always run on the session model. To keep Fable out of forks, don't run the session on Fable.

## R19. A trust-anchor notice stops the turn

The state, the change file, baseline and config the hooks trust are writable by the agent they check, so `hooks/trust_anchor.py` can't prevent a change; at Stop it shows you one. A notice reads "Verification anchors changed: …" and names what moved: `Track:`, `Risk:`, `Top model:`, `Base:` or `Process:`; a failing test added to `.sdlc/baseline.md` or changed commands in `.sdlc/config.json` since `Base:`; the change file above `## Review` (its criteria and tests) edited during Review; leaving Review without a passing full run of the current code (at every size), or with code changed since it; leaving Review while a review's latest report says `VERDICT: FAIL` and no `waived round <N>` deviation covers it; an active feature no longer active other than by `Status: done`; "verify records disagree" (`.sdlc/.work/verify.json` differs from the freshness hook's copy of the run, or is missing or damaged while the hook holds one: rerun `verify.py` and say why the record changed); or its own record (`.sdlc/.work/trust-anchor.json`) damaged.

1. **Stricter changes** (Track up, Risk low → high) only add checks: "Stricter process: …", no block. Only current features (`Process: 3`) are anchored.
2. **Every other change** blocks the stop once. Claude must tell you what changed and why, without undoing it on its own. Your next message accepts it: the current values become the anchor, and the notice doesn't block again. Autopilot stops at a notice you haven't seen.
3. If the change was wrong, say so in that message and have it reverted (`state.py set`, or restore the file from git); moving a value back is itself a notice.
