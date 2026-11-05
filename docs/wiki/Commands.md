# Commands

| Command | Does |
|---|---|
| `/sdlc:start [request]` | Start a feature, or resume the active one if the request is empty (`B<n>`: a named part) |
| `/sdlc:setup [what you're building]` | Set the repo up once (greenfield or brownfield); resumes if interrupted |
| `/sdlc:upgrade [--dry-run] [--revisit]` | Bring the repo's scaffold up to the installed plugin version |
| `/sdlc:eject` | Remove the plugin's files from the repo, keeping your work |
| `/sdlc:doctor` | Health check of the machine, the plugin and the repo, with a fix for each problem. Changes nothing |
| `/sdlc:status` | Setup state and version drift, then one line per feature: track, phase, last gate, open questions. Changes nothing |
| `/sdlc:deploy [feature] [environment]` | Deploy on request through the project's own deploy path, with your go-ahead before production or a DB migration |
| `/sdlc:prune [--older-than 45d]` | Delete the working files of merged, finished features; keeps the change file and state. Asks first, one commit |
| `/sdlc:context-diet` | Propose turning off plugins and skills this project doesn't need, in `.claude/settings.local.json`, after you approve. Any repo, Claude Code only |
| `/sdlc:review-pr` | Local pre-PR review of the diff with the right agents for it |
| `/sdlc:code-review` | Review a GitHub PR (needs `gh`) |
| `/sdlc:commit`, `/sdlc:commit-push-pr`, `/sdlc:clean-gone` | Git helpers |
| `/sdlc:revise-claude-md`, `/sdlc:knowledge-audit` | Promote lessons; keep always-loaded context small |
| `/sdlc:hookify` | Turn repeated corrections into rules |
| `/sdlc-extras:ralph-loop`, `/sdlc-extras:cancel-ralph`, `/sdlc-extras:ralph-help` | Optional self-iterating loop for one well-specified task (`sdlc-extras` plugin) |
| `/sdlc-extras:hookify-list`, `/sdlc-extras:hookify-configure`, `/sdlc-extras:hookify-help` | List, toggle and explain hookify rules (`sdlc-extras` plugin) |
