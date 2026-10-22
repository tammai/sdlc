# Design: project setup, upgrade and eject

Status: approved, in progress (`scripts/scaffold.py`, policy rules, guardrails, lint snippets, `diff_stats.py` done) · Target: v1.3.0 · From the 2026-10-22 interview

## Problem

Today, "setup" is improvised inside `/sdlc:start` step 0: it adds a `.gitignore` line, offers a constitution, detects the stack into each feature's `state.md`, and offers to set up knowledge. Nothing records which plugin version created which project file, so a plugin update has no safe way to patch what an earlier version scaffolded. Greenfield projects get no skeleton or CI. Brownfield projects get no audit or baseline, so Stage 5 can blame a feature for failures that were already there.

## Decisions (from the interview)

| Topic | Decision |
|---|---|
| Greenfield scope | SDLC scaffolding + project skeleton + CI (GitHub Actions running verify only) |
| Greenfield stack | Free-form interview each time; Claude proposes, the user approves, official generators do the work. The plugin maintains no presets. |
| Brownfield depth | Deep audit: detect, check the commands actually run, seed knowledge with code-explorer agents, mine git history, migrate existing AI config, record a baseline |
| Existing AI config | Propose a migration per source (CLAUDE.md, AGENTS.md, .cursor/rules, .specify/, ADRs); the user approves each diff; originals are kept unless the user approves deleting them |
| Baseline | `.sdlc/baseline.md`, committed. Stage 5 fails only on *new* failures. The baseline only shrinks unless the user approves an addition. |
| Command contract | A root `justfile` in **every** project, with required recipes. Recipes wrap the existing tools (pnpm, make, turbo…) instead of replacing them. The user owns the file; the plugin only checks the contract and proposes missing recipes. |
| Monorepo | One root (`.sdlc/`, `knowledge/`, justfile). Per-package work goes through recipe arguments. |
| Triggers | `/sdlc:setup` (explicit, re-runnable), and `/sdlc:start` routes to setup when the project isn't set up (hard stop). No SessionStart hook. |
| Always-on text | `.claude/rules/sdlc.md`: plugin-owned, regenerated on upgrade. CLAUDE.md belongs to the user and is never touched. |
| Upgrades | Hybrid: generic material is read from the plugin at runtime; generated files are regenerated; seeded files are replaced only if unmodified; user-owned files change only through versioned migrations |
| Drift | `/sdlc:start` and `/sdlc:status` compare versions and offer `/sdlc:upgrade`. They never block. |
| Declined migration | Recorded as skipped and never asked again (`/sdlc:upgrade --revisit` to reconsider). The version still advances. |
| Team skew | The repo pins `min_plugin_version`. An older plugin gets a warning to update; a newer one gets an offer to upgrade. |
| Git | Setup, upgrade and eject each run on their own branch, one commit per step, then **ask**: open a PR or merge locally |
| Guardrails | Dangerous commands, sensitive files, permission allowlist, code-hygiene warnings |
| Eject | `/sdlc:eject` removes what the plugin owns and keeps the user's work |

## File ownership model

Every file the plugin places in a project falls into exactly one class. That class determines what setup, upgrade and eject may do to it.

| Class | Files | Setup | Upgrade | Eject |
|---|---|---|---|---|
| **Runtime** (never copied) | templates, stage rules, agent prompts, migrations | — | free (comes with the plugin update) | — |
| **Generated** (plugin-owned) | `.claude/rules/sdlc.md` | render | re-render from config, overwrite | delete |
| **Seeded** (plugin-owned until edited) | `.github/workflows/sdlc-verify.yml`, `.claude/hookify/sdlc-*.md`, `knowledge/` skeleton files (`index.md`, `log.md` while still empty) | write, record hash | unchanged hash → replace; changed → show diff, apply or skip | unchanged → delete; changed → ask |
| **Keyed merge** | `.claude/settings.json` (`permissions.allow` entries), `.gitignore` (lines) | add entries, record which ones | add/remove only the entries it recorded | remove only the entries it recorded |
| **Contract** | `justfile` | create or wrap (diff approved) | check required recipes; propose missing ones | keep |
| **User-owned** | `CLAUDE.md`, `.sdlc/constitution.md`, `knowledge/**` (after seeding), `.sdlc/baseline.md`, `.sdlc/<feature>/**` | write once (approved) | migrations only (diff approved; decline → skipped) | keep |
| **Data** | `.sdlc/config.json` (human), `.sdlc/scaffold.lock.json` (machine) | write | update | delete the lock, keep config |

Keeping most material in the Runtime class is the main lever: anything generic stays in the plugin, so a plugin update reaches it without touching the project.

### `.sdlc/config.json` (committed, human-editable)

