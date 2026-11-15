---
paths:
  - "src/**"
  - "vite.config.ts"
---
# React: layers

A React single-page app on Vite. It knows two things about the backend: the `/api/*` paths and the types generated
from the contract.

- Function components and hooks only. Nothing fetches in `useEffect`.
- Server data flows through TanStack Query and one `openapi-fetch` client typed by `openapi-typescript` (the
  `generate:api` script; its output isn't committed and runs before build and test).
- Queries live in `src/queries/<domain>.ts`, exporting `queryOptions` objects and `useXxx` mutation hooks;
  components call only `useQuery(...)` or those hooks, never the client.
- Keys go from general to specific (`["orders"]`, `["orders", id]`); a mutation invalidates its domain's prefix
  through `queryClient.invalidateQueries({ queryKey })`.
- One `["session"]` query reads the current session; sign-in and sign-out invalidate it, and sign-out calls
  `queryClient.clear()`. A 401 from any call invalidates `["session"]`.
- Routes are declared in one place with React Router (declarative mode). A guard component sends a signed-out user
  to `/login`. That's user experience only: the backend enforces access.
- Zustand stores hold UI state only; server data is never copied into one.
- Only `VITE_` variables reach the app, and all of them are public: never a secret. User content is never
  rendered with `dangerouslySetInnerHTML`.
- Tests: Vitest with Testing Library for hooks and components with logic; Playwright for sign-in and the one or
  two critical flows.
