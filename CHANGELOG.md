# Changelog

Versions follow the `version` in `.claude-plugin/plugin.json`. Repos record the version they were set up or upgraded with; `/sdlc:upgrade` brings them forward.

## Unreleased

No migration: `/sdlc:upgrade` regenerates an unedited `sdlc-verify.yml` and `.sdlc/ci/invariants.py`, which a brownfield repo needs for the CI baseline waiver. Keep the two together: a regenerated workflow with an edited, older `invariants.py` fails a red run with an `unrecognized arguments: --baseline-tests` error.

### Changed
- **A brownfield repo's CI passes when only baselined tests fail.** When `sdlc-verify.yml` is generated while `.sdlc/baseline.md` lists a failing test, its test step tees its output. A red run is handed to `.sdlc/ci/invariants.py --baseline-tests`, which passes it only when every failing test the runner names is listed. It matches names by the same rule as `ship.py --waive-baseline`. Before, every PR was red from the start (3.15.0 known issue).
- **Guarded changes see more** ([ADR 0032](docs/adr/0032-opt-in-guards.md)), with `guards.dependencies` or `guards.lint_config` on.
  - A changed dependency source is an item: an index URL or `-e` line in a requirements file, package.json's `overrides`, `resolutions` and `pnpm.overrides`, go.mod's `replace`, Cargo's `[patch.*]` and `[replace]`, and `.npmrc`, `.yarnrc*`, `pip.conf` and `pip.ini`.
  - More suppressions count: `# ruff: noqa`, `# flake8: noqa`, `# mypy: ignore-errors`, pyright file-level settings, `/* eslint <rule>: … */`, `oxlint-disable` and `deno-lint-ignore`.
  - `dev-requirements.txt`, `requirements.in` and an inline `optional-dependencies = { dev = [...] }` table are read.
- **The plugin's own test suite runs in parallel** (maintainers only, nothing changes in projects). `tests/run_parallel.py` runs the same tests as `unittest discover` on every core, one job per test class, with a private temp, plugin-data and security-state folder per worker: 953 tests in about 100 s on a 16-core Windows machine, against about 12 minutes one at a time. CI and the runbook use it.

### Fixed
- **Plan approval holds against a hand-edited track and a re-created feature** ([ADR 0031](docs/adr/0031-approval-policy.md)).
  - Under a policy that covers some track, `state.py new` writes an `Approval floor:` line into the state file.
  - `set Track` raises the floor at any stage, and at Define takes back an approval of the smaller plan. Only an approved downsize lowers it.
  - The approval check takes the stricter of the floor and `Track:`, so editing `Track:` from M to S no longer skips the stop under `approval: ml`.
  - A feature started before the policy has no floor and is judged by its track, as in 3.16.
  - A feature deleted by hand and re-created under the same name no longer inherits the old approval.
  - Any approval is used up when the feature leaves Define, so a feature sent back to Define needs a new one.
- **A dialog Approve from a workbench's app repo counts.** In a session started in an app repo with its own `.sdlc`, the question is now recorded when the feature waits at the workbench.
- **`scaffold.py approval`, `checks` and `guard` report what this session's scripts read** when the session covers `--root` (a nested repo included), and `--root`'s own config otherwise. Before, they always read `--root`'s own gate.
- **UI evidence** (`guards.ui_evidence`):
  - In a workbench, an app repo's own `areas.ui` now counts for its files, beside the workbench's.
  - A git failure inside the check reports `ui_evidence_not_checked` instead of `git_failed`.
  - ADR 0032 now says a deleted UI file counts as a UI change.
- **Setup asks the monorepo's profile and the solo or shared checks as two questions**, inferring neither from the other. A small team is `lean` and shared.
- **Guarded changes:**
  - A file moved with `mv`, not yet staged, no longer has its suppressions flagged again.
  - A Base manifest that can't be read flags each dependency by name instead of one "unreadable" item.
  - An Allow whose question excludes something (`all except …`) allows nothing.
  - An Allow covers another feature's item only when the question names that feature.
  - An error anywhere in the check reports `guarded_not_checked` instead of a traceback.

## 3.16.0 — 2026-11-24

No migration: every new config key (`approval`, `guards`) keeps 3.15's behaviour when absent, a trust-anchor record from 3.15 stays valid, and `/sdlc:upgrade` regenerates the changed templates. A team turns the new checks on with `/sdlc:setup checks shared`.

