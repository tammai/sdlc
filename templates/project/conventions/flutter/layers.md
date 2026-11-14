---
paths:
  - "lib/**"
  - "test/**"
  - "pubspec.yaml"
---
# Flutter: layers

The app talks to the backend only through a client generated from the contract.

- Feature-first: each domain has a folder under `lib/features/` with its screens, widgets and providers; shared
  code sits in `lib/app/` (entry, routing, theme) and `lib/api/`.
- State is Riverpod. Server data comes from async providers (`FutureProvider`, `AsyncNotifier`) that call the
  API client; widgets watch providers and never call the client. Local UI state stays in the widget.
- Routing is `go_router`, with one `redirect` sending a signed-out user to sign-in.
- The API client is generated from the contract into `lib/api/generated/` (the stack's Flutter section names the
  generator) on `dio`; generated code is never edited, and models come from it. Hand-written models are UI state
  only.
- The API base URL and other public values come from `--dart-define`. The app bundle holds no secret: its users
  can read anything in it.
- One `ThemeData` from a color scheme; widgets read colors and text styles from the theme. Tappable targets are at
  least 48 logical pixels; text scales with the system setting.
- User-facing strings sit in one place per feature, so localization can be added later.
- Tests: unit tests for providers, widget tests for screens with logic, one integration test per critical flow;
  `flutter analyze` reports nothing.
