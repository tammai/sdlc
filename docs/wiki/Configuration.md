# Configuration

Setup writes `.sdlc/config.json`. It's yours to edit, and holds only what differs from the plugin defaults (`templates/project/config.defaults.json`, deep-merged: your values win, lists replace). Most teams only touch it to change a command.

**After changing `commands` or `ci`, run `/sdlc:upgrade`** so the generated CI follows. Never edit `.sdlc/scaffold.lock.json` by hand.

## Common keys

| Key | Meaning |
|---|---|
| `commands` | `install`, `test`, `lint`, `typecheck`, `build`, as the team runs them. `null` = the step doesn't apply |
| `packages` | Monorepo, instead of `commands`: `[{"name", "path", "stack", "commands"}]`, each run from its path. A root `commands.test` beside it (for example `turbo run test`) runs after every package in verify and CI, and a full run of it counts for every package. Other root commands don't run |
| `areas.*` | Path patterns for policy rules and reviewers: `source`, `ui`, `tests`, `migrations`, `sensitive`, `ci`. **Keep `sensitive` and `migrations` right:** a path they miss gets no security review |
| `review_rounds` | Review rounds before the agent stops and asks you: 2 (default: the review, then one check of its fixes) to 5; anything else counts as 2. Setup asks it; `/sdlc:setup review-rounds` changes it. A lower value applies at once and stays for the feature; a higher one applies to features started after it's committed, or at once when you type `/sdlc:setup review-rounds <n>` |
| `mode` | `full` (default: the whole workflow, its hooks and gates) or `advisory` (the skills and agents as aids; no hook, gate or guardrail, except a workbench's read-only guard; `SDLC_SECURITY_REVIEW=always` still forces the security reviews). Setup asks it first; `/sdlc:setup mode …` changes it. A move to advisory is shown to you by the trust anchor. [ADR 0030](../adr/0030-modes-and-skips.md) |
| `skip` | Full mode only: steps this repo skips, any of `security-review`, `code-review`, `ui-review`, `pr`. A skipped review doesn't run and `## Review` says so; `security-review` also turns off the commit and turn-end security reviews (the push review stays); `pr` ends Ship after the local commit. `/sdlc:setup skip …` (or `--clear`); a newly skipped step is shown to you by the trust anchor |
| `guards` | Opt-in guards, each `"<name>": true`. `s_tests`: an S feature's red step locks its test files as on M and L, so a test changed afterwards fails verify until a `test-change` deviation and a red run at Base are recorded. `dependencies`: verify fails on a dependency name new since the feature's Base in a known manifest (a version bump is fine). `lint_config`: verify fails on any change to a known lint or type config file and on an added suppression comment (`@ts-ignore`, `eslint-disable`, `# type: ignore`, `# noqa`, …). You allow an item by answering Allow in the `Allow change` dialog, or typing `allow`; an allowed dependency gets the dependency audit in Review, and Ship writes the allowed items into the record. `/sdlc:setup guard s-tests|dependencies|lint-config on|off`; turning one off is shown to you by the trust anchor. [ADR 0032](../adr/0032-opt-in-guards.md) |
| `approval` | Which plans wait for your approval before Build: `high-risk` (default: high-risk M only, as before), `ml` (every M and L; L no longer approves itself) or `always` (S too). Answer the `Approve plan` question with Approve, or type `approve <feature>`; `state.py advance <f> 2` refuses until then, and autopilot blocks the part. `/sdlc:setup approval …`; a move to fewer stops is shown to you by the trust anchor. [ADR 0031](../adr/0031-approval-policy.md) |
| `done` | The project's Definition of Done: 1 to 10 one-line items every change shows before Ship (a changelog line, docs updated…). Setup asks it; `/sdlc:setup done` changes it. Define copies it into the change file's `## Definition of Done`, each item is ticked with its evidence, and `ship.py` refuses while one is open. A change from Base is shown to you by the trust anchor, and for a feature in flight an item leaves the bar only once you accepted that notice |
| `storybook` | `true`: Storybook is the living design system (builtin design mode only; needs a `.storybook/` folder). The stories are the component catalog: each component a change touches gets a story for every state the spec names, and the UI review checks against them. `scaffold.py storybook on\|off` (setup's design step). An optional `commands.storybook` (your Storybook build, e.g. `npx storybook build --test`; the test runner needs a served Storybook) runs in verify right after `build` (in a monorepo, a root one runs after the packages') |
| `team` | `true`: team mode (full mode only). An M or L feature's stages run as role agents the orchestrator coordinates: `analyst` for Define (opus), `builder` for Build and each fix round, the reviewers, `releaser` for Ship; the role guard holds each to its files. `/sdlc:setup team on\|off` |
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
| `verify.order` | Order of verify steps (default lint, typecheck, build, storybook, test; a custom order must list `storybook` for `commands.storybook` to run) |
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
