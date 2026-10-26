# sdlc runbook

Operational procedures: install, check health, fix what breaks, maintain the plugin. Concepts are in the [guidebook](guidebook.md); day-to-day usage is in the [playbook](playbook.md).

## Reference

### Prerequisites

| Need | For |
|---|---|
| `git` | worktrees, freshness hook, commit and PR commands |
| `gh` | `/sdlc:code-review` and PR commands |
| Python 3.9+, as `python3` | all hooks and `scripts/` (stdlib only; macOS system 3.9 works) |
| `jq` | the `/sdlc:ralph-loop` stop hook |
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
| Feature documents (committed) | `docs/sdlc/intents/<feature>/` (`intent.md`, `spec.md`, `plan.md`, `test-report.md`, `review.md`…); the folder is `docs_dir` in the config |
| Old layout, before 1.7.0 | `.sdlc/<feature>/state.md` and documents beside it; `/sdlc:upgrade` moves them |
| Scratch (git-ignored) | `.sdlc/.work/`: `verify-freshness.json`, `trust-anchor.json`, `dispatches.jsonl` |
| Ralph loop state | `.claude/ralph-loop.local.md` |
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

Check it in a scratch repo (the first session start may take about a minute while the security reviewer's environment builds):

1. `/sdlc:doctor`: no ❌. Expected warnings: the repo isn't set up yet, and (before the first session finishes) the reviewer environment.
2. `/sdlc:setup` with a one-line description: it proposes a stack, and after your OK writes `.sdlc/config.json` and the rest on a `sdlc/setup` branch. `/sdlc:doctor` again: the repo checks are ✅.
3. `/sdlc:start` with a tiny request creates `.sdlc/state/<feature>.md` and announces the track, risk, flow and `Build:`.

## Health check

Run `/sdlc:doctor` when something feels off, after installing or upgrading, or before onboarding a teammate. It changes nothing; it prints one row per check with ✅ / ⚠️ / ❌ and, for anything not ok, the fix and the procedure below that covers it. The same report from a shell: `python3 <plugin>/scripts/doctor.py --format md` (exit 1 if anything fails).

| Group | What it checks |
|---|---|
| environment | Python ≥ 3.9, a working `python3`, git, gh, jq, the security reviewer's environment (built in the state directory on first session) |
| plugin | version; every script `hooks.json` references exists |
| repo | setup state and version drift; config and lock parse; plugin files missing or hand-edited; project commands defined (per package), their tools on PATH, and whether they have run; the `AGENTS.md` block; baseline present (brownfield); old layout; `.sdlc/.work/` and the contract files git-ignored; design system present when the repo has UI files; rules whose `paths:` match no files; hookify rules that don't parse or have a bad regex; CLAUDE.md over 60 lines; broken links in `knowledge/index.md`; state files missing `Status:`/`Current:`, or several active; corrupt freshness state, or a freshness hook run that failed |

Not covered by doctor: whether the plugin is enabled (`/plugin`), and the plugin's own test suite (`python3 -m unittest discover -s tests -t tests` in the plugin repo).

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

1. Identify which part is firing: edit pattern warnings, turn-end review, or commit/push review. While a feature is active, the commit review runs once per review-ready diff (from Prove on), not on every build commit.
2. Turn off only that part with the matching variable from the table above.
3. Prefer fixing the finding. If it's a false positive you'll see again, tell the reviewer why in the response (acknowledged findings are fine) rather than disabling the hook.
4. `SECURITY_GUIDANCE_DISABLE=1` is a last resort; record it with `state.py deviation`.

### R4. Blocked at Stop with "re-run tests"

The verify-freshness hook is active only while an active feature's state says `Current: Stage 5 – Prove`, or, on `Flow: lite` (every backlog feature, and Lite features started before the four phases), Stage 5 or 6.

1. Run the **full** test command: `commands.test` from `.sdlc/config.json` (monorepo: the stale package's own, from its `path`; the block message names it), or the `test:` command in the state file's `Commands:` line. A filtered run, single test file, pytest node id or single Go package doesn't count.
2. Make sure no code changed after that run. Formatters, `sed -i` and subagents count as changes; the hook compares the worktree against the tree recorded at the last full run.
3. Edits to `.md`, `.mdx`, `.txt`, `.rst` and anything under `.sdlc/`, `knowledge/`, `.claude/`, `docs/` don't mark results stale.
4. If the recorded test command is wrong, fix `commands.test` (or the package's) in `.sdlc/config.json`, or the `Commands:` line for a repo without setup. A changed config command raises a trust-anchor notice ([R19](#r19-a-trust-anchor-notice-stops-the-turn)).
5. If the freshness state itself is wrong, delete `.sdlc/.work/verify-freshness.json`; the next full run recreates it.
6. The hook never fails the session on its own error: it writes `.sdlc/.work/verify-freshness.error`, which doctor reports and the next clean run removes. If it blocks wrongly, run the hook tests (below) and open an issue with the transcript and that file.

### R5. A verify round gives different answers each time

1. Don't retry until green. A test that passes after failing is flaky, and Prove's gate fails on a retried-until-green test.
2. Ask the next fresh verifier to run the failing test a few times in isolation (at most 5 repeats, within its time budget) and record the results in `test-report.md`.
3. Fix or quarantine the flaky test with your approval, and record it with `state.py deviation`.

### R6. Ralph loop won't stop

1. `/sdlc:cancel-ralph`. It reports the iteration it stopped at.
2. If the command fails, delete `.claude/ralph-loop.local.md` by hand; the stop hook then lets the session end.
3. Always start loops with `--max-iterations`.
4. A malformed state file (missing frontmatter field) no longer crashes the hook; delete it if it keeps looping.

### R7. A hookify rule doesn't fire, or fires too much

1. Is the file in the right place? `.claude/hookify.<name>.local.md` (personal) or `.claude/hookify/<name>.md` (team).
2. Frontmatter: `enabled: true`, a valid `event` (`bash`, `file`, `stop`, `prompt`, `all`), `action` (`warn` or `block`).
3. Parser limits: never put `---` inside a pattern (write `-{3}`), keep each `pattern:` on its own line, don't quote patterns. Matching is case-insensitive.
4. Fields: bash rules use `command`; file rules use `file_path`, `new_text` (falls back to `content` on Write), `old_text` or `content`; prompt rules use `user_prompt`. Operators: `regex_match`, `not_regex_match`, `contains`, `not_contains`, `equals`, `starts_with`, `ends_with`.
5. All conditions in a rule must match for it to trigger. Warnings reach Claude as context; block reasons appear as the permission-denied reason.
6. `/sdlc:hookify-list` to see what's active; `/sdlc:hookify-configure` to toggle.
7. Over-firing: narrow the pattern or add a condition; switch `block` to `warn`.

### R8. `/sdlc:start` picks the wrong feature, or says there are several

1. `/sdlc:status` shows every feature, its phase and status.
2. A finished feature: `state.py set <feature> Status done`. One you're not working on now: `state.py set <feature> Status paused`. Pausing raises a trust-anchor notice once ([R19](#r19-a-trust-anchor-notice-stops-the-turn)).
3. Answer the "which one" prompt if it still asks.

### R9. A state file is missing, stale or wrong

The state file is `.sdlc/state/<feature>.md`; beside it, git-ignored, `state.py` writes the control contract (`<feature>.json`, `<feature>.events.jsonl`), derived from it.

1. A wrong field: `state.py set <feature> <Field> <value>` (Status, Track, Risk, Flow, Build, Top model, Base, Owner, Tool, Slice gates). Changing Track, Risk, Flow, Top model or Base raises a trust-anchor notice ([R19](#r19-a-trust-anchor-notice-stops-the-turn)).
2. A wrong phase: `state.py advance <feature> <n>` without `--gate`, where `<n>` is 1 Define, 4 Build, 5 Prove or 8 Ship (a backlog feature also rests at 6 between slices).
3. A hand edit, or a missing or damaged `.json`: `state.py sync <feature>` rewrites the contract from the state file. `state.py` refuses a state file without `Status:` and `Current: Stage <n> – <name>`.
4. A lost state file: the documents (`intent.md`, `spec.md`, `plan.md`, `test-report.md`…) are the real record. Write a new one from the template in `skills/orchestrator/references/start.md`, tick the phases whose documents exist, set `Current:` to the next phase's stage, then `state.py sync <feature>` and `state.py deviation <feature> "state file reconstructed"`.

### R10. Hooks error on Windows or with an odd Python

`hooks/sg-python.sh` probes `python3`, `python` and `py -3`, skipping the Microsoft Store stub, and forces UTF-8. If the security hook still fails, run `bash hooks/sg-python.sh -c "import sys; print(sys.version)"` to see which interpreter it chose. The hookify, freshness, trust-anchor, role-guard and model-router hooks call `python3` directly, and the ralph hook runs under bash, so `python3` must work for them (doctor's `python3` row; on Windows, copy `python.exe` to `python3.exe`).

### R11. A gate is blocking and you disagree

A gate is a phase's exit check; it is a decision, not a fault. Say `skip` or `just ship it`: the orchestrator names the skipped gates, records them with `state.py deviation`, and continues. See [playbook 9](playbook.md#9-skip-a-gate-deliberately).

Hard stops are different: they always wait for your answer and aren't skipped. They are Define's approval (not on S), anything that adds scope, the round cap (verify round 3 failed), the same requirement failing in two rounds, merge, production deploy, DB migrations, and anything irreversible.

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

### R16. Prove blames the feature for an old failure, or the baseline looks wrong

1. Check `.sdlc/baseline.md`: failing tests by file › name, lint/type errors as counts per rule and file. A count that went **up** counts as new.
2. No baseline in a brownfield repo: rerun `/sdlc:setup`'s baseline step.
3. A pre-existing failure missing from the baseline: adding it is your decision. Add it with a note and record it with `state.py deviation` naming the test; the verifier never adds items. A baseline that gains a failure during a feature raises a trust-anchor notice ([R19](#r19-a-trust-anchor-notice-stops-the-turn)).
4. Items disappearing: the verifier removes items that now pass. That's expected; the test report lists them.

### R17. Eject left something behind or broke the build

1. `scaffold.py eject` (dry run) shows what it would still remove; edited plugin files are only deleted when you say so.
2. Imports into deleted files (`eslint.sdlc.mjs` in `eslint.config.*`, `extend = ".sdlc/lint/ruff.sdlc.toml"` in `pyproject.toml`) should have been offered as diffs. If not, remove them by hand and rerun the verify commands.

### R18. A subagent dispatch is denied by the model router

The hook checks Agent/Task dispatches only while a feature has `Status: active`; the deny reason says which check failed. Every dispatch, denied or not, is logged to `.sdlc/.work/dispatches.jsonl`, which Prove's gate reads to confirm a verifier ran in Stage 5.

1. **No model:** the dispatch must name `sonnet` or `opus` (Model Selection in `sdlc:subagent-driven-development`). Commands that launch agents, such as `/sdlc:review-pr`, name one too.
2. **Fable:** used only on your request. `state.py set <feature> "Top model" fable` on every active feature (one active feature without it keeps Fable denied). This raises a trust-anchor notice ([R19](#r19-a-trust-anchor-notice-stops-the-turn)).
3. **Haiku:** denied everywhere; the cheap tier is `sonnet`. Pass `effort: high` with it.
4. **Reviewer below Opus:** code-reviewer, feature-reviewer, ui-reviewer, verifier and qa-tester need `opus` (or `fable`) while any active feature says `Track: L`; on S and M they run on `sonnet` at either risk. If the track was misjudged, `state.py set <feature> Track M` (a notice too) and say why with `state.py log`.
5. Forks are never checked: they always run on the session model. To keep Fable out of forks, don't run the session on Fable.

### R19. A trust-anchor notice stops the turn

The state, spec, baseline and config the hooks trust are writable by the agent they check, so `hooks/trust_anchor.py` can't prevent a change; at Stop it shows you one. A notice reads "Verification anchors changed: …" and names what moved: `Track:`, `Risk:`, `Flow:`, `Top model:` or `Base:`; a failing test added to `.sdlc/baseline.md` or changed commands in `.sdlc/config.json` since `Base:`; `spec.md` edited during Prove; leaving or skipping Prove with untested code (on S, a passing full run of the current code counts; on `Flow: lite`, any Stop outside Stages 4–6 with untested code); an active feature no longer active other than by `Status: done`; or its own record (`.sdlc/.work/trust-anchor.json`) damaged.

1. **Stricter changes** (Track up, Risk low → high, Flow lite → full) only add checks: "Stricter process: …", no block. Exception: a backlog feature leaving `Flow: lite` blocks.
2. **Every other change** blocks the stop once. Claude must tell you what changed and why, without undoing it on its own. Your next message accepts it: the current values become the anchor, and the notice doesn't block again. Autopilot stops at a notice you haven't seen.
3. If the change was wrong, say so in that message and have it reverted (`state.py set`, or restore the file from git); moving a value back is itself a notice.

## Maintenance

### Run the tests

```bash
python3 -m unittest discover -s tests -t tests
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
2. Bump `version` in `.claude-plugin/plugin.json`, then run `python3 scripts/hosts.py build` so the Codex, Cursor and Antigravity manifests carry it too (CI's `hosts.py check` fails while they differ). Repos record this number at setup and upgrade, so every release that changes project files needs a new one.
3. Move the `Unreleased` notes in `CHANGELOG.md` under `## <version> — <date>`, and update the README if commands, phases, configuration or requirements changed.
4. If the release changes files that live in projects:
   - templates of generated or seeded files: nothing to do, `/sdlc:upgrade` regenerates or replaces them;
   - anything a project owns (required commands, config keys, knowledge layout, renamed paths, ignore patterns): add `migrations/<version>-<slug>.md` with frontmatter `version`, `summary` and, if old plugins must stop, `min_plugin_version`, then the steps in prose.
5. **Distill knowledge** with `sdlc:managing-knowledge` (`CLAUDE.md` ≤ 60 lines, `.claude/rules/<area>.md` with `paths:`, `knowledge/` linked from `knowledge/index.md` and logged in `knowledge/log.md`). Sources: the changelog notes, `git log <last tag>..HEAD` (fix commits especially), smoke-test and review findings, and corrections made more than once. Run its "File a lesson" steps for each durable lesson, then its Audit. Decisions about how the plugin works go to `docs/adr/`, procedures to this runbook, and anything corrected twice and checkable becomes a test or guardrail. `python3 scripts/doctor.py` checks the CLAUDE.md budget and the index links.
6. Commit (`release: sdlc <version>`), then run the [smoke test](#smoke-test-before-a-release) against that commit. Every **must** item has to pass.
7. `claude plugin tag . --dry-run`, then `claude plugin tag . --push` (creates and pushes `sdlc--v<version>`). Push the branch too.
8. Publish the GitHub release; the tag alone doesn't make one. As the `tammai` account (`gh auth switch -u tammai`), with the version's changelog section as the notes:
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
3. The repo has `.claude/rules/sdlc*.md`, `.claude/hookify/sdlc-*.md`, `.github/workflows/sdlc-verify.yml` and `sdlc-invariants.yml`, `.sdlc/ci/invariants.py`, `docs/sdlc/constitution.md`, `knowledge/index.md`, `.sdlc/scaffold.lock.json`, and `.gitignore` lists `.sdlc/.work/` and the `.sdlc/state/*.json` contract patterns; `CLAUDE.md` untouched.
4. Context diet (should): after `enable-plugin` it asks whether to trim plugins. Accept. It shows a table of plugins with estimated tokens per call, verdicts and reasons, and writes `.claude/settings.local.json` only after you approve; no commit includes that file.
5. It asks PR or local merge; pick local merge. `/sdlc:doctor` now shows the repo checks ✅.
6. Interrupt test (should): in a second throwaway repo, stop setup midway (Esc), run `/sdlc:setup` again; it resumes after the last finished step.

**D. Guardrails reach Claude (must)**
1. Ask: "add a comment `// Step 1: add the numbers` above the add function". A hookify warning shows, **and Claude's reply acknowledges it** (proof the warning reaches Claude, not only you).
2. Ask: "run `git push --force origin main`". It's blocked, and Claude can say why.
3. Ask Claude to write `const k = "sk-ant-api03-…"` with 30+ characters after the prefix: blocked.

**E. An S fix through all four phases (must)**
1. `/sdlc:start fix: add returns a string when given numeric strings`. It proposes track S and creates `.sdlc/state/<yyyy-mm-dd>-s-<slug>.md`; the announcement shows `Build: subagent`.
2. Define writes `intent.md`, `spec.md` (the repro among its acceptance criteria) and `plan.md` in `docs/sdlc/intents/<feature>/`, and goes on to Build **without asking for approval**.
3. Build dispatches one implementer subagent with `model: sonnet`, which writes a failing test first, then the fix, runs the full suite and doesn't commit.
4. Prove dispatches **nothing** (`.sdlc/.work/dispatches.jsonl` shows no verifier or reviewer): the session runs the full suite once, and the trust anchor accepts that run in place of a verifier.
5. While in Prove, ask Claude to change a source file **with a shell command** (e.g. `sed -i`), then end the turn: it's **blocked**, and the message names the test command. Run it; the turn then ends normally.
6. Ship runs the verified-tree check and Learn, makes one commit, then **stops to ask** merge, PR or keep. `git status` never shows `.sdlc/state/*.json`.
7. Trust anchor (should): in a new S feature, ask Claude to run `state.py set <feature> Risk high`: a "Stricter process" message, no block. Then `Risk low`: the stop is blocked once, and your next message clears it.

**F. Security hooks (should)**
1. Ask Claude to add `eval(input)` to a file: a security warning appears in Claude's context.
2. At the end of that turn, a security review of the turn's changes runs (or, without credentials, you're told once that it's skipped).

**G. Brownfield setup (must)**
1. Copy a small real repo (or a sample with two packages in different languages) into `/tmp/sdlc-smoke-brown`, add one deliberately failing test, commit.
2. `/sdlc:setup`: it records the existing commands per package and **asks you to approve** them; it writes `.sdlc/baseline.md` listing the failing test; audit drafts are shown in batches and nothing is written before you approve.
3. `/sdlc:start` a small change; in Prove the known failure doesn't fail the round, and a new failure would.
4. Monorepo (should): edit a file in one package during Prove; the block names only that package and its command.

**H. Upgrade and eject (must)**
1. In the greenfield repo, edit one guardrail file in `.claude/hookify/` and simulate an older scaffold: set `scaffold_version` in `.sdlc/scaffold.lock.json` to `1.2.9` (the only time to edit the lock by hand).
2. `/sdlc:status` reports the repo as behind and suggests `/sdlc:upgrade`.
3. `/sdlc:upgrade --dry-run` shows the plan and changes nothing (`git status` clean).
4. `/sdlc:upgrade` works on its own branch, asks about the guardrail you edited (apply / skip / keep mine), and ends asking PR or local merge.
5. `/sdlc:eject` shows a dry run first; applied on a branch, it removes the plugin's files, keeps `.sdlc/config.json`, the constitution, knowledge and specs.

**I. Windows (should, if the team uses it).** A teammate runs B–E on Windows in Git Bash.

**J. Other agents (should, one per agent the release claims; must once each before calling an agent supported)**
1. Install from the checkout: Codex `codex plugin marketplace add <checkout>` and `codex plugin add sdlc@sdlc` (note which manifest it used, whether `start` appears as a skill, and whether the Claude-format hooks run; on Windows, whether the skills' bash commands work from its PowerShell); Cursor, a copy in `~/.cursor/plugins/local`; Antigravity, `python3 scripts/hosts.py dist antigravity <folder>` then `agy plugin install <folder>`. The agent lists the sdlc skills, including `start`, `setup` and `upgrade` (Codex: `sdlc:start`, and no `sdlc:source-command-*` duplicates), and Antigravity's `agy agents` lists 13.
2. In a new repo, ask the agent to set up sdlc. It doesn't ask which agent it is, finds `scaffold.py` through the plugin folder note, and records only that host (`.sdlc/scaffold.lock.json` → `hosts`). `AGENTS.md` has the sdlc block. Under `.claude/` there are at most the knowledge step's area rules (`.claude/rules/<area>.md`, which the block copies), and no `sdlc*` rules, hookify or settings. Codex asks to approve each commit unless you give it full access; that's its sandbox, not a failure.
3. Open the same repo in Claude Code and run `/sdlc:setup`: it joins (`hosts` gains `claude-code`), writes the Claude Code rules and guardrails, doesn't redo the commands or baseline, and `/sdlc:doctor` has no fails.
4. Antigravity only: its agent list shows the sdlc agents, or the load error, which goes in the notes.

When every must item passes, record the date and commit in the changelog entry's notes and continue with step 7 above.

### Add or change a phase rule

Phase behavior lives in `skills/orchestrator/`: the core `SKILL.md` (the phase → stage number → file map, tracks, risk and model tiers, state, what several phases share, the rules and hard stops) and `references/` (`define.md`, `build.md`, `prove.md`, `ship.md`, plus `start.md`, `backlog-slices.md`, `review-brief.md`). Anything two phases use goes in the core. The hooks and `state.py` key on the stage numbers (1, 4, 5, 8; 6 for a backlog between slices), not the names. After editing, keep these in step:

| If you change… | Also check |
|---|---|
| Phase gates or tracks | `docs/diagrams/*.svg`, `docs/guidebook.md`, README phase table, the gate table in `docs/sdlc/intents/2026-10-26-four-phases/spec.md` |
| A hard stop | the Rules section of the orchestrator, `docs/playbook.md`, R11 above |
| Verify behavior | `agents/verifier.md`, `agents/qa-tester.md`, `hooks/verify_freshness.py`, `hooks/prove_budget.py` (the 120 s kill), `tests/test_verify_freshness.py`, `hooks/trust_anchor.py` (what it watches), `hooks/role_guard.py` (what the verifier may write) |
| State fields or stage numbers | `scripts/state.py`, `tests/test_state.py`, `docs/specs/12-control-contract.md`, the template in `references/start.md`, every hook that reads the field (`verify_freshness`, `trust_anchor`, `model_router`, `sdlc_review_gate`) |
| An agent's role or file access | the agent's `tools:` frontmatter, `hooks/role_guard.py`, `tests/test_role_guard.py`, `docs/specs/03-scope-and-review.md` and `04-verification.md` |
| Model tiers, track or risk | Model Selection in `skills/subagent-driven-development/SKILL.md`, `hooks/model_router.py`, `tests/test_model_router.py`, `hooks/trust_anchor.py` (it anchors `Risk:`), `docs/specs/02-orchestration.md` |
| Scope-tracing rules | `skills/writing-specs`, `designing-solutions`, `writing-plans`, `analyzing-consistency`, `scripts/diff_stats.py` |
| Setup, upgrade or eject | `skills/setting-up-projects/`, `scripts/scaffold.py`, `templates/project/`, `tests/test_scaffold.py`, `tests/test_project_templates.py`, `docs/diagrams/sdlc_setup_phase.svg`; a changed decision gets a new ADR in `docs/adr/` |

Then run the stale-docs audit in `CONTRIBUTING.md`.

### Setup, upgrade, eject internals

The skill makes the judgment calls; `scripts/scaffold.py` keeps the records (lock, file hashes and classes, keyed merges, migrations, drift). Why it works this way: [ADR 0001](adr/0001-project-setup-upgrade-eject.md) and [ADR 0002](adr/0002-record-the-repos-own-commands.md).

Every command prints one JSON object. Exit codes: 0 ok, 1 error, 2 refused because the user edited the file. Run as `python3 <plugin>/scripts/scaffold.py [--root DIR] <command>`.

| Command | Does |
|---|---|
| `init --kind greenfield\|brownfield [--docs-dir <d>] [--force]` | start setup: write the lock, plus a minimal `config.json` if none exists, and record `docs_dir` (default `docs/sdlc`; left unset while features from before setup are still in `.sdlc/`, reported as `legacy_features`) |
| `paths [<feature>]` | where this repo keeps a feature's state and documents, the constitution and the design system (`layout`: `new` or `legacy`) |
| `relocate [--docs-dir <d>] [--apply]` | move an old-layout repo: state to `.sdlc/state/`, documents to `<d>` with `git mv`; tracked files only; dry run unless `--apply`; clean tree only; all or nothing (any conflict moves nothing); records `docs_dir` |
| `status` | setup state, steps done, drift (`current` / `behind` / `ahead` / `plugin_too_old`), pending migrations, file states, `layout`, and `docs_site` (the file that shows `docs/` is published as a site) |
| `config` | effective config: plugin defaults merged with the project's overrides |
| `step-done <step> [--complete]` | record setup progress (resumable) |
| `contract` | check the commands per scope: required ones present, package paths exist, tools on PATH; reports the recorded runs |
| `commands` | scopes plus the install steps and verify plan, each with its directory |
| `run-commands [--timeout S]` | run install and the verify plan once, record each exit in the lock; exit 1 if a command couldn't start |
| `render <template\|builtin:…> <dest> [--class seeded] [--if-unchanged]` | render a plugin template (`{{config.x.y}}`, `{{plugin_version}}`) or a builtin (`ci`, `ci:<package>`, `contract-check`, `invariants`, `codeowners`), and record its hash |
| `preview <template\|builtin:…>` | render without writing |
| `record <generated\|seeded> <paths…> [--template T]` / `forget <paths…>` | track files Claude wrote / hand them over to the user |
| `allow --add/--remove … [--from-commands]`, `gitignore --add/--remove …`, `enable-plugin` | keyed merges; only ever removes entries the plugin added (`enable-plugin`: the sdlc marketplace and `enabledPlugins` in `.claude/settings.json`) |
| `host` / `add-host <host>` | the coding agent running (from the plugin's install folder, else the environment), the hosts recorded in the lock, and whether this one is joining / record a joining agent |
| `agents [--check]` | rebuild the sdlc block in `AGENTS.md` for the recorded hosts (removed when Claude Code is the only one) and `.claude/rules/sdlc-agents-md.md`, Claude Code's copy of the team's own `AGENTS.md` text; `--check` exits 1 when either is out of date |
| `migrations [--revisit]`, `migration <id> --applied\|--skipped REASON` | pending migrations (scaffold < version ≤ plugin, numeric order) / record the outcome |
| `set-version <v> [--min-plugin m]` | advance `scaffold_version`; raises the pin, never lowers it |
| `upgrade-plan` | regenerate / replace / review / restore / template_gone, `agents` (off, in_sync or stale), plus pending migrations |
| `eject [--apply] [--also <edited files>]` | dry run by default; applying deletes plugin files, removes recorded entries and the lock |
