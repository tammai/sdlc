---
paths:
  - "app/components/**"
  - "app/pages/**"
  - "app/layouts/**"
  - "app/app.vue"
  - "app/app.config.ts"
  - "app/assets/css/**"
---
# Nuxt: UI with Nuxt UI

`sdlc-ui.md` and the design system hold the general UI rules; this file says how they map onto Nuxt UI.

- The root wraps the app in `<UApp>`, so toasts, tooltips and overlays work.
- Nuxt UI covers buttons, inputs, forms, tables, modals, menus, navigation and layout: look there before writing
  markup. A custom component is composed from Nuxt UI primitives; no second component library.
- Colors are set once in `app/app.config.ts` under `ui.colors` (`primary`, `neutral`), tokens in `main.css`
  (`@import "tailwindcss"; @import "@nuxt/ui";`). Components use the semantic colors (`primary`, `neutral`,
  `success`, `error`) and Tailwind utilities; no scoped CSS overriding Nuxt UI internals.
- Forms are `<UForm>` with a Zod schema (shared with the API where the schemas are shared) and `<UFormField>`
  around every input, which gives it its label.
- Mutations confirm through `useToast()` and disable their trigger while pending. A destructive action confirms in
  a `<UModal>` with the button colored `error`.
- Icons through the `icon` prop or `<UIcon>` (Iconify); no other icon package.
