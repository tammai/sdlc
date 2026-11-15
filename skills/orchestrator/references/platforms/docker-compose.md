# Docker Compose on a server

For a project whose `.sdlc/config.json` has `deploy.target: docker-compose`: one server (a VPS) running the app with Docker Compose behind an HTTPS proxy such as Caddy. `brief.py` prints the Define checks below on every Define; the rest of this file is for a change that touches the deploy itself (Compose files, the Dockerfile, the proxy, CI, the runbook) and for `/sdlc:deploy`.

## Define checks

Each one that applies to the change becomes a failure mode in `<change>`, with a criterion or a must-never-break line.

- **Firewall.** Docker routes a published port before ufw's rules apply, so `ports:` on a container opens it to the internet whatever ufw says. Only the proxy publishes (80, 443); the database, Redis and the app listen on the Compose network, or publish on `127.0.0.1` only.
- **Backups.** No managed service is behind a self-hosted database: backups (continuous WAL archiving plus a daily base backup, with pgBackRest or WAL-G) go to object storage off the server, and a restore drill into a scratch container runs before launch and on a schedule. A change that adds data the business can't lose checks the backup covers it. A medium or high-load product on one server's database is a single point of failure: consider a managed database.
- **Deploy and rollback.** Migrations run as a one-off container before the new app version starts; rollback deploys the previous image tag and doesn't undo migrations, so every migration must work with the previous image.
- **Restarts drop requests.** `docker compose up -d` replaces the container: requests in flight for a few seconds fail. Accepted until the team asks for a rolling release; a change that can't take that (long uploads, websockets) says so.
- **Secrets.** An env file on the server readable only by the deploy user, never in the repository or an image layer (no `COPY .env`, no `ARG` for a secret). A committed `.env.example` lists every variable with a placeholder.
- **Containers.** Each runs as a non-root user, has a health check and a restart policy, and logs to stdout with rotation set in Compose; the disk fills otherwise.
- **The team operates it.** Operating system patching, disk space, certificates and uptime are the team's: a change that adds a service adds its health check and its line in the deploy runbook.
- **Staging.** A second Compose project with its own database; it never shares the production database.

## Building blocks

| Piece | On the server |
|---|---|
| one deployable (Nuxt or Next.js with Hono) | one app container running the framework's Node server |
| a standalone API | its own container; the proxy serves the web app's static files and proxies `/api/*` to it |
| Postgres | the official `postgres` image pinned to a major version, on a named volume; the app has its own user, never `postgres` |
| HTTPS | Caddy (automatic certificates) or Traefik, the only published service |
| scheduled jobs | a cron container or the host's scheduler, calling a command in the app image |
| background workers | their own Compose service on the same image |
| images | built in CI, tagged by commit, pushed to a registry; the server only pulls |

## Deploy, rollback and logs

CI runs, in order: install, typecheck and lint, tests against a disposable Postgres, migrations from empty on it, build and push the images; on `main`, after the go-ahead, over SSH: the migrate container, `docker compose pull`, `docker compose up -d`, then a smoke test on the deployed URL. Rollback sets the previous tag and runs `docker compose up -d` again. Logs: `docker compose logs --tail 100 <service>`.

## The server

SSH by key only, a firewall that opens 80, 443 and the SSH port, automatic security updates, and an uptime check on the health endpoint with alerts on disk and memory. Keep the deploy runbook current so the stack can be rebuilt on a new server from images, the env file and backups.
