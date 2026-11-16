# The living spec (only when `.sdlc/config.json` sets `living_spec`)

The repo keeps what the system does now, one file per capability, in the folder the brief's `living spec` section names (`<docs>/capabilities/` by default). Each file is a purpose line and its requirements (`R-001` onward), each with its test and the change it came from. Nobody edits them by hand: `ship.py` writes them from the change file's `## Capabilities` section, after verify, into Ship's commit. A spec-backed repo has none: its rspec spec is the living spec.

**In Define,** after the acceptance criteria, write `## Capabilities` in `<change>` (M and L must; S may skip it when no capability's behaviour changes). One line each:

- `- add <name>: AC-001 AC-002` — each AC becomes a new requirement of `<name>`. A capability that doesn't exist yet also needs its purpose: `- add <name>: AC-001 — <what it is for>`.
- `- replace <name> R-003: AC-004` — R-003 now says what AC-004 says, with its test; it keeps its id.
- `- remove <name> R-005: <why>` — the behaviour goes away.
- `- retire <name>: <why>` — deletes the whole file; needed when removals would empty it.
- `- none: <why>` — no behaviour a capability describes changed (a refactor, tooling, docs). Never invent a requirement to avoid this line.

**Naming.** Read the brief's capability list first and reuse an existing name; a new one is kebab-case and names a lasting behaviour of the system (`sessions`, `invoice-export`), not this change (`add-timeout`). Open the file of each capability you replace or remove from, to name the right `R-nnn`. Only behaviour a user or another system relies on goes in: an AC about an internal detail gets no line.

**Before Ship,** `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/capabilities.py" check <feature>` says whether the section applies (an unknown name or `R-nnn`, a missing purpose, an emptied capability without `retire`); `ship.py` refuses on the same problems before anything moves. Two branches changing the same requirement conflict in its file at merge: resolve it like any conflict, keeping what the code now does.
