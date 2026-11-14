---
paths:
  - "src/repositories/**"
  - "src/db/**"
  - "backend/repositories/**"
  - "backend/db/**"
---
# Node API (Drizzle): data access

- Only `repositories/` and `db/` import Drizzle; services call repositories.
- Every repository function takes what scopes its rows as a required parameter (the tenant id in a multi-tenant
  product, the owner where rows belong to a user); none reads the scope from a global.
- Queries use Drizzle's builder. Raw SQL only through the `sql` template tag, which binds values; never string
  concatenation.
- A write to more than one table is one transaction: the service opens `db.transaction(async (tx) => …)` and passes
  `tx` to each repository call.
- Select only the columns needed; no query inside a loop (N+1).
- One connection pool per process, created in `db/`; on Workers, the driver the Node section of the stack names.
- Tests run repositories against a real database, not mocks.
