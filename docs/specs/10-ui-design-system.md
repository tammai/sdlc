# Spec 10: UI and the design system

When a project has UI, every UI change follows the project's design system and avoids the generic "AI look". The design system is recorded once at setup, applied while writing (policy rule, guardrail) and checked in review.

**Entry points:** setup (`design-system` step), Stages 1, 2 and 6, `/sdlc:review-pr ui`, `/sdlc:doctor` · **Source:** `templates/project/rules/ui.md`, `templates/project/hookify/sdlc-ui-hardcoded-values.md`, `templates/design-system-template.md`, `agents/ui-reviewer.md`, `skills/setting-up-projects/SKILL.md`, `skills/orchestrator/SKILL.md`, `migrations/1.4.0-design-system.md` · **Decision:** [ADR 0004](../adr/0004-ui-follows-the-design-system.md)

## User scenarios

1. **Existing system.** Given a React repo using shadcn/ui and a Tailwind theme, when the user runs `/sdlc:setup`, then `.sdlc/design-system.md` points at the theme, `components/ui` and the icon set, and the user approves it before it's written.
2. **No system.** Given a greenfield web app, when setup reaches the design-system step, then it proposes one mainstream library and a minimal token set; it never invents a bespoke system.
3. **Hard-coded color.** When Claude writes `className="bg-[#1a2b3c]"` in a `.tsx` file, then a warning names the design system and the write goes ahead.
4. **Generic hero.** Given a diff that adds a purple-gradient hero with emoji feature cards, when Stage 6 runs, then `sdlc:ui-reviewer` reports both as High and the gate doesn't pass until they're fixed.
5. **Screenshots.** When the user asks for a visual check and Playwright and a dev server command are available, then the reviewer screenshots the changed screens; otherwise it says why it didn't.

## Requirements

| ID | Requirement | Guarantee |
|---|---|---|
| UI-FR-001 | `areas.ui` defaults to web UI files (`tsx jsx vue svelte astro html css scss sass less`); setup adjusts it to the project's real UI paths (Flutter, SwiftUI, …). | defaults `[enforced]` test_project_templates › test_defaults_file_is_valid_json_with_every_area; adjusting `[instructed]` setting-up-projects |
| UI-FR-002 | Setup's `design-system` step runs only for projects with UI. It finds an existing system and writes `.sdlc/design-system.md` pointing at it, or proposes a mainstream library plus minimal tokens; the user approves. The file is user-owned and eject keeps it. | `[instructed]` setting-up-projects; eject keep list in `scaffold.py` |
| UI-FR-003 | Generated rule `sdlc-ui.md`, scoped by `areas.ui`, ≤ 30 lines: follow the design system strictly; tokens only; reuse its components; new component, variant or token needs a reason and goes into the system; no AI-slop styling or filler copy; every state the spec names; accessibility basics. | length and frontmatter `[enforced]` test_project_templates › test_area_rules_have_paths_frontmatter_and_stay_short; content `[instructed]` rules/ui.md, and the same lines in implementer-prompt.md |
| UI-FR-004 | Guardrail `sdlc-ui-hardcoded-values` **warns** on raw hex/rgb/hsl colors, arbitrary Tailwind values and inline `style=` in UI files, and stays quiet in token and theme files, CSS custom-property definitions, `var(--…)`, style references like `style={styles.card}`, `#anchor` links and non-UI files. | `[enforced]` test_guardrails › test_file_guardrails_on_write |
| UI-FR-005 | Stage 1: a UI spec names each screen's states (loading, empty, error, success) and its real copy. | `[instructed]` orchestrator §1 |
| UI-FR-006 | Stage 2: design.md maps each screen to the system's components, tokens and patterns; a new component, variant or token is a Complexity Tracking row. Once the user approves one, it goes into `.sdlc/design-system.md` before Stage 4, logged in the Gate log. When Stage 2 is skipped (S, or an obvious M), the same mapping goes in plan.md's `UI mapping` section (M) or the Gate log (S), and anything the system lacks still goes to the user before Stage 4. | `[instructed]` designing-solutions, orchestrator §2 |
| UI-FR-007 | Stage 6, every track: when the diff touches `areas.ui`, `sdlc:ui-reviewer` checks tokens, components, AI-slop patterns, states, accessibility and consistency. Off-system values or components, slop, missing spec'd states and accessibility blockers are High and block the gate. `/sdlc:review-pr` picks it for UI diffs. Its "Proposed design-system changes" go to the user: accepted ones are added to the system and resolve the findings they cover; declined ones send the code back to existing tokens or components. | `[instructed]` orchestrator §6, ui-reviewer.md, review-pr.md |
| UI-FR-008 | Visual check only when the user asks: with a browser tool and a dev server command, screenshots at desktop and mobile width (and dark mode if the system has one); otherwise "Visual check not run: <reason>". Never installs tools for it. | `[instructed]` ui-reviewer.md |
| UI-FR-009 | `/sdlc:doctor` warns when a set-up repo has UI files and no `.sdlc/design-system.md`. | `[enforced]` test_doctor › test_ui_without_design_system_warns |
| UI-FR-010 | Existing repos get the rule and guardrail from the upgrade's *add* step, and the design system from migration `1.4.0-design-system` (skipped when the repo has no UI). | add step `[enforced]` test_scaffold › test_upgrade_adds_rules_and_guardrails_new_in_this_version; migration `[instructed]` |

## Edge cases

- Native mobile or desktop UI (Flutter, SwiftUI, Compose): the guardrail's patterns are web-only; the rule, reviewer and doctor still apply once `areas.ui` names the real paths.
- A legitimately new token: approved in Stage 2 when the design names it, otherwise listed by the reviewer under "Proposed design-system changes" for the user to decide. Either way it's added to the system and the tokens file in the same change.
- No design system file in a UI diff: the reviewer reports it as its first High finding and reviews against neighbouring screens.

## Non-goals

- Generating designs, mockups or Figma files; choosing a visual style for the user.
- Automatic screenshots or visual regression on every change.
- Pixel-level checks of native mobile UI.
