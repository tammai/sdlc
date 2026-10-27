This repo uses the sdlc workflow. It runs from the sdlc plugin in Claude Code, Codex, Cursor or Antigravity. Start or resume work through the plugin: its `start` command, or its `orchestrator` skill. If your agent doesn't have the plugin, follow these rules so that your work doesn't break the workflow's stage gates or its verification records.

- A feature's documents (spec, design, plan) live in `{{layout.intents_root}}<feature>/`, and its state file lives under `{{layout.state_root}}`. Before changing code for a feature, read its spec and plan, and work only on the tasks the plan gives you.
- Never edit these files by hand. Only the sdlc workflow's own steps write them, because they record the stage gates and the verification evidence:
  - a feature's state file under `{{layout.state_root}}`
  - `review.md` (`test-report.md` on older features) in a feature's documents folder
  - `{{config.baseline}}`, the list of failures that existed before
- If one of them needs to change, say so, and run the stage through the plugin, or ask a teammate who has the plugin to run it.
- A feature's state file names its `Owner:` (a git email) and `Tool:` (the agent). Before advancing a feature someone else owns, ask the user first: two people advancing one feature conflict on its state file. When the plugin advances it for a new owner, it records the handover.
- Use the project's commands exactly as written in `.sdlc/config.json`: `commands`, or for a monorepo, `commands` per package under `packages`. Run them from the package's directory. A full test run is the `test` command with no filters.
- The project's principles are in `{{layout.constitution}}`. For team knowledge, open `knowledge/index.md` and follow its links as needed.
- Scratch files go in `.sdlc/.work/`, which git ignores.
