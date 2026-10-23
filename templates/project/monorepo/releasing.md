# Releasing

Each app releases on its own schedule from this one repo.

## Versions and tags

Tag each release with the app's name: `web@1.4.2`, `api@2.1.0`, `mobile@3.0.0`. Versions follow semver per app; one app's release never bumps another's.

## Release branches

Ship from `main` while that's enough. When an older major needs fixes after `main` has moved on, branch it: `release/<app>-v<major>` (`release/api-v1`), fix there, tag there, and carry the fix to `main` if it applies.

## CI

Each app's workflow (`.github/workflows/sdlc-verify-<app>.yml`) runs only when that app, a shared package, a root file (lockfile, workspace manifest) or the workflow itself changes. A contract change runs every app's CI.

If you protect `main` with required status checks, make `sdlc contract` required (it runs on every pull request), but don't mark the per-app workflows as required: a pull request that doesn't touch an app never runs its workflow, so a required check would wait forever.
