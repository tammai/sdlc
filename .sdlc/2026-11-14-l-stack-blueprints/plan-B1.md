# Part plan: 2026-11-14-l-stack-blueprints B1

**Record:** the feature's change file (`scaffold.py paths <feature>` → `change`) · **Backlog:** [backlog.md](backlog.md)

## Tasks

1. **Selection table and warnings in stacks.md** — AC-001 AC-002
   - Files: `skills/setting-up-projects/references/stacks.md`
   - Test first: `Selection.test_choosing_a_stack_table`, `Selection.test_warnings`
   - Then: `## Choosing a stack` (shape, backend language, web, mobile; from `init/selection.json`'s web, mobile,
     backend and shape rules) and `### Warnings` (the shape, language, mobile and deploy warnings; the auth, data
     and tenancy ones wait for B3 and B4). Platform facts checked against current docs, marked "(verify)".
2. **The stack interview** — AC-003
   - Files: `skills/setting-up-projects/references/greenfield.md`, `skills/setting-up-projects/references/monorepo.md`,
     `skills/setting-up-projects/references/workbench.md`
   - Test first: `Selection.test_stack_interview_applies_the_table`
   - Then: three questions (outside API clients, heaviest workload, scale), apply the table, show pick + reason +
     warnings, hard stop unchanged; monorepo and workbench stack steps point to the same table.
3. **ADR 0026 and stale docs**
   - Files: `docs/adr/0026-stack-blueprints-in-setup.md`, `docs/adr/README.md`, `docs/specs/01-setup-upgrade-eject.md`,
     `docs/wiki/Project-setup.md`, `CHANGELOG.md`

## Public Surface

- none

## Sources checked

- Vercel Hobby plan: personal, non-commercial use only (vercel.com/docs/limits/fair-use-guidelines, verified in B1).
- Cloudflare Workers: no long-running processes; background work through Cron Triggers, Queues or Workflows
  (developers.cloudflare.com/workers, verified in B1).
