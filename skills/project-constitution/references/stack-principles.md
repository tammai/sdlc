# Principles per stack

Proposals for the constitution's architecture principles, one section per stack (the names `scaffold.py
conventions` uses). Propose **Every stack** and the section of each stack the project uses; the user keeps, rewords
or drops each line. Name the stack from the package's manifest, as Define does (`flow.md`, Conventions on first
touch): in `package.json`, `nuxt` → `nuxt`, else `next` → `nextjs`, else `react` → `react`, else `vue` → `vue`
(the first match wins); `hono` → `node`; `pubspec.yaml` → `flutter`;
`Package.swift` or an `.xcodeproj` → `ios`; `build.gradle.kts` → `android`; `go.mod` → `go`; `fastapi` in
`pyproject.toml`. Config `stack` is the CI toolchain (`typescript` covers four web stacks), so it doesn't say which.

These are boundaries, not how-tos: the how lives in the stack's conventions (`.claude/rules/<stack>-<area>.md`,
rendered when a feature first touches an area). Don't restate the plugin's own rules: secrets and PII
(`sdlc-sensitive.md`), UI tokens and states (`sdlc-ui.md`), migrations (`sdlc-migrations.md`).

## Every stack

- Dependencies MUST be pinned with a lockfile, and a new one MUST be added with a stated reason.
- Generated files (API clients, server stubs, a spec exported from code) MUST NOT be edited by hand; the change that
  changes their source MUST regenerate them.
- An SSR layer, a BFF, a queue, a distributed cache or a new service MUST NOT be added before a measured need
  calls for it, or, when the project has a scaling roadmap (`knowledge/decisions/scaling-roadmap.md`), before its
  trigger there is met. Propose it as an addition to **V. Simplicity**.
- Backends: email, storage, payments, error tracking and other vendors MUST sit behind an interface the business
  code owns; business code MUST NOT import a vendor SDK.

Rationale: the stack stays replaceable piece by piece, and growth happens when a measured need asks for it.

## node (Hono API)

- Business logic MUST live in services. A route validates the input, builds the caller's context, calls one service
  and returns its result.
- Services and repositories MUST NOT import Hono or a vendor SDK, and the backend MUST NOT import from any client app.
- One deployable (mounted in Nuxt or Next.js): the bridge file is the only one that imports the backend, and it holds no logic.

Rationale: services stay callable from a job, a script or a split-out API without a rewrite.

## go (API)

- Business logic MUST live in the service package. A handler converts the request, calls a service and converts
  the result.
- Every exported service method MUST take `context.Context` first and the caller's identity next.
- The service and store packages MUST NOT import `net/http`, the router or a vendor SDK.

Rationale: handlers stay thin and services testable without HTTP.

## fastapi (API, Python)

- Business logic MUST live in services. A router converts the request, calls a service and returns its result.
- Services and repositories MUST NOT import `fastapi`, `starlette` or a vendor SDK.
- Blocking or CPU-bound work MUST NOT run on the event loop.
- Every business endpoint MUST declare its request and response models, so the exported contract is complete.

Rationale: one blocking call stalls every request; the contract is only as good as the models behind it.

## nuxt (web)

- The app MUST read and write data only through the API client typed from the contract.
- Components MUST NOT call the API client; calls live in query composables.

Rationale: one place per query keeps caching, errors and the contract in step.

## vue (web, without Nuxt)

- The app MUST read and write data only through the API client typed from the contract.
- Components MUST NOT call the API client; calls live in query composables.

Rationale: one place per query keeps caching, errors and the contract in step.

## react (web)

- The app MUST read and write data only through the API client typed from the contract.
- Components MUST NOT call the API client; calls live in query hooks.

Rationale: one place per query keeps caching, errors and the contract in step.

## nextjs (web)

- Business data MUST go through the API (`/api/*`). Server actions, route handlers and server components MUST NOT
  read or change it themselves; the one exception is the one-deployable bridge route that mounts the backend.
- Components MUST NOT call the API client; calls live in query hooks.
- A secret MUST NOT be exposed through a `NEXT_PUBLIC_` variable.

Rationale: Next.js offers several ways to reach data; one keeps the backend the only owner of business rules.

## flutter (mobile)

- The app MUST read and write data only through the client generated from the contract, called from providers.
- The app MUST NOT hold a secret: anything shipped in the app is public.

Rationale: widgets stay free of data access, and the contract is the one interface to the backend.

## ios (mobile, native)

- The app MUST read and write data only through the client generated from the contract, called from view models.
- The app MUST NOT hold a secret: anything shipped in the app is public.

Rationale: views stay free of data access, and the contract is the one interface to the backend.

## android (mobile, native)

- The app MUST read and write data only through the client generated from the contract, called from repositories.
- The app MUST NOT hold a secret: anything shipped in the app is public.

Rationale: composables stay free of data access, and the contract is the one interface to the backend.
