---
name: setting-up-projects
description: Sets up (greenfield or brownfield), upgrades or ejects the sdlc workflow in a repo, tracking every plugin-written file so plugin updates can patch it. Use when a repo has no .sdlc/config.json, its scaffold is behind the installed plugin, or the user asks to set up, upgrade or remove sdlc.
---

`${CLAUDE_PLUGIN_ROOT}` is the sdlc plugin's folder. Claude Code fills it in; on other agents it stays as written, so use the installed plugin's folder instead: the one above this file that holds `scripts/` and `skills/`.

# Setting Up Projects

Paths: `<change>` is the feature's change file (its record for people), `<state>` its state file (the agent's), `<work>` the folder beside it for working files (backlog, part plans, QA report) and `<docs>` the sdlc docs folder (`docs_dir`); `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py" paths <feature>` prints them for this repo's layout (`intents` is a pre-2.0 feature's documents folder).

Decisions behind it: `${CLAUDE_PLUGIN_ROOT}/docs/adr/0001-project-setup-upgrade-eject.md` and `0002-record-the-repos-own-commands.md`. This skill is the procedure; `scripts/scaffold.py` keeps the records exact. You make the judgment calls, the script does the bookkeeping. Never hand-edit `.sdlc/scaffold.lock.json`.

```bash
# Every command prints JSON; exit 2 = refused (user edited the file). A function named by $S, not a string in $S:
# zsh doesn't split a variable into words, and the quotes keep a plugin folder with spaces in one piece.
sdlc_scaffold() { python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py" "$@"; }; S=sdlc_scaffold
```

The shell forgets it between calls: put these lines at the top of each shell call that uses `$S`.

## Which flow


This skill runs in Claude Code, Codex, Cursor or Antigravity. First `$S host`: `host` is the agent running you, found from where the plugin is installed (or the environment). If it's `null`, ask the user which agent this is (the only time setup asks) and pass it as `--host`. Then `$S status`:

| `setup` | `drift` | Do |
|---|---|---|
| `none` | — | **Setup**: greenfield or brownfield (below) |
| `complete` | any, and `$S host` says `joining: true` | **Join** (below): another agent set this repo up; add this agent's layer only. Then handle `drift` as below |
| `in_progress` | — | Resume setup: skip `completed_steps` |
| `complete` | `behind` | **Upgrade**: `references/upgrade.md` |
| `complete` | `plugin_too_old` | Tell the user to update the plugin (`/plugin update sdlc`); change nothing |
| `complete` | `current` / `ahead` | Nothing to do; say so |

The user asks for `design` (`/sdlc:setup design`), to switch the design mode or finish impeccable's step: run **Revisiting it** in `references/design-mode.md` instead of the row (`setup: none` → run Setup, which asks it).

User asks to remove sdlc → **Eject**: `references/eject.md`.

## Ownership: what you may touch

Every file the plugin places is in one class (the lock records it). Respect it in every flow:

