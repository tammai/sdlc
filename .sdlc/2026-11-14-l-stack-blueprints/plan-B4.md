# Part plan: 2026-11-14-l-stack-blueprints B4

**Record:** the feature's change file (`scaffold.py paths <feature>` → `change`) · **Backlog:** [backlog.md](backlog.md)

## Tasks

1. **Platform references** — AC-010
   - Files: `skills/orchestrator/references/platforms/cloudflare.md`, `skills/orchestrator/references/platforms/vercel.md`,
     `skills/orchestrator/references/platforms/docker-compose.md`, `tests/test_stack_blueprints.py`
   - Test first: `Platforms.test_define_checks_per_target`
   - Then: each in `gcp-cloud-run.md`'s shape (intro, `## Define checks`, then how-to for changes to the deploy),
     from the blueprint's `deploy/*` modules, the deferred `init/selection.json` warnings (Better Auth hashing on
     Workers free, self-hosted DB at medium scale) and the data-layer driver notes (neon, supabase, self-hosted).
     Limits and prices marked "(verify)". `brief.py` already prints any target with a file (`platform()`), so it
     isn't changed.
2. **B1's Vercel warning** — AC-002
   - Files: `skills/setting-up-projects/references/stacks.md`
   - Then: Vercel now runs Python (GA) and Go (beta) as functions; the warning keeps flagging a Go or Python API on
     Vercel, for function limits rather than "can't run there".

## Public Surface

- none

## Sources checked (2026-11-14)

- Cloudflare Workers limits: CPU per request 10 ms Free, 30 s default up to 5 min Paid; Cron Triggers and Queue
  consumers 15 min wall clock; 128 MB per isolate (developers.cloudflare.com/workers/platform/limits).
- `nodejs_compat` on by default from compatibility date 2026-08-04, opt-in before (developers.cloudflare.com/workers/
  runtime-apis/nodejs); Smart Placement `[placement] mode = "smart"` (…/workers/configuration/placement);
  Hyperdrive pools connections and caches queries, works with `pg`, supports Neon and Supabase
  (developers.cloudflare.com/hyperdrive).
- Neon serverless driver: HTTP `transaction()` is a non-interactive batch; WebSocket `Pool`/`Client` for interactive
  transactions and sessions, which can't outlive one request in an edge runtime (neon.com/docs/serverless/
  serverless-driver).
- Vercel durations with Fluid compute: 300 s default and max on Hobby, 300 s default and 800 s max on Pro and
  Enterprise, 1800 s beta (vercel.com/docs/functions/configuring-functions/duration). `waitUntil` runs within that
  max, no retries; Cron Jobs only in production, `CRON_SECRET` sent as `Authorization: Bearer`, no retry, may be
  missed or duplicated, Hobby once a day; Queues public beta; Workflows GA (vercel.com/kb/guide/
  background-workers-on-vercel). Runtimes: Python GA (ASGI/WSGI, whole app one function, 500 MB bundle), Go beta,
  Container runtime (vercel.com/docs/functions/runtimes, …/python, …/go). `attachDatabasePool` from
  `@vercel/functions` for a module-scope `pg` pool on Fluid (vercel.com/kb/guide/
  efficiently-manage-database-connection-pools-with-fluid-compute). Hobby non-commercial: checked in B1.
- Docker: published ports are routed before ufw's rules apply (docs.docker.com/engine/network/
  packet-filtering-firewalls).
- Supabase: transaction pooler (6543) for serverless, no prepared statements, no session state; session pooler or
  direct connection (IPv6 unless the IPv4 add-on) for long-lived servers; direct for migrations
  (supabase.com/docs/guides/database/connecting-to-postgres). New `public` tables are reachable through the Data
  API by default; enable RLS on every exposed table (supabase.com/docs/guides/api/securing-your-api).
- Dropped, not confirmed: "Workers can't use native modules or file system" (fs is supported; native addons not
  documented either way: the reference says confirm a dependency runs on Workers); the blueprint's "Neon serverless
  driver over WebSockets on Vercel" (Vercel's current guidance is a pooled `pg` client with `attachDatabasePool`).
- Not carried: the blueprint's "internal tool described as multi-tenant" warning (tenancy waits for the feature;
  B3's templates scope tenant rules to "when the product is multi-tenant").
