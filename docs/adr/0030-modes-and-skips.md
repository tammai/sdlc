# ADR 0030: A repo chooses full or advisory mode, and a full repo may skip named steps

- **Status:** Accepted, 2026-11-23. Records: `.sdlc/2026-11-23-l-configurable-stages/change.md`. Related: [0019](0019-model-security-review-only-for-security-touched-work.md), [0029](0029-configurable-review-round-cap.md).
- **Deciders:** Tâm Mai.

## Context

Every set-up repo got the whole workflow: the security review whenever it fired, the push/PR/CI step at every Ship, and the hooks and guardrails in every session. Two kinds of team didn't fit:
- teams whose own release path does a step (a CI security scan, shipping without PRs);
- teams whose own workflow would conflict with sdlc's gates, but who still want its skills and agents.

Their only way out was "skip" on every change, recorded as a deviation, or not using sdlc at all.

## Decision

1. **`"mode": "full" | "advisory"`** in `.sdlc/config.json`, set by `scaffold.py mode` (setup's first question, `/sdlc:setup mode …`).
   - An unknown value, or a config that can't be read, counts as `full`.
   - **Advisory:** every sdlc hook returns silently, through one check at its entry (`sdlc_scopes.advisory`). That covers the hookify rules and the security warnings and reviews too. Exceptions:
     - a workbench's read-only guard and watch, which protect other teams' repos;
     - `SDLC_SECURITY_REVIEW=always`, which still forces the security reviews;
     - the session status line, which names the mode and gates nothing.
   - The orchestrator doesn't run its flow in advisory: it does what is asked with the skills and agents.
   - Advisory setup renders no guardrails, CI, workflow rules or `AGENTS.md` block.
2. **`"skip"`** (full mode only) is a list of `security-review`, `code-review`, `ui-review` and `pr`, set by `scaffold.py skip`.
   - A skipped review doesn't run when its row fires, and `## Review` says it was skipped by config.
   - `security-review` also turns off the security hooks' commit and turn-end reviews for features; the push review and pattern warnings stay.
   - `pr` ends Ship after the local commit.
   - Define, the red step, the test lock and verify are never skippable.
3. **A relaxing change counts only once the user accepts it.** The hooks honour `advisory` or a skip only when the trust anchor's record of what the user accepted says so; with no readable record, HEAD's committed config decides (a team's choice on a fresh clone). Every reader, the trust anchor included, takes the mode from one place (`sdlc_scopes.gate_root`: from the session's folder, the outermost folder holding `.sdlc` up to its git top level; for a workbench app repo, the workbench); `scaffold.py mode`/`skip` refuse to write anywhere the session's hooks don't read, never a nested folder's or an app repo's own config.
4. **A relaxing change reaches the user.** The trust anchor keeps a repo-level anchor of the mode and the skips.
   - A move to advisory, or a newly skipped step, is a notice at the next turn end, even in advisory mode. The user's reply accepts what the notice showed, not whatever config says by then; a damaged record is said and reset to the committed config.
   - A move toward more checks is taken silently.
   - Unlike [0029](0029-configurable-review-round-cap.md)'s ratchet, acceptance isn't tied to a typed prompt: the record of what the user accepted is local (`.sdlc/.work/trust-anchor.json`), and with none, HEAD's committed config decides, so a team's committed choice holds on every teammate's clone.

## Consequences

- One small surface (two keys, four step names) instead of a switch per hook. Combinations that undo the plugin's guarantees (no tests, no record) can't be configured.
- An agent can still write these keys by hand. The trust anchor makes that visible, not impossible, as for the baseline and commands (docs/wiki/Limitations.md).
- Turning advisory on in a set-up repo silences the guardrails already installed (CI's own checks still run in CI), but doesn't remove their files; `scaffold.py mode` switches `.claude/rules/sdlc.md` between the workflow rule and the advisory note while it is unedited.
