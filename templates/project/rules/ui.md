---
paths:
{{config.areas.ui|yaml_list}}
---
<!-- Managed by the sdlc plugin v{{plugin_version}}; regenerated on upgrade. Change paths via "areas.ui" in .sdlc/config.json. -->
# UI (sdlc policy)

Design system
- Read `.sdlc/design-system.md` before UI work. It names the tokens, the component library and the patterns this project uses; follow it strictly.
- Colors, spacing, type, radius, shadows and motion come from tokens only: no raw hex/rgb, arbitrary Tailwind values (`w-[13px]`) or inline `style=`.
- Reuse the design system's components. A new component, variant or token needs a stated reason, and goes into the design system, not inline.
- No design system file yet? Say so and ask before building UI; don't invent one silently.

No AI slop
- No default "AI look": purple/blue gradients, glassmorphism, glow, blobs, oversized rounded cards, emoji as icons, gradient text, decorative shadows. Only what the design system defines.
- No generic filler: lorem ipsum, "Welcome to", "Get started today", three-feature-card heroes, stock testimonials. Use the spec's real copy or ask.
- Match the density, alignment and hierarchy of existing screens; don't restyle what the task didn't ask for.

Every screen
- Handle loading, empty, error and success states the spec names.
- Accessible by default: semantic elements, labels on inputs and icon buttons, visible focus, keyboard reachable, contrast from the system's tokens.
