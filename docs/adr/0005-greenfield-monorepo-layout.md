# ADR 0005: Greenfield multi-app repos are one monorepo with a versioned contract

- **Status:** Accepted, 2026-10-23. Builds on [ADR 0002](0002-record-the-repos-own-commands.md).
- **Deciders:** Tâm Mai.

## Context

Greenfield setup asked "several of these (→ monorepo)?" and recorded `packages`, but said nothing about the layout, how apps share an API, or how team size changes the setup. A product with web, api and mobile apps is usually built contract-first: backend publishes the API contract, then backend, web and mobile build against it in parallel and integrate. The teams move at different speeds: web ships continuously, the api serves several versions, mobile releases slowly.

## Decision

- **One monorepo for every team size:** `apps/<name>/`, `packages/<name>/` (always `packages/api-contract/` when one app serves an API another consumes), `docs/` for BA, QA and design artifacts, and `infras/` only if the user asks for it. Every app and package is a `packages` entry with its own commands.
- **The contract is versioned by folder** (`v1/openapi.yaml`, `v2/…`). Merging to `main` publishes a version; a published version takes additions only, and a breaking change is a new folder. CI enforces it with oasdiff (`builtin:contract-check`), when the user accepts it and the contract is OpenAPI.
- **Each app generates its client** from the version it uses, in its own language; no hand-written shared DTO package.
- **Team size is asked, never inferred**, and stored as `project.profile`. `lean` (solo, small team): one CI workflow, no CODEOWNERS. `large` (separate roles): CODEOWNERS from `project.owners`, one path-filtered workflow per package (`builtin:ci:<package>`), per-app tags and release branches, no root test command.
- **`docs/` artifacts are linked, never copied**, from feature work.

### Alternatives considered

| Option | Why not |
|---|---|
| Monorepo plus git subtrees (one repo per app) for large teams | different cadences don't need separate repos: per-app CI, tags and release branches give them inside one repo, without two-way subtree syncs, a subtree that tracks only one branch while the api keeps release branches, or shared code that breaks once an app leaves the repo. Revisit only if a team needs a repo of its own (e.g. access control). |
| Contract published to a package registry | consumers pick a version folder instead of pinning a package; nothing to publish or host |
| `shared/` for shared code | `packages/` is what workspace tools (pnpm, Melos, Turborepo) find by default |
| A standalone skill or a `scaffold.py monorepo` command | a second home for setup rules, or a fixed generator that fights "use the ecosystem's own tool" |

## Consequences

- **Good:** one layout people recognise; a contract change that breaks an app shows in that pull request's CI; each team releases on its own schedule; a solo developer gets the contract safety without team ceremony.
- **Costs:** the per-app workflows are path-filtered, so they can't be required status checks (a PR that doesn't touch an app never runs its workflow); the contract check runs on every PR so it can be; the contract check covers OpenAPI only; a client generator that needs another toolchain (Java) is an extra install.
- **Not covered:** restructuring an existing repo into this layout.
