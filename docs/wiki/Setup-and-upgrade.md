# Setup and upgrade

## 14. Adopt sdlc in an existing repo

1. Install the plugin ([Install](Install.md)).
2. Commit or stash your work, then `/sdlc:setup`. It detects brownfield and works on a `sdlc/setup` branch, one commit per step.
3. **Commands:** it records the commands you already use (`pnpm test`, `make lint`, `./gradlew build`, …) in `.sdlc/config.json`, per package in a monorepo. A missing step stays `null`. It doesn't touch your manifest, dependencies or tooling. You approve the list.
4. **Baseline:** it runs them and records what already fails in `.sdlc/baseline.md`. Features are judged only on new failures. A failing install or build stops setup.
5. **Audit:** explorer agents draft conventions, gotchas from git history, decisions and per-area rules. You approve, edit or drop each item.
6. **Existing AI config** (long `CLAUDE.md`, `AGENTS.md`, Cursor rules, ADRs): one migration diff per source; originals stay unless you say delete.
7. **The rest:** rules, guardrails, lint snippets (only for a linter you already have), allowlist, a product doc (PRD; yours if you have one, else drafted and approved), constitution, a design system (UI projects only: first who does the design work, sdlc's builtin system or impeccable, recommended from the PRD), knowledge. Turning sdlc on for this repo asks one thing, where: `.claude/settings.local.json`, your machine's file, never committed, or the committed `.claude/settings.json`, which teammates get too (a cloud session doesn't install plugins from it; see [Cloud sessions](Cloud-sessions.md)); setup names the companion plugins it can add too (`sdlc-extras`; skipped for sdlc itself, and said so, when the session runs sdlc from a directory with `--plugin-dir`), and the companion skill Cloudflare's `security-audit` with its install command, for a full security audit on request (sdlc never installs or runs it unasked). The context diet is asked first ([13](Rules-and-context.md#13-keep-always-loaded-context-small)). Existing CI is left alone (it points out steps that differ from the recorded commands); a repo without CI is offered a workflow, and every repo the `sdlc-invariants` check.
8. At the end it merges `sdlc/setup` into your branch locally, without asking; nothing is pushed. Then `/sdlc:start` a small S fix to see the loop end to end.

Interrupted? Run `/sdlc:setup` again; it resumes from the last finished step.

## 15. Start a new project

1. Create an empty repo (README and LICENSE are fine) and run `/sdlc:setup what you're building`.
2. Answer a few stack questions. It proposes the stack, layout, generator and the commands per package, plus optional extras (a linter, formatter, toolchain pinning), each off unless you say yes. **You approve before anything is generated.** No auth, database or infra "for later" unless you asked.
3. The ecosystem's own generators build the skeleton, plus strict types, a test runner and one passing test per package. Every command must pass.
4. CI: `.github/workflows/sdlc-verify.yml` from the same commands, with `sdlc-invariants.yml` beside it to check the shared sdlc files. Windows teammates: set `"ci": {"os": ["ubuntu-latest", "windows-latest"]}` in `.sdlc/config.json`.
5. The common steps as in [14](#14-adopt-sdlc-in-an-existing-repo). No baseline: nothing fails yet.
6. It merges locally, then `/sdlc:start` the first feature.

**Several apps** (web, an API, mobile): one monorepo, with `apps/<name>/` per app, `packages/` for shared code, `docs/` for BA, QA and design files, and `infras/` only if you say yes. It asks who will work in the repo. Separate roles get CODEOWNERS, one CI workflow per app and a release runbook (`docs/runbooks/releasing.md`); a solo developer or small team gets one workflow. When one app serves an API another uses, the contract goes in `packages/api-contract/v1/`, and if you agree, CI blocks breaking changes to published versions. Details: `skills/setting-up-projects/references/monorepo.md`.

## 16. Upgrade after a plugin update

`/sdlc:start` and `/sdlc:status` tell you when the repo's scaffold is behind the installed plugin. Nothing breaks if you wait; you miss the new rules and fixes.

1. Finish or pause in-flight features if you can.
2. `/sdlc:upgrade --dry-run` shows the plan: files added, regenerated, replaced, edited by you, deleted by you, no longer shipped, and migrations.
3. `/sdlc:upgrade` runs it on a `sdlc/upgrade-<from>-<to>` branch. A new CI workflow is asked about first. For each plugin file you edited you choose: **apply** the proposed merge, **skip** this time, or **keep mine** (the plugin stops managing it). An edited guardrail (`.claude/hookify/sdlc-*.md`) you apply yourself: Claude is blocked from editing the rules that constrain it.
4. Each migration is shown as a diff. Declined ones aren't asked again; `/sdlc:upgrade --revisit` brings them back.
5. It merges the branch locally, without asking. The repo now records the minimum plugin version, so teammates on an older plugin are told to update.

## 17. Remove sdlc from a repo

`/sdlc:eject` shows a dry run first. It removes the plugin's own files (generated rules, unedited guardrails, CI workflow and lint snippets, the allowlist, plugin-enablement and `.gitignore` entries it added, the sdlc block in `AGENTS.md`, the lock) and keeps `.sdlc/config.json`, the PRD, the constitution, design system, knowledge, baseline, area rules and every feature's change file (older features: their documents) and state. Edited plugin files are asked about one by one. On a `sdlc/eject` branch it fixes imports that would point at deleted files, runs the verify commands, then merges locally without asking. Uninstall the plugin afterwards (`/plugin uninstall sdlc`) if you're done with it.

## 18. Clean up finished features

Every feature keeps its working files after it ships. Old plans and reports describe code that has since changed, and agents searching the repo can be misled by them.

1. `/sdlc:prune` lists features marked done on the main branch 45+ days ago (`--older-than 90d` to change that), with the files that would go: the parts' `plan-B<n>.md` files and `qa-report.md`.
2. Pick which to prune. The change file and the state file stay.
3. It commits the deletions in one commit. Git history keeps everything.
