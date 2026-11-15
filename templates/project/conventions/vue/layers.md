---
paths:
  - "src/**"
  - "vite.config.ts"
---
# Vue: layers

A Vue 3 single-page app on Vite. It knows two things about the backend: the `/api/*` paths and the types generated
from the contract.

- Components are single-file components with `<script setup lang="ts">` and the Composition API; no Options API,
  no mixins.
- Server data flows through Pinia Colada and one `openapi-fetch` client typed by `openapi-typescript` (the
  `generate:api` script; its output isn't committed and runs before build and test).
- Queries live in `src/queries/<domain>.ts`, exporting `defineQueryOptions` objects and `useXxx` mutation
  functions; components call only `useQuery(...)` or those functions, never the client.
- Keys go from general to specific (`["orders"]`, `["orders", id]`); a mutation invalidates its domain's prefix
  through `useQueryCache().invalidateQueries({ key })`.
- One `["session"]` query reads the current session; sign-in and sign-out invalidate it, and sign-out clears the
  whole query cache. A 401 from any call invalidates `["session"]`.
- Routes are declared in `src/router/` with Vue Router, each page lazy-loaded. One `router.beforeEach` guard sends
  a signed-out user to `/login`; public routes opt out through `meta`. That's user experience only.
- Pinia stores hold UI state only; server data is never copied into one.
- Only `VITE_` variables reach the app, and all of them are public: never a secret. User content is never
  rendered with `v-html`.
- Tests: Vitest with Vue Test Utils for composables and components with logic; Playwright for sign-in and the one
  or two critical flows.
