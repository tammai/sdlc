# Project setup

Before the first feature, `/sdlc:setup` prepares the repo once; `/sdlc:start` offers it when a repo isn't set up. See [sdlc_setup_phase.svg](../diagrams/sdlc_setup_phase.svg).

**The project's commands.** Setup records the repo's own `install`, `test`, `lint`, `typecheck` and `build` commands in `.sdlc/config.json`, exactly as the team runs them (`pnpm test`, `go test ./...`, `make lint`, …); a step the repo doesn't have is `null`. Everything that runs them reads them from there, so nothing in the plugin is stack-specific. A monorepo lists `packages`, each with a path, a stack and its own commands, run from its directory; a polyglot repo is several packages with different stacks.

**It adds no tooling you didn't ask for.** Setup never changes the product's manifest or dependencies: no new fields (`bin`, `engines`, `packageManager`, scripts), no new linter, formatter or devDependency, and no tool installed without asking.

- **Greenfield** (no source yet): a short stack interview, then a proposal you approve. The ecosystem's own generator builds the skeleton, plus the test runner and one passing smoke test. A linter, toolchain pinning and extra manifest fields are separate choices in the proposal, off unless you say yes.
- **Brownfield** (existing code): the commands the repo already uses, shown to you before they're written; a **baseline** of what already fails; an audit (conventions, git-history gotchas, decisions, area rules) drafted by explorer agents and written only as you approve each batch; existing AI configs (long CLAUDE.md, AGENTS.md, Cursor rules, ADRs) migrated into the three knowledge tiers, one diff per source.
- **Common steps, both modes:** policy rules (`.claude/rules/sdlc*.md`); hookify guardrails; sdlc lint snippets, only for a linter the project already has; a permission allowlist for the project's commands; sdlc and its companion plugins turned on, asked where: `.claude/settings.local.json`, this machine's file, never committed, or the committed `.claude/settings.json`, so teammates get them too (cloud sessions don't: see [Cloud sessions](Cloud-sessions.md)) (the companion plugins `sdlc-extras` and `sdlc-stepper` are on by default; setup lists them in one line, and the companion skill Cloudflare's `security-audit` with its install command when it isn't installed, which sdlc never runs for you; a conflicting plugin such as superpowers is turned off for this repo only, with a warning, and spec-kit's files are reported, with removal asked); with your approval, a context diet (`/sdlc:context-diet`) for this project; a CI workflow from the recorded commands (asked first if the repo already has CI); the sdlc block in `AGENTS.md` when another agent (Codex, Cursor, Antigravity) uses the repo; `.gitignore` entries; a product doc (PRD: an existing one used as is, else drafted from a short interview or from the code with every guess marked "inferred, confirm", approved before it's written to `docs/sdlc/prd.md`); a constitution (with the default Simplicity principle); a design system (projects with UI); and the knowledge folder. The steps that write `.claude/` run only under Claude Code.

Setup runs on an `sdlc/setup` branch with one commit per step, resumes where it stopped, and ends by merging the branch locally, without asking; nothing is pushed.

**Who owns which file.** Everything the plugin puts in a repo is tracked in `.sdlc/scaffold.lock.json` with a class that decides what an upgrade may do:

| Class | Examples | On upgrade |
|---|---|---|
| Generated | `.claude/rules/sdlc*.md` | regenerated |
| Seeded | `.claude/hookify/sdlc-*.md`, `.github/workflows/sdlc-verify.yml`, `sdlc-invariants.yml`, `.sdlc/ci/invariants.py`, `.sdlc/lint/*` | replaced only if you haven't edited it; otherwise you choose: merge, skip, or keep yours for good |
| Keyed merge | allowlist in `.claude/settings.json`, plugin-enablement keys in `.claude/settings.local.json` (or `.claude/settings.json` when the team's), `.gitignore` lines, the `<!-- sdlc:begin -->` block in `AGENTS.md` | only the entries the plugin added; your text around the block is never touched |
| Yours | the commands in `.sdlc/config.json`, `CLAUDE.md`, PRD, constitution, design system, `knowledge/`, baseline, your own rules | changed only by migrations you approve |

Files named `sdlc-*` belong to the plugin; everything else is yours.

**Upgrades.** When the plugin is newer than the repo's scaffold, `/sdlc:start` and `/sdlc:status` suggest `/sdlc:upgrade`, which never blocks your work. It runs on its own branch: regenerate, replace untouched files, walk you through edited ones, then apply versioned migrations one diff at a time (declined ones are asked again only with `--revisit`). The repo pins a minimum plugin version, so teammates on an older plugin get a warning. `/sdlc:eject` removes what the plugin owns and keeps your work.

## Setup with impeccable

A project with UI can hand its design work to the [impeccable](https://github.com/pbakaus/impeccable) skill, while sdlc keeps the record, the gates and the review verdict ([ADR 0021](../adr/0021-impeccable-for-ui-design.md)). The choice is made in setup's `design-system` step and recorded as `design` in `.sdlc/config.json` (`builtin` or `impeccable`; no key means `builtin`).

```
/sdlc:setup
│
├─ detect … gitignore            (unchanged: commands, CI, rules, guardrails …)
│    └─ guardrails renders all sdlc-* guardrails, incl. sdlc-ui-hardcoded-values
│       (the mode isn't known yet)
│
├─ prd                            HARD STOP: approve the PRD
├─ constitution                   HARD STOP: approve it
│
├─ design-system                  (only if the project has UI)
│   ├─ 1. Recommend a mode from the PRD           HARD STOP: you choose,
│   │      impeccable ← user-facing, no design system yet    every time
│   │      builtin    ← internal tool on a stock library, a design team's
│   │                   system, or offline / no third-party calls
│   │      + where impeccable stands here: missing, disabled or enabled
│   │      + names impeccable.style's network call and the telemetry opt-outs
│   ├─ 2. scaffold.py design impeccable
│   │      ├─ records "design": "impeccable" (your reason goes in the commit)
│   │      └─ removes sdlc-ui-hardcoded-values once impeccable's detector
│   │         hook runs here (unchanged → deleted; edited → asks first)
│   ├─ 3. Missing → prints the install command, records builtin;
│   │      /sdlc:setup design reruns the step once it is (sdlc never installs it)
│   │   Disabled → asks to turn it on for this repo (--enable, local file);
│   │      it loads next session, so the step stays pending: restart, then
│   │      /sdlc:setup resumes it
│   ├─ 4. /impeccable init, told to read the PRD
│   │      └─ one round of product questions → PRODUCT.md, whose first line
│   │         links to the PRD (the PRD wins where they differ)
│   ├─ 5. Existing styles worth recording → /impeccable document → DESIGN.md
│   │      (a system you must stay on → documented as pinned, restyling
│   │      commands off limits); none yet → DESIGN.md comes later
│   └─ 6. docs/sdlc/design-system.md = a short pointer to DESIGN.md
│
├─ knowledge
└─ finalize                       local merge (no question, no push)
```

What you end up with:

| File | Owner | Holds |
|---|---|---|
| `docs/sdlc/prd.md` | you | the product's source of truth |
| `PRODUCT.md` | impeccable | the design-relevant part, linking back to the PRD |
| `DESIGN.md` | impeccable | the design system, once a visual world exists |
| `docs/sdlc/design-system.md` | you | a pointer to `DESIGN.md` |
| `.sdlc/config.json` | you | `"design": "impeccable"` |
| `.claude/hookify/` | sdlc | every guardrail except `sdlc-ui-hardcoded-values`, whose job impeccable's detector hook does |

Each UI change afterwards:

| Phase | In impeccable mode |
|---|---|
| Define | `/impeccable shape`; you confirm the brief, which is copied into the state file's `## UI mapping` and its copy into the ACs |
| Build | built through impeccable; its detector hook reports after UI edits |
| Review | `sdlc:ui-reviewer` (opus) runs impeccable's `detect` and applies its `audit` checks (read from `reference/audit.md`) as evidence and writes the verdict; a missing `DESIGN.md` is Medium, not High |
| Ship | as usual |

impeccable missing or turned off for the repo when a step runs: the step says so in one line and runs builtin; `/sdlc:doctor` warns. Switch later, or finish turning impeccable on, with `/sdlc:setup design`: it asks the question again on its own branch, and the mode change puts the UI guardrail back or takes it away.
