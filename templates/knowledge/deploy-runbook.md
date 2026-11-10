---
type: runbook
title: Deploy
description: How this project deploys, smoke-tests, rolls back and reads logs; /sdlc:deploy follows it.
---

# Deploy

<!-- Seeded by sdlc setup from `deploy` in .sdlc/config.json; the project's from now on. /sdlc:deploy reads it before
     every deploy and adds what a deploy teaches to "Learnt on deploys". Leave a line [unknown] rather than guess. -->

Target: [deploy.target]. One-time setup (accounts, projects, DNS) lives in: [a README section or script, or "not yet"].

## Environments

| Environment | Where (project, URL) | Routine |
|---|---|---|
| [dev] | [project or URL] | yes: deploys and migrates without a go-ahead |
| [prod] | [project or URL] | no: a go-ahead every time |

Routine matches `deploy.environments` in `.sdlc/config.json` (`scaffold.py deploy` changes it): keep the two the same.

## Deploy

[The command per environment, e.g. `scripts/deploy.sh <tag> <environment>`, and what it does in order: build or pick the image, run the migrations, move traffic.]

## Smoke test

[What shows a deploy works: a request and the answer expected (`curl -fsS https://<host>/health` → 200), a sign-in, the main screen.]

## Rollback

[The command that puts the previous version back, and what it doesn't undo: a migration stays applied, so every migration must work with the version before it.]

## Logs

[Where to read them: the command or console page, and the filter for this service.]

## Learnt on deploys

<!-- One line per fact a deploy taught: date, environment, fact (a header shape, a URL, a limit, a missing step). -->
-
