---
name: doctor
description: Health check for sdlc — machine (git, gh, Python, security reviewer), plugin install, and this repo (setup, version drift, project commands and their tools, rules, hookify rules, knowledge, feature state). Use when something feels off, after installing or upgrading, or before onboarding a teammate.
---

`${CLAUDE_PLUGIN_ROOT}` is the sdlc plugin's folder. Claude Code fills it in; on other agents it stays as written, so use the installed plugin's folder instead: the one above this file that holds `scripts/` and `skills/`.

Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/doctor.py" --format md` and show the table as is.

Then, in a few lines:
- **Failing (❌):** what each one breaks in the workflow, and its fix.
- **Warnings (⚠️):** group them; say which can wait.
- **Fixes:** offer to apply the ones that are safe and local (add a `.gitignore` line, add missing commands to `.sdlc/config.json`, fix a rule's `paths:`, run `/sdlc:upgrade` or `/sdlc:setup`). Apply only what the user picks. Never install tools, change the plugin, or edit files outside this repo without an explicit yes.

Doctor itself changes nothing. If everything is ✅, say so in one line.
