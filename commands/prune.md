---
description: Delete the working files of finished, merged features (parts' plans, reports, checklists) and keep their record (change.md and state; intent, spec, design, retro on older features). Shows the list and asks before deleting
argument-hint: "[--older-than 45d]"
---

`${CLAUDE_PLUGIN_ROOT}` is the sdlc plugin's folder. Claude Code fills it in; on other agents it stays as written, so use the installed plugin's folder instead: the one above this file that holds `scripts/` and `skills/`.

Paths: `<intents>` is the feature's documents folder, `<state>` its state file and `<docs>` the sdlc docs folder (`docs_dir`); `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py" paths <feature>` prints them for this repo's layout.


1. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/prune.py" list $ARGUMENTS`. If it prints an `error`, say it and stop.
2. Nothing in `prune`: say so, list the `skipped` features with their reason in one line each, and stop.
3. Show each feature in `prune` with its age and the files that would go. Say that change.md and the state file stay (a 2.0 feature's whole record), as do intent, spec, design and retro on older features, a 2.0 feature's plans go, review.md (with its security section) and security.md stay on high-risk features, and git history keeps every deleted file. Ask which to prune (all, some, none).
4. For the chosen features run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/prune.py" apply $ARGUMENTS <feature>...`. Report any `refused` entries with their reason.
5. Commit the deletions in one commit, `Prune finished feature records: <features>`, staging only those `<intents>/` paths. Don't push.
