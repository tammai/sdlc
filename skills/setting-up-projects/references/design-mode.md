# The design-system step: design mode and design system

Setup's `design-system` step, also run on its own by `/sdlc:setup design` (below) and by migration `2.1.0-design-mode`. Decision: `${CLAUDE_PLUGIN_ROOT}/docs/adr/0021-impeccable-for-ui-design.md`.

Only when the project has UI: files match `areas.ui`, or the greenfield stack has a web, mobile or desktop UI. No UI → record the step and say so. First fix `areas.ui` to the real UI paths (e.g. `lib/**/*.dart` for Flutter, `**/*View.swift`).

## 1. Ask the design mode (hard stop, every time)

Who does the UI design work: `builtin` (sdlc's design system, rule and guardrail) or `impeccable` (the [impeccable](https://github.com/pbakaus/impeccable) skill; sdlc keeps the gates and the review verdict). Put the question to the user even when the answer looks obvious, and never record a mode they didn't give.

- Run `$S design` first and say where impeccable stands here (`impeccable.state`): `missing`, `disabled` (installed as a Claude Code plugin but off for this repo, so none of its commands load) or `enabled`.
- Recommend from the PRD: **impeccable** for a user-facing product (audience consumer or business) with no established design system, web or native (its design commands cover iOS and Android; its detector only web files). **builtin** for an internal tool on a stock component library, a system a design team owns, or a PRD constraint of offline or no third-party network calls.
- In the same message: impeccable's new-design flow fetches directions from impeccable.style and, unless turned off (`IMPECCABLE_NO_TELEMETRY=1` or `DO_NOT_TRACK=1`), sends an anonymous record of the choice.
- `disabled` and the user may pick impeccable: ask in the same message whether to turn it on for this repo on this machine (`.claude/settings.local.json`, never committed). Say it loads next session, not this one. Turning it on for every project is the user's own `claude plugin enable <id> --scope user`, never sdlc's.

Record the answer with `$S design <mode>` and put the mode **and the user's reason** in the body of the step's commit (`Design mode: impeccable. Why: <their reason>`), so the choice can be traced later.

## 2. impeccable chosen

By `impeccable.state`:

- **`missing`:** give the install command (`npx impeccable install`, or `/plugin marketplace add pbakaus/impeccable` in Claude Code), never install it yourself, record `builtin` and say `/sdlc:setup design` runs this step again once it's installed.
- **`disabled`:** with the user's yes, `$S design impeccable --enable`. Its `guardrail.kept` is expected: sdlc's UI guardrail stays until impeccable's detector hook runs, so nothing goes unchecked in between. Then `$S step-done design-system --pending "impeccable loads next session"`, commit, and carry on with the remaining steps. Before `finalize`, tell the user to restart Claude Code and run `/sdlc:setup`: it resumes here with impeccable loaded. The user said no: record `builtin`, as for `missing`.
- **`enabled`:** in order:
  1. `/impeccable init`, telling it to read the PRD (its `PRODUCT.md` starts with a line linking to the PRD, which wins where they differ).
  2. Existing UI: `/impeccable document` (it writes `DESIGN.md`), or the pinned form below. No styles to document yet: `DESIGN.md` comes later, from impeccable's own process (`ui-work.md`).
  3. The detector hook: `$S design impeccable` again. `guardrail.removed`: impeccable's hook now does that check. `guardrail.kept`: the hook doesn't run here; a skill-folder install (`impeccable.via` is `skill`) needs `/impeccable hooks on`, a plugin one `/impeccable hooks status`; then run it again. `guardrail.ask`: the team edited that file, so ask before deleting it.
  4. Write `<docs>/design-system.md` from the template's impeccable form, a pointer to `DESIGN.md`.

sdlc never edits `PRODUCT.md`, `DESIGN.md` or `.impeccable/`; impeccable writes them.

**An existing system the project must stay on** (a design team's system, a library such as Primer or Material named in the constitution or PRD, a rule against raw values): offer to have impeccable document it as pinned instead of scanning. Run `/impeccable document` with this brief: `DESIGN.md` names that system and its token source as the only one; the visual direction is not open; the restyling commands (`bolder`, `colorize`, `overdrive`, `delight`) are off limits; new UI composes the system's components and semantic tokens. impeccable follows its brief, and Build skips any command `DESIGN.md` puts off limits.

## 3. builtin chosen

- **Existing system:** find it (tokens or theme files, Tailwind theme or `@theme`, the UI library in the manifest, shadcn's `components.json`, a `components/ui` folder, Storybook) and fill `<docs>/design-system.md` from `${CLAUDE_PLUGIN_ROOT}/templates/design-system-template.md`, pointing at it rather than copying values.
- **None:** propose one mainstream component library for the stack plus a minimal token set (color roles, spacing, type scale, radius), create the tokens file in the stack's usual place, and fill the doc from it; never invent a full bespoke system.

`$S design builtin` puts the UI guardrail back (unless the team declined it). User approves the design system doc.

## Revisiting it: `/sdlc:setup design`

On a set-up repo, to switch modes, finish a pending impeccable step, or answer a question that was never asked. Clean tree, branch `sdlc/design`, then run this step from section 1 with the current mode (`$S design`) in the question. Switching to builtin: impeccable's files stay (they're the team's); rewrite `<docs>/design-system.md` from the template's builtin form with approval. A `pending` step from setup: `$S step-done design-system` once it's done, and `$S step-done finalize --complete` if setup was waiting on it. One commit, `chore(sdlc): design mode – <mode>` with the reason in its body, then merge the branch locally as in setup's `finalize`, without asking.
