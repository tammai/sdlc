# sdlc runbook

Operational procedures: install, check health, fix what breaks, maintain the plugin. Concepts are in the [guidebook](guidebook.md); day-to-day usage is in the [playbook](playbook.md).

## Reference

### Prerequisites

| Need | For |
|---|---|
| `git` | worktrees, freshness hook, commit and PR commands |
| `gh` | `/sdlc:code-review` and PR commands |
| Python 3.9+ | all hooks (started through `hooks/sg-python.sh`, which finds `python3`, `python` or `py -3`) and `scripts/` (stdlib only; macOS system 3.9 works) |
| `jq` | the Ralph loop's stop hook (the optional `sdlc-extras` plugin) |
| Node | brainstorming visual companion |
| `typescript-language-server`, `typescript` | TypeScript code intelligence (`npm i -g typescript-language-server typescript`) |

### Where state lives

| What | Path |
|---|---|
| Project config (overrides on plugin defaults) | `.sdlc/config.json` |
| What the plugin placed, scaffold version, migrations | `.sdlc/scaffold.lock.json` (never edit by hand) |
| Known failures from before setup | `.sdlc/baseline.md` |
| Feature state (committed; written by `scripts/state.py`) | `.sdlc/state/<feature>.md` |
| Control contract, derived from the state file (git-ignored) | `.sdlc/state/<feature>.json`, `<feature>.events.jsonl`, `<feature>.commands/` |
| Feature change file, the record for people (committed) | `docs/sdlc/changes/<feature>.md`; 1.x features keep their documents in `docs/sdlc/intents/<feature>/` (`intent.md`, `spec.md`, `plan.md`, `review.md` and others); `docs/sdlc` is `docs_dir` in the config |
| Feature working files (committed) | `.sdlc/state/<feature>/`: `backlog.md` and `plan-B<n>.md` for work split into parts, `qa-report.md` from a QA round, `release.md` from `/sdlc:deploy`, committed only if you ask |
| Old layout, before 1.7.0 | `.sdlc/<feature>/state.md` and documents beside it; `/sdlc:upgrade` moves them |
| Scratch (git-ignored) | `.sdlc/.work/`: `verify.json` (written by `scripts/verify.py`), `verify-freshness.json` (the freshness hook's copy of verify runs, written by the hook and by `verify.py` itself), `trust-anchor.json`, `dispatches.jsonl`, `findings/<feature>/` (each review's report, ending in its `VERDICT:` line) |
| Ralph loop state (`sdlc-extras`) | `.claude/ralph-loop.local.md` |
| Personal hookify rules | `.claude/hookify.<name>.local.md` (git-ignored) |
| Team hookify rules | `.claude/hookify/<name>.md` (committed) |
| Security hook per-session state, reviewer venv | `$SECURITY_WARNINGS_STATE_DIR`, else `$CLAUDE_CONFIG_DIR/security/`, else `~/.claude/security/` (venv: `agent-sdk-venv` inside it) |

### Environment switches for the security hooks

Set in the shell or in `settings.json` `env`.

| Variable | Default | Effect |
|---|---|---|
| `SECURITY_GUIDANCE_DISABLE=1` (or `ENABLE_SECURITY_REMINDER=0`) | off | Disable the whole security hook |
| `ENABLE_PATTERN_RULES=0` | on | Turn off regex warnings on edits |
| `ENABLE_CODE_SECURITY_REVIEW=0` | on | Turn off the turn-end diff review and the commit/push review |
| `ENABLE_COMMIT_REVIEW=0` | on | Turn off the commit review |
| `ENABLE_STOP_REVIEW=0` | on | Turn off the turn-end review |
| `SDLC_SECURITY_REVIEW=always` | off | Run the turn-end and commit reviews on every change, not only while a security-touched feature is active (ADR 0019); also installs the reviewer's environment at session start |
| `MAX_STOP_HOOK_FIRINGS` | 3 | Cap on repeated turn-end review firings |
| `MAX_DIFF_FILES` | 30 | Largest diff the reviewer will look at |

## Install

Install from the marketplace that hosts the plugin:

```
/plugin marketplace add tammai/sdlc
/plugin install sdlc@sdlc
```

Then restart the session so the plugin's commands and hooks load. `/plugin` lists installed plugins and whether sdlc is enabled. To get a new version, update the marketplace and the plugin from `/plugin`, restart, then run `/sdlc:upgrade` in each repo. Other agents (Codex, Cursor, Antigravity): see the README.

