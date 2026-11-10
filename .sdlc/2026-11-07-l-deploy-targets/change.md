# Deploy targets in setup and /sdlc:deploy

## Why

**Request (verbatim, from the missue session on the user's behalf):** Teach setup and /sdlc:deploy about deploy targets, starting with GCP Cloud Run. (1) setup deploy step — ask target (none yet / Docker compose / GCP Cloud Run / Vercel / Cloudflare / other) and environments, record in .sdlc/config.json as "deploy": {"target": ..., "environments": [{"name","routine"}]}, seed knowledge/runbooks/deploy.md from a new template (environments, deploy command, smoke test, rollback, logs); (2) /sdlc:deploy reads config.deploy + runbook, only routine envs skip the hard go-ahead stop, takes smoke test/rollback from runbook, writes first-deploy facts back; (3) platform reference skills/orchestrator/references/platforms/gcp-cloud-run.md read by Define when deploy.target matches; (4) templates: change template failure modes gain "deploy and rollback"; templates/project/rules/migrations.md explains why additive matters; constitution template gets optional Release principle; (5) integrations.md hosting row adds GCP. BUG: config.defaults.json areas.migrations misses Drizzle's drizzle/ folder; also check whether a rule re-rendered at a newer version stamp than the repo scaffold confuses upgrade/doctor. Ship as a PR.

Today `/sdlc:deploy` only says "use the project's own deploy path" and setup never asks how a project deploys, so each project rediscovers the same platform traps by hand. missue (Thoi) moving to Cloud Run + Cloud SQL hit a set of them (`/Users/tammai/vibe-coding/missue/docs/sdlc/changes/2026-11-07-m-cloud-run-deploy.md`, the worked example): in-process rate limits under scale to zero, Cloud SQL connection caps, the socket URL form, trailing newlines in secrets, the `X-Forwarded-For` shape, domain-mapping regions, Firebase Hosting dropping cookies. Most of that is generic: recorded once in the plugin, every project on that target sees it in Define as failure modes, and `/sdlc:deploy` follows a runbook instead of improvising. Separately, Drizzle projects never got the migrations rule, because the default globs miss `drizzle/`.

**The user's words:** None asked here. The user approved the direction in the missue session; this session sized and settled the details (Decisions).

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| Config shape `deploy: {target, environments: [{name, routine}], runbook}`; `runbook` defaults to `knowledge/runbooks/deploy.md` | A fixed runbook path | missue already has `knowledge/runbooks/gcp-deploy.md`; a path keeps it without a rename. |
| `scaffold.py deploy [--target T] [--env NAME[:routine] …] [--runbook PATH]` records it and prints it; targets `none`, `docker-compose`, `gcp-cloud-run`, `vercel`, `cloudflare`, `other`; anything else refused | Setup editing `.sdlc/config.json` by hand | Same pattern as `prd` and `design`: the script keeps the record exact and validates it. |
| Setup gets a `deploy` common step after `knowledge`, a hard stop (target and environments are the user's call); it seeds the runbook from `templates/knowledge/deploy-runbook.md` unless the path exists, user-owned from then on. `none` records the target and seeds nothing | Asking only in greenfield | Brownfield repos are the ones that already deploy somewhere. |
| Existing repos get it through upgrade: `migrations/3.6.0-deploy-target.md` runs the same step | Only new setups | missue picks this up with `/sdlc:upgrade`. 3.6.0 is the next minor release (3.3.0 to 3.5.0 shipped while this was in Review). |
| `brief.py` prints the platform reference's `## Define checks` section (and its path) when `deploy.target` names a file in `references/platforms/`; the rest of the file is read on demand | Printing the whole file every Define; a "read it when relevant" line only | The checks are the part that must show up as failure modes on every change; the setup detail matters only when touching the deploy itself. The target is checked against `[a-z0-9-]+` before it names a file: repo config is untrusted (gotcha `repo-config-is-untrusted`). |
| `/sdlc:deploy`: with `config.deploy`, only an environment marked `routine` skips the go-ahead; an unlisted environment needs it. Smoke test, rollback and logs come from the runbook; a fact learnt on a deploy (a header shape, a URL) is written to the runbook's `## Learnt on deploys` and named in the report. Without `config.deploy` the current rule stands | Stopping when there is no config | Repos set up before 3.6.0 keep working until they upgrade. |
| Default `areas.migrations` adds `**/drizzle/**`, `**/alembic/**` and `**/db/migration/**` (Flyway) | Detecting the ORM in setup | A default glob costs nothing and also fixes repos already set up, on their next upgrade (the rule is regenerated). Prisma, Knex, TypeORM, Django, Rails and Supabase already land in `migrations/` or `migrate/`. |
| Version stamp: no change. A rule re-rendered by a newer plugin carries that plugin's version in its comment, but nothing reads that comment: `status`'s drift and doctor's scaffold check read `scaffold_version` in the lock, and `render` records the new file's hash, so the file stays `unchanged` and the next upgrade regenerates it as usual | A fix | Checked in `scripts/scaffold.py` (`cmd_status`, `cmd_render`) and `scripts/doctor.py`; no failure to fix. |

**Proposals not asked for:** None.

## Acceptance criteria

- **AC-001** Given the plugin's default `areas.migrations`, then it matches `drizzle/0001_init.sql`, `alembic/versions/1a2b_add.py` and `src/main/resources/db/migration/V1__init.sql`, and still matches `prisma/migrations/x/migration.sql` and `db/migrate/001.rb`. (Today the first three miss: the bug.)
- **AC-002** `scaffold.py deploy --target gcp-cloud-run --env dev:routine --env prod` writes `deploy: {target: gcp-cloud-run, environments: [{name: dev, routine: true}, {name: prod, routine: false}], runbook: knowledge/runbooks/deploy.md}` to `.sdlc/config.json` and prints it; `--runbook <path>` records that path; with no flags it prints the recorded value (or `target: null` when none). An unknown target or an empty environment name exits 2 and changes nothing.
- **AC-003** `templates/knowledge/deploy-runbook.md` exists with the sections Environments, Deploy, Smoke test, Rollback, Logs and Learnt on deploys.
- **AC-004** Setup's `SKILL.md` has a `deploy` step that runs `$S deploy` and seeds the runbook from that template, and lists the deploy target among its hard stops; `migrations/3.6.0-deploy-target.md` exists (version 3.6.0) and runs the same step for a set-up repo.
- **AC-005** `commands/deploy.md` reads `config.deploy` and the runbook: only an environment with `routine: true` skips the go-ahead, the smoke test and rollback come from the runbook, and facts learnt on a deploy are written to its `## Learnt on deploys`.
- **AC-006** Given `deploy.target: gcp-cloud-run`, `brief.py` prints a `platform: gcp-cloud-run` section with the reference's Define checks and its path; given `none`, an unknown target, or a target like `../x`, it prints no platform section.
- **AC-007** `skills/orchestrator/references/platforms/gcp-cloud-run.md` has a `## Define checks` section covering state in process memory, Cloud SQL connections against `--max-instances`, the `/cloudsql/` socket URL, Workload Identity Federation, `printf '%s'` for secrets, the `X-Forwarded-For` shape, Firebase Hosting's `__session` cookie, and rollback by `update-traffic` not undoing migrations.
- **AC-008** The change template's failure modes and flow.md's list name "deploy and rollback"; the migrations rule says the deploy migrates before it moves traffic and a rollback leaves the new schema under the old code; the constitution template has an optional Release principle (deploy script only, explicit go-ahead, secrets in the platform's store).
- **AC-009** `integrations.md`'s hosting row names GCP (Cloud Run, Cloud SQL, Firebase).

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_deploy_targets.py › test_default_migration_globs_cover_drizzle_alembic_flyway | `python3.10 -m unittest discover -s tests -t tests -p test_deploy_targets.py -k test_default_migration_globs_cover_drizzle_alembic_flyway` |
| AC-002 | tests/test_scaffold.py › test_deploy_records_target_environments_and_runbook | `python3.10 -m unittest discover -s tests -t tests -p test_scaffold.py -k test_deploy_records_target_environments_and_runbook` |
| AC-003 | tests/test_deploy_targets.py › test_runbook_template_has_its_sections | `python3.10 -m unittest discover -s tests -t tests -p test_deploy_targets.py -k test_runbook_template_has_its_sections` |
| AC-004 | tests/test_deploy_targets.py › test_setup_and_upgrade_run_the_deploy_step | `python3.10 -m unittest discover -s tests -t tests -p test_deploy_targets.py -k test_setup_and_upgrade_run_the_deploy_step` |
| AC-005 | tests/test_deploy_targets.py › test_deploy_command_follows_config_and_runbook | `python3.10 -m unittest discover -s tests -t tests -p test_deploy_targets.py -k test_deploy_command_follows_config_and_runbook` |
| AC-006 | tests/test_brief.py › test_prints_platform_checks_only_for_a_known_target | `python3.10 -m unittest discover -s tests -t tests -p test_brief.py -k test_prints_platform_checks_only_for_a_known_target` |
| AC-007 | tests/test_deploy_targets.py › test_cloud_run_reference_has_define_checks | `python3.10 -m unittest discover -s tests -t tests -p test_deploy_targets.py -k test_cloud_run_reference_has_define_checks` |
| AC-008 | tests/test_deploy_targets.py › test_templates_carry_deploy_and_rollback | `python3.10 -m unittest discover -s tests -t tests -p test_deploy_targets.py -k test_templates_carry_deploy_and_rollback` |
| AC-009 | tests/test_deploy_targets.py › test_integrations_hosting_row_names_gcp | `python3.10 -m unittest discover -s tests -t tests -p test_deploy_targets.py -k test_integrations_hosting_row_names_gcp` |

## Must never break

- A repo with no `deploy` key behaves as today: `/sdlc:deploy` falls back to the project's own path, and `brief.py` prints what it printed before.
- A production deploy or DB migration always needs the explicit go-ahead; nothing in the config can mark production routine by default (`routine` is false unless the user says `:routine`).
- `setting-up-projects/SKILL.md` stays under 20,000 characters.
- An existing runbook, constitution or knowledge file is never overwritten: setup seeds the runbook only when its path doesn't exist.

## Failure modes

- **Untrusted input:** `deploy.target` comes from repo config and names a file → `brief.py` accepts only `[a-z0-9-]+` that names an existing platform file (AC-006); `scaffold.py` refuses unknown targets (AC-002).
- **Persisted data:** a new optional config key; old configs without it keep working (must-never-break 1).
- **Deploy and rollback** (the new failure mode itself): no product code here; the plugin only adds text and config.

## Out of scope

- Platform references for targets other than GCP Cloud Run (the target values exist; their files can come later).
- Running or generating any deploy script, Terraform or CI deploy job; `/sdlc:deploy` still never invents a deploy path.
- Detecting the ORM in setup (the default globs cover it).
- The release itself (version bump to 3.6.0, tag): a separate request.

## Review

- **Recommended and chosen:** code (default depth) and security, because L with a Public Surface (the `scaffold.py deploy` command, the `deploy` config key), and untrusted repo config (`deploy.target`, `deploy.runbook`) reaches a file path, with the diff touching `migrations/`; chosen by the trigger list (L, self-chosen).
- **Verdicts:**
  - Round 1: code-reviewer → `.sdlc/.work/findings/2026-11-07-l-deploy-targets/code-reviewer-r1.md` → FAIL (M1, M2); security → `security-r1.md` → FAIL (S-001, S-002).
  - Round 2, the closing check, after the rebase onto de61977: code-reviewer → `code-reviewer-r2.md` → PASS; security → `security-r2.md` → PASS. Both found the rebase dropped nothing from either side.
- **Fixed:**
  - S-001 (high): a committed config could mark production routine, so `/sdlc:deploy` skipped its go-ahead. Production names can't be routine (exit 2), a stored routine production is set back and listed under `invalid`, and `commands/deploy.md` keeps production's go-ahead whatever `routine` says. Tests: test_scaffold › test_deploy_never_marks_production_routine; test_deploy_targets › test_deploy_command_follows_config_and_runbook.
  - S-002 / M2: stored `deploy.target` and `deploy.runbook` were printed unchecked, then read and written by `/sdlc:deploy`. `stored_deploy` checks every value on each read, and `deploy.md` uses only what it prints. Test: test_scaffold › test_deploy_checks_the_runbook_flag_and_every_stored_value.
  - M1: `--runbook` outside the repo exited 1 through `rel()` and `--runbook ""` recorded `.`. Now `runbook_path` refuses both with exit 2, symlinks resolved (same test).
  - L1 (r1): `/sdlc:setup deploy` didn't cover `setup: none`. F1 (r1): `brief.py` docstring wrap.
  - Round 2, its medium and low bugs, fixed test-first and closed by verify:
    - Code M1: `/sdlc:setup deploy` never reached the step, because `commands/setup.md` handled only `design`. It takes `deploy` now (test_deploy_targets › test_setup_and_upgrade_run_the_deploy_step).
    - Code M2 / security M-2: production was matched by exact name, so `prod-eu:routine` passed. Now any name with a `prod`, `production`, `live` or `prd` part is production, and names are plain ASCII (test_scaffold › test_deploy_production_is_any_name_with_a_production_part).
    - Security M-1: setup and the migration could seed the runbook at the default path through a planted symlink. They now write only at the path `$S deploy` printed, and nothing when it's invalid.
    - Security L-2: the runbook could name `.claude/settings.json` or a `.git/` hook. It must be a `.md` file outside `.git/`, `.claude/` and `.sdlc/` (test_scaffold › test_deploy_runbook_is_a_markdown_doc_outside_tool_folders).
    - Security L-3: added the stored and default symlinked-runbook cases to the test.
    - F1 and F2: the docs (runbook, Configuration, spec 01) describe the checks.
- **Tickets:** a `.sdlc/config.json` whose top level isn't a JSON object crashes every `scaffold.py` command with a traceback, `deploy` included (code r2 L1, security r2 L-1). It predates this change, so the fix belongs where the config is loaded, for all commands.
- **Drift and manual checks:** the state file's Deviations lines: ran without sdlc setup (this repo isn't set up for sdlc, as with earlier features); `cmd_deploy` and `platform` named for drift; extra doc files from the stale-docs audit; the round-1 and round-2 fix helpers; the rebase onto de61977 (3.3.0 to 3.5.0 shipped meanwhile: `Base` moved, and the upgrade migration renamed `3.6.0-deploy-target.md`, with AC-004 and the Decisions rows following). No `manual` AC. The full suite passed after each fix round: 433, then 495 after the rebase, then 497 tests on Python 3.10.
- **Security:** no secrets in the diff. No dependency audit: the plugin is stdlib-only Python with no manifest. The GCP reference's advice was checked sound: Workload Identity Federation over keys, Secret Manager, `printf '%s'`, internal ingress with IAM, CORS not treated as access control.
- **Lessons filed:** [.sdlc/recurring-defects.md](../recurring-defects.md): "Repo config relaxes a safety stop or names a file". The gotcha behind it, `knowledge/gotchas/repo-config-is-untrusted.md`, already existed.
