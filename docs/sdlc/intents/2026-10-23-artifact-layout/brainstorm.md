# Brainstorm: split sdlc docs from sdlc machinery

Status: draft for approval · 2026-10-23

## Intent and why

In a set-up repo today, everything the plugin keeps sits in `.sdlc/`: config, lock, scratch, and also the documents people read and review (constitution, design system, every feature's brainstorm, spec, design, plan and reports). The user wants those documents to live with the project's docs, next to the BA, QA and design artifacts (`docs/specs`, `docs/test-cases`, `docs/designs`), and `.sdlc/` to hold only what the plugin runs on. Feature folders keep the agreed name `<yyyy-mm-dd>[-<ticket>]-<slug>`.

## Goals

1. **The layout, in every set-up repo:**

   ```
   .sdlc/                                  machinery
     config.json  scaffold.lock.json
     baseline.md                           known failures (the verifier maintains it; hooks diff it)
     state/<name>.md                       one per feature: track, stage, gate log, deviations, questions
     ci/  lint/  .work/
   <docs_dir>/                             documents (default docs/sdlc)
     constitution.md  design-system.md
     intents/<name>/                       brainstorm, spec, design, plan, research, checklists,
                                           test-report, qa-report, review, security, release, retro
   knowledge/                              unchanged
   ```

   `<name>` is the same for a feature's state file and its intents folder.
2. **The docs location is recorded** in `.sdlc/config.json` as `docs_dir` (default `docs/sdlc`). Setup and upgrade look for a docs-site builder before writing: `docusaurus.config.*`, `mkdocs.yml`, `docs/.vitepress/`, `docs/conf.py`, or an Astro/Starlight content dir under `docs`. If one is found, they tell the user `docs/sdlc/` would be published and ask: `.sdlc` itself, a path of their choice, or `docs/sdlc` anyway. Otherwise they use the default without asking.
3. **One resolver.** A shared helper gives `docs_dir`, a feature's intents folder and its state file. Every hook and script uses it; skills and agents get paths from `scaffold.py paths [<name>]` (JSON). Rendered project files (`.claude/rules/sdlc*.md`, guardrails) use `{{config.docs_dir}}`.
4. **Upgrade moves existing repos.** A migration runs `scaffold.py relocate`: dry run by default, then `git mv` of every feature (done ones too) and of `constitution.md` and `design-system.md`, and records `docs_dir`. History follows the files. Existing folder names are kept, not renamed to the new convention.
5. **Both layouts are read.** Hooks and scripts that look for features (model-router, trust-anchor, verify-freshness, diff_stats, prune, doctor, status) find state in `.sdlc/state/*.md` and, until a repo is upgraded, in the old `.sdlc/*/state.md`. A not-yet-upgraded repo keeps working, and `/sdlc:status` says to upgrade.
6. **Guards follow the docs.** The role guard lets the verifier write `test-report.md` and the qa-tester write `qa-report.md` in the feature's intents folder, and lets the qa-tester read the docs folder (the spec) as it reads `.sdlc/` today.

## Non-goals

- Renaming old feature folders to the date-ticket-slug convention.
- Moving `knowledge/`, or moving the baseline out of `.sdlc/`.
- Supporting a docs location outside the repo.
- Changing what's in each document.

## Anti-goals

- A half-moved repo: some features in the old place and some in the new after an upgrade finishes.
- Hooks that silently stop seeing the active feature between a plugin update and `/sdlc:upgrade`.
- Internal plans and reviews ending up on a team's public docs site without anyone being asked.
- Path rules copied into dozens of skills, so the next layout change is another 50-file edit.

## Constraints

- Ownership classes are unchanged. The moved docs stay user-owned, and the migration moves them; it never rewrites their content.
- `relocate` refuses on a dirty tree (like setup), runs on the `sdlc/upgrade-<from>-<to>` branch, and is idempotent: a second run moves nothing.
- Windows: no symlinks. Paths are written with `/` in config and output.
- Stdlib-only Python 3.9+ and the existing scripts rules (UTF-8 stdout, subprocess decoding).
- Tests stay minimal: one per user-visible behaviour, plus the failure case that matters most.

## Approaches

- **A. One path resolver plus a `relocate` command (chosen).** A shared helper is used by hooks and scripts, `scaffold.py paths` serves skills, and `scaffold.py relocate` does the move deterministically, called from a migration file. The layout lives in one function. It costs one new command, and the skills are reworded to ask for paths.
- B. Conventions written in prose, with a hand-run markdown migration. Fewer code changes, but about 50 places each re-derive the paths, and a manual move can miss files or the lock.
- C. A fixed `docs/sdlc` with a symlink for docs-site repos. Rejected: symlinks are unreliable on Windows checkouts, and site builders often follow them.

The user chose **A**.

## Decided

- Machinery and state (config, lock, baseline, state, ci, lint, .work) stay in `.sdlc/`. Documents go to `docs_dir`, default `docs/sdlc`.
- Every repo gets this layout. Upgrade moves existing repos.
- If the repo has a docs site, the user is asked for the location (including `.sdlc` itself), and the answer is recorded.
- The baseline stays in `.sdlc/` (brainstormer's call, which the user delegated).
- State is one file per feature, `.sdlc/state/<name>.md` (brainstormer's call).
- Hooks read both layouts (brainstormer's call).

## Calls made after the builder check (brainstormer's calls, not the user's)

- **Which layout a repo is on:** a repo is on the new layout when the project's own `.sdlc/config.json` sets `docs_dir`. `docs_dir` is **not** added to `config.defaults.json`. Otherwise the repo is legacy. Until it upgrades, `paths` returns the old layout for every feature (new ones included, so a repo is never half-moved), with `"layout": "legacy"`. `/sdlc:status` and doctor then say to run `/sdlc:upgrade`. Setup always writes `docs_dir`.
- **The move, per old `.sdlc/<name>/` folder** (any folder holding a `state.md`): `state.md` goes to `.sdlc/state/<name>.md`, and everything else in the folder (files and subfolders such as `checklists/`) goes to `<docs_dir>/intents/<name>/`.
- **In-flight features move too.** Before moving, the migration lists the active features and warns that their open branches will see renames, then asks to go ahead. This uses the same warning moment `upgrade.md` already has for a feature past Stage 3.
- **Resumable, not all-or-nothing.** `relocate` moves whatever is still in the old place and writes `docs_dir` to config **last**, so the switch happens only once everything has moved. An interrupted run is finished by running it again. Until then the hooks read both layouts. If a name exists in both, the new location wins for reading, and `relocate` stops on that name and reports it rather than overwrite.
- **How the location gets in:** the migration asks the docs-site question and passes the answer as `relocate --docs-dir <path>`. A dry run writes nothing.
- **What `docs_dir` may be:** a relative path inside the repo, not `.git` or under it, and not `.` itself. `.sdlc`, `docs` and `docs/sdlc` are all valid. Anything else is refused with the reason.
- **Prune** reads a feature's state on the ref at either path, and takes its age from `git log --follow`, so the move doesn't reset every feature's age.
- **Freshness:** edits under `docs_dir` don't make tests stale, the same way edits to docs and `.sdlc/` are already treated.

## Left to the builder

- Where the shared helper lives (hooks and scripts are separate directories today; `verify_freshness.py` is already imported by `trust_anchor.py`) and its exact signatures.
- `relocate`'s JSON output shape and dry-run format.
- The migration file (`migrations/1.7.0-artifact-layout.md` or the next version) and the plugin version bump.
- Rewording the skills, agents and commands that name old paths. Roughly: orchestrator, brainstorming, writing-specs, clarifying-specs, designing-solutions, writing-plans, analyzing-consistency, project-constitution, managing-knowledge, requesting-code-review, subagent-driven-development's implementer prompt, setting-up-projects (SKILL, upgrade, eject), the verifier, qa-tester and ui-reviewer agents, and the prune, review-pr and status commands.
- Rendered templates: `rules/sdlc.md`, `rules/ui.md`, `hookify/sdlc-ui-hardcoded-values.md`, `knowledge/doc.md`.
- The eject keep-list and doctor's checks.
- Docs: a new ADR amending 0001, specs 01, 02, 05, 07 and 10, the guidebook "Where things live", the runbook and README, the CHANGELOG, and the stale-docs audit.

## Acceptance criteria (draft, ≤10)

1. Greenfield setup with no docs site writes `docs_dir: "docs/sdlc"` and puts the constitution in `docs/sdlc/`.
2. Setup in a repo with `mkdocs.yml` (or another listed builder) asks for the location before writing, and records the answer.
3. `scaffold.py paths <name>` returns the state file and intents folder for that name under the recorded `docs_dir`.
4. A new feature's state is written to `.sdlc/state/<name>.md` and its documents to `<docs_dir>/intents/<name>/`.
5. `relocate` on an old-layout repo moves every feature and both docs with `git mv`, records `docs_dir`, and a second run moves nothing. It refuses on a dirty tree.
6. The model router and trust anchor find an active feature in either layout.
7. `prune` deletes a done feature's files from its intents folder in the new layout.
8. The role guard allows the verifier to write `test-report.md` in the intents folder, and refuses source edits as before.
9. Eject keeps `docs_dir` and `.sdlc/state/`.
