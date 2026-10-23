# Brainstorm: greenfield polyglot monorepo scaffold

Status: draft for approval · 2026-10-23

## Intent and why

When `setting-up-projects` runs greenfield setup on a product that has more than one app (say web, api and mobile), it should produce a **polyglot monorepo** with a fixed, recognisable layout. Today `references/greenfield.md` stops at "several of these (→ monorepo)?" and the `packages` entries in `.sdlc/config.json`. It never says what the layout is, how the apps share an API contract, or how team size changes the setup. This change fills that gap.

The user's real workflow is **contract-first**. Backend owns the API contract and publishes a version (merging it to `main` makes it final). Backend, web and mobile then build against it in parallel and integrate once both sides are done. Each app also has its own release pace: web ships continuously, the api supports several versions at once, and mobile releases slowly.

## Goals

1. Greenfield setup with more than one app proposes this layout:
   - `apps/<name>/`: each app, generated with its ecosystem's own tool (web, api, mobile, …)
   - `packages/<name>/`: shared code, always including `packages/api-contract/` when there's an API and a client
   - `docs/`: artifacts owned by BA, QA and Design (specs, test cases, designs, runbooks)
   - `infras/`: Dockerfiles, deploy playbooks and similar, **only if the user says yes** when asked
2. Every `apps/*` and `packages/*` folder is registered as its own entry in `packages` in `.sdlc/config.json`, with its own commands.
3. The API contract is versioned by folder (`packages/api-contract/v1/`, `v2/`, …). Merging to `main` publishes a version. Each feature picks the version the teams agreed on.
4. A version that's already published accepts non-breaking additions only. A breaking change means a new version folder. CI enforces this by diffing each changed version against `main`.
5. Each app generates its client and types from the contract version it uses, in its own language. There is no hand-written DTO package.
6. Setup asks one question, who will work in the repo, and the answer picks the **lean** or **large** profile:

   | | Lean (solo / small) | Large (separate roles) |
   |---|---|---|
   | Layout, `packages` entries, contract rules, generated clients | yes | yes |
   | `CODEOWNERS` (backend owns `packages/api-contract/`, each team owns its app) | no | yes; setup asks for the team handles |
   | CI per app, triggered by that app's paths | no; one CI | yes |
   | Per-app version tags (`web@x.y.z`) and release branches (`release/api-v1`) | no; one version | yes; documented convention |
   | `docs/` subfolders per role | minimal | yes |

7. `docs/` artifacts are **referenced, never copied**. BA, QA and design produce them in their own workflow and sync them into `docs/`. Feature work in `.sdlc/<feature>/` links to them.

## Non-goals

- **Git subtrees and per-app repos.** We considered them for the separate cadences and dropped them. Per-app CI, tags and release branches inside one monorepo give the same cadences without two-way syncing. Splitting an app into its own repo (for access control, say) would be a separate request later.
- Restructuring an existing (brownfield) repo into this layout.
- Publishing the contract to a package registry.
- Picking the contract format for the user. OpenAPI is the default; other formats get their own check tool when one is needed.
- Infra contents beyond an empty, documented `infras/` folder.

## Anti-goals

- A solo developer ends up with team ceremony (CODEOWNERS, per-app release machinery) they never asked for.
- Specs or test cases duplicated between `docs/` and `.sdlc/`, so they drift apart.
- A published contract version changes in a breaking way under a team building on it.
- Hand-written app skeletons instead of the ecosystem generators (this would break an existing setup rule).

## Constraints

- Work inside the existing setup flow. Files the plugin places go through `scaffold.py render` with the right ownership class (seeded for CODEOWNERS and CI), so upgrade and eject keep working. Never hand-edit the lock.
- The existing hard stops still apply: stack choice, installing tools, adding CI. New hard stops: the infra question, the team-size question and the CODEOWNERS handles.
- Every package's commands must pass on day one (`$S contract` ok, `$S run-commands` all exit 0).
- Windows works: scripts write UTF-8 and the CI OS matrix is respected.
- Tests stay minimal: one test per user-visible behaviour, plus the failure case that matters most.

## Approaches

