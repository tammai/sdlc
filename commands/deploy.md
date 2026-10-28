---
description: Deploy a shipped feature through the project's own deploy path, with an explicit go-ahead before any production deploy or DB migration, a smoke test and a release record
argument-hint: "[feature] [environment]"
---

`${CLAUDE_PLUGIN_ROOT}` is the sdlc plugin's folder. Claude Code fills it in; on other agents it stays as written, so use the installed plugin's folder instead: the one above this file that holds `scripts/` and `skills/`.

Paths: `<intents>` is the feature's documents folder, `<state>` its state file and `<docs>` the sdlc docs folder (`docs_dir`); `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py" paths <feature>` prints them for this repo's layout.

Deploy runs only on request; it isn't a phase, and no track runs it on its own. `$ARGUMENTS` may name the feature and the environment.

1. **What to deploy.** The named feature, else the only active one (or the one just shipped). If its state file exists and `Current:` is before Stage 8, say that it hasn't passed Review and Ship, and continue only if the user says so (record it with `state.py deviation`).
2. **How.** Use the project's existing deploy path: scripts, a CI job or the platform CLI. Never invent one. If there is none, say so and stop. For platform integrations see `${CLAUDE_PLUGIN_ROOT}/skills/orchestrator/references/integrations.md`.
3. **Go-ahead (hard stop).** Before any production deploy or DB migration, show the environment, version or commit, the steps you'll run, the migration (if any) and the rollback command, and wait for the user's explicit yes. A staging or preview deploy the project treats as routine needs no extra stop.
4. **Deploy and smoke test.** Run the steps, then a smoke test (the project's own, or a request to the main endpoint or screen). If it fails, say what failed and offer the rollback; running the rollback on production is another go-ahead.
5. **Record.** Write `<intents>/release.md` with the version, environment, steps run, smoke-test result and rollback command. If a state file exists: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/state.py" log <feature> "deployed <version> to <environment>: smoke test <pass|fail>"`. Commit `release.md` only if the user asks.
