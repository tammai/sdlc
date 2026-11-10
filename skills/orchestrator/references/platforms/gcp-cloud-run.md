# GCP Cloud Run

For a project whose `.sdlc/config.json` has `deploy.target: gcp-cloud-run`. `brief.py` prints the Define checks below on every Define; the rest of this file is for a change that touches the deploy itself (scripts, CI, infrastructure, the runbook) and for `/sdlc:deploy`. Facts marked "verify" change with Google's pricing and tiers: check the current docs before relying on a number.

## Define checks

Each one that applies to the change becomes a failure mode in `<change>`, with a criterion or a must-never-break line.

- **State in process memory.** Cloud Run scales to zero and runs more than one instance under load, so a rate limit, session, cache or counter held in process memory resets on a cold start and is counted per instance. It belongs in the database (an atomic upsert) or Redis.
- **Connections.** Each instance opens up to its pool size: instances × pool size must stay under the Cloud SQL tier's `max_connections`, so set `--max-instances` from that (it's a cap, not a cost). `db-f1-micro` allows about 25 connections, `db-g1-small` more (verify).
- **Socket URL.** Cloud SQL over the Unix socket: `postgres://user@localhost/db?host=/cloudsql/PROJECT:REGION:INSTANCE`, password from `PGPASSWORD`. A host-less URL (`postgres:///db?host=…`) fails strict URL parsing in a startup check.
- **CI credentials.** Images are pushed from GitHub Actions with Workload Identity Federation bound to one repository, never a service-account key in secrets.
- **Secrets.** Write them to Secret Manager with `printf '%s'`, never `echo`: its trailing newline breaks a strict env check, and the service won't start.
- **Client IP.** Confirm the real `X-Forwarded-For` shape on the first deploy before trusting proxies; until then rate limits and audit logs by IP may key on Google's front end, not the client.
- **Cookies.** Firebase Hosting in front of Cloud Run drops every cookie except `__session`, which breaks cookie auth; domain mapping or a load balancer doesn't.
- **Deploy and rollback.** The deploy migrates before it moves traffic, and rollback (`gcloud run services update-traffic SERVICE --to-revisions=PREV=100`) does not undo migrations: every migration must work with the previous revision.
- **Exposure.** A private API is `--ingress internal` with `--no-allow-unauthenticated`; a secret in a mobile or desktop binary is public, and CORS is not access control.

## Building blocks

What each piece of a Docker compose setup becomes:

| Compose | Cloud Run |
|---|---|
| app container | a Cloud Run service |
| `db` (Postgres) | Cloud SQL, attached to the service (`--add-cloudsql-instances`) |
| the HTTPS proxy (Caddy, Traefik) | domain mapping, or a global external load balancer |
| the migrate step | a Cloud Run Job on the same image, run with `--wait` before the service deploys |
| `.env` secrets | Secret Manager, mounted as env vars (`--set-secrets`) |
| the image registry | Artifact Registry |
| one host per environment | one GCP project per environment |

The deploy script runs, in order: build and push the image (by commit SHA), execute the migrate job on that tag and wait, deploy the service on the same tag, smoke test. A failed migrate job stops it before the service changes (`set -euo pipefail`).

## Domains and HTTPS

- **Domain mapping** is a preview feature that only some regions offer: pick the region for it. Verify domain ownership (Search Console), then CNAME the subdomain to `ghs.googlehosted.com`, or A/AAAA records for an apex domain. Cloudflare records must be DNS-only (grey cloud), or the certificate never issues.
- **A global external load balancer** costs about $18/month (verify): worth it from about three apps behind one IP, or for Cloud Armor, IAP or a CDN.
- **Firebase Hosting** rewrites to Cloud Run cheaply, but keeps only the `__session` cookie.

## Access

- **Private API** (service to service): `--ingress internal`, `--no-allow-unauthenticated`, and `roles/run.invoker` for the caller's service account; the caller sends an ID token.
- **Public API used by your own clients:** ingress `internal-and-cloud-load-balancing` behind a load balancer with Cloud Armor, user tokens for identity, App Check for mobile apps. Anything shipped in a mobile or desktop binary is public. CORS only tells browsers what to allow; it stops nobody else.
- **Staff tools:** IAP in front, not a shared password.

## A cheap dev project

- A separate GCP project, on the $300 trial credit where available (verify).
- The Cloud SQL tier and point-in-time recovery as setup inputs (the smallest tier, recovery off for dev; a larger tier and recovery on in production), not values fixed in the script.
- Stop Cloud SQL out of hours: `gcloud sql instances patch INSTANCE --activation-policy=NEVER` (and `ALWAYS` to start). Storage still bills, and the app's requests fail while it's stopped.
- Cloud Run's free tier covers a small team's dev traffic (verify).
- A budget alert on the project: it alerts, it doesn't cap spending.

## Rollback and logs

- **Rollback:** `gcloud run revisions list --service SERVICE` names the previous revision; `gcloud run services update-traffic SERVICE --to-revisions=PREV=100` moves traffic back at once. The migration stays applied.
- **Logs:** `gcloud run services logs read SERVICE --region REGION --limit 100`, or Logs Explorer filtered on `resource.type="cloud_run_revision"` and the service name; the migrate job's under `cloud_run_job`.
