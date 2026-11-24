# Architecture decision records

Decisions about how the plugin itself is built: what was decided, why, and what it costs. One decision per file, numbered in order, never rewritten after acceptance: a changed decision gets a new ADR that amends or supersedes the old one.

| ADR | Decision | Status |
|---|---|---|
| [0001](0001-project-setup-upgrade-eject.md) | Project setup, upgrade and eject, with a file-ownership model | Accepted, amended by 0002, 0006 and 0007 |
| [0002](0002-record-the-repos-own-commands.md) | Record the repo's own commands instead of a justfile | Accepted |
| [0003](0003-guard-against-over-engineering.md) | Guard against over-engineering and comment noise | Accepted |
| [0004](0004-ui-follows-the-design-system.md) | UI follows the project's design system | Accepted |
| [0005](0005-greenfield-monorepo-layout.md) | Greenfield multi-app repos are one monorepo with a versioned contract | Accepted; extended by 0025 |
| [0006](0006-split-sdlc-docs-from-machinery.md) | Split sdlc documents from the plugin's machinery | Accepted |
| [0007](0007-multi-tool-adapters.md) | One plugin for Claude Code, Codex, Cursor and Antigravity | Accepted |
| [0008](0008-lite-flow-for-low-risk-m.md) | Low-risk M features run the Lite flow by default | Superseded by 0020 |
| [0009](0009-cheaper-pipeline-and-control-contract.md) | A cheaper pipeline, a control contract, and fewer commit reviews | Accepted, amended by 0010; superseded in part by 0020 |
| [0010](0010-four-phases.md) | Four phases instead of eleven stages | Accepted, amended by 0011 and 0014 |
| [0011](0011-track-cost.md) | Fewer agents per track and a bounded Prove | Accepted, amended by 0012, 0013 and 0016; superseded in part by 0020 |
| [0012](0012-enforced-prove-budget.md) | An enforced Prove budget, and M full without QA | Accepted, amended by 0013; superseded in part by 0020 |
| [0013](0013-build-proves-prove-judges.md) | Build proves, Prove judges | Accepted, amended by 0014 and 0015; superseded in part by 0020 |
| [0014](0014-lighter-s-and-a-companion-plugin.md) | A lighter S, and a companion plugin for niche parts | Accepted, amended by 0015; superseded in part by 0020 |
| [0015](0015-prove-only-where-it-pays.md) | Prove only where it pays: none on S and M lite, skippable on M full and L, security review only when security-touched | Accepted, amended by 0016 and 0019; superseded in part by 0020 |
| [0016](0016-cut-l-cost-where-it-bought-nothing.md) | Cut L's cost where it bought nothing: footprint sizing, one Define exchange, one reviewer, no Ship question | Accepted, amended by 0017; superseded in part by 0020 |
| [0017](0017-thin-main-session-and-stage-agents.md) | A thin main session, kept-alive stage agents, one record file | Superseded by 0020 |
| [0018](0018-m-maker-in-the-main-session.md) | On M the main session is the maker; the checker stays a fresh subagent | Superseded by 0020 |
| [0019](0019-model-security-review-only-for-security-touched-work.md) | The model security review runs only for security-touched work; the reviewer SDK installs lazily | Accepted |
| [0020](0020-sdlc-2-slim-process-core.md) | sdlc 2.0: the slim process core (same record at every size, intent before code, reviews recommended after the build) | Accepted |
| [0021](0021-impeccable-for-ui-design.md) | UI design work can go to impeccable (config `design`); sdlc keeps the record, gates and review verdict | Accepted |
| [0022](0022-phases-numbered-one-to-four.md) | The phases are numbered 1 to 4 (was 1, 4, 5, 8); `Process: 3`, a migration renumbers state files | Accepted |
| [0023](0023-two-review-rounds.md) | Review aims for two rounds: one full review, one closing check | Accepted |
| [0024](0024-deploy-targets.md) | Setup records how a project deploys (config `deploy`, a runbook); production is never routine; platform references give Define its checks | Accepted |
| [0025](0025-workbench-for-multi-app-projects.md) | New multi-app projects can get one repo per app inside a workbench repo (beside 0005's monorepo), which holds the contract and one feature record driving a PR per repo | Accepted |
| [0026](0026-stack-blueprints-in-setup.md) | The stack-blueprints knowledge lives in setup: a selection table the agent applies, more stacks, conventions rendered when a feature first touches an area; no separate tool, no resolver code | Accepted |
| [0027](0027-scaffold-lock-merge-at-save.md) | Scaffold's lock and config merge this command's changes at save (no mutex across commands); atomic writes keep mode and links; one inside-the-repo check | Accepted |
| [0028](0028-domain-model-objects-md.md) | An opt-in domain model in `objects.md` (not rspec's `domain.md`), checked by a script in Define's gate and doctor, never a model turn | Accepted |
| [0029](0029-configurable-review-round-cap.md) | The review round cap is config's `review_rounds` (2 to 5); the agent's edit can only lower it; a raise counts from the next feature's Base, or at once when the user types `/sdlc:setup review-rounds <n>` | Accepted |
| [0030](0030-modes-and-skips.md) | `mode` full or advisory (advisory: skills and agents as aids, every hook silent but a workbench's read-only guard); in full mode `skip` may list security-review, code-review, ui-review, pr; a relaxing change is a trust-anchor notice | Accepted |
| [0031](0031-approval-policy.md) | `approval` high-risk (default), ml (every M and L) or always (S too): `state.py advance 2` refuses until the user's `Approve plan` answer or typed `approve <feature>` is recorded; a move to fewer stops is a trust-anchor notice | Accepted |
| [0032](0032-opt-in-guards.md) | Opt-in `guards` in config (`s_tests`: S locks its tests at the red step, as M and L do); turning one off is a trust-anchor notice | Accepted |

New ADR: copy the shape of an existing one (Status, Context, Decision, Consequences), take the next number, and add a row here.
