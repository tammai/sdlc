# Workbench: one repo per app under a parent workbench repo

## Why

**Request (verbatim):** "i want to replace momorepo structure wiht another approach" → chose Polyrepo, then:

> i think separate repos will decouple better. the approach i want is:
> - one app per repo
> - add a repo called <project-name>-workbench
> - workbench is the parent folder of project, gitignore apps repo, main session start on workbench, workbench has the structure, know which repos inside it folder is for what parts, include specs, tests, designs repos from other team

New multi-app projects (web, api, mobile, …) get one repo per app instead of ADR 0005's single monorepo, so that apps
and the teams owning them are decoupled: each repo has its own history, access, CI and release pace. A
`<project>-workbench` repo is the parent folder and the place every session starts: it describes the product (specs,
contract, designs, test cases, the map of repos) and holds the sdlc feature records, but no product code. Prompted by
a review of the monorepo support (this session) and the wish to decouple apps.

**The user's words:**

- Approach: polyrepo, with the workbench as the parent folder (above).
- A feature that touches several apps: "one feature in the workbench driving PRs in each repo".
- Repos owned by other teams (specs, tests, designs): "read only, other teams change their own repos".
- Existing monorepos: "keep monorepo support, only new projects get workbench".
- How sdlc handles it: "A, sdlc understands the workbench directly".
- App repos get a small sdlc setup of their own (commands, CI, guardrails, no feature records): "yes".
- product-rebuild's `repos.yaml`: "keep apart" (separate file name and detection; no product-rebuild change here).
- Adding an app or a read-only repo after setup: "in scope".
- Added during Build (B1), as part B8: "i want to include the prefer stack template: nuxt stack: nuxt spa, nuxt-ui,
  pinia, pinia-colada, zod · react stack: react vite, shadcn/ui, the rest equivalent to nuxt · nodejs backend: hono,
  postgresql, drizzle, zod, deploy to gcp cloud run + cloud sql or cloudflare worker + neon · go backend: you decide".
  Go: "Gin + sqlc" (Gin, oapi-codegen, pgx/v5 + sqlc, golang-migrate, PostgreSQL; Cloud Run + Cloud SQL).

### Goals

- Greenfield setup with two or more apps creates a workbench repo plus one repo per app, cloned inside it.
- One sdlc feature, recorded once in the workbench, branches, verifies and opens a PR in each repo it touches.
- A fresh clone of the workbench can bring back every repo it lists.
- Contract safety survives the split: a breaking change to a published contract version still fails CI, and an app's
  PR is checked against the contract change of the same feature before it merges.
- A repo can be added to (or removed from) a workbench after setup.

### Non-goals

