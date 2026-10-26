# sdlc runbook

Operational procedures: install, check health, fix what breaks, maintain the plugin. Concepts are in the [guidebook](guidebook.md); day-to-day usage is in the [playbook](playbook.md).

## Reference

### Prerequisites

| Need | For |
|---|---|
| `git` | worktrees, freshness hook, commit and PR commands |
| `gh` | `/sdlc:code-review` and PR commands |
| Python 3 | all hooks and `scripts/` (stdlib only; macOS system 3.9 works) |
| Node | brainstorming visual companion |
| `typescript-language-server`, `typescript` | TypeScript code intelligence (`npm i -g typescript-language-server typescript`) |

### Where state lives

| What | Path |
|---|---|
| Project config (overrides on plugin defaults) | `.sdlc/config.json` |
| What the plugin placed, scaffold version, migrations | `.sdlc/scaffold.lock.json` (never edit by hand) |
| Known failures from before setup | `.sdlc/baseline.md` |
| Feature state | `.sdlc/state/<feature>.md` |
| Feature artifacts | `docs/sdlc/intents/<feature>/*.md` (committed) |
| Scratch | `.sdlc/.work/` (git-ignored) |
| Verify freshness state | `.sdlc/.work/verify-freshness.json` |
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

Then restart the session so the plugin's commands and hooks load. `/plugin` lists installed plugins and whether sdlc is enabled. To get a new version, update the marketplace and the plugin from `/plugin`, then restart.

