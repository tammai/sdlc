# Fold the stack-blueprints content into /sdlc:setup

## Why

**Request (verbatim):** Fold the stack-blueprints content into /sdlc:setup. I built a separate repository,
stack-blueprints (version 0.3.0), that holds stack choices and agent guidance organised by layer: web, mobile,
backend, shape, data, auth, deploy. I have decided NOT to ship it as its own tool. Its content moves into this
plugin's setup, and this plugin stays the owner of setup, file ownership, upgrade and eject. […] Five parts, in this
order. Plan all five; build them one at a time. (1) Selection table and the extra `stack` interview questions;
(2) stack sections for Vue, Next.js, Flutter, native iOS, native Android, FastAPI, and reconcile Nuxt, React, Node,
Go; (3) per-stack convention templates rendered through scaffold.py into `.claude/rules/<area>.md` as user-owned
files, rendered when the first feature touches an area; (4) platform references with `## Define checks` for
cloudflare, vercel and docker-compose; (5) constitution proposals per stack, and the scaling roadmap as a knowledge
page template. (Full text: the session's `/sdlc:start` request, 2026-11-14.)

Greenfield setup today proposes from four stacks (Nuxt, React, Node, Go) with no rule for choosing between them,
no mobile or Python option, and no guidance for the agent once code exists. The blueprints hold that knowledge, but
as a separate Node tool that writes `CLAUDE.md` and installs auth, a database and tenant columns up front, which
conflicts with how sdlc sets up (Python only, minimal greenfield, the lock owns every placed file). This change
moves the knowledge in and drops the tool.

Source (read-only): `%USERPROFILE%\Downloads\stack-blueprints\stack-blueprints`, `VERSION` 0.3.0; its
`docs/SDLC-MAPPING.md` says where each piece lands.

**The user's words:** Define answers, 2026-11-14: "Confirm all 7" (decisions 1–7 as proposed); convention rule
ownership: "User-owned + rendered list"; how parts reach `main`: "One growing PR" (a draft PR after B1 on the
feature branch, later parts add commits, one Review and Ship at the end).

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| 1. Node API: `@hono/zod-openapi` when the API has a consumer and a contract, `@hono/zod-validator` otherwise | one default for all | user's proposal (confirmed) |
| 2. Auth libraries are named only in the auth convention template, never in `stacks.md` | naming them per stack | user's proposal (confirmed); auth waits for the feature that needs it |
| 3. A Python section with FastAPI | no Python stack | user's proposal (confirmed) |
| 4. Sections for Vue, Next.js, Flutter, native iOS, native Android | fallback to "ecosystem mainstream" | user's proposal (confirmed) |
| 5. Blueprint `vps-compose` maps to the existing `docker-compose` deploy target | a new target | user's proposal (confirmed); same thing, no config change |
| 6. Auth, database and tenant conventions only when the first feature needs them | scaffold installs them at setup | user's proposal (confirmed); greenfield stays minimal |
| 7. Selection is a table the agent applies; no resolver code | porting `compose.mjs` / a Python resolver | user's proposal (confirmed); setup's other steps work this way, the table has ~10 rules |
| The selection table covers shape, backend language, web and mobile only | the blueprint's data, auth and deploy rules in the table | deploy is setup's existing `deploy` step (ADR 0024); data and auth wait for the feature (6). Their rules and warnings move to part 3 (auth, data templates) and part 4 (platform references) |
| Interview adds three questions: API clients beyond the product's own apps, heaviest workload, first-year scale | the blueprint's `project_name`, `project_description`, `agents`, `platform`, `multi_tenant`, `auth_methods` | the PRD step and host detection cover the first three; the rest decide auth, data and tenancy, which wait for the feature (6) |
| Shape maps onto existing layouts: one deployable → `greenfield.md` (one app); standalone API with clients → two or more apps → the existing monorepo-or-workbench question | a new shape config field | no new config; the layout question already exists (ADR 0025) |
| Convention rule files are named `.claude/rules/<area>.md` from a fixed allowlist of areas (layers, schema, contract, auth, data-access, ui) and never overwrite an existing file | `sdlc-<area>.md`; paths from config | `sdlc-*` names are the plugin's generated rules; brownfield already writes area rules under these names; repo config never names a path (recurring defect) |
| Convention rule files are user-owned: rendered, then forgotten (eject keeps them like area rules); the lock keeps a list of rendered areas with their template and version, so `/sdlc:upgrade` can offer a template change as a diff | `seeded` (upgrade replaces, eject deletes while unedited); untracked with no list | user's answer |
| One branch and one growing PR: a draft PR after B1, later parts add commits in later sessions, one Review and Ship after B5 | a PR per part | user's answer; the parts flow's one Review and Ship |
| Templates don't restate `sdlc-ui.md`, `sdlc-sensitive.md`, `sdlc-migrations.md`; the blueprint's security checklist and definition of done fold into those, not new files | parallel checklists | the user's constraint; one source per rule |
| "First feature touches an area" is detected in the orchestrator's Define (`flow.md`, `s-track.md`): the change's files match an area of the approved stack that has no rule file → the plan proposes rendering it | detection in a hook or at setup | Define already reads the touched code and writes the plan; no new hook |
| Scaling roadmap: a knowledge page template (`templates/knowledge/scaling-roadmap.md`), written by setup with the approved stack's rows, user-owned, linked from `knowledge/index.md`; a met trigger is a signal to size a change as L | rows in `CLAUDE.md` or a generated doc | knowledge tier 3 is where the plugin keeps docs like this (deploy runbook precedent) |
| Every library API in a template or section is checked against current documentation in the part that adds it; what can't be confirmed is dropped | carrying blueprint samples as written | the user's constraint: samples were never executed |
| ADR 0026 records the decision in part 1's PR | writing it in part 5 | the decision is made now |

**Proposals not asked for:** None.

## Acceptance criteria

- **AC-001** (B1) Given `references/stacks.md`, then before the first stack section a `## Choosing a stack` table
  says how to pick: one deployable (Hono mounted in Nuxt or Next.js) only when there is one web client in Nuxt or
  Next.js, a TypeScript backend, no mobile app, no outside API clients, internal or small scale and CRUD work, else a
  standalone API with clients; the backend language the user names wins, else Go for CPU-heavy or realtime work or
  high load, else TypeScript; Python when the user names it; Nuxt the default web app; no mobile app unless asked,
  Flutter for both platforms from one codebase.
- **AC-002** (B1) Given `stacks.md`, then a warnings list names when to flag a pick before approval: TypeScript or
  Python asked for heavy or high-load work, Go for a small CRUD product, no client at all, two native apps, iOS
  needing a macOS runner, Cloudflare Workers with background jobs, Vercel with a Go or Python API, Vercel's plan for
  commercial use, and the operations a VPS leaves to the team.
- **AC-003** (B1) Given greenfield setup's `stack` step, then it asks whether anything outside the product calls the
  API, the heaviest workload and the first-year scale (each with a suggested answer), applies the selection table,
  shows each pick with its reason and any warning, and the proposal stays a hard stop the user approves; the
  monorepo and workbench stack steps apply the same table.
- **AC-004** (B2) Given `stacks.md`, then it has sections for Vue (without Nuxt), Next.js, Flutter, native iOS,
  native Android and FastAPI, each with pieces, generator and the five commands.
- **AC-005** (B2) Given `stacks.md`, then the Node section uses `@hono/zod-openapi` when the API has a consumer and
  a contract and `@hono/zod-validator` otherwise; the Nuxt and Next.js sections cover the one-deployable shape; no
  section names an auth library.
- **AC-006** (B2) Given a package whose stack is Flutter, Swift or Kotlin, when `builtin:ci` renders, then the
  workflow sets up that toolchain (Swift on a macOS runner) instead of a `# TODO` line.
- **AC-007** (B3) Given an approved stack, when `scaffold.py conventions` renders one area for a package, then
  `.claude/rules/<area>.md` holds that stack's convention with `paths:` from the package path and is recorded per
  the ownership decision; an area or stack outside the allowlist, or an existing rule file, is refused with the
  allowed names and nothing is written.
- **AC-008** (B3) Given setup, then no convention is rendered; given a change whose files first touch an area of the
  approved stack with no rule file, Define's plan proposes rendering it.
- **AC-009** (B3, B2) Every library API named in a stack section or convention template was checked against current
  documentation, with the source noted in the part's plan; what couldn't be confirmed is not in the repo.
- **AC-010** (B4) Given `deploy.target` `cloudflare`, `vercel` or `docker-compose`, when `brief.py` runs, then it
  prints that platform's `## Define checks`.
- **AC-011** (B5) Given an approved stack, then `sdlc:project-constitution` proposes that stack's principles from a
  per-stack reference, and setup writes the scaling roadmap page from `templates/knowledge/scaling-roadmap.md` with
  the stack's triggers, linked from `knowledge/index.md`.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_stack_blueprints.py › Selection.test_choosing_a_stack_table | `py -3.10 -m unittest discover -s tests -t tests -p test_stack_blueprints.py -k test_choosing_a_stack_table` |
| AC-002 | tests/test_stack_blueprints.py › Selection.test_warnings | `py -3.10 -m unittest discover -s tests -t tests -p test_stack_blueprints.py -k test_warnings` |
| AC-003 | tests/test_stack_blueprints.py › Selection.test_stack_interview_applies_the_table | `py -3.10 -m unittest discover -s tests -t tests -p test_stack_blueprints.py -k test_stack_interview_applies_the_table` |
| AC-004 | tests/test_stack_blueprints.py › StackSections.test_new_sections | (B2) |
| AC-005 | tests/test_stack_blueprints.py › StackSections.test_reconciled_sections | (B2) |
| AC-006 | tests/test_stack_blueprints.py › StackSections.test_ci_sets_up_mobile_toolchains | (B2) |
| AC-007 | tests/test_stack_blueprints.py › Conventions.test_render_one_area | (B3) |
| AC-008 | tests/test_stack_blueprints.py › Conventions.test_rendered_on_first_touch_not_at_setup | (B3) |
| AC-009 | manual | each API is checked against its docs while writing; a test can't read upstream docs |
| AC-010 | tests/test_stack_blueprints.py › Platforms.test_define_checks_per_target | (B4) |
| AC-011 | tests/test_stack_blueprints.py › Constitution.test_stack_principles_and_roadmap | (B5) |

The exact Run commands for B2–B5 are written when each part starts (its plan), in the same form as AC-001.


## Must never break

- Setup never writes `CLAUDE.md`, and installs nothing "for later": no auth, database or tenant setup at setup.
- The plugin needs Python only; nothing here adds a Node dependency.
- An existing `.claude/rules/<area>.md` is never overwritten, and no convention file takes an `sdlc-` name.
- Every file the plugin places is tracked so `/sdlc:upgrade` and `/sdlc:eject` handle it per its class.
- A file path never comes from repo config: areas and stacks come from the plugin's allowlist; a package path feeds
  only `paths:` frontmatter.
- The existing stack sections keep pieces, generator and five commands (`PreferredStacks` still passes).
- The blueprints folder is never edited.

## Failure modes

- Untrusted input naming a file (an area or stack name, a package path) → AC-007.
- Library APIs written from memory and never executed → AC-009.
- Platform facts that change with pricing (Vercel's plan, Workers limits) → marked "(verify)" as in
  `gcp-cloud-run.md`; checked in the part that writes them (AC-002, AC-010).
- A rule template restating a plugin rule that later changes → must-never-break above (one source per rule).
- No concurrency, persisted-data or deploy edges: the change is reference text plus one render command.

## Out of scope

- `compose.mjs`, `init/PROTOCOL.md`, the generated `CLAUDE.md`, `docs/SCAFFOLD.md`, the two checklists (user's
  constraint). The blueprint's scaffold steps are candidate first features for `/sdlc:start`, not setup steps.
- A resolver in code (decision 7).
- The blueprint's `platform`, `multi_tenant` and `auth_methods` questions at setup (they wait for the feature).
- Data-layer entries (`neon`, `cloud-sql`, `supabase`, `self-hosted`) as stack sections: their driver notes go to
  the platform references (B4) and the data convention template (B3).

