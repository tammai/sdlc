---
paths:
  - "src/components/**"
  - "src/views/**"
  - "src/App.vue"
  - "src/assets/**"
---
# Vue: UI with Nuxt UI

`sdlc-ui.md` and the design system hold the general UI rules; this file says how they map onto Nuxt UI in a Vue
app (its Vite plugin and Vue plugin, set up as the stack's Vue section says).

- `App.vue` wraps the app in `<UApp>`, so toasts, tooltips and overlays work.
- Nuxt UI covers buttons, inputs, forms, tables, modals, menus, navigation and layout: look there before writing
  markup. A custom component is composed from Nuxt UI primitives; no second component library.
- The theme colors (`primary`, `neutral`) are configured in one place, tokens in the main CSS file. Components use the semantic colors (`primary`, `neutral`, `success`, `error`) and Tailwind utilities.
- Forms are `<UForm>` with a Zod schema and `<UFormField>` around every input, which gives it its label.
- Mutations confirm through `useToast()` and disable their trigger while pending. A destructive action confirms in
  a `<UModal>` with the button colored `error`.
- Icons through the `icon` prop or `<UIcon>` (Iconify); no other icon package.
