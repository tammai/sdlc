---
paths:
{{config.areas.source|yaml_list}}
---
<!-- Managed by the sdlc plugin v{{plugin_version}}; regenerated on upgrade. Change paths via "areas.source" in .sdlc/config.json. -->
# Code style (sdlc policy)

Comments
- Comment only the *why* the code can't show: a constraint, a non-obvious reason, a workaround with its cause.
- Never narrate or restate code ("Step 1", "Now we…", "This function…", "Loop over the items").
- Never reference the task, PR, ticket, conversation or change history ("added for X", "now uses Y", "fixed bug"). That belongs in git.
- Doc comments only on exported API, one line by default; add params/returns only when the contract isn't obvious from names and types.
- Match the comment density of the surrounding file.

Scope
- Write the smallest change that meets the acceptance criteria; edit existing code before adding new code.
- No abstraction with a single implementation, no options/params/config the spec didn't ask for, no handling of cases that can't happen.
- No new files, layers, dependencies or public exports the plan doesn't name. If you think one is needed, say so instead of adding it.
- Follow the patterns already in the codebase; don't restructure code outside the task.
