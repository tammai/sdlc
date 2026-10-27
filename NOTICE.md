# Third-party notices

This plugin bundles and adapts material from the projects below. Their license texts are in `licenses/`. The optional companion plugin in `plugins/sdlc-extras/` holds some of it; it is listed under each source below.

## Superpowers — MIT License, Copyright (c) 2025 Jesse Vincent
https://github.com/obra/superpowers — `licenses/superpowers-MIT.txt`

Copied: skills `brainstorming`, `writing-plans`, `executing-plans`, `subagent-driven-development`, `dispatching-parallel-agents` (now `skills/orchestrator/references/dispatching-parallel-agents.md`), `test-driven-development`, `systematic-debugging`, `verification-before-completion`, `requesting-code-review` (now `skills/executing-plans/references/requesting-code-review.md` and `code-reviewer.md`), `receiving-code-review`, `using-git-worktrees`, `finishing-a-development-branch` (these three now `skills/orchestrator/references/<name>.md`), and `using-superpowers/references/claude-code-tools.md` (now `skills/executing-plans/references/`).

Modified: skill cross-references renamed from `superpowers:` to `sdlc:`; output paths moved to `.sdlc/<feature>/` and working files to `.sdlc/.work/`; brainstorming hands back to the orchestrator and doesn't re-ask Define's blocking questions; `executing-plans` and `subagent-driven-development` skip their final whole-branch review when the orchestrator moves it to Prove (the review stays on the top tier), and under the orchestrator ("Prove is the only review") `subagent-driven-development` also skips its per-task reviews; the brainstorm companion's remote logo fetch is disabled by default; `systematic-debugging`'s creation log and pressure-test scenarios are not shipped. The descriptions of `brainstorming`, `test-driven-development` and `systematic-debugging` are rewritten to say what each does and when, scoped to the orchestrator's phases, instead of firing on any creative work, feature or bug.

## GitHub Spec Kit — MIT License, Copyright GitHub, Inc.
https://github.com/github/spec-kit — `licenses/spec-kit-MIT.txt`

Copied: `templates/spec-template.md`, `templates/constitution-template.md`, and `templates/design-template.md` (originally `plan-template.md`), with command placeholders and paths updated.

Adapted (rewritten without the Spec Kit CLI, scripts and extension hooks): skills `writing-specs` (from `specify`), `clarifying-specs` (from `clarify`), `designing-solutions` (from `plan`), `analyzing-consistency` (from `analyze`), `project-constitution` (from `constitution`).

## Anthropic Claude Code plugins — Apache License 2.0, Copyright Anthropic, PBC
https://github.com/anthropics/claude-plugins-official — `licenses/anthropic-plugins-Apache-2.0.txt`

- **feature-dev:** agents `code-explorer`, `code-architect`, and `code-reviewer` (renamed `feature-reviewer` to avoid a name clash; in `plugins/sdlc-extras/agents/`)
- **pr-review-toolkit:** command `review-pr`; agents `code-reviewer`, `pr-test-analyzer`, `silent-failure-hunter`, and `comment-analyzer`, `type-design-analyzer` (in `plugins/sdlc-extras/agents/`)
- **code-simplifier:** agent `code-simplifier` (in `plugins/sdlc-extras/agents/`)
- **code-review:** command `code-review`
- **commit-commands:** commands `commit`, `commit-push-pr`, `clean_gone`
- **claude-md-management:** command `revise-claude-md` (modified to route lessons into the 3 knowledge tiers), skill `claude-md-improver` (now `skills/managing-knowledge/references/claude-md-improver.md` and its folder; its `update-guidelines.md` folded into `revise-claude-md`)
- **hookify:** command `hookify` (now `skills/hookify/SKILL.md`); commands `list` → `hookify-list`, `configure` → `hookify-configure`, `help` → `hookify-help` and agent `conversation-analyzer` (in `plugins/sdlc-extras/`); skill `writing-rules` (now `skills/hookify/references/rule-syntax.md`); `core/`, `matchers/`, `utils/`, hook scripts, examples
- **ralph-loop:** commands `ralph-loop`, `cancel-ralph`, `help` → `ralph-help`; `hooks/stop-hook.sh`; `scripts/setup-ralph-loop.sh` (all in `plugins/sdlc-extras/`)
- **security-guidance:** hook scripts in `hooks/` (`security_reminder_hook.py` and its modules, `sg-python.sh`; the launcher now starts every sdlc hook, remembers the interpreter it found and words its errors for all of them)
- **typescript-lsp:** language server config, now `.lsp.json`

Modified: command and skill references renamed to the `sdlc:` namespace (`sdlc-extras:` for what moved to the companion plugin, whose agents' descriptions are shortened); the three plugins' hook configs merged into `hooks/hooks.json`; hookify's `posttooluse.py` removed (rules aren't evaluated after tool use, so it was never registered); `security_reminder_hook.py`'s commit review asks `hooks/sdlc_review_gate.py` which commits to review (and skips a feature's change that isn't security-touched), so while an sdlc feature is active a build commit is deferred and the next review-ready commit's review covers it as one net diff (one review per review-ready diff, not per commit); no amend-delta review then. Bug fixes, covered by `tests/`: hookify's `new_text` field falls back to `content` for `Write`; hookify gains a `not_regex_match` operator (the `require-tests-stop` example uses it); hookify also loads committed team rules from `.claude/hookify/*.md`, sends warnings to Claude as `additionalContext` and block reasons as `permissionDecisionReason` (upstream only used `systemMessage`, which only the user sees), and its PostToolUse hook is no longer registered (it re-evaluated the same rules, so every warning fired twice); ralph's `stop-hook.sh` no longer crashes on a state file missing a frontmatter field. The pr-review-toolkit `code-reviewer` is read-only: it may run the project's test command but no scripts of its own (ADR 0012). `TodoWrite` is dropped from the feature-dev agents' tools and the `hookify` command, since Claude Code no longer provides it by default.

Not included: Anthropic's `claude-security` plugin (its license reserves all rights). Install it separately if you want deep vulnerability scans.

## Everything else
The orchestrator, setting-up-projects and managing-knowledge skills (with `skills/orchestrator/references/` and `skills/setting-up-projects/references/trimming-context.md`), the `ac-checker`, `verifier`, `qa-tester` and `ui-reviewer` agents, `hooks/verify_freshness.py`, `sdlc_review_gate.py`, `model_router.py`, `role_guard.py`, `prove_budget.py` and `trust_anchor.py`, the `start`, `status`, `knowledge-audit` and `deploy` commands, everything in `scripts/`, `templates/knowledge/`, `templates/project/`, `templates/design-system-template.md`, `templates/backlog-template.md`, `migrations/` and `tests/` are original to this plugin, MIT licensed (`LICENSE`).
