# infras

How the apps are built into images and deployed: Dockerfiles, compose files, deploy playbooks, infrastructure as code.

- `infras/<app>/` for what belongs to one app (`infras/api/Dockerfile`).
- `infras/shared/` for what several apps use (a network, a database, a compose file for local dev).

Changes here count as CI and deploy changes: the sdlc review treats them with the same care as `.github/`.
