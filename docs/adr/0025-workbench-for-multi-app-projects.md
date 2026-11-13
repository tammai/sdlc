# ADR 0025: New multi-app projects are one repo per app inside a workbench repo

- **Status:** Accepted, 2026-11-13. Supersedes [ADR 0005](0005-greenfield-monorepo-layout.md) for new projects;
  existing monorepos keep ADR 0005's layout and its support. Record: `.sdlc/2026-11-13-l-workbench/change.md`.
- **Deciders:** Tâm Mai.

## Context

ADR 0005 put every app of a new product in one monorepo. Apps and the teams owning them stay coupled there: one
history, one access list, one CI, every team's release pace tied to one `main`. Teams that want each app in its own
repo still need what the monorepo gave them: one place every session starts, one record per feature, and a contract
that breaks CI when a change would break a consumer.

## Decision

- **A workbench repo is the parent folder.** `<project>-workbench` is a git repo holding `workbench.json` (the map of
  repos), the API contract (`contract/v<N>/openapi.yaml`), shared docs, the rules and knowledge, and every sdlc feature
  record; never product code. Each app is its own repo cloned inside it and gitignored there. Sessions start in the
  workbench.
- **Detected by config, never by a file name:** `"workbench": true` in its `.sdlc/config.json` plus `workbench.json`.
  product-rebuild's `repos.yaml` is never read, so neither plugin misreads the other's workbench.
- **Each app repo has a small sdlc setup of its own** (its commands, lock, CI, guardrails, and a `"workbench"`
  back-reference) and never holds features: `state.py new` refuses there. Commands live once, in the app.
- **Repos other teams own are read-only:** listed with `write: false`, any write into them is denied, naming the owner.
- **One feature drives a branch and a PR per touched repo.** `state.py repo` branches a repo from its default branch
  the first time Build touches it (recorded under `## Repos`); verify, freshness and drift run per repo; `ship.py`
  stages each repo and lists them in merge order: workbench (contract), provider, consumers. `ship.py --status` warns
  on an out-of-order merge and never blocks.
- **Contract safety survives the split:** the workbench's CI runs the oasdiff check on `contract/`; a consuming
  app's CI checks out the workbench at the branch named like its PR's branch, else `main`, so it builds against the
  same feature's unmerged contract change.
- **Repos come and go after setup:** `scaffold.py workbench add|remove`, and `workbench clone` brings back listed repos a fresh clone lacks; doctor
  reports drift.

### Alternatives considered

| Option | Why not |
|---|---|
| Keep ADR 0005's monorepo for every new project | couples apps and teams; kept for existing monorepos and on request |
| Workbench as a sibling folder (product-rebuild's layout) | sessions would start outside every repo, without the committed rules and knowledge |
| App repos as git submodules of the workbench | every app commit becomes a workbench commit too |
| A linked feature record per app repo | two records of one feature that can disagree |
| One subagent lane per repo | heavy for a solo developer or small team; can come later on top of this |
| `workbench.yaml` | the plugin is stdlib-only Python with no YAML parser; a hand-rolled subset would be a parser over untrusted input |
| App CI pinned to a workbench tag | tags and pin bumps to manage; same-named branches give a PR the matching contract change |

## Consequences

- **Good:** each app has its own history, access, CI and release pace; one record per feature; a breaking contract
  change still fails CI; a fresh clone of the workbench can bring back every repo it lists.
- **Costs:** a private workbench needs a `WORKBENCH_TOKEN` secret in each consuming app repo (setup explains it, never
  creates it); merge order across repos is advised, not enforced; the verified tree covers each branched repo, so a
  verify run takes as long as every touched repo's commands.
- **Not covered:** converting an existing monorepo, writing to other teams' repos, nesting repos more than one level
  below the workbench, parallel per-repo lanes.
