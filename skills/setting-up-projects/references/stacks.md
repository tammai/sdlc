# Preferred stacks

Greenfield setup proposes from these: one app (`greenfield.md`) or each app of a workbench (`workbench.md`). They are
the project owner's defaults, not rules: the user still approves every proposal, a stack not listed here falls back
to its ecosystem's mainstream choice, and an existing package is never regenerated. Propose a database or a deploy
target only when the first feature needs one; otherwise name it as "later" in one line. Each stack lists its
pieces, its generator and its five commands (`null`: the step doesn't apply or the user declined the tool).

Versions: take the generator's current release; don't pin older majors from memory.

## Choosing a stack

Apply the rows in order, from the interview's answers (`greenfield.md`); in each block the first row that matches
wins. Show the user each pick with its reason, plus any warning below that applies, in the proposal. Then wait for
approval. A pick the user overrides stands, and the rows after it are applied again.

| Choice | Pick | When | Reason to give |
|---|---|---|---|
| Web app | the one the user names (Nuxt, Vue, React, Next.js) or none | they name one, or say there is no web app | requested |
| | Nuxt | no preference | the default web frontend |
| Mobile app | the one the user names: Flutter, native iOS and Android, iOS only, Android only | they ask for a mobile app | requested; Flutter covers both platforms from one codebase |
| | none | otherwise | no mobile app was asked for |
| Backend language | the one the user names: TypeScript, Go or Python | the user names one | requested |
| | Go | the heaviest workload is CPU-heavy or realtime, or the scale is high load | real parallelism, low memory, stable long-running processes |
| | TypeScript (Node section) | otherwise | CRUD-shaped work at this scale ships fastest with one language across the stack |
| Shape | one deployable: the TypeScript API mounted in the Nuxt or Next.js app through one bridge file | one web client in Nuxt or Next.js, a TypeScript backend, no mobile app, nothing outside the product calls the API, internal or small scale, mostly CRUD | one codebase and one deploy is the cheapest to run; the bridge file is the only coupling, so the API can split out later |
| | a standalone API with its clients | otherwise | more than one client, a backend outside the web framework, or a scale or workload that needs the API to deploy on its own |

A standalone API with one or more clients is two or more apps: ask the layout (`greenfield.md`), then follow
`monorepo.md` or `workbench.md`. One deployable, or an API with no client, is one app: `greenfield.md` as is. The
database, sign-in and tenancy aren't chosen here: they wait for the first feature that needs them. The deploy
target is setup's `deploy` step.

### Warnings

Say each one that applies, in the proposal, before approval:

- **TypeScript asked for heavy work.** TypeScript was named for CPU-heavy or realtime work or high load; without
  that preference the rows pick Go. Confirm the language.
- **Python asked for heavy work.** CPU-bound work blocks the event loop and must move to worker processes; Go
  handles it in-process. Confirm the language.
- **Go for a small CRUD product.** An internal or small product doing CRUD or background jobs ships the same thing
  in TypeScript with less code. Confirm Go is wanted.
- **No web or mobile client.** Only the API gets built. Confirm that's intended.
- **Two native apps.** Native iOS and Android are two codebases to build and keep in step; Flutter covers both from
  one. Confirm native is needed.
- **iOS needs macOS.** iOS builds and tests need macOS with Xcode, locally and in CI (a macOS runner). Confirm one
  is available.
- **Cloudflare Workers with background jobs.** Workers have no long-running process: background work must fit Cron
  Triggers, Queues or Workflows, each with its own CPU and duration limits (verify), or the deploy target should
  change.
- **Vercel with a Go or Python API.** Vercel hosts the web app; the Go or Python API goes on a container host (Cloud
  Run, say) behind a rewrite.
- **Vercel's free plan.** Hobby is for personal, non-commercial use: a commercial product needs a paid plan (verify).
- **One VPS.** The team owns operating system patching, backups, restore drills and uptime. Confirm someone has
  time for that.

## Nuxt (web, SPA)

- **Pieces:** Nuxt in SPA mode (`ssr: false` in `nuxt.config.ts`), Nuxt UI (`@nuxt/ui`), Pinia (`@pinia/nuxt`) for
  client state, Pinia Colada (`@pinia/colada`, `@pinia/colada-nuxt`) for server state and caching, Zod for every
  boundary (forms, API responses). Tests: Vitest with `@nuxt/test-utils`.
- **Generator:** `pnpm create nuxt@latest <name>`, then `pnpm add @nuxt/ui @pinia/nuxt pinia @pinia/colada
  @pinia/colada-nuxt zod` and the modules in `nuxt.config.ts`.
- **API client** (consuming a contract): `openapi-typescript` from `../contract/v<N>/openapi.yaml` as `generate:api`.

| Step | Command |
|---|---|
| `install` | `pnpm install --frozen-lockfile` |
| `test` | `pnpm vitest run` |
| `lint` | `pnpm lint` when the user chose `@nuxt/eslint`, else `null` |
| `typecheck` | `pnpm nuxi typecheck` (needs `vue-tsc`) |
| `build` | `pnpm nuxi generate` (static SPA output) |

## React (web, SPA)

- **Pieces:** React with Vite (TypeScript), shadcn/ui on Tailwind for components, Zustand for client state (Pinia's
  counterpart), TanStack Query for server state (Pinia Colada's), React Router for routes (Nuxt's file router's),
  Zod for every boundary. Tests: Vitest with Testing Library.
- **Generator:** `pnpm create vite@latest <name> --template react-ts`, then `pnpm dlx shadcn@latest init` and
  `pnpm add zustand @tanstack/react-query react-router zod`.
- **API client:** `openapi-typescript` as `generate:api`, as for Nuxt.

| Step | Command |
|---|---|
| `install` | `pnpm install --frozen-lockfile` |
| `test` | `pnpm vitest run` |
| `lint` | `pnpm lint` (the Vite template ships ESLint; `null` if the user removes it) |
| `typecheck` | `pnpm exec tsc -b --noEmit` |
| `build` | `pnpm build` |

## Node (API)

- **Pieces:** Hono with Zod validation (`@hono/zod-validator`), PostgreSQL through Drizzle ORM (`drizzle-orm`,
  `drizzle-kit` for migrations). Deploy, when the first feature needs it: Google Cloud Run + Cloud SQL (driver
  `postgres`), or Cloudflare Workers + Neon (driver `@neondatabase/serverless`, Hono's `cloudflare-workers`
  template). Tests: Vitest.
- **Generator:** `pnpm create hono@latest <name>` (template `nodejs` for Cloud Run, `cloudflare-workers` for Workers),
  then `pnpm add zod @hono/zod-validator drizzle-orm` and `pnpm add -D drizzle-kit vitest`.
- **Contract:** the provider; keep routes and `contract/v<N>/openapi.yaml` in step (a test that checks each route
  against the spec, or `@hono/zod-openapi` generating it).

| Step | Command |
|---|---|
| `install` | `pnpm install --frozen-lockfile` |
| `test` | `pnpm vitest run` |
| `lint` | `null` unless the user chose a linter |
| `typecheck` | `pnpm exec tsc --noEmit` |
| `build` | `pnpm build` (`tsc` for Cloud Run; `wrangler deploy --dry-run` for Workers) |

## Go (API)

- **Pieces:** Gin for HTTP, oapi-codegen generating the server interface and types from the contract, PostgreSQL
  through pgx/v5 with sqlc generating typed queries, golang-migrate for migrations. Deploy, when the first feature
  needs it: Google Cloud Run + Cloud SQL.
- **Generator:** `go mod init <module>`, then `go get github.com/gin-gonic/gin github.com/jackc/pgx/v5`, the tools
  as `go get -tool github.com/oapi-codegen/oapi-codegen/v2/cmd/oapi-codegen github.com/sqlc-dev/sqlc/cmd/sqlc`
  (Go 1.24+), and golang-migrate's CLI or library.
- **Generated code:** `go generate ./...` runs oapi-codegen and sqlc; commit their output (Go's convention) so
  `go build` needs no tools.

| Step | Command |
|---|---|
| `install` | `go mod download` |
| `test` | `go test ./...` |
| `lint` | `go vet ./...` |
| `typecheck` | `null` (the build compiles) |
| `build` | `go build ./...` |
