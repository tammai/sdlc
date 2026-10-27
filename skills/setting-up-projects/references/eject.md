`${CLAUDE_PLUGIN_ROOT}` is the sdlc plugin's folder. Claude Code fills it in; on other agents it stays as written, so use the installed plugin's folder instead: the one above this file that holds `scripts/` and `skills/`.

# Eject

Paths: `<intents>` is the feature's documents folder, `<state>` its state file and `<docs>` the sdlc docs folder (`docs_dir`); `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py" paths <feature>` prints them for this repo's layout.

Removes what the plugin owns from the project and keeps everything the team made with it.

```bash
$S eject           # dry run: delete / ask / already_gone / unmerge / keep
```

Show the plan in a few lines. **Keeps:** `.sdlc/config.json` (with the commands), constitution, design system, `knowledge/`, baseline, area rules, and every feature's documents (`<intents>/`) and state (`.sdlc/state/`, or `.sdlc/<feature>/` in the old layout). **Removes:** generated rules, unedited seeded files (guardrails, CI workflow, lint snippets), the allowlist, plugin-enablement and `.gitignore` entries the plugin added, the sdlc block in `AGENTS.md` (the file too if the plugin created it), and the lock.

For each file under `ask` (seeded but edited): ask whether to delete it too.

Clean working tree, branch `sdlc/eject`, then:

1. `$S eject --apply --also <edited files the user agreed to delete>`
2. Imports the user added during setup now point at deleted files: the `eslint.sdlc.mjs` import in `eslint.config.*`, `extend = ".sdlc/lint/ruff.sdlc.toml"` in `pyproject.toml`. Propose a diff for each (approved) so nothing is left broken.
3. Run the verify commands (`$S commands` before ejecting, or from `.sdlc/config.json`) to confirm the project still builds.
4. Commit, then **ask**: open a PR or merge locally.

Report what was removed, what was kept, and that the plugin can be uninstalled (`/plugin uninstall sdlc`) or set up again later with `/sdlc:setting-up-projects`.
