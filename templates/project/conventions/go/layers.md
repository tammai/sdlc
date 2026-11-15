---
paths:
  - "**/*.go"
---
# Go API: layers

- One module, three layers, one way: `internal/httpapi` calls `internal/service`, which calls `internal/store`.
  Only `httpapi` knows about HTTP.
- A handler converts the request, calls one service and converts the result. Business logic lives in
  `internal/service`.
- Every exported service method takes `ctx context.Context` and the principal (the user, and the tenant when the
  product is multi-tenant) first. A service never imports `net/http`, Gin or a vendor SDK, and checks authorization
  itself, not only in the handler.
- Errors: services return typed errors carrying a code; one error handler maps codes to HTTP statuses and writes
  `{ "error": { "code", "message", "requestId" } }`. An unexpected error answers 500 with a generic message; the
  detail goes to the log only. Wrap with `fmt.Errorf("…: %w", err)`.
- Lists are paginated: `limit` (default 20, at most 100) and an opaque `cursor`.
- Paths: business endpoints under `/api/v1/*`, liveness at `/api/health`.
- Server: `http.Server` sets `ReadTimeout`, `WriteTimeout` and `IdleTimeout`; request bodies are capped with
  `http.MaxBytesReader` (1 MB unless a route says otherwise); `SIGTERM` shuts down gracefully.
- Concurrency: every goroutine has an owner, a context and a way to stop; none outlives its request unless a
  supervised worker owns it.
- Configuration: `internal/config` reads the environment once at startup and exits on a missing or malformed
  value; no other package reads it.
- Logging: one `log/slog` line per request (request id, method, path, status, duration, user id).
- Email, storage, error tracking and other vendors sit behind interfaces in `internal/platform`.
- Tests: table-driven; services against a real database, not a mocked store; handlers through `httptest`.
