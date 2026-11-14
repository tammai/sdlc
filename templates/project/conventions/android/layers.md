---
paths:
  - "app/src/**"
  - "app/build.gradle.kts"
  - "gradle/libs.versions.toml"
---
# Android: layers

A Jetpack Compose app that talks to the backend only through a client generated from the contract.

- Feature-first packages: each domain has its screens, view models and a repository; shared code sits in `app`
  (entry, navigation, theme) and `api` (client setup, auth interceptor).
- Each screen has a `ViewModel` exposing one immutable UI state as a `StateFlow`; composables collect it and send
  events, and never call the API client. Repositories call the client.
- Navigation Compose with type-safe routes (`@Serializable` route types); one root graph switches between the
  signed-out and signed-in flows.
- The generated client (OkHttp, Kotlin serialization) is built by a Gradle task and never committed or edited.
- Coroutines and Flow: network and disk work off the main dispatcher; view models launch in `viewModelScope`.
- Hilt, with constructor injection everywhere.
- The API base URL and other public values come from build types and `BuildConfig`. The APK holds no secret: its
  users can read anything in it.
- Material 3: colors, shapes and typography come from `MaterialTheme`, never literals. Touch targets are at least
  48 dp; text scales with the system font size; strings live in string resources.
- Dependencies are declared in `gradle/libs.versions.toml`, each one approved first.
- Tests: view models with a fake repository, one Compose UI test per critical flow; Android lint passes.
