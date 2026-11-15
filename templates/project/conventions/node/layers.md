---
paths:
  - "src/**"
  - "backend/**"
---
# Node API (Hono): layers

- Three layers, one way: `routes` call `services`, `services` call `repositories`. Only `routes` and `middleware`
  import Hono.
- A route validates the input, builds the context (the user, and the tenant when the product is multi-tenant) and
  calls one service. Business logic lives in `services/`.
- A service takes that context first and validated input second, never Hono's `Context`, so a job or a script can
  call it. It checks authorization itself, not only in the route.
- Errors: services throw an `AppError` with a code; one `app.onError` handler maps codes to HTTP statuses and writes
  `{ "error": { "code", "message", "requestId" } }`. An unexpected error answers 500 with a generic message; the
  detail goes to the log only.
- Lists are paginated: `limit` (default 20, at most 100) and an opaque `cursor`, answering `{ items, nextCursor }`.
- Paths: business endpoints under `/api/v1/*`, liveness at `/api/health`. A breaking change opens `/api/v2`; `v1`
  is never edited in place.
- Every app uses `secureHeaders` (`hono/secure-headers`), `bodyLimit` (`hono/body-limit`, 1 MB unless a route says
  otherwise) and `requestId` (`hono/request-id`). None is turned off to fix a symptom. Cookie-authenticated routes
  also use `csrf` (`hono/csrf`), which checks only form posts: JSON endpoints accept `application/json` bodies only.
- Configuration: one `config.ts` parses the environment with Zod at startup and fails on a missing or malformed
  value; no other file reads `process.env`.
- Logging: one structured JSON line per request (request id, method, path, status, duration, user id) through one
  logger, never `console.log`.
- Email, storage, error tracking and other vendors sit behind interfaces in `platform/`; services and repositories
  never import a vendor SDK.
- One deployable (mounted in Nuxt or Next.js): only the bridge file imports `backend/`, and it holds no logic.
- Tests: services against a real database, not mocked repositories; routes through `app.request()`.
