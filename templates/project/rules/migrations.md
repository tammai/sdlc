---
paths:
{{config.areas.migrations|yaml_list}}
---
<!-- Managed by the sdlc plugin v{{plugin_version}}; regenerated on upgrade. Change paths via "areas.migrations" in .sdlc/config.json. -->
# Schema migrations (sdlc policy)

- Any migration is a hard stop: describe it and get the user's go-ahead before creating or running it.
- Never edit a migration that has been applied anywhere; add a new one.
- Every migration needs a tested rollback (down migration or written restore steps in the feature's `release.md`).
- Prefer additive, backward-compatible steps (add column → backfill → switch reads → drop later) over destructive ones.
- Why it matters: the deploy migrates before it moves traffic, so the running version meets the new schema first, and a rollback moves traffic back without undoing the migration, leaving the new schema under the old code. A migration must work with the app version before it.
- Work touching migrations is at least M track and always gets a security review after the build.
