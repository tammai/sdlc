---
paths:
  - "internal/auth/**"
  - "internal/httpapi/**"
---
# Go API: auth

Sessions live in PostgreSQL behind an `HttpOnly` cookie; no token reaches browser JavaScript. Auth is assembled from
maintained libraries, and the code joining them stays small. Password hashing, session tokens and other
cryptography are never written by hand.

- Libraries: `alexedwards/scs` with its `pgxstore` for sessions, `alexedwards/argon2id` for password hashing,
  `markbates/goth` for OAuth sign-in. Passkeys or 2FA only when asked for.
- Endpoints under `/api/auth/*`, in the contract: sign-in, sign-out, current session, one callback per provider.
- Cookie: `HttpOnly`, `Secure`, `SameSite=Lax`, a fixed lifetime and an idle timeout.
- Sign-in calls `RenewToken` before storing the user id (no session fixation); sign-out destroys the session.
- One-time tokens (verification, reset): 32 bytes from `crypto/rand`, stored only as a hash with an expiry,
  deleted on first use. Email and password always come with verification and a reset flow.
- One middleware loads the session, resolves the user (and tenant) and puts the principal in the request context.
- State-changing requests pass `http.CrossOriginProtection` (Go 1.25+).
- Sign-in, sign-up and reset are rate-limited per IP and per account, with counters in a shared store.
- Roles and permissions live in our tables and are checked in services.
