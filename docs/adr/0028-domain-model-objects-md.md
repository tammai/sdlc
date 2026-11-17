# ADR 0028: An opt-in domain model in `objects.md`, checked by a script, not a model turn

- **Status:** Accepted, 2026-11-17. Records: `.sdlc/2026-11-17-l-domain-objects/change.md`; spec [13](../specs/13-domain-model.md).
- **Deciders:** Tâm Mai.

## Context

Nothing in a set-up repo said what the product's things are, what they're called, which states they move through
and which rules they obey, so each change rediscovered it from the code: two changes could name one thing two ways,
and a must-never-break line lived only in the change that stated it. rspec writes a `<spec>/domain.md` for rebuilds,
but in another format (roles, enumerations, limits, identifiers) and only in spec-backed repos. An earlier attempt to
lint criteria in Define (C1) was removed for its cost: M-low tokens +97%, S +62%, no quality change.

## Decision

- **One project-owned file, `<docs>/objects.md`, opt-in** (`"objects": true` or an in-repo path): objects with UI
  name, code name, relations, states, actions and how they're shown; `DR-nnn` rules; an Avoid list.
- **Not `domain.md`:** rspec owns that name with another format, and both run in a product-rebuild workbench. In a
  spec-backed repo the switch does nothing and the brief points at rspec's file instead, read-only.
- **Checked by a script, never a model turn:** `objects.py check [FEATURE]` in Define's gate call and in doctor. Code
  spans are reserved for declared states, which keeps the file valid input for the vendored `contracts.py --domain`.
- **Who decides:** a new or renamed object and a changed or removed `DR` rule are the owner's call before the build;
  a new state, action or attribute goes ahead and is recorded.
- **In parts:** the file, check, brief, doctor and the Define, Review and Learn wiring first; the UI layer and
  `/sdlc:setup objects` only if a five-change eval shows the switch costs at most +10% tokens on low-risk M over
  3.11.0 and leaves fewer names per object.

## Consequences

- With the key absent nothing changes: no brief section, no doctor row, no check.
- A repo writes the file by hand from the template until setup drafts it.
- The file is read only through the brief and by reviewers, so it adds no always-loaded context; past 200 lines Define
  sees only the first 200, and the check warns.
