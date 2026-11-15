# Part plan: 2026-11-14-l-stack-blueprints B5

**Record:** the feature's change file (`scaffold.py paths <feature>` → `change`) · **Backlog:** [backlog.md](backlog.md)

## Tasks

1. **Stack principles for the constitution** — AC-011
   - Files: `skills/project-constitution/references/stack-principles.md`, `skills/project-constitution/SKILL.md`,
     `tests/test_stack_blueprints.py`
   - Test first: `Constitution.test_stack_principles_and_roadmap`
   - Then: one section for every stack and one for every stack in common, keyed by the conventions allowlist
     (`scaffold.py` `CONVENTION_STACKS`), from the blueprint's `rules-always` / `rules-never` blocks only; the
     skill proposes the sections of the stacks in use, named from the manifest as Define does (flow.md).
2. **Scaling roadmap page** — AC-011
   - Files: `templates/knowledge/scaling-roadmap.md`, `skills/setting-up-projects/SKILL.md`,
     `skills/setting-up-projects/references/greenfield.md`
   - Then: a knowledge page template with the table (step, trigger, what changes, what stays) and candidate rows
     per stack from the blueprint's `roadmap` rows; setup's `knowledge` step writes it on greenfield with the
     approved stack's rows, links it from `knowledge/index.md`; the `deploy` step adds the hosting rows.

## Public Surface

- none

## Sources (2026-11-14)

- Principles: blueprint `modules/*/*.md` `rules-always` / `rules-never` blocks; roadmap rows: `catalog/*/*/entry.json`
  `roadmap` and `catalog/core/base/entry.json` `when`.
- Not carried: `checklist-security` and `checklist-done` (verify.py, `sdlc-sensitive.md` and review hold those);
  auth-library rules (Better Auth, Supabase; decisions 2 and 6); tenancy rules (`tenant_id`, RLS; they wait for the
  feature: the roadmap's multi-tenancy row stands in); UI token rules (`sdlc-ui.md` and the hardcoded-values
  guardrail say it); the secrets-in-logs rule (`sdlc-sensitive.md`); API names (`createRoute`, `operation_id`,
  `MaterialTheme`: B3's checked conventions hold them, so no library API is named here and AC-009 has nothing new
  to check); the auth roadmap rows (auth isn't chosen at setup).
- Next.js "no route handlers for business data" keeps an exception for the one-deployable bridge route (B2).
