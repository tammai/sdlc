# sdlc runbook

Operational procedures: install, check health, fix what breaks, maintain the plugin. Concepts are in the [guidebook](guidebook.md); day-to-day usage is in the [playbook](playbook.md).

## Reference

### Prerequisites

| Need | For |
|---|---|
| `git` | worktrees, freshness hook, commit and PR commands |
| `gh` | `/sdlc:code-review` and PR commands |
| Python 3 | all hooks and `scripts/` (stdlib only; macOS system 3.9 works) |
| `just` (≥ 1.31 for monorepo modules) | the command contract in set-up repos. Prefer prebuilt installs: `npm i -g rust-just`, `pipx install rust-just`, `winget install Casey.Just`. `brew install just` only where Homebrew has a bottle for your Mac; otherwise it compiles Rust and LLVM from source for hours |
| Git for Windows (Windows only) | `just` recipes run through `sh`; run them from Git Bash |
| Node | brainstorming visual companion |
| `typescript-language-server`, `typescript` | TypeScript code intelligence (`npm i -g typescript-language-server typescript`) |

### Where state lives

| What | Path |
|---|---|
| Project config (overrides on plugin defaults) | `.sdlc/config.json` |
| What the plugin placed, scaffold version, migrations | `.sdlc/scaffold.lock.json` (never edit by hand) |
| Known failures from before setup | `.sdlc/baseline.md` |
| Feature state | `.sdlc/<feature>/state.md` |
| Feature artifacts | `.sdlc/<feature>/*.md` (committed) |
| Scratch | `.sdlc/.work/` (git-ignored) |
| Verify freshness state | `.sdlc/.work/verify-freshness.json` |
| Ralph loop state | `.claude/ralph-loop.local.md` |
| Personal hookify rules | `.claude/hookify.<name>.local.md` (git-ignored) |
| Team hookify rules | `.claude/hookify/<name>.md` (committed) |
| Security hook per-session state, reviewer venv | `~/.claude/security/` (venv: `~/.claude/security/agent-sdk-venv`) |

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

Then restart the session so the plugin's commands and hooks load. `/plugin` lists installed plugins and whether sdlc is enabled. To get a new version, update the marketplace and the plugin from `/plugin`, then restart.

