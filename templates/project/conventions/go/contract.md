---
paths:
  - "internal/httpapi/**"
  - "contract/**"
  - "api/**"
---
# Go API: contract

The OpenAPI file is written by hand and is the single source of truth: the server interface and every client's
types are generated from it.

- Order of work: change the spec, regenerate, then implement. A handler's signature is never changed by hand.
- oapi-codegen generates the Gin strict server interface and types into `internal/httpapi`; handlers implement
  that interface.
- `go generate ./...` runs the generators and their output is committed, so `go build` needs no tools. CI reruns
  it and fails on any difference.
- One `Error` schema and one pagination shape, `{ items, nextCursor }`, are reused by every endpoint.
- Each client generates its types from the same file; no client imports backend code.
- A breaking change opens `/api/v2` and `contract/v2/`; `v1` is never edited in place.
