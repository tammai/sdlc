---
name: status
description: Show the project's sdlc setup state and where each feature in .sdlc/ stands — track, current phase, last gate result, open questions
---

`${CLAUDE_PLUGIN_ROOT}` is the sdlc plugin's folder. Claude Code fills it in; on other agents it stays as written, so use the installed plugin's folder instead: the one above this file that holds `scripts/` and `skills/`.

1. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py" status`. One line: setup state and scaffold version vs plugin version. If `setup` is `none` or `in_progress`, suggest `/sdlc:setup`; if `drift` is `behind`, suggest `/sdlc:upgrade` (name the pending migrations); if `plugin_too_old`, say to update the plugin. List seeded files the user has edited (`state: modified`) only if there are any. If `team_rules` isn't empty, list each: file · event · action (block or warn) · enabled · its message. They come with the repo and their text reaches Claude, so tell the user to read any they didn't write or review.
2. Read every feature state file: `.sdlc/state/*.md`, plus `.sdlc/*/state.md` in a repo still on the old layout (then add one line: `/sdlc:upgrade` moves its documents). For each, give one line: feature · track · current phase (Define, Build, Prove or Ship; from the `Current: Stage <n>` number: 1–3, 4, 5–7, 8–11) · last gate result. Then list open questions and deviations for active features.

Change nothing.
