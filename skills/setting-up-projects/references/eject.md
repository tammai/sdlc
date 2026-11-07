`${CLAUDE_PLUGIN_ROOT}` is the sdlc plugin's folder. Claude Code fills it in; on other agents it stays as written, so use the installed plugin's folder instead: the one above this file that holds `scripts/` and `skills/`.

# Eject

Paths: `<change>` is the feature's change file (its record for people), `<state>` its state file (the agent's), `<work>` the folder beside it for working files (backlog, part plans, QA report) and `<docs>` the sdlc docs folder (`docs_dir`); `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py" paths <feature>` prints them for this repo's layout (`intents` is a pre-2.0 feature's documents folder).

Removes what the plugin owns from the project and keeps everything the team made with it.

```bash
$S eject           # dry run: delete / ask / already_gone / unmerge / keep
```

Show the plan in a few lines. **Keeps:** the plan's `keep` list, which names only what exists here (any of `.sdlc/config.json` with the commands, the PRD, constitution, design system, `knowledge/`, baseline, and every feature's record: its change file (`<docs>/changes/`; older features: `<docs>/intents/`) and state (`.sdlc/state/`, or `.sdlc/<feature>/` in the old layout)), plus area rules; never name one the list leaves out. **Removes:** generated rules, unedited seeded files (guardrails, CI workflow, lint snippets), the allowlist, plugin-enablement and `.gitignore` entries the plugin added, the sdlc block in `AGENTS.md` (the file too if the plugin created it), and the lock.

For each file under `ask` (seeded but edited): ask whether to delete it too.

Clean working tree, branch `sdlc/eject`, then:

1. `$S eject --apply --also <edited files the user agreed to delete>`
2. Imports the user added during setup now point at deleted files: the `eslint.sdlc.mjs` import in `eslint.config.*`, `extend = ".sdlc/lint/ruff.sdlc.toml"` in `pyproject.toml`. Propose a diff for each (approved) so nothing is left broken.
3. Run the verify commands (`$S commands` before ejecting, or from `.sdlc/config.json`) to confirm the project still builds.
4. Commit, then merge the branch locally as in setup's `finalize`, without asking.

Report what was removed, what was kept (including any plugin key under the result's `kept`: one sdlc wrote that the user has since changed, so it stays), and that the plugin can be uninstalled (`/plugin uninstall sdlc`) or set up again later with `/sdlc:setup`.
