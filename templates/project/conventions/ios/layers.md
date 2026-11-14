---
paths:
  - "**/*.swift"
  - "Package.swift"
---
# iOS: layers

A SwiftUI app that talks to the backend only through the client Swift OpenAPI Generator builds from the contract.

- Feature-first: each domain has a folder with its views and view models; shared code sits in `App/` (entry,
  navigation, theme) and `API/` (client setup, auth middleware).
- View models are `@Observable` classes (iOS 17+) calling the client with `async`/`await`; views read view models
  and never call the client.
- Navigation is a `NavigationStack` with typed routes; one root view switches between the signed-out and
  signed-in flows.
- The generated client (build plugin, URLSession transport) is never committed or edited.
- Swift Concurrency only: UI state changes on the main actor; no completion-handler networking, no manual dispatch
  queues.
- The API base URL and other public values come from one build configuration file per environment. The app holds
  no secret: its users can read anything in it.
- System components, SF Symbols, semantic colors and Dynamic Type text styles; no color or font literal in a view.
- User-facing strings go through a String Catalog, so localization can be added later.
- Dependencies through Swift Package Manager only, each one approved first. Creating or restructuring the Xcode
  project is a step the engineer does or approves.
- Tests: view models with a stubbed transport, one UI test per critical flow; the build has no warnings.
