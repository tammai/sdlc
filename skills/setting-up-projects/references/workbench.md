`${CLAUDE_PLUGIN_ROOT}` is the sdlc plugin's folder. Claude Code fills it in; on other agents it stays as written, so use the installed plugin's folder instead: the one above this file that holds `scripts/` and `skills/`.

# Greenfield workbench

A new project with two or more apps (web, api, mobile, …) gets one repo per app, cloned inside a `<project>-workbench`
repo. This replaces the `stack`, `skeleton`, `commands` and `ci` steps of `greenfield.md`; the step names stay, so
resume still works. One app: this file doesn't apply, follow `greenfield.md`. An existing monorepo, or a user who asks
for one repo: `monorepo.md`. Decision: `${CLAUDE_PLUGIN_ROOT}/docs/adr/0025-workbench-for-multi-app-projects.md`
(it supersedes ADR 0005 for new projects).

The session's folder becomes the workbench: every session starts there. It describes the product and holds the sdlc
feature records, never product code.

```
<project>-workbench/          git repo; every session starts here
  workbench.json              the map of repos (below)
  .gitignore                  one line per cloned repo folder (/api/)
  .sdlc/                      config ("workbench": true), lock, feature records
  CLAUDE.md, .claude/         rules, settings, knowledge, as in any sdlc repo
  contract/v1/openapi.yaml    when one app serves an API another consumes
  docs/                       workbench-owned specs, designs, test cases (optional)
  api/  web/  mobile/         app repos: own .sdlc/config.json, CI, hooks; writable
  specs/  qa/  designs/       other teams' repos, read-only
```

## `stack` – interview, then propose (hard stop)

Ask what you can't infer, a few at a time, each with a suggested answer:

- The apps and the stack of each, proposed from `stacks.md` (package manager, test runner, generator, five commands).
- The team handle that owns each app (`@org/web`, `@org/backend`), when there is more than one person. Backend owns
  the contract.
- With an API and a client: the contract format (default OpenAPI) and whether the workbench's CI should block breaking
  changes to published versions (oasdiff).
- Repos other teams own that this project reads (specs, test cases, designs): their clone URLs and owners. sdlc
  never writes to them.
- Where each app repo's remote lives. Creating a remote (`gh repo create`) is outward-facing: name each one in the
  proposal, and create it only on the user's yes; otherwise the user creates it and gives the URL.
- **Add `infras/`** in the workbench for deploy playbooks? No → nothing is created.

Propose in one message: the tree, the generator and five commands per app, the remotes, the read-only repos. **The
user approves before anything is generated.**

## `skeleton`

1. The workbench: `$S init --kind greenfield` as usual, then set `"workbench": true` in `.sdlc/config.json`, and,
   with the contract check, `"api_contract": {"path": "contract", "spec": "openapi.yaml"}`. Write
   `contract/v1/openapi.yaml` (a minimal valid spec: info, one health path) and
   `$S render templates/project/monorepo/api-contract-README.md contract/README.md --class seeded`.
2. Each app, in its own folder inside the workbench: run its official generator there (as in `greenfield.md`), then
   `git init -b main`, the test runner and one smoke test. A consuming app gets a `generate:api` script (or the
   stack's equivalent) that generates its client from `../contract/v<N>/openapi.yaml`, its output gitignored in the app.
3. Each app's small sdlc setup, run with `--root <app>` from the workbench: `$S --root <app> init --kind greenfield`,
   its `commands` (as in `greenfield.md`), `"workbench": "<project>-workbench"` (or `"<owner>/<project>-workbench"`
   when the workbench lives under another account) and `project.stack` in its `.sdlc/config.json`, then its `ci`
   step below, invariants and the `guardrails` step. Never feature records: `state.py new` refuses in an app repo and
   points to the workbench.
4. Record each repo in the manifest, which also gitignores its folder:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py" workbench add <url> --name api --role app --write --owner @org/backend --contract provides:v1
   $S workbench add <url> --name web --role app --write --owner @org/web --contract consumes:v1
   $S workbench add <url> --role specs --owner @org/ba        # another team's repo: cloned, read-only
   ```

   An app folder that is already a git repo is recorded as it is; a missing one is cloned (`git clone -- <url>`).
   Names are plain folder names one level down (never `.git`, `.sdlc`, `.claude`, a path or a drive).
5. Each app's first commit, then push to its remote (the user's yes covers the remotes named in the proposal).

`workbench.json` holds per repo: `name` (its folder), `url`, `role` (`app`, `specs`, `tests`, `designs`, `other`),
`owner`, `write` (true only for app repos this project owns) and for an app `contract` (`provides`/`consumes`:
`v<N>`). No commands: an app's commands live once, in its own `.sdlc/config.json`.

## `commands`

The workbench itself usually has none (`"commands": {}`, or a docs lint). Each app's are checked in the app:
`$S --root <app> contract` → `ok: true`, then `$S --root <app> run-commands`, every command exiting 0.

## `ci`

| Where | Render (all `--class seeded`) |
|---|---|
| each app | `$S --root <app> render builtin:ci .github/workflows/sdlc-verify.yml`. An app that consumes the contract gets steps that check out the workbench first: its branch named like the PR's branch when it exists, else `main`, its `contract/` copied to `../contract` |
| workbench | `$S render templates/project/ci/invariants.py .sdlc/ci/invariants.py`, `$S render builtin:invariants .github/workflows/sdlc-invariants.yml` |
| workbench, `api_contract` set | `$S render templates/project/ci/contract-check.sh .sdlc/ci/contract-check.sh` and `$S render builtin:contract-check .github/workflows/sdlc-contract.yml` (the oasdiff check on `contract/`) |

A private workbench: tell the user that app CI needs a `WORKBENCH_TOKEN` secret in each consuming app repo, a token
or deploy key that can read the workbench; setup explains it and never creates it. Tell them to make `sdlc contract`
a required check in the workbench.

## Working in a workbench (for the report)

- Sessions start in the workbench. Guards follow each call into the app repo it acts in; any write into a read-only
  repo is denied, naming its owner.
- One feature, recorded once in the workbench, drives a branch and PR per repo it touches. The first time Build
  touches a repo: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/state.py" repo <feature> <name>` (a writable repo gets the
  feature's branch from its default branch, refused while dirty; a read-only one records the commit read).
  `verify.py` runs each touched repo's own commands in its folder.
- Ship: `ship.py <feature>` stages each repo and lists them in merge order (workbench, provider, consumers) with a PR
  body each; commit, push and open each PR, then `state.py pr <feature> <repo> <url>`.
  `ship.py <feature> --status` reports each PR and warns when one merged out of order; the feature is done when every
  PR is merged.
- Later: `$S workbench add <url> …` adds a repo (on a workbench branch, like any setup change); `$S workbench remove
  <name>` drops its entry and gitignore line and leaves the folder. `/sdlc:doctor` reports listed repos not cloned,
  unlisted nested repos, folders not gitignored and apps without their own config.

Then continue with the common steps in `SKILL.md` in the workbench. In the report, name each repo, its remote and
role, and anything left out: no contract check (and why), no `infras/`, the `WORKBENCH_TOKEN` to create.