JSON rather than YAML: the scripts are stdlib-only and must run on macOS's system Python 3.9, which has no YAML or TOML parser.

```json
{
  "min_plugin_version": "1.3.0",
  "project": {
    "kind": "brownfield",
    "stack": ["typescript", "node", "pnpm", "vitest"],
    "packages": ["apps/web", "packages/api"]
  },
  "verify": { "full": ["just verify", "just test"] },
  "baseline": ".sdlc/baseline.md"
}
```

`packages` is for monorepos only (just recipes take an optional `pkg` argument). `verify.full` lists the commands that count as a full run for the freshness hook.

### `.sdlc/scaffold.lock.json` (committed, machine-only)

```json
{
  "scaffold_version": "1.3.0",
  "files": { ".github/workflows/sdlc-verify.yml": { "class": "seeded", "sha256": "…" } },
  "merged": { ".claude/settings.json": ["Bash(just test:*)", "…"], ".gitignore": [".sdlc/.work/"] },
  "migrations": { "applied": ["1.3.0"], "skipped": { "1.4.0-knowledge-folders": "keeping flat layout" } },
  "setup": { "completed_steps": ["detect", "justfile", "ci", "…"] }
}
```

`completed_steps` makes setup resumable: re-running `/sdlc:setup` continues where it stopped.

### Justfile contract

Required recipes: `test`, `lint`, `typecheck`, `build`, `verify` (runs all four). Optional: `test-affected` (monorepo: turbo `--filter` / `nx affected`) and `fmt`. Every recipe takes an optional `pkg` argument in monorepos. Stages, CI, the allowlist and the freshness hook all call `just <recipe>`, so none of them need stack-specific logic. If `just` is missing, setup offers to install it (`brew install just`) as a hard stop; CI installs it with `extractions/setup-just`.

## Flows

### `/sdlc:setup`

Mode: **greenfield** when the repo has no source files (ignoring README, LICENSE and dotfiles), otherwise **brownfield**. Creates the branch `sdlc/setup` and makes one commit per step.

**Greenfield**
1. Interview: what is being built, runtime, package manager, test runner, deploy target. Claude proposes a stack and skeleton → **user approves**.
2. Generate with the official tools (`pnpm create`, `create-next-app`, …), then apply conventions (strict tsconfig, lint, test runner).
3. Write the justfile against the generated scripts. Run `just verify` once, which must pass.
4. CI: `.github/workflows/sdlc-verify.yml` runs `just verify` on PRs and on main.
5. Common steps (below).

**Brownfield**
1. Detect: stack, package manager, workspaces, existing scripts/Makefile, CI, AI config.
2. Justfile: wrap the existing commands → **user approves the diff**. Run every recipe and record the results.
3. Baseline: failing tests (by ID) and lint/type error counts (per rule and file) → `.sdlc/baseline.md`.
4. Deep audit, run in parallel by `sdlc:code-explorer` agents:
   - conventions: naming, layering, error handling, test style → draft `knowledge/conventions/*`
   - git history: hot files, reverts, recurring fix areas → draft `knowledge/gotchas/*`
   - existing ADRs/docs → `knowledge/decisions/*` (links, or migration)
   - existing AI config → one migration proposal per source (tiers; CLAUDE.md ≤ 60 lines)
   → **user reviews each batch**; nothing is written without approval.
5. CI: if no CI runs the verify contract, offer the workflow. Existing CI stays untouched.
6. Common steps (below).

**Common steps**
- Guardrails (seeded, as `.claude/hookify/sdlc-*.md`):
  - block `rm -rf`, `git push --force` to main/master, and `git reset --hard` on main
  - warn on `.env*`, credential and key files
  - warn on `console.log`, `.only(` in tests, and newly added `@ts-ignore` / `eslint-disable`
- Allowlist: `Bash(just test:*)`, `Bash(just lint:*)`, `Bash(just typecheck:*)`, `Bash(just build:*)`, `Bash(just verify:*)` → `.claude/settings.json` (keyed merge).
- `.gitignore` gets `.sdlc/.work/`.
- Constitution: inferred from the repo and the interview (`sdlc:project-constitution`) → **user approves**.
- `knowledge/` skeleton (`index.md`, `log.md`, folders) if not created by the audit.
- Render `.claude/rules/sdlc.md`, then write `config.json` and `scaffold.lock.json`.
- **Ask:** open a PR, or merge locally.

### `/sdlc:start` changes
- No `config.json` → "This project isn't set up for sdlc. Run setup first?" (hard stop; yes → setup, then continue with the request).
- Lock version below the plugin version → one line naming what changed, plus an offer to run `/sdlc:upgrade` (never blocks).
- Plugin version below `min_plugin_version` → warn: update the plugin.
- Commands come from the justfile contract, no longer detected per feature.