Checked on 2026-11-24 at commit 8267bf9, on Windows 11:
- **Tests:** the full suite (906 tests, 9 skipped, Python 3.10), `claude plugin validate .` and `hosts.py check`.
- **Smoke test:** run in real headless sessions loading the checkout with `--plugin-dir`, in four groups at once (A+B; C then E and H in C's repo; G; K). Every must item passed. The new C9 (solo or shared), E12 (plan approval) and E13 (guarded changes) passed too.
- **Out of scope:** D and F, since the release doesn't touch the guardrails or the security hooks.
- **Not run:** C4's installed-plugin and `--team` variants, C6–C8, E8 and E9.
- **How the dialogs were checked:** a headless session has no question tool, so `Approve plan`, `Allow change` and the trust-anchor dialogs were answered as typed replies. Their rendering wasn't seen; the hooks and scripts behind them were.

### Known issues
- **The layer diagram (`docs/diagrams/sdlc_plugin_layers.svg`) still shows 3.1's hooks and commands**; the plan-approval and guarded-changes hooks need a relayout, not a text edit.
- **A brownfield repo's generated CI fails while its baseline lists a failing test** (carried over from 3.15.0).
- **Smoke-test notes (should).**
  - Setup in a repo with no commits renames `sdlc/setup` to `main`.
  - A `rules.plan` line can leak words into a task's Files line.
  - The 3.6.0 migration asks for the deploy target when config already has one.
  - Eject leaves `.sdlc/state/*.json` and `*.events.jsonl` untracked.
  - `state.py repo` in a workbench with no commits says it isn't on a branch.
- The open items from this release's reviews (hardening of the guarded-change detection, an approval in a workbench session started inside an app repo) are listed in `.sdlc/todo.md`.

### Added
- **UI evidence and solo or shared checks** (`/sdlc:setup guard ui-evidence on`, `/sdlc:setup checks shared`, part 4 of [#92](https://github.com/tammai/sdlc/issues/92)). With UI evidence on, Ship needs screenshots (or a manual reason) for a change touching your UI and lists them in the PR. Setup now asks whether the repo is solo or shared; shared turns on plan approval for every M and L and every guard at once.
- **Guarded changes** (`/sdlc:setup guard dependencies on`, `/sdlc:setup guard lint-config on`, [ADR 0032](docs/adr/0032-opt-in-guards.md), part 3 of [#92](https://github.com/tammai/sdlc/issues/92)). With them on, verify fails on a new dependency, a changed lint or type config, or an added suppression comment (`@ts-ignore`, `eslint-disable`, `# type: ignore`, …) until you allow it in the `Allow change` dialog or by typing `allow`. An allowed dependency gets the dependency audit in Review, and Ship writes what you allowed into the record. Off by default.
- **An opt-in test lock on S** (`/sdlc:setup guard s-tests on`, [ADR 0032](docs/adr/0032-opt-in-guards.md), part 2 of [#92](https://github.com/tammai/sdlc/issues/92)). With it on, an S feature's red step locks its test files as on M and L, so a test weakened afterwards fails verify until the change is recorded with its reason and a red run at Base. Off by default; turning it off is shown by the trust anchor.
- **Plan approval for teams** (`/sdlc:setup approval ml|always`, [ADR 0031](docs/adr/0031-approval-policy.md), part 1 of [#92](https://github.com/tammai/sdlc/issues/92)). Under `ml` every M and L waits after Define for your approval, and L no longer approves itself; under `always` S does too. Answer the `Approve plan` question with Approve (or type `approve <feature>` where there's no dialog): until then `state.py advance 2` refuses, so no test or code is written, and autopilot blocks the part. The Gate log records who approved. The default, `high-risk`, keeps today's flow; a move to fewer stops is shown by the trust anchor.

### Changed
- **A review agent dispatched without a model is told to use `model: opus`.** The model router's refusal used to list the tiers, so an agent often retried a review on sonnet and was refused again; it now names the one model a review takes.
- **Learn reads as what it is: a judgment, not a gate** ([#96](https://github.com/tammai/sdlc/issues/96)). The change file's `Lessons filed` line may say `None` or be left out when nothing was learned, the Ship gate reads "Learn considered", and `knowledge/log.md` is optional in `managing-knowledge`; no script checks either, and the flow, template, releaser agent and specs 02 and 07 now say so instead of reading as required.

## 3.15.0 — 2026-11-23

No migration: every new config key (`mode`, `skip`, `team`, `done`, `storybook`) keeps 3.14's behaviour when absent, and `/sdlc:upgrade` regenerates the changed templates.

Checked on 2026-11-23 at commit 6b51ad3, on Windows 11: the full suite (883 tests, 9 skipped, Python 3.10), `claude plugin validate .`, `claude plugin test plugins/sdlc-stepper` (26 tests, now passing on Windows too) and `hosts.py check`. The smoke test ran in real headless sessions on Windows 11, loading the checkout with `--plugin-dir` (the installed sdlc turned off per test repo), in five groups at once against 6831c71: A+B, C then D, E and H in C's repo, F, G and K; every part was in scope. Every must item passed. K2, K4 and K5 passed again at caf3b57 after their fixes. Should items: F1 passed; F2 ran only its no-credentials branch (see Known issues); the new D4 (advisory), E12 (Definition of Done), E13 (skip pr) and K5 (a flipped repo stays guarded) were added and pass. Not run: C4's `--team` and installed-plugin variants, E8's L change with an Avoid word, E9, and H6's regenerated `invariants.py`. The smoke test's other findings were fixed test first in this release (each listed under Fixed) or are under Known issues. Cursor on Windows was checked live with headless cursor-agent 2026.11.22 (and 2026.10.22 in WSL); the desktop app wasn't.

### Known issues
- **A brownfield repo's generated CI fails while its baseline lists a failing test.** `sdlc-verify.yml` runs the repo's own test command, which has no way to skip the baselined tests; locally, `ship.py --waive-baseline` lets them through.
- **sdlc's turn-end, commit and push reviews get no credentials when you sign in with `/login`** on some machines (seen on Windows, in 3.14.0 too): the hooks say once a week that the review isn't running. An `ANTHROPIC_API_KEY` in the environment turns them on.

### Added
- **Team mode** (`/sdlc:setup team on`). An M or L feature's stages run as role agents, each starting fresh from the record, with the main session as their coordinator: `sdlc:analyst` writes the change file (on opus), `sdlc:builder` builds and fixes review findings, the reviewers review, `sdlc:releaser` ships. The role guard holds each to its files: the analyst writes only the record, the builder never the change file's criteria, a reviewer's report or the state file, the releaser no product code.
- **Storybook as an opt-in living design system** (builtin design mode). `scaffold.py storybook on` (setup's design step) makes the stories the component catalog: each component a change touches gets a story for every state the spec names, the UI review treats a component without a story as off-system, and an optional `commands.storybook` runs in verify after `build`. Doctor warns when it's on with no `.storybook/` (the root's or a package's), in impeccable mode, or when a custom `verify.order` leaves it out; a Storybook build's `storybook-static/` is never drift, committed by Ship, or sent to the security reviews.
- **A Definition of Done.** Setup asks for the team's own bar (a changelog line, docs updated, a migration note…), up to 10 items, as config `done` (`/sdlc:setup done`). Every change carries it as a checklist in its change file, each item ticked with its evidence, and `ship.py` won't proceed while one is open; the trust anchor shows a change to the list.
- **Advisory mode and configurable steps** ([ADR 0030](docs/adr/0030-modes-and-skips.md)). Setup now asks first whether a repo runs sdlc in **full** or **advisory** mode. Advisory gives the skills and agents as aids: every hook, gate and guardrail stays silent, except a workbench's read-only guard, and the orchestrator does what you ask without running its flow. A full repo can skip named steps with `/sdlc:setup skip security-review|code-review|ui-review|pr`; a skipped review is recorded in `## Review`, and `pr` ends Ship after the local commit. Define, tests and verify are never skippable. The trust anchor shows any change toward fewer checks for your confirmation; the session status line names the mode. Reading the mode never waits on a FIFO, and the reply that accepts a new mode or skip tells the agent at once.

### Security
- **Workbench: a read-only repo made writable in `workbench.json` stays read-only until you accept it.** The per-call write guard now follows the read-only watch's record, not only the edited file, so `"write": true` no longer lets writes through before your `accept read-only <repo>`.
- **A committed lock can't make an upgrade copy a file from outside the plugin.** `.sdlc/scaffold.lock.json` names each file's template, and an upgrade renders it without asking: an absolute, `../` or linked template path read any local file (an SSH key, a token) into the repo. A template is now only one of the plugin's own (a known `builtin:`, or a path under its `templates/` that resolves inside it), checked on the lock and on `render`, `record` and `preview`; and nothing is recorded, rendered or deleted in a `.git` folder, written or reached through a link, Windows aliases included.

- **A Monitor command meets the workbench's read-only guard.** The Monitor tool runs a shell command, but only Bash and PowerShell calls were checked, so in a workbench a Monitor command could write a read-only repo, an app repo no feature had branched, a recorded acceptance test, or the read-only watch's files. It is now judged as a Bash command.

- **A committed link can't make setup write into `.git` or outside the repo.** `AGENTS.md`, `.gitignore`, `.claude/settings.json` and `.claude/settings.local.json` are merged by their fixed names; a committed link (`AGENTS.md -> .git/config`, `.claude -> .git/info`) had sdlc append to the file it named, and read an outside file's text into the repo. Those files are now refused when they lead out of the repo or into a git dir, and read as absent wherever sdlc only reads them (doctor included); a `CLAUDE.md` or `.claude/rules/*.md` linked out of the repo is left out of AGENTS.md's block. A link inside the repo still works, and eject lists such a file under `outside` and leaves it.

- **A committed link can't make sdlc read a file outside the repo.** Doctor, the scripts' config and lock (`scaffold.py` now refuses them, exit 1), the hooks' config and `workbench.json` readers, and the AGENTS.md block skip or name a committed file that links out of the repo or into `.git`, so it can't hang them (`CLAUDE.md -> /dev/zero`) or put its text in a report. A broken or looping link, or a folder, at such a name is a warning, not a traceback.
- **A committed glob can't stall the commit review or doctor.** The security areas in `.sdlc/config.json` and a rule's `paths:` were turned into regexes that backtracked for minutes on `*a*a*a…` or a long brace list; the same globs are now run as a small automaton, in time linear in the path, with exactly the old meaning.
- **The `.git` checks catch `.g\u200cit` and `.GIT`.** The code points HFS+ ignores, and case on macOS, no longer let a path through.
- **A generated lock entry never overwrites or deletes a file git doesn't track.** An upgrade offers it for review and eject asks, when a local file such as `.env` differs from the lock.
- **Workbench: editing `workbench.json` or the workbench config can't switch the guards off unnoticed.** A read-only repo made writable or removed is reported, and blocks the end of the turn, until you accept it; once sdlc has looked, `"workbench": false` leaves the guards, the watch and the app review on.
- **Workbench: a recorded PR doesn't end the review of an app repo's commits** while the repo is on the feature's branch, and the turn-end security review now covers an app repo's uncommitted change.
- **The read-only guard denies shell syntax it knows it reads differently from the shell** (ANSI-C quoting that ends apart from `'…'`, a substitution inside `$(( ))`, zsh's `>!` and `>>|`, a `#` after an escaped delimiter), instead of letting a write hide in it. It remains a seatbelt: other spellings can still get past it (docs/wiki/Limitations.md), and the read-only watch reports what changed.
- **A Monitor command can't commit or push:** run those with Bash, where the commit and push security reviews run.
- **A Monitor command meets the review-cap hold and the read-only watch's per-call check**, as Bash does.

- **Workbench: a done feature keeps the commit review on its app repos until its branch is merged upstream**, on any branch and whatever PR is recorded. A high-risk done feature stays reviewed beside a new one.
- **Workbench: a turn run from the workbench root gets the turn-end review in the app repo it edited**; before, no app repo was reviewed. The root keeps it when its own edits lead or touch steering files.
- **Every `.git` check shares one rule** (case, trailing dots and spaces, NTFS stream suffix, 8.3 name, HFS+ code points).
- **The Monitor deny uses the commit and push reviews' own patterns**, and stays on if they can't load.
- **Workbench: a done feature's branch deleted after its merge ends its review of the app repo**, judged by the branch's last tip in HEAD's reflog; a subagent's turn-end review at the workbench root reviews the app repo it edited instead of skipping; the ownership check looks up the remote's default branch once, however many done features there are.
- **Workbench: the turn-end review covers every repo a turn edited with the edit tools**, in one review call (each file named by its path from the session's folder), not only the one with the most edits; when that one has nothing to review, the others still are. A finding the agent left on unchanged code isn't raised again when a rewake re-sends that repo.
- **The deploy runbook path is barred from `.claude` and `.sdlc` at any depth** (a nested package's, or an app repo's in a workbench), not only at the top. It is never an agent's instruction file (`CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md`), since `/sdlc:deploy` appends to it, nor a name with a control or format character.
- **`.claude` and `.sdlc` are barred from the deploy runbook and objects paths in every spelling `.git` is** (8.3 short name, NTFS stream suffix, HFS+ code points), not only by case and trailing dots.
- **impeccable's machine-local `config.local.json` is never read through a link** out of the repo or into `.git`, at the file or its `.impeccable` folder, like its committed `config.json`. Doctor and `/sdlc:setup design` name such a file and say to replace the link, instead of advising `/impeccable hooks on`.

### Fixed
- **`ship.py --waive-baseline` refused for another failure names everything to fix**: it no longer says to rerun with the flag you gave, and it still names a failing test `.sdlc/baseline.md` doesn't list.
- **sdlc's working folder is ignored from setup's first step**: a `.sdlc/.work/` a hook creates ignores itself, so setup's early commits no longer take its record (`trust-anchor.json`) before the gitignore step.
- **Doctor names the mode, and an advisory repo passes.** A `mode` row shows full (with any skipped steps) or advisory; in advisory, missing commands and guardrails are expected, not failures.
- **`- None` under `## Avoid` in `objects.md` means nothing to avoid**, instead of an Avoid line `/sdlc:setup objects` couldn't enable.
- **A note after a task's file stays with it:** `--task "… | src/x.test.ts (test)"` no longer lists `(test)` as a file.
- **Workbench: `accept read-only` says when sdlc's scripts refuse the manifest it accepts**, such as a non-app repo made writable.
- **`/sdlc:status` doesn't count runtime files of features on another branch** as features or as an outdated scaffold.
- **Workbench: an app repo with stray files tells the agent to ask you.** `state.py repo` names the uncommitted or untracked files (a `__pycache__` folder) and says to ask you to commit, remove or ignore them, since sdlc holds writes there until the feature branches it; before, it told the agent to clean up, which the guard then denied.
- **Cursor's hooks run on Windows.** Cursor runs a hook command there through Windows PowerShell, where `python3` is often missing or the Microsoft Store stub, so every sdlc hook did nothing. The command now reads in both sh and PowerShell; on Windows it runs the first working `python3`, `python` or `py -3` and hands it the event.
- **The background Agent SDK install no longer runs in your project folder.** On Windows, a folder a running process sits in can't be deleted or renamed, and the install can take minutes; it now runs in the plugin's state folder.
- **Eject removes a linked `.sdlc/.work` as a link** instead of crashing after the lock was gone.
- **`.impeccable/config.json` is never read through a committed link**, and an upgrade or eject never overwrites an untracked file in a project below the git toplevel or opened through a link.
- **`accept read-only` names the repos it stopped watching.**
- **Upgrade and eject keep a file you merged.** After an upgrade's "apply merge", the next upgrade replaced the file with the template and eject deleted it without asking, since the merge was recorded like a plain render. A merged file is now reviewed only when the template changed since, asked about on eject, and never overwritten by `render --if-unchanged`.
- **Commits and pushes through PowerShell get the commit security review.** On Windows, where Claude Code runs commands in its PowerShell tool, they were never reviewed.
- **A folder named `..something` is inside the project.** The freshness hook and the turn's security-review diff treated `..hidden/` as outside it.
- **`/sdlc:setup review-rounds <n>` during a feature no longer commits on the default branch** (3.14.0 known issue): the step reads the active feature from the session status line and leaves the change for the feature to ship.
- **Eject names a linked file only when it has something to unmerge**, and a folder at a recorded file's path counts as edited instead of crashing `status` and `upgrade-plan`.
- **The read-only watch takes back a change you accepted and then undid**, silently, when the repo is back to how sdlc first saw it.
- **sdlc-stepper doesn't mark a failed merge done.** A `gh pr merge` that fails (a red check, a conflict) now leaves the bar at Ship; before, any `gh pr merge` command showed `Ship · done` until the next prompt.

### Changed
- **sdlc-stepper finishes Ship when CI passes.** Once `gh pr checks` passes at Ship the bar checks all four stages (`Ship · CI passed`; nothing pulses on the desktop), a failed merge reads `Ship · merge failed`, and in a workbench a feature another session ships gives way to the older active one.

## 3.14.0 — 2026-11-21

No migration: repos without the key keep two rounds; `/sdlc:setup review-rounds` sets it.

Checked on 2026-11-21 at commit 5e4f10d: the full suite (698 tests, 5 skipped, Python 3.10), `claude plugin validate .`, `claude plugin test plugins/sdlc-stepper` (22 tests) and `hosts.py check`. The smoke test ran in real sessions on macOS under tmux, loading the checkout with `--plugin-dir`, in three groups at once (about 17 minutes). A and B passed: `/plugin` listed sdlc 3.14.0, and doctor gave only the "not set up" warning. C, E and H passed every must item, run because the release touches setup, `scaffold.py`, the orchestrator and two hooks. Two new checks passed: setup's `review-rounds` question recorded the answer (3) in config; and `/sdlc:setup review-rounds 4`, typed mid-feature, set config and the feature's ceiling to 4, while `review-rounds 9` was refused with nothing changed. The stepper check passed: the bar went from `Review` to `Ship`, then to `✓─✓─✓─✓ · Ship · done` on a `gh pr merge`, and was gone at the next prompt. D, F, G and K didn't run, since the release touches none of what they cover. J didn't run, since no new agent was added. The desktop band wasn't checked.

### Known issues
- sdlc-stepper marks a ship done when a `gh pr merge` command runs, from its text: a merge that then fails still shows `Ship · done` until the next prompt.
- `/sdlc:setup review-rounds <n>` typed during a feature can lead the agent to commit the config change on the default branch (it misjudged the feature as not active in the smoke test). The cap itself applies correctly; commit the config change on the feature branch instead.

### Added
- **Configurable review round cap.** How many review rounds run before the review-rounds hook stops for you is now `review_rounds` in `.sdlc/config.json`, 2 (the default) to 5. Setup asks for it, and `/sdlc:setup review-rounds` (`scaffold.py review-rounds <n>`) changes it at any time. Since the cap is a safety stop, a lower value applies at once; a higher one applies to features started after it is committed, or at once when you type `/sdlc:setup review-rounds <n>` with the number (the hook writes it into config): a value the agent writes mid-feature can only lower it, and once lower it stays lower for that feature. Any other value counts as 2.

### Changed
- **sdlc-stepper marks a merged ship done.** When the session merges the shipped feature's PR (`gh pr merge`), the bar checks all four stages and reads `Ship · done`, and the next prompt clears it. Before, it stayed at `Ship` with Ship in progress until `/clear`, a restart or the next `/sdlc:start`, though the work was finished. A PR merged on GitHub isn't seen, so that case is unchanged.

## 3.13.1 — 2026-11-20

No migration: the fix is in sdlc-stepper, which updates with the plugin.

Checked on 2026-11-20 at commit e5361eb: `claude plugin validate .`, `claude plugin test plugins/sdlc-stepper` (20 tests), the marketplace and hosts tests and `hosts.py check`. The full suite last ran on the fix's branch (675 tests, 5 skipped, Python 3.10). The smoke test ran in real sessions on macOS in Claude Code 2.1.329 under tmux, loading the checkout with `--plugin-dir`. A and B passed: `/plugin` listed sdlc 3.13.1, and `/sdlc:doctor` and `doctor.py` gave no failure, with the "not set up" warning and its fix. A new check for this release passed too: in a session showing a feature at Review, the bar read `✓─✓─✓─● · Ship · PR` once its state file went to done at Stage 4, it was gone after `/clear`, and a fresh session showed nothing for that feature. Parts C–H and K didn't run, since the release touches only `plugins/sdlc-stepper/`. J didn't run, since no new agent was added. The desktop band wasn't checked.

### Fixed
- **sdlc-stepper shows the Ship stage.** `ship.py` advances a feature to Stage 4 and sets `Status: done` in the same run, and the bar only read active features, so it disappeared just as Ship began and never showed Ship. Now the feature the bar was showing stays on it at Ship, through the commit, the PR and CI. A feature shipped before the session started still isn't shown, and neither is one after `/clear`. `/sdlc:start` or a `Define · …` line replaces it with the next feature's Define, or with an older active feature being resumed.

## 3.13.0 — 2026-11-19

No migration: the new hook ships with the plugin and needs nothing in projects.

Checked on 2026-11-19 at commit 5a84c5f: the full suite (675 tests, 4 skipped, Python 3.10), `claude plugin validate` and `hosts.py check`. The smoke test ran in real sessions on Windows in Claude Code 2.1.328, loading the plugin with `--plugin-dir`, in two groups: A+B, and E (after `/sdlc:setup` in E's repo). Every must item passed, including the new E11: after the third identical failure, the stuck-turn note reached Claude, which then loaded `sdlc:systematic-debugging`. E8–E10 passed too. One E6 clause wasn't observable: the machine had no API credentials, so the commit security review exits before the skip-and-record path; that code is unchanged since 3.12.0. Parts C, D, F, G, H and K didn't run, since the release touches none of what they cover. J didn't run, since no new agent was added.

Known issues (should):
- After an M change with a committed `graphify-out/graph.json`, the session's `graphify-out/cache/` was left untracked, so `git status` wasn't clean after Ship.
- When Claude Code adds its attribution trailer, the agent's first `git commit -F .sdlc/.work/commit-msg.txt -m …` fails ("options '-m' and '-F' cannot be used together"), and it recovers with a second message file.
- With `--plugin-dir`, setup skips sdlc itself but turns on the installed `sdlc-extras` and `sdlc-stepper` in `.claude/settings.local.json`.
- On Windows, every session prints "Language server plugin:sdlc:typescript couldn't start" (seen before this release).

### Added
- **A Build turn that keeps failing the same way gets one nudge.** The new stuck-turn hook watches failed shell calls in Build: the same command failing the same way three times in one turn adds one note telling the agent to stop retrying and use `sdlc:systematic-debugging`. It never blocks, and stays silent outside Build, under the review round cap and in subagents. Claude Code only. The idea comes from microsoft/TokenEconomizer's failure-loop guard.

### Docs
- The host gotchas list what TokenEconomizer reports about Codex, Cursor and Antigravity hooks, and the wiki's Limitations page has a tested-versions table.

## 3.12.0 — 2026-11-17

No migration: `objects` is an optional config key, off by default; `/sdlc:setup objects` turns it on.

Smoke test passed on 2026-11-17 against 94f1605, with part C rerun on the fix for C3 (`dac9743`'s first round). Parts A, B, C, E, G and H ran in three groups (A+B; C then E and H in C's repo; G). D and F didn't run: the release touches no guardrail template or security hook. K didn't run: no workbench code changed. J didn't run: no new agent. A ran with `--plugin-dir`. C3 failed at 94f1605: on Windows the setup session's shell loop over `scaffold.py guardrails` picked up a `
` on each path, every render failed unseen, and `.claude/hookify/` stayed empty while setup and doctor said ok; fixed under Fixed below, and the rerun wrote all 15 guardrails through `guardrails --render` with doctor's new row ok. The new checks passed: `/sdlc:setup objects` showed objects and wrote nothing before approval, then a file that passes the check, `"objects": true` with the other keys, one commit and a local merge, and `--enable` was refused in a repo whose setup wasn't finished (C8); the brief's `objects:` section, `objects.py check <f>` stopping an L change on an avoided name, and doctor's `objects` row (E8); eject kept `objects.md` (H5); in a brownfield repo `scaffold.py objects` listed the sample's model and type files and no tests (G). C6, C7 and E9 (should) didn't run; E7 ran its `--json` half.

Known issues (should):
- In a live headless L session, the agent edited the user's `objects.md` (dropped an Avoid line, added an object) to get past Define's gate rather than asking; D2 makes a new object the owner's call, but the Avoid list isn't named in it.
- In a brownfield repo whose only failing test is in the baseline, Build's gate passes with `state.py advance 3 --gate pass` and no verified record (seen since 3.9.0).
- On Windows with `core.autocrlf=true`, a checkout that rewrites a locked test file with CRLF makes `verify.py` report `test_lock_changed` (since 3.10.0; not exercised this time).
- On M in Claude Code, the built-in `code-review` skill doesn't read `review-brief.md`, so the objects file's `DR` rules aren't checked there (spec 13 O9).
- `brief.py` prints the PRD at config's `prd` path, which is checked by its spelling only.

### Fixed
- **Setup writes every guardrail itself.** On Windows, setup's guardrails step could leave `.claude/hookify/` empty: the agent looped over `scaffold.py guardrails` in the shell, a carriage return (`\r`) on each path failed every render unseen, and doctor said ok. `scaffold.py guardrails --render` now writes them all in one call (keeping ones you edited or declined), setup uses it, and `/sdlc:doctor` warns when a finished setup's guardrails were never written.
- **The brainstorm companion is branded sdlc.** The browser page `sdlc:brainstorming` opens showed "Superpowers Brainstorming" and a Superpowers header; it now says sdlc, with sdlc's version, and credits Superpowers (MIT), whose code it is.

### Added
- **An opt-in domain model** (spec 13, ADR 0028). With `"objects": true` in `.sdlc/config.json`, `<docs>/objects.md` (from `templates/objects-template.md`) says what the product's things are: each object's UI name, code name, states, actions and how it's shown, the rules it obeys (`DR-001` onward) and the names to avoid. `brief.py` prints it for Define, which uses its names and states and asks you before adding or renaming an object or changing a rule. `scripts/objects.py check [FEATURE]` runs in Define's gate: it fails on a missing file, an undeclared state, a duplicate or avoided object name or a bad `DR` id, warns on a long file or missing UI fields, and on an avoided name in the ACs warns on M and fails on L. Review checks each `DR` rule like a must-never-break line; doctor gets an `objects` row that also warns about an object whose code name is in no tracked file. Off by default; a spec-backed repo's brief points at rspec's `domain.md` instead. `/sdlc:setup objects` drafts the file with you from the PRD or the code's schema, types and routes, in approved batches, and turns it on (`scaffold.py objects --enable`, which refuses until the file passes the check, and in a spec-backed repo); eject keeps the file. With the model on, UI work maps each object to its `Shown as` component and actions, and the UI review rates a wrong component, an unlisted action or another name Medium. Measured before the UI layer and setup step were built: over five changes to one product, objects on used 0.84x the tokens of off and kept one name per object where off drifted to two (spec 13).

## 3.11.0 — 2026-11-17

No migration: `living_spec` and `rules` are optional config keys, and `.sdlc/ci/invariants.py` is generated, so `/sdlc:upgrade` offers the new one.

Smoke test passed on 2026-11-17 against 077b799, with H4 rerun against b4cffee. Parts A, B, C, E, G, H and K ran in four parallel groups (A+B; C then E and H in C's repo; G; K), about 20 minutes, set by the C→E,H group. D and F didn't run: the release touches no guardrail or security-hook file. J didn't run: the release claims no new agent. A ran with `--plugin-dir`, since the installed marketplace is also named `sdlc`; `sdlc-extras` and `sdlc-stepper` loaded from the installed 3.10.0 copy, so only their version bump went untested. The new checks passed: `doctor.py`, `verify.py`, `ship.py` and `invariants.py` print one JSON document with coded `problems` and a `fix` (`ship.py` in a workbench names `repo_not_ignored` and `workbench_invalid`); a `rules.plan` line reached the brief and the plan; with `living_spec` on, an M change's `## Capabilities` became `docs/sdlc/capabilities/<name>.md` in Ship's commit; a committed `graphify-out/graph.json` put the graphify section in the brief and an edit to it wasn't drift; eject kept `<docs>/capabilities/`; upgrade replaced the old `invariants.py` with one that takes `--json`. H4 failed twice at 077b799: `/sdlc:upgrade` chose "skip this time" itself for an edited guardrail and merged, the second time with a template that had really changed. After the fix under Fixed it asked about both edited guardrails, stopped before any commit, and merged only after the answer.

Known issues (should):
- On Windows with `core.autocrlf=true`, a checkout that rewrites an unchanged locked test file with CRLF makes `verify.py` and `ship.py` report `test_lock_changed`: the test lock hashes raw bytes (CI's `invariants.py` accepts either line ending). Since 3.10.0.
- In a brownfield repo whose only failing test is in the baseline, `verify.py` doesn't record a pass, and Build's gate now passes with `state.py advance 3 --gate pass` and no verified record; `ship.py --waive-baseline` still refuses a failure the baseline doesn't list (seen since 3.9.0).
- In a brownfield repo the generated `sdlc-verify.yml` runs the baselined failing test, so CI is red from the start; setup's report warns about it.
- `ship.py` doesn't stage a changed `graphify-out/graph.json`; the agent adds it by name.
- In a workbench, an app repo needs its own `.sdlc/config.json` with a test command before `verify.py` runs; part K's steps don't say so.
- The guardrail loop the setup skill gives agents picks up `\r` on Windows and writes nothing at first; agents noticed and re-rendered (seen since 3.10.0).
- After `/sdlc:eject`, the untracked `.sdlc/state/*.json`, `*.events.jsonl` and `.sdlc/.work/` show in `git status`, since eject removes the `.gitignore` lines that hid them (seen since 3.10.0).
- The plugin-layers and setup-phase diagrams in `docs/diagrams/` need relayout.

### Added
- **Uses a graphify code graph when the repo has one.** When `graphify-out/graph.json` exists, `brief.py` adds a section telling Define to run `graphify query "<the request>" --budget 1500` alongside its reads (or to read `graphify-out/GRAPH_REPORT.md` when the `graphify` command isn't installed), with the graph's build date and a reminder that the code wins over a stale graph. Without a graph nothing changes, and sdlc never builds or installs one. Files under `graphify-out/` no longer count as drift in `verify.py` or as code changes in the freshness hook, so a graph rebuilt by `graphify --watch` doesn't stop a build.
- **A living spec, opt-in** (#73, from OpenSpec's delta specs). With `"living_spec": true` in `.sdlc/config.json`, the repo keeps what the system does now, one file per capability in `<docs>/capabilities/`: a purpose and its requirements (`R-001` onward), each with its test and the change it came from. A change's `## Capabilities` section says what it does to them (`add`, `replace`, `remove`, `retire`, or `none: <why>`); M and L need the section, S may skip it. `ship.py` checks it before anything moves and writes the files after verify, into Ship's commit (`scripts/capabilities.py check|merge` does the same by hand). A removed requirement's id is never reused; deleting a capability needs a `retire` line. `brief.py` lists the capabilities so Define reuses names. Off by default, and does nothing in a spec-backed repo. Its time cost hasn't been measured yet: run an eval before turning it on by default.
- **Output tools can match on** (#76, from OpenSpec's agent contract). `verify.py --json` and `ship.py --json` print one JSON document: `result`, then `problems`, each `{severity, code, message, target?, fix?}`. The code is stable (`red_not_recorded`, `test_lock_changed`, `drift_unrecorded`, `verify_failed`, …) and `fix` is the command to run (`verify.py red AC-001`). The plain-text output and exit codes don't change. `doctor` gives each check a `code` (`repo.commands`) and lists failing and warning checks under `problems`. The CI check `.sdlc/ci/invariants.py` takes `--json` too; repos get it with `/sdlc:upgrade`.
- **Project rules per document** (#75, from OpenSpec's per-artifact rules). An optional `rules` object in `.sdlc/config.json`, keyed `change`, `plan` and `review`, each a list of lines: `brief.py` prints them as their own section, Define applies `change` to the change file and `plan` to the plan, and every review checks `review` against the diff. For example `"rules": {"plan": ["Every task touching file paths adds a Windows check."]}`. Other keys and non-string items are ignored. They're instructions to the agent, read like CLAUDE.md; nothing runs without asking because of them.

### Fixed
- **`/sdlc:upgrade` waits for your pick on a file you edited.** When the plugin's template for a seeded file you changed has moved on, upgrade now asks apply merge / skip this time / keep mine and waits for the answer before it commits or merges. Before, it could choose "skip this time" itself and merge, mentioning the choice only afterwards.

### Changed
- **Better acceptance criteria and a checklist at the approval** (#74, ideas from OpenSpec). The change template says what makes a good criterion: one behaviour, observable by someone who never saw the code, and between them the case the user would most hate to see broken, named in its test. When Define stops for approval (high-risk M, or L in doubt), the message ends with what to check, in order: the why, scope, testable criteria, the missing case, tasks mapped to criteria. Sizing treats a request with more than one intent (not sayable in one sentence, or half could ship alone) as more than one change, done one after another.

## 3.10.0 — 2026-11-16

Smoke test passed on 2026-11-16 against 731d45c. Parts A, B, C, E, G, H and K ran in four parallel groups (A+B; C then E and H in C's repo; G; K), about 25 minutes, set by the C→E,H group. D and F didn't run: the release touches no guardrail or security-hook file. A ran with `--plugin-dir`, since the installed marketplace is also named `sdlc`. The new checks passed: an S fix wrote no `## Test lock` and an M change did; the generated `invariants.py` passed on the shipped M and failed, naming the file, once its locked test was edited; in a brownfield repo `--waive-baseline` named the baselined test in the Gate log and refused an unlisted failing test by name.

Known issues (should):
- In a brownfield repo whose only failing test is in the baseline, `verify.py` doesn't record a pass, so Build's gate needs the verified head and tree recorded by hand before `ship.py --waive-baseline` (seen in 3.9.0 too).
- In a workbench, an S change can write its failing test in an app repo before `state.py new`; that repo is then dirty, `state.py repo` refuses to branch it, and the guard denies the agent's own revert, so the user reverts it (seen in 3.9.0, worse here).
- An AC's Run cell runs from the repo (or workbench) root, so a package's test command needs `cd <package> &&`.
- The guardrail loop the setup skill gives agents picks up `\r` on Windows and writes nothing at first; agents noticed and re-rendered.
- After `/sdlc:upgrade` applies a merge to an edited guardrail, `/sdlc:eject` deletes that file (seen since 3.8.0).
- After `/sdlc:eject`, the untracked `.sdlc/state/*.json`, `*.events.jsonl` and `.sdlc/.work/` show in `git status`, since eject removes the `.gitignore` lines that hid them.
- Setup's knowledge audit (drafts in batches) wasn't exercised: both brownfield samples were small enough that setup skipped it.
- The plugin-layers and setup-phase diagrams in `docs/diagrams/` need relayout.

### Added
- **A decided departure can set a recorded acceptance test aside** (#68). In a spec-backed repo, an AC whose open recorded test can't pass against the rebuild (a decided departure in `docs/departures.yaml` explains why) gets a row `| AC-003 | departure D-004 | acceptance/http/F-ISS-01.AC2.yaml |` beside a builder test row for the same AC. `verify.py` accepts it only when the registry is valid (contracts C5), holds the ID with `decided_by` (not `status: proposed`) and covers the recorded test's criterion, and fails an AC that has the departure row but no builder test; `red` runs the builder row.
- **CI checks the test lock and each AC's test file** (#56 P6). `.sdlc/ci/invariants.py` fails when a file under a feature's `## Test lock` no longer has the sha256 it had at its red run (LF or CRLF line endings both match) and no `test-change <file> What: … Why: …` deviation says why, for active features and, with `--base`, any feature whose state file changed in the push (Ship marks it done in its own commit). Past Define, it also fails on an AC row whose test file doesn't exist (`manual` and `departure` rows name none). In a workbench, app repos' files are left to their own CI. Existing repos get it from `/sdlc:upgrade`, which offers the regenerated script.

### Changed
- **The verification record holds up** (#56, P1–P3 and P5). An AC whose Run command exits 0 after running no tests (unittest's `Ran 0 tests`, node's `# tests 0`, and the texts the red step already knew) now fails `verify.py` as "did not run" instead of passing. `ship.py --waive-baseline` waives only failing tests `.sdlc/baseline.md` lists: it names them from the test step's report (pytest, unittest, jest, vitest, go test, node --test), checks the count against the runner's own summary, writes the waived names to the Gate log, and refuses, naming them, a failure the baseline doesn't list or a report it can't name. `verify.py` keeps a failing test step's whole output (its last 1 MB) in `.sdlc/.work/verify.json` for that. The test lock (each test file's sha256 at its red run; a later change needs a `test-change` deviation and a `red --at <Base>` that still fails) is now on for M and L features in every repo, not only spec-backed ones; S, and a state file with no `Track:`, lock nothing, and a feature already in flight has no lock to check. The PRD now lists the eval rounds on record (§8) and what hasn't been measured (§11).

## 3.9.0 — 2026-11-15

Smoke test passed on 2026-11-15 against eb1dcb4. Parts A, B, C, E, G, H and K ran, in four parallel groups (A+B; C then E and H in C's repo; G; K), about 31 minutes, set by the C→E,H group. D and F didn't run: the release touches no guardrail or security-hook file. A ran with `--plugin-dir`, since the installed marketplace is also named `sdlc`. The new checks passed: setup's stack questions and table pick with reasons, the scaling-roadmap page, `scaffold.py conventions` writing once and refusing to overwrite, upgrade and eject keeping the convention file, and valid lock and config with no temp files left.

Known issues (should):
- In a brownfield repo whose only failing test is in `.sdlc/baseline.md`, `state.py advance <f> 3 --verified` is refused (no passing verify), though `flow.md` says to log the failure and pass Build's gate; `ship.py --waive-baseline` at Ship gets past it (not new in 3.9.0).
- In a workbench, an S change can write its failing test in an app repo before `state.py new`, so before `state.py repo` branches it; the guard holds once the feature exists.
- A monorepo change file's acceptance-test `Run` cells run from the repo root, so they need `cd <package> &&`.
- The guardrail loop the setup skill gives agents (`scaffold.py guardrails | while read`) picks up `\r` on Windows and renders nothing at first; agents noticed and re-rendered.
- After `/sdlc:upgrade` applies a merge to an edited guardrail, `/sdlc:eject` deletes that file (seen in 3.8.0 too).
- The plugin-layers and setup-phase diagrams in `docs/diagrams/` predate the workbench and stack choice and need relayout.

### Fixed
- **The CI workflow generated for a Python repo pins a `setup-uv` tag that exists.** It pinned `astral-sh/setup-uv@v10`, but setup-uv publishes only full version tags, so the `verify` job failed at "Set up job" (`unable to find version v10`) on every PR and push before lint or tests ran. It now pins `astral-sh/setup-uv@v10.3.3`. Existing repos get it from `/sdlc:upgrade`, which regenerates the workflow; a repo that already pinned it by hand gets the same line.
- **Eject's report, convention entries, workbench writes.** `eject --apply` now lists the allow entries and `.gitignore` lines it removed (the report was always empty); upgrade-plan reports a `conventions` lock entry it can't use instead of skipping it silently; the workbench's `.gitignore` and workbench file keep their mode and links when rewritten; a permission error that won't clear is no longer retried for 2.5 s on Windows.
- **Every reader checks the scaffold lock.** The shape of `.sdlc/scaffold.lock.json`, inside as well as at the top (every key a command reads), is checked the first time any command reads it, `status`, `design` and `contract` included, so a malformed lock gives error JSON instead of a traceback; the session-start status line says the lock is unreadable instead of going quiet; `init --force` still restarts over a malformed one (a lock that isn't valid JSON still has to be restored or deleted by hand). `run-commands` saves into the lock as it is on disk when its commands finish, so a change made meanwhile is kept. Without hard links, a convention claims its name with an empty placeholder and then replaces it with the complete file, so it never overwrites another file and a kill never leaves part of one. When another scaffold command saved the lock while this one ran, the save merges this command's own changes onto it (the lock's sections key by key, lists by item, one file's record as a whole) instead of overwriting; two commands changing the same entry still end with the last one's value, a save landing in the instant between another's re-read and write can still be lost, and a lock removed or broken meanwhile is not overwritten. The lock and config are written atomically, keeping each file's mode and writing through a link, and each is written only when the command changed it (`config.json` merges the same way; a list of objects, such as `packages`, is kept whole: when two commands both change it, the last one's list wins); their temp copies are made in the gitignored `.sdlc/.work/` once it exists (a new repo's first save leaves it to setup), so a kill leaves nothing to commit; `doctor` warns about tracked files that resolve outside the project; a file protected from writing (the read-only attribute, its mode, or a Windows ACL) is refused, not replaced. `eject` never deletes outside the repo: the lock's `files` and `declined` must be relative paths inside it, and a file reached through a link out is listed under `outside` and kept; `status` and `upgrade-plan` report such a file as `outside` without reading it, and `render` and `record` refuse one (a deliberate link from a plugin file to a shared folder outside the repo is now skipped by upgrade). A rerun renders over a convention's empty placeholder left by a kill, `config.json` must be a JSON object, a lock holding `null` is an error, `run-commands` still prints its results when the lock is gone at save, and scaffold's own stray temp files (`.sdlc-tmp-*`) over an hour old are cleaned up.
- **Stack conventions, hardened.** `scaffold.py conventions` refuses a `.claude/rules` folder that links outside the project, never overwrites a file that appears while it renders, saves the lock first so a killed render runs again, and checks a lock entry's `root` when reading it back. A lock that isn't a JSON object, or whose `files` or `declined` has the wrong type, is now an error, not a traceback, for every command that needs the lock. `--one-deployable` drops a node convention's `src/` paths, so in a one-deployable Next.js app with `src/` the API's rules leave the web app out. The constitution's "Every stack" principle no longer needs a scaling roadmap page to stand.

### Added
- **Choosing a stack.** Greenfield setup asks three more questions (does anything outside the product call the API, the heaviest workload, the first-year scale) and applies a selection table in `references/stacks.md`: web and mobile app, backend language (Go for CPU-heavy or realtime work or high load, else TypeScript; the one you name wins) and shape (one deployable, or a standalone API with its clients, which leads to the monorepo-or-workbench question). Each pick shows its reason and any warning (heavy work in TypeScript or Python, Go for a small CRUD product, two native apps, iOS needing macOS, Workers and background jobs, Vercel's plans, a VPS's operations), and you still approve the proposal. First part of folding stack-blueprints into setup ([ADR 0026](docs/adr/0026-stack-blueprints-in-setup.md)).
- **More preferred stacks.** `references/stacks.md` adds Vue without Nuxt, Next.js, Flutter, native iOS, native Android and FastAPI, each with pieces, generator, its config `stack` and five commands. The Node section validates with `@hono/zod-openapi` when the API has a consumer and a contract, else `@hono/zod-validator`; Nuxt and Next.js cover the one-deployable shape through one bridge file. The generated CI sets up Xcode for a Swift package and runs it in its own `verify-macos` job on `macos-latest`, whatever `ci.os` says, so the other packages keep their runners.
- **Stack conventions on first touch.** `scaffold.py conventions <stack> <area> [--package <name>]` writes a stack's rules for one area (layers, schema, contract, auth, data-access, ui) to `.claude/rules/<stack>-<area>.md`, scoped by `paths:` to the package. Setup writes none: Define proposes one when a change first touches that area. The file is yours from the start (eject keeps it); `/sdlc:upgrade` shows a changed template as a diff and never overwrites it. Templates cover Node, Go and FastAPI (all six areas but ui), Nuxt, Vue, React and Next.js (layers, ui), and Flutter, iOS and Android (layers, auth).
- **Cloudflare, Vercel and Docker Compose platform references.** With `deploy.target` `cloudflare`, `vercel` or `docker-compose`, Define sees that platform's checks as failure modes, as it already did for `gcp-cloud-run`: Workers' CPU cap and no long-running process, Hyperdrive and Neon's HTTP driver without interactive transactions; Vercel's Hobby plan, function duration, `waitUntil` and Cron limits, `attachDatabasePool`, previews never reaching production data; a Compose server's published ports bypassing ufw, off-server backups with a restore drill, and rollback by image tag not undoing migrations.
- **Constitution principles per stack and a scaling roadmap.** `sdlc:project-constitution` proposes architecture principles for the stacks in use from `references/stack-principles.md` (where business logic lives, what services may import, data only through the contract's client, no secret in a mobile app, nothing generated edited by hand). Greenfield setup writes `knowledge/decisions/scaling-roadmap.md` with the approved stack's growth steps (split the API out, move hot paths to Go, extract a worker, add a BFF, multi-tenancy, change hosting, a managed database), each with its trigger; a change that takes a step is sized L. Last part of folding stack-blueprints into setup.

## 3.8.0 — 2026-11-13

Smoke test (runbook A–H and the new K, workbench) passed on 2026-11-13 against 7a777a2. All parts ran, because the release touches each one's scope; they ran in five parallel groups and took about 46 minutes, set by the C→D,E,H group. K ran the workbench in real sessions for the first time:
- writes into a read-only repo were denied, naming its owner;
- a change made outside the session was reported after the next call and blocked Stop;
- the message `accept read-only specs` was accepted;
- an S change in an app repo was branched before its first write and shipped with a commit message and PR body per repo.

Known issues (should):
- Undoing a read-only change you already accepted counts as a new change, so you accept again.
- Setup's context-diet table still doesn't show before its trim question (seen in 3.7.0 too).
- `ship.py --waive-baseline` waives any failure of the test step without checking that `.sdlc/baseline.md` lists it; the agent's own check is all that stands in the way (not new in 3.8.0).
- After `/sdlc:upgrade` applies a merge to an edited guardrail, `/sdlc:eject` deletes that file, and your edit survives only in git history.
- Under auto mode, the classifier can still block `scaffold.py allow --from-commands` during setup and upgrade.
- The plugin-layers and setup-phase diagrams in `docs/diagrams/` predate the workbench and need relayout.

### Added
- **Workbench: one repo per app, beside the monorepo, for new multi-app projects** ([ADR 0025](docs/adr/0025-workbench-for-multi-app-projects.md), extending ADR 0005). Greenfield setup with two or more apps now asks which layout: one repo holding every app (the monorepo, as before) or a workbench. A workbench makes the session's folder a `<project>-workbench` repo holding `workbench.json`, the API contract (`contract/v<N>/`) and every feature record, with each app its own repo cloned inside it and set up with its own commands, CI and guardrails (`references/workbench.md`). Existing monorepos are unchanged.
- **Guards follow calls into app repos.** In a session started in a workbench, hookify rules and the role guard act for the app repo a call targets; a write into a read-only repo (`write: false`) is denied, naming its owner (behind that, a new `read_only_watch.py` hook reports any change in a read-only repo after the call that made it and blocks Stop until the user undoes or accepts it, and read-only repos get a push URL that points nowhere; outside a workbench the hook exits at once), and a write into an app repo the active feature hasn't branched (`state.py repo`) is denied, naming the command; `state.py new` refuses in an app repo and points to the workbench.
- **One feature across repos.** `state.py repo <feature> <name>` branches a writable repo from its default branch (refused while dirty) or records the commit of a read-only one; `verify.py` runs each touched repo's commands in its folder and records its tree; freshness and drift are per repo; `diff_stats.py` lists read-only repos that moved since.
- **Ship across repos.** `ship.py` stages each touched repo with its own commit message and a PR body linking the others, in merge order (workbench, provider, consumers); `state.py pr` records each PR and `ship.py <feature> --status` warns on an out-of-order merge without blocking.
- **App CI follows the workbench.** A consuming app's `builtin:ci` checks out the workbench branch named like its PR's (else `main`) for the contract; a private workbench needs a `WORKBENCH_TOKEN` secret.
- **Preferred stacks.** Greenfield setup proposes from `references/stacks.md`: Nuxt (SPA, Nuxt UI, Pinia, Pinia Colada, Zod), React (Vite, shadcn/ui, Zustand, TanStack Query, React Router, Zod), Node (Hono, PostgreSQL, Drizzle, Zod; Cloud Run + Cloud SQL or Cloudflare Workers + Neon) and Go (Gin, oapi-codegen, pgx/v5, sqlc, golang-migrate; Cloud Run + Cloud SQL), each with its generator and five commands. You still approve every proposal.
- **`scaffold.py workbench list|add|remove|clone`** maps repos after setup (`clone` brings back listed repos a fresh clone of the workbench lacks); `/sdlc:doctor` reports repos not cloned, unlisted nested repos, folders not gitignored and apps without their own config.

### Changed
- **A root `commands.test` beside `packages` now runs** in the verify plan and CI, from the root after every package's steps, and still counts as a full run of every package. Scripts and hooks read scopes through one parser.

## 3.7.0 — 2026-11-12

Smoke test (runbook A–H) passed on 2026-11-12 against 4b82ea5, with the `Trust anchor` and `Review cap` dialogs and the pre-filled-answer denial checked in real sessions. Known issues (should):
- Setup's context-diet table can sit collapsed under "· summary" in the terminal before its question.
- Setup's report says `.claude/settings.local.json` "was not written" when only sdlc's own key was skipped; the companion keys were written.
- Under auto mode, the classifier can block `scaffold.py allow --from-commands` during `/sdlc:upgrade` as self-modification, which pauses the upgrade until you run it.
- After `/sdlc:eject`, `.sdlc/state/` and `.sdlc/.work/` show as untracked, because eject removes their `.gitignore` lines.

### Changed
- **The review round cap and a trust-anchor notice ask in a dialog.** They used to stop the turn and wait for you to type a reply. Now each one asks with `AskUserQuestion` (headers `Review cap` and `Trust anchor`), and picking an option lifts the gate. A new `user_answer.py` hook denies a question that arrives with its answers already filled in and records the others; the two gates accept only an answer to a recorded question with their header, so the agent still can't answer for you. A typed message still works, and under Codex, Cursor and Antigravity it's still the only way.

## 3.6.1 — 2026-11-11

A patch that only re-vendors the shared contracts; no behaviour change in sdlc. The smoke test in real sessions (runbook) was not run for this release.

### Changed
- **Shared contracts 1.3.0**, vendored byte-identical in `scripts/contracts/v1/` from product-rebuild f4ac06e. `check_lock` now reports an error for a criterion tagged `[inferred]` at level 1 (C3), with a new invalid fixture that `vendor-check` runs; sdlc never writes a criteria lock, so nothing it produces is affected.
- **Shared contracts 1.2.0**, vendored byte-identical in `scripts/contracts/v1/` from product-rebuild aeff427. C3's level 1 now needs a SUPPORTED verdict, and a criterion tagged `[inferred]` never reaches it by audit; no field or format changes, and nothing in sdlc reads the level rule.

## 3.6.0 — 2026-11-10

### Added
- **Setup asks how the project deploys.** A new `deploy` step records the target (`none` yet, `docker-compose`, `gcp-cloud-run`, `vercel`, `cloudflare` or `other`) and the environments, each routine or not, as `deploy` in `.sdlc/config.json` (`scaffold.py deploy`), and seeds `knowledge/runbooks/deploy.md` from a new template: environments, deploy command, smoke test, rollback, logs and what deploys taught. `/sdlc:setup deploy` runs the step on its own; `/sdlc:upgrade` asks it in repos set up before.
- **`/sdlc:deploy` follows the runbook.** Only an environment marked routine deploys without your go-ahead; the smoke test and rollback come from the runbook, and a fact a deploy teaches (a header shape, a URL) is written back to it.
- **A GCP Cloud Run platform reference.** With `deploy.target: gcp-cloud-run`, Define sees its checks as failure modes: no state in process memory, Cloud SQL connections against `--max-instances`, the `/cloudsql/` socket URL, Workload Identity Federation instead of keys, `printf '%s'` for secrets, the real `X-Forwarded-For` shape, Firebase Hosting's `__session` cookie, and rollback by traffic not undoing migrations.
- **Deploy and rollback in the templates.** The change template's failure modes ask whether the migration works with the previous app version and whether anything assumes one process; the migrations rule says why additive steps matter; the constitution template has an optional Release principle.

### Fixed
- **The migrations rule now loads for Drizzle, Alembic and Flyway projects.** The default `areas.migrations` missed `drizzle/`, `alembic/` and `db/migration/`, so `.claude/rules/sdlc-migrations.md` and the migrations security trigger never applied there. Repos that set their own `areas.migrations` keep it.

### Known issues
- The setup diagram (`docs/diagrams/sdlc_setup_phase.svg`) still draws twelve numbered steps: its description names the deploy step, but the boxes need a relayout to add it.
- A `.sdlc/config.json` whose top level isn't a JSON object crashes every `scaffold.py` command (`deploy` included) with a traceback instead of an error. It predates 3.6.0.
- Only GCP Cloud Run has a platform reference; the other targets get the config and the runbook.

Checked on 2026-11-10 at commit 2cdea8f: the full suite (497 tests, 4 skipped, Python 3.10), `claude plugin validate` and `hosts.py check`. Only the parts of the smoke test this release changes were run, headless in Claude Code 2.1.322 with the plugin loaded by `--plugin-dir` (auto permission mode):
- C (greenfield setup) on a tiny Python library: the deploy step recorded `gcp-cloud-run` with `dev` routine and `prod` not, seeded `knowledge/runbooks/deploy.md` with its six sections and linked it from the index, and setup merged locally. `brief.py` in that repo printed the Cloud Run Define checks.
- `/sdlc:setup deploy` in the set-up repo: `--env prod:routine` was refused (exit 2, nothing written); `staging` was added as routine, and the branch merged locally.
- H (upgrade) from a simulated 3.5.0 repo with its own `knowledge/runbooks/gcp-deploy.md`: the `3.6.0-deploy-target` migration recorded `deploy` with that runbook and seeded no other; the regenerated migrations rule covers `**/drizzle/**`.
- `/sdlc:deploy`: `dev` (routine) deployed without asking, said it was marked routine, ran the runbook's smoke test and named its rollback. With `prod` planted as routine in the committed config, it deployed nothing and stopped for the go-ahead, naming the rejected value.
- A, B, D–G, I and J were not run.

## 3.5.0 — 2026-11-09

**No standalone behaviour change except one:** Build now writes against what Review checks (below, under Changed). Otherwise a repo without an rspec `criteria.lock.json` (or `spec_lock` in `.sdlc/config.json`) and without `acceptance/manifest.json` works exactly as with 3.4.0: no test lock, no criteria lint, no new config keys, no new `/sdlc:doctor` rows, no new hook denials and no extra hook process (the read-only rule for recorded tests runs inside the existing hookify PreToolUse hook). Two things every repo sees: a pre-release now sorts before its release (`3.5.0-rc.7` < `3.5.0`), and the 3.5.0 migration runs once and adds nothing outside spec-backed mode. 3.4.0's test suite passes unchanged apart from one added assertion in `tests/test_brief.py`.

3.5.0 adds **spec-backed mode, for product-rebuild**, on only in a repo that holds one of those files (`spec_lock.spec_backed_repo`). It is rebuilt from 3.4.0 (sdlc--v3.4.0), porting only the kept code from rc.1 to rc.3 and the contracts 1.1.1 re-vendor; rc.1 to rc.5 are superseded, and rc.6 and rc.7 are merged into this section.

### Added (spec-backed repos only)
- **Shared contracts 1.1.1**, vendored byte-identical in `scripts/contracts/v1/` (MANIFEST sha256 e385f981…de30b, `-text` in `.gitattributes`; `contracts.py vendor-check`).
- **Spec-backed change files** (spec 03 S2): an AC cites criteria from the lock (`- **AC-003** → F-ISS-01.AC2`); `state.py new --criteria` records what a slice owes and `state.py cite` each cited criterion's lock hash; `verify.py` and `verify.py trace` fail on an ID the lock doesn't hold, one not recorded, a slice criterion not covered and a `stale criterion`; `brief.py --criteria` prints the criteria's text.
- **Recorded acceptance tests** (S3): a row whose Test is an `open` test in `acceptance/manifest.json` runs it (`contracts.py run-http`, Playwright, Maestro) against the build `verify.py` starts from `accept.start` at `accept.base_url`; the hookify PreToolUse hook denies everyone writes to the manifest and its tests, by edit tools and shell commands, other agents too (`hosts/hook.py`).
- **Test lock** (S4): `verify.py red` records each test file's sha256 under `## Test lock`; a run fails on a locked test that changed or was deleted unless a `test-change` deviation names it and `verify.py red --at <Base>` shows it still fails on Base.
- **Spec questions** (S10): `state.py question` writes a finding-v1 (`source: sdlc-question`, `class: spec-gap`) and blocks the running part; `state.py questions` unblocks it when the lock shows the amended criterion; autopilot runs the other ready parts meanwhile.
- **`accept.start` / `accept.base_url`** (S12): `scaffold.py add-config-keys` (the 3.5.0 migration) adds them, empty, in a spec-backed repo only; `/sdlc:doctor` warns while they are empty, in a spec-backed repo only. No mutation-command key.

### Changed (every repo)
- **Build writes against what Review checks.** On the 3.5 parts, round-1 findings were mostly bad loaded data reaching the user as a traceback, other parts that read a reshaped file or counter, open-ended shell and path spellings, and stale docs. The builder never saw the defect list the reviewer used. Now `brief.py` also prints the plugin's `recurring-defects.md`, flow.md's Build names those classes to check while writing (no extra pass, no agent), a fix keeps the other shells, platforms and readers working, and S's Build step names the list too. Effect on review findings: not measured yet. What every repo sees: the builder gets the recurring-defects list in the brief and the Build checklist on every track, at a small token cost per run.

### Withdrawn (were in rc.1 to rc.5)
- **S1** criterion lint in Define and the `Criteria: c1` mark, **S5** the test-auditor, **S6** the mutation probe and `commands.mutation`, **S7** the test-writer, **S8** the QA review row, **S9** the UI render, **S11** the Level column. Why: the rc.5 eval measured tokens +97% on M low and +62% on S against 3.4.0 with no change in quality on the eval tasks; sdlc 1.6.0 had already taken the qa-tester out of the gate for the same reason. They are not part of 3.5.0.

Checked on 2026-11-09 on the release commit: the full suite (484 tests, 4 skipped, Python 3.10), `claude plugin validate` and `hosts.py check`; 3.4.0's tests are unchanged apart from `tests/test_brief.py`. The smoke test was not re-run on the release commit.

## 3.4.0 — 2026-11-08

### Changed
- **Review aims for two rounds: one full review, one closing check.** On cuti-os and bug-hunter, features took 3 to 9 rounds. Almost every failure after round 1 was a bug a fix added, a finding fixed in one place but not the others, or the next variant of one class (another encoding of a secret, another env var). So:
  - Round 1 runs at full depth always (the built-in `code-review` as `high --max-findings all`). The reviewer has no confidence-80 cut-off, no 30-line report limit and no limit to the diff's own files. Unsure findings are marked `unconfirmed` and never fail the round. Each finding names its root cause, every place it shows, and what its fix must keep working.
  - The fix pass fixes the whole class with a test that covers its variants. An open-ended class gets the structural fix the reviewer names. An `unconfirmed` finding gets a test, and is fixed or dropped by its result.
  - Round 2 checks the fixes and the code around them at full depth, and fails only on a high. A medium or low bug it lists is fixed test first and closed by `verify.py`, without a round 3 (`review_report.py` writes that verdict). The round cap still stops for you when round 2 fails on a high.
  - Cost: round 1 now costs more than before; this hasn't been measured against the M bar yet.

### Fixed
- **Eject's report names only what it keeps that exists.** `scaffold.py eject` listed the baseline, design system, PRD and feature folders under `keep` whether or not the repo had them, and the eject steps repeated a fixed list, so a greenfield repo with no UI was told its `.sdlc/baseline.md` and `docs/sdlc/design-system.md` were kept. The `keep` list now holds only paths that exist (a `<feature>` pattern only when its folder does), and the report reads it.

### Known issues
- In the track-matrix diagram (`docs/diagrams/sdlc_track_matrix.svg`), rows 3.4 and 3.5 have new labels, but their marks and the totals still reflect the old two code depths. `docs/track-matrix.md` is current.
- Fixing the medium and low bugs that round 2 lists is an instruction only: no gate checks that each one got its test and fix.
- `--max-findings all` stays in effect for your own later `/code-review` calls until you pass `--max-findings default`.

Checked on 2026-11-08: the full suite (426 tests, Python 3.10) and `claude plugin validate`. Only the smoke-test parts this release changes were run, headless in Claude Code with the plugin loaded by `--plugin-dir`, as for 3.3.0:
- G (brownfield setup) on a tiny Python library: it merged locally.
- An M feature (`divide` and `parse_number`) through Review:
  - Both code-review calls were `high --max-findings all`.
  - Round 1 reported 7 findings and failed on 3 bugs, one with a class named (float overflow on input the regex accepts).
  - Round 2, the closing check, passed. Its findings were 7 lows, all tickets.
  - The run took 4.3 minutes, 33 turns and $0.89.
- A–F, H, I and J were not run.

## 3.3.0 — 2026-11-07

### Changed
- **Setup, upgrade and eject merge their branch locally without asking.** Local merge was always the answer, so setup's `finalize` (and Join, and `/sdlc:setup design`), `/sdlc:upgrade` and `/sdlc:eject` now merge their branch into the one it was made from and delete it; nothing is pushed and no PR is opened unless you ask.

### Known issues
- Eject's report lists `.sdlc/baseline.md` and `docs/sdlc/design-system.md` as kept in a greenfield repo with no UI, where neither exists.

Checked on 2026-11-07 at commit 9ed4107: the full suite (424 tests, Python 3.10), `claude plugin validate`, and, by the maintainer's choice, only the parts of the smoke test this release changes: C (greenfield setup) and H (upgrade and eject), headless in Claude Code with the plugin loaded by `--plugin-dir`. Setup, upgrade and eject each merged their branch into `main` locally, deleted it, pushed nothing and asked no merge question. A, B, D–G, I and J were not run.

## 3.2.1 — 2026-11-06

### Fixed
- **`/sdlc:setup` joins a repo another agent set up, even when the session status line says `setup complete`.** It answered "already set up" from that line, which doesn't show the recorded agents, instead of running `scaffold.py host` and joining.

### Known issues
- Setup's context diet doesn't always show its table (plugin, tokens per call, verdict, reason) before asking: in the smoke test it summarised `context_diet.py`'s output into a one-line question.
- `scaffold.py eject --apply` reports `.claude/settings.json` and `.gitignore` as `unmerged` with empty lists although it removed their lines, leaves `"allow": []`, and leaves `.sdlc/state/` runtime files untracked once their ignore lines are gone. A guardrail kept as "keep edit, stay managed" at upgrade is listed for plain deletion.
- `ship.py --waive-baseline` waives any failing test step without comparing test names to `baseline.md`; that comparison is left to the agent.
- A join can recommend different places for the plugin keys (`settings.local.json` or `settings.json`) in similar repos, and setup writes the UI rule and guardrail into a repo with no UI when the design mode is `builtin`.
- Antigravity's slash menu shows the commands as `/sdlc:..:hosts:skills:<name>`; they work.

Checked on 2026-11-06 at commit bca6380: the full suite (424 tests, Python 3.10), `claude plugin validate`, and the smoke test in real sessions under `tmux` with the plugin loaded by `--plugin-dir`: A–H in Claude Code 2.1.318–319 (every must item passes; C.4's trim table and E.6's security-review skip are the gaps: the first wasn't shown, the second couldn't run without API credentials; G's audit batches didn't run on a sample that small), J in Codex 0.154.0 and Antigravity 1.5.1, including Claude Code joining each repo after the other agent set it up. Not run: Windows (I), Cursor, and the desktop app's layout.

## 3.2.0 — 2026-11-05

### Changed
- **The agent runs unattended and asks only when blocked, with a question dialog.** Questions used to arrive as a line at the end of an update ("Reply 'approved'", 'say "merge" to merge'), which was easy to miss. The orchestrator now settles and records what the request, the code or a sensible default settles, and asks only at a named stop or for a decision only you can make, always through the agent's question tool (Claude Code: `AskUserQuestion`, recommendation first): the high-risk approval, the review choice, a disputed high finding, the owner handover, setup not done, merge at the PR, and setup's hard stops. Two stay typed replies, because their hooks lift only on a prompt you send: the decision past the review round cap and a trust-anchor notice.
- **product-rebuild is no longer in the sdlc marketplace.** `/plugin install product-rebuild@sdlc` stops working; it has its own marketplace now: `/plugin marketplace add tammai/product-rebuild`, then `/plugin install product-rebuild@product-rebuild` (keep the `sdlc` marketplace added; its dependencies come from there). A copy installed as `product-rebuild@sdlc` no longer updates; reinstall it as `product-rebuild@product-rebuild`.

### Fixed
- **The role guard no longer treats a project path starting with two dots as outside the project.** It tested `startswith("..")`, so a folder like `..hidden/` or a file like `..env` slipped past its rules: a code-reviewer could edit there and the qa-tester could read code there. Only `..` or a path starting with `../` counts as outside now.
- **`hosts.py` ignores stray entries in `hosts/skills/` and `hosts/cursor/agents/`.** A file there such as the `.DS_Store` macOS writes, or a folder without a `SKILL.md`, made `check` report it as stale on every run and `build` crash with `NotADirectoryError` before writing anything. Only what a build writes now counts: a folder holding a `SKILL.md`, and a `.md` file in `hosts/cursor/agents/`. Generated files whose command or agent was removed are still deleted.
- **`/sdlc:doctor` no longer calls knowledge index links with spaces broken.** `[Deploy runbook](deploy%20runbook.md)` and `[On call](<on call.md>)` were flagged although both files existed: the link pattern stopped at the first space, didn't know `<…>` targets and checked the path without URL-decoding it. Both forms now resolve, with or without a `#fragment`.
- **`state.py blocker raise` keeps an open question that starts with `(`.** The step that drops the template's placeholder line dropped every item starting with `(`, so `(owner) needs the API key` vanished at the next raise and was never listed. Only the template's own `(oldest first …)` line is dropped now.
- **A bold backlog ID no longer stalls the backlog.** `backlog.py` kept `**B1**` as written, so a part depending on B1 never saw it done and `next` returned nothing, with no error. An ID in bold, italics or backticks now reads as its plain `B<n>`.
- **File names with spaces or non-ASCII characters stay whole in `diff_stats.py` and the freshness hook.** `diff_stats.collect()` split git's name lists on whitespace and kept git's quoting, so an untracked `src/my file.py` came back as `src/my` and `file.py`, `café.py` as `"caf\303\251.py"`, and `verify.py`'s drift check flagged files that don't exist. Name lists are now read NUL-separated (`-z`), and diff headers are unquoted. `verify_freshness.changed_code_files()` had the same quoting problem: a non-ASCII `.md` counted as code because its name ended in `.md"`.
- **Backlog AC cells no longer read digits inside words as ACs.** `backlog.py` took the `2` in `OAuth2` or the `3` in `B3` for AC-002 and AC-003, so `verify.py` skipped those ACs as owned by a later part. A number now counts only as an `AC-` token or on its own.
- **`/sdlc:doctor`'s `.gitignore` check asks git.** It matched `.gitignore`'s words against the literal `.sdlc/.work/` and the control contract's patterns, so `.sdlc/.work`, `/.sdlc/.work/`, a parent folder such as `.sdlc/state/`, or a rule in `.git/info/exclude` gave a false warning. In a git repo it now runs `git check-ignore`; outside one it reads `.gitignore`'s lines with leading and trailing `/` ignored.
- **`ship.py` ships from a feature branch that `origin/HEAD` names, and a refusal moves no state.** On a repo whose first push was the feature branch, GitHub makes it the default and `origin/HEAD` names it, so Ship took it for the default branch and failed at `git switch -c <feature>` after it had already set Stage 4 and `Status: done`. On a branch named after the feature, Ship now stages there. The branch is settled before the state moves: on the default branch with a branch of the feature's name already there, Ship refuses and says to switch to it, leaving the state file as it was.
- **The drift check names new dependencies correctly.** A one-line go.mod `require github.com/pkg/errors v0.9.1` was reported as the dependency `require`, and requirements lines such as `requests<3`, `flask~=2.0` or `uvicorn[standard]>=0.30` kept their specifiers, extras and markers, so verify flagged an "undeclared dependency" that Public Surface did declare. It now reports the module path and the bare package name, and no longer reports option lines such as `-r dev.txt`.
- **`/sdlc:status` maps stages with 3.0's numbering** (1 Define, 2 Build, 3 Review, 4 Ship). It still listed the 2.x ranges (1–3, 4, 5–7, 8–11), so a Build feature could read as Define.
- **Setup no longer commits `.sdlc/.work/review-rounds.json`.** The review-rounds hook saved its store on every tool call and prompt, even with no feature active, so setup's first commits picked up an empty one before the `.gitignore` step took it out again. It now writes only when a round's count changes.
- **`--surface` writes what `verify.py` reads.** The docs showed `--surface "<item> — <AC>"`, and `state.py new` copied the text as written, but the drift check reads only `` - export `name` `` lines, so a free-text entry such as `calc.div(a, b) — AC-001` left every export flagged as undeclared at Build. `--surface` now takes the kind first (`export div — AC-001`; also `endpoint`, `command`, `config`, `env`, `dependency`), writes the name in backticks, and refuses free text at Define with the form to use. flow.md, s-track.md and the plan template show it.

## 3.1.0 — 2026-11-05

### Changed
- **`/sdlc:clean_gone` is now `/sdlc:clean-gone`,** with a hyphen like every other command. The old name came unchanged from the vendored commit-commands plugin. There is no alias: type the new name.
- **The plugin's homepage is the wiki,** `https://github.com/tammai/sdlc/wiki`, in the Claude Code, Codex and Cursor manifests; `repository` still names the repo. `hosts.py` takes the homepage from `.claude-plugin/plugin.json` instead of hard-coding the repo.
- **The docs moved to the [GitHub wiki](https://github.com/tammai/sdlc/wiki).** The guidebook, playbook and the runbook's user procedures (install, health check, R1–R19) are now wiki pages, written in `docs/wiki/` and published by `.github/workflows/wiki.yml` on each push to `main`; play and procedure numbers are unchanged. `docs/guidebook.md` and `docs/playbook.md` point to the pages, and `docs/runbook.md` keeps only the maintainer procedures. `/sdlc:doctor`'s fixes link to the wiki's Troubleshooting page instead of `docs/runbook.md`, a path that only existed in the plugin's own repo.
- **Setup checks that impeccable is on, not just installed, and can turn it on** (issue #9). `scaffold.py design` reports `impeccable.state` (`missing`, `disabled`, `enabled`) and whether its detector hook runs; a Claude Code plugin that's installed but off for the repo no longer counts as there. With the user's yes, `scaffold.py design impeccable --enable` turns it on in `.claude/settings.local.json` (`enable-plugin --remove` and eject take it back). Plugins load at session start, so the step stays pending (`step-done --pending`) and `finalize` waits until a restarted `/sdlc:setup` finishes it. `/sdlc:doctor` warns on a disabled plugin.
- **The design-mode question is always asked**, even when the recommendation looks obvious, and the user's reason goes in the step's commit.
- **`/sdlc:setup design` runs just the design step on a set-up repo**, to switch modes or finish turning impeccable on.
- **The UI guardrail waits for impeccable's hook.** `sdlc-ui-hardcoded-values` is removed only once impeccable's detector hook runs in the repo, never in the call that turned the plugin on, so nothing goes unchecked in between.
- **A design system the project must stay on can be pinned in impeccable mode:** setup has `/impeccable document` record it as the only system, with the restyling commands (`bolder`, `colorize`, `overdrive`, `delight`) off limits, and Build skips what `DESIGN.md` puts off limits.
- The `design-system` step's procedure moved to `skills/setting-up-projects/references/design-mode.md`.
- **sdlc-stepper shows the title `SDLC` again,** in bold before the stepper (`SDLC ✓─●─○─○ · Build · …`) in the terminal and in semibold before the icons on the desktop. 3.0.1 had dropped it for the stepper alone.

### Known issues
- Setup commits `.sdlc/.work/review-rounds.json` before its gitignore step, then removes it from git again.
- `verify.py` rejects the Public Surface form `flow.md` documents (`--surface "<item> — <AC>"`); `diff_stats.py` accepts only lines like `` - export `name` ``. Older than this release.
- Review's freshness check doesn't count a test run chained with other commands (`cd web && npm test ; … ; true`).
- Codex runs sdlc's hooks only after the user approves them in its hooks panel at first start.
- Antigravity's model read the plugin's own source for a long while before setup's first step until told to follow the skill in order.

Checked on 2026-11-05 at commit 91df5a0: the full suite (400 tests, Python 3.10), `claude plugin validate`, the stepper's 13 tests, and the smoke test in real sessions under `tmux`: A–H in Claude Code 2.1.318 (every must item passes; the plugin was loaded with `--plugin-dir`, since the `sdlc` marketplace name was taken by the installed copy), J in Codex 0.154.0 and Antigravity 1.0.16. The stepper showed `SDLC ✓─✓─●─○ · Review · commit`. Not run: Windows (I), Cursor, and the desktop app's layout.

## 3.0.4 — 2026-11-04

### Changed
- **Setup turns on sdlc-extras and sdlc-stepper with sdlc.** `enable-plugin` wrote only `sdlc@sdlc`; both companions shipped off by default, so setup only named them. They are now on by default, in whichever settings file holds sdlc's keys; upgrade's re-run adds them to repos set up earlier. Set either to `false` there to keep it off.

## 3.0.3 — 2026-11-03

From a real rebuild (Kutt, on 2.4.1), checked against 3.0.2 first: each of these still reproduced.

### Changed
- **A bare `state.py advance … --verified` records what `verify.py` recorded.** Review and Build's gates passed `<head> <tree>` by hand, copying `verify.py`'s head, which is the parent of the commit the builder makes next. With no values it now takes the head and tree of the last passing run, and refuses when the code changed since or no passing run is recorded; `--verified <commit> <tree>` still works.
- **The built-in `code-review` and the dependency audit get a report file.** `scripts/review_report.py` writes `code-reviewer-r<N>.md` or `dependency-audit-r<N>.md` from the findings the orchestrator rated, and computes the `VERDICT` line from those ratings (FAIL for every high and every bug), so nobody types it and it can't disagree with the table above it. `dependency-audit-r<N>.md` is now one of the reports the trust anchor and the round cap read. An audit tool that can't run is not a pass.
- **Learn creates `<docs>/recurring-defects.md` when it's missing**, with a heading and the shape line, instead of appending to a file nothing makes.

Checked on 2026-11-03: the full suite (392 tests, Python 3.10) and `claude plugin validate`; `review_report.py` and a bare `--verified` against a real verify run, and Review's budget hook letting the report script through. The runbook's real-session smoke test (A-J) was not run for this release.

## 3.0.2 — 2026-11-03

### Fixed
- **sdlc-stepper shows during Define.** sdlc writes a feature's state file only at the end of Define (`state.py new` runs in the call that moves to Build), and the bar reads state files, so it appeared only once Define was done. Now submitting `/sdlc:start` in an sdlc repo with no feature on disk shows the bar at once, at Define; it then follows the agent's own `Define · …` lines and hands over to the state file when it appears. A start that turns out trivial leaves nothing: a Define band the agent never spoke for goes when its turn ends. The feature name is left out until there is one. A feature the model starts without `/sdlc:start` shows from its first `Define · …` line (a `skill.prompt` hook would catch it sooner, but a built-in module runs ahead of it and the engine reports the hook as skipped in the transcript). Found in `missue`.

Checked on 2026-11-03: only sdlc-stepper changed since 3.0.1. In a real terminal session (under `tmux`, with an sdlc config and no state file) nothing showed at start; submitting `/sdlc:start add a csv export` showed `●─○─○─○ · Define` at once and then `Define · sizing · waiting for approval` from the agent's line. The stepper's 13 tests, `claude plugin validate` and the full suite pass. The desktop is checked by its test only.

## 3.0.1 — 2026-11-03

### Changed
- **sdlc-stepper is a mini stepper, on the desktop and in the terminal.** Both draw one row: the four stages as marks joined by short lines where the title was, a dot, where the session is now (phase, part, step), and the feature at the right. It replaces 3.0.0's two-row desktop card (its capsule bar of stages with names, and the part icons on Build's line) and the old terminal rows (`sdlc ✓ Define ─── ● Build …` and `■□□ 1/3 parts`); the part in progress is in the words instead.
  - **Desktop:** the stages are one 20px-high image: a green check when done, a green dot when current and a gray ring after, with 1px lines between them that turn green once passed. Only the current icon pulses (a ring spreads out from it). It sits straight on the app's own band.
  - **Terminal:** the same stepper as `✓─●─○─○` in a rounded outline, in the terminal's own theme colors, with the current stage green like the done ones (the orange accent is gone).

### Fixed
- **The bar says what the transcript says.** The step changed only when a tool the bar knew ran, so after `verify.py red` it kept saying `failing tests` while the agent moved on to a browser tool and wrote `Build · audit · …`. The bar now shows the last line of what the model said that starts with the phase (`Build · …`), which sdlc has every update begin with, and a tool it knows still replaces it, being newer. A line for another phase is ignored. Found on the desktop app.
- **A long status is cut with an ellipsis, on both surfaces.** The agent's update line can be long (`Build · verify · the full verify plan is running in the background …`); in a box of its own that takes the room left, the words are now truncated with `…` and the feature name keeps its place at the right. Before, on the desktop, the text ran past the card's edge with no ellipsis and pushed the feature name out of sight. Checked in the real terminal UI under `tmux`; the desktop is checked by its test and by eye.
- **The terminal band no longer vanishes in a short window.** The engine gives the band only the rows left above the prompt and hides one that doesn't fit; the old 5-row band went at about 16 rows of terminal, the 3-row one at 14. With fewer than 3 rows the band now drops its outline and shows as one line. With none to spare the engine shows nothing, which the mod can't change. Found by running the real terminal UI under `tmux` and shrinking it.

Checked on 2026-11-03 at commit 21bc7fb: only sdlc-stepper changed since 3.0.0, so the runbook's smoke test was not repeated in full. The real terminal UI, run under `tmux`, showed the band at start, through a prompt and a tool run, and with a long update line cut by an ellipsis, and at 40 and 20 rows tall (one line at 14, nothing at 12 and below); the desktop app was looked at by hand on a live preview. The stepper's 11 tests, `claude plugin validate` and the full suite (384 tests, Python 3.10) pass.

## 3.0.0 — 2026-11-03

### Breaking
- **The phases are numbered 1 to 4, not 1, 4, 5 and 8** ([ADR 0022](docs/adr/0022-phases-numbered-one-to-four.md)). `Current: Stage 2 – Build`, `Stage 3 – Review`, `Stage 4 – Ship`; `state.py advance <f> 2|3|4`; a state file says `Process: 3` and the control contract is `contract_version` 3. The old numbers were kept from the eleven-stage pipeline so no hook had to change; they are now gaps that every reader has to explain. The hooks and `state.py` act only on `Process: 3`: a `Process: 2` feature has no guard and `state.py` refuses it until it is migrated. `/sdlc:upgrade` does that: the `3.0.0-stage-numbers` migration runs `state.py migrate`, which rewrites every `Process: 2` state file (the `Current:` line, the Stages checklist and the Gate log; finished features too) and drops the trust anchor's remembered stage for it. Nothing has to finish first, unlike 1.x → 2.0. The CI check `invariants.py` counts Build as 2 and Ship as 4 on `Process: 3` and as 4 and 8 on an unmigrated feature, so a branch in between still passes. `sdlc-stepper` reads `Process: 2` and `3` (the phase name first, the number by marker as the fallback). If you use `sdlc-stepper`, update it with sdlc.
- **`product-rebuild` needs its own release for 3.0.** It is a separate plugin (`tammai/product-rebuild`); its release 2.0.0 requires `sdlc ^2.4`, so with sdlc 3.0.0 it shows `failed to load`, and its lane scripts still use the old stage numbers (`state.py advance <f> 4` to enter Build, `Current: Stage 4 or later`). Until it has a release that requires `sdlc ^3.0` and uses stages 2, 3 and 4, keep sdlc at 2.5.0 if you use it.

### Added
- **`docs/track-matrix.md` and its diagram `sdlc_track_matrix.svg`: which step runs on which track.** 36 steps against Trivial, S, M low risk, M high risk, L and L in parts; each is always, conditional (with its condition listed) or not run, with the totals per track and where the usual use cases (bugfix, refactor, security patch, infra, MVP, PoC) land. Asked for by a teammate.
- **`verify.py trace`: requirement → AC coverage, checked by a script.** When an AC cites a written spec (`AC-003 … prd.md §4.2` or `§FR-002`), it reports a cited section the spec doesn't have and any `FR-nnn` in the cited spec that no AC names and `## Out of scope` doesn't set aside. Until now L's plan self-approval judged "every requirement maps to an AC" by reading; it now runs the script first (`verify.py --feature <f> trace`, before `state.py new`) and treats a finding as a doubt. A full run prints the same findings as `trace:` notes, recorded in `verify.json` and in `status`, and never fails on them: advisory until its false-positive rate is known. Nothing runs when no AC cites a spec, so existing features and the S, low-risk M and trivial tracks are unchanged, and no migration is needed. It checks that references exist, not that an AC really covers its requirement, and it doesn't flag an AC that cites nothing (a failure-mode AC legitimately cites no requirement). Idea taken from AI-DLC's traceability sensor ([awslabs/aidlc-workflows](https://github.com/awslabs/aidlc-workflows)), cut down to what our change file can parse.

### Fixed
- **`$S` works in zsh, and with a plugin folder that has spaces.** The setup, upgrade and eject skill defined `S="python3 …/scaffold.py"` and ran `$S status`, but zsh (the macOS default shell) doesn't split a variable into words, so it looked for one command called `python3 /…/scaffold.py` (found by the 3.0 smoke test, where the agent worked round it with a function). `S` now names a shell function that quotes the path, and a test runs the documented lines in bash and zsh.

### Changed
- **sdlc-stepper draws a card on the desktop app.** The terminal keeps its text bar. On desktop the card has two rows: `SDLC` with the part and step the session is on beside it and the feature on the right, then one bar across the full width with each phase's status icon and its name, joined by lines that stretch to fill the room. Build's line carries a small icon per part, in the same icon set (a check when done, a pulsing dot when current, a dashed ring when blocked, an empty ring after). The card is white in the light theme and black in the dark one, and every element is neutral: one mid gray that reads on both, state told by shape, never by hue. Each icon has alt text (`Build: in progress`, `B2: done`). Checked by the stepper's tests and by rendering the icons on a white and a black card; the card's layout, whose connector lines are runs of `─`, has not been seen in the desktop app yet, so it may need a fixed-width SVG fallback.

Smoke test on 2026-11-03 at commit 0aa335f (runbook parts A to J). A and B were run by the maintainer in an interactive session (not re-run here); `claude plugin list` shows sdlc 3.0.0 installed from the checkout. C, D, E, G and H ran as headless `claude -p` sessions with `--plugin-dir` in throwaway repos, with the answers pre-given in each prompt: C, a greenfield setup (one commit per step, every file in the list, commands recorded, `.gitignore` patterns); D, the comment warning reached Claude and was acknowledged, a force-push to main and a fake API key were blocked; E, an S fix through stages 1, 2 and 4 with a red record per AC and `## Review` saying no review ran, and the Stop hook blocking a shell edit in `Stage 3 – Review` with the test command named; G, a brownfield two-package setup with the failing test in the baseline, then a change shipped past it with `--waive-baseline`; H, an upgrade from 2.5.0 that renumbered an active `Process: 2` feature from `Stage 4 – Build` to `Stage 2 – Build` (the status line named it and `/sdlc:start` resumed it in Build) and kept an edited guardrail, then an eject that kept the config, PRD, constitution and knowledge. A headless run can't answer a question, so "waits for your approval" was not re-checked. Not run: F (security hooks), I (Windows), J (other agents). The desktop card redesign was committed after this test, so none of these runs covered it.

## 2.5.0 — 2026-11-03

### Added
- **sdlc-stepper, a stepper bar above the prompt** (`/plugin install sdlc-stepper@sdlc`), so someone reading a session sees where the feature stands without reading the transcript: `✓ Define ─── ● Build ─── ○ Review ─── ○ Ship`, a square per backlog part, and the part and step (`B2 Title row · failing tests`). Phases come from the state file, parts from `backlog.md`, the step from the session's own calls (`verify.py red`, test or code edits, `git commit`, a review agent, `ship.py`, `gh pr create`, `gh pr checks`). It reads the session's folder or, when that isn't an sdlc repo, the sdlc repos up to two levels below it, and shows the one whose active feature changed last; with none it draws nothing. It only reads files and never holds a prompt or a tool call when it fails. It's a Claude Code hooks module (TypeScript, `plugins/sdlc-stepper/`), drawn in the terminal and the desktop app, and released with sdlc's version; Codex, Cursor and Antigravity don't get it. `/sdlc:setup` names it as an optional companion (off by default) when it writes the plugin keys. CI validates and tests it, and `test_marketplace` fails when a companion's version differs from sdlc's.

Checked on 2026-11-03: `claude -p` with `--plugin-dir plugins/sdlc-stepper` in a set-up repo loaded the module (`hooks module sdlc-stepper loaded … events: session.start, prompt.submit, tool.call, turn.complete, ui.render`) and its hooks settled without errors. The bar itself is drawn only in an interactive session, which this check didn't open; the module's tests draw it on the terminal and desktop surfaces. The full smoke test (A–J) was not rerun.

## 2.4.3 — 2026-11-03

### Changed
- **Updates name the phase, part and step, and stay short** (asked for by a teammate reading a backlog run). Every update starts `<Phase> · <part> · <step>` by name, never a stage number (`Build · B1 Title row · failing tests`), from a fixed list of step names per phase. While work goes as planned the agent says nothing of its own, and only that prefix and a few words when Claude Code asks for an update; a part ends in one line (`… · done (<commit>) · AC-001–004 pass · next: B2 <title>`), a feature in a short summary. A failure it couldn't fix, a deviation, a decision for the user or a hard stop still gets a few lines. The orchestrator's "What the user reads", `/sdlc:start`, spec 02 (ORC-FR-041).

### Fixed
- **A part's `verify.py` no longer fails on later parts' ACs** (found by the 2.4.2 smoke test and a teammate's run). It checked every AC in the change file, so part B1 failed on B2's ACs, which have no tests yet, and the session explained the false FAIL at length. While a part is `in progress`, an AC that only parts not started yet own (backlog.md's ACs column: `1, 2`, `AC-003–005`, `2-3`) is skipped and named (`not checked yet, later parts: AC-002 (B2)`), and so is the drift check for a task whose ACs are all theirs. The run records them as `skipped`, and `verify.py status` never offers it for reuse. With no part in progress (between parts, Feature close) everything is checked, and `ship.py` always checks everything.
- **A part is one commit.** `state.py slice <f> done B<n>` takes no commit now and runs before the part's commit, so its `done` row goes into that commit. Before, the row was set to `done <commit>` after the commit, which needed a second commit (`… marking the row done`), and amending the part's commit left a stale ID in `backlog.md`. A commit given is still written (`done <commit>`), and `backlog.py`, `autopilot.py` and the control contract's `slice_done` (its `commit` now null) read both forms.

Checked live on 2026-11-03 against `36f7d57`: a headless session given `autopilot` on an approved two-part backlog printed `Build · B1 subtract · done (05b86c7) · AC-001 passes · next: B2 multiply` and similar lines, `verify.py` passed on B1 with `not checked yet, later parts: AC-002 (B2)`, each part was one commit with its row `done` inside it, and it never ran `autopilot.py`. The full smoke test (A–J) was not rerun.

## 2.4.2 — 2026-11-03

### Added
- **product-rebuild is in the sdlc marketplace** (`/plugin install product-rebuild@sdlc`). The entry points at github.com/tammai/product-rebuild, which declares sdlc and sdlc-extras (`^2.4`) as dependencies, so installing it brings both. It's Claude Code only: the Codex, Cursor and Antigravity marketplace files that `scripts/hosts.py` builds still list sdlc alone.

### Fixed
- **Asking for autopilot in a session runs it in that session** (found by a smoke test). Asked mid-backlog, the session tried `scripts/autopilot.py`, whose headless sessions couldn't read the plugin's own files, then asked whether to run the parts here or have the user widen `permissions.additionalDirectories`. Now a request for autopilot in a session runs every remaining part, then Feature close, here and without asking: it skips `Slice gates` and the context stop at part boundaries (the part's commit and `## Handoff` carry it past compaction), takes Review's recommendation, blocks a part that would add scope and goes on with the others. The session never starts or offers `autopilot.py`; it stays the user's terminal command for headless runs. `backlog-slices.md` step 6, `/sdlc:start`, the orchestrator, README, guidebook, playbook, PRD and spec 02 (new ORC-FR-040) say the same; the playbook now also says the headless sessions may need the plugin's folder in `permissions.additionalDirectories`. Checked live on 2026-11-03 against `fa53200`: a headless session from the checkout, given only `autopilot` on an approved two-part backlog, logged in-session autopilot, built both parts, ran Review and Ship, asked nothing and never ran `autopilot.py`. The full smoke test (A–J) was not rerun for this rules-only change.

## 2.4.1 — 2026-11-02

### Fixed
- **`/sdlc:doctor` warns when sdlc is turned off for the repo** (found by the 2.4.0 smoke test). With `"sdlc@sdlc": false` in `.claude/settings.local.json` (or the committed `.claude/settings.json`), no sdlc hook runs, so a force push to main and a real-looking API key both went through unflagged, and doctor still reported the plugin as `ok`. Doctor now warns, naming the file and the fix. When it runs from a checkout (`--plugin-dir`), the `false` that the headless-test recipe sets is expected and reported as `ok`. Setup's `enable-plugin` still leaves a `false` the user set in place, without a warning; doctor is where it shows.
- **Eject and `enable-plugin --remove` no longer delete a plugin key the user changed** (found by the same smoke test). The lock records which keys sdlc wrote, not their values, so a `"sdlc@sdlc": true` that sdlc wrote and the user later set to `false`, or a superpowers turn-off the user set back to `true`, was deleted, quietly changing which plugins load. A key whose value is no longer the one `enable-plugin` writes (`true`, or `false` for a conflicting plugin) now stays, and the result lists it under `kept`. Marketplace entries are removed as before.

## 2.4.0 — 2026-11-02

### Added
- **Hookify and the role guard work in a session started above the repo** (requested for product-rebuild, which starts in a workbench folder holding several repos and worktrees, each set up for sdlc). Before, both read only the session's folder (`CLAUDE_PROJECT_DIR`): its guardrails never loaded (`cd api && git push --force origin main` was allowed), and the role guard judged paths against the wrong root (a code-reviewer writing `api/.sdlc/.work/findings/r.md` was denied). Now `sdlc_layout.target_repo` finds the repo a call acts in, the nearest folder strictly inside the session folder with `.sdlc/config.json`, from a file tool's path or a command's leading `cd`/`pushd`, `git -C`, `--git-dir` or `--work-tree`, else the call's cwd. Hookify adds that repo's rules to the session's (an enabled rule of the same name in the repo replaces the session's); the role guard judges the path against that repo and its `docs_dir`.

  Exactly what changes: only a session whose folder has no `.sdlc/` at all, and only for a PreToolUse call into a folder below it that has `.sdlc/config.json`. A session started in a repo with `.sdlc/` (set up or not) is unchanged, and a nested sdlc repo below it is never read: checked by running 396 hook calls through 2.3.1 and this change in a set-up repo, a `.sdlc/`-without-config repo and a plain folder, each holding a nested sdlc repo with its own rules; the first two gave identical output, the plain folder differed only on calls into the nested repo. Not covered: Codex (its hooks get no project folder), commands that change folder inside `bash -c` or a script, more than one repo per command (the first named wins), and the other sdlc hooks (freshness, prove budget, model router, review rounds, trust anchor, stop), which still read only the session folder's features and so stay silent there.

## 2.3.1 — 2026-11-02

### Fixed
- **Setup no longer says the committed `.claude/settings.json` gives cloud sessions sdlc** (#7). Per the Claude Code docs a cloud session doesn't install the plugins a repo's settings turn on, so `enable-plugin --team` only helps teammates on their own machines. Setup stops recommending the team file for cloud work and, for a user who works in cloud sessions, points to the guidebook's new "Cloud sessions" section: organization-wide server-managed settings, or a setup script on the cloud environment. This corrects the 2.3.0 notes below; the README, guidebook, playbook, SET-FR-012, spec 11, the setup diagram's description, the `2.3.0-team-plugin-keys` migration and the cloud-sessions gotcha say the same. Not run in a real cloud session.
- **The suite is green on a stock Intel Mac** (#8). Three tests failed there for two reasons the 2.3.0 notes ran together. `test_prove_budget`'s two wrapped-command tests need a `timeout` or `gtimeout` binary, which macOS has without coreutils; they now skip without one, and a new test covers the no-binary path (only the tool `timeout` is lowered). `test_sg_python`'s hook-times test needs bash 5 for `EPOCHREALTIME`, and macOS's `/bin/bash` is 3.2, so it skips there. The runbook's R10a now says `SDLC_HOOK_TIMES` logs nothing under bash 3.2.
- **A brownfield repo can ship past the failures its baseline lists** (found by the 2.3.1 smoke test). `ship.py` reruns `verify.py`, which never read `.sdlc/baseline.md`, so a repo with a known failing test could pass Build's gate (logged by hand) and then never finish Ship. `ship.py --waive-baseline` now lets a failed run through when only the test step failed and the baseline lists failing tests, and writes the waiver to the Gate log. It does not check that each failure is the listed one; the agent does, as at Build's gate.
- **`NOTICE.md` records the upstream commits the vendored code was last compared with, and every local patch** (#8). Superpowers v7.0.1 is in sync. Anthropic's plugins differ only by sdlc's patches (several were unlisted: narrowed agent tools, hookify's regex timeout, `NotebookEdit` and message limits) and by what sdlc leaves out on purpose: the security hook's telemetry and `code-review`'s new `haiku` gate, `--comment` default and inline-comment MCP tool. `/sdlc:code-review` takes upstream's agent-assumptions block. Re-syncing means updating that record (CONTRIBUTING).
- **A test fails any `SKILL.md` that reaches 20,000 characters** (#8), the size at which Claude Code truncates a skill after compaction. The largest is `setting-up-projects` at about 17,900.

Smoke test, 2026-11-02, run headlessly (`claude -p` with the checkout as `--plugin-dir`, throwaway repos, approvals given in the prompt) against the commit before this one: parts A, B, C, D, E and H passed; G passed its setup and baseline steps and found the Ship bug above, whose fix was checked by running `ship.py` on that stuck feature, not by a second full session. Not run: F (security hooks), G.4 (monorepo), I (Windows) and J (other agents), and nobody has run the cloud-session fix in a real cloud session. Setup's "where do the plugin keys go" question was not exercised, because a `--plugin-dir` run skips that step.

## 2.3.0 — 2026-10-29

### Changed
- **Setup asks where the keys that turn sdlc on go: this machine, or the team's committed `.claude/settings.json`** (user feedback: `.claude/settings.local.json` is never committed, so a cloud session, which starts from a fresh clone, ran without sdlc and its companions). `scaffold.py enable-plugin --team` writes the sdlc marketplace and `enabledPlugins` for sdlc and the companions that are on (`sdlc-extras` when picked) to `.claude/settings.json`, recorded so `--remove-team` and eject take back only those; once the team file holds them, a later `--with` and upgrade's re-run add there too. Turning a conflicting plugin off (superpowers) stays in the local file: it's one machine's setting. A local run never shadows a key the committed file already has. `/sdlc:doctor`'s companion check reads both files. Migration `2.3.0-team-plugin-keys` offers the switch to repos already set up.

Migration `2.3.0-team-plugin-keys` is offered to a repo on 2.2.0 (checked with `scaffold.py migrations`). The suite and `claude plugin validate .` pass, apart from three tests that also fail on 2.2.0 on an Intel Mac without `timeout` (`test_prove_budget` x2, `test_sg_python`'s hook-times launcher). The full release smoke test (parts A–J) and a live setup in a cloud session weren't run.

## 2.2.0 — 2026-10-29

### Added
- **Cloudflare's `security-audit` skill is an optional companion.** It is the first companion that's a skill rather than a plugin, so sdlc never installs it: setup's `enable-plugin` step lists it with whether it's installed and its install command (`npx skills add https://github.com/cloudflare/security-audit-skill --skill security-audit`). It is never part of a change's review. On L, when the security review fired on a sensitive path, the end-of-Review message says a full audit is available; it runs only when the user asks, and its confirmed findings are handled like the security review's. Why it isn't the per-change security reviewer: on the eval's L pre-review code its focused review (58 s) rated the clone command pasted into a shell as hardening only, and a full `quick` audit scoped to the diff (8 min, $1.59) confirmed nothing. The plugin's security reviewer rated that issue medium, and it was fixed.

### Changed
- **A bug a review finds is fixed before Ship without asking, whatever its severity** (user feedback: a finished feature ended by asking whether to fix bugs its review had found): a medium or low finding that's a bug in code the change touched (wrong behaviour, a crash, an unhandled error, a missing test for something it does) goes back to Build with the highs, test first. Only what isn't a bug in this change (an improvement, hardening the brief didn't ask for, code it didn't touch) is a ticket, and Review and Ship never end by asking whether to fix one. Reviewers mark such a bug `(bug)` and it makes the verdict FAIL like a high.
- **Review fixes its bugs once, then checks the fixes, and a hook holds the cap** (new `hooks/review_rounds.py`): round 1 reviews the whole change and its bugs are fixed; round 2 reruns the review that failed on just the files the fixes touched, told round 1's findings, and reports whether each is gone and whether a fix added a bug (anything else is a ticket). Before, the review never ran again, so nothing showed the fixes worked. When round 2 still fails, the agent stops and asks you: one more fix round, a waiver, or stop. Until you reply, the hook denies every edit, shell command, subagent and skill but a reviewer's own report and a test run (the project's test command or `verify.py`); each message you send allows one more round. The highest round seen is kept in `.sdlc/.work/review-rounds.json`, so deleting a report doesn't reset it, and round numbers continue from the highest report in the findings folder, so a resumed Review never overwrites one. In Codex, Cursor and Antigravity too, through `hosts/hook.py`. Checked headless on the eval's M code with a seeded high: the fixes went in without asking, the cap stopped the agent and denied its next command, and a reply allowed exactly one more round. An earlier cut of 3 full rounds was dropped: each full re-review found new small issues, so the rounds didn't settle. The check of the fixes adds about 40-90 s on M whenever round 1 finds a bug.
- **Define's reading is two turns at most, and the change file is written straight off** (the eval of 1817fc0, 3 M runs: time 3.90x median, tokens 2.34x; before Build 83–124 s, with 2–4 read turns after `brief.py` and a 33–58 s silent pause before the change file): sizing reads the expected track's flow file beside `brief.py` and the named code, then one more parallel turn at most for the code and tests the file list points to; a low-risk M writes one AC per behaviour the request names, settling details from the code it read, without drafting the file first.
- **Risk names what a public API change is:** a breaking one, removing or changing an exported signature, an HTTP endpoint, a CLI flag, or output the README or docs say programs read. Adding a command, flag or field, changing text people read, or adding an optional field to stored data is low. On the eval's M task (a `priority` command and a sorted plan), one headless run thought for 2 min over whether CLI output and the saved file counted, called it high and stopped for approval; the eval's run had called it low.
- **Define reads in one call, and a low-risk M writes a short change file** (the eval of 83de649: M at 4.1x time, 2.2x tokens; Define still took 113 s over 4 read turns and two long drafting pauses): `scripts/brief.py` prints everything Define reads before the code (config, baseline, knowledge index, recurring defects, constitution, PRD, README, manifest, tracked files, change template), run when the request is sized, so the router's reading and Define's are one turn beside the code; a low-risk M's change file is Why, the ACs and their tests and must-never-break, with Decisions, failure modes and out of scope only when there's something to say. High-risk M and L keep the full form.
- **Define on M is shorter** (the eval of f06c56c spent about 2 min before Build, mostly thinking and writing): `state.py new` writes the state file from Define's answers (track, risk, tasks with their ACs and files, public surface, handoff), looking up Base, Owner, the test command and the date, in the same shell call as the move to Build and the red run, so the agent writes only the change file; Define reads everything it needs, the change template and the PRD included, in one turn; sizing is a lookup (count the files, take the first row that fits) rather than a deliberation. A full security audit, when the user runs one, always leaves a line in `## Review`, even when it confirms nothing.
- **M's bar is 3x plain Claude with a review step added, 4x in time** (was 1.5x): plain plus review finishes an M in about a minute, and the change file, state file and red tests alone take about that long. The time bar was set from measurement: across four eval rounds of cuts (83de649, 1817fc0 x3, 7c9b385) M held at 3.9–4.1x time (Define about 1.6 min, Build 0.9, Review 1.1, Ship 0.4) and 2.2–2.3x tokens, with hidden tests level and the rubric above the baseline.
- **From the eval of f06c56c:** Review writes `## Review` with the Edit or Write tool, and the Review command budget's refusal of a heredoc now says so (an M lost a turn appending with `cat >> … <<'EOF'`); a decision record in `knowledge/decisions/` is only for a decision later features must follow, not this change's own behaviour; a brownfield PRD draft lists only non-goals the README or docs state (the planner repo's draft had guessed "no priorities", the next feature).
- **The code review on S and M uses Claude Code's built-in `/code-review`** where the agent has it: `medium` for default depth, `high` for high, the level always passed (it is sticky otherwise) and no `--fix`. It runs in its own subagent, mostly on Sonnet, in about 40–90 s against the plugin reviewer's minutes on Opus; the agent rates each finding against the change file (high when it would fail an AC, break a must-never-break line or the spec, lose data or be a security issue) and fixes highs test first as before. L, and Codex, Cursor and Antigravity (no built-in review an agent can call), keep the plugin's `code-reviewer`; security and UI reviews are unchanged. Tested on pre-review code from the eval: on M (abc87f5) the built-in review found the high the plugin's reviewer found (a stored `"priority": null` read as `normal`); on L (c925268) it missed both highs the plugin's reviewers found (TRACE answered 500, charts stuck on "Loading chart..." after an error) in three runs at `medium` and `high`, so L keeps them.

No migration: nothing a project owns changed; `/sdlc:upgrade` brings the regenerated files (the change template's guidance). Checked on 2026-10-29 at the release commit's tree: the suite and `claude plugin validate .` pass, and headless sessions on Windows ran an S fix end to end (smoke E: sized S, red first, no review fired, shipped, `Status: done`) and an M Review with a seeded high (round 1 fixed it without asking, round 2 checked only the fixes and passed) and the round cap (stopped, denied, one round per reply). The eval measured M at 3.9–4.1x time and 2.2–2.3x tokens against plain Claude plus a review over five rounds, with hidden tests level. Smoke parts A (the interactive `/plugin` install), B, C, D, G and H weren't rerun: setup, guardrails, upgrade and eject are unchanged since 2.1.0 except the companion listing, which the suite covers. Known gap: `docs/diagrams/sdlc_plugin_layers.svg` names the review-rounds hook only in its description, not in its drawn labels.

## 2.1.0 — 2026-10-29

### Added
- **UI design work can go to impeccable** (ADR 0021): setup's design step asks who does UI design, sdlc's builtin design system or the [impeccable](https://github.com/pbakaus/impeccable) skill, recommending from the PRD, and records it (`design` in `.sdlc/config.json`, `scaffold.py design`). In impeccable mode `design-system.md` points at `DESIGN.md`, Define plans UI with `/impeccable shape` and keeps its brief in the state file, impeccable's detector hook replaces the hard-coded-values guardrail, and `ui-reviewer` keeps the verdict with impeccable's `detect` and `audit` as evidence. sdlc never installs impeccable; missing, each step falls back to builtin and `/sdlc:doctor` warns. Existing repos are offered the choice by migration `2.1.0-design-mode`; without it nothing changes.
- **impeccable's own agents get through the model router** while a feature is active (they're spawned with no model).

Migration `2.1.0-design-mode` offers set-up repos the design choice; declining it changes nothing. Checked live on 2026-10-28 and 2026-10-29 in headless sessions on Windows with impeccable 4.8.0 installed by `npx impeccable install`, in a small React app: setup in impeccable mode, an S UI change through Define (`shape`), Build (impeccable's detector hook fired) and Review (`detect` and the audit checks cited), and the fallback with impeccable missing. Not exercised live: impeccable's own agents passing the model router (covered by the suite), and a new screen that makes impeccable write `DESIGN.md`. The full release smoke test (parts A–J) wasn't rerun; the suite and `claude plugin validate .` pass.

## 2.0.1 — 2026-10-28

### Changed
- **sdlc turns itself on in `.claude/settings.local.json`, never the committed `.claude/settings.json`,** so setup no longer asks: the file is this machine's (if git doesn't ignore it yet, `enable-plugin` adds it to `.git/info/exclude`, not the team's `.gitignore`). Teammates are no longer offered sdlc by the repo; each one's own setup or `/sdlc:upgrade` turns it on for them. Upgrading asks whether to keep the `.claude/settings.json` keys an earlier setup added (`enable-plugin --remove-team` takes back only those; migration `2.0.1-local-plugin-keys`).

### Added
- **Companion plugins, as data:** the plugin's config defaults list `companions` (id, marketplace, a one-line reason, on by default or not), starting with `sdlc-extras`. `enable-plugin` turns on the ones that are on by default, names the rest in one line, and adds one with `--with <id>`; an id that isn't listed is refused. Pairing another plugin is a new entry, not new code. `/sdlc:doctor` warns when a companion is turned on for the repo but not installed on this machine.
- **Conflicting tools, as data too:** the shipped `conflicts` list names plugins and repo files that clash with sdlc. A plugin (superpowers, whose skills sdlc carries its own copies of) is turned off for this repo only, in `.claude/settings.local.json`, and setup warns you which and why; it stays on in your other projects, and `enable-plugin --remove` undoes it. Files written into the repo (spec-kit's `.specify/` and `speckit.*` commands) can't be switched off, so setup tells you and asks whether to keep them or remove them. `/sdlc:doctor` warns while either is still in play. Companions and conflicts are read only from the plugin's shipped defaults, never the repo's `.sdlc/config.json`, so a repo can't name a plugin for setup to turn on.

## 2.0.0 — 2026-10-28

**Before you update:** finish every feature in progress with sdlc 1.8.1, or archive it (`Status: done`). 2.0 can't run a feature started under 1.x, and `/sdlc:upgrade` waits until none is active.

### sdlc 2.0: the slim process core (ADR 0020)
- **The same record at every size, in two files**: the change file `docs/sdlc/changes/<feature>.md` for people (why, decisions, a bug's proof and cause, acceptance criteria each with its test, must-never-break lines, out of scope, and the review after the build) and the feature's state file for the agent (where it stands, and how it's built: tasks, files, public surface, deviations). Both are kept. No more `intent.md`, `spec.md`, `plan.md` or `review.md`, and no per-feature documents folder: a split feature's `backlog.md` and its parts' `plan-B<n>.md` go in a work folder beside the state file (`.sdlc/state/<feature>/`), with QA and release reports. Features from before 2.0 keep `docs/sdlc/intents/<feature>/`; `/sdlc:upgrade` moves a legacy repo's change files to `changes/`.
- **Intent before code.** The agent asks only when what, why or how isn't clear, one question at a time, at any size. A bug is proven first, then its root cause, then the fix. S doesn't stop before the build; on M and L you read and approve the change file.
- **The builder works like plain Claude:** no review agents during the build; tests still recorded failing first (`verify.py red`). The agent decides before the build whether it runs inline, in parts across fresh sessions, or with parallel subagents.
- **Reviews are recommended after the build** (security; code at default or high depth; UI; advisor where available; or none). S runs a fixed trigger list instead (security for high risk or a sensitive or migration path, UI for a UI path, code at default depth for a declared public surface; otherwise none), M and L use fixed triggers too (default: a declared public surface, a large diff, or L; high: high risk, or a crash or concurrency failure mode); high-risk M and L ask you. Each review runs once, on opus.
- **Learn before merge:** lessons land in the project's knowledge in the same change. Then green locally and on CI (one CI fix, then it asks), and it stops at the PR.
- **Trivial changes skip the workflow.** Start, implement and fix requests trigger it in a repo set up for sdlc (brainstorm requests go to the brainstorming skill), but a change no test could see (a typo, a rename, docs, an untested config value) is just done and committed, with no record. Any bug fix or behaviour change is at least S, so the same request always takes the same path.
- **S runs from one file** (`references/s-track.md`: the whole flow and the record's shapes inline) and goes from Build straight to Ship. On a one-line fix it took 23 turns instead of 40.
- **`verify.py`:** writing the record after a passing run (the change file's review, a lesson) no longer counts as a code change, files the tests leave behind (`__pycache__`, `*.pyc`, tool caches) are never drift, and a task that changes only Markdown (a README) is no longer flagged as not done.
- **Low-risk M runs unattended:** it shows its plan and builds without waiting for "approved" (the Gate log says it wasn't stopped), and its review is decided by a fixed list like S's: nothing fires (every AC seen failing, then passing; no public surface, large diff, UI path or `manual` AC) → no review, straight from Build to Ship; what fires runs without asking. High-risk M still stops for the approval and the review choice. L reasons through both first, as autopilot would (every requirement mapped to an AC, no open questions, every decision settled by the request, spec, code or knowledge, nothing extra or irreversible; the reviews the table names), logs why it went on, and asks only when a check leaves a doubt.
- **L points to its spec and stays one part:** when the request or repo already has a written spec (a PRD, design doc, mock, a ticket with requirements), the change file links it instead of restating it: `## Why` is one line, each acceptance criterion names the requirement it proves, and Decisions and failure modes hold only what the spec leaves open; the brainstorming interview is skipped when the spec settles the design. Work splits into parts only when it won't fit one session, since each part repeats the whole loop.
- **One test may prove several acceptance criteria:** their rows share its Run command, and `verify.py` runs it once (red and full run), recording red for each.
- **Two code-review depths, default and high:** low depth is gone, since it only re-proved what `verify.py` proves (each AC's test red, then green). A declared public surface (S and M), a large diff or L fires default; a `manual` AC is checked by whichever review runs, or by the session.
- **A finding that breaks a requirement is fixed before Ship:** the reviewer names the requirement each finding breaks (an AC, a must-never-break line, the linked spec, a constitution rule), and any that names one is high; the session checks every medium and low against the same list and raises it if it breaks one. Only the rest become tickets. (The gh-rising eval shipped a data-loss bug its own reviewer had filed as a ticket.)
- **Cheaper reviews:** the reviewer reads the brief itself (the session doesn't), gets the diff as one command and the AC ids, doesn't call an advisor, and keeps its report to about 30 lines.
- **Ship is one command:** `scripts/ship.py <feature>` checks the owner, writes `## Review` from `--review` when there's none, reuses the last passing `verify.py` (or reruns it), advances to Stage 8, sets `Status: done`, branches off the default branch, stages the change and writes the commit message (the change file's title, or `--message`); the commit, push and PR follow in the same call, so the commit carries the finished record. The commit security review treats the commit that finishes a feature as that feature's. A reviewed change advances to Stage 8 when it writes `## Review`, so Ship's call runs outside Review's command budget.
- **Leaner Define:** a SessionStart hook puts the setup state, the record's paths, the remote and the active features in context, so no `scaffold.py status`/`paths` call; `/sdlc:start` carries the orchestrator's text, so no skill load; the record, the tests and the red step go in one turn on S and low-risk M.
- **Every set-up project has a product doc (PRD):** setup's new `prd` step, before the constitution, uses a PRD you already have as is (and records its path, `prd` in `.sdlc/config.json`), or drafts one, from a short interview on a new project or from the README, docs, routes, models and screens on an existing one, with every guess marked "inferred, confirm". It's written to `docs/sdlc/prd.md` only after you approve, and it's yours: sdlc never overwrites it and eject keeps it. Define reads it as background when a change touches product scope; `/sdlc:doctor` warns when a set-up repo has none, and `/sdlc:upgrade` offers the same step (migration `2.0.0-prd`).
- **Setup's CI for a stack written as one name:** `"stack": "node"` in `.sdlc/config.json` (as often written as `["node"]`) was read letter by letter, so the generated workflow had a `# TODO` line per letter instead of the toolchain setup.
- **Review's command budget** lets quick reads chain in one call (`git remote -v; git branch --show-current; tail -5 <file>`); they run without the 120 s wrapper.
- **Fewer turns per change:** `verify.py red` takes every AC in one call (all recorded or none), a passing `verify.py` prints the head and tree `state.py verified` takes, each phase's state move goes in one shell call with its next step, Ship commits, pushes and opens the PR in one call with git and `gh` (no `/sdlc:commit` skill load), the builder batches independent edits, the references are read in two batches, and the gate messages and the final summary are short.
- **One file per track, and fewer turns:** the orchestrator skill is a short router; S reads `references/s-track.md` and M and L read `references/flow.md` (its turn plan, rules and all four phases), once. `state.py advance … --verified <head> <tree>` records the passing verify and the move in one call. 
- **Phases are Define, Build, Review, Ship** (stages 1, 4, 5, 8); a 2.0 feature's state carries `Process: 2`.
- **Learn records lasting decisions:** a decision in the change file that later features must follow (a library, a data shape, a boundary) gets a record in `knowledge/decisions/`, linked from the index; Define treats recorded decisions as constraints.
- **Removed:** Prove and its rounds, Lite/Full, `Prove: run|skip`, the verifier, ac-checker and code-architect agents, the relay, and the skills writing-specs, clarifying-specs, designing-solutions, analyzing-consistency, executing-plans, subagent-driven-development and writing-plans. Every command you type keeps its name.

### Also since 1.8.1
Work done after 1.8.1 that 2.0 keeps (earlier steps toward 2.0, such as Prove, the relay, `intent.md`, the Lite flow and the verifier, were replaced before release and aren't listed).

**Changed**
- **The model security review runs only for security-touched work** (ADR 0019): the turn-end and commit reviews run only while a feature is active and its change is security-touched (`Risk: high`, or `areas.sensitive` or `areas.migrations` touched); a feature's build commits are reviewed once, as one net diff, when the change is ready. Pattern warnings, secret blocking and the push review are unchanged.
- **The reviewer's SDK installs lazily:** SessionStart no longer builds its venv; the first edit in a security-touched feature starts the install in the background.
- **Fewer skills, same commands:** `dispatching-parallel-agents`, `using-git-worktrees`, `receiving-code-review`, `finishing-a-development-branch`, `requesting-code-review`, `claude-md-improver` and `trimming-context` are references the flow reads when needed; `/sdlc:hookify` is one skill. Every command people type keeps its name. The always-loaded listing dropped from about 2,740 to 1,960 tokens per call.
- **`sdlc-extras`,** a companion plugin in the same marketplace (`/plugin install sdlc-extras@sdlc`): the Ralph loop, hookify's `list`, `configure` and `help`, and the `feature-reviewer`, `conversation-analyzer`, `type-design-analyzer`, `comment-analyzer` and `code-simplifier` agents.
- **Models:** no Haiku anywhere (the model router denies it); the cheap tier is Sonnet with `effort: high`; every review runs on Opus. Untrusted input reaching a shell, terminal, file path or database sets `Risk: high`.
- **Faster hooks, about 30% per event** on Windows: each hook starts the Python `hooks/sg-python.sh` found and remembered (it skips the Microsoft Store `python3` stub); the security hook loads its HTTP and TLS modules only when it calls a model. `SDLC_HOOK_TIMES=1` logs each hook's time to `.sdlc/.work/hook-times.jsonl`.
- **Deploy is the on-request `/sdlc:deploy`,** no longer a stage; Operate is removed.
- **Feature names carry their track:** `<yyyy-mm-dd>-<s|m|l>-<slug>` (with a ticket: `<yyyy-mm-dd>-<s|m|l>-<ticket>-<slug>`).
- **Records are written with the file-writing tool,** never through the shell, whose quoting broke on backticks and `$`.
- **Setup doesn't change your product's manifest or dependencies** without asking (no `bin`, `engines`, `packageManager`, devDependency or tool), and `/sdlc:setup` and `/sdlc:upgrade` untrack files committed before their ignore lines existed (for example `.sdlc/.work/trust-anchor.json`), keeping them on disk.
- **`scaffold.py enable-plugin` skips** when the session runs sdlc from a directory (`--plugin-dir`) or sdlc isn't installed, so it never enables a second copy.
- The trust anchor shows a change that only adds checks (Track up, Risk low → high) without blocking; moving the other way still needs your next message.
- The control contract's `state.json` gains `phase` (`define`, `build`, `review`, `ship`), and `contract_version` is 2.
- The contributor `CLAUDE.md` moved to `.claude/CLAUDE.md`, and `plugin.json` has `homepage` and `repository`, so `claude plugin validate --strict` passes.

**Fixed**
- A crash window in a write (a lock created then written, a write then a rename) is a high finding when the spec says a killed process must not leave the system unusable; fixes go in at the rule, not the instance.
- Review's command budget can't be skipped by chaining after a project command (`npm test && sleep 900` is timed), and lets `VAR=value` steps through before a timed command.
- Hookify: prompt rules fire (`field: user_prompt` reads Claude Code's `prompt`), rules stay on their own event, the hooks print nothing on their own errors, and the never-registered `hooks/posttooluse.py` is removed.
- The freshness hook recognises the plugin's `verify.py` after `cd <dir> &&`, with redirects, and followed by `| tail`, `| head`, `| grep`, `| cat` or `; echo …`.
- `/sdlc:prune` also deletes a finished feature's part plans (`plan-B<n>.md`).

**Added**
- **`scripts/state.py`:** every change to a feature's state in one call (`advance`, `verified`, `log`, `deviation`, `slice`, `blocker`, `set`, `sync`), which also writes the control contract for a runner or control app.
- **Parts and autopilot:** work too big for one session gets `<work>/backlog.md`, built one part at a time; `scripts/autopilot.py <feature>` runs each part in a fresh headless session.
- **`/sdlc:context-diet`** trims what Claude Code loads into every call for a project (enabled plugins, personal skills, MCP servers), with or without sdlc set up; setup offers it on Claude Code.
- **Failure modes and recurring defects:** the change file lists the failure modes that apply as criteria or must-never-break lines, and every reviewer checks them along with the plugin's and the project's `recurring-defects.md`.

## 1.8.1 — 2026-10-25

No migration. Only the hook adapter for Codex and Antigravity changed, which Claude Code doesn't load: the suite covers it, and the plugin installs as 1.8.1 in Codex, Antigravity (Windows and WSL) and Cursor with its hooks registered.

### Fixed
- In Codex, a command whose output starts with `Exit code: 0` no longer counts as a passing test run: Codex sends a command's raw output, so that text came from the command. A full test run there always records `unknown`.
- In Antigravity, the hooks match write tools by verb (edit, write, replace, create, delete, patch, move, rename, notebook), so `multi_replace_file_content`, `edit_notebook` and later ones are checked too.

## 1.8.0 — 2026-10-25

No migration. The new CI check and its workflow reach set-up repos through `/sdlc:upgrade`, which asks first; the `AGENTS.md` block rebuilds itself; a state file without `Owner:` counts as unowned. Smoke test passed 2026-10-25 in interactive Sonnet sessions on Windows (parts A–H; G4, I and J not rerun; J ran per agent during development, see spec 11). Greenfield and brownfield setup both added the invariants check, and it passed on their first features, including a `+dirty` round. Known issue: the command allowlist uses prefix wildcards (`Bash(pnpm test:*)`), which the security review flags because any arguments pass; setup and upgrade add them back.

### Added
- `sdlc-invariants` CI checks the shared sdlc files whichever agent or person changed them (`.sdlc/ci/invariants.py`, `.github/workflows/sdlc-invariants.yml`). For active features: the latest test-report round must be complete, and on pull requests must name a commit in the code's history. Baseline growth needs a Deviations entry naming it, in any feature. No `[inferred]` tags past Stage 1. Setup's `ci` step adds it, and `/sdlc:upgrade` offers it to repos with an sdlc verify workflow.
- A feature's state file records `Owner:` (git email) and `Tool:` (the agent). Before advancing someone else's feature, the orchestrator, and other agents through `AGENTS.md`, ask first and record the handover.
- With Codex among a repo's agents, `scaffold.py agents` and `/sdlc:doctor` warn when the root `AGENTS.md` passes 32 KiB. Codex stops reading there, so it would miss the end of the sdlc block.
- The plugin installs in Codex, Cursor and Antigravity as well as Claude Code (manifests built by `scripts/hosts.py` and checked in CI; setup smoke-tested in each, see spec 11). Setup detects which agent runs it, from the plugin's install folder or the environment, without asking, and records it in the lock (`hosts`). The Claude Code files (`.claude/rules`, guardrails, allowlist) are written only on Claude Code. Other agents get one managed block in `AGENTS.md`, which they all read: the workflow rules, `CLAUDE.md`, the plugin's policy rules and your own `.claude/rules/`. A second agent opening a set-up repo joins it (`scaffold.py add-host`) and adds only its own files. Claude Code sees your own `AGENTS.md` text through a generated `.claude/rules/sdlc-agents-md.md`. Claude-only lines are rewritten, or stop the build with the file and line. Upgrade rebuilds the block, eject removes it, and `/sdlc:doctor` warns when it's out of date. Spec 11, ADR 0007, #1.
- Codex and Antigravity get `start`, `setup`, `upgrade` and the other commands as skills (`hosts/skills/`, built by `scripts/hosts.py`), because neither loads a command that takes arguments. The Ralph loop and hookify commands are left out: the Ralph loop's hook runs only in Claude Code, and hookify rules live in `.claude/`, which only Claude Code's setup writes. Codex no longer adds its own partial copies of the commands.
- Antigravity installs from `python3 scripts/hosts.py dist antigravity <folder>`, a copy whose agents it can load. A direct install from the repo loads 3 of the 13 agents. Claude Code's agents are unchanged.
- In Codex, Cursor and Antigravity, the freshness hook, the trust anchor and the hookify guardrails now run through `hosts/hook.py`. It turns each agent's hook payloads into Claude Code's and runs the same scripts. So Stage 5 can't finish on stale test results, and a guardrail rule denies the command. In Codex, trust the hooks once in `/hooks`. In Antigravity they run in the CLI, from the `hosts.py dist antigravity` install. Claude Code's hooks are unchanged.
- `/sdlc:doctor` skips the `jq` and security-reviewer checks in a repo without Claude Code, since only Claude Code's hooks use them.
- Shell scripts are checked out with LF line endings on every platform (`.gitattributes`), so WSL bash can run them from a Windows clone.
- `todo` skill: "add a todo" or work left out on purpose is recorded in `todo.md` in the sdlc docs folder instead of a `TODO` comment in code, and moved to Done when finished.

### Changed
- `/sdlc:start` with a GitHub issue, Linear or Jira link now reads the ticket before sizing the work (`gh issue view` or the tracker's MCP server) and uses it as the request. If the ticket can't be read, it asks for the text instead of guessing from the URL. A ticket link pasted on its own, without `/sdlc:start`, now starts the orchestrator too.
- The plugin and marketplace descriptions now match the README: S/M/L sizing, up to 11 gated stages, a fresh verifier, design-system-aware UI review and any stack or monorepo. New keywords: `orchestrator`, `monorepo`, `claude-code-plugin`.

## 1.7.1 — 2026-10-23

No migration. Only the role guard changed: the suite covers it, and a headless smoke run checked that the plugin loads as 1.7.1 and that the guard still holds a live verifier to its report. 1.7.0's full smoke test covers the rest.

### Fixed
- The role guard no longer lets the verifier or qa-tester write a report through a path containing `~` or `:`. On Windows, a short name like `WORK~1` could reach `.sdlc/.work/` by another spelling.

## 1.7.0 — 2026-10-23

Migration: `1.7.0-artifact-layout` (moves existing repos; `/sdlc:upgrade` previews it first).

Smoke test passed 2026-10-23 in headless Sonnet sessions on Windows (parts A–E, G, H). Brownfield setup first went past its command approval, which is fixed below and passed on rerun. Known issue: after `/sdlc:eject`, the trust-anchor hook recreates an untracked `.sdlc/.work/` at the end of that session; delete it.

### Changed
- sdlc documents now live with your project docs. The constitution, the design system and each feature's brainstorm, spec, design, plan and reports go to `docs/sdlc/` (features in `docs/sdlc/intents/<date>-<ticket>-<slug>/`). `.sdlc/` keeps only what the plugin runs on: config, lock, baseline, CI and lint snippets, scratch, and one state file per feature in `.sdlc/state/`. If your repo publishes `docs/` as a site (Docusaurus, MkDocs, VitePress, Sphinx, Starlight), setup and upgrade ask where the documents should go instead, `.sdlc` included, and record it as `docs_dir`.
- `/sdlc:upgrade` moves an existing repo with `git mv`, so history follows the files. It shows the moves first and warns about features still in progress, whose open branches will see the renames. Until you upgrade, everything keeps working on the old layout, and `/sdlc:status` and `/sdlc:doctor` remind you.

### Fixed
- Brownfield setup now stops and waits after proposing the commands, and after each audit batch, before writing anything. It used to record the commands and area rules first and report afterwards. A skipped audit writes no area rules.

### Added
- Setting up a new repo with two or more apps (say web, an API and mobile) now builds one monorepo: `apps/` for the apps, `packages/` for shared code, `docs/` for BA, QA and design files, and `infras/` if you want it. Setup asks who will work in the repo. A large team with separate roles also gets CODEOWNERS, a CI workflow per app that runs only when that app or shared code changes, and a release runbook with per-app tags. A solo developer or small team gets one CI workflow.
- When one app serves an API another uses, the contract lives in `packages/api-contract/` with a folder per version (`v1/`, `v2/`). Merging a version to `main` publishes it. If you agree, CI fails a pull request that breaks or removes a published version (oasdiff, OpenAPI only). Additions are fine, and a breaking change goes in a new version folder. Each app generates its own client from the version it uses.
- Spec templates have a **References** line for linking the BA specs, test cases and designs a feature builds on.

## 1.6.1 — 2026-10-23

No migration. `/sdlc:upgrade` regenerates the CI workflow with the Node 24 action pins.

The release smoke test was skipped at the maintainer's request. The changes were checked by the suite (207 tests) and `claude plugin validate .`.

### Changed
- An S-track fix goes to one implementer subagent on the cheap tier (standard on high risk) instead of the session, so it no longer runs at your session model's price.
- When a feature starts on the S track, or M with low risk, in an Opus or Fable session, the orchestrator suggests `/model sonnet` once. It never blocks; reviewers and the verifier keep their own models.
- The execution method you pick at the end of Stage 3 has one name everywhere: **native** (you implement in the session) or **subagent-driven**. The orchestrator, playbook, README and diagrams used to call native execution "inline".
- Stage 10 (Operate) is parked: no track runs it until there's a monitoring process to back it. Stage 9 (Deploy) runs on any track only when you ask, so the L track now ends at PR and CI, then Learn.
- The CI workflow setup generates pins actions that run on Node 24 (`checkout@v7`, `setup-node@v7`, `setup-go@v7`, `setup-java@v6`, `setup-dotnet@v6`, `setup-uv@v10`); the old pins drew GitHub's Node 20 deprecation warning. Existing repos get it from `/sdlc:upgrade`, which regenerates the workflow.

### Fixed
- Design-system additions no longer dead-end in review. A new component, variant or token approved in Stage 2 goes into `.sdlc/design-system.md` before Stage 4, and the ui-reviewer's "Proposed design-system changes" go to you in Stage 6: accept one and it's added to the system, decline it and the code uses an existing token. Before, an approved addition stayed out of the file and the reviewer flagged it as off-system.
- UI work that skips Stage 2 (S, or an M with an obvious approach) still maps each screen to the design system before Stage 4, in plan.md (M) or the Gate log (S), and asks you about anything the system lacks.
- The trust anchor also tells you when an active feature's `state.md` is deleted, or the feature is marked done before Stage 8.
- The test suite passes on Windows CI: tests read script output as UTF-8, and the missing-`python3` test is skipped where Windows finds `python3.exe` beside the interpreter.

## 1.6.0 — 2026-10-23

No migration. Repos set up earlier get a `/sdlc:doctor` warning that their commands were never run, until `/sdlc:upgrade` (or `scaffold.py run-commands`) runs them once.

The release smoke test was skipped at the maintainer's request. The changes were checked by the suite and by live headless sessions on 2026-10-23: an M feature through Stage 8 in a brownfield monorepo, and probes of the role guard, a failing full run, a trust-anchor notice and the model router (see the PRD). The new CI workflow first runs on this push.

### Added
- A trust-anchor hook tells you when what verification relies on changes during a feature: `Risk:`, `Track:` or `Top model:` changed, `baseline.md` gaining failures, the commands changing, `spec.md` changing after Stage 5 began, or leaving Stage 5 with code that changed since the last full test run. Claude stops once to explain; your next message accepts it. It makes these visible, it can't prevent them.
- When a feature has `contracts/`, the verifier checks each declared interface against the build.
- `/sdlc:status`, and the first feature started in a repo, list the repo's own hookify rules (anything in `.claude/hookify/` not named `sdlc-*`) with what they do. A cloned repo's rules reach Claude, so you see them before relying on them.
- `scaffold.py run-commands` runs the recorded commands and keeps each exit in the lock; setup uses it, so a command that can't even start no longer passes setup. `/sdlc:doctor` warns on a set-up repo whose commands were never run (repos set up earlier: run it once).
- A role-guard hook holds the plugin's own agents to their role, using the `agent_type` Claude Code now passes to hooks: reviewers can't edit files, the verifier writes only its report, the baseline and its red-green worktree, and the qa-tester can't read or search the code. They keep Bash, so this covers the file tools only.
- The model router logs every dispatch during a feature to `.sdlc/.work/dispatches.jsonl`, with the stage it happened in; the Stage 5 gate only counts a verdict from an `sdlc:verifier` dispatched in Stage 5.
- CI for the plugin itself: the test suite on Linux and Windows and `claude plugin validate`, on every push to main and every PR. Its first run happens at the next push; check it then.

### Fixed
- The freshness hook never saw a full test run that failed: Claude Code reports a non-zero exit as `PostToolUseFailure`, which the hook didn't listen to. In a brownfield repo with a baselined failure, running the package's test command could never make it fresh. A red run now counts, and each scope records whether its last run passed, failed or was piped (unknown).
- The freshness hook's own errors are no longer invisible: it leaves `.sdlc/.work/verify-freshness.error`, and `/sdlc:doctor` warns about it. Doctor's freshness line also reads the per-package state again (it always said fresh).
- `Verified:` now records the worktree tree as well as the commit, so Stage 8's check works when the verified work wasn't committed yet (found by the 1.5.0 smoke test).
- Gate-log, round and deviation lines go at the end of their section, in time order.

### Changed
- The `qa-tester` is no longer part of Stage 5: it runs only when you ask for a QA round, and its result isn't part of any gate. Its blindness to the code was instructions only, and in its one live run it found nothing the verifier missed, so it didn't earn its cost on every M and L round. Use your own independent agents for this kind of testing, or ask for an on-demand round.

## 1.5.0 — 2026-10-23

No migration: nothing a project owns changed. `/sdlc:upgrade` refreshes the generated files as usual.

Release smoke test passed on 2026-10-23 on Windows (headless sessions on sonnet, the checkout loaded with `--plugin-dir`, every must item and the monorepo should item, at e126e4a, about $4).

### Known issues
- When a feature's work is uncommitted at the Stage 5 gate, `Verified:` gets a commit plus "working tree", which Stage 8's check can't diff against.
- New gate-log lines go at the top of their section, so the log isn't in time order.

### Added
- Setup can add the sdlc marketplace and `enabledPlugins` to `.claude/settings.json` (`scaffold.py enable-plugin`, asked first) so teammates who trust the repo are offered the plugin. Keys you already set are left alone, and eject removes only what setup added. Repos set up earlier can run `scaffold.py enable-plugin` by hand.
- Stage 5 has a `qa-tester` agent on M and L tracks. It never sees the code, runs the feature against the spec's scenarios and edge cases the way a user would, and writes `qa-report.md`. A failed scenario fails the round. The model router holds it to `opus` on `Risk: high`.
- The verifier checks red-green: in a throwaway worktree with the feature's code put back to `Base:`, the feature's tests must fail. A test that still passes doesn't count as evidence.
- A later verify round reruns the qa-tester only when non-test code changed since its last PASS.
- `analyzing-consistency` maps each acceptance scenario to a named test in the plan and flags a scenario with none as HIGH.
- `/sdlc:prune` deletes the working files (plan, reports, review, checklists) of features marked done on the main branch 45+ days ago, after showing the list and asking. Spec, design, retro and state stay; git history keeps the rest.

### Changed
- One whole-branch review per feature: under the orchestrator, the execution skills skip their own final review and Stage 6 does it, with the plan's Review Focus and the Rulings made during Stage 4. A live run had spent two top-tier reviews on the same diff.
- Features are named `<yyyy-mm-dd>-<slug>`, with the ticket key after the date when the request names one (`2026-10-22-PROJ-123-month-filter`, `gh-42` for a GitHub issue). A name already in `.sdlc/` gets `-2`, so a new feature never writes into an old one's folder. The branch and knowledge entry use the same name.
- Verified code stays verified to the PR: `state.md` records the `Verified:` commit at the Stage 5 gate, the simplifier runs before the Stage 6 reviewers instead of after, a code fix in Stage 7 goes back to Stage 5 like one in Stage 6, and Stage 8 goes back to Stage 5 if non-test code changed since `Verified:`.
- `code-reviewer`, `comment-analyzer`, `pr-test-analyzer`, `silent-failure-hunter` and `type-design-analyzer` no longer have Edit or Write tools.
- The orchestrator adds each `state.md` line under its own heading; appending had put deviations under Open questions.

### Fixed
- `diff_stats.py` crashed on Windows when the diff had characters outside the code page (found by a live Stage 6 run); it now reads git output and writes its report as UTF-8.
- The verify-freshness hook switched itself off silently in a repo under a folder with non-ASCII characters in its name, because it decoded git's paths with the Windows code page. It now reads git output as UTF-8, and so does `/sdlc:doctor`.
- Stage 6 picked reviewers from `git diff --name-only`, which lists only unstaged changes, so on a branch whose tasks were committed only `code-reviewer` ran. `diff_stats.py` now uses the feature's `Base:` commit and lists every changed file, and `/sdlc:review-pr` and the reviewers work from that.
- The README no longer calls plan consistency machine-checked: `analyzing-consistency` is a skill.

## 1.4.0 — 2026-10-22

Release smoke test passed on 2026-10-22 on Windows (headless sessions, every must item, at 46a3365); the freshness fixes after it (f04c3d6, c60dff5) were checked by the suite and a real Stage 5 session.

### Known issues
- With the official `security-guidance` plugin also installed, Claude sees each security warning twice.
- The brownfield setup reference puts `packages` under `project` in `.sdlc/config.json`; `scaffold.py` reads it from the top level.
- Allowlist entries `Bash(<command>:*)` also allow extra arguments to the test command; exact matches would be tighter.
- The generated CI workflow defaults to Node 22 whatever version the repo pins.

### Added
- **UI follows the design system** ([spec 10](docs/specs/10-ui-design-system.md), [ADR 0004](docs/adr/0004-ui-follows-the-design-system.md)): setup records the project's design system in `.sdlc/design-system.md` (pointing at the existing library and tokens, or a mainstream library plus minimal tokens when there is none). A new `sdlc-ui.md` rule (scoped by the new `areas.ui`) and the `sdlc-ui-hardcoded-values` guardrail apply it while writing; the new `sdlc:ui-reviewer` checks every UI diff in Stage 6 for off-system values and components, AI-slop styling, missing states and accessibility, with screenshots only when you ask. `/sdlc:doctor` warns when a UI repo has no design system. Existing repos: `/sdlc:upgrade` adds the rule and guardrail, and migration `1.4.0-design-system` writes the design system.

### Security
- **Guardrails:** `sdlc-dangerous-rm` now catches `rm -rf /*`, `~/*`, `./*`, `../..`, `"$HOME"`, `${HOME}`, quoted targets and split or long flags. `sdlc-force-push-main` now catches pushes after `git -C`/`-c`, `-fu`, line continuations, branch deletion and `--mirror`.
- **Guardrails can't be switched off by the agent:** new `sdlc-protect-guardrails-file` and `sdlc-protect-guardrails-bash` block edits, moves and deletes of `.claude/hookify/sdlc-*.md`. Existing repos get them from `/sdlc:upgrade`.
- **Secrets:** blocked in notebook cells and Bash commands too (`sdlc-secret-values-bash`), and the key formats now include `sk-proj-`, `github_pat_`, Stripe live keys and Google API keys.
- **Hookify engine:** rules load from the project root even when a hook starts in a subdirectory; a `block` rule on a prompt now blocks it; broken rules (unknown event, action or operator, invalid regex, no frontmatter) are reported in the hook output and by `/sdlc:doctor` instead of being skipped silently; a BOM, blank first line or capitalised `Block`/`Bash` no longer disarms a rule; a regex that runs over 1 s is skipped; rule messages are capped at 2000 characters.
- **Other:** the reviewer SDK is installed at a pinned version; `/sdlc:ralph-loop` rejects a multi-line `--completion-promise` and warns when no session id is available.

### Changed
- **Model tiers are named:** cheap = `haiku`, standard = `sonnet`, top = `opus`. Skills used to say "the most capable available model", which could resolve to Fable. Fable is now used only when you ask for it (`Top model: fable` in `state.md`), and fix-loop escalation stops at the top tier.
- **Risk sets the models:** the orchestrator records `Risk: low | high` next to `Track:`, and every dispatch picks its model from track and risk. A small change to auth, payments, secrets, PII, migrations or a public API still gets top-tier review.
- **Model router hook:** while a feature is active, a subagent dispatch is denied if it names no model, asks for Fable without your opt-in, or runs a reviewer below Opus on a high-risk feature. Forks are exempt (they always use the session model).
- **Upgrades add new plugin files:** `/sdlc:upgrade` now installs policy rules and guardrails that are new in the installed version (an "add" step), so repos set up earlier get them. Files you handed back with "keep mine" (`forget`) are remembered and never re-added; a file of yours with the same name is never overwritten.
- **Monorepo verify:** the orchestrator records the commit a feature starts from (`Base:` in `state.md`); in Stage 5 only packages changed since then need their tests rerun. Without a base, every package does, as before.

### Fixed
- **`sdlc-sensitive-files`** now matches Windows paths (`C:\proj\.env`, `.ssh\id_rsa`); the pattern only accepted `/`.
- **Upgrades on Windows:** `scaffold render` writes LF, so `upgrade-plan` no longer lists every unchanged seeded file as "replace". Repos set up on Windows show one spurious "replace" per file on the first upgrade after this.
- **Line endings on Windows:** plugin files checked out with CRLF (git's `core.autocrlf`) no longer count as hand-edited. `/sdlc:doctor` stops warning about them, and `/sdlc:upgrade` overwrites them instead of asking you to review each one. File hashes ignore CRLF versus LF.
- **Stage 5 freshness:** a test command whose own flags look like a name filter (unittest's `-t .`) now counts as a full run. It never did, so Stage 5 blocked every turn end for such packages. Only arguments added after the test command are checked for filters now, so a run piped through `grep -t` counts too. A filter or test file after a redirect (`npm test 2>/dev/null -t login`) is no longer missed.
- **`/sdlc:doctor`** no longer crashes with `UnicodeEncodeError` when its output goes to a non-UTF-8 console or pipe (cp1252 on Windows); it writes UTF-8.
- **Setup and upgrade on Windows:** `scaffold.py` no longer crashes with `UnicodeEncodeError` on non-ASCII output (rendered rules, migration summaries, paths); it writes UTF-8.
- **`/sdlc:doctor`** fails when `python3` is missing or doesn't run (the hooks start with it and fail open without it) and warns when `jq` is missing (the ralph-loop stop hook needs it).
- Greenfield setup no longer creates or edits `CLAUDE.md`; the knowledge pointer lives in `.claude/rules/sdlc.md`.
- `/sdlc:doctor` no longer warns about the plugin's own policy rules (e.g. `sdlc-migrations.md`) matching no files yet, and explains that the security reviewer's environment is only built when the security hooks receive credentials.
- `/sdlc:eject` removes the `.sdlc/.work/` scratch folder along with its `.gitignore` line.
- Setup reports a step it skips as not applicable (with the reason) when it skips it, not only in the final report.

## 1.3.0 — 2026-10-22

### Added
- **Project setup:** `/sdlc:setup` for new and existing repos. Records the repo's own commands in `.sdlc/config.json` (per package in a monorepo), a known-failures baseline, a deep audit into knowledge and area rules, policy rules, guardrails, lint snippets, an allowlist, generated CI, constitution and knowledge. Runs on a branch, resumable.
- **Upgrades and removal:** `/sdlc:upgrade` (regenerate plugin files, ask before touching edited ones, versioned migrations) and `/sdlc:eject`. File ownership is tracked in `.sdlc/scaffold.lock.json`.
- **`/sdlc:doctor`:** read-only health check of machine, plugin and repo, with a fix per problem.
- **Scope tracing:** `[user]`/`[clarified]`/`[inferred]` requirement tags and Non-Goals in specs (inferred items dropped unless kept); Complexity Tracking for every design addition; task `Requirements:` lines and a Public Surface section in plans; `diff_stats.py --plan` flags undeclared surface in review.
- **Conventions:** policy rules (`.claude/rules/sdlc-*.md`: workflow, code style, tests, migrations, sensitive areas, CI), 11 hookify guardrails (dangerous `rm`, force-push to main, secrets, narrating/history/long comments, suppressions, focused tests, `console.log`), ESLint and Ruff snippets, and `diff_stats.py` facts in every review.
- **Verification:** baseline-aware verifier (fails only on new failures); freshness tracked per package; config-driven test commands.
- **Docs:** guidebook, playbook, runbook, diagrams, CONTRIBUTING; ADRs (`docs/adr/`), a PRD and numbered capability specs with each requirement tied to the test that proves it (`docs/prd.md`, `docs/specs/`); marketplace manifest.

### Changed
- `/sdlc:start` routes to setup when a repo isn't set up and reports version drift; `/sdlc:status` shows setup state.
- Track sizing defaults to the smallest track that fits; sizing up names its signal.
- Default constitution template includes a Simplicity principle.

### Fixed
- Hookify: `new_text` now covers `Write`; new `not_regex_match` operator; warnings reach Claude (`additionalContext`) and blocks say why (`permissionDecisionReason`); committed team rules in `.claude/hookify/*.md`; no more duplicate evaluation after each tool call.
- Ralph loop: stop hook no longer crashes on a state file missing a field.
- Verify freshness: catches edits made outside Edit/Write (worktree fingerprint), single-file and single-package runs, and redirects like `2>&1`.

## 1.2.0

First version: orchestrator with S/M/L tracks and 11 gated stages; vendored skills, agents and commands from Superpowers, GitHub Spec Kit and Anthropic's plugins under the `sdlc:` namespace; fresh verifier per round with the Stage 5 freshness hook; 3-tier knowledge; security-guidance, hookify and ralph-loop hooks; hook test suite.