Working on the plugin itself instead? See [Develop locally](#develop-locally).

Check it in a scratch repo:

1. `/sdlc:doctor`: no ❌. Expected warnings: the repo isn't set up yet, and (before the first session finishes) the reviewer environment.
2. `/sdlc:setup` with a one-line description: it proposes a stack, and after your OK writes `.sdlc/config.json` and the rest on a `sdlc/setup` branch. `/sdlc:doctor` again: the repo checks are ✅.
3. `/sdlc:start` with a tiny request creates `.sdlc/state/<feature>.md` and announces the track, risk and top model tier.

## Health check

Run `/sdlc:doctor` when something feels off, after installing or upgrading, or before onboarding a teammate. It changes nothing; it prints one row per check with ✅ / ⚠️ / ❌ and, for anything not ok, the fix and the procedure below that covers it. The same report from a shell: `python3 <plugin>/scripts/doctor.py --format md` (exit 1 if anything fails).

| Group | What it checks |
|---|---|
| environment | Python ≥ 3.9, a Python 3 the hooks' launcher (`hooks/sg-python.sh`) finds, git, gh, jq, the security reviewer's environment (built in the state directory on first session) |
| plugin | version; every script `hooks.json` references exists |
| repo | setup state and version drift; config and lock parse; plugin files missing or hand-edited; project commands defined (per package), their tools on PATH, and whether they have run; the `AGENTS.md` block; baseline present (brownfield); old layout; `.sdlc/.work/` and the contract files git-ignored; design system present when the repo has UI files; impeccable installed when the design mode is impeccable; rules whose `paths:` match no files; hookify rules that don't parse or have a bad regex; CLAUDE.md over 60 lines; broken links in `knowledge/index.md`; state files missing `Status:`/`Current:`, or several active; corrupt freshness state, or a freshness hook run that failed |

Not covered by doctor: whether the plugin is enabled (`/plugin`), and the plugin's own test suite (`py -3.10 -m unittest discover -s tests -t tests` in the plugin repo; macOS/Linux: `python3.10`).

## Procedures

State changes go through `scripts/state.py` (`python3 <plugin>/scripts/state.py <command> <feature> …`); it updates the state file and the control contract together. Below, `state.py` means that call.

### R1. Plugin won't load or components are missing

1. Open `/plugin` and confirm `sdlc` is installed and enabled. If not, install it (see [Install](#install)).
2. Slash commands use the `sdlc:` prefix. If `/sdlc:start` isn't found, restart the session after installing or updating.
3. Still missing after a restart: update the marketplace and reinstall the plugin from `/plugin`.
4. Maintainers: run `claude plugin validate .` in the plugin repo and read the first error; check `.claude-plugin/plugin.json` and `hooks/hooks.json` are valid JSON.

### R2. First session is slow or the security reviewer is unavailable

Cause: the SessionStart hook builds a venv with the Claude Agent SDK in the background, and only when the security hooks receive credentials (a Claude Code sign-in, or `ANTHROPIC_API_KEY`). Without credentials the model reviews are skipped and the venv is never built; pattern warnings still work. A session closed before the build finishes cancels it.

1. Keep a signed-in session open for the first start to finish (timeout is 180 s).
2. If it failed, check network access to the Python package index, then start a new session to retry.
3. To rebuild from scratch: remove `agent-sdk-venv` from the security state directory (see Where state lives; `/sdlc:doctor` prints it) and start a new session.
4. The venv lives outside the plugin, so it survives plugin updates.

### R3. Security hook is too noisy or too slow

1. Identify which part is firing: edit pattern warnings, turn-end review, or commit/push review. The turn-end and commit reviews run only while a security-touched feature is active (ADR 0019). While a feature is active, the commit review runs once per review-ready diff (from Review on), not on every build commit, and only on a security-touched change (`Risk: high`, or a diff touching `areas.sensitive` or `areas.migrations`); any other is recorded as reviewed with no model call. If a sensitive path gets no review, add it to `areas.sensitive` in `.sdlc/config.json`.
2. Turn off only that part with the matching variable from the table above.
3. Prefer fixing the finding. If it's a false positive you'll see again, tell the reviewer why in the response (acknowledged findings are fine) rather than disabling the hook.
4. `SECURITY_GUIDANCE_DISABLE=1` is a last resort; record it with `state.py deviation`.

### R4. Blocked at Stop with "re-run tests"

The verify-freshness hook is active only while an active 2.0 feature (`Process: 2`) says `Current: Stage 5 – Review`, at every size.

1. Run the **full** test command: `commands.test` from `.sdlc/config.json` (monorepo: the stale package's own, from its `path`; the block message names it), or the `test:` command in the state file's `Commands:` line. A filtered run, single test file, pytest node id or single Go package doesn't count.
2. Make sure no code changed after that run. Formatters, `sed -i` and subagents count as changes; the hook compares the worktree against the tree recorded at the last full run.
3. Edits to `.md`, `.mdx`, `.txt`, `.rst` and anything under `.sdlc/`, `knowledge/`, `.claude/`, `docs/` don't mark results stale.
4. If the recorded test command is wrong, fix `commands.test` (or the package's) in `.sdlc/config.json`, or the `Commands:` line for a repo without setup. A changed config command raises a trust-anchor notice ([R19](#r19-a-trust-anchor-notice-stops-the-turn)).
5. If the freshness state itself is wrong, delete `.sdlc/.work/verify-freshness.json`; the next full run recreates it.
6. The hook never fails the session on its own error: it writes `.sdlc/.work/verify-freshness.error`, which doctor reports and the next clean run removes. If it blocks wrongly, run the hook tests (below) and open an issue with the transcript and that file.

### R5. `verify.py` gives different answers each time

1. Don't retry until green. A test that passes after failing is flaky, and a retried-until-green test doesn't pass the gate.
2. Run the failing test a few times in isolation (at most 5 repeats; its row's command in the change file's `## Acceptance tests` runs just that test) and record the results in the change file's `## Review`.
3. Fix or quarantine the flaky test with your approval, and record it with `state.py deviation`.

### R6. Ralph loop won't stop

The Ralph loop comes with the optional `sdlc-extras` plugin.

1. `/sdlc-extras:cancel-ralph`. It reports the iteration it stopped at.
2. If the command fails, delete `.claude/ralph-loop.local.md` by hand; the stop hook then lets the session end.
3. Always start loops with `--max-iterations`.
4. A malformed state file (missing frontmatter field) no longer crashes the hook; delete it if it keeps looping.

### R7. A hookify rule doesn't fire, or fires too much

1. Is the file in the right place? `.claude/hookify.<name>.local.md` (personal) or `.claude/hookify/<name>.md` (team).
2. Frontmatter: `enabled: true`, a valid `event` (`bash`, `file`, `stop`, `prompt`, `all`), `action` (`warn` or `block`).
3. Parser limits: never put `---` inside a pattern (write `-{3}`), keep each `pattern:` on its own line, don't quote patterns. Matching is case-insensitive.
4. Fields: bash rules use `command`; file rules use `file_path`, `new_text` (falls back to `content` on Write), `old_text` or `content`; prompt rules use `user_prompt`. Operators: `regex_match`, `not_regex_match`, `contains`, `not_contains`, `equals`, `starts_with`, `ends_with`.
5. All conditions in a rule must match for it to trigger. Warnings reach Claude as context; block reasons appear as the permission-denied reason.
6. With `sdlc-extras` installed, `/sdlc-extras:hookify-list` to see what's active and `/sdlc-extras:hookify-configure` to toggle; otherwise read and edit `enabled:` in the rule files.
7. Over-firing: narrow the pattern or add a condition; switch `block` to `warn`.

### R8. `/sdlc:start` picks the wrong feature, or says there are several

1. `/sdlc:status` shows every feature, its phase and status.
2. A finished feature: `state.py set <feature> Status done`. One you're not working on now: `state.py set <feature> Status paused`. Pausing raises a trust-anchor notice once ([R19](#r19-a-trust-anchor-notice-stops-the-turn)).
3. Answer the "which one" prompt if it still asks.
4. It says a feature was started under sdlc 1.x: see [R20](#r20-upgrade-to-20-with-a-1x-feature-in-progress).

### R9. A state file is missing, stale or wrong

The state file is `.sdlc/state/<feature>.md`; beside it, git-ignored, `state.py` writes the control contract (`<feature>.json`, `<feature>.events.jsonl`), derived from it.

1. A wrong field: `state.py set <feature> <Field> <value>` (Status, Track, Risk, Top model, Base, Owner, Tool, Slice gates, Process). Changing Track, Risk, Top model, Base or Process raises a trust-anchor notice ([R19](#r19-a-trust-anchor-notice-stops-the-turn)).
2. A wrong phase: `state.py advance <feature> <n>` without `--gate`, where `<n>` is 1 Define, 4 Build, 5 Review or 8 Ship (a backlog feature stays at 4 between parts).
3. A hand edit, or a missing or damaged `.json`: `state.py sync <feature>` rewrites the contract from the state file. `state.py` refuses a state file without `Status:` and `Current: Stage <n> – <name>`, and one without `Process: 2` (a 1.x feature: [R20](#r20-upgrade-to-20-with-a-1x-feature-in-progress)).
4. A lost state file: it held half the record (the plan sections: how the build runs, handoff, tasks, Public Surface, deviations); git history usually has it. Otherwise write a new one from the template in `skills/orchestrator/references/flow.md` (S: `s-track.md`), rewrite its plan sections from the change file and the diff (or `verify.py`'s drift check fails), tick the phases the change file shows done (`## Acceptance tests` filled: Define; `## Review` written: Review), set `Current:` to the next phase's stage, then `state.py sync <feature>` and `state.py deviation <feature> "state file reconstructed"`.

### R10. Hooks error on Windows or with an odd Python

`hooks/sg-python.sh` probes `python3`, `python` and `py -3`, skipping the Microsoft Store stub, and forces UTF-8. It remembers the interpreter it chose, and where that name resolved, in `sdlc-hook-python` in the plugin's data folder (else `~/.cache/sdlc/`, never a shared temp folder; a file the user doesn't own is ignored), so later hooks skip the probes; it probes again when that name resolves elsewhere or is gone. Under Claude Code it also writes `sdlc-hook-python.fast` there, the interpreter's path, which each hook's command in `hooks.json` starts directly without the launcher; while that path exists, a PATH change doesn't reach it. Delete both files to force a fresh probe. If the security hook still fails, run `bash hooks/sg-python.sh -c "import sys; print(sys.version)"` to see which interpreter it chose. Every hook in `hooks/hooks.json` starts through it, so one working Python 3 serves them all. Doctor's "hook python" row runs the launcher; when it fails, install Python 3 from python.org (not the Microsoft Store) and, on Windows, Git Bash. The Ralph loop's hook (`sdlc-extras`) runs under bash.

### R10a. Hooks feel slow

Set `SDLC_HOOK_TIMES=1` in the session's environment (for one project: `"env": {"SDLC_HOOK_TIMES": "1"}` in `.claude/settings.local.json`) and restart the session. Each hook then appends `{"t", "hook", "event", "tool", "ms", "rc"}` to the project's `.sdlc/.work/hook-times.jsonl` (only where `.sdlc/` exists): the script name, the hook event and tool, its wall-clock time including the launcher, and its exit code. The security review after a commit, push or Stop runs in the background (`asyncRewake`), so its time doesn't hold up a tool call. It sends every hook through the launcher (no direct start) plus one more bash, so the times include that; turn it off after measuring. Total time per hook and event: `python3 -c "import json,collections; c=collections.Counter(); [c.update({(e['hook'], e['event']): e['ms']}) for e in map(json.loads, open('.sdlc/.work/hook-times.jsonl'))]; print(c.most_common())"`.

### R11. A gate is blocking and you disagree

A gate is a phase's exit check; it is a decision, not a fault. Say `skip` or `just ship it`: the orchestrator names the skipped gates, records them with `state.py deviation`, and continues. See [playbook 9](playbook.md#9-skip-a-gate-deliberately).

Hard stops are different: they always wait for your answer and aren't skipped. They are the approval before the build and the review choice after it on high-risk M (on L only when the agent's own checks leave a doubt), anything that adds scope, a reviewer and the builder disagreeing on a high finding, CI still red after one fix, merge, production deploy, DB migrations, and anything irreversible.

### R12. Setup stopped halfway

1. Run `/sdlc:setup` again. It reads `completed_steps` from the lock and continues with the next step on the same `sdlc/setup` branch.
2. Config or lock won't parse: fix the JSON, or restore it from git, then rerun.
3. Want a clean restart instead: delete the branch, then `python3 <plugin>/scripts/scaffold.py init --kind <greenfield|brownfield> --force` and rerun setup.
4. "Working tree not clean": commit or stash first; setup won't mix its commits with your changes.

### R13. A project command is missing, wrong, or its tool isn't installed

1. `/sdlc:doctor` (repo · commands, command tools, commands run) or `python3 <plugin>/scripts/scaffold.py contract` shows, per package, which required commands are missing and which tools aren't on PATH.
2. Commands live in `.sdlc/config.json`: `commands` for one project, `packages[].commands` per package. Use what the team already runs; set a step to `null` if it doesn't apply to that stack.
3. A tool not found: install it the way the project expects (the lockfile and toolchain files say which version), or fix the command.
4. Then `scaffold.py run-commands` runs them once and records the result, and `/sdlc:upgrade` makes the generated CI workflow follow (or review its diff if you edited the workflow). During a feature, changed commands raise a trust-anchor notice ([R19](#r19-a-trust-anchor-notice-stops-the-turn)).

### R14. An upgrade won't overwrite a file, or keeps asking about it

1. That file is seeded and you edited it, so the upgrade refuses to overwrite it (`scaffold.py render --if-unchanged` exits 2). This is on purpose.
2. Pick **apply** to take the proposed merge, **skip** to be asked next time, or **keep mine**: `scaffold.py forget <path>` makes it yours for good and upgrades stop asking.
3. A deleted plugin file is offered for restore once; declining forgets it.

### R15. A migration was declined and you want it after all

`/sdlc:upgrade --revisit` lists skipped migrations with the reason you gave and offers each again. `scaffold.py migrations --revisit` shows the same list without changing anything.

### R16. `verify.py` blames the feature for an old failure, or the baseline looks wrong

1. Check `.sdlc/baseline.md`: failing tests by file › name, lint/type errors as counts per rule and file. A count that went **up** counts as new.
2. No baseline in a brownfield repo: rerun `/sdlc:setup`'s baseline step.
3. A pre-existing failure missing from the baseline: adding it is your decision. Add it with a note and record it with `state.py deviation` naming the test; nothing adds items on its own. A baseline that gains a failure during a feature raises a trust-anchor notice ([R19](#r19-a-trust-anchor-notice-stops-the-turn)).
4. `verify.py` doesn't read the baseline: a baselined failure fails it. When only the test step fails and every failure is listed there, Build logs it with `state.py log` and passes the gate; nothing checks that mechanically yet ([spec 04 Known gaps](specs/04-verification.md#known-gaps)).

### R17. Eject left something behind or broke the build

1. `scaffold.py eject` (dry run) shows what it would still remove; edited plugin files are only deleted when you say so.
2. Imports into deleted files (`eslint.sdlc.mjs` in `eslint.config.*`, `extend = ".sdlc/lint/ruff.sdlc.toml"` in `pyproject.toml`) should have been offered as diffs. If not, remove them by hand and rerun the verify commands.

### R18. A subagent dispatch is denied by the model router

The hook checks Agent/Task dispatches only while a 2.0 feature (`Process: 2`) has `Status: active`; the deny reason says which check failed. Every dispatch, denied or not, is logged to `.sdlc/.work/dispatches.jsonl`.

1. **No model:** the dispatch must name `sonnet` or `opus` (Model selection in `sdlc:orchestrator`). Commands that launch agents, such as `/sdlc:review-pr`, name one too. Exempt: forks, and impeccable's own agents (`impeccable-*`), which impeccable spawns without a model.
2. **Fable:** used only on your request. `state.py set <feature> "Top model" fable` on every active feature (one active feature without it keeps Fable denied). This raises a trust-anchor notice ([R19](#r19-a-trust-anchor-notice-stops-the-turn)).
3. **Haiku:** denied everywhere; the cheap tier is `sonnet`. Pass `effort: high` with it.
4. **Reviewer below Opus:** every review agent (code-reviewer, feature-reviewer, ui-reviewer, qa-tester, pr-test-analyzer, silent-failure-hunter; the security review is a code-reviewer) needs `opus` (or `fable`), on every track and risk. Name `opus` in the dispatch.
5. Forks are never checked: they always run on the session model. To keep Fable out of forks, don't run the session on Fable.

### R19. A trust-anchor notice stops the turn

The state, the change file, baseline and config the hooks trust are writable by the agent they check, so `hooks/trust_anchor.py` can't prevent a change; at Stop it shows you one. A notice reads "Verification anchors changed: …" and names what moved: `Track:`, `Risk:`, `Top model:`, `Base:` or `Process:`; a failing test added to `.sdlc/baseline.md` or changed commands in `.sdlc/config.json` since `Base:`; the change file above `## Review` (its criteria and tests) edited during Review; leaving Review without a passing full run of the current code (at every size), or with code changed since it; leaving Review while a review's latest report says `VERDICT: FAIL` and no `waived round <N>` deviation covers it; an active feature no longer active other than by `Status: done`; "verify records disagree" (`.sdlc/.work/verify.json` differs from the freshness hook's copy of the run, or is missing or damaged while the hook holds one: rerun `verify.py` and say why the record changed); or its own record (`.sdlc/.work/trust-anchor.json`) damaged.

1. **Stricter changes** (Track up, Risk low → high) only add checks: "Stricter process: …", no block. Only 2.0 features (`Process: 2`) are anchored.
2. **Every other change** blocks the stop once. Claude must tell you what changed and why, without undoing it on its own. Your next message accepts it: the current values become the anchor, and the notice doesn't block again. Autopilot stops at a notice you haven't seen.
3. If the change was wrong, say so in that message and have it reverted (`state.py set`, or restore the file from git); moving a value back is itself a notice.

### R20. Upgrade to 2.0 with a 1.x feature in progress

sdlc 2.0 carries no copy of the 1.x flow ([ADR 0020](adr/0020-sdlc-2-slim-process-core.md)). A feature whose state file has no `Process: 2` was started under 1.x: `/sdlc:start` won't run it, `state.py` refuses to change it, the hooks ignore it, and `/sdlc:upgrade` names it and stops (`scaffold.py set-version` refuses while one is active).

1. `/sdlc:status` lists the active features; the ones without `Process: 2` are 1.x.
2. For each: install sdlc 1.8.1 (`/plugin install sdlc@sdlc` at 1.8.1), restart, and finish it there. Or, if you'll drop or redo it, archive it: set `Status: done` in its state file.
3. Install 2.0 again, restart, and run `/sdlc:upgrade`.

Best done before installing 2.0: the plugin is installed per machine, so finish in-progress 1.x features first.

## Maintenance

### Run the tests

```bash
py -3.10 -m unittest discover -s tests -t tests   # once, on Python 3.10 only (macOS/Linux: python3.10)
```

Stdlib only; they must pass on Python 3.9. Each test runs a hook or script as a subprocess against a throwaway project. Run after any hook change and after updating vendored code. `claude plugin test` doesn't apply: it only runs TypeScript hook modules.

### Update vendored code

Sources and licenses are in `NOTICE.md`.

1. Re-copy the listed upstream files.
2. Re-apply the documented renames (`superpowers:` → `sdlc:`, paths → `.sdlc/`) and the patches listed under "Modified" in `NOTICE.md`.
3. Run the tests. The hookify and ralph tests exist to catch exactly those regressions.
4. Update `NOTICE.md` if you added or removed vendored files or patches.

Claude Security is not bundled (its license reserves all rights); install it separately.

### Develop locally

For changes to the plugin itself, run it from a checkout instead of the marketplace copy: `claude plugin validate .` checks the manifest and components parse, `claude --plugin-dir .` loads it for one session. The dev loop and layout are in [CONTRIBUTING](../CONTRIBUTING.md).

### Release a new version

1. Run the tests and `claude plugin validate .`, and check that CI (`.github/workflows/ci.yml`) is green on the last pushed commit.
2. Bump `version` in `.claude-plugin/plugin.json` and, to the same number, in `plugins/sdlc-extras/.claude-plugin/plugin.json`, then run `python3 scripts/hosts.py build` so the Codex, Cursor and Antigravity manifests carry it too (CI's `hosts.py check` fails while they differ). Repos record this number at setup and upgrade, so every release that changes project files needs a new one.
3. Move the `Unreleased` notes in `CHANGELOG.md` under `## <version> — <date>`, and update the README if commands, phases, configuration or requirements changed.
4. If the release changes files that live in projects:
   - templates of generated or seeded files: nothing to do, `/sdlc:upgrade` regenerates or replaces them;
   - anything a project owns (required commands, config keys, knowledge layout, renamed paths, ignore patterns): add `migrations/<version>-<slug>.md` with frontmatter `version`, `summary` and, if old plugins must stop, `min_plugin_version`, then the steps in prose.
5. **Distill knowledge** with `sdlc:managing-knowledge` (`CLAUDE.md` ≤ 60 lines, `.claude/rules/<area>.md` with `paths:`, `knowledge/` linked from `knowledge/index.md` and logged in `knowledge/log.md`). Sources: the changelog notes, `git log <last tag>..HEAD` (fix commits especially), smoke-test and review findings, and corrections made more than once. Run its "File a lesson" steps for each durable lesson, then its Audit. Decisions about how the plugin works go to `docs/adr/`, procedures to this runbook, and anything corrected twice and checkable becomes a test or guardrail. `python3 scripts/doctor.py` checks the CLAUDE.md budget and the index links.
6. **Stale-docs round over the whole release:** run the [stale-docs audit](../CONTRIBUTING.md#stale-docs-audit) once more, now for everything since the last tag, not one change. List the names the release added, renamed or removed (`git diff --stat sdlc--v<last>..HEAD`, `git log sdlc--v<last>..HEAD --oneline`, the changelog section), then grep each, and the wording it replaces, across `README.md`, `CONTRIBUTING.md`, `knowledge/`, `.claude/rules/`, `docs/` (guidebook, playbook, runbook, prd, specs, ADRs), the plugin and marketplace descriptions (`.claude-plugin/*.json`, then `python3 scripts/hosts.py build`), and every diagram in `docs/diagrams/*.svg`: its `<desc>` **and** its visible labels (render it, [rendering SVG diagrams](../knowledge/gotchas/rendering-svg-diagrams.md)). Fix what's stale; a diagram that needs relayout rather than a text edit goes in the changelog's notes as a known gap. Commit as `docs: stale-docs round for <version>`.
7. Commit (`release: sdlc <version>`), then run the [smoke test](#smoke-test-before-a-release) against that commit. Every **must** item has to pass.
8. `claude plugin tag . --dry-run`, then `claude plugin tag . --push` (creates and pushes `sdlc--v<version>`). Push the branch too.
9. Publish the GitHub release; the tag alone doesn't make one. As the `tammai` account (`gh auth switch -u tammai`), with the version's changelog section as the notes:
   ```bash
   v=<version>; awk -v v="$v" '/^## /{p=($2==v);next} p' CHANGELOG.md > notes.md
   gh release create "sdlc--v$v" --verify-tag --title "sdlc $v" --notes-file notes.md --latest; rm notes.md
   ```
   Users get the new version by updating the marketplace and the plugin from `/plugin`, then run `/sdlc:upgrade` in each repo.

### Smoke test before a release

The test suite runs hooks and scripts as subprocesses; this checks the installed plugin in real sessions, which the suite can't. About 45 minutes. Use throwaway repos outside any real project, a **fresh session** for each part, and write down anything that doesn't match (what you did, what you saw, the session's transcript path). **Must** items block the release; **should** items become known issues in the changelog.

**A. Install from the checkout (must)**
1. In a new terminal: `claude`, then `/plugin marketplace add <path to this checkout>` and `/plugin install sdlc@sdlc`. Restart the session.
2. `/plugin` lists `sdlc` as enabled, version matching `plugin.json`. The first start may pause about a minute while the security reviewer's environment builds.

**B. Doctor in an empty repo (must)**
1. `mkdir /tmp/sdlc-smoke-green && cd $_ && git init`, start `claude`.
2. `/sdlc:doctor`: no ❌; the repo check says "not set up"; the security reviewer environment is ✅ (or ⚠️ only if no API credentials).

**C. Greenfield setup (must)**
1. `/sdlc:setup a tiny TypeScript library that adds two numbers`. It asks a few stack questions and **waits for your approval** before generating anything.
2. It works on a `sdlc/setup` branch with one commit per step; `.sdlc/config.json` has the five commands; it runs them and they pass.
3. The repo has `.claude/rules/sdlc*.md`, `.claude/hookify/sdlc-*.md`, `.github/workflows/sdlc-verify.yml` and `sdlc-invariants.yml`, `.sdlc/ci/invariants.py`, `docs/sdlc/prd.md` (written after you approve the interview's draft), `docs/sdlc/constitution.md`, `knowledge/index.md`, `.sdlc/scaffold.lock.json`, and `.gitignore` lists `.sdlc/.work/` and the `.sdlc/state/*.json` contract patterns; `CLAUDE.md` untouched.
4. `enable-plugin` and context diet (should): run from the installed plugin, setup doesn't ask and writes the sdlc marketplace and `enabledPlugins` to `.claude/settings.local.json` only (`.claude/settings.json` gets no plugin keys), and names the companions it can add (`sdlc-extras`); run with `--plugin-dir`, sdlc itself isn't written and the setup report says it was skipped. After that it asks whether to trim plugins. Accept. It shows a table of plugins with estimated tokens per call, verdicts and reasons, and writes `.claude/settings.local.json` only after you approve; no commit includes that file, and it adds no `true`.
5. It asks PR or local merge; pick local merge. `/sdlc:doctor` now shows the repo checks ✅.
6. Interrupt test (should): in a second throwaway repo, stop setup midway (Esc), run `/sdlc:setup` again; it resumes after the last finished step.

**D. Guardrails reach Claude (must)**
1. Ask: "add a comment `// Step 1: add the numbers` above the add function". A hookify warning shows, **and Claude's reply acknowledges it** (proof the warning reaches Claude, not only you).
2. Ask: "run `git push --force origin main`". It's blocked, and Claude can say why.
3. Ask Claude to write `const k = "sk-ant-api03-…"` with 30+ characters after the prefix: blocked.

**E. An S fix: Define, Build, Review, Ship (must)**
1. `/sdlc:start fix: add returns a string when given numeric strings`. It proposes track S and creates `.sdlc/state/<yyyy-mm-dd>-s-<slug>.md` with `Process: 2`.
2. Define proves the bug with a failing test, names the root cause, writes the change file (the proving test as AC-001 in `## Acceptance tests`) and the state file's `## Tasks` and `## Public Surface`, a few lines each, and goes on to Build **without asking for approval**.
3. Build, in the session, records the test failing with `verify.py red AC-001` (in one call with `state.py sync` and `advance 4`), then the fix, then `verify.py`. `.sdlc/.work/verify.json` holds the red record and a passing run.
4. S has no Review phase: with no trigger firing (no `Risk: high`, no sensitive, migration or UI path, no Public Surface) it goes from Build straight to Ship, and the change file's `## Review` says no review ran and why. A trigger that fires runs its review **without stopping**; any review agent in `.sdlc/.work/dispatches.jsonl` has `model: opus`.
5. Freshness in Review: in that repo, `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/state.py" advance <feature> 5` on a feature still active (or start an M change whose Public Surface isn't `- none`, so a review fires), then ask Claude to change a source file **with a shell command** (e.g. `sed -i`) and end the turn: it's **blocked**, and the message names the test command. Run it; the turn then ends normally.
6. Ship runs the verified-tree check and Learn, makes the final commit on a feature branch and, with a remote, pushes and opens a PR, then stops; without a remote it stops with the branch ready. It never merges. Its security review is skipped (not security-touched): it is recorded as reviewed with no model call. `git status` never shows `.sdlc/state/*.json`.
7. Trust anchor (should): in a new S feature, ask Claude to run `state.py set <feature> Risk high`: a "Stricter process" message, no block. Then `Risk low`: the stop is blocked once, and your next message clears it.

**F. Security hooks (should)**
1. Ask Claude to add `eval(input)` to a file: a security warning appears in Claude's context.
2. At the end of that turn, a security review of the turn's changes runs (or, without credentials, you're told once that it's skipped).

**G. Brownfield setup (must)**
1. Copy a small real repo (or a sample with two packages in different languages) into `/tmp/sdlc-smoke-brown`, add one deliberately failing test, commit.
2. `/sdlc:setup`: it records the existing commands per package and **asks you to approve** them; it writes `.sdlc/baseline.md` listing the failing test; audit drafts are shown in batches and nothing is written before you approve.
3. `/sdlc:start` a small M change; at Build's gate the known failure is logged against the baseline, and a new failure would fail it.
4. Monorepo (should): edit a file in one package during Review; the block names only that package and its command.

**H. Upgrade and eject (must)**
1. In the greenfield repo, edit one guardrail file in `.claude/hookify/` and simulate an older scaffold: set `scaffold_version` in `.sdlc/scaffold.lock.json` to `1.2.9` (the only time to edit the lock by hand).
2. `/sdlc:status` reports the repo as behind and suggests `/sdlc:upgrade`.
3. `/sdlc:upgrade --dry-run` shows the plan and changes nothing (`git status` clean).
4. `/sdlc:upgrade` works on its own branch, asks about the guardrail you edited (apply / skip / keep mine), and ends asking PR or local merge.
5. 1.x feature (must, for 2.0): in a repo with an active feature whose state has no `Process: 2`, `/sdlc:upgrade` names it and stops; after `Status: done` it goes ahead ([R20](#r20-upgrade-to-20-with-a-1x-feature-in-progress)).
6. `/sdlc:eject` shows a dry run first; applied on a branch, it removes the plugin's files, keeps `.sdlc/config.json`, the PRD, the constitution, knowledge and specs.

**I. Windows (should, if the team uses it).** A teammate runs B–E on Windows in Git Bash.

**J. Other agents (should, one per agent the release claims; must once each before calling an agent supported)**
1. Install from the checkout: Codex `codex plugin marketplace add <checkout>` and `codex plugin add sdlc@sdlc` (note which manifest it used, whether `start` appears as a skill, and whether the Claude-format hooks run; on Windows, whether the skills' bash commands work from its PowerShell); Cursor, a copy in `~/.cursor/plugins/local`; Antigravity, `python3 scripts/hosts.py dist antigravity <folder>` then `agy plugin install <folder>`. The agent lists the sdlc skills, including `start`, `setup` and `upgrade` (Codex: `sdlc:start`, and no `sdlc:source-command-*` duplicates), and Antigravity's `agy agents` lists the 6 core agents.
2. In a new repo, ask the agent to set up sdlc. It doesn't ask which agent it is, finds `scaffold.py` through the plugin folder note, and records only that host (`.sdlc/scaffold.lock.json` → `hosts`). `AGENTS.md` has the sdlc block. Under `.claude/` there are at most the knowledge step's area rules (`.claude/rules/<area>.md`, which the block copies), and no `sdlc*` rules, hookify or settings. Codex asks to approve each commit unless you give it full access; that's its sandbox, not a failure.
3. Open the same repo in Claude Code and run `/sdlc:setup`: it joins (`hosts` gains `claude-code`), writes the Claude Code rules and guardrails, doesn't redo the commands or baseline, and `/sdlc:doctor` has no fails.
4. Antigravity only: its agent list shows the sdlc agents, or the load error, which goes in the notes.

When every must item passes, record the date and commit in the changelog entry's notes and continue with step 8 above.

### Add or change a phase rule

Phase behavior lives in `skills/orchestrator/`: the router `SKILL.md` (start or resume, the tracks, risk, and which one file each track reads) and `references/`: `s-track.md` (all of S), `flow.md` (all of M and L: the turn plan, model tiers, state, context and shared rules, hard stops, the state template, then Define, Build, Review and Ship), plus `review-brief.md`, `backlog-slices.md` for work split into parts and `ui-work.md` for UI work. A rule S and M both need goes in both `s-track.md` and `flow.md`, or in the router if every track needs it. The hooks and `state.py` key on the stage numbers (1 Define, 4 Build, 5 Review, 8 Ship) and act only on features with `Process: 2`, not on the names. After editing, keep these in step:

| If you change… | Also check |
|---|---|
| Phase gates or tracks | `docs/diagrams/*.svg`, `docs/guidebook.md`, README phase table, `docs/specs/02-orchestration.md` |
| A hard stop | the Shared rules in the orchestrator's `SKILL.md`, `docs/playbook.md`, R11 above |
| The record (the change file and the state file's plan sections) | `templates/change-template.md`, the state templates in `references/flow.md` and `s-track.md`, `flow.md`'s Define and Review, `scripts/verify.py` (reads the change file's `## Acceptance tests` and the state file's tasks, Public Surface and deviations), `hooks/trust_anchor.py` (what's above `## Review`), `scripts/prune.py` and `tests/test_prune.py` (what it keeps), `templates/project/ci/invariants.py` and `tests/test_invariants.py`, `docs/specs/04-verification.md`, `08-health-and-status.md` |
| The review recommendation or brief (`flow.md`'s Review, `s-track.md` step 5, `review-brief.md`) | `agents/code-reviewer.md`, `agents/ui-reviewer.md`, `hooks/trust_anchor.py` (reads each report's `VERDICT:` line), `hooks/model_router.py` (reviews on opus), `docs/specs/03-scope-and-review.md`, `05-security.md` |
| Verify behavior | `scripts/verify.py`, `tests/test_verify.py`, `hooks/verify_freshness.py` (its own copy of verify runs), `hooks/prove_budget.py` (Review's 120 s kill), `tests/test_verify_freshness.py`, `hooks/trust_anchor.py` (what it watches) |
| State fields or stage numbers | `scripts/state.py`, `tests/test_state.py`, `docs/specs/12-control-contract.md`, the templates in `references/flow.md` and `s-track.md`, every hook that reads the field (`verify_freshness`, `trust_anchor`, `model_router`, `sdlc_review_gate`, `sdlc_layout`) |
| An agent's role or file access | the agent's `tools:` frontmatter, `hooks/role_guard.py`, `tests/test_role_guard.py`, `docs/specs/03-scope-and-review.md` and `04-verification.md` |
| Model tiers, track or risk | Model selection in `skills/orchestrator/SKILL.md`, `hooks/model_router.py`, `tests/test_model_router.py`, `hooks/trust_anchor.py` (it anchors `Risk:`), `docs/specs/02-orchestration.md` |
| Scope-tracing rules | `flow.md`'s Define, `templates/change-template.md`, the state template in `references/flow.md` and `plan-template.md` (Public Surface), `review-brief.md`, `scripts/diff_stats.py` |
| Setup, upgrade or eject | `skills/setting-up-projects/`, `scripts/scaffold.py`, `templates/project/`, `tests/test_scaffold.py`, `tests/test_project_templates.py`, `docs/diagrams/sdlc_setup_phase.svg`; a changed decision gets a new ADR in `docs/adr/` |

Then run the stale-docs audit in `CONTRIBUTING.md`.

### Setup, upgrade, eject internals

The skill makes the judgment calls; `scripts/scaffold.py` keeps the records (lock, file hashes and classes, keyed merges, migrations, drift). Why it works this way: [ADR 0001](adr/0001-project-setup-upgrade-eject.md) and [ADR 0002](adr/0002-record-the-repos-own-commands.md).

Every command prints one JSON object. Exit codes: 0 ok, 1 error, 2 refused because the user edited the file. Run as `python3 <plugin>/scripts/scaffold.py [--root DIR] <command>`.

| Command | Does |
|---|---|
| `init --kind greenfield\|brownfield [--docs-dir <d>] [--force]` | start setup: write the lock, plus a minimal `config.json` if none exists, and record `docs_dir` (default `docs/sdlc`; left unset while features from before setup are still in `.sdlc/`, reported as `legacy_features`) |
| `paths [<feature>]` | where this repo keeps a feature's state, change file and working files (`work`; a pre-2.0 feature's documents: `intents`), the constitution and the design system (`layout`: `new` or `legacy`) |
| `relocate [--docs-dir <d>] [--apply]` | move an old-layout repo: state to `.sdlc/state/`, a feature's `change.md` to `<d>/changes/<feature>.md` and its other documents to `<d>/intents/<feature>/`, with `git mv`; tracked files only; dry run unless `--apply`; clean tree only; all or nothing (any conflict moves nothing); records `docs_dir` |
| `status` | setup state, steps done, drift (`current` / `behind` / `ahead` / `plugin_too_old`), pending migrations, file states, `layout`, and `docs_site` (the file that shows `docs/` is published as a site) |
| `config` | effective config: plugin defaults merged with the project's overrides |
| `step-done <step> [--complete]` | record setup progress (resumable) |
| `contract` | check the commands per scope: required ones present, package paths exist, tools on PATH; reports the recorded runs |
| `commands` | scopes plus the install steps and verify plan, each with its directory |
| `run-commands [--timeout S]` | run install and the verify plan once, record each exit in the lock; exit 1 if a command couldn't start |
| `render <template\|builtin:…> <dest> [--class seeded] [--if-unchanged]` | render a plugin template (`{{config.x.y}}`, `{{plugin_version}}`) or a builtin (`ci`, `ci:<package>`, `contract-check`, `invariants`, `codeowners`), and record its hash |
| `preview <template\|builtin:…>` | render without writing |
| `record <generated\|seeded> <paths…> [--template T]` / `forget <paths…>` | track files Claude wrote / hand them over to the user |
| `allow --add/--remove … [--from-commands]`, `gitignore --add/--remove …`, `enable-plugin [--with <id>]` | keyed merges; only ever removes entries the plugin added (`enable-plugin`: the sdlc marketplace and `enabledPlugins` for sdlc and its companions, in `.claude/settings.local.json`, kept out of git with `.git/info/exclude` when nothing ignores it; returns `companions` with each one's reason and state, `turned_off` for a conflicting plugin it switched off for this repo (superpowers), `conflicts_in_repo` for a conflicting tool's files (spec-kit), and `skipped` for sdlc itself when the running plugin isn't Claude Code's installed copy) |
| `host` / `add-host <host>` | the coding agent running (from the plugin's install folder, else the environment), the hosts recorded in the lock, and whether this one is joining / record a joining agent |
| `agents [--check]` | rebuild the sdlc block in `AGENTS.md` for the recorded hosts (removed when Claude Code is the only one) and `.claude/rules/sdlc-agents-md.md`, Claude Code's copy of the team's own `AGENTS.md` text; `--check` exits 1 when either is out of date |
| `migrations [--revisit]`, `migration <id> --applied\|--skipped REASON` | pending migrations (scaffold < version ≤ plugin, numeric order) / record the outcome |
| `prd [<path>]` | where the product doc is and whether it exists; with a path, records it in config (`prd`) |
| `design [builtin\|impeccable]` | who does UI design work (config `design`, default builtin) and whether impeccable is installed; with a mode, records it |
| `guardrails` | the guardrails setup renders for the design mode (impeccable mode leaves out `sdlc-ui-hardcoded-values`) |
| `set-version <v> [--min-plugin m]` | advance `scaffold_version`; raises the pin, never lowers it |
| `upgrade-plan` | regenerate / replace / review / restore / template_gone, `agents` (off, in_sync or stale), plus pending migrations |
| `eject [--apply] [--also <edited files>]` | dry run by default; applying deletes plugin files, removes recorded entries and the lock |
