---
paths:
  - "**/Auth/**"
  - "**/API/**"
---
# iOS: auth

A mobile app can't rely on browser cookies, so it carries its session as a bearer token the backend issues and can
revoke, like a web session.

- The token lives only in the Keychain (Keychain Services). Never in `UserDefaults`, files or logs.
- One client middleware adds the `Authorization` header to every request, over HTTPS only.
- Sign-out revokes the session on the server, then deletes the token from the Keychain.
- A 401 clears the token, and the root view switches to the signed-out flow.
- The app never decides permissions: it shows what the API returns.
