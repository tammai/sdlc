---
name: prune
description: Delete the working files of finished, merged features (parts' plans, reports, checklists) and keep their record (the change file and state; intent, spec, design, retro on older features). Shows the list and asks before deleting
---

`${CLAUDE_PLUGIN_ROOT}` is the sdlc plugin's folder. Claude Code fills it in; on other agents it stays as written, so use the installed plugin's folder instead: the one above this file that holds `scripts/` and `skills/`.

Paths: `<change>` is the feature's change file (its record for people), `<state>` its state file (the agent's), `<work>` the folder beside it for working files (backlog, part plans, QA report) and `<docs>` the sdlc docs folder (`docs_dir`); `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py" paths <feature>` prints them for this repo's layout (`intents` is a pre-2.0 feature's documents folder).


1. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/prune.py" list <the user's request>`. If it prints an `error`, say it and stop.
2. Nothing in `prune`: say so, list the `skipped` features with their reason in one line each, and stop.
3. Show each feature in `prune` with its age and the files that would go. Say that the change file and the state file stay (a 2.0 feature's whole record), as do intent, spec, design and retro on older features, a 2.0 feature's plans go, review.md (with its security section) and security.md stay on high-risk features, and git history keeps every deleted file. Ask which to prune (all, some, none).
4. For the chosen features run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/prune.py" apply <the user's request> <feature>...`. Report any `refused` entries with their reason.
5. Commit the deletions in one commit, `Prune finished feature records: <features>`, staging only the deleted paths. Don't push.
