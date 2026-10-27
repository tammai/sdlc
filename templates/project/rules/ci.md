---
paths:
{{config.areas.ci|yaml_list}}
---
<!-- Managed by the sdlc plugin v{{plugin_version}}; regenerated on upgrade. Change paths via "areas.ci" in .sdlc/config.json. -->
# CI, build and infrastructure (sdlc policy)

- Changes here need the user's go-ahead before they are committed: they affect everyone and every environment.
- Never weaken a required check (removing a step, adding `continue-on-error`, skipping tests or lint) to get green.
- CI runs the same commands as local work (`commands` in `.sdlc/config.json`). Change a command there, then let `/sdlc:upgrade` regenerate the workflow, rather than editing CI steps so they drift from local runs.
- Pin actions and images to a version; never pass secrets through command-line arguments or logs.
