# Pair sdlc with impeccable for UI design work

## Why

**Request (verbatim):** "i want to use this plugin collab with sdlc to handle the uiux design parts" (https://github.com/pbakaus/impeccable) · "can we rewrite the sdlc to delegate all design job to impeccable when user choose using it alongside with sdlc and a fallback solution when they choose not using? and the last concern is which kind of product need impeccable? the setup step need to decide should pair with it or not." · "run the define stage for impaccable pairing and stop"

sdlc owns the process: gates, the record, team consistency. Its UI spec (`docs/specs/10-ui-design-system.md`) lists "generating designs, mockups … choosing a visual style" as non-goals. Today UI work gets a design-system file, a policy rule, one guardrail and `sdlc:ui-reviewer`. impeccable (Apache 2.0, v4.8.0) does exactly the part sdlc leaves out: product context (`PRODUCT.md`), UX planning (`shape`), building with a quality floor, the design record (`DESIGN.md`), a rule-based detector and a report-only `audit`. Teams that choose it get impeccable's design work inside sdlc's process. Teams that don't keep today's behaviour unchanged. Setup decides which, from the PRD that 2.0.0 now writes.

**The user's words:** sdlc keeps the process and hands all design work to impeccable when the user picks it; when they don't, a fallback (today's behaviour). Setup decides whether to pair. The PRD step (2.0.0) was built first so impeccable has a foundation: "when pairing with impeccable sdlc has a foundation structure to pair smoothly". A new PRD goes to `<docs>/prd.md`.

**What impeccable does (read from its skill files, v4.8.0, not its README):**
- `init` writes `PRODUCT.md`, scans the repo's product docs first, and needs one real answer round. It takes no seed file.
- `shape` interviews, presents a brief in chat and stops; it writes no code and no file.
- On a new visual world, `DESIGN.md` is written **after** the build by its documenter subagent. `document` records an existing one.
- `audit` reports only ("Don't fix issues"). `critique` writes `.impeccable/critique/*.md`, asks the user about intent and may start a live server.
- The detector hook runs after UI edits and never blocks. It also runs a deep pass on Stop. It scans web file types only.
- iOS and Android are supported by the design commands; the detector doesn't cover them.
- Commands run through a launcher next to its `SKILL.md` (`scripts/impeccable`, `.cmd` on Windows); the engine is a binary downloaded on first run.
- New-work fetches directions from impeccable.style and, unless opted out, sends an anonymous record of the choice.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| One config key, `design: "impeccable" \| "builtin"` in `.sdlc/config.json`; absent means `builtin`. Read and set with `scaffold.py design [<mode>]` | A third `detect-only` mode | Two modes are what was asked; detect-only is listed under proposals |
| Setup's `design-system` step asks which mode (hard stop) with a recommendation read from the PRD: **impeccable** for user-facing products (PRD audience consumer or business) with no established design system, web or native; **builtin** for internal tools on a stock component library, an existing system owned by a design team, or a PRD constraint of offline or no third-party network calls | Native → builtin | impeccable supports iOS and Android; only its detector is web-only, which the setup message says |
| sdlc never installs impeccable. Chosen but not installed: setup prints the install command (`npx impeccable install`, or `/plugin marketplace add pbakaus/impeccable`) and records `builtin` until it's installed, then the user re-runs the step | sdlc installing it | Setup never installs tools (hard stop list); the engine is a downloaded binary that runs unsandboxed |
| Product facts: `<docs>/prd.md` stays the source. In impeccable mode setup runs `init`, telling it to read the PRD; `PRODUCT.md`'s first line links to the PRD, and where they disagree the PRD wins | sdlc writing `PRODUCT.md` itself; seeding `init` | `PRODUCT.md` has impeccable's own schema and an answer-round gate; `init` has no seed input but scans product docs anyway |
| The design record: `<docs>/design-system.md` becomes a short pointer to `DESIGN.md` (and `.impeccable/design.json`). An existing UI: setup runs `document`, so `DESIGN.md` exists from the start. **Greenfield (no `DESIGN.md` until the first world is built):** Define maps screens against the `shape` brief, the first UI feature's Build ends with impeccable's documenter writing `DESIGN.md`, and on that feature the reviewer doesn't raise "no design system" as High | Requiring `DESIGN.md` before the first build | impeccable writes it from the built world on purpose; demanding it first fights its method |
| Define in impeccable mode: `ui-work.md` sends UI changes through `/impeccable shape`; the confirmed brief is copied into the state file's `## UI mapping`, and its states and copy into the ACs | Leaving the brief in chat | Nothing stays in the agent's head: a fresh session builds from the files |
| Build in impeccable mode: UI work goes through impeccable's commands, and its detector hook replaces the `sdlc-ui-hardcoded-values` guardrail, which isn't rendered in impeccable mode (switching mode adds or removes it) | Keeping both | Same issue reported twice on every edit |
| Review: the UI row still fires on `areas.ui` and `sdlc:ui-reviewer` still writes the verdict on opus. In impeccable mode it reviews against `DESIGN.md`, runs impeccable `detect` on the changed UI files and `audit` (report-only) as evidence, through the launcher it finds | Replacing ui-reviewer with `audit`; running `critique` in Review | The gate needs `VERDICT:` lines and the trust anchor; `critique` is interactive and writes files |
| The model router lets impeccable's own subagents (`impeccable-*`) through without a named model; every other rule stays | Asking impeccable to name models | Its agents declare `model: inherit` in frontmatter and impeccable spawns them without a model, so the router denies them today whenever an sdlc feature is active |
| Run-time fallback: impeccable mode but impeccable missing → the step works as builtin and says so in one line; `/sdlc:doctor` warns | Failing the step | A teammate without impeccable must still be able to work |
| impeccable's network call and default telemetry are named in setup's message with the opt-outs (`IMPECCABLE_NO_TELEMETRY=1`, `DO_NOT_TRACK=1`); sdlc changes no impeccable setting | Turning telemetry off for the user | It's the user's choice and impeccable's config |

**Proposals not asked for:** a `detect-only` mode (impeccable's detector in Review with no design commands, for internal tools); a doctor check that `PRODUCT.md` is older than the PRD. Dropped unless kept.

## Acceptance criteria

- **AC-001** Given a set-up repo, when `scaffold.py design impeccable` runs, then config records `"design": "impeccable"` and `scaffold.py design` prints it; with no key it prints `builtin`; any other value is refused with exit 2 and config unchanged.
- **AC-002** Given `design` is `impeccable`, when setup or upgrade lists the guardrails to render, then `sdlc-ui-hardcoded-values` isn't among them, and switching back to `builtin` lists it again.
- **AC-003** Given an active feature, when a subagent dispatch names `impeccable-documenter` (or any `impeccable-*` agent) with no model, then the model router allows it; a dispatch of any other agent with no model is still denied.
- **AC-004** Given `design` is `impeccable` and no impeccable skill is installed (none in the project's or user's agent skill folders or plugins), when `/sdlc:doctor` runs, then it warns and names the install command; with impeccable installed, or `design` builtin, it doesn't.
- **AC-005** Given a UI project, when setup reaches `design-system`, then it recommends a mode from the PRD per the Decisions table, stops for the user's choice, records it, and in impeccable mode runs `init` (reading the PRD) and, on existing UI, `document`, and writes `design-system.md` as a pointer to `DESIGN.md`.
- **AC-006** Given impeccable mode and a UI change, when Define runs, then it goes through `shape` and the confirmed brief is in the state file's `## UI mapping`, with the brief's states and copy in the ACs.
- **AC-007** Given impeccable mode and a diff touching `areas.ui`, when Review runs the UI review, then `sdlc:ui-reviewer` reviews against `DESIGN.md`, cites `detect` and `audit` output, ends with a `VERDICT:` line, and doesn't raise "no design system" as High on the feature that builds the first visual world.
- **AC-008** Given impeccable mode on a machine without impeccable, when a Define, Build or Review step would call it, then the step runs the builtin path and says so in one line.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_scaffold.py › test_design_mode_records_and_refuses_unknown | `py -3.10 -m unittest test_scaffold.ScaffoldTest.test_design_mode_records_and_refuses_unknown` (from `tests/`) |
| AC-002 | tests/test_scaffold.py › test_impeccable_mode_drops_ui_guardrail | `py -3.10 -m unittest test_scaffold.ScaffoldTest.test_impeccable_mode_drops_ui_guardrail` (from `tests/`) |
| AC-003 | tests/test_model_router.py › test_impeccable_agents_pass_without_model | `py -3.10 -m unittest test_model_router.ModelRouterTest.test_impeccable_agents_pass_without_model` (from `tests/`) |
| AC-004 | tests/test_doctor.py › test_impeccable_mode_without_impeccable_warns | `py -3.10 -m unittest test_doctor.DoctorTest.test_impeccable_mode_without_impeccable_warns` (from `tests/`) |
| AC-005 | manual | Instruction text in the setup skill; checked with one headless setup on a scratch UI repo with impeccable installed |
| AC-006 | manual | Instruction text in `ui-work.md`; checked in the same scratch run, one M UI change through Define |
| AC-007 | manual | Agent instructions; checked by the same change's Review in the scratch run |
| AC-008 | manual | Instruction text; checked by repeating the scratch Define with impeccable uninstalled |


## Must never break

- With `design` absent or `builtin`, setup, Define, Build and Review behave exactly as in 2.0.0: same guardrails rendered, same reviewer brief.
- sdlc never installs impeccable, never edits `.impeccable/config*.json`, and never overwrites `PRODUCT.md` or `DESIGN.md`.
- The model router's other rules (no haiku, fable opt-in, reviews on opus) are unchanged.
- The review gate still comes from `sdlc:ui-reviewer`'s `VERDICT:` line; impeccable output is evidence, never the verdict.

## Failure modes

- impeccable missing or its launcher failing at run time → AC-008.
- impeccable's subagents dispatched during an active feature → AC-003.
- Two hooks on one UI edit (impeccable's detector and sdlc's guardrail) → AC-002.
- `DESIGN.md` absent on a greenfield project's first UI feature → AC-007.
- Untrusted input: impeccable's engine is third-party code run unsandboxed → must-never-break (sdlc never installs it; the user chooses).
- Concurrent use, scale, persisted-data migration, crash mid-write: the only write is one config key through `scaffold.py`'s existing writer; none new apply.

## Out of scope

- Building or bundling any of impeccable; copying its commands or skills into sdlc.
- `detect-only` mode and the `PRODUCT.md` staleness check (proposals above, unless kept).
- impeccable's live mode, `critique` in Review, and its telemetry settings.
- Changing what builtin mode does.
- Native (iOS/Android) detector coverage: impeccable has none; the design commands still apply.
