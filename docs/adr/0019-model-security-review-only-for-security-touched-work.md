# ADR 0019: The model security review runs only for security-touched work

- **Status:** Accepted, 2026-10-27. Amends [ADR 0015](0015-prove-only-where-it-pays.md): the turn-end review no longer runs on every change.
- **Deciders:** Tâm Mai, on a plugin audit's finding.

## Context

ADR 0015 kept the turn-end (Stop) model review on every turn that changed code, up to 3 per turn, and the commit review on every commit made outside an active feature. Inside a feature, the commit gate already skipped changes that aren't security-touched. So every session paid for a top-tier model review, even outside the sdlc flow, which the orchestrator's own rule (security review only on security-touched work) doesn't ask for. SessionStart also built a venv and pip-installed `claude-agent-sdk` (up to 180 s, in the background) on the first session, only to serve those reviews.

## Decision

1. **Turn-end review:** runs only while one sdlc feature is active and its change is security-touched: `Risk: high`, an uncommitted `.sdlc/config.json`, or committed, uncommitted or untracked files since `Base:` in `areas.sensitive` or `areas.migrations` (`sdlc_review_gate.review_wanted`). With no active feature it is skipped. Several active features, a state without `Base:`, or an error: it runs.
2. **Commit review:** with no active feature, skipped and not recorded as reviewed, so the push review still covers those commits. Inside a feature, unchanged (SEC-FR-009).
3. **`SDLC_SECURITY_REVIEW=always`** restores both reviews outside the flow. The `ENABLE_*` switches still turn them off.
4. **Unchanged:** the pattern rules, secret blocking, the push review and Prove's security pass.
5. **The reviewer's SDK is installed lazily:** SessionStart installs nothing (unless `SDLC_SECURITY_REVIEW=always`). The first PostToolUse that finds a security-touched feature and no SDK starts the install in the background (`ensure_agent_sdk.py --now`). Until it's ready, reviews use the single-call fallback.

## Consequences

- Work outside an sdlc feature, and a feature that doesn't touch security, gets no model security review at turn end or on commit. Only the pattern rules cover it, plus the push review.
- The first security-touched feature on a machine starts the SDK install; its first review or two use the fallback reviewer.
- Unmeasured: how many findings the dropped turn-end reviews used to catch.
