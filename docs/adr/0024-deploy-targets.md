# ADR 0024: Setup records how a project deploys; platform knowledge lives in the plugin

- **Status:** Accepted, 2026-11-10.
- **Deciders:** Tâm Mai, from missue (Thoi) moving to GCP Cloud Run and Cloud SQL.

## Context

`/sdlc:deploy` said only "use the project's own deploy path", and setup never asked how a project deploys. missue's move to Cloud Run hit a run of platform traps by hand: in-process rate limits under scale to zero, Cloud SQL connection caps, the socket URL, trailing newlines in secrets, the `X-Forwarded-For` shape, domain-mapping regions, and Firebase Hosting dropping cookies. Most of that is generic to the platform, not to missue. Separately, the migrations rule never loaded for Drizzle, because the default globs missed `drizzle/`.

## Decision

1. **Setup's `deploy` step records the target and environments** as `deploy` in `.sdlc/config.json`: `target` from a fixed list, `environments` each routine or not, and `runbook`. `scaffold.py deploy` writes it. Setup seeds the runbook from `templates/knowledge/deploy-runbook.md`, and the runbook stays the project's. `/sdlc:setup deploy` runs the step alone. The `3.6.0-deploy-target` migration asks it in repos set up before.
2. **`/sdlc:deploy` follows the runbook.** Its deploy command, smoke test, rollback and logs come from the runbook. A fact a deploy teaches is written back to the runbook.
3. **Only a routine environment skips the go-ahead, and production never is one.** Repo config is untrusted: a pull request can change it ([gotcha](../../knowledge/gotchas/repo-config-is-untrusted.md)). So `scaffold.py` refuses `:routine` on any name with a `prod`, `production`, `live` or `prd` part, and names must be plain ASCII. Every stored value is checked on each read, and a bad one is null or corrected and listed in `invalid`. `/sdlc:deploy` uses only the printed values and keeps production's go-ahead whatever the config says. The runbook must be a `.md` file inside the repo, outside `.git/`, `.claude/` and `.sdlc/`, after symlinks are resolved.
4. **Platform knowledge is a plugin reference, one per target:** `skills/orchestrator/references/platforms/<target>.md`, starting with GCP Cloud Run. Its `## Define checks` section is what every change must weigh, and `brief.py` prints it on every Define when the target matches. The target must be a plain slug before it names a file. The rest of the file, how-to detail for changes to the deploy itself, is read on demand.
5. **The default `areas.migrations` covers `drizzle/`, `alembic/` and `db/migration/`.** We chose default globs over detecting the ORM in setup.

## Consequences

- A project on a target with a reference gets its checks in Define without asking. A target without one (`vercel`, `cloudflare`, `docker-compose`, `other`) gets the config and the runbook only, until its reference is written.
- The Define checks cost a few hundred tokens on every Define in such a project. The how-to detail costs nothing until it's read.
- Production can't deploy without a person's go-ahead, even if the user wanted that. Doing so would need a per-user local setting and a new ADR.
- The plugin, not each project, now owns platform facts that change (tiers, prices, preview features). The reference marks them "verify", and they need updating when Google changes them.
