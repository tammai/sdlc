---
name: setting-up-projects
description: Use when a project has no .sdlc/config.json yet (new or existing repo), when /sdlc:start or /sdlc:status reports the project isn't set up or its scaffold is behind the installed plugin, or when the user asks to set up, upgrade or remove the sdlc workflow in a repo. Runs setup (greenfield or brownfield), upgrade and eject, keeping every plugin-written file tracked so later plugin updates can patch it safely.
---

# Setting Up Projects

Decisions behind it: `${CLAUDE_PLUGIN_ROOT}/docs/adr/0001-project-setup-upgrade-eject.md` and `0002-record-the-repos-own-commands.md`. This skill is the procedure; `scripts/scaffold.py` keeps the records exact. You make the judgment calls, the script does the bookkeeping. Never hand-edit `.sdlc/scaffold.lock.json`.

```bash
S="python3 ${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py"   # every command prints JSON; exit 2 = refused (user edited the file)
```

## Which flow

Run `$S status`:

| `setup` | `drift` | Do |
|---|---|---|
| `none` | — | **Setup**: greenfield or brownfield (below) |
| `in_progress` | — | Resume setup: skip `completed_steps` |
| `complete` | `behind` | **Upgrade**: `references/upgrade.md` |
| `complete` | `plugin_too_old` | Tell the user to update the plugin (`/plugin update sdlc`); change nothing |
| `complete` | `current` / `ahead` | Nothing to do; say so |

User asks to remove sdlc → **Eject**: `references/eject.md`.

## Ownership: what you may touch

Every file the plugin places is in one class (the lock records it). Respect it in every flow:

| Class | Examples | Rule |
|---|---|---|
| Generated | `.claude/rules/sdlc*.md` | `$S render` overwrites freely |
| Seeded | `.claude/hookify/sdlc-*.md`, `.github/workflows/sdlc-verify.yml`, `.sdlc/lint/*` | `$S render --if-unchanged`; exit 2 → show the user a diff, never overwrite |
| Keyed merge | `.claude/settings.json` allow entries, `.gitignore` lines | only via `$S allow` / `$S gitignore` |
| Commands | `commands` / `packages[].commands` in `.sdlc/config.json` | user-owned data; `$S contract` checks, `$S commands` prints the verify plan |
| User-owned | `CLAUDE.md`, `.sdlc/constitution.md`, `.sdlc/design-system.md`, `knowledge/**`, `.sdlc/baseline.md`, other `.claude/rules/*.md` | write once with approval; afterwards only through approved migrations |

Plugin-owned files are named `sdlc-*` (or `sdlc.md`); everything else belongs to the project.

## Setup

**Before anything:** the working tree must be clean (else ask the user to commit or stash). Create branch `sdlc/setup`. Commit after each step (`chore(sdlc): setup – <step>`) and record it with `$S step-done <step>`, so an interrupted setup resumes. Never mark a step done without doing it. A step that doesn't apply (no AI config to migrate, a repo too small to audit, no lint config to import into) is still recorded, but say so in your next message with the reason, not only in the final report.

**Mode:** greenfield when the repo has no source files (ignore README, LICENSE, docs, dotfiles); brownfield otherwise. If it's unclear (only docs, a spike folder), ask.

1. `detect` – `$S init --kind <greenfield|brownfield>`. Then follow `references/greenfield.md` or `references/brownfield.md` for the stack, commands, baseline, audit and CI steps. Both end with the project's commands recorded and checked (`$S contract` → `"ok": true`).
2. Then the common steps below, in order.

### Common steps

| Step | Do |
|---|---|
| `rules` | `$S render templates/project/rules/sdlc.md .claude/rules/sdlc.md`, and for each of `code-style tests migrations sensitive ci ui`: `$S render templates/project/rules/<x>.md .claude/rules/sdlc-<x>.md`. Before rendering, check `$S config` → `areas.*` globs against the real layout; put project-specific globs in `.sdlc/config.json` (overrides only). |
| `guardrails` | For each `${CLAUDE_PLUGIN_ROOT}/templates/project/hookify/sdlc-*.md`: `$S render templates/project/hookify/<f> .claude/hookify/<f> --class seeded`. Mention the list in one line; the user can delete any. |
| `lint` | JS/TS: `$S render templates/project/lint/eslint.sdlc.mjs .sdlc/lint/eslint.sdlc.mjs --class seeded`, then propose the import in the user's `eslint.config.*` (diff, approved). Python: same with `ruff.sdlc.toml` and `extend = ".sdlc/lint/ruff.sdlc.toml"` in `pyproject.toml`. Run the lint command(s) afterwards: new warnings go to the baseline (brownfield) or get fixed (greenfield). |
| `allowlist` | `$S allow --from-commands` (adds `Bash(<command>:*)` for every command in config) |
| `gitignore` | `$S gitignore --add ".sdlc/.work/" ".claude/*.local.md"` |
| `constitution` | `sdlc:project-constitution`, inferring from the repo and the interview; keep the default **V. Simplicity**. User approves. |
| `design-system` | Only when the project has UI: files match `areas.ui`, or the greenfield stack has a web, mobile or desktop UI. No UI → record the step and say so. First fix `areas.ui` to the real UI paths (e.g. `lib/**/*.dart` for Flutter, `**/*View.swift`). **Existing system:** find it (tokens or theme files, Tailwind theme or `@theme`, the UI library in the manifest, shadcn's `components.json`, a `components/ui` folder, Storybook) and fill `.sdlc/design-system.md` from `${CLAUDE_PLUGIN_ROOT}/templates/design-system-template.md`, pointing at it rather than copying values. **None:** propose one mainstream component library for the stack plus a minimal token set (color roles, spacing, type scale, radius), create the tokens file in the stack's usual place, and fill the doc from it; never invent a full bespoke system. User approves. |
| `knowledge` | If `knowledge/index.md` is missing: `sdlc:managing-knowledge` setup, **steps 1 and 3 only** (index, log, folders, area rules). Skip its `CLAUDE.md` step: the knowledge pointer already lives in `.claude/rules/sdlc.md`, and setup never creates or edits `CLAUDE.md`. Brownfield: the audit's approved drafts go here. User-owned from the start. |
| `finalize` | `$S step-done finalize --complete`, final commit, then **ask**: open a PR (`gh pr create`, body lists what was added and why) or merge `sdlc/setup` locally. Never push or merge without the answer. |

## Hard stops (always ask)

Stack choice (greenfield) · the commands (brownfield) · installing any tool · each audit batch before it is written · each AI-config migration · adding CI to a repo that already has CI · lint config import · constitution · design system · PR vs local merge. Everything else proceeds without asking.

## Report

Mode, branch, steps done, files added (by class), baseline size (brownfield), anything skipped and why, and the next step: `/sdlc:start <first feature>`.
