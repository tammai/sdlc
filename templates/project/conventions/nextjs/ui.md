---
paths:
  - "app/**/*.tsx"
  - "components/**"
  - "src/components/**"
  - "app/globals.css"
---
# Next.js: UI with shadcn/ui

`sdlc-ui.md` and the design system hold the general UI rules; this file says how they map onto shadcn/ui.

- Components are added with `npx shadcn@latest add <component>` into `components/ui/` and belong to the repo. A
  file there is edited only to change the design system for the whole app, never for one screen. No second
  component library.
- Colors, radius and fonts are CSS variables in the global stylesheet; components use the semantic tokens
  (`primary`, `muted`, `destructive`) and Tailwind utilities.
- Forms use shadcn's `Field` components with React Hook Form (`Controller`) and a Zod schema; every input has its
  `FieldLabel`. Forms are client components.
- Mutations confirm with a toast (`sonner`) and disable their trigger while pending. A destructive action confirms
  in an `AlertDialog` with the destructive variant.
- Icons from `lucide-react` only.
