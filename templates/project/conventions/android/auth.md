---
paths:
  - "app/src/main/**/auth/**"
  - "app/src/main/**/api/**"
---
# Android: auth

A mobile app can't rely on browser cookies, so it carries its session as a bearer token the backend issues and can
revoke, like a web session.

- The token is encrypted with a key held in the Android Keystore before it is stored. Not
  `EncryptedSharedPreferences`: Jetpack Security Crypto is deprecated in favour of the platform APIs and the
  Keystore. Never in plain preferences, files or logs.
- One OkHttp interceptor adds the `Authorization` header to every request, over HTTPS only.
- Sign-out revokes the session on the server, then deletes the stored token.
- A 401 clears the token, and the root graph returns to the signed-out flow.
- The app never decides permissions: it shows what the API returns.
