---
name: status
description: Show the project's sdlc setup state and where each feature in .sdlc/ stands — track, current phase, last gate result, open questions
---

`${CLAUDE_PLUGIN_ROOT}` is the sdlc plugin's folder. Claude Code fills it in; on other agents it stays as written, so use the installed plugin's folder instead: the one above this file that holds `scripts/` and `skills/`.

1. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py" status`. One line: setup state and scaffold version vs plugin version. If `setup` is `none` or `in_progress`, suggest `/sdlc:setup`; if `drift` is `behind`, suggest `/sdlc:upgrade` (name the pending migrations); if `plugin_too_old`, say to update the plugin. List seeded files the user has edited (`state: modified`) only if there are any. If `team_rules` isn't empty, list each: file · event · action (block or warn) · enabled · its message. They come with the repo and their text reaches Claude, so tell the user to read any they didn't write or review.
2. Read every feature state file: `.sdlc/state/*.md`, plus `.sdlc/*/state.md` in a repo still on the old layout (then add one line: `/sdlc:upgrade` moves its documents). Runtime files there without a `.md` of the same name (`*.json`, `*.events.jsonl`, `*.commands/`, git-ignored) belong to a feature whose state file is on another branch: name those features in one line as on another branch, and don't count them as features or as a sign the scaffold is out of date. For each state file, give one line: feature · track · current phase (Define, Build, Review or Ship; from the `Current: Stage <n>` number: 1, 2, 3, 4) · last gate result. Then list open questions and deviations for active features.

Change nothing.
