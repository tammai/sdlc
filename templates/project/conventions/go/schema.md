---
paths:
  - "db/migrations/**"
  - "migrations/**"
  - "sqlc.yaml"
---
# Go API (golang-migrate, sqlc): schema

- Primary keys are UUIDs, times are `timestamptz` in UTC, table and column names are `snake_case`.
- Business tables have `created_at` and `updated_at`; rows are hard-deleted unless a table asks for soft delete.
- A new filter or sort on a table that grows comes with an index; unique constraints match the rule they enforce.
- When the product is multi-tenant (the PRD or the constitution says so): every business table has
  `tenant_id NOT NULL` with a foreign key, unique constraints include it, indexes on growing tables start with it,
  and a test proves one tenant can't read another's rows. The tenant id comes only from the verified session.
- golang-migrate files in `db/migrations/`, each an up and a down; sqlc reads the same folder as its schema.
- Migrations run from CI or the deploy over a direct connection, never from the app at startup.
