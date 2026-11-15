---
paths:
  - "app/repositories/**"
  - "app/db/**"
---
# FastAPI (SQLAlchemy): data access

- Only `app/db/` and `app/repositories/` import SQLAlchemy; services call repositories.
- Every repository method takes what scopes its rows as a required argument (the tenant id in a multi-tenant
  product).
- One `AsyncSession` per request, from a dependency; a session never crosses requests or tasks.
- Queries use `select()`, `update()` and `delete()`; raw SQL only through `text()` with bound parameters.
- Relationships load explicitly (`selectinload` or a join); lazy loading is set to `raise`, so an accidental N+1
  fails loudly.
- A write to more than one table runs inside `async with session.begin()`, opened by the service.
- The engine and its pool (explicit size and recycle time) are created once in `app/db/session.py`.
- Tests run repositories against a real database, not mocks.
