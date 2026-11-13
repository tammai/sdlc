# Configuration

Setup writes `.sdlc/config.json`; it's yours to edit and holds only what differs from the plugin's defaults (`templates/project/config.defaults.json`, deep-merged, your values win, lists replace). Most teams only touch it to change a command.

| Key | Meaning |
|---|---|
| `commands` | `install`, `test`, `lint`, `typecheck`, `build` as the team runs them. `null` means the step doesn't apply |
| `packages` | Monorepo instead of `commands`: `[{"name", "path", "stack", "commands"}]`, each run from its path. A root `commands.test` beside it (e.g. `turbo run test`) runs from the root after every package's steps, in verify and CI, and a full run of it counts for every package; other root commands don't run |
| `project.kind` | `greenfield` or `brownfield`, set by setup |
| `workbench` | `true` in a workbench repo (with `workbench.json` beside `.sdlc/`; both are needed); in an app repo of a workbench, the workbench's repo name (`shop-workbench`, or `acme/shop-workbench` under another account), which its CI checks out for the contract and which stops features starting there |
| `project.profile`, `project.owners` | Multi-app repos: `lean` or `large` (the answer to "who works here"), and for `large` the CODEOWNERS entries (`{pattern: [handles]}`, in order) |
| `api_contract` | Multi-app repos with the contract check: `{"path", "spec"}` of the versioned API contract |
| `docs_dir` | Where the sdlc documents live (default `docs/sdlc`; `.sdlc` or another in-repo folder if `docs/` is published as a site). Without it a repo is on the old all-in-`.sdlc/` layout |
| `contract.required` | The commands every package must list, `null` allowed (default all five) |
| `verify.order` | Order of the verify steps (default lint, typecheck, build, test) |
| `areas.*` | Path patterns for the policy rules and reviewers: `source`, `ui`, `tests`, `migrations`, `sensitive`, `ci` |
| `deploy` | How the project deploys, set by setup's `deploy` step (`scaffold.py deploy`; `/sdlc:setup deploy` changes it): `target` (`none`, `docker-compose`, `gcp-cloud-run`, `vercel`, `cloudflare`, `other`), `environments` (`[{"name", "routine"}]`; only a routine one deploys without your go-ahead, and production, any name with a `prod`, `production`, `live` or `prd` part, never is) and `runbook` (a Markdown file in the repo, default `knowledge/runbooks/deploy.md`), which `/sdlc:deploy` follows. A value that fails its check is ignored and reported as `invalid` |
| `ci` | `os` matrix (default `["ubuntu-latest"]`; add `"windows-latest"` if teammates develop on Windows) and toolchain versions (`node_version`, `java_version`, `dotnet_version`, `oasdiff_version`) for the generated workflow |
| `baseline` | Where the known-failures baseline lives (default `.sdlc/baseline.md`) |
| `min_plugin_version` | Teammates on an older plugin get a warning to update |

After changing commands or `ci`, run `/sdlc:upgrade` so the generated CI workflow follows. Don't edit `.sdlc/scaffold.lock.json` by hand. Why it's designed this way: [ADR 0001](../adr/0001-project-setup-upgrade-eject.md), [ADR 0002](../adr/0002-record-the-repos-own-commands.md), [ADR 0005](../adr/0005-greenfield-monorepo-layout.md), [ADR 0006](../adr/0006-split-sdlc-docs-from-machinery.md), [ADR 0007](../adr/0007-multi-tool-adapters.md); the `scaffold.py` reference is in the [runbook](../runbook.md#setup-upgrade-eject-internals).

## Security hook switches


Set in the shell or in `settings.json` `env`.

| Variable | Default | Effect |
|---|---|---|
| `SECURITY_GUIDANCE_DISABLE=1` (or `ENABLE_SECURITY_REMINDER=0`) | off | Disable the whole security hook |
| `ENABLE_PATTERN_RULES=0` | on | Turn off regex warnings on edits |
| `ENABLE_CODE_SECURITY_REVIEW=0` | on | Turn off the turn-end diff review and the commit/push review |
| `ENABLE_COMMIT_REVIEW=0` | on | Turn off the commit review |
| `ENABLE_STOP_REVIEW=0` | on | Turn off the turn-end review |
| `SDLC_SECURITY_REVIEW=always` | off | Run the turn-end and commit reviews on every change, not only while a security-touched feature is active (ADR 0019); also installs the reviewer's environment at session start |
| `MAX_STOP_HOOK_FIRINGS` | 3 | Cap on repeated turn-end review firings |
| `MAX_DIFF_FILES` | 30 | Largest diff the reviewer will look at |
