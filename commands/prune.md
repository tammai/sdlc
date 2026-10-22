---
description: Delete the working files of finished, merged features (plan, reports, review, checklists) and keep their record (spec, design, retro, state). Shows the list and asks before deleting
argument-hint: "[--older-than 45d]"
---

1. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/prune.py" list $ARGUMENTS`. If it prints an `error`, say it and stop.
2. Nothing in `prune`: say so, list the `skipped` features with their reason in one line each, and stop.
3. Show each feature in `prune` with its age and the files that would go. Say that spec, design, retro and state stay, security.md stays on high-risk features, and git history keeps every deleted file. Ask which to prune (all, some, none).
4. For the chosen features run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/prune.py" apply $ARGUMENTS <feature>...`. Report any `refused` entries with their reason.
5. Commit the deletions in one commit, `Prune finished feature records: <features>`, staging only those `.sdlc/<feature>/` paths. Don't push.
