---
paths:
  - "app/**"
  - "src/**"
  - "next.config.*"
---
# Next.js: layers

The App Router app. It knows two things about the backend: the `/api/*` paths and the types generated from the
contract.

- Interactive screens are client components that read and write through query hooks. Server actions, route
  handlers and server components never read or change business data; it goes through `/api/v1/*`. (One
  deployable: the bridge route under `app/api/` mounts the Hono app and holds no logic.)
- Server data flows through TanStack Query and one `openapi-fetch` client typed by `openapi-typescript` (the
  `generate:api` script; its output isn't committed and runs before build and test).
- Queries live in one file per domain under `queries/`, exporting `queryOptions` objects and `useXxx` mutation
  hooks; components call only `useQuery(...)` or those hooks, never the client, and never fetch in `useEffect`.
- Keys go from general to specific; a mutation invalidates its domain's prefix through
  `queryClient.invalidateQueries({ queryKey })`. One `["session"]` query reads the session; sign-out calls
  `queryClient.clear()`; a 401 invalidates `["session"]`.
- A guard in the signed-in layout sends a signed-out user to `/login`. That's user experience only.
- Zustand stores hold UI state only; server data is never copied into one.
- Only `NEXT_PUBLIC_` variables reach the browser, and all of them are public: never a secret. User content is
  never rendered with `dangerouslySetInnerHTML`.
- Tests: Vitest with Testing Library for hooks and components with logic; Playwright for sign-in and the one or
  two critical flows.
