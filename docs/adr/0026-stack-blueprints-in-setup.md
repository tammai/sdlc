# ADR 0026: The stack-blueprints knowledge lives in setup, not in a tool of its own

- **Status:** Accepted, 2026-11-14. Builds on [ADR 0024](0024-deploy-targets.md) (deploy targets and platform
  references) and [ADR 0025](0025-workbench-for-multi-app-projects.md) (the layout question). Record:
  `.sdlc/2026-11-14-l-stack-blueprints/change.md`.
- **Deciders:** Tâm Mai.

## Context

Greenfield setup proposed from four preferred stacks (Nuxt, React, Node, Go) with no rule for choosing between them,
no mobile or Python option, and no guidance for the agent once the code exists. A separate repository,
stack-blueprints 0.3.0, held that knowledge by layer (web, mobile, backend, shape, data, auth, deploy) with selection
rules, warnings, per-stack conventions, deploy notes and a scaling roadmap. As its own tool it was a Node resolver
(`compose.mjs`) that wrote `CLAUDE.md`, a scaffold plan and checklists, and installed sign-in, a database and tenant
columns up front: a second owner of the files setup owns, a Node dependency the plugin doesn't have, and the opposite
of a minimal greenfield.

## Decision

- **The plugin is the only owner.** The blueprint content moves into setup; stack-blueprints isn't shipped. Not
  carried over: `compose.mjs`, `init/PROTOCOL.md`, the generated `CLAUDE.md`, `docs/SCAFFOLD.md`, the two checklists.
  Setup never writes `CLAUDE.md`.
- **Selection is a table the agent applies** (`references/stacks.md`, **Choosing a stack**), as the rest of setup
  works; no resolver code. It picks the web and mobile apps, the backend language and the shape from the interview's
  answers, which gain three questions: whether anything outside the product calls the API, the heaviest workload, and
  the first-year scale. Each pick shows its reason and any warning, and the proposal stays a hard stop.
- **Shape maps onto the existing layouts:** one deployable (a TypeScript API mounted in Nuxt or Next.js) is one app;
  a standalone API with clients is two or more apps, so the layout question (ADR 0025) follows.
- **Nothing for later.** Database, sign-in and tenancy aren't chosen at setup; their conventions wait for the first
  feature that needs them. The deploy target stays setup's `deploy` step; the blueprint's `vps-compose` is the
  existing `docker-compose` target.
- **The Node API** uses `@hono/zod-openapi` when it has a consumer and a contract, `@hono/zod-validator` otherwise.
  Auth libraries are named only in the auth convention, never in `stacks.md`.
- **Stacks added:** Vue without Nuxt, Next.js, Flutter, native iOS, native Android, FastAPI; Nuxt, React, Node and Go
  reconciled with the blueprint entries.
- **Per-stack conventions** (layers, tenant-ready schema, contract, auth, data access, UI) are templates
  `scaffold.py` renders into `.claude/rules/<stack>-<area>.md` (so a web app and an API each get their own) when a feature first touches the area, never at setup. They are
  user-owned (eject keeps them); the lock lists each rendered area with its template and version, so upgrade can
  offer a template change as a diff. Area and stack names come from the plugin's own list; an existing rule file is
  never overwritten.
- **Platform references** for `cloudflare`, `vercel` and `docker-compose` join `gcp-cloud-run`, each with Define
  checks. **Constitution proposals per stack** and a **scaling roadmap** knowledge page complete it.
- **Every library API** that enters the plugin was checked against current documentation; one that couldn't be is
  left out. The blueprint's samples were never executed.

### Alternatives considered

| Option | Why not |
|---|---|
| Ship stack-blueprints as its own tool beside sdlc | two owners of setup's files; a Node dependency; it writes `CLAUDE.md` |
| Port `compose.mjs` to a Python resolver in `scaffold.py` | about ten rules an agent applies reliably from a table; code to maintain for no gain |
| Vendor the catalog JSON and read it from Python | the same resolver, plus a data format to version |
| Install auth, database and tenant columns at setup, as the blueprints did | builds for later; the first feature may not need them |
| Convention rules as `seeded` files | upgrade would replace and eject delete them while unedited: not the team's own |

## Consequences

- **Good:** one setup path with a reasoned stack proposal; mobile and Python covered; conventions arrive when the
  code they govern does.
- **Costs:** the table and sections are prose the agent applies, so a wrong pick is caught at the hard stop, not by
  a test; library facts age and are re-checked when a part touches them.
- **Built in parts:** the selection table first (3.9), then the stack sections, conventions, platform references and
  the constitution and roadmap, on one branch.
