---
paths:
  - "src/auth/**"
  - "src/middleware/**"
  - "backend/auth/**"
  - "backend/middleware/**"
---
# Node API: auth

Auth is a library's job, chosen by the feature that first needs it and recorded in its change file: Better Auth
inside the backend, or Supabase Auth when the project already uses Supabase. Password hashing, sessions and token
signing are never written by hand.

- **Better Auth** runs in the backend at `/api/auth/*` and is the only writer to its tables. Its schema comes from
  `npx auth@latest generate` and is migrated with Drizzle's tooling; adding a plugin regenerates it in the same
  change. Sessions are read only through `auth.api.getSession({ headers })` in one middleware that builds the
  request's context; services never read cookies. Cookies keep the library's defaults (`HttpOnly`, `Secure`,
  `SameSite=Lax`); trusted origins list only the app's own. Rate limiting is on in production with
  `storage: "database"` (serverless instances share no memory). Secrets: `BETTER_AUTH_SECRET`, `BETTER_AUTH_URL`;
  rotate through `BETTER_AUTH_SECRETS`. On Cloudflare Workers' free plan, password hashing can exceed the CPU limit
  (verify the current limit).
- **Supabase Auth** signs users in; the backend verifies each access token against the project's JWKS
  (`/auth/v1/.well-known/jwks.json`): signature, issuer, audience, expiry and algorithm, with keys cached. The
  user is the token's `sub`, matched to our own `users` row. Roles and tenant come from our tables, never from
  `user_metadata` (the user can edit it). Clients use the Supabase SDK for sign-in only; business data goes through
  `/api/v1/*`. The secret (service role) key bypasses Row Level Security and stays in the server's secret store. The
  web SDK keeps the session in browser storage, readable by injected script: keep the CSP strict.
- Either way: email and password always come with email verification and a reset flow; roles and permissions
  live in our tables keyed by user (and tenant) and are checked in services, never in the client.
