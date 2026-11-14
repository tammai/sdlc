---
paths:
  - "lib/auth/**"
  - "lib/api/**"
  - "lib/features/auth/**"
---
# Flutter: auth

A mobile app can't rely on browser cookies, so it carries its session as a bearer token the backend issues and can
revoke, like a web session.

- The token lives only in `flutter_secure_storage` (the iOS Keychain; on Android, the package's own
  Keystore-backed encryption). Never in plain preferences, files or logs.
- One `dio` interceptor adds the `Authorization` header to every request, over HTTPS only.
- Sign-out revokes the session on the server, then deletes the token on the device.
- A 401 clears the token, and the router's `redirect` returns the user to sign-in.
- The app never decides permissions: it shows what the API returns.