Working on the plugin itself instead? See [Develop locally](#develop-locally).

Smoke test in a scratch repo:

1. `/sdlc:status` answers "nothing in `.sdlc/`" (or lists features) without errors.
2. `/sdlc:start` with a tiny request creates `.sdlc/<feature>/state.md` and announces a track and first stage.
3. First session start may take about a minute while the security reviewer's Python environment is built.

## Health check

Run through this when something feels off.

| Check | How | Expected |
|---|---|---|
| Plugin installed and enabled | `/plugin` | `sdlc` listed as enabled |
| Python available | `python3 --version` | 3.x |
| Reviewer environment | `ls ~/.claude/security/agent-sdk-venv` | exists after the first session |
| Repo set up and current | `/sdlc:status` | setup complete, scaffold version = plugin version |
| Command contract | `python3 <plugin>/scripts/scaffold.py contract` | `"ok": true`, `"just": {"ok": true}` |
| Feature state readable | `/sdlc:status` | one line per feature |
| Hook tests pass | `python3 -m unittest discover -s tests -t tests` from the plugin repo | all pass |

## Procedures

### R1. Plugin won't load or components are missing

1. Open `/plugin` and confirm `sdlc` is installed and enabled. If not, install it (see [Install](#install)).
2. Slash commands use the `sdlc:` prefix. If `/sdlc:start` isn't found, restart the session after installing or updating.
3. Still missing after a restart: update the marketplace and reinstall the plugin from `/plugin`.
4. Maintainers: run `claude plugin validate .` in the plugin repo and read the first error; check `.claude-plugin/plugin.json` and `hooks/hooks.json` are valid JSON.

### R2. First session is slow or the security reviewer is unavailable

Cause: the SessionStart hook builds a venv with the Claude Agent SDK if it isn't importable.

1. Wait for the first start to finish (timeout is 180 s).
2. If it failed, check network access to the Python package index, then start a new session to retry.
3. To rebuild from scratch: remove `~/.claude/security/agent-sdk-venv` and start a new session.
4. The venv lives outside the plugin, so it survives plugin updates.

### R3. Security hook is too noisy or too slow

1. Identify which part is firing: edit pattern warnings, turn-end review, or commit/push review.
2. Turn off only that part with the matching variable from the table above.
3. Prefer fixing the finding. If it's a false positive you'll see again, tell the reviewer why in the response (acknowledged findings are fine) rather than disabling the hook.
4. `SECURITY_GUIDANCE_DISABLE=1` is a last resort and should be recorded under Deviations in `state.md`.

### R4. Blocked at Stop with "re-run tests"

The verify-freshness hook is active only while `state.md` says `Current: Stage 5 – Verify`.

1. Run the **full** test command (`just verify`/`just test`, or the `test:` command in `state.md`). A filtered run, single test file, pytest node id or single Go package doesn't count.
2. Make sure no code changed after that run. Formatters, `sed -i` and subagents count as changes; the hook compares the worktree against the tree recorded at the last full run.
3. Edits to `.md`, `.mdx`, `.txt`, `.rst` and anything under `.sdlc/`, `knowledge/`, `.claude/`, `docs/` don't mark results stale.
4. If the recorded full-run command is wrong, fix `test:` in `state.md`, or set `verify.full` in `.sdlc/config.json` (a list of commands).
5. If the state file itself is wrong, delete `.sdlc/.work/verify-freshness.json`; the next full run recreates it.
6. The hook never fails the session on its own error. If it blocks wrongly, run the hook tests (below) and open an issue with the transcript.

### R5. A verify round gives different answers each time

1. Don't retry until green. Each retry that passes after failing is a flaky test, which the gate counts as a violation.
2. Ask the next fresh verifier to run the failing test several times in isolation and record the results in `test-report.md`.
3. Fix or quarantine the flaky test with your approval, and record it under Deviations.

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

1. `/sdlc:status` shows every feature and its state.
2. Features that are finished should have `Status: done`. Others you're not working on: set `Status:` to something other than `active` (for example `paused`).
3. Answer the "which one" prompt if it still asks.

### R9. `state.md` is missing, stale or hand-edited wrong

1. The file is plain markdown; fix it directly. Keep the line format `Current: Stage <n> – <name>` and `Status: active`.
2. The artifacts (`spec.md`, `plan.md`, `test-report.md`…) are the real record. To rebuild a lost state file, create one from the template in `skills/orchestrator/SKILL.md`, tick the stages whose artifacts exist, and set `Current:` to the next stage.
3. Add a Deviations line saying the file was reconstructed.

### R10. Hooks error on Windows or with an odd Python

`hooks/sg-python.sh` probes `python3`, `python` and `py -3`, skipping the Microsoft Store stub, and forces UTF-8. If the security hook still fails, run `bash hooks/sg-python.sh -c "import sys; print(sys.version)"` to see which interpreter it chose. The hookify, freshness and ralph hooks call `python3` or bash directly, so `python3` must work for them.

### R11. A gate is blocking and you disagree

This is a decision, not a fault. Say `skip` or `just ship it`; the orchestrator names the gates, writes them under Deviations, and continues. See playbook 9.

### R12. Setup stopped halfway

1. Run `/sdlc:setup` again. It reads `completed_steps` from the lock and continues with the next step on the same `sdlc/setup` branch.
2. Want a clean restart instead: delete the branch, then `python3 <plugin>/scripts/scaffold.py init --kind <greenfield|brownfield> --force` and rerun setup.
3. "Working tree not clean": commit or stash first; setup won't mix its commits with your changes.

### R13. `just` missing, too old, or "could not find sh"

1. `python3 <plugin>/scripts/scaffold.py contract` reports `just.installed`, `just.version`, the minimum (1.31 when the justfile uses modules) and an install command for your OS.
2. Install a prebuilt binary (see Prerequisites). Linux distro packages are often older than 1.31.
3. Windows "could not find sh": run `just` from Git Bash, or reinstall Git for Windows with its Unix tools on PATH. CI is unaffected: workflows run every step with `shell: bash`.
4. `contract` lists missing recipes per justfile (and per package in a monorepo): add them; the names are fixed, the bodies are yours.

### R14. An upgrade won't overwrite a file, or keeps asking about it

1. That file is seeded and you edited it, so the upgrade refuses to overwrite it (`scaffold.py render --if-unchanged` exits 2). This is on purpose.
2. Pick **apply** to take the proposed merge, **skip** to be asked next time, or **keep mine**: `scaffold.py forget <path>` makes it yours for good and upgrades stop asking.
3. A deleted plugin file is offered for restore once; declining forgets it.

### R15. A migration was declined and you want it after all

`/sdlc:upgrade --revisit` lists skipped migrations with the reason you gave and offers each again. `scaffold.py migrations --revisit` shows the same list without changing anything.

### R16. Stage 5 blames the feature for an old failure, or the baseline looks wrong

1. Check `.sdlc/baseline.md`: failing tests by file › name, lint/type errors as counts per rule and file. A count that went **up** counts as new.
2. A pre-existing failure missing from the baseline: add it yourself with a note, and record a Deviation in that feature's `state.md`. The verifier never adds items.
3. Items disappearing: the verifier removes items that now pass. That's expected; the test report lists them.

### R17. Eject left something behind or broke the build

1. `scaffold.py eject` (dry run) shows what it would still remove; edited plugin files are only deleted when you say so.
2. Imports into deleted files (`eslint.sdlc.mjs` in `eslint.config.*`, `extend = ".sdlc/lint/ruff.sdlc.toml"` in `pyproject.toml`) should have been offered as diffs. If not, remove them by hand and run `just verify`.

## Maintenance

### Run the tests

```bash
python3 -m unittest discover -s tests -t tests
```

Stdlib only. Each test runs a hook as a subprocess against a throwaway project. Run after any hook change and after updating vendored code. `claude plugin test` doesn't apply: it only runs TypeScript hook modules.

### Update vendored code

Sources and licenses are in `NOTICE.md`.

1. Re-copy the listed upstream files.
2. Re-apply the documented renames (`superpowers:` → `sdlc:`, paths → `.sdlc/`) and the patches listed under "Modified" (hookify field fallback, `not_regex_match`, team-rule loading, `additionalContext`/`permissionDecisionReason`, no PostToolUse duplicate, ralph state-file tolerance).
3. Run the tests. The hookify and ralph tests exist to catch exactly those regressions.
4. Update `NOTICE.md` if you added or removed vendored files or patches.

Claude Security is not bundled (its license reserves all rights); install it separately.

### Develop locally

For changes to the plugin itself, run it from a checkout instead of the marketplace copy:

```bash
claude plugin validate .             # manifest and components parse
claude --plugin-dir .                # load it for one session
```

### Release a new version

1. Run the tests and `claude plugin validate .`.
2. Bump `version` in `.claude-plugin/plugin.json`.
3. Update README if commands, stages or requirements changed.
4. If the release changes files that live in projects:
   - templates of generated or seeded files: nothing to do, `/sdlc:upgrade` regenerates or replaces them;
   - anything a project owns (justfile recipes, config keys, knowledge layout, renamed paths): add `migrations/<version>-<slug>.md` with frontmatter `version`, `summary` and, if old plugins must stop, `min_plugin_version`, then the steps in prose.
5. Commit, tag, and push. Users get the new version by updating the marketplace and the plugin from `/plugin`, then run `/sdlc:upgrade` in each repo.

### Add or change a stage rule

Stage behavior lives in `skills/orchestrator/SKILL.md`. After editing it, keep these in step:

| If you change… | Also check |
|---|---|
| Stage gates or tracks | `docs/diagrams/*.svg`, `docs/guidebook.md`, README stage table |
| A hard stop | the Rules section of the orchestrator, `docs/playbook.md` |
| Verify behavior | `agents/verifier.md`, `hooks/verify_freshness.py`, `tests/test_verify_freshness.py` |
| Scope-tracing rules | `skills/writing-specs`, `designing-solutions`, `writing-plans`, `analyzing-consistency`, `scripts/diff_stats.py` |
| Setup, upgrade or eject | `skills/setting-up-projects/`, `scripts/scaffold.py`, `templates/project/`, `templates/justfile/`, `tests/test_scaffold.py`, `tests/test_project_templates.py`, `docs/design/setup-and-upgrade.md`, `docs/diagrams/sdlc_setup_phase.svg` |

### Setup, upgrade, eject internals

The skill makes the judgment calls; `scripts/scaffold.py` keeps the records (lock, file hashes and classes, keyed merges, migrations, drift). Every command prints JSON; exit 2 means "refused, the user edited this file". Design, ownership model and command reference: `docs/design/setup-and-upgrade.md`.
