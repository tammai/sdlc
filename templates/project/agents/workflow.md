This repo runs the sdlc workflow in Claude Code. Teammates on Cursor or Codex follow these rules so that their work doesn't break the workflow's stage gates or its verification records.

- A feature's documents (spec, design, plan) live in `{{layout.intents_root}}<feature>/`, and its state file lives under `{{layout.state_root}}`. Before changing code for a feature, read its spec and plan, and work only on the tasks the plan gives you.
- Never edit these files. Only the sdlc workflow in Claude Code writes them, because they record the stage gates and the verification evidence:
  - a feature's state file under `{{layout.state_root}}`
  - `test-report.md` in a feature's documents folder
  - `{{config.baseline}}`, the list of failures that existed before
- If one of them needs to change, say so, and ask a teammate on Claude Code to run the stage. `/sdlc:start` resumes a feature, and `/sdlc:status` shows where it is.
- Use the project's commands exactly as written in `.sdlc/config.json`: `commands`, or for a monorepo, `commands` per package under `packages`. Run them from the package's directory. A full test run is the `test` command with no filters.
- The project's principles are in `{{layout.constitution}}`. For team knowledge, open `knowledge/index.md` and follow its links as needed.
- Scratch files go in `.sdlc/.work/`, which git ignores.
