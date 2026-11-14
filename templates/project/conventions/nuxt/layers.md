---
paths:
  - "app/**"
  - "nuxt.config.ts"
---
# Nuxt: layers

A Nuxt single-page app (`ssr: false`). It knows two things about the backend: the `/api/*` paths and the types
generated from the contract.

- Server data flows through Pinia Colada and one `openapi-fetch` client typed by `openapi-typescript` (the
  `generate:api` script; its output isn't committed and runs before build and test). No `useFetch`,
  `useAsyncData` or bare `$fetch` against business endpoints.
- Queries live in `app/composables/queries/<domain>.ts`, exporting `defineQueryOptions` objects and `useXxx`
  mutation functions; components call only `useQuery(...)` or those functions, never the client.
- Keys go from general to specific (`["orders"]`, `["orders", id]`); a mutation invalidates its domain's prefix
  through `useQueryCache().invalidateQueries({ key })`.
- One `["session"]` query reads the current session; sign-in and sign-out invalidate it, and sign-out clears the
  whole query cache. A 401 from any call invalidates `["session"]`.
- One global route middleware sends a signed-out user to `/login`; public pages opt out with `definePageMeta`.
  That's user experience only: the backend enforces access.
- Pinia stores hold UI state only (filters, open panels, wizard steps); server data is never copied into one.
- The app holds no secret: `runtimeConfig.public` is for public values only. User content is never rendered with
  `v-html`.
- One deployable: the bridge file in `server/api/` mounts the Hono app and holds no logic.
- Tests: Vitest for query composables and components with logic; Playwright for sign-in and the one or two
  critical flows.
