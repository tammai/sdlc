# Vercel

For a project whose `.sdlc/config.json` has `deploy.target: vercel`. `brief.py` prints the Define checks below on every Define; the rest of this file is for a change that touches the deploy itself (`vercel.json`, CI, the runbook) and for `/sdlc:deploy`. Facts marked "verify" change with Vercel's plans: check the current docs (vercel.com/docs/functions/limitations) before relying on a number.

## Define checks

Each one that applies to the change becomes a failure mode in `<change>`, with a criterion or a must-never-break line.

- **Plan.** Hobby is for personal, non-commercial use: a commercial product needs Pro (verify). Set a spend limit so a traffic spike or a retry loop can't run up the bill.
- **Function duration.** With Fluid compute a function runs 300 s by default; Hobby can't go past that, Pro and Enterprise up to 800 s (`maxDuration` per function; 1800 s in beta) (verify). An export, import or report that can take longer becomes a Workflow or a queued job, not a longer request.
- **Work after the response.** `waitUntil` runs within the same max duration, with no retry and no record: fine for a log line, not for an email or a payment step. Retried work goes to Queues (public beta, verify) or Workflows.
- **Cron.** Vercel Cron runs only on production, calls a function by URL, may be missed or run twice and isn't retried, and Hobby allows one run a day per job (verify). The endpoint checks `Authorization: Bearer <CRON_SECRET>` and returns 401 otherwise, and the job is safe to repeat.
- **State in function memory.** Instances are reused and scaled out, so a rate limit, session or counter in a module variable is per instance and lost at any time. It belongs in the database or Redis.
- **Database connections.** Create the `pg` pool at module scope and register it with `attachDatabasePool` from `@vercel/functions`, so idle connections close before the instance suspends; keep the pool small and connect through the provider's pooler (Neon's pooled string; Supabase's transaction pooler with prepared statements off and no session state). Migrations use the direct string, from CI only.
- **Go or Python API.** Python runs as one function per app (GA; 500 MB bundle) and Go is in beta (verify): both live under the duration and memory limits above. CPU-heavy or long-lived work goes on a container host.
- **Environments.** Production, preview and development have their own variables; a preview deployment never reaches the production database or production secrets (a database branch per preview).
- **Region.** Functions run in one region (`iad1` unless set): put it next to the database.
- **Security headers.** The Content Security Policy is set in the framework config or `vercel.json`; a change keeps it free of `unsafe-inline` scripts.

## Building blocks

| Piece | On Vercel |
|---|---|
| Next.js with Hono | one project; Hono runs in the bridge route handler (`app/api/[[...route]]/route.ts`) as a function |
| Nuxt with Hono | one project; Nitro's `vercel` preset: assets on the CDN, `/api/*` as a function |
| a standalone API | its own project; the web app is a second project from the same repo with a rewrite of `/api/*` to it, or Services in one project |
| scheduled jobs | Vercel Cron, with `CRON_SECRET` |
| background work | Workflows, Queues (beta) |
| logs | the project's runtime logs; a drain for anything kept longer |

## Deploy and rollback

CI runs, in order: install from the lockfile, typecheck and lint, tests against a disposable Postgres, migrations from empty on it, build; on `main` only, migrations on production, then Vercel's Git deploy, then a smoke test on the deployed URL. Instant Rollback moves the domain to a previous deployment but doesn't undo migrations: every migration must work with the previous deployment.

## Exit

Keep services and repositories free of Vercel APIs, so moving hosts means changing the entry point and the database client.
