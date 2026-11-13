# Preferred stacks

Greenfield setup proposes from these: one app (`greenfield.md`) or each app of a workbench (`workbench.md`). They are
the project owner's defaults, not rules: the user still approves every proposal, a stack not listed here falls back
to its ecosystem's mainstream choice, and an existing package is never regenerated. Propose a database or a deploy
target only when the first feature needs one; otherwise name it as "later" in one line. Each stack lists its
pieces, its generator and its five commands (`null`: the step doesn't apply or the user declined the tool).

Versions: take the generator's current release; don't pin older majors from memory.

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