- **A. A monorepo reference inside `setting-up-projects` (chosen).** Add `references/monorepo.md`, which greenfield's `stack` step routes to when there's more than one app. New files become templates rendered through `scaffold.py`. Reuses all the existing bookkeeping and adds no new trigger. Its limit is that it can't be run outside setup.
- B. A standalone skill called from setup. Only worth it if the flow is reused outside setup. It adds a competing trigger and a second home for setup rules.
- C. A `scaffold.py monorepo` command that writes everything. Predictable, but it fights the "use the ecosystem's generator" rule and goes stale for polyglot stacks.

The user chose **A**.

## Decided

- Layout: `apps/`, `packages/` (not `shared/`, so workspace tools find it), `docs/`, plus `infras/` only if the user opts in.
- No subtrees, for either profile.
- Merging to `main` publishes a contract version. Versions are folders. Additive changes are allowed and breaking changes need a new folder.
- Team size is asked during setup, never guessed.
- `docs/` holds BA/QA/design artifacts and is referenced, not copied. `.sdlc/<feature>/` stays the per-feature workspace. `knowledge/` is unchanged.

## Calls made after the builder check (brainstormer's calls, not the user's)

- **Trigger:** two or more apps means monorepo. `packages/api-contract/` exists when at least one app serves an API and another consumes it. A single app is unchanged, even an API on its own.
- **Profile is stored** in `.sdlc/config.json` as `project.profile: "lean" | "large"`. Large also stores `project.owners` (path → handles). `builtin:ci` and the CODEOWNERS template render from these, so an upgrade regenerates the same shape.
- **Published means the version folder exists on `main`.** CI diffs only those folders against `main`. A new version folder in a PR has nothing to diff against, so it passes. A breaking edit to a published version fails, with no override. This follows the user's rule: published is final, and a breaking change means a new version.
- **The contract check is OpenAPI only.** If the user declines installing oasdiff, or picks a format other than OpenAPI, the job is omitted. The final report says the check is missing, and criterion 5 is recorded as skipped.
- **Client generation** is an app script (`generate:api` or the stack's equivalent) that runs before build and test. Generated code is gitignored. Each stack uses its own native generator where one exists (for example `openapi-typescript` for TS). A generator that needs another toolchain (such as Java) counts as a tool install, so it's a hard stop.
- **Large profile:** there's no root `commands.test`, so per-app CI isn't overridden by a full run. Lean may keep the workspace's root test command.
- **Per-app CI path filters** cover the app's own folder plus `packages/api-contract/**`, so a contract change runs every app's CI.

## Left to the builder

- Exact wording and structure of `references/monorepo.md`, and how `greenfield.md` routes to it.
- Per-app CI. `generate_ci` currently emits one `verify` job covering every package. Large profile needs path-filtered jobs per package, either as a mode of `builtin:ci` or a separate builtin. A contract-check job is needed in both profiles.
- The breaking-change tool for OpenAPI (oasdiff is the obvious candidate), installed only after the user agrees (installing tools is a hard stop).
- Templates: `CODEOWNERS`, `packages/api-contract/README.md` (version rules), `docs/README.md` (role folders, link-don't-copy rule) and `infras/README.md`.
- Workspace manifests per stack (pnpm workspace, Melos, uv workspace, …) follow each ecosystem's convention.
- How `writing-specs` or the spec template points at `docs/` artifacts (a "References" line is enough).
- The stale-docs audit from `CONTRIBUTING.md`, the ADR (this is a setup decision, alongside 0001/0002) and the user-facing spec in `docs/specs/01-setup-upgrade-eject.md`.

## Acceptance criteria (draft, ≤10)

1. Greenfield setup with two or more apps proposes the `apps/` + `packages/` + `docs/` layout and waits for approval.
2. The infra question: yes creates `infras/` and no creates nothing.
3. Every `apps/*` and `packages/*` folder appears in `packages` with its own commands, and `$S contract` returns ok.
4. With an API and a client, `packages/api-contract/v1/` exists, and every app generates its client from it.
5. CI fails a PR that makes a breaking change to a published contract version, and passes one that only adds.
6. Lean profile: no CODEOWNERS and a single CI job.
7. Large profile: CODEOWNERS with the handles the user gave, and CI jobs triggered per app path.
8. `docs/README.md` states the role folders and the link-don't-copy rule.
9. A single-app greenfield setup is unchanged.