### `/sdlc:upgrade`
1. Read `scaffold_version`, list the plugin's `migrations/` newer than it, and summarize. If a feature is mid-stage, warn and recommend finishing it first, or confirm.
2. Branch `sdlc/upgrade-<from>-<to>`.
3. Re-render Generated files.
4. Seeded files: hash matches → replace (`render --if-unchanged`). Hash differs → show a diff of the user's file against the newly rendered template; Claude proposes a merge; the user applies it or skips. No pristine base copies are stored: the old version is in git history if needed. Deleted seeded files are offered for restore, never forced.
5. Keyed merges: add new entries and remove retired ones (only entries listed in the lock).
6. Justfile contract: propose any newly required recipes.
7. Migrations, in version order. Each is `migrations/<version>-<slug>.md`, with frontmatter `version` and `summary`, then the steps in prose. Claude applies it as a diff; the user approves → applied, or declines → skipped, with the reason.
8. Bump `scaffold_version`, and `min_plugin_version` when a migration says so. Commit, then **ask** whether to open a PR or merge locally.

`--revisit` re-offers skipped migrations. `--dry-run` shows everything and writes nothing.

### `/sdlc:eject`
On branch `sdlc/eject`:
- delete Generated files, and Seeded files whose hash is unchanged (ask about edited ones)
- remove the keyed-merge entries the plugin added
- delete the lock

Keeps `config.json`, the constitution, `knowledge/`, the baseline, the justfile and all feature artifacts. Then asks whether to open a PR or merge locally.

## Stage 5 and the baseline
- The verifier reads `.sdlc/baseline.md` and classifies each failure as *new* or *baseline*. The gate fails on new failures only, and the report lists both groups.
- A baseline failure that now passes is removed from the baseline, and the report says so. Adding an item needs user approval and is recorded under Deviations.
- `verify_freshness.py` reads its full-run commands from `config.json` `verify.full` (default `just verify`, `just test`), falling back to the current `state.md` `test:` and generic patterns.

## Plugin-side changes

| Change | Notes |
|---|---|
| `commands/setup.md`, `upgrade.md`, `eject.md` | thin wrappers around the skill |
| `skills/setting-up-projects/` | SKILL.md + `references/{greenfield,brownfield,upgrade,eject,ownership}.md` |
| `scripts/scaffold.py` | the deterministic, testable parts: render the generated file, hash and classify files, read and write the lock, keyed merges, list pending migrations, version comparison, eject plan. Claude does the judgment calls; this script does the bookkeeping. |
| `templates/project/` | ✅ `config.defaults.json`, `rules/*.md`, `hookify/sdlc-*.md`, `lint/*`. To do: `justfile` snippets, `sdlc-verify.yml`, `baseline.md` |
| `migrations/` | empty in 1.3.0. Projects with a pre-setup `.sdlc/` have no lock, so `/sdlc:start` routes them to setup (brownfield), which adopts what's there. |
| orchestrator step 0 | route to setup, drift check, justfile commands |
| `agents/verifier.md` | baseline-aware gate |
| `hooks/verify_freshness.py` | full-run commands from `config.json` |
| `core/config_loader.py` (hookify) | **also** load committed team rules from `.claude/hookify/*.md`. Today it only reads `.claude/hookify.*.local.md`, which hookify's own docs say to git-ignore, so those files are personal. Another vendored patch; record it in NOTICE.md. |
| `tests/` | scaffold.py ✅ (29 tests), hookify team-rule loading, freshness `config.json` commands |

## Tier 2 rules and conventions

Two kinds of `.claude/rules/` files, with different owners:

