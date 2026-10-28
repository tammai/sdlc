# Spec 10: UI and the design system

When a project has UI, every UI change follows the project's design system and avoids the generic "AI look". The design system is recorded once at setup, applied while writing (policy rule, guardrail) and checked in review.

**Entry points:** setup (`design-system` step), Define and Review, `/sdlc:review-pr ui`, `/sdlc:doctor` · **Source:** `templates/project/rules/ui.md`, `templates/project/hookify/sdlc-ui-hardcoded-values.md`, `templates/design-system-template.md`, `agents/ui-reviewer.md`, `skills/setting-up-projects/SKILL.md`, `skills/orchestrator/references/ui-work.md`, `migrations/1.4.0-design-system.md`, `migrations/2.1.0-design-mode.md`, `scripts/scaffold.py` (`design`, `guardrails`), `hooks/model_router.py` · **Decision:** [ADR 0004](../adr/0004-ui-follows-the-design-system.md), [ADR 0021](../adr/0021-impeccable-for-ui-design.md) (impeccable mode)

## User scenarios

1. **Existing system.** Given a React repo using shadcn/ui and a Tailwind theme, when the user runs `/sdlc:setup`, then `docs/sdlc/design-system.md` points at the theme, `components/ui` and the icon set, and the user approves it before it's written.
2. **No system.** Given a greenfield web app, when setup reaches the design-system step, then it proposes one mainstream library and a minimal token set; it never invents a bespoke system.
3. **Hard-coded color.** When Claude writes `className="bg-[#1a2b3c]"` in a `.tsx` file, then a warning names the design system and the write goes ahead.
4. **Generic hero.** Given a feature whose diff adds a purple-gradient hero with emoji feature cards, when Review runs the UI review (always recommended for a diff touching `areas.ui`), then `sdlc:ui-reviewer` reports both as High and the gate doesn't pass until they're fixed.
5. **Screenshots.** When the user asks for a visual check and Playwright and a dev server command are available, then the reviewer screenshots the changed screens; otherwise it says why it didn't.

## Requirements

