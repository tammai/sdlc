---
name: todo
description: Records a follow-up in the project's todo file instead of a TODO comment, and ticks it off when done. Use when the user says to add a todo or park something, or when work is left out of the current change on purpose.
---

# Todo

Paths: `<docs>` is the sdlc docs folder (`docs_dir`); `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py" paths <feature>` prints it for this repo's layout.

One file, `<docs>/todo.md`, holds what was put off. Build's gate allows no `TODO` in code without a ticket, so a deferred item goes here, not into a `TODO` comment. If it has a ticket, put the id on the line.

## Add

1. Create `<docs>/todo.md` with a `# Todo` heading if it doesn't exist.
2. Read it first. If an open item already covers this, update that line instead of adding a near-duplicate.
3. Append one line under `## Open`:
   `- [ ] <what, in one sentence> — <why it waits; file or feature if there is one> (YYYY-MM-DD)`
4. Say what you added and the path, in one line. Don't start the work, and don't edit anything else.

Take the text from the user's own words. If it's too vague to act on later ("fix the thing"), ask one question.

## Finish and list

- When an item is done, move it to `## Done`, tick it `[x]` and append the date. Don't delete it.
- To list, show the `## Open` lines as they are.