- Converting an existing monorepo (ADR 0005 layout, e.g. `tohe`) into a workbench. Monorepo support stays.
- Writing to repos other teams own.
- Running repos in parallel lanes (product-rebuild's G5); can come later on top of this.
- Changing product-rebuild, or sharing its `repos.yaml`.

### Anti-goals (failure even if it works)

- An edit, commit or command lands in the wrong repo (workbench vs app, or one app vs another) without the agent
  or the user seeing it.
- Two records of one feature that can disagree, or the same commands kept in two places.
- A single-repo project (one app, or an existing monorepo) behaves differently than today, except the root-test
  change below.
- sdlc's workbench and a product-rebuild workbench trip each other's guards.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| Workbench is a git repo and the parent folder; app repos are cloned inside it and gitignored | Workbench as a sibling (product-rebuild today); one monorepo (ADR 0005); app repos as submodules | The user's choice. A session starting in the workbench loads its committed CLAUDE.md, settings, rules and knowledge. Submodules would make every app commit a workbench commit too. |
| One feature lives in the workbench and drives a branch and PR per touched repo | A linked feature per app repo (B); one subagent lane per repo (C) | The user's choice (A). One record; reuses the per-package scope machinery; lanes can come later. |
| Each app repo has a small sdlc setup: `.sdlc/config.json` with its commands, its lock, CI, guardrail hooks; never feature records | sdlc only in the workbench | The user's choice. A session or teammate in `api/` alone keeps guardrails; upgrade patches each repo's own files against its own lock; the nested-repo routing in `hooks/sdlc_layout.py` already keys on a repo's `.sdlc/config.json`. Commands live once, in the app. |
| Repos other teams own are read-only to sdlc | Opening PRs in them | The user's choice. |
| Existing monorepos keep support; only new greenfield multi-app setups get a workbench | An upgrade that converts a monorepo | The user's choice. ADR 0005 is superseded for new projects only. |
| sdlc's manifest is `workbench.json`; a workbench is detected by `"workbench": true` in its `.sdlc/config.json`, never by a file name | Sharing product-rebuild's `repos.yaml` | The user's choice (keep apart). product-rebuild's guards switch on for any repo listed in a `repos.yaml`; a shared name would make each plugin misread the other's workbench. |
| Adding or removing a repo after setup is a setup step (`$S workbench add <url>` / `remove <name>`) | Manifest written once at setup | The user's choice (in scope). |
| The API contract lives in the workbench, versioned by folder (`contract/v1/openapi.yaml`); the workbench's CI runs the oasdiff check | A contract repo; the contract in the api repo; a registry | [recommended] The contract describes the product; folder versioning is ADR 0005's proven rule. |
| An app's CI checks out the workbench branch with its own branch's name when one exists, else `main` | Pinning a workbench tag per app; the workbench as an app submodule | [my call] With one branch name per feature across repos, a web PR sees the same feature's unmerged contract change; additions-only keeps `main` safe for everyone else; no tags or pin bumps to manage. |
| Merge order: workbench (contract) PR, then the provider app (api), then consumers; ship warns on out-of-order merges, doesn't block | No ordering; blocking | [my call] Consumers' clients need the contract on `main` once their own branch is gone; blocking needs cross-repo branch protection sdlc doesn't own. |
| CI's read access to a private workbench: setup explains the token or deploy key to create; it doesn't create it | Setup creating secrets | [my call] Creating credentials on the user's GitHub is outward-facing. |
| A feature records the commit of each read-only repo it read (`specs@a1b2c3`) | Reading whatever is checked out | [recommended] Other teams move those repos at any time; Review can show what changed. |
| Greenfield setup proposes from preferred stacks (`references/stacks.md`): Nuxt SPA + Nuxt UI + Pinia + Pinia Colada + Zod; React + Vite + shadcn/ui + Zustand + TanStack Query + React Router + Zod; Node: Hono + PostgreSQL + Drizzle + Zod on Cloud Run + Cloud SQL or Cloudflare Workers + Neon; Go: Gin + oapi-codegen + pgx/v5 + sqlc + golang-migrate on Cloud Run + Cloud SQL. The user still approves each proposal; a database or deploy target is proposed only when the first feature needs it | "The ecosystem's mainstream choice" with no preference | The user's stacks; the Go and React pieces beyond what they named are [my call] (React: the counterparts of Pinia, Pinia Colada and Nuxt's router; Go: the user picked "Gin + sqlc"). |
| One `scopes()` implementation, shared by scripts and hooks; a root `commands.test` beside `packages` runs as a root step in the verify plan and CI, and still counts as covering every package for freshness | Two parsers; ignoring the root test | [my call] Workbench scopes extend this machinery and the two parsers already disagree (review finding). For existing monorepos with a root test, this only adds a run; `tohe` has none. |

### Approaches considered

- **A. sdlc understands the workbench directly (chosen).** The manifest lists repos; each writable repo is a scope with
  its own git root. Hooks, verify, freshness and ship resolve which repo a path or command belongs to and act there.
  One record. Largest change to the core.
- **B. Workbench plans, each app repo runs its own sdlc features.** Little core change, but two records per repo that
  can drift, and one feature becomes several. Ruled out by "one feature in the workbench".
- **C. One subagent lane per repo (product-rebuild G5).** Parallel and an existing pattern, but heavy for a solo
  developer or small team, needs B's per-repo setup underneath, and work happens out of sight until a lane reports.

### Design

**Layout.**

```
<project>-workbench/          git repo; every session starts here
  workbench.json              the map (below)
  .gitignore                  one line per cloned repo folder
  .sdlc/                      config ("workbench": true), lock, feature records
  CLAUDE.md, .claude/         rules, settings, knowledge, as in any sdlc repo
  contract/v1/openapi.yaml    when one app serves an API another consumes
  docs/                       workbench-owned specs, designs, test cases (optional)
  api/  web/  mobile/         app repos: own .sdlc/config.json, CI, hooks; writable (gitignored)
  specs/  qa/  designs/       other teams' repos, read-only (gitignored)
```

