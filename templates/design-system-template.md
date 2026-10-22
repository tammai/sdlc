# Design system

<!-- Project-owned. Written at setup (design-system step) with the user's approval; change it only with the team's approval. Every UI change follows it: `.claude/rules/sdlc-ui.md` loads with UI files and `sdlc:ui-reviewer` checks diffs against it. Point at the source of truth; don't copy values that live in code. -->

## Source of truth
- Library: <e.g. shadcn/ui on Radix · MUI 6 · Vuetify 3 · Flutter Material 3 · none, our own components>
- Tokens: <path: src/styles/tokens.css · tailwind.config.ts `theme` · @theme in app.css · lib/theme.dart>
- Components: <path to the project's component folder; Storybook URL if any>
- Icons: <set, e.g. lucide-react>; never emoji as icons
- Fonts: <families, where they're loaded>
- Themes: <light only | light + dark>

## Tokens
Use these by name; the values live in the tokens file.
- Color roles: <background, foreground, primary, muted, accent, destructive, border, ring, …>
- Spacing: <scale, e.g. 4px steps: 1 2 3 4 6 8 12 16>
- Type: <role → token: display, heading, body, small, caption>
- Radius / shadow / motion: <tokens; "none" is a valid answer>

## Components to reuse
| Need | Use | Not |
|---|---|---|
| <Button> | <`<Button variant="…">` from components/ui/button> | <a styled `<button>`> |

## Patterns
- Layout: <max width, grid, page and section spacing>
- Forms: <label placement, help and error text, required marker>
- Feedback: <inline errors vs toast; skeleton vs spinner>
- Empty and error states: <the component or pattern to use>

## Don't
Project-specific, on top of the AI-slop list in `.claude/rules/sdlc-ui.md`:
- <e.g. no gradients; no cards inside cards; one primary button per view>

## Changing the system
A new token, component or variant is proposed in the feature's design (Complexity Tracking) or in review, approved by the user, then added here and to the tokens or component files in the same change.
