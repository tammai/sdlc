---
paths:
  - "app/auth/**"
  - "app/routers/auth*"
---
# FastAPI: auth

Sessions live in PostgreSQL behind an `HttpOnly` cookie; no token reaches browser JavaScript. Auth is assembled from
maintained libraries, and the code joining them stays small. Password hashing and token generation are never
written by hand.

- Libraries: `pwdlib` with Argon2 (`PasswordHash.recommended()`) for passwords, Authlib's Starlette client for
  OAuth sign-in (it keeps its state in the session, so it needs Starlette's `SessionMiddleware`). Passkeys or 2FA
  only when asked for.
- Endpoints under `/api/auth/*`: sign-in, sign-out, current session, one callback per provider.
- Session tokens come from `secrets.token_urlsafe(32)`; the database keeps only a SHA-256 hash, an expiry and an
  idle timeout. Cookie: `HttpOnly`, `Secure`, `SameSite=Lax`.
- Sign-in issues a fresh session and deletes the previous one; sign-out deletes the session row.
- One-time tokens (verification, reset) are made the same way, stored hashed with an expiry, deleted on first use.
  Email and password always come with verification and a reset flow.
- One dependency, `current_principal`, loads the session and returns the principal (user, and tenant); routers
  pass it to services.
- A middleware rejects state-changing requests whose `Origin` or `Sec-Fetch-Site` shows another site.
- Sign-in, sign-up and reset are rate-limited per IP and per account, with counters in a shared store.
- Roles and permissions live in our tables and are checked in services.