**`workbench.json`.** One entry per repo: `name` (also its folder; one level deep only), `url`, `role` (`app`,
`specs`, `tests`, `designs`, `other`), `owner` (team handle), `write` (true only for app repos this project owns), and
for apps `contract` (`provides: v1` or `consumes: v1`). No commands: an app's commands live in its own
`.sdlc/config.json`. Doctor reports listed repos that are missing (and offers to clone them), unlisted nested repos,
folders not gitignored, and a writable repo without `.sdlc/config.json`.

**App repo setup.** Each app repo is set up as a small sdlc repo: `.sdlc/config.json` with `project.stack` and its
five `commands` and a `"workbench": "<project>-workbench"` back-reference, its lock, `builtin:ci`, invariants and the
guardrail hooks. It never holds features: the orchestrator refuses to start one there and points to the workbench.

**Scopes.** In a workbench, `scopes()` returns one scope per writable repo (its folder, git root, default branch and
the commands from its own config) plus the workbench itself (docs, contract, config). A path belongs to the repo whose
folder contains it, else to the workbench. `hooks/sdlc_layout.py:target_repo` routes to the nested repo when the
session root is a workbench, instead of returning None because the root has a `.sdlc/`. An Edit/Write into a
read-only repo is blocked, naming its owner.

**A feature across repos.** The change and state files live in the workbench. The state file's plan names, per task,
the repo it touches. When Build first touches a repo, sdlc creates the feature branch there (same name in every repo,
from that repo's default branch) and records the repo and base commit in the state file. Verify, freshness and the
review diff run per touched repo, with that repo's commands, in its folder. Ship opens one PR per touched repo (the
workbench's included when the feature changed it); each PR links the others and the change file. The feature is
shipped when every PR is merged; the state file lists each PR and its state.

**Contract.** `contract/v<N>/openapi.yaml` in the workbench; additions only once published; a breaking change is a
new folder. The workbench's CI runs the oasdiff check (`builtin:contract-check`). A consuming app's `generate:api`
reads `../contract/v<N>` locally; its CI checks out the workbench at the branch with its own branch's name if it
exists, else `main`, and generates from there. Ship orders the merges workbench → provider → consumers and warns when
one lands out of order.

**Read-only repos.** A feature records each read-only repo's commit on first read (state file). If one has moved by
Review, the review brief says what changed.

**Setup (greenfield, two or more apps).** Make the session's folder the workbench repo; interview as `monorepo.md`
does (stacks, owners, contract, `infras/`); create each app repo with its ecosystem's generator in its folder, give
it a remote, run the small sdlc setup in it; write `workbench.json`; gitignore the folders; add other teams' repos by
URL; tell the user what token app CI needs to read the workbench. `profile` shrinks to which `docs/` folders and
owners to set up; CODEOWNERS is per repo and optional. One app: unchanged (single repo). Brownfield and existing
monorepos: unchanged.

**Add / remove later.** `$S workbench add <url> [--role app|specs|tests|designs|other] [--write]` clones into the
workbench, gitignores, writes the manifest entry, and for an app runs the small sdlc setup and the contract
generation step. `$S workbench remove <name>` drops the entry and the gitignore line and leaves the folder for the
user to delete. Both run on a branch of the workbench, like any setup change.

**Docs.** New ADR superseding 0005 for new projects (0005 stays for existing monorepos); `references/workbench.md`
in the greenfield path (`monorepo.md` kept for existing monorepos); wiki pages Project-setup, Configuration,
Where-things-live; the stale-docs audit in CONTRIBUTING.md.

### Calls I made (the user hasn't confirmed)

- Same branch name in every repo; each branch starts from its repo's default branch.
- App CI follows the workbench's same-named branch, else `main` (no tags or pins).
- Merge order workbench → provider → consumers; out-of-order merges warn, never block.
- Setup explains the CI read token; it doesn't create it.
- The workbench is itself a scope, so a docs- or contract-only feature works the same way.
- Root `commands.test` beside `packages` runs in the verify plan and CI and still clears freshness for every package.
- One level of nesting; folder name = manifest name.
- `remove` never deletes the folder.

### Left to the builder

- Exactly which hooks need repo resolution (start from `hooks/sdlc_layout.py`, `hooks/reporesolve.py` (already
  finds nested repos for commit review), `gitutil.py`, `verify_freshness.py`, `prove_budget.py`, `pretooluse.py`,
  `role_guard.py`, `scripts/ship.py`, `prune.py`, `diff_stats.py`, and the orchestrator's git and worktree
  references).
- Whether a workbench feature uses worktrees per repo or works on branches in place.
- `workbench.json` schema details beyond the fields above.

**Proposals not asked for:** None.

## Acceptance criteria

B1 · one scope parser
- **AC-001** Given a `.sdlc/config.json` with `packages` (named, unnamed, trailing-slash and `./` paths), when the
  freshness hook and `scaffold.py` read its scopes, then both return the same names and paths from one shared function.
- **AC-002** Given `packages` and a root `commands.test`, when the verify plan and `builtin:ci` are built, then the
  root test is a step run from the repo root (scope `(root)`), and a full run of it still marks every package fresh.
- **AC-003** Given the brownfield setup reference, when it says where packages are recorded, then it names the
  top-level `packages` key, not `project`.

B2 · the workbench manifest
- **AC-004** Given `"workbench": true` in `.sdlc/config.json` and a `workbench.json`, when scopes are read, then
  there is one scope per `write: true` repo (its folder, its own config's commands) plus the workbench itself; a
  folder with only product-rebuild's `repos.yaml`, or no `workbench` key, is not a workbench; a malformed manifest
  (not a mapping, `null` fields, wrong types) gives `not run: workbench.json …`, never a traceback.
- **AC-005** Given a workbench, when `scaffold.py workbench add <url> --role app --write` runs, then the repo is
  cloned into `<name>/`, `<name>/` is gitignored and the entry written; `workbench remove <name>` drops the entry and
  the gitignore line and leaves the folder; a name that isn't a plain folder name (`@org/web`, `a/b`, `..`, `a\b`,
  `.git`, `.sdlc`, `.claude`, `C:x`) is refused with a message and nothing written.
- **AC-006** Given a workbench, when doctor runs, then it reports each listed repo that's missing, each nested git
  repo not listed, each listed folder not gitignored, and each writable repo without `.sdlc/config.json`.

B3 · routing and guards
- **AC-007** Given a session started in a workbench (which has its own `.sdlc/`), when a guarded call targets a file
  or command in an app repo, then the guards act for that app repo; a session in a repo that isn't a workbench is
  unchanged.
- **AC-008** Given a `write: false` repo, when an Edit, Write or a shell write targets a path inside it, then the
  call is denied with a message naming the repo and its owner.
- **AC-009** Given an app repo whose config names its workbench, when `state.py new` runs there, then it refuses
  with a message pointing to the workbench and writes nothing.

B4 · one feature, several repos
- **AC-010** Given a workbench feature, when Build first touches an app repo, then `state.py` creates the feature's
  branch there from that repo's default branch and records repo, branch and base commit; a repo with uncommitted
  changes is refused, naming it. `verify.py` then runs each touched repo's verify plan in its folder, and a failure
  names the repo.
- **AC-011** Given a workbench feature in Review, when a file in `api/` changes, then only the `api` scope goes
  stale, and a full test run in `api/` makes only `api` fresh.
- **AC-012** Given a feature that recorded `specs@<commit>`, when the read-only repo has moved (or the commit is gone
  after a force-push), then `diff_stats.py` for the feature lists the repo, the recorded and current commits and the
  files changed (or says the recorded commit no longer exists).

B5 · ship across repos
- **AC-013** Given a workbench feature touching the workbench, `api` (provides v1) and `web` (consumes v1), when
  `ship.py` runs, then it commits in each touched repo on the feature branch naming the change file, and lists the
  repos in merge order workbench → provider → consumers, with each PR body linking the others.
- **AC-014** Given the feature's PRs recorded in the state file, when a consumer's PR is merged before its
  provider's, then `ship.py --status` warns naming both and never blocks; the feature is done only when every PR is
  merged.

B6 · contract and CI
- **AC-015** Given an app repo that consumes a contract, when `builtin:ci` renders, then it checks out the workbench
  at the branch with the PR's branch name when that exists, else `main`, before the install step; the workbench's
  `builtin:contract-check` uses `api_contract.path` (`contract`) unchanged.

B7 · setup and docs
- **AC-016** Given greenfield setup with two or more apps, when the setup skill routes it, then it follows
  `references/workbench.md` (not `monorepo.md`); ADR 0025 supersedes ADR 0005 for new projects, and the wiki's
  Project-setup, Configuration and Where-things-live pages describe the workbench.

B8 · preferred stacks
- **AC-017** Given greenfield setup (one app, or each app of a workbench), when it proposes a stack, then it starts
  from `references/stacks.md`, which names for each stack its pieces (Nuxt: SPA mode, Nuxt UI, Pinia, Pinia Colada,
  Zod; React: Vite, shadcn/ui, Zustand, TanStack Query, React Router, Zod; Node: Hono, PostgreSQL, Drizzle, Zod,
  Cloud Run + Cloud SQL or Cloudflare Workers + Neon; Go: Gin, oapi-codegen, pgx/v5, sqlc, golang-migrate, Cloud
  Run + Cloud SQL), its generator, and its five commands.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_workbench.py › test_one_scope_parser_for_scripts_and_hooks | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_one_scope_parser_for_scripts_and_hooks` |
| AC-002 | tests/test_workbench.py › test_root_test_beside_packages_runs_and_covers_every_package | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_root_test_beside_packages_runs_and_covers_every_package` |
| AC-003 | tests/test_workbench.py › test_brownfield_reference_records_top_level_packages | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_brownfield_reference_records_top_level_packages` |
| AC-004 | tests/test_workbench.py › test_workbench_scopes_and_detection | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_workbench_scopes_and_detection` |
| AC-005 | tests/test_workbench.py › test_workbench_add_and_remove | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_workbench_add_and_remove` |
| AC-006 | tests/test_workbench.py › test_doctor_reports_workbench_drift | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_doctor_reports_workbench_drift` |
| AC-007 | tests/test_workbench.py › test_guards_route_into_an_app_repo_from_a_workbench | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_guards_route_into_an_app_repo_from_a_workbench` |
| AC-008 | tests/test_workbench.py › test_writes_into_a_read_only_repo_are_denied | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_writes_into_a_read_only_repo_are_denied` |
| AC-009 | tests/test_workbench.py › test_no_feature_starts_in_an_app_repo | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_no_feature_starts_in_an_app_repo` |
| AC-010 | tests/test_workbench.py › test_build_branches_and_verifies_each_touched_repo | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_build_branches_and_verifies_each_touched_repo` |
| AC-011 | tests/test_workbench.py › test_freshness_is_per_app_repo | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_freshness_is_per_app_repo` |
| AC-012 | tests/test_workbench.py › test_moved_read_only_repo_is_reported | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_moved_read_only_repo_is_reported` |
| AC-013 | tests/test_workbench.py › test_ship_commits_each_repo_in_merge_order | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_ship_commits_each_repo_in_merge_order` |
| AC-014 | tests/test_workbench.py › test_out_of_order_merge_warns | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_out_of_order_merge_warns` |
| AC-015 | tests/test_workbench.py › test_app_ci_checks_out_the_workbench | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_app_ci_checks_out_the_workbench` |
| AC-016 | tests/test_workbench.py › test_setup_and_docs_describe_the_workbench | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_setup_and_docs_describe_the_workbench` |
| AC-017 | tests/test_workbench.py › test_greenfield_proposes_the_preferred_stacks | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_greenfield_proposes_the_preferred_stacks` |

## Must never break

- A single-repo project or an existing monorepo behaves as today (scopes, verify plan, hooks, ship), apart from a
  root `commands.test` beside `packages` now also running in the verify plan and CI.
- A command or edit is never run or recorded against a repo other than the one it targets.
- sdlc never writes to a repo marked read-only.
- A product-rebuild workbench is never detected as an sdlc workbench, and vice versa.
- A manifest value never becomes a path outside the workbench, or into `.git/`, `.claude/` or `.sdlc/`.

## Failure modes

- A listed repo missing locally → AC-006 (doctor), AC-005 (`add` re-clones).
- A repo dirty when Build first touches it → AC-010.
- One PR merged and another rejected or still open → AC-014 (the feature stays open; the state lists each PR).
- A read-only repo force-pushed under a recorded commit → AC-012.
- The session's cwd moved into an app folder → AC-007.
- A feature started from inside an app repo → AC-009.
- Untrusted manifest values (a committed `workbench.json` names folders and clone URLs) → AC-005 (plain-name
  allowlist, kept inside the workbench, away from `.git/`, `.claude/`, `.sdlc/`), AC-004 (malformed values), and the
  must-never-break line above. Clone URLs reach `git clone` only as an argument after `--`, never through a shell.
- Windows paths in the manifest (`a\b`, `C:x`) → AC-005.

## Out of scope

- Converting an existing monorepo to a workbench.
- Writing to repos other teams own.
- Parallel per-repo lanes.
- Changing product-rebuild or sharing its `repos.yaml`.
- Nesting repos more than one level below the workbench.
