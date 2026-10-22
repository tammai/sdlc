# ADR 0001: Project setup, upgrade and eject

- **Status:** Accepted, 2026-10-22. Amended by [ADR 0002](0002-record-the-repos-own-commands.md) (commands).
- **Deciders:** Tâm Mai, from a design interview.

## Context

Before v1.3.0, "setup" was improvised inside `/sdlc:start` step 0: it added a `.gitignore` line, offered a constitution, detected the stack into each feature's `state.md`, and offered to set up knowledge. Nothing recorded which plugin version created which project file, so a plugin update had no safe way to patch what an earlier version scaffolded. Greenfield projects got no skeleton or CI. Brownfield projects got no audit or baseline, so Stage 5 could blame a feature for failures that were already there.

## Decision

A dedicated setup phase, versioned upgrades and a clean eject, built on an explicit file-ownership model.

| Topic | Decision |
|---|---|
| Greenfield | Free-form stack interview; Claude proposes, the user approves, the ecosystem's official generators build the skeleton. No presets maintained in the plugin. Skeleton, commands and CI pass on day one. |
| Brownfield | Deep audit: record the commands that exist and run them, record a baseline, seed knowledge with code-explorer agents (conventions, git-history gotchas, decisions, area rules), migrate existing AI config one diff per source. Nothing written without approval. |
| Baseline | `.sdlc/baseline.md`, committed. Stage 5 fails only on *new* failures. It only shrinks unless the user approves an addition. |
| Monorepo | One root (`.sdlc/`, `knowledge/`); packages declared in config (see ADR 0002). |
| Triggers | `/sdlc:setup` (explicit, re-runnable); `/sdlc:start` routes to setup when the repo isn't set up (hard stop). No SessionStart hook. |
| Always-on text | `.claude/rules/sdlc.md`, plugin-owned and regenerated on upgrade. `CLAUDE.md` belongs to the user and is never touched. |
| Upgrades | Generic material is read from the plugin at runtime; generated files are regenerated; seeded files are replaced only if unedited; user-owned files change only through versioned migrations the user approves. Declined migrations are recorded and not asked again (`--revisit` to reconsider). |
| Drift and team skew | `/sdlc:start` and `/sdlc:status` report a repo behind the plugin and offer `/sdlc:upgrade`; they never block. The repo pins `min_plugin_version`; an older plugin gets a warning. |
| Git | Setup, upgrade and eject each run on their own branch, one commit per step, then ask: open a PR or merge locally. |
| Eject | Remove what the plugin owns, keep the user's work. |

### File ownership

Every file the plugin places in a project is in exactly one class, recorded in `.sdlc/scaffold.lock.json`. The class decides what setup, upgrade and eject may do.

| Class | Files | Setup | Upgrade | Eject |
|---|---|---|---|---|
| **Runtime** (never copied) | templates, stage rules, agent prompts, migrations | — | arrives with the plugin update | — |
| **Generated** | `.claude/rules/sdlc*.md` | render | re-render, overwrite | delete |
| **Seeded** | `.github/workflows/sdlc-verify.yml`, `.claude/hookify/sdlc-*.md`, `.sdlc/lint/*` | write, record hash | unedited → replace; edited → user chooses merge, skip, or keep theirs for good | unedited → delete; edited → ask |
| **Keyed merge** | `permissions.allow` entries in `.claude/settings.json`, `.gitignore` lines | add, record which | touch only recorded entries | remove only recorded entries |
| **User-owned** | `CLAUDE.md`, constitution, `knowledge/**`, baseline, area rules, `.sdlc/<feature>/**`, `.sdlc/config.json` | write once, approved | approved migrations only | keep |

Keeping most material in the Runtime class is the main lever: anything generic stays in the plugin, so a plugin update reaches it without touching the project. Plugin-owned files are named `sdlc-*` (or `sdlc.md`), so ownership is visible at a glance.

`.sdlc/config.json` is JSON, not YAML, because the scripts are stdlib-only and must run on macOS's system Python 3.9, which has no YAML or TOML parser. It holds only overrides; defaults live in the plugin (`templates/project/config.defaults.json`), so a new default reaches every repo without a migration.

### Flows

**Setup:** detect greenfield (no source files; ask if unclear) or brownfield → stack and commands (greenfield) or commands, baseline, audit and AI-config migration (brownfield) → CI → common steps (policy rules, guardrails, lint snippets, allowlist, `.gitignore`, constitution, knowledge) → PR or local merge. Progress is recorded per step, so a rerun resumes.

**Upgrade:** plan (regenerate / replace / review / restore / template gone, plus pending migrations) → its own branch → apply bucket by bucket, asking about edited files → migrations in version order, each an approved diff → bump the recorded version → PR or local merge. `--dry-run` writes nothing.

**Eject:** dry run first → delete generated and unedited seeded files, ask about edited ones, remove recorded keyed-merge entries and the lock → fix imports left pointing at deleted files → PR or local merge.

The procedures are in `skills/setting-up-projects/`; the bookkeeping is `scripts/scaffold.py` (command reference in the [runbook](../runbook.md#setup-upgrade-eject-internals)).

### Resolved questions

1. Greenfield detection when unclear (only docs, a spike folder): ask.
2. Monorepo baseline: one `.sdlc/baseline.md` with a package column.
3. Force-push guardrail: also blocks `--force-with-lease`, on main/master only.

## Consequences

- **Good:** plugin updates can patch projects safely; nothing a user edited is overwritten without asking; existing failures stop blocking new work; setup is resumable and reviewable as a PR.
- **Costs:** a lock file to keep consistent (only `scaffold.py` writes it); seeded files the user edits need a manual merge on upgrade; migrations must be written for any change to files projects own.
- **Follow-ups:** dogfood setup on the `sdlc` repo itself; first real migration will exercise the `--revisit` path.
