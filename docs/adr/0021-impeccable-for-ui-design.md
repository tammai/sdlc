# ADR 0021: UI design work can go to impeccable; sdlc keeps the gates

- **Status:** Accepted, 2026-10-28. Extends [ADR 0004](0004-ui-follows-the-design-system.md): builtin mode is 0004 unchanged.
- **Deciders:** Tâm Mai. Record: `.sdlc/2026-10-28-l-impeccable-pairing/change.md`.

## Context

sdlc's UI support records a design system, applies it (a rule and a guardrail) and checks it in review, but it doesn't design: generating designs and choosing a visual style are non-goals of [spec 10](../specs/10-ui-design-system.md). The [impeccable](https://github.com/pbakaus/impeccable) skill (Apache 2.0) does exactly that part: product context (`PRODUCT.md`), UX planning (`shape`), building with a quality floor, the design record (`DESIGN.md`), a rule-based detector hook and a report-only `audit`. The user wanted sdlc to hand all design work to impeccable when a team picks it, with today's behaviour as the fallback, and setup to decide which.

## Decision

1. **One config key**, `design`: `builtin` (default, and what a missing key means) or `impeccable`, set with `scaffold.py design <mode>`. Setup's `design-system` step asks for it (a hard stop), recommending from the PRD: impeccable for a user-facing product with no established design system, web or native; builtin for an internal tool on a stock library, a system a design team owns, or an offline or no-third-party-network constraint.
2. **sdlc never installs impeccable** and never edits `PRODUCT.md`, `DESIGN.md` or `.impeccable/`. Chosen but missing: setup gives the install command and records builtin; at run time each step falls back to builtin with one line, and `/sdlc:doctor` warns.
3. **The PRD stays the product source.** impeccable's `init` reads it (it has no seed input but scans the repo's docs); `PRODUCT.md` links back to it, and the PRD wins where they differ.
4. **`DESIGN.md` is the design system** in impeccable mode; `<docs>/design-system.md` points at it. A greenfield project has none until impeccable builds or records a visual world, through its own process (a change that builds a new surface with it, or `/impeccable document`); sdlc never adds a task for it, since with no styles that starts a multi-round design interview. Until then Define maps against the `shape` brief and the existing screens, and the review reports the missing `DESIGN.md` as Medium, not High. (Amended after the live check: the first plan made the first UI feature write it, and a small change deferred it.)
5. **Define uses `shape`; its brief goes into the state file's `## UI mapping`,** since impeccable shows it only in chat.
6. **impeccable's detector hook replaces the `sdlc-ui-hardcoded-values` guardrail** in impeccable mode (`scaffold.py guardrails` lists what setup renders, and setting the mode removes or restores an installed copy), so one issue isn't reported twice.
7. **`sdlc:ui-reviewer` keeps the verdict** (the gate and trust anchor read its `VERDICT:` line); impeccable's `detect` and `audit` are its evidence. `detect` runs through the launcher; `audit` is a skill command a subagent can't invoke, so the reviewer reads its `reference/audit.md` and applies the checks itself (the live check showed the slash-command wording was skipped). `critique` stays out of Review: it asks the user questions and writes files.
8. **The model router lets impeccable's own agents through without a model:** they declare `model: inherit` and impeccable spawns them without one, which the router denied while a feature was active.

## Consequences

- A team that picks impeccable gets its design work inside sdlc's record and gates; one that doesn't sees no change.
- impeccable's new-design flow calls impeccable.style and, unless turned off, sends anonymous telemetry; setup says so and leaves the setting to the user.
- The instruction parts (setup's recommendation, Define with `shape`, the reviewer's evidence, the run-time fallback) aren't tested by the suite; they're checked by a run on a scratch UI repo with impeccable installed.
- Native projects get impeccable's design commands but no detector (it scans web files only).