| Class | Examples | Rule |
|---|---|---|
| Generated | `.claude/rules/sdlc*.md` (including `sdlc-agents-md.md`, the Claude Code copy of `AGENTS.md`'s own text) | `$S render` / `$S agents` overwrite freely |
| Seeded | `.claude/hookify/sdlc-*.md`, `.github/workflows/sdlc-verify.yml`, `.sdlc/lint/*` | `$S render --if-unchanged`; exit 2 → show the user a diff, never overwrite |
| Keyed merge | `.claude/settings.json` allow entries, the plugin-enablement keys in `.claude/settings.local.json` (this machine only, never committed), `.gitignore` lines, the `<!-- sdlc:begin -->`…`<!-- sdlc:end -->` block in `AGENTS.md` | only via `$S allow` / `$S enable-plugin` / `$S gitignore` / `$S agents`; text outside the block is the user's |
| Commands | `commands` / `packages[].commands` in `.sdlc/config.json` | user-owned data; `$S contract` checks, `$S commands` prints the verify plan |
| User-owned | `CLAUDE.md`, the PRD (`<docs>/prd.md`, or the one the repo already had, recorded as `prd` in config), `<docs>/constitution.md`, `<docs>/design-system.md`, `knowledge/**`, `.sdlc/baseline.md`, other `.claude/rules/*.md` | write once with approval; afterwards only through approved migrations |

Plugin-owned files are named `sdlc-*` (or `sdlc.md`); everything else belongs to the project.

## Setup

**Before anything:** the working tree must be clean (else ask the user to commit or stash). Create branch `sdlc/setup`. Commit after each step (`chore(sdlc): setup – <step>`) and record it with `$S step-done <step>`, so an interrupted setup resumes. Never mark a step done without doing it. A step that doesn't apply (no AI config to migrate, a repo too small to audit, no lint config to import into) is still recorded, but say so in your next message with the reason, not only in the final report.

**Mode:** greenfield when the repo has no source files (ignore README, LICENSE, docs, dotfiles); brownfield otherwise. If it's unclear (only docs, a spike folder), ask.

1. `detect` – first `$S status` → `docs_site`: if it names a file, the repo builds a site from `docs/`, so `docs/sdlc` (where sdlc documents go) would be published. Say so and ask where they go: `.sdlc` itself, a folder of their choice, or `docs/sdlc` anyway. Then `$S init --kind <greenfield|brownfield> --docs-dir <that folder>` (default `docs/sdlc`); it records the detected host, or pass `--host <host>` when you had to ask. If `init` reports `legacy_features` (features from before setup), commit first (`relocate --apply` needs a clean tree), then run `$S relocate --docs-dir <d>` (preview) and `--apply` once the user agrees; it records `docs_dir`. Then follow `references/greenfield.md` or `references/brownfield.md` for the stack, commands, baseline, audit and CI steps. Both end with the project's commands recorded and checked (`$S contract` → `"ok": true`).
2. Then the common steps below, in order. Steps marked **Claude Code** write Claude Code's own files (`.claude/`): run them only when the host is `claude-code`, and record the others as done with "not this agent". The other agents get the same rules and workflow through the `agents` step.

### Common steps

| Step | Do |
|---|---|
| `rules` | **Claude Code.** `$S render templates/project/rules/sdlc.md .claude/rules/sdlc.md`, and for each of `code-style tests migrations sensitive ci ui`: `$S render templates/project/rules/<x>.md .claude/rules/sdlc-<x>.md`. Before rendering, check `$S config` → `areas.*` globs against the real layout; put project-specific globs in `.sdlc/config.json` (overrides only). |
| `guardrails` | **Claude Code.** For each entry of `$S guardrails` (the plugin's `sdlc-*` guardrails for this repo's design mode: impeccable mode leaves out `sdlc-ui-hardcoded-values`, whose job impeccable's detector hook does): `$S render <template> <dest> --class seeded`. Mention the list in one line; the user can delete any. |
| `lint` | Only for a linter the project already has (an `eslint.config.*` or eslint dependency; ruff configured in `pyproject.toml`): never install one, add its plugins (`globals`, …) or add a lint script; no linter → skip the step and say so in one line (`commands.lint` stays `null`). JS/TS: `$S render templates/project/lint/eslint.sdlc.mjs .sdlc/lint/eslint.sdlc.mjs --class seeded`, then propose the import in the user's `eslint.config.*` (diff, approved). Python: same with `ruff.sdlc.toml` and `extend = ".sdlc/lint/ruff.sdlc.toml"` in `pyproject.toml`. Run the lint command(s) afterwards: new warnings go to the baseline (brownfield) or get fixed (greenfield). |
| `allowlist` | **Claude Code.** `$S allow --from-commands` (adds `Bash(<command>:*)` for every command in config) |
| `enable-plugin` | **Claude Code.** **Ask first** (hard stop) where the keys that turn sdlc on go: **this machine only** (`$S enable-plugin`: `.claude/settings.local.json`, never committed; if git doesn't ignore it yet, the command adds it to `.git/info/exclude`, never the team's `.gitignore`) or **the team's committed file** (`$S enable-plugin --team`: `.claude/settings.json`, so every teammate who trusts the repo gets sdlc and its companions). Recommend the team file when the user wants teammates on sdlc. **It does not give a cloud session sdlc:** Claude Code on the web and routines don't install plugins a repo's `settings.json` turns on, whichever file holds the keys. When the user works in cloud sessions, say so and point to the wiki's Cloud sessions page (https://github.com/tammai/sdlc/wiki/Cloud-sessions) (org-wide server-managed settings, or a setup script on the cloud environment); sdlc writes neither. With `--team` the result has `commit`: commit that file with the step. Either way it turns sdlc on for this repo, plus each companion plugin that's on by default; once the team file holds them, later runs (a `--with`, upgrade) add there too. Its `companions` list gives every other one with its one-line reason: name them in one line ("also available: …"), and when the user wants one, `$S enable-plugin --with <id>`. Its `skills` list gives the companion skills (Cloudflare's `security-audit`), each with `installed` and its `install` command: name any not installed in the same line with that command. sdlc never installs one; run the command only when the user asks. Keys the user already set stay theirs. When the result has `skipped` (this session runs sdlc from a directory, e.g. `--plugin-dir`, not the installed copy), sdlc itself isn't written: say so in the setup report. **Conflicts:** `turned_off` lists plugins that clash with sdlc (superpowers) and were turned off for this repo only: warn the user in your next message, naming each, why it conflicts, and that it stays on everywhere else (`$S enable-plugin --remove`, or setting it back to `true` in `.claude/settings.local.json`, undoes it). `conflicts_in_repo` lists a tool written into the repo (spec-kit's `.specify/` and `speckit.*` commands): say why it conflicts and ask whether to keep it beside sdlc or remove its files; removing changes team files, so it's a hard stop. |
| `context-diet` | **Claude Code.** **Ask first**: offer to trim the plugins this project doesn't need, which Claude Code otherwise loads into every call. Accepted → follow `references/trimming-context.md`. It writes only `.claude/settings.local.json`, which is never committed: commit the step as usual (it holds only the lock's record) and never stage that file. Declined → record the step and say so. |
| `agents` | `$S agents`. With a host other than Claude Code recorded, it writes one managed block in `AGENTS.md` (Codex, Cursor and Antigravity all read it): the workflow rules, the plugin's policy rules, `CLAUDE.md` and the team's own `.claude/rules/`. With Claude Code recorded and team text in `AGENTS.md`, it also writes `.claude/rules/sdlc-agents-md.md` so Claude Code sees that text. Claude Code alone with no `AGENTS.md`: nothing to write. An error naming a file and line is a Claude-only construct (`${CLAUDE_PLUGIN_ROOT}`, `scaffold.py`): propose rewording it, then run it again. |
| `gitignore` | `$S gitignore --add ".sdlc/.work/" ".sdlc/state/*.json" ".sdlc/state/*.events.jsonl" ".sdlc/state/*.commands/"` (the last three: the control contract's runtime files, spec 12), plus `".claude/*.local.md"` when the host is Claude Code. Files already committed under those lines (the hooks' scratch, say) are untracked from the index and kept on disk; its `untracked` list says which, and the setup or upgrade commit records their removal from git: tell the user |
| `prd` | Every set-up project has a product doc (problem, audience, goals and non-goals, capabilities, constraints, success measures); Define reads it as background. One of three ways in. **A PRD already exists** (anywhere in the repo, or a path the user names): use it as is and never rewrite it; at most list the template's sections it lacks, then `$S prd <path>`. **Greenfield:** a short interview, about 6–8 questions in one message, each with a suggested answer the user can keep (who it's for, the problem, goals, what it won't do, the top capabilities, constraints, how success shows; voice and brand only with a UI). **Brownfield:** draft it from the README, docs, routes, models and screens, and end every line you guessed with "(inferred, confirm)". Non-goals only as the README or docs state them: something the code doesn't do yet is not a non-goal, and listing it would make a later feature look out of scope; with none stated, leave one line asking the user. Write from `${CLAUDE_PLUGIN_ROOT}/templates/prd-template.md` to `<docs>/prd.md` (a library, CLI or service skips Voice and brand) only after the user approves, then `$S prd <docs>/prd.md`. User-owned from then on, like the constitution: sdlc never overwrites it and eject keeps it. |
| `constitution` | `sdlc:project-constitution`, inferring from the repo, the PRD and the interview; keep the default **V. Simplicity**. User approves. |
| `design-system` | Follow `references/design-mode.md`. Only when the project has UI. The design mode, `builtin` or `impeccable`, is a hard stop asked every time, even when the answer looks obvious; record it with `$S design <mode>` and put the user's reason in the step's commit. impeccable installed but off for this repo → offer `$S design impeccable --enable`; it loads next session, so the step stays pending (`$S step-done design-system --pending <why>`) and setup resumes it after a restart. The UI guardrail is swapped only once impeccable's detector hook runs. User approves the design system doc. |
| `knowledge` | If `knowledge/index.md` is missing: `sdlc:managing-knowledge` setup, **steps 1 and 3 only** (index, log, folders, area rules). Skip its `CLAUDE.md` step: the knowledge pointer already lives in `.claude/rules/sdlc.md` (and in the `AGENTS.md` block for the other agents), and setup never creates or edits `CLAUDE.md`. Brownfield: the audit's approved drafts go here. User-owned from the start. |
| `finalize` | `$S status` lists `pending_steps`: any → don't finalize; commit, say what each waits for and that `/sdlc:setup` resumes it (a pending `design-system` needs a restart first). Else `$S step-done finalize --complete`, final commit, then merge `sdlc/setup` locally into the branch it was made from, without asking (`git switch <that branch>` then `git merge --no-ff sdlc/setup`) and delete `sdlc/setup`. Never push or open a PR unless the user asks; a merge conflict stops for the user. |

## Join: a second agent in a set-up repo

The repo's shared setup (config and commands, baseline, PRD, constitution, design system, CI, knowledge) is already done and committed; never redo it. Clean tree, branch `sdlc/join-<host>`, then:

1. `$S add-host <host>`.
2. Host is `claude-code`: run the **Claude Code** steps (`rules`, `guardrails`, `allowlist`, `enable-plugin`, `context-diet` with its question, the `.claude/*.local.md` ignore line). Any other host: nothing of its own to write.
3. `$S agents`: rebuilds the `AGENTS.md` block for every recorded host and, with Claude Code recorded, the `.claude/rules/sdlc-agents-md.md` copy of the team's own `AGENTS.md` text. What the first agent's team wrote (`CLAUDE.md`, `.claude/rules/`, `AGENTS.md`) is carried over, never rewritten.
4. Check: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/doctor.py"` reports no fails. One commit (`chore(sdlc): join – <host>`), then merge the branch locally as in `finalize`, without asking.

Report: the host added, the hosts now recorded, files written.

## Hard stops (always ask)

A hard stop ends your turn: ask it with the question tool (Claude Code: `AskUserQuestion`, your proposal first as the `(Recommended)` option, the question standing on its own; another agent: its own question tool, else the question as the message's last line) and wait for the answer before writing anything it covers. Never bury a question in a progress update. Never answer it yourself, even when the choice looks obvious.

Stack choice (greenfield) · where sdlc documents go when the repo has a docs site · monorepo team size, team handles, `infras/` and the contract check (`references/monorepo.md`) · the commands (brownfield) · installing any tool · each audit batch before it is written · each AI-config migration · adding CI to a repo that already has CI · lint config import · which agent is running, only when `$S host` can't tell · PRD (before it's written, and which existing doc to use) · constitution · design mode (builtin or impeccable) and the design system · where the plugin keys go (this machine or the team's `.claude/settings.json`) · trimming plugins for this project · removing a conflicting tool's files (spec-kit) · PR vs local merge. Everything else proceeds without asking.

## Report

Mode, branch, steps done, files added (by class), baseline size (brownfield), anything skipped and why, and the next step: `/sdlc:start <first feature>`.
