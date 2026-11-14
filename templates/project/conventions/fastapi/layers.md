---
paths:
  - "app/**"
  - "tests/**"
---
# FastAPI: layers

- Three layers, one way: `app/routers` call `app/services`, which call `app/repositories`. Only routers and the
  auth dependency import FastAPI or Starlette.
- A router converts the request, calls one service and returns its result. Business logic lives in
  `app/services`.
- Every public service method takes the principal (the user, and the tenant when the product is multi-tenant)
  first, then validated input. A service never imports `fastapi`, `starlette` or a vendor SDK, and checks
  authorization itself, not only in the router.
- Pydantic models in `app/schemas/` define every request and response; a database model is never returned from a
  router.
- Errors: services raise an `AppError` with a code; one exception handler maps codes to HTTP statuses and writes
  `{ "error": { "code", "message", "requestId" } }`, and validation errors are reshaped to the same form. An
  unexpected error answers 500 with a generic message; the detail goes to the log only.
- Lists are paginated: `limit` (default 20, at most 100) and an opaque `cursor`.
- Paths: business endpoints under `/api/v1/*`, liveness at `/api/health`.
- Async end to end: blocking I/O goes to a thread pool, CPU-heavy work to a worker process, never the event loop.
- Configuration: `app/config.py` reads settings once with `pydantic-settings` and fails on a missing or malformed
  value; no other module reads the environment.
- Logging: one structured line per request (request id, method, path, status, duration, user id) through
  `logging`.
- Email, storage, error tracking and other vendors sit behind interfaces in `app/platform/`.
- Tests: pytest with an async HTTP client against the app; services against a real database, not a mocked
  repository.
