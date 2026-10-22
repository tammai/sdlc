# Eject

Removes what the plugin owns from the project and keeps everything the team made with it.

```bash
$S eject           # dry run: delete / ask / already_gone / unmerge / keep
```

Show the plan in a few lines. **Keeps:** `.sdlc/config.json` (with the commands), constitution, design system, `knowledge/`, baseline, area rules, and every `.sdlc/<feature>/`. **Removes:** generated rules, unedited seeded files (guardrails, CI workflow, lint snippets), the allowlist and `.gitignore` entries the plugin added, and the lock.

For each file under `ask` (seeded but edited): ask whether to delete it too.

Clean working tree, branch `sdlc/eject`, then:

1. `$S eject --apply --also <edited files the user agreed to delete>`
2. Imports the user added during setup now point at deleted files: the `eslint.sdlc.mjs` import in `eslint.config.*`, `extend = ".sdlc/lint/ruff.sdlc.toml"` in `pyproject.toml`. Propose a diff for each (approved) so nothing is left broken.
3. Run the verify commands (`$S commands` before ejecting, or from `.sdlc/config.json`) to confirm the project still builds.
4. Commit, then **ask**: open a PR or merge locally.

Report what was removed, what was kept, and that the plugin can be uninstalled (`/plugin uninstall sdlc`) or set up again later with `/sdlc:setup`.