| Kind | Files | Class | Where content comes from |
|---|---|---|---|
| **Policy rules** (plugin's SDLC rules, by kind of file) | `sdlc.md` (always-on), `sdlc-code-style.md`, `sdlc-tests.md`, `sdlc-migrations.md`, `sdlc-sensitive.md`, `sdlc-ci.md` | Generated | `templates/project/rules/`; `paths:` from `areas.*` in config (defaults in `templates/project/config.defaults.json`, project overrides in `.sdlc/config.json`) |
| **Area rules** (project knowledge, by area of the codebase) | `api.md`, `payments.md`, … | User-owned | Brownfield: drafted by the deep audit, approved per batch. Greenfield: only what follows from the stack choices; the rest grows from Stage 11. |

Naming makes ownership visible: `sdlc-*` files belong to the plugin, everything else to the project. The same holds for committed hookify team rules in `.claude/hookify/`.

**Comment noise and over-engineering** are handled at three points:

| When | What | Files |
|---|---|---|
| Writing | `sdlc-code-style.md` policy rule (why-only comments, doc comments on exports only, one line; smallest diff, no single-implementation abstractions, no unrequested surface); the same lines in the subagent implementer prompt | `templates/project/rules/code-style.md`, `skills/subagent-driven-development/implementer-prompt.md` |
| Automatic checks | hookify warnings on narration, change-history and long doc comments, suppressions, focused/skipped tests, `console.log`; blocks on dangerous rm, force-push to main, secret values. Lint snippets for complexity, depth, params, function length, TODOs. | `templates/project/hookify/sdlc-*.md`, `templates/project/lint/{eslint.sdlc.mjs,ruff.sdlc.toml}` (seeded into `.sdlc/lint/`) |
| Review | `scripts/diff_stats.py` facts in every reviewer prompt; unrequested public surface is high severity; comment noise is medium and fixed in Stage 6; S track runs `code-simplifier` too; `comment-analyzer` no longer asks for comments aimed at the least experienced reader; constitution template ships a default **V. Simplicity** principle | `scripts/diff_stats.py`, `skills/orchestrator/SKILL.md`, `commands/review-pr.md`, `agents/comment-analyzer.md`, `templates/constitution-template.md` |

**Upstream: scope is traced to a request in every stage,** because over-engineering usually starts before any code is written:

| Stage | Mechanism |
|---|---|
| Sizing | Smallest fitting track; a size-up names its signal in `state.md` |
| 1 Spec | Every FR/SC tagged `[user]` / `[clarified]` / `[inferred]`; required Non-Goals section; future-proofing words need a measurable requirement. At the gate, `[inferred]` items are listed separately and **dropped unless the user keeps them**; dropped ones move to Non-Goals. |
| 2 Design | Complexity Tracking always filled: every new module, layer, abstraction, dependency, service, config key and store cites an FR/SC, or comes out. Architect options are minimal / minimal + one named extension / pragmatic; minimal is recommended unless it fails a named requirement. Scale and performance numbers must cite an SC. "Deliberately not built" section. |
| 3 Plan | Every task has a **Requirements:** line (reverse trace in the self-review, so all tracks get it). **Public Surface** section declares every new export, endpoint, command, config key, env var and dependency. `analyzing-consistency`: leftover `[inferred]` or a Non-Goal planned in is CRITICAL; other scope creep is HIGH. |
| 6 Review | `diff_stats.py --plan` flags exports and dependencies missing from Public Surface (unrequested surface → high severity) and declared items never built. Endpoints, commands, config and env are listed for a reviewer to check by hand. |

Hookify patches this needed (recorded in NOTICE.md): load `.claude/hookify/*.md`; send warnings to Claude via `additionalContext` and block reasons via `permissionDecisionReason` (upstream used `systemMessage`, which only the user sees); unregister the duplicate PostToolUse evaluation.

## Resolved questions
1. **Greenfield detection:** when it's unclear (only docs, a spike folder), ask.
2. **Monorepo baseline:** one `.sdlc/baseline.md` with a package column.
3. **Force-push guardrail:** also blocks `--force-with-lease`, on main/master only.
4. **Dogfood:** set up the `sdlc` repo itself once setup works (justfile: `python3 -m unittest discover -s tests -t tests`, `claude plugin validate .`).

## `scripts/scaffold.py` reference

Every command prints one JSON object. Exit codes: 0 ok, 1 error, 2 refused because the user edited the file.

| Command | Does |
|---|---|
| `init --kind greenfield\|brownfield` | write the lock, plus a default `config.json` if none exists |
| `status` | setup state, steps done, drift (`current` / `behind` / `ahead` / `plugin_too_old`), pending migrations, file states |
| `step-done <step> [--complete]` | record setup progress (resumable) |
| `render <template> <dest> [--class seeded] [--if-unchanged]` | render a plugin template with `{{config.x.y}}` / `{{plugin_version}}` and record its hash |
| `preview <template>` | render without writing |
| `record <generated\|seeded> <paths…> [--template T]` / `forget <paths…>` | track files Claude wrote / hand them over to the user |
| `allow --add/--remove …`, `gitignore --add/--remove …` | keyed merges; only ever removes entries the plugin added |
| `migrations [--revisit]`, `migration <id> --applied\|--skipped REASON` | list pending migrations (version window: scaffold < v ≤ plugin, ordered numerically) / record the outcome |
| `set-version <v> [--min-plugin m]` | advance `scaffold_version`; raises the pin, never lowers it |
| `upgrade-plan` | regenerate / replace / review / restore / template_gone, plus pending migrations |
| `eject [--apply] [--also <edited files>]` | dry-run plan by default; applying it deletes plugin files, removes merged entries and the lock, and tidies emptied folders |
