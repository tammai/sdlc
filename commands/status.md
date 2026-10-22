---
description: Show the project's sdlc setup state and where each feature in .sdlc/ stands — track, current stage, last gate result, open questions
---

1. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py" status`. One line: setup state and scaffold version vs plugin version. If `setup` is `none` or `in_progress`, suggest `/sdlc:setup`; if `drift` is `behind`, suggest `/sdlc:upgrade` (name the pending migrations); if `plugin_too_old`, say to update the plugin. List seeded files the user has edited (`state: modified`) only if there are any.
2. Read every `.sdlc/*/state.md`. For each, give one line: feature · track · current stage · last gate result. Then list open questions and deviations for active features.

Change nothing.
