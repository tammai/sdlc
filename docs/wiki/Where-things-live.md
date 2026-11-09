# Where things live

```
.sdlc/
  config.json              the project's commands (per package in a monorepo) and overrides on the plugin's defaults (yours)
  scaffold.lock.json       what the plugin placed, versions, migrations (machine-only)
  baseline.md              known failures from before setup (yours)
  state/<feature>.md       the agent's record: track, phase, the plan (tasks, Public Surface), gate log, deviations, open questions, and the path of the feature's change file
  state/<feature>/         the feature's work folder:
    backlog.md  plan-B<n>.md                          work split into parts (/sdlc:prune may delete the plans once merged)
    qa-report.md                                      when a QA round ran
    release.md                                        /sdlc:deploy
  state/<feature>.json, <feature>.events.jsonl   control contract for a runner or control app (git-ignored)
  lint/                    sdlc lint snippets your ESLint/Ruff config imports (seeded)
  ci/invariants.py         checks test reports, the baseline and active features' change files in CI (seeded)
  ci/contract-check.sh     the API contract check CI runs (multi-app repos that chose it; seeded)
  .work/                   scratch, git-ignored (verify record, freshness, dispatch log, trust anchor, QA runs)
docs/sdlc/                 docs_dir: the documents people read (default; setup asks when the repo publishes docs/)
  prd.md                   the product doc: problem, audience, goals, capabilities (yours)
  constitution.md          project principles (yours)
  design-system.md         the design system UI work follows (UI projects; yours)
  recurring-defects.md     defects Review found and Build fixed, one line each: Learn adds, Define and reviewers read
  changes/<feature>.md     the change file, the record for people: Define writes it, Review adds ## Review; kept
knowledge/                 tier 3, on-demand docs (index.md links everything)
.claude/rules/<area>.md    tier 2, loads when matching paths are touched (yours)
.claude/rules/sdlc*.md     plugin policy rules: workflow, code style, tests, migrations, sensitive areas, CI, UI (generated)
.claude/hookify/*.md       team hookify rules; sdlc-*.md are the plugin's guardrails (seeded)
.github/workflows/sdlc-verify.yml       CI generated from the commands in config (seeded)
.github/workflows/sdlc-invariants.yml   runs .sdlc/ci/invariants.py on pull requests and pushes (seeded)
CLAUDE.md                  tier 1, at most 60 lines (never touched by the plugin)
```

Each feature is named `<yyyy-mm-dd>-<s|m|l>-<slug>`, or `<yyyy-mm-dd>-<s|m|l>-<ticket>-<slug>` with a ticket (e.g. `2026-10-22-m-PROJ-123-month-filter`). The letter is the track it started on; a later size-up doesn't rename it. The branch uses the same name. Commit the state file, the change file `docs/sdlc/changes/<feature>.md` and the working files in `.sdlc/state/<feature>/` (`release.md` only if you want it).

## `state.md`

Resume depends on this file. The orchestrator looks for `.sdlc/state/*.md` with `Status: active`: one match resumes, several asks which, none starts a new feature.

```markdown
# <feature>
Status: active
Process: 3
Change: <change>   (this feature's record for people)
Track: S | M | L   (sized up because: <named signal, or "—">; footprint: <n> files)
Risk: low | high   (<signal: auth, payments, secrets, PII, migration, public API>)
Top model: opus   (fable only if you chose it)
Commands: test: `<test command>`   (monorepo: one per package; no setup: the detected command)
Started: <date>
Base: <commit the feature started from>
Owner: <git email of whoever advances it>
Tool: <claude-code | codex | cursor | antigravity>
Verified: <commit> tree <worktree tree at the last passing verify>
Slice: B<n>   Slice base: <commit>   Slice gates: none   (work split into parts only)
Slice criteria: <criterion IDs>   (spec-backed: what the slice owes, from state.py new --criteria)
Current: Stage 1 – Define   (then Stage 2 – Build, Stage 3 – Review, Stage 4 – Ship)

## Stages            (1 Define, 2 Build, 3 Review, 4 Ship)
## How the build runs   (Define: inline, parts in fresh sessions or parallel subagents, and why)
## Handoff             (what the builder needs and wouldn't find in the code)
## Tasks               (numbered, each naming its files and ACs)
## Public Surface      (what the change adds that others can see, or - none)
## UI mapping          (UI work only)
## Gate log
## Deviations          (state.py deviation: "What: … Why: … Effect: …")
## Criteria            (spec-backed: each cited criterion's lock hash, state.py cite)
## Test lock           (spec-backed: each test file's sha256 at its red run, verify.py red)
## Spec questions      (spec-backed: open questions on cited criteria, state.py question)
## Open questions
```

It is the agent's record of the change, beside the change file for people. The orchestrator writes this file once from the template and fills its plan sections once in Define, then never edits it by hand: `scripts/state.py` makes each change in one call and writes the control contract beside it ([spec 12](../specs/12-control-contract.md)). Before advancing someone else's feature (`Owner:`), it asks and records the handover.

## Three-tier knowledge

| Tier | Where | Loads |
|---|---|---|
| 1 | `CLAUDE.md` (≤ 60 lines) | every session |
| 2 | `.claude/rules/<area>.md` with `paths:` | automatically, when matching files are touched |
| 3 | `knowledge/**.md` | on demand, via `knowledge/index.md` and links from tier 2 |

Learn, before the final commit, files a lesson in the right tier only when the feature found one that isn't obvious from the code or the commit, and links it from the Lessons filed line of the change file's `## Review`, so it ships in the same PR. A decision later features must follow (a library, a data shape, a boundary) becomes a record in `knowledge/decisions/`, which Define treats as a constraint. Something corrected twice and checkable by machine becomes a hookify rule instead of more text.

## By path


| What | Path |
|---|---|
| Project config (overrides on plugin defaults) | `.sdlc/config.json` |
| What the plugin placed, scaffold version, migrations | `.sdlc/scaffold.lock.json` (never edit by hand) |
| Known failures from before setup | `.sdlc/baseline.md` |
| Feature state (committed; written by `scripts/state.py`) | `.sdlc/state/<feature>.md` |
| Control contract, derived from the state file (git-ignored) | `.sdlc/state/<feature>.json`, `<feature>.events.jsonl`, `<feature>.commands/` |
| Feature change file, the record for people (committed) | `docs/sdlc/changes/<feature>.md`; `docs/sdlc` is `docs_dir` in the config |
| Feature working files (committed) | `.sdlc/state/<feature>/`: `backlog.md` and `plan-B<n>.md` for work split into parts, `qa-report.md` from a QA round, `release.md` from `/sdlc:deploy`, committed only if you ask |
| Scratch (git-ignored) | `.sdlc/.work/`: `verify.json` (written by `scripts/verify.py`), `verify-freshness.json` (the freshness hook's copy of verify runs, written by the hook and by `verify.py` itself), `trust-anchor.json`, `dispatches.jsonl`, `findings/<feature>/` (each review's report, ending in its `VERDICT:` line) |
| Ralph loop state (`sdlc-extras`) | `.claude/ralph-loop.local.md` |
| Personal hookify rules | `.claude/hookify.<name>.local.md` (git-ignored) |
| Team hookify rules | `.claude/hookify/<name>.md` (committed) |
| Security hook per-session state, reviewer venv | `$SECURITY_WARNINGS_STATE_DIR`, else `$CLAUDE_CONFIG_DIR/security/`, else `~/.claude/security/` (venv: `agent-sdk-venv` inside it) |