Working on the plugin itself instead? See [Develop locally](#develop-locally).

Smoke test in a scratch repo:

1. First session start may take about a minute while the security reviewer's Python environment is built.
2. `/sdlc:doctor`: no ❌. Expected warnings: the repo isn't set up yet, and (before the first session finishes) the reviewer environment.
3. `/sdlc:status` says the repo isn't set up and lists no features.
4. `/sdlc:setup` with a one-line description: it proposes a stack, and after your OK writes `.sdlc/config.json` and the rest on a `sdlc/setup` branch. Run `/sdlc:doctor` again: the repo checks are ✅.
5. `/sdlc:start` with a tiny request creates `.sdlc/state/<feature>.md` and announces a track and its phases.

## Health check

Run `/sdlc:doctor` when something feels off, after installing or upgrading, or before onboarding a teammate. It changes nothing; it prints one row per check with ✅ / ⚠️ / ❌ and, for anything not ok, the fix and the procedure below that covers it. The same report from a shell: `python3 <plugin>/scripts/doctor.py --format md` (exit 1 if anything fails).

| Group | What it checks |
|---|---|
| environment | Python ≥ 3.9, a working `python3`, git, gh, jq, the security reviewer's environment (built in the state directory on first session) |
| plugin | version; every script `hooks.json` references exists |
| repo | setup state and version drift; config and lock parse; plugin files missing or hand-edited; project commands defined (per package) and their tools found on PATH; baseline present (brownfield); design system present when the repo has UI files; `.sdlc/.work/` git-ignored; rules whose `paths:` match no files; hookify rules that don't parse or have a bad regex; CLAUDE.md over 60 lines; broken links in `knowledge/index.md`; malformed or several active `state.md`; corrupt freshness state |

Not covered by doctor: whether the plugin is enabled (`/plugin`), and the plugin's own test suite (`python3 -m unittest discover -s tests -t tests` in the plugin repo).

## Procedures

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

1. Identify which part is firing: edit pattern warnings, turn-end review, or commit/push review.
2. Turn off only that part with the matching variable from the table above.
3. Prefer fixing the finding. If it's a false positive you'll see again, tell the reviewer why in the response (acknowledged findings are fine) rather than disabling the hook.
4. `SECURITY_GUIDANCE_DISABLE=1` is a last resort and should be recorded under Deviations in `state.md`.

### R4. Blocked at Stop with "re-run tests"

The verify-freshness hook is active only while `state.md` says `Current: Stage 5 – Prove` (Stage 5; for a feature started under the old Lite flow, also Stage 6).

1. Run the **full** test command: `commands.test` from `.sdlc/config.json` (monorepo: the stale package's own, from its `path`; the block message names it), or the `test:` command in `state.md`. A filtered run, single test file, pytest node id or single Go package doesn't count.
2. Make sure no code changed after that run. Formatters, `sed -i` and subagents count as changes; the hook compares the worktree against the tree recorded at the last full run.
3. Edits to `.md`, `.mdx`, `.txt`, `.rst` and anything under `.sdlc/`, `knowledge/`, `.claude/`, `docs/` don't mark results stale.
4. If the recorded test command is wrong, fix `commands.test` (or the package's) in `.sdlc/config.json`, or `test:` in `state.md` for a repo without setup.
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
2. The artifacts (`spec.md`, `plan.md`, `test-report.md`…) are the real record. To rebuild a lost state file, create one from the template in `skills/orchestrator/references/start.md` (then `state.py sync <feature>`), tick the phases whose artifacts exist, and set `Current:` to the next phase's stage (1 Define, 4 Build, 5 Prove, 8 Ship).
3. Add a Deviations line saying the file was reconstructed.

### R10. Hooks error on Windows or with an odd Python

`hooks/sg-python.sh` probes `python3`, `python` and `py -3`, skipping the Microsoft Store stub, and forces UTF-8. If the security hook still fails, run `bash hooks/sg-python.sh -c "import sys; print(sys.version)"` to see which interpreter it chose. The hookify, freshness, model-router and ralph hooks call `python3` or bash directly, so `python3` must work for them.

### R11. A gate is blocking and you disagree

This is a decision, not a fault. Say `skip` or `just ship it`; the orchestrator names the gates, writes them under Deviations, and continues. See playbook 9.

### R12. Setup stopped halfway

1. Run `/sdlc:setup` again. It reads `completed_steps` from the lock and continues with the next step on the same `sdlc/setup` branch.
2. Want a clean restart instead: delete the branch, then `python3 <plugin>/scripts/scaffold.py init --kind <greenfield|brownfield> --force` and rerun setup.
3. "Working tree not clean": commit or stash first; setup won't mix its commits with your changes.

### R13. A project command is missing, wrong, or its tool isn't installed

1. `/sdlc:doctor` (repo · commands, command tools) or `python3 <plugin>/scripts/scaffold.py contract` shows, per package, which required commands are missing and which tools aren't on PATH.
2. Commands live in `.sdlc/config.json`: `commands` for one project, `packages[].commands` per package. Use what the team already runs; set a step to `null` if it doesn't apply to that stack.
3. A tool not found: install it the way the project expects (the lockfile and toolchain files say which version), or fix the command.
4. After changing commands, run `/sdlc:upgrade` so the generated CI workflow follows (or review its diff if you edited the workflow).

### R14. An upgrade won't overwrite a file, or keeps asking about it

1. That file is seeded and you edited it, so the upgrade refuses to overwrite it (`scaffold.py render --if-unchanged` exits 2). This is on purpose.
2. Pick **apply** to take the proposed merge, **skip** to be asked next time, or **keep mine**: `scaffold.py forget <path>` makes it yours for good and upgrades stop asking.
3. A deleted plugin file is offered for restore once; declining forgets it.

### R15. A migration was declined and you want it after all

`/sdlc:upgrade --revisit` lists skipped migrations with the reason you gave and offers each again. `scaffold.py migrations --revisit` shows the same list without changing anything.

### R16. Prove blames the feature for an old failure, or the baseline looks wrong

1. Check `.sdlc/baseline.md`: failing tests by file › name, lint/type errors as counts per rule and file. A count that went **up** counts as new.
2. A pre-existing failure missing from the baseline: add it yourself with a note, and record a Deviation in that feature's `state.md`. The verifier never adds items.
3. Items disappearing: the verifier removes items that now pass. That's expected; the test report lists them.

### R17. Eject left something behind or broke the build

1. `scaffold.py eject` (dry run) shows what it would still remove; edited plugin files are only deleted when you say so.
2. Imports into deleted files (`eslint.sdlc.mjs` in `eslint.config.*`, `extend = ".sdlc/lint/ruff.sdlc.toml"` in `pyproject.toml`) should have been offered as diffs. If not, remove them by hand and rerun the verify commands.

### R18. A subagent dispatch is denied by the model router

The hook is active only while a feature has `Status: active`; the deny reason says which check failed.

1. **No model:** the dispatch must name `haiku`, `sonnet` or `opus` (Model Selection in `sdlc:subagent-driven-development`). Commands that launch agents, such as `/sdlc:review-pr`, name one too.
2. **Fable:** used only on your request. Set `Top model: fable` in every active `state.md` (one active feature without it keeps Fable denied).
3. **Reviewer below Opus:** the feature says `Risk: high`. If the risk was misjudged, fix `Risk:` in `state.md` and record it under Deviations.
4. Forks are never checked: they always run on the session model. To keep Fable out of forks, don't run the session on Fable.

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

1. Run the tests and `claude plugin validate .`, and check that CI (`.github/workflows/ci.yml`) is green on the last pushed commit.
2. Bump `version` in `.claude-plugin/plugin.json`, then run `python3 scripts/hosts.py build` so the Codex, Cursor and Antigravity manifests carry it too (CI fails while they differ). Repos record this number at setup and upgrade, so every release that changes project files needs a new one.
3. Move the `Unreleased` notes in `CHANGELOG.md` under the new version, and update the README if commands, phases, configuration or requirements changed.
4. If the release changes files that live in projects:
   - templates of generated or seeded files: nothing to do, `/sdlc:upgrade` regenerates or replaces them;
   - anything a project owns (required commands, config keys, knowledge layout, renamed paths): add `migrations/<version>-<slug>.md` with frontmatter `version`, `summary` and, if old plugins must stop, `min_plugin_version`, then the steps in prose.
5. **Distill knowledge** with `sdlc:managing-knowledge`, the same 3-tier spec the plugin gives projects: `CLAUDE.md` (≤ 60 lines), `.claude/rules/<area>.md` with `paths:`, and `knowledge/` (OKF, linked from `knowledge/index.md`, logged in `knowledge/log.md`). Sources: the changelog notes, `git log <last tag>..HEAD` (fix commits especially), smoke-test and review findings, and corrections made more than once. Run its "File a lesson" steps for each durable lesson, then its Audit. Decisions about how the plugin works still go to `docs/adr/` (the index links there), procedures to this runbook, and anything corrected twice and checkable becomes a test or guardrail. `python3 scripts/doctor.py` checks the CLAUDE.md budget and the index links.
6. Commit, then run the [smoke test](#smoke-test-before-a-release) against that commit. Every **must** item has to pass.
7. `claude plugin tag . --dry-run`, then `claude plugin tag . --push` (creates `sdlc--v<version>`, checks that `plugin.json` and the marketplace entry agree, and pushes the tag). Push the branch too.
8. Publish the GitHub release; the tag alone doesn't make one. As the `tammai` account (`gh auth switch -u tammai`), with the version's changelog section as the notes:
   ```bash
   v=<version>; awk -v v="$v" '/^## /{p=($2==v);next} p' CHANGELOG.md > /tmp/notes.md
   gh release create "sdlc--v$v" --verify-tag --title "sdlc $v" --notes-file /tmp/notes.md --latest
   ```
   Users get the new version by updating the marketplace and the plugin from `/plugin`, then run `/sdlc:upgrade` in each repo.

### Smoke test before a release

The test suite runs hooks and scripts as subprocesses; this checks the installed plugin in real Claude Code sessions, which the suite can't. About 45 minutes. Use throwaway repos outside any real project, a **fresh session** for each part, and write down anything that doesn't match (what you did, what you saw, the session's transcript path).

**Must** items block the release; **should** items become known issues in the changelog.

**A. Install from the checkout (must)**
1. In a new terminal: `claude`, then `/plugin marketplace add <path to this checkout>` and `/plugin install sdlc@sdlc`. Restart the session.
2. `/plugin` lists `sdlc` as enabled, version matching `plugin.json`.
3. The first session start may pause about a minute while the security reviewer's environment builds.

**B. Doctor in an empty repo (must)**
1. `mkdir /tmp/sdlc-smoke-green && cd $_ && git init`, start `claude`.
2. `/sdlc:doctor`: no ❌; the repo check says "not set up"; the security reviewer environment is ✅ (or ⚠️ only if no API credentials).

**C. Greenfield setup (must)**
1. `/sdlc:setup a tiny TypeScript library that adds two numbers`.
2. It asks a few stack questions and **waits for your approval** before generating anything.
3. It works on a `sdlc/setup` branch with one commit per step; `.sdlc/config.json` has the five commands; it runs them and they pass.
4. The repo has `.claude/rules/sdlc*.md`, `.claude/hookify/sdlc-*.md`, `.github/workflows/sdlc-verify.yml` and `sdlc-invariants.yml`, `.sdlc/ci/invariants.py`, `docs/sdlc/constitution.md`, `knowledge/index.md`, `.sdlc/scaffold.lock.json`; `CLAUDE.md` untouched.
5. Context diet (should): right after `enable-plugin` it asks whether to trim plugins. Accept it. It shows a table of plugins with estimated tokens per call, verdicts and reasons, and writes `.claude/settings.local.json` only after you approve. `git status` and the setup commits never include that file.
6. It asks PR or local merge; pick local merge. `/sdlc:doctor` now shows the repo checks ✅.
7. Interrupt test (should): in a second throwaway repo, stop setup midway (Esc), run `/sdlc:setup` again; it resumes after the last finished step.

**D. Guardrails reach Claude (must)**
1. Ask: "add a comment `// Step 1: add the numbers` above the add function". A hookify warning shows, **and Claude's reply acknowledges it** (proof the warning reaches Claude, not only you).
2. Ask: "run `git push --force origin main`". It's blocked, and Claude can say why (the reason reaches Claude).
3. Ask Claude to write `const k = "sk-ant-api03-…"` with 30+ characters after the prefix: blocked.

**E. An S fix through Prove (must)**
1. `/sdlc:start fix: add returns a string when given numeric strings`. It proposes track S and creates `.sdlc/state/<feature>.md`.
2. Build dispatches one implementer subagent with `model: haiku`, which writes a failing test first, then the fix.
3. Prove spawns a **fresh** verifier agent and the reviewer (with diff stats) in parallel; the verifier which appends a round to `test-report.md`.
4. While in Prove, ask Claude to change a source file **with a shell command** (e.g. `sed -i`), then end the turn: it's **blocked**, and the message names the test command. Run it; the turn then ends normally.
5. Ship commits and stops before merging to ask you.

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
4. `/sdlc:upgrade` works on its own branch, asks about the guardrail you edited (merge / skip / keep mine), and ends asking PR or local merge.
5. `/sdlc:eject` shows a dry run first; applied on a branch, it removes the plugin's files, keeps `.sdlc/config.json`, the constitution, knowledge and specs.

**I. Windows (should, if the team uses it)**
A teammate runs B–E on Windows in Git Bash.

**J. Other agents (should, one per agent the release claims; must once each before calling an agent supported)**
1. Install from the checkout: Codex `codex plugin marketplace add <checkout>` and `codex plugin add sdlc@sdlc` (note which manifest it used, whether `start` appears as a skill, and whether the Claude-format hooks run; on Windows, whether the skills' bash commands work from its PowerShell); Cursor, a copy in `~/.cursor/plugins/local`; Antigravity, `python3 scripts/hosts.py dist antigravity <folder>` then `agy plugin install <folder>`. The agent lists the sdlc skills, including `start`, `setup` and `upgrade` (Codex: `sdlc:start`, and no `sdlc:source-command-*` duplicates), and Antigravity's `agy agents` lists 13.
2. In a new repo, ask the agent to set up sdlc. It doesn't ask which agent it is, finds `scaffold.py` through the plugin folder note, and records only that host (`.sdlc/scaffold.lock.json` → `hosts`). `AGENTS.md` has the sdlc block. Under `.claude/` there are at most the knowledge step's area rules (`.claude/rules/<area>.md`, which the block copies), and no `sdlc*` rules, hookify or settings. Codex asks to approve each commit unless you give it full access; that's its sandbox, not a failure.
3. Open the same repo in Claude Code and run `/sdlc:setup`: it joins (`hosts` gains `claude-code`), writes the Claude Code rules and guardrails, doesn't redo the commands or baseline, and `/sdlc:doctor` has no fails.
4. Antigravity only: its agent list shows the sdlc agents, or the load error, which goes in the notes.

When every must item passes, record the date and commit in the changelog entry's notes (or the PR) and continue with step 6 above.

### Add or change a phase rule

Phase behavior lives in `skills/orchestrator/`: the core `SKILL.md` (the phase → stage number → file map, tracks, tiers, state, what several phases share) and `references/` (`define.md`, `build.md`, `prove.md`, `ship.md`, plus `start.md`, `backlog-slices.md`, `review-brief.md`). Anything two phases use goes in the core. The hooks key on the stage numbers (1, 4, 5, 8), not the names. After editing, keep these in step:

| If you change… | Also check |
|---|---|
| Phase gates or tracks | `docs/diagrams/*.svg`, `docs/guidebook.md`, README phase table, the gate table in `docs/sdlc/intents/2026-10-26-four-phases/spec.md` |
| A hard stop | the Rules section of the orchestrator, `docs/playbook.md` |
| Verify behavior | `agents/verifier.md`, `agents/qa-tester.md`, `hooks/verify_freshness.py`, `tests/test_verify_freshness.py`, `hooks/trust_anchor.py` (what it watches) |
| An agent's role or file access | the agent's `tools:` frontmatter, `hooks/role_guard.py`, `tests/test_role_guard.py`, `docs/specs/03-scope-and-review.md` and `04-verification.md` |
| Model tiers or risk | Model Selection in `skills/subagent-driven-development/SKILL.md`, `hooks/model_router.py`, `tests/test_model_router.py`, `hooks/trust_anchor.py` (it anchors `Risk:`), `docs/specs/02-orchestration.md` |
| Scope-tracing rules | `skills/writing-specs`, `designing-solutions`, `writing-plans`, `analyzing-consistency`, `scripts/diff_stats.py` |
| Setup, upgrade or eject | `skills/setting-up-projects/`, `scripts/scaffold.py`, `templates/project/`, `tests/test_scaffold.py`, `tests/test_project_templates.py`, `docs/diagrams/sdlc_setup_phase.svg`; a changed decision gets a new ADR in `docs/adr/` |

### Setup, upgrade, eject internals

The skill makes the judgment calls; `scripts/scaffold.py` keeps the records (lock, file hashes and classes, keyed merges, migrations, drift). Why it works this way: [ADR 0001](adr/0001-project-setup-upgrade-eject.md) and [ADR 0002](adr/0002-record-the-repos-own-commands.md).

Every command prints one JSON object. Exit codes: 0 ok, 1 error, 2 refused because the user edited the file. Run as `python3 <plugin>/scripts/scaffold.py [--root DIR] <command>`.

| Command | Does |
|---|---|
| `init --kind greenfield\|brownfield [--docs-dir <d>]` | start setup: write the lock, plus a minimal `config.json` if none exists, and record `docs_dir` (default `docs/sdlc`; left unset while features from before setup are still in `.sdlc/`, reported as `legacy_features`) |
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
| `allow --add/--remove … [--from-commands]`, `gitignore --add/--remove …` | keyed merges; only ever removes entries the plugin added |
| `host` / `add-host <host>` | the coding agent running (from the plugin's install folder, else the environment), the hosts recorded in the lock, and whether this one is joining / record a joining agent |
| `agents [--check]` | rebuild the sdlc block in `AGENTS.md` for the recorded hosts (removed when Claude Code is the only one) and `.claude/rules/sdlc-agents-md.md`, Claude Code's copy of the team's own `AGENTS.md` text; `--check` exits 1 when either is out of date |
| `migrations [--revisit]`, `migration <id> --applied\|--skipped REASON` | pending migrations (scaffold < version ≤ plugin, numeric order) / record the outcome |
| `set-version <v> [--min-plugin m]` | advance `scaffold_version`; raises the pin, never lowers it |
| `upgrade-plan` | regenerate / replace / review / restore / template_gone, `agents` (off, in_sync or stale), plus pending migrations |
| `eject [--apply] [--also <edited files>]` | dry run by default; applying deletes plugin files, removes recorded entries and the lock |
