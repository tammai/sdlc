# Preferred stacks

Greenfield setup proposes from these: one app (`greenfield.md`) or each app of a workbench (`workbench.md`). They are
the project owner's defaults, not rules: the user still approves every proposal, a stack not listed here falls back
to its ecosystem's mainstream choice, and an existing package is never regenerated. Propose a database or a deploy
target only when the first feature needs one; otherwise name it as "later" in one line. Each stack lists its
pieces, its generator, its `stack` value for `.sdlc/config.json` (it picks the CI toolchain) and its five
commands (`null`: the step doesn't apply or the user declined the tool). Sign-in is not part of any stack: it waits
for the feature that needs it.

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
- **API client** (consuming a contract): `openapi-typescript` from `../contract/v<N>/openapi.yaml` as `generate:api`,
  calls through `openapi-fetch` (`import createClient from "openapi-fetch"`).
- **One deployable** (Choosing a stack): the Node section's Hono app lives in `backend/`, and one bridge file,
  `server/api/[...].ts`, mounts it: `export default defineEventHandler((event) => app.fetch(toWebRequest(event)))`.
  Nothing else in the Nuxt app imports `backend/`, and the bridge holds no logic, so the API can split out later.
  The build is then `pnpm nuxi build` (a server), not `generate`: with `ssr: false`, server routes run only under
  `build`. `toWebRequest` is Nuxt 4's h3 v1; Nuxt 5 (h3 v2) passes `event.req` instead (verify on upgrade).
- **Config `stack`:** `typescript`.

| Step | Command |
|---|---|
| `install` | `pnpm install --frozen-lockfile` |
| `test` | `pnpm vitest run` |
| `lint` | `pnpm lint` when the user chose `@nuxt/eslint`, else `null` |
| `typecheck` | `pnpm nuxi typecheck` (needs `vue-tsc`) |
| `build` | `pnpm nuxi generate` (static SPA output); `pnpm nuxi build` for one deployable |

## Vue (web, SPA without Nuxt)

- **Pieces:** Vue 3 with Vite and TypeScript, Vue Router, Pinia for client state, Pinia Colada for server state, Nuxt
  UI on Tailwind CSS through its Vite plugin (the same components as the Nuxt section), Zod for every boundary.
  Tests: Vitest with Vue Test Utils. A Vite SPA has no server, so it is always a client of a standalone API.
- **Generator:** `pnpm create vue@latest <name>` (TypeScript, Vue Router, Pinia, Vitest; ESLint if the user wants a
  linter), then `pnpm add @nuxt/ui tailwindcss @pinia/colada zod`: `ui()` from `@nuxt/ui/vite` in
  `vite.config.ts`, `app.use(ui)` from `@nuxt/ui/vue-plugin` in `main.ts`, `@import "tailwindcss"; @import
  "@nuxt/ui";` in the main CSS, and the app wrapped in `<UApp>`.
- **API client:** `openapi-typescript` and `openapi-fetch`, as for Nuxt.
- **Config `stack`:** `typescript`.

| Step | Command |
|---|---|
| `install` | `pnpm install --frozen-lockfile` |
| `test` | `pnpm vitest run` |
| `lint` | the lint script create-vue writes when the user chose ESLint, else `null` |
| `typecheck` | `pnpm type-check` (`vue-tsc --build`) |
| `build` | `pnpm build` (runs `type-check` too) |

## React (web, SPA)

- **Pieces:** React with Vite (TypeScript), shadcn/ui on Tailwind for components, Zustand for client state (Pinia's
  counterpart), TanStack Query for server state (Pinia Colada's), React Router for routes (Nuxt's file router's),
  Zod for every boundary. Tests: Vitest with Testing Library.
- **Generator:** `pnpm create vite@latest <name> --template react-ts`, then `pnpm dlx shadcn@latest init` and
  `pnpm add zustand @tanstack/react-query react-router zod`.
- **API client:** `openapi-typescript` as `generate:api`, as for Nuxt.
- **Config `stack`:** `typescript`.

| Step | Command |
|---|---|
| `install` | `pnpm install --frozen-lockfile` |
| `test` | `pnpm vitest run` |
| `lint` | `pnpm lint` (the Vite template ships ESLint; `null` if the user removes it) |
| `typecheck` | `pnpm exec tsc -b --noEmit` |
| `build` | `pnpm build` |

## Next.js (web)

- **Pieces:** Next.js with the App Router and TypeScript, shadcn/ui on Tailwind, TanStack Query for server state,
  Zustand for client state, Zod for every boundary. Screens that read or change data are client components using
  query hooks; server actions and route handlers hold no business logic. Tests: Vitest with Testing Library
  (Next.js's Vitest guide; not in the generator's defaults).
- **Generator:** `pnpm create next-app@latest <name>` (TypeScript, App Router, Tailwind; ESLint, Biome or no
  linter), then `pnpm dlx shadcn@latest init`, `pnpm add @tanstack/react-query zustand zod` and `pnpm add -D vitest
  @vitejs/plugin-react jsdom @testing-library/react @testing-library/dom vite-tsconfig-paths`.
- **API client:** `openapi-typescript` and `openapi-fetch`, as for Nuxt.
- **One deployable** (Choosing a stack): the Node section's Hono app (`new Hono().basePath("/api")`) lives in
  `backend/`, and one bridge file, `app/api/[[...route]]/route.ts`, mounts it: `import { handle } from
  "@hono/vercel"`, then `export const GET = handle(app)` and the same for `POST`, `PUT`, `PATCH` and `DELETE`
  (`hono/vercel` inside `hono` is deprecated). Nothing else imports `backend/`, so the API can split out later.
- **Config `stack`:** `typescript`.

| Step | Command |
|---|---|
| `install` | `pnpm install --frozen-lockfile` |
| `test` | `pnpm vitest run` |
| `lint` | `pnpm lint` (`eslint`; `next lint` is gone) when the user chose ESLint, else `null` |
| `typecheck` | `pnpm exec tsc --noEmit` |
| `build` | `pnpm build` |

## Flutter (mobile, iOS and Android)

- **Pieces:** Flutter with Riverpod (`flutter_riverpod`) for state, `go_router` for routes, `dio` for HTTP.
  Tests: `flutter test`.
- **Generator:** `flutter create <name>`, then `flutter pub add flutter_riverpod go_router dio`.
- **API client:** OpenAPI Generator's `dart-dio` generator from `../contract/v<N>/openapi.yaml` (default
  serialization `built_value`), committed like other generated code.
- **Config `stack`:** `flutter` (not `dart`: CI then installs Flutter, not the bare Dart SDK).

| Step | Command |
|---|---|
| `install` | `flutter pub get` |
| `test` | `flutter test` |
| `lint` | `flutter analyze` |
| `typecheck` | `null` (`flutter analyze` checks types) |
| `build` | `null` (a release build needs signing; `flutter build apk --debug` if the user wants one) |

## iOS (mobile, native)

- **Pieces:** Swift with SwiftUI. Builds and tests need macOS with Xcode (the warning in Choosing a stack).
- **Generator:** Xcode: a new App project with the SwiftUI interface; there is no command-line generator.
- **API client:** Swift OpenAPI Generator (`apple/swift-openapi-generator`, a SwiftPM build plugin) with
  `swift-openapi-runtime` and the `swift-openapi-urlsession` transport; `openapi.yaml` and
  `openapi-generator-config.yaml` sit in the target's source folder.
- **Config `stack`:** `swift`. The generated CI then runs on a macOS runner with the latest stable Xcode.

| Step | Command |
|---|---|
| `install` | `xcodebuild -resolvePackageDependencies` |
| `test` | `xcodebuild test -scheme <App> -destination 'platform=iOS Simulator,name=<device>'` (a device the runner image has: `xcrun simctl list devices available`) |
| `lint` | `null` unless the user chose SwiftLint |
| `typecheck` | `null` (the build compiles) |
| `build` | `xcodebuild build -scheme <App> -destination 'generic/platform=iOS Simulator'` |

## Android (mobile, native)

- **Pieces:** Kotlin with Jetpack Compose, Hilt for dependency injection (plugin `com.google.dagger.hilt.android`,
  compiler through KSP), OkHttp with Kotlin serialization for HTTP. Needs JDK 17 or later.
- **Generator:** Android Studio: a new Empty Activity project (Compose); there is no command-line generator.
- **API client:** OpenAPI Generator's `kotlin` generator with `library=jvm-okhttp4` and
  `serializationLibrary=kotlinx_serialization`.
- **Config `stack`:** `kotlin` (CI sets up Java; GitHub's Ubuntu runners have the Android SDK).

| Step | Command |
|---|---|
| `install` | `null` (Gradle fetches dependencies on the first task) |
| `test` | `./gradlew testDebugUnitTest` |
| `lint` | `./gradlew lintDebug` |
| `typecheck` | `null` (the build compiles) |
| `build` | `./gradlew assembleDebug` |

## Node (API)

- **Pieces:** Hono with Zod validation, PostgreSQL through Drizzle ORM (`drizzle-orm`,
  `drizzle-kit` for migrations). Deploy, when the first feature needs it: Google Cloud Run + Cloud SQL (driver
  `postgres`), or Cloudflare Workers + Neon (driver `@neondatabase/serverless`, Hono's `cloudflare-workers`
  template). Tests: Vitest.
- **Generator:** `pnpm create hono@latest <name>` (template `nodejs` for Cloud Run, `cloudflare-workers` for Workers),
  then `pnpm add zod drizzle-orm` plus the validator below, and `pnpm add -D drizzle-kit vitest`.
- **Validation:** `@hono/zod-openapi` when the API has a consumer and a contract (a web or mobile client, or an
  outside caller): routes are `createRoute` definitions registered with `app.openapi(route, handler)` on an
  `OpenAPIHono` app, `z` is imported from `@hono/zod-openapi`, and `app.doc()` serves the spec the contract file is
  written from. Otherwise (no consumer, no contract) `@hono/zod-validator`: `zValidator("json", schema)` on each
  route. Both take Zod 4.
- **Contract:** the provider; the spec `@hono/zod-openapi` generates is written to `contract/v<N>/openapi.yaml`.
- **One deployable:** the same app, mounted in Nuxt or Next.js through their bridge file (those sections); tests
  call it with `app.request()`, not through the framework.
- **Config `stack`:** `typescript`.

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
- **Config `stack`:** `go`.

| Step | Command |
|---|---|
| `install` | `go mod download` |
| `test` | `go test ./...` |
| `lint` | `go vet ./...` |
| `typecheck` | `null` (the build compiles) |
| `build` | `go build ./...` |

## FastAPI (API, Python)

- **Pieces:** FastAPI with Pydantic, managed by `uv`; PostgreSQL through SQLAlchemy 2 async (`sqlalchemy[asyncio]`,
  `create_async_engine`, driver `asyncpg`), Alembic for migrations (`alembic init -t async migrations`). Tests:
  pytest. Lint: Ruff. Types: Pyright.
- **Generator:** `uv init --app <name>`, then `uv add "fastapi[standard]" "sqlalchemy[asyncio]" asyncpg alembic`
  and `uv add --dev pytest ruff pyright`.
- **Contract:** the provider; `app.openapi()` returns the spec, written to `contract/v<N>/openapi.yaml` by a small
  script so the clients generate from it.
- **Config `stack`:** `python`.

| Step | Command |
|---|---|
| `install` | `uv sync --locked` |
| `test` | `uv run pytest` |
| `lint` | `uv run ruff check .` |
| `typecheck` | `uv run pyright` |
| `build` | `null` (no build step; the deploy builds an image when the first feature needs one) |
