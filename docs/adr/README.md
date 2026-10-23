# Architecture decision records

Decisions about how the plugin itself is built: what was decided, why, and what it costs. One decision per file, numbered in order, never rewritten after acceptance: a changed decision gets a new ADR that amends or supersedes the old one.

| ADR | Decision | Status |
|---|---|---|
| [0001](0001-project-setup-upgrade-eject.md) | Project setup, upgrade and eject, with a file-ownership model | Accepted, amended by 0002 |
| [0002](0002-record-the-repos-own-commands.md) | Record the repo's own commands instead of a justfile | Accepted |
| [0003](0003-guard-against-over-engineering.md) | Guard against over-engineering and comment noise | Accepted |
| [0004](0004-ui-follows-the-design-system.md) | UI follows the project's design system | Accepted |
| [0005](0005-greenfield-monorepo-layout.md) | Greenfield multi-app repos are one monorepo with a versioned contract | Accepted |

New ADR: copy the shape of an existing one (Status, Context, Decision, Consequences), take the next number, and add a row here.
