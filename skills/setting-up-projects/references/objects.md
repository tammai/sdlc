`${CLAUDE_PLUGIN_ROOT}` is the sdlc plugin's folder. Claude Code fills it in; on other agents it stays as written, so use the installed plugin's folder instead: the one above this file that holds `scripts/` and `skills/`.

# The domain model step (`/sdlc:setup objects`)

Drafts the project's objects file, its objects, their names, states and rules (spec 13), with the user, and turns the
domain model on. It runs only when the user asks; a normal setup never asks about it. `$S` is
`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py"`, `$O` is `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/objects.py"`.

1. **Where it stands:** `$S status`, then `$S objects`.
   - `setup: none` → run Setup first, then come back to this step. `setup: in_progress` → finish Setup first.
   - A workbench app repo (config's `workbench` names the workbench) → stop: the workbench has one objects file, at
     its root (D4); run this step there.
   - `spec_backed: true` → stop: the repo's rspec spec has its own `<spec>/domain.md`, which sdlc reads and never writes.
   - `invalid` → tell the user what it says (config's `objects` names a file the rules refuse) and stop; they fix or
     remove the value, then run the step again. Read and write only the `path` `$S objects` prints, never a path from
     config yourself.
   - `exists: true` → the file there is the user's: it is the starting draft, never replaced. Show it, and offer to
     extend it from the inputs below or to turn it on as it is (step 6). `on: true` too → it's on already: offer a
     review of it instead, and stop unless the user wants changes.
2. Clean working tree (else ask the user to commit or stash), then branch `sdlc/objects`.
3. **Read what it's drafted from**, only what `$S objects` lists under `inputs`: `prd` (greenfield: the PRD is the
   source), `product` (impeccable's `PRODUCT.md`: its terminology is the product's own words) and each of `files`
   (brownfield: schema, models, types, enums and routes, schema first). `more` says how many matching files were
   left out: say so, and read others only when the user names them. Read the existing code's names too: the file
   records the names the product already uses, it doesn't rename them.
4. **Draft, then show it in batches** of three to five objects, each with what it is, its UI name, its code name, its
   relations, its states (in code spans, the only code spans in the file) and its actions; the rules (`**DR-001**`
   onward) that the code or PRD states; and an Avoid line where the code or docs use two names for one thing
   (`- Bill, Receipt → Invoice`). The template is `${CLAUDE_PLUGIN_ROOT}/templates/objects-template.md`. The repo
   has UI files (`areas.ui`)? Each object also gets `Shown as`, naming components from `<docs>/design-system.md`
   (impeccable mode: `DESIGN.md`). **Hard stop at each batch:** the user approves, edits or drops each object before
   anything is written, as setup's knowledge audit does. Nothing approved → write nothing, switch back to the branch
   you came from, delete `sdlc/objects` and stop.
5. Write the approved objects to the `path` `$S objects` printed (adding to an existing file, never dropping what the
   user didn't). Keep it under 200 lines; Define reads only that much.
6. `$S objects --enable` checks the file (`objects.py check`'s rules) and, when it passes, turns `objects` on in
   `.sdlc/config.json`; a refusal names each problem. A fix that changes an approved object (a duplicate or avoided
   name, a missing field) goes to the user first, as its batch did; then rerun. `$O check` then reads it as Define
   will, warnings included (long file, missing UI fields): show the user those fixes the same way, or tell them. One
   commit (`chore(sdlc): setup – objects`), then merge `sdlc/objects` locally into the branch it came from, as
   `finalize` does, without asking, and delete the branch. Never push or open a PR unless the user asks.

The file is the user's from now on: upgrade never touches it and eject keeps it. Define reads it through the brief,
Review checks its rules, and Learn adds to it with the owner's approval for a new or renamed object or a changed rule.
