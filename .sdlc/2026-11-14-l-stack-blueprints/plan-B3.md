# Part plan: 2026-11-14-l-stack-blueprints B3

**Record:** the feature's change file (`scaffold.py paths <feature>` → `change`) · **Backlog:** [backlog.md](backlog.md)

## Tasks

1. **`scaffold.py conventions`** — AC-007
   - Files: `scripts/scaffold.py`, `tests/test_stack_blueprints.py`
   - Test first: `Conventions.test_render_one_area`
   - Then: `conventions` lists stacks and their areas; `conventions <stack> <area> [--package <name>]` checks
     stack, area, template, package and destination before writing, writes `.claude/rules/<stack>-<area>.md`
     (LF, atomic) with `paths:` = the template's globs under the package path, adds it to `declined` (never to
     `files`) and to `conventions` in the lock (stack, area, package, template, version, sha256);
     `conventions --seen <path>` records the current template after an upgrade's diff; `upgrade-plan` lists
     rendered conventions whose template changed, with a diff. Reports when AGENTS.md's block went stale.
2. **Templates** — AC-007 AC-009
   - Files: `templates/project/conventions/<stack>/<area>.md`
   - Then: one per blueprint `target: rules` module mapped onto the allowlist: node, go, fastapi (layers, schema,
     data-access, contract, auth); nuxt, vue, react, nextjs (layers, ui); flutter, ios, android (layers, auth).
     Prose, no code samples or placeholders; nothing `sdlc-ui.md`, `sdlc-sensitive.md`, `sdlc-migrations.md`
     already says; auth libraries only in auth templates; tenant rules only "when the product is multi-tenant".
3. **Define proposes the render; setup doesn't** — AC-008
   - Files: `skills/orchestrator/references/flow.md`, `skills/orchestrator/references/s-track.md`,
     `skills/setting-up-projects/SKILL.md`, `skills/setting-up-projects/references/greenfield.md`,
     `skills/setting-up-projects/references/upgrade.md`, `skills/setting-up-projects/references/eject.md`
   - Test first: `Conventions.test_rendered_on_first_touch_not_at_setup`
   - Then: Define infers the stack from the package manifest; a change whose files first touch an area of that
     stack with no `<stack>-<area>.md` → a plan task renders it. Setup says no convention is rendered there;
     upgrade offers a changed template as a diff; eject keeps them.

## Public Surface

- command `scaffold.py conventions` — AC-007

## Sources checked (AC-009, 2026-11-14)

Checked by a research subagent and two searches; full list with a URL per claim kept out of the repo (scratchpad
`api-claims.md`). Templates name only what's below.

- Go: `http.CrossOriginProtection` (Go 1.25+), `http.MaxBytesReader`, `log/slog` (pkg.go.dev/net/http);
  `pgxpool.Config.MaxConns`/`MaxConnIdleTime`; sqlc `WithTx(pgx.Tx)`, `@name` params, golang-migrate files as
  schema (down files ignored, lexical order: zero-pad) (docs.sqlc.dev/en/latest/howto/ddl.html); oapi-codegen
  `gin-server` + `strict-server`; `alexedwards/scs` + `pgxstore` (`RenewToken`), `alexedwards/argon2id`,
  `markbates/goth`.
- Node: Hono `secureHeaders`, `bodyLimit`, `requestId`, `csrf` (form content types only, hono.dev/docs/middleware/
  builtin/csrf: the template says so), `app.request()`; Drizzle `drizzle-kit generate`/`push`, `db.transaction`,
  `sql` tag (orm.drizzle.team/docs/kit-overview); Better Auth `npx auth@latest generate` (`@better-auth/cli` is
  unsupported), `auth.api.getSession({ headers })`, rate limit `storage: "database"`, `BETTER_AUTH_SECRET`,
  `BETTER_AUTH_URL`, `BETTER_AUTH_SECRETS` (better-auth.com/docs/concepts/cli, /docs/reference/options); Supabase
  JWKS `/auth/v1/.well-known/jwks.json`, `user_metadata` user-editable, secret key bypasses RLS, web session in
  browser storage (supabase.com/docs/guides/auth/signing-keys).
- Python: `pwdlib` `PasswordHash.recommended()` (pypi.org/project/pwdlib); Authlib Starlette client for FastAPI,
  needing `SessionMiddleware` (docs.authlib.org FastAPI client); pydantic-settings; FastAPI `app.openapi()`,
  `operation_id`, `response_model`; SQLAlchemy 2.x (2.1 current) `Mapped`/`mapped_column`, `selectinload`,
  `lazy="raise"`, `session.begin()`; `alembic revision --autogenerate`.
- Web: TanStack Query v5 `queryOptions`, `invalidateQueries({ queryKey })`, `clear()`; Pinia Colada
  `defineQueryOptions`, `useQuery`, `useQueryCache().invalidateQueries({ key })` (pinia-colada.esm.dev);
  openapi-typescript, openapi-fetch; Nuxt UI v4 `<UApp>`, `<UForm>`, `<UFormField>`, `useToast()`, `<UModal>`,
  `app/app.config.ts` `ui.colors`, `<UIcon>` (ui.nuxt.com); shadcn `npx shadcn@latest add`, forms on `Field` +
  React Hook Form `Controller` (ui.shadcn.com/docs/forms/react-hook-form), `AlertDialog`, `sonner`, `lucide-react`;
  Vue Router `beforeEach` + `meta`; `VITE_`, `NEXT_PUBLIC_`; React Router is at v8, so the template says
  "declarative mode", no version.
- Mobile: `flutter_secure_storage` (Keychain; Android uses its own Keystore-backed ciphers since v10, not
  EncryptedSharedPreferences); go_router `redirect`; Riverpod 3 `FutureProvider`/`AsyncNotifier`; `@Observable`
  iOS 17+ (developer.apple.com migrating-from-the-observable-object-protocol); Android Jetpack Security Crypto
  deprecated in favour of the Keystore (developer.android.com/jetpack/androidx/releases/security); Navigation
  Compose `@Serializable` routes; Hilt; `libs.versions.toml`.
- Dropped, not confirmed: Nuxt UI's color option for plain Vue (the Vue template says "one place"); DataStore +
  Tink for Android tokens (community pattern only); Zustand API details (named only as the store);
  `NavigationStack`, Keychain Services and String Catalogs are named as Apple features, not APIs, since Apple's
  pages didn't render for the check.
