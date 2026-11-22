# Configuration

Setup writes `.sdlc/config.json`. It's yours to edit, and holds only what differs from the plugin defaults (`templates/project/config.defaults.json`, deep-merged: your values win, lists replace). Most teams only touch it to change a command.

**After changing `commands` or `ci`, run `/sdlc:upgrade`** so the generated CI follows. Never edit `.sdlc/scaffold.lock.json` by hand.

## Common keys

| Key | Meaning |
|---|---|
| `commands` | `install`, `test`, `lint`, `typecheck`, `build`, as the team runs them. `null` = the step doesn't apply |
| `packages` | Monorepo, instead of `commands`: `[{"name", "path", "stack", "commands"}]`, each run from its path. A root `commands.test` beside it (for example `turbo run test`) runs after every package in verify and CI, and a full run of it counts for every package. Other root commands don't run |
| `areas.*` | Path patterns for policy rules and reviewers: `source`, `ui`, `tests`, `migrations`, `sensitive`, `ci`. **Keep `sensitive` and `migrations` right:** a path they miss gets no security review |
| `rules` | Your own lines per document: `{"change": [...], "plan": [...], "review": [...]}`. Define applies `change` and `plan`; every review checks `review` against the diff. Other keys are ignored |
| `ci` | `os` matrix (default `["ubuntu-latest"]`; add `"windows-latest"` for Windows teammates; Swift runs in its own `verify-macos` job). Toolchain versions: `node_version`, `java_version`, `dotnet_version`, `oasdiff_version` |
| `deploy` | Set by setup's deploy step (`/sdlc:setup deploy` changes it). `target`: `none`, `docker-compose`, `gcp-cloud-run`, `vercel`, `cloudflare`, `other`. `environments`: `[{"name", "routine"}]`; only a routine one deploys without your go-ahead, and a production one (any name with a `prod`, `production`, `live` or `prd` part) never does. `runbook`: default `knowledge/runbooks/deploy.md`. An invalid value is ignored and reported |

## Optional features

| Key | Meaning |
|---|---|
| `living_spec` | `true`: one file per capability under `<docs_dir>/capabilities/`, merged at Ship ([How it works](How-it-works.md#optional-features)). Not used in a spec-backed repo |
| `objects` | `true` (or an in-repo path): the domain model `<docs_dir>/objects.md`. Set by `/sdlc:setup objects`. Does nothing in a spec-backed repo |
| `design` | `builtin` (default) or `impeccable` ([Setup with impeccable](Project-setup.md#setup-with-impeccable)) |

## Less common

| Key | Meaning |
|---|---|
| `project.kind` | `greenfield` or `brownfield`, set by setup |
| `project.profile`, `project.owners` | Multi-app repos: `lean` or `large`, and for `large` the CODEOWNERS entries (`{pattern: [handles]}`, in order) |
| `workbench` | `true` in a workbench repo (with `workbench.json`). In an app repo: the workbench's repo name (`shop-workbench` or `acme/shop-workbench`), which its CI checks out and which stops features starting there |
| `api_contract` | Multi-app repos with the contract check: `{"path", "spec"}` |
| `docs_dir` | Where sdlc documents live (default `docs/sdlc`; use `.sdlc` or another folder if `docs/` is a published site). Without it, a repo uses the old all-in-`.sdlc/` layout |
| `contract.required` | Commands every package must list, `null` allowed (default: all five) |
| `verify.order` | Order of verify steps (default lint, typecheck, build, test) |
| `baseline` | Baseline location (default `.sdlc/baseline.md`) |
| `min_plugin_version` | Teammates on an older plugin get a warning |

Why it's designed this way: ADRs [0001](../adr/0001-project-setup-upgrade-eject.md), [0002](../adr/0002-record-the-repos-own-commands.md), [0005](../adr/0005-greenfield-monorepo-layout.md), [0006](../adr/0006-split-sdlc-docs-from-machinery.md), [0007](../adr/0007-multi-tool-adapters.md). `scaffold.py` reference: [runbook](../runbook.md#setup-upgrade-eject-internals).

## Security hook switches

Set these in the shell or in `settings.json` → `env`.

| Variable | Default | Effect |
|---|---|---|
| `SECURITY_GUIDANCE_DISABLE=1` (or `ENABLE_SECURITY_REMINDER=0`) | off | Disables the whole security hook |
| `ENABLE_PATTERN_RULES=0` | on | Turns off regex warnings on edits |
| `ENABLE_CODE_SECURITY_REVIEW=0` | on | Turns off the turn-end and commit/push reviews |
| `ENABLE_COMMIT_REVIEW=0` | on | Turns off the commit review |
| `ENABLE_STOP_REVIEW=0` | on | Turns off the turn-end review |
| `SDLC_SECURITY_REVIEW=always` | off | Reviews every change, not only security-touched ones (ADR 0019); also installs the reviewer environment at session start |
| `MAX_STOP_HOOK_FIRINGS` | 3 | Cap on repeated turn-end reviews |
| `MAX_DIFF_FILES` | 30 | Largest diff the reviewer looks at |
