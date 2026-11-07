# sdlc runbook

Maintainer procedures: tests, vendored code, releases, the smoke test, phase rules and the setup internals. For users, install, the health check and the fixes (R1–R19) are in the wiki: [Install](https://github.com/tammai/sdlc/wiki/Install), [Health check](https://github.com/tammai/sdlc/wiki/Health-check), [Troubleshooting](https://github.com/tammai/sdlc/wiki/Troubleshooting). The layout and dev loop are in [CONTRIBUTING](../CONTRIBUTING.md).

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

When the maintainer says "release", the agent runs every step below through to the published GitHub release: bump, changelog, docs, commit, PR, CI, merge, tag and release. It doesn't stop to hand a step back or to ask before each one. It stops only when a step fails, or for a decision only the maintainer can make (a failing **must** item, a version number the changelog doesn't settle). `main` accepts changes only through a pull request, and the `protect tag` ruleset lets only repository admins create tags.

1. Run the tests and `claude plugin validate .`, and check that CI (`.github/workflows/ci.yml`) is green on the last pushed commit.
2. Bump `version` in `.claude-plugin/plugin.json` and, to the same number, in `plugins/sdlc-extras/.claude-plugin/plugin.json` and `plugins/sdlc-stepper/.claude-plugin/plugin.json` (`test_marketplace` fails while they differ), then run `python3 scripts/hosts.py build` so the Codex, Cursor and Antigravity manifests carry it too (CI's `hosts.py check` fails while they differ). Repos record this number at setup and upgrade, so every release that changes project files needs a new one.
3. Move the `Unreleased` notes in `CHANGELOG.md` under `## <version> — <date>`, and update the README and the wiki pages in `docs/wiki/` if commands, phases, configuration or requirements changed.
4. If the release changes files that live in projects:
   - templates of generated or seeded files: nothing to do, `/sdlc:upgrade` regenerates or replaces them;
   - anything a project owns (required commands, config keys, knowledge layout, renamed paths, ignore patterns): add `migrations/<version>-<slug>.md` with frontmatter `version`, `summary` and, if old plugins must stop, `min_plugin_version`, then the steps in prose.
5. **Distill knowledge** with `sdlc:managing-knowledge` (`CLAUDE.md` ≤ 60 lines, `.claude/rules/<area>.md` with `paths:`, `knowledge/` linked from `knowledge/index.md` and logged in `knowledge/log.md`). Sources: the changelog notes, `git log <last tag>..HEAD` (fix commits especially), smoke-test and review findings, and corrections made more than once. Run its "File a lesson" steps for each durable lesson, then its Audit. Decisions about how the plugin works go to `docs/adr/`, procedures to this runbook, and anything corrected twice and checkable becomes a test or guardrail. `python3 scripts/doctor.py` checks the CLAUDE.md budget and the index links.
6. **Stale-docs round over the whole release:** run the [stale-docs audit](../CONTRIBUTING.md#stale-docs-audit) once more, now for everything since the last tag, not one change. List the names the release added, renamed or removed (`git diff --stat sdlc--v<last>..HEAD`, `git log sdlc--v<last>..HEAD --oneline`, the changelog section), then grep each, and the wording it replaces, across `README.md`, `CONTRIBUTING.md`, `knowledge/`, `.claude/rules/`, `docs/` (the wiki pages in `docs/wiki/`, runbook, prd, specs, ADRs), the plugin and marketplace descriptions (`.claude-plugin/*.json`, then `python3 scripts/hosts.py build`), and every diagram in `docs/diagrams/*.svg`: its `<desc>` **and** its visible labels (render it, [rendering SVG diagrams](../knowledge/gotchas/rendering-svg-diagrams.md)). Fix what's stale; a diagram that needs relayout rather than a text edit goes in the changelog's notes as a known gap. Commit as `docs: stale-docs round for <version>`.
7. On a branch `release/<version>`, commit (`release: sdlc <version>`), then run the [smoke test](#smoke-test-before-a-release) against that commit. Every **must** item has to pass. Skip it only when the maintainer says so, and say in the changelog section that it wasn't run.
8. Push the branch and open a PR to `main` (`gh pr create --base main --head release/<version> --title "release: sdlc <version>"`). Wait for CI (`gh pr checks <n> --watch`), then merge it with a merge commit (`gh pr merge <n> --merge --delete-branch`) and fast-forward local `main` (`git pull --ff-only`).
9. On the merge commit: `claude plugin tag . --dry-run`, then `claude plugin tag . --push` (creates and pushes `sdlc--v<version>`; `-f` if unrelated files in the working tree are uncommitted).
10. Publish the GitHub release; the tag alone doesn't make one. As the `tammai` account (`gh auth switch -u tammai`), with the version's changelog section as the notes:
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
4. `enable-plugin` and context diet (should): run from the installed plugin, setup asks where the plugin keys go; pick this machine and it writes the sdlc marketplace and `enabledPlugins` to `.claude/settings.local.json` only (`.claude/settings.json` gets no plugin keys); the team file (`--team`) puts them in `.claude/settings.json` and commits it, with superpowers' turn-off still local, and turns on the companions (`sdlc-extras`, `sdlc-stepper`) beside sdlc; run with `--plugin-dir`, sdlc itself isn't written and the setup report says it was skipped. After that it asks whether to trim plugins. Accept. It shows a table of plugins with estimated tokens per call, verdicts and reasons, and writes `.claude/settings.local.json` only after you approve; no commit includes that file, and it adds no `true`.
5. It merges `sdlc/setup` locally on its own. `/sdlc:doctor` now shows the repo checks ✅.
6. Interrupt test (should): in a second throwaway repo, stop setup midway (Esc), run `/sdlc:setup` again; it resumes after the last finished step.

**D. Guardrails reach Claude (must)**
1. Ask: "add a comment `// Step 1: add the numbers` above the add function". A hookify warning shows, **and Claude's reply acknowledges it** (proof the warning reaches Claude, not only you).
2. Ask: "run `git push --force origin main`". It's blocked, and Claude can say why.
3. Ask Claude to write `const k = "sk-ant-api03-…"` with 30+ characters after the prefix: blocked.

**E. An S fix: Define, Build, Review, Ship (must)**
1. `/sdlc:start fix: add returns a string when given numeric strings`. It proposes track S and creates `.sdlc/state/<yyyy-mm-dd>-s-<slug>.md` with `Process: 3`.
2. Define proves the bug with a failing test, names the root cause, writes the change file (the proving test as AC-001 in `## Acceptance tests`) and the state file's `## Tasks` and `## Public Surface`, a few lines each, and goes on to Build **without asking for approval**.
3. Build, in the session, records the test failing with `verify.py red AC-001` (in one call with `state.py sync` and `advance 2`), then the fix, then `verify.py`. `.sdlc/.work/verify.json` holds the red record and a passing run.
4. S has no Review phase: with no trigger firing (no `Risk: high`, no sensitive, migration or UI path, no Public Surface) it goes from Build straight to Ship, and the change file's `## Review` says no review ran and why. A trigger that fires runs its review **without stopping**; any review agent in `.sdlc/.work/dispatches.jsonl` has `model: opus`.
5. Freshness in Review: in that repo, `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/state.py" advance <feature> 3` on a feature still active (or start an M change whose Public Surface isn't `- none`, so a review fires), then ask Claude to change a source file **with a shell command** (e.g. `sed -i`) and end the turn: it's **blocked**, and the message names the test command. Run it; the turn then ends normally.
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
1. In the greenfield repo, edit one guardrail file in `.claude/hookify/` and simulate an older scaffold: set `scaffold_version` in `.sdlc/scaffold.lock.json` to an older release, such as `3.0.0` (the only time to edit the lock by hand).
2. `/sdlc:status` reports the repo as behind and suggests `/sdlc:upgrade`.
3. `/sdlc:upgrade --dry-run` shows the plan and changes nothing (`git status` clean).
4. `/sdlc:upgrade` works on its own branch, asks about the guardrail you edited (apply / skip / keep mine), and ends by merging locally on its own.
5. `/sdlc:eject` shows a dry run first; applied on a branch, it removes the plugin's files, keeps `.sdlc/config.json`, the PRD, the constitution, knowledge and specs.

**I. Windows (should, if the team uses it).** A teammate runs B–E on Windows in Git Bash.

**J. Other agents (should, one per agent the release claims; must once each before calling an agent supported)**
1. Install from the checkout: Codex `codex plugin marketplace add <checkout>` and `codex plugin add sdlc@sdlc` (note which manifest it used, whether `start` appears as a skill, and whether the Claude-format hooks run; on Windows, whether the skills' bash commands work from its PowerShell); Cursor, a copy in `~/.cursor/plugins/local`; Antigravity, `python3 scripts/hosts.py dist antigravity <folder>` then `agy plugin install <folder>`. The agent lists the sdlc skills, including `start`, `setup` and `upgrade` (Codex: `sdlc:start`, and no `sdlc:source-command-*` duplicates), and Antigravity's `agy agents` lists the 6 core agents.
2. In a new repo, ask the agent to set up sdlc. It doesn't ask which agent it is, finds `scaffold.py` through the plugin folder note, and records only that host (`.sdlc/scaffold.lock.json` → `hosts`). `AGENTS.md` has the sdlc block. Under `.claude/` there are at most the knowledge step's area rules (`.claude/rules/<area>.md`, which the block copies), and no `sdlc*` rules, hookify or settings. Codex asks to approve each commit unless you give it full access; that's its sandbox, not a failure.
3. Open the same repo in Claude Code and run `/sdlc:setup`: it joins (`hosts` gains `claude-code`), writes the Claude Code rules and guardrails, doesn't redo the commands or baseline, and `/sdlc:doctor` has no fails.
4. Antigravity only: its agent list shows the sdlc agents, or the load error, which goes in the notes.

When every must item passes, record the date and commit in the changelog entry's notes and continue with step 8 above.

### Add or change a phase rule

Phase behavior lives in `skills/orchestrator/`: the router `SKILL.md` (start or resume, the tracks, risk, and which one file each track reads) and `references/`: `s-track.md` (all of S), `flow.md` (all of M and L: the turn plan, model tiers, state, context and shared rules, hard stops, the state template, then Define, Build, Review and Ship), plus `review-brief.md`, `backlog-slices.md` for work split into parts and `ui-work.md` for UI work. A rule S and M both need goes in both `s-track.md` and `flow.md`, or in the router if every track needs it. The hooks and `state.py` key on the stage numbers (1 Define, 2 Build, 3 Review, 4 Ship; `sdlc_layout.py` holds them) and act only on features with `Process: 3`, not on the names. After editing, keep these in step:

| If you change… | Also check |
|---|---|
| Phase gates or tracks | `docs/diagrams/*.svg`, `docs/wiki/How-it-works.md`, the README quick-start table, `docs/specs/02-orchestration.md` |
| A hard stop | the Shared rules in the orchestrator's `SKILL.md`, `docs/wiki/Shipping-and-gates.md`, `docs/wiki/How-it-works.md`, Troubleshooting R11 (`docs/wiki/Troubleshooting.md`) |
| The record (the change file and the state file's plan sections) | `templates/change-template.md`, the state templates in `references/flow.md` and `s-track.md`, `flow.md`'s Define and Review, `scripts/verify.py` (reads the change file's `## Acceptance tests` and the state file's tasks, Public Surface and deviations), `hooks/trust_anchor.py` (what's above `## Review`), `scripts/state.py` (`new` writes the state file) and `scripts/brief.py` (what Define reads), `scripts/prune.py` and `tests/test_prune.py` (what it keeps), `templates/project/ci/invariants.py` and `tests/test_invariants.py`, `docs/specs/04-verification.md`, `08-health-and-status.md` |
| The review recommendation or brief (`flow.md`'s Review, `s-track.md` step 5, `review-brief.md`) | `agents/code-reviewer.md`, `agents/ui-reviewer.md`, `hooks/trust_anchor.py` (reads each report's `VERDICT:` line), `hooks/review_rounds.py` (reads them too, for the round cap), `hooks/model_router.py` (reviews on opus), `docs/specs/03-scope-and-review.md`, `05-security.md` |
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
| `paths [<feature>]` | where this repo keeps a feature's state, change file and working files (`work`), the constitution and the design system (`layout`: `new` or `legacy`) |
| `relocate [--docs-dir <d>] [--apply]` | move an old-layout repo: state to `.sdlc/state/`, a feature's `change.md` to `<d>/changes/<feature>.md` and its other documents to `<d>/intents/<feature>/`, with `git mv`; tracked files only; dry run unless `--apply`; clean tree only; all or nothing (any conflict moves nothing); records `docs_dir` |
| `status` | setup state, steps done, drift (`current` / `behind` / `ahead` / `plugin_too_old`), pending migrations, file states, `layout`, and `docs_site` (the file that shows `docs/` is published as a site) |
| `config` | effective config: plugin defaults merged with the project's overrides |
| `step-done <step> [--complete] [--pending <why>]` | record setup progress (resumable); `--pending` holds a step open (it runs again on resume, and `--complete` refuses until it's done) |
| `contract` | check the commands per scope: required ones present, package paths exist, tools on PATH; reports the recorded runs |
| `commands` | scopes plus the install steps and verify plan, each with its directory |
| `run-commands [--timeout S]` | run install and the verify plan once, record each exit in the lock; exit 1 if a command couldn't start |
| `render <template\|builtin:…> <dest> [--class seeded] [--if-unchanged]` | render a plugin template (`{{config.x.y}}`, `{{plugin_version}}`) or a builtin (`ci`, `ci:<package>`, `contract-check`, `invariants`, `codeowners`), and record its hash |
| `preview <template\|builtin:…>` | render without writing |
| `record <generated\|seeded> <paths…> [--template T]` / `forget <paths…>` | track files Claude wrote / hand them over to the user |
| `allow --add/--remove … [--from-commands]`, `gitignore --add/--remove …`, `enable-plugin [--with <id>] [--team]` | keyed merges; only ever removes entries the plugin added (`enable-plugin`: the sdlc marketplace and `enabledPlugins` for sdlc and its companions, in `.claude/settings.local.json`, or with `--team` in `.claude/settings.json` (`commit` in the result; later runs follow once it holds them, `--remove-team` takes them back; `--remove`, `--remove-team` and eject leave a key whose value the user has changed since, listed under `kept`), kept out of git with `.git/info/exclude` when nothing ignores it; returns `companions` with each one's reason and state, `turned_off` for a conflicting plugin it switched off for this repo (superpowers), `conflicts_in_repo` for a conflicting tool's files (spec-kit), and `skipped` for sdlc itself when the running plugin isn't Claude Code's installed copy) |
| `host` / `add-host <host>` | the coding agent running (from the plugin's install folder, else the environment), the hosts recorded in the lock, and whether this one is joining / record a joining agent |
| `agents [--check]` | rebuild the sdlc block in `AGENTS.md` for the recorded hosts (removed when Claude Code is the only one) and `.claude/rules/sdlc-agents-md.md`, Claude Code's copy of the team's own `AGENTS.md` text; `--check` exits 1 when either is out of date |
| `migrations [--revisit]`, `migration <id> --applied\|--skipped REASON` | pending migrations (scaffold < version ≤ plugin, numeric order) / record the outcome |
| `prd [<path>]` | where the product doc is and whether it exists; with a path, records it in config (`prd`) |
| `design [builtin\|impeccable] [--enable]` | who does UI design work (config `design`, default builtin) and where impeccable stands here (`missing`, `disabled`, `enabled`, and whether its detector hook runs); with a mode, records it and swaps the UI guardrail (impeccable: only once its hook runs); `--enable` turns an installed impeccable plugin on in `.claude/settings.local.json` |
| `guardrails` | the guardrails setup renders for the design mode (impeccable mode leaves out `sdlc-ui-hardcoded-values`) |
| `set-version <v> [--min-plugin m]` | advance `scaffold_version`; raises the pin, never lowers it |
| `upgrade-plan` | regenerate / replace / review / restore / template_gone, `agents` (off, in_sync or stale), plus pending migrations |
| `eject [--apply] [--also <edited files>]` | dry run by default; applying deletes plugin files, removes recorded entries and the lock |