| ID | Requirement | Guarantee |
|---|---|---|
| UI-FR-001 | `areas.ui` defaults to web UI files (`tsx jsx vue svelte astro html css scss sass less`); setup adjusts it to the project's real UI paths (Flutter, SwiftUI, …). | defaults `[enforced]` test_project_templates › test_defaults_file_is_valid_json_with_every_area; adjusting `[instructed]` setting-up-projects |
| UI-FR-002 | Setup's `design-system` step runs only for projects with UI. It finds an existing system and writes `docs/sdlc/design-system.md` pointing at it, or proposes a mainstream library plus minimal tokens; the user approves. The file is user-owned and eject keeps it. | `[instructed]` setting-up-projects; eject keep list in `scaffold.py` |
| UI-FR-003 | Generated rule `sdlc-ui.md`, scoped by `areas.ui`, ≤ 30 lines: follow the design system strictly; tokens only; reuse its components; new component, variant or token needs a reason and goes into the system; no AI-slop styling or filler copy; every state the spec names; accessibility basics. | length and frontmatter `[enforced]` test_project_templates › test_area_rules_have_paths_frontmatter_and_stay_short; content `[instructed]` rules/ui.md |
| UI-FR-004 | Guardrail `sdlc-ui-hardcoded-values` **warns** on raw hex/rgb/hsl colors, arbitrary Tailwind values and inline `style=` in UI files, and stays quiet in token and theme files, CSS custom-property definitions, `var(--…)`, style references like `style={styles.card}`, `#anchor` links and non-UI files. | `[enforced]` test_guardrails › test_file_guardrails_on_write |
| UI-FR-005 | Define: a UI spec names each screen's states (loading, empty, error, success) and its real copy. | `[instructed]` orchestrator: define, `ui-work.md` |
| UI-FR-006 | Define, at every size (S too: every size has a state file): the state file's `## UI mapping` maps each changed screen to the system's components, tokens and patterns. Anything the system lacks goes to the user; an approved addition goes into `docs/sdlc/design-system.md` before Build, logged with `state.py log`. | `[instructed]` orchestrator: define, `ui-work.md` |
| UI-FR-007 | Review: when the diff touches `areas.ui`, the UI review is always recommended (S runs it; on M and L the user can decline it), and `sdlc:ui-reviewer`, on `opus`, checks tokens, components, AI-slop patterns, states, accessibility and consistency. Off-system values or components, slop, missing spec'd states and accessibility blockers are High and block the gate. `/sdlc:review-pr` picks it for UI diffs. Its "Proposed design-system changes" go to the user: accepted ones are added to the system and resolve the findings they cover; declined ones send the code back to existing tokens or components. | `[instructed]` orchestrator: review, `ui-work.md`, ui-reviewer.md, review-pr.md |
| UI-FR-008 | Visual check only when the user asks: with a browser tool and a dev server command, screenshots at desktop and mobile width (and dark mode if the system has one); otherwise "Visual check not run: <reason>". Never installs tools for it. | `[instructed]` ui-reviewer.md |
| UI-FR-009 | `/sdlc:doctor` warns when a set-up repo has UI files and no `docs/sdlc/design-system.md`. | `[enforced]` test_doctor › test_ui_without_design_system_warns |
| UI-FR-010 | Existing repos get the rule and guardrail from the upgrade's *add* step, and the design system from migration `1.4.0-design-system` (skipped when the repo has no UI). | add step `[enforced]` test_scaffold › test_upgrade_adds_rules_and_guardrails_new_in_this_version; migration `[instructed]` |
| UI-FR-011 | Design mode, config `design`: `builtin` (default; UI-FR-001 to 010 as written) or `impeccable` (ADR 0021). `scaffold.py design [<mode>]` prints or records it and refuses any other value. Setup's `design-system` step asks for it, recommending from the PRD; sdlc never installs impeccable (chosen but missing → builtin and the install command). | key `[enforced]` test_scaffold › test_design_mode_records_and_refuses_unknown; the step `[instructed]` setting-up-projects |
| UI-FR-012 | impeccable mode leaves `sdlc-ui-hardcoded-values` out of the guardrails setup and upgrade install (`scaffold.py guardrails`); its detector hook does that job. Setting the mode swaps an installed copy: impeccable deletes an unchanged one (untracked, not declined), an edited one is asked about; builtin renders it again unless declined. | `[enforced]` test_scaffold › test_impeccable_mode_drops_ui_guardrail, test_switching_design_mode_swaps_the_ui_guardrail |
| UI-FR-013 | impeccable mode: `design-system.md` points at `DESIGN.md`; Define runs `/impeccable shape` and copies its brief into `## UI mapping`; Build goes through impeccable; `sdlc:ui-reviewer` keeps the verdict, with `detect` and `audit` as evidence and no `critique`; with no `DESIGN.md` yet, Define maps against the brief and the existing screens, no task writes it (impeccable does, in its own process), and the review reports it as Medium, never High. impeccable missing at run time → that step runs builtin, said in one line. | `[instructed]` ui-work.md, ui-reviewer.md |
| UI-FR-014 | The model router lets impeccable's own agents (`impeccable-*`) through without a model; every other rule stands. | `[enforced]` test_model_router › test_impeccable_agents_pass_without_model |

## Edge cases

- Native mobile or desktop UI (Flutter, SwiftUI, Compose): the guardrail's patterns are web-only; the rule, reviewer and doctor still apply once `areas.ui` names the real paths.
- A legitimately new token: approved in Define when the UI mapping names it, otherwise listed by the reviewer under "Proposed design-system changes" for the user to decide. Either way it's added to the system and the tokens file in the same change.
- No design system file in a UI diff: the reviewer reports it as its first High finding and reviews against neighbouring screens.

## Non-goals

- Generating designs, mockups or Figma files; choosing a visual style for the user. (In impeccable mode impeccable does design work; sdlc still doesn't.)
- Automatic screenshots or visual regression on every change.
- Pixel-level checks of native mobile UI.

## Known gaps

- On M and L the user can decline the UI review; such a change is checked against the design system only by the guardrail and the rule.
