# Architecture decision records

Decisions about how the plugin itself is built: what was decided, why, and what it costs. One decision per file, numbered in order, never rewritten after acceptance: a changed decision gets a new ADR that amends or supersedes the old one.

| ADR | Decision | Status |
|---|---|---|
| [0001](0001-project-setup-upgrade-eject.md) | Project setup, upgrade and eject, with a file-ownership model | Accepted, amended by 0002, 0006 and 0007 |
| [0002](0002-record-the-repos-own-commands.md) | Record the repo's own commands instead of a justfile | Accepted |
| [0003](0003-guard-against-over-engineering.md) | Guard against over-engineering and comment noise | Accepted |
| [0004](0004-ui-follows-the-design-system.md) | UI follows the project's design system | Accepted |
| [0005](0005-greenfield-monorepo-layout.md) | Greenfield multi-app repos are one monorepo with a versioned contract | Accepted |
| [0006](0006-split-sdlc-docs-from-machinery.md) | Split sdlc documents from the plugin's machinery | Accepted |
| [0007](0007-multi-tool-adapters.md) | One plugin for Claude Code, Codex, Cursor and Antigravity | Accepted |
| [0008](0008-lite-flow-for-low-risk-m.md) | Low-risk M features run the Lite flow by default | Accepted, amended by 0009 and 0010 |
| [0009](0009-cheaper-pipeline-and-control-contract.md) | A cheaper pipeline, a control contract, and fewer commit reviews | Accepted, amended by 0010 |
| [0010](0010-four-phases.md) | Four phases instead of eleven stages | Accepted, amended by 0011 and 0014 |
| [0011](0011-track-cost.md) | Fewer agents per track and a bounded Prove | Accepted, amended by 0012, 0013 and 0016 |
| [0012](0012-enforced-prove-budget.md) | An enforced Prove budget, and M full without QA | Accepted, amended by 0013 |
| [0013](0013-build-proves-prove-judges.md) | Build proves, Prove judges | Accepted, amended by 0014 and 0015 |
| [0014](0014-lighter-s-and-a-companion-plugin.md) | A lighter S, and a companion plugin for niche parts | Accepted, amended by 0015 |
| [0015](0015-prove-only-where-it-pays.md) | Prove only where it pays: none on S and M lite, skippable on M full and L, security review only when security-touched | Accepted, amended by 0016 and 0019 |
| [0016](0016-cut-l-cost-where-it-bought-nothing.md) | Cut L's cost where it bought nothing: footprint sizing, one Define exchange, one reviewer, no Ship question | Accepted, amended by 0017 |
| [0017](0017-thin-main-session-and-stage-agents.md) | A thin main session, kept-alive stage agents, one record file | Accepted, amended by 0018 |
| [0018](0018-m-maker-in-the-main-session.md) | On M the main session is the maker; the checker stays a fresh subagent | Accepted |
| [0019](0019-model-security-review-only-for-security-touched-work.md) | The model security review runs only for security-touched work; the reviewer SDK installs lazily | Accepted |
| [0020](0020-sdlc-2-slim-process-core.md) | sdlc 2.0: the slim process core (same record at every size, intent before code, reviews recommended after the build) | Accepted |

New ADR: copy the shape of an existing one (Status, Context, Decision, Consequences), take the next number, and add a row here.
