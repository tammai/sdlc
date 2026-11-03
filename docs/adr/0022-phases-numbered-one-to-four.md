# ADR 0022: The phases are numbered 1 to 4

- **Status:** Accepted, 2026-11-03. Supersedes the "stage numbers kept (option a)" decision in [ADR 0010](0010-four-phases.md) and the matching line in [ADR 0020](0020-sdlc-2-slim-process-core.md).
- **Deciders:** Tâm Mai, after a teammate asked for a matrix of which steps run on which track and the gaps (1, 4, 5, 8) needed explaining.

## Context

ADR 0010 cut eleven stages to four phases and left each at the number it already had (Define 1, Build 4, Review 5, Ship 8), so no hook had to change and a feature started under the old stages resumed without a migration. Three releases later every number a person meets is a gap: `Current: Stage 4 – Build`, `advance <f> 5`, a "part rests at Stage 4", and a matrix whose sections (1 to 4) don't match the stage numbers. The reason for keeping them (a migration and five hooks) has since gone: users never type or read the number (2.4.3 made updates name the phase), and one constant now holds it.

## Decision

1. **Define 1, Build 2, Review 3, Ship 4**, held in `hooks/sdlc_layout.py` (`DEFINE`, `BUILD`, `REVIEW`, `SHIP`); `state.py`, the hooks, `ship.py`, `autopilot.py` and the CI check read them there.
2. **`Process: 3` marks a state file on the new numbers**, `contract_version` is 3. The hooks and `state.py` act only on `Process: 3`. A `Process: 2` file is refused with `/sdlc:upgrade` as the fix, rather than read with the wrong numbers (a 2.x `Stage 4` is Build, a 3.0 one is Ship).
3. **A migration renumbers instead of waiting.** `state.py migrate` rewrites every `Process: 2` state file (finished features too: the `Current:` line, the Stages checklist, the Gate log), drops the trust anchor's remembered stage for it, and refreshes its snapshot; the `3.0.0-stage-numbers` migration runs it. The mapping is one to one, so unlike 1.x → 2.0 nothing has to be finished first.
4. **The CI check handles both until migrated:** `templates/project/ci/invariants.py` counts Build as 2 and Ship as 4 on `Process: 3`, and as 4 and 8 on anything else.
5. **A backlog part still rests at Build** (now Stage 2); feature close goes on to Review.
6. **`sdlc-stepper` reads `Process: 2` and `3`**, the phase name first and the number by marker as the fallback, so an older or newer stepper than the plugin still draws the bar for a feature in the other form during the move.

## Consequences

- **Breaking, so 3.0.0.** A repo moves with `/sdlc:upgrade`; until then a `Process: 2` feature has no guard and `state.py` refuses it. The steps are in the migration file.
- Old documents (ADRs, the audit, past change files) keep the old numbers; they describe what ran then.
- Hook messages and specs now say Stage 3 for Review. The runtime anchor file (`.sdlc/.work/trust-anchor.json`) is git-ignored, so the migration clears its entry rather than leave a stale stage that would read as a move.
