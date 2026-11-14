---
paths:
  - "src/routes/**"
  - "src/schemas/**"
  - "backend/routes/**"
  - "backend/schemas/**"
---
# Node API (Hono): contract

The OpenAPI file the app generates is the only thing clients know about the backend.

- Every business endpoint is a `createRoute` from `@hono/zod-openapi`, with schemas for params, query, body and
  each response status, registered with `app.openapi(route, handler)`.
- Request and response schemas are plain Zod in `schemas/`; web forms reuse them.
- The `gen:api` script writes `contract/v<N>/openapi.yaml` from the app's OpenAPI document, and the file is
  committed. Changing a route or schema reruns it in the same change; CI reruns it and fails on a difference.
- One `Error` schema and one pagination shape, `{ items, nextCursor }`, are reused by every endpoint.
- Each client generates its types from that file. No client imports backend code: no tRPC, no Hono RPC client.
- A breaking change opens `/api/v2` and `contract/v2/`; `v1` is never edited in place.
