# Cloudflare Workers

For a project whose `.sdlc/config.json` has `deploy.target: cloudflare`. `brief.py` prints the Define checks below on every Define; the rest of this file is for a change that touches the deploy itself (Wrangler config, CI, the runbook) and for `/sdlc:deploy`. Facts marked "verify" change with Cloudflare's plans and limits: check the current docs (developers.cloudflare.com/workers/platform/limits) before relying on a number.

## Define checks

Each one that applies to the change becomes a failure mode in `<change>`, with a criterion or a must-never-break line.

- **CPU per request.** The Free plan allows 10 ms of CPU per request; Paid defaults to 30 s and can be raised to 5 minutes (verify). Password hashing, image work or a large JSON transform can exceed the Free cap: on Free, email and password sign-in (Better Auth's hashing included) needs the paid plan or company sign-in only.
- **No long-running process.** Work after the response, a queue worker or a nightly job must fit Cron Triggers (a scheduled handler calling a function in the service layer), Queues or Workflows; Cron Triggers and Queue consumers stop after 15 minutes of wall clock (verify). Heavier background work means another deploy target.
- **State in isolate memory.** Isolates come and go and run in many places at once, so a rate limit, session, cache or counter held in a module variable is per isolate and lost at any time. It belongs in the database, KV, or a Durable Object.
- **Database connections.** A Worker can't hold a pool across requests. Postgres goes through Hyperdrive (it pools and caches; works with `pg`, Neon and Supabase) or a serverless driver. Neon's HTTP driver has no interactive transactions (its `transaction()` is a fixed batch): logic that reads then writes in one transaction needs Hyperdrive or the WebSocket `Pool`, connected and closed inside the one request. Supabase through its transaction pooler: prepared statements off, no `SET`, `LISTEN/NOTIFY` or session advisory locks.
- **Not Node.** `nodejs_compat` is on by default from compatibility date 2026-08-04 and opt-in before it (verify): check the flag before relying on Node APIs. Confirm each new dependency runs on Workers before adding it.
- **Memory.** 128 MB per isolate (verify): no loading a whole upload or export into memory; stream it, or put it in R2.
- **Secrets.** Workers secrets (`wrangler secret put`) per environment, never `vars` in the Wrangler file, which is committed. A committed `.env.example` lists every variable with a placeholder.
- **Environments.** Local, preview and production each have their own database and secrets; a preview never points at production data.
- **Security headers.** Static assets' headers, the Content Security Policy among them, live in `_headers`; a change to the web app keeps the CSP free of `unsafe-inline` scripts.

## Building blocks

| Piece | On Workers |
|---|---|
| the API (Hono) | a Worker; one deployable: one Worker serves the assets and `/api/*` (Nuxt: Nitro's `cloudflare_module` preset) |
| a static web app | Workers static assets; with a separate API Worker, a route on the same hostname sends `/api/*` to it, so the two deploy separately |
| Postgres | Neon, Supabase or another host, through Hyperdrive |
| files | R2 |
| scheduled jobs | Cron Triggers |
| background work | Queues, Workflows |
| per-key coordination (rate limits, rooms) | Durable Objects |
| logs | Workers Logs |

Smart Placement (`[placement] mode = "smart"` in the Wrangler file) runs the Worker near its database when most of its time is database round trips.

## Deploy and rollback

CI runs, in order: install from the lockfile, typecheck and lint, tests against a disposable Postgres, migrations from empty on it, build; on `main` only, migrations on production, `wrangler deploy`, smoke test on the deployed URL. Rollback (`wrangler rollback`) moves traffic to a previous version but doesn't undo migrations: every migration must work with the previous version.

## Exit

Keep services and repositories free of Cloudflare APIs, so moving to a Node host (Cloud Run, a VPS) means changing the entry point and the database client, and moving the database is dump and restore.
