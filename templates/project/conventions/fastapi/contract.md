---
paths:
  - "app/routers/**"
  - "app/schemas/**"
---
# FastAPI: contract

The OpenAPI file exported from the app is the only thing clients know about the backend. It is language-neutral,
so an endpoint can later move to another language without touching the clients.

- Every path operation sets `response_model`, an explicit `operation_id` and the error responses it can return.
  Bodies, queries and params are Pydantic models.
- A small script writes `contract/v<N>/openapi.yaml` from `app.openapi()`, and the file is committed. Changing a
  router or schema reruns it in the same change; CI reruns it and fails on a difference.
- One `Error` model and one pagination shape, `{ items, nextCursor }`, are reused by every endpoint; JSON fields
  are camelCase through one shared base model.
- Each client generates its types from that file; no client imports backend code.
- A breaking change opens `/api/v2` and `contract/v2/`; `v1` is never edited in place.
