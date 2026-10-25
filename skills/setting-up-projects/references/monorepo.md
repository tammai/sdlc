`${CLAUDE_PLUGIN_ROOT}` is the sdlc plugin's folder. Claude Code fills it in; on other agents it stays as written, so use the installed plugin's folder instead: the one above this file that holds `scripts/` and `skills/`.

# Greenfield monorepo

Two or more apps (web, api, mobile, …) become one polyglot monorepo. It replaces the `stack`, `skeleton`, `commands` and `ci` steps of `greenfield.md`; the step names stay, so resume still works. One app: this file doesn't apply, follow `greenfield.md` as is. Decision: `${CLAUDE_PLUGIN_ROOT}/docs/adr/0005-greenfield-monorepo-layout.md`.

The layout is the same for every team size. No git subtrees or per-app repos: per-app CI, tags and release branches give each team its own cadence inside one repo.

```
apps/<name>/              each app, from its ecosystem's generator
packages/api-contract/    when one app serves an API another consumes: v1/openapi.yaml, v2/…
packages/<name>/          other shared code, one language each
docs/                     BA, QA and design artifacts, linked from features, never copied
infras/                   only if the user says yes
```

## `stack` – interview, then propose (hard stop)

Ask what you can't infer, a few at a time, each with a suggested answer:

- The apps and the stack of each; the package manager and test runner per stack (mainstream defaults, one line why).
- **Who will work in this repo?** A solo developer or a small team → profile `lean`. Separate roles (BA, QA, design, frontend, backend, DevOps) → profile `large`. Ask; never infer it from anything else.
- `large`: the team handle per area (`@org/web`, `@org/backend`, …). Backend owns the contract.
- **Add `infras/`** for Dockerfiles and deploy playbooks? No → nothing is created.
- With an API and a client: the contract format (default OpenAPI), and whether CI should block breaking changes to published versions (installs oasdiff in CI). Another format, or no → no contract check; say so in the report.

Propose in one message: the tree, the generator per app, the workspace manifest per ecosystem (pnpm workspace, Melos, uv workspace, Cargo workspace, …), and the five commands per package. **The user approves before anything is generated.**

## `skeleton`

- Generate each app into `apps/<name>` with its official tool (as in `greenfield.md`), then add strict types, test runner, lint and one smoke test.
- `packages/api-contract/v1/openapi.yaml`: a minimal valid spec (info, one health path). `$S render templates/project/monorepo/api-contract-README.md packages/api-contract/README.md --class seeded`.
- Each app that consumes the API gets a `generate:api` script (or the stack's equivalent, e.g. a `build_runner` step) that generates its client and types from the agreed version, run before build and test. Use the stack's native generator (`openapi-typescript`, `openapi-generator` for Dart/Kotlin, `oapi-codegen` for Go). Its output is gitignored via `$S gitignore --add <path>`. A generator that needs another toolchain (Java for `openapi-generator`) is a tool install: hard stop.
- `$S render templates/project/monorepo/docs-README.md docs/README.md --class seeded`. `large`: also create `docs/specs/`, `docs/test-cases/`, `docs/designs/`, `docs/runbooks/` (a `.gitkeep` each) and `$S render templates/project/monorepo/releasing.md docs/runbooks/releasing.md --class seeded`.
- `infras/` chosen: `$S render templates/project/monorepo/infras-README.md infras/README.md --class seeded`.

## `commands`

One `packages` entry per `apps/*` and `packages/*` folder, each with `name`, `path`, `stack` and its five commands (see `greenfield.md`). Then in `.sdlc/config.json`:

```json
"project": {"kind": "greenfield", "profile": "large",
            "owners": {"/apps/web/": ["@org/web"], "/apps/api/": ["@org/backend"],
                       "/packages/api-contract/": ["@org/backend"]}},
"api_contract": {"path": "packages/api-contract", "spec": "openapi.yaml"}
```

- `owners` only for `large`, in CODEOWNERS order (the last matching line wins).
- `api_contract` only when the contract check was accepted.
- `large`: no root `commands.test`; it would count as a full run of every package and defeat per-app CI. `lean` may keep the workspace's root test command.

Check as in `greenfield.md`: `$S contract` ok, `$S run-commands` all exit 0.

## `ci`

| Profile | Render (all `--class seeded`) |
|---|---|
| `lean` | `$S render builtin:ci .github/workflows/sdlc-verify.yml` |
| `large` | per package: `$S render builtin:ci:<name> .github/workflows/sdlc-verify-<name>.yml` (runs on that package's path, `packages/**`, root files such as lockfiles and workspace manifests, and its own file); `$S render builtin:codeowners .github/CODEOWNERS` |
| `api_contract` set | `$S render templates/project/ci/contract-check.sh .sdlc/ci/contract-check.sh` and `$S render builtin:contract-check .github/workflows/sdlc-contract.yml` |

`sdlc contract` runs on every pull request: tell the user to make it a required status check, or breaking changes are flagged but not blocked. `large`: tell the user not to mark the per-app workflows as required: a pull request that doesn't touch an app never runs its workflow, so a required check would wait forever.

Then continue with the common steps in `SKILL.md`. In the report, name the profile and anything left out: no contract check (and why), no `infras/`.
