# Full-pipeline review: enforcement and trust boundaries

- **Date:** 2026-10-22
- **Version audited:** 1.4.0 (`.claude-plugin/plugin.json`)
- **Commit:** `f6054e4` (clean when the review began; branch ahead of `origin/main`). Unrelated
  plugin-enablement edits appeared in the working tree during the audit and are excluded from
  the findings and line references.
- **Scope:** the 11-stage lifecycle from `skills/orchestrator/SKILL.md`, the enforcement hooks in
  `hooks/`, the agents in `agents/`, the setup/health/review scripts in `scripts/`, and the
  capability specs in `docs/specs/`.
- **Method:** static review plus the stdlib test suite run on the reviewer's machine. No live
  Claude Code session, model dispatch, or vendored security-hook execution was exercised.
- **Status:** nothing in the repository was changed by this review. Addressed for 1.5.0: PIPE-03 (review
  input uses `Base:`), PIPE-09's two stale doc claims, PIPE-05's missing router tests, PIPE-02 (`Verified:`
  commit, simplifier before review, Stage 7 and 8 re-verify) and PIPE-04 for the five read-only reviewers.
  The rest is in `docs/backlog.md`.

## Executive summary

The pipeline is well designed and unusually candid about its own limits: the per-capability
specs have "Known gaps" sections, and most orchestration requirements are explicitly tagged
`[instructed]`. The weak parts are structural rather than scattered defects:

> The guarantees are concentrated in four small mechanisms — the model router, the freshness
> hook, hookify, and `diff_stats.py` — and the evidence those mechanisms trust is writable by
> the agent being verified.

Everything else (track sizing, risk classification, stage order, gate criteria, review
independence, the security pass, deployment) is prompt text. The README's "Gates you can
trust" (`README.md:12`) is stronger than the implementation.

## Severity legend

| Level | Meaning |
|---|---|
| **Critical** | A passing gate can be produced without the work the gate claims to prove. |
| **High** | A normal workflow can skip a check or review the wrong diff. |
| **Medium** | A documented guarantee degrades silently, or a realistic environment bypasses it. |
| **Low** | Hygiene, documentation drift, or defense-in-depth weakness. |

---

## Findings

### PIPE-01 — Critical: the trust anchor is agent-writable

`hooks/verify_freshness.py:33` excludes `.sdlc/` from code-change detection. The files that
control enforcement and evidence all live there: `state.md`, `spec.md`, `baseline.md`,
`config.json`, `test-report.md`.

| Agent action | Effect |
|---|---|
| Change `Current: Stage 5` to `Stage 4` in `state.md` | The freshness hook turns off (`verify_freshness.py:109-120`). |
| Change `Status: active` to `paused` | The model router turns off (`model_router.py:22-31`). |
| Add `Top model: fable` | Fable becomes allowed (`model_router.py:41-43`). |
| Lower `Risk: high` to `low` | Cheaper reviewers are allowed on auth, payments, secrets or migration work (`model_router.py:44-46`). |
| Edit the acceptance criteria in `spec.md` | The verifier proves a weaker spec. |
| Add a failing test to `baseline.md` | A failure becomes "known" and stops blocking the round. |

None of these edits mark tests stale, and no gate audits them. The user's approval at a hard
stop is the only counterweight, but the orchestrator writes `state.md` itself, so the bypass
is silent. This is the difference between "the hook enforces X" and "the hook enforces X as
long as the agent leaves its own control file alone".

**Recommendation:** seal each verification round. When the full suite runs, record
`{commit, tree, command, exit, hash(spec.md), hash(baseline.md), hash(config.json)}` under
`.sdlc/.work/`, and have `test-report.md` reference that record. Any later change to a hashed
file invalidates the round. Move `Status`/`Current` enforcement state out of the
model-writable file, or make it append-only and hook-maintained.

### PIPE-02 — High: verification expires at the Stage 5 gate

The Stage 5 gate is "latest round's verifier verdict PASS on the current commit (no code edits
since)" (`skills/orchestrator/SKILL.md:100`). After that gate:

- Stage 6 fixes review findings and runs `code-simplifier` after the review
  (`SKILL.md:107`, `commands/review-pr.md:46`).
- Stage 7 fixes security findings (`SKILL.md:115-119`).
- `Current` moves to Stage 6/7, which switches the freshness hook off.
- Stage 8's `finishing-a-development-branch` reruns only the test suite
  (`skills/finishing-a-development-branch/SKILL.md:14-18`) — not build, lint, typecheck, or
  the acceptance-criteria evidence.

The merged code can therefore differ from the code the verifier proved. A final test run
catches breakage, but not a regressed acceptance criterion, and not a lint or type error
introduced by the simplifier.

**Recommendation:** record the verified commit in `state.md`. If the diff since that commit
is non-empty at Stage 8, reopen Stage 5 for a fast round or record explicit verification
debt. Simpler ordering fix: run `code-simplifier` before the final review, or review its diff.

### PIPE-03 — High: Stage 6 can be blind to committed work

`commands/review-pr.md:33` identifies changed files with `git diff --name-only`, which lists
**unstaged** changes only. On the default L path, `subagent-driven-development` has each
implementer commit its task, so by Stage 6 the working tree is clean. File-type selection then
falls through to `code-reviewer` only — no `pr-test-analyzer`, `silent-failure-hunter`,
`type-design-analyzer`, or UI reviewer.

`scripts/diff_stats.py:42` has a related edge. `default_base()` returns `HEAD` when there is no
upstream divergence, so on `main` with all work committed (or with no `origin/main` ref) it
reports only uncommitted changes. It also ignores the `Base:` commit the orchestrator already
records in `state.md`.

**Recommendation:** use `Base:` (or merge-base) for both review file selection and diff
stats: `git diff --name-only <base>...HEAD` plus the working tree. Fail loudly when Stage 6
sees an empty diff for a feature that is not empty.

### PIPE-04 — High: role boundaries are not enforced by tool scoping

Seven of the twelve agents omit `tools:` and therefore inherit every tool:
`code-reviewer`, `code-simplifier`, `comment-analyzer`, `pr-test-analyzer`,
`silent-failure-hunter`, `type-design-analyzer`, `ui-reviewer`.

The verifier deliberately has `Write` and `Edit` (`agents/verifier.md:4`) so it can write
`test-report.md`. The same tools let it edit source or the baseline. "The reviewer must not
fix" and "the verifier never edits source" are prompt-only rules.

There is also no before/after worktree check tying a verification report to an unchanged tree.

**Recommendation:** add explicit read-only `tools:` to every reviewer. Give the verifier
`Bash` plus the narrowest write surface available for `test-report.md`. Compare the worktree
before and after a round and fail the round if source changed.

### PIPE-05 — Medium-High: the model router checks labels, not roles

`hooks/model_router.py:35` matches `subagent_type.split(":")[-1]` against exactly four names.
A verification or review run under `general-purpose`, a renamed agent, or a Bash-spawned
OpenCode or `claude -p` session is invisible. The router never checks which stage is running:
nothing prevents Stage 5 from being done by a non-verifier on a cheap model, as long as some
model is named.

The high-risk floor is also the least-tested enforcement: `tests/test_model_router.py` has
two tests, one positive and one Fable-negative. The opus floor for high-risk reviewers,
forks, and the no-active-feature path are untested.

**Recommendation:** bind each stage to a required agent type, log every dispatch
`{stage, agent, model, commit}` to `.sdlc/.work/`, and validate the log at the gate. Either
support an external verifier as a first-class path or state plainly that it is unsupported.

### PIPE-06 — Medium-High: freshness is a heuristic proxy that fails silently

The git-tree diff is a good idea — it catches edits made by any tool — but it proves that a
full run happened, not that the run was green:

- Exit code is ignored (`verify_freshness.py:327-338`). A failing full suite marks the scope
  fresh.
- Command matching is textual. `npm run test` vs `npm test`, wrapper scripts, and env-based
  filters can miss; `.only` is only a warning (already documented).
- Only the **first** active Stage 5 feature is tracked (`active_verify_feature`,
  `verify_freshness.py:109-120`). Two concurrent Stage 5 features leave one unguarded.
- `except Exception: pass` (`verify_freshness.py:377-381`) and the 10s hook timeout
  (`hooks/hooks.json`) mean a parse error or slow repository silently disables the block.
  Nothing in the session says enforcement is degraded.
- The suite is red on a stock Windows machine with WSL installed. See the measurement below.

**Recommendation:** surface degraded enforcement through `systemMessage` and a failing
doctor check; track every active Stage 5 feature; record the exit code separately from
freshness; pin the test suite to Git Bash rather than relying on `PATH` order.

### PIPE-07 — Medium: setup records commands but never proves they run

`scripts/scaffold.py:323` (`cmd_contract`) checks that each required command key exists and
that its executable resolves. It never runs the command. A repository can reach
`setup: complete` with a test command that fails immediately, or is effectively `true`; the
first Stage 5 then either fails or passes vacuously.

The remainder of the setup surface — brownfield command recording, baseline classification,
upgrade merge decisions — is instructed. There is one shipped migration
(`migrations/1.4.0-design-system.md`); the migration path is exercised only by tests.

**Recommendation:** run each command once at setup, store the exit status in the lock, and
fail the contract when a command does not run. Add a fixture-repository end-to-end test for
setup → start → upgrade → eject.

### PIPE-08 — Medium: repository-committed hookify rules are a prompt-injection channel

`core/config_loader.py:242-243` loads `.claude/hookify/*.md` from the repository, and
`core/rule_engine.py:43-46,97-131` puts rule messages into `permissionDecisionReason` or
`additionalContext`. A cloned repository can ship a catch-all rule that blocks tools or feeds
arbitrary text into the model.

`sdlc-*` guardrails are protected against agent edits, but non-`sdlc-*` team rules are not
listed or reviewed anywhere. The spec says to review changes under that folder like code; an
agent entering a new repository does not.

**Recommendation:** treat repository rules as untrusted until the user approves them. List
non-`sdlc-*` rules in `/sdlc:status` and in the Stage 0 report, and keep rule text out of the
agent's instruction channel where possible.

### PIPE-09 — Low-Medium: governance is warn-only, and the docs overclaim enforcement

`scripts/doctor.py:248-265` only warns on `CLAUDE.md` over 60 lines, dead rule paths, and
broken knowledge-index links. The Stage 11 gate requires `CLAUDE.md` ≤ 60 lines, but nothing
checks it at the transition. The gate log in `state.md` is self-written, with no user identity
or transcript reference.

Two documentation claims do not match the implementation:

- `README.md:167` calls plan consistency "machine-checked", but `analyzing-consistency` is an
  instructed LLM skill (`docs/specs/03-scope-and-review.md:26`).
- `docs/specs/01-setup-upgrade-eject.md` says setup has not been run end-to-end in a live
  session, while the 1.4.0 changelog and PRD say the smoke test covered setup, upgrade and
  eject. One of the two is stale.

**Recommendation:** add `doctor --strict` for CI and Stage 11, fix the two stale claims, and
consider a `scaffold.py verify-state` command that checks the artifacts each stage requires.

### PIPE-10 — Medium: the plugin's own quality gate is manual

The repository has no `.github/` directory. The 181-test suite, `claude plugin validate`, and
the release smoke test are run by a human. The model router has two tests; the vendored
security-guidance hooks have no tests in this repository (`docs/specs/05-security.md`).

A one-line regression in a hook can therefore ship between releases. This is the same class of
problem the plugin is designed to prevent in other repositories.

**Recommendation:** add GitHub Actions for tests and `claude plugin validate` on push and pull
request, on Linux and Windows. Add tests for every model-router branch and a wiring test for
`hooks/hooks.json`.

---

## Measured test run

Command:

```text
python3 -m unittest discover -s tests -t tests
```

Result on 2026-10-22, Windows, Git Bash shell:

```text
Ran 181 tests in 150.187s
FAILED (failures=7, skipped=1)
```

All seven failures are `test_ralph_stop.py`, with the error:

```text
/bin/bash: C:Users...hooksstop-hook.sh: No such file or directory
```

Cause: `tests/helpers.py:12` uses `shutil.which("bash")`, which resolves to
`C:\WINDOWS\system32\bash.EXE` (WSL) when System32 precedes Git in `PATH`. The documented fix
in `knowledge/gotchas/windows-bash-is-wsl.md` assumes `shutil.which` finds Git Bash; it does
not in this environment. The hooks themselves are unaffected; the harness is.

---

## Stage-by-stage summary

| Stage | Claim | What actually enforces it | Weak link |
|---|---|---|---|
| 0 Setup | Commands and baseline recorded | `scaffold.py` lock and contract | Commands are resolved, never executed |
| 1 Spec | No inferred items, Non-Goals filled | User approval | Spec can be weakened later; no parser |
| 2 Design | Every addition cites a requirement | User approval | Complexity Tracking is unchecked |
| 3 Plan | Traceability, Public Surface declared | `analyzing-consistency` (L, M > 8 tasks) | LLM skill; S track has no plan |
| 4 Implement | TDD, every task done | Hookify and later freshness | No proof a test came first; ralph promise is text |
| 5 Verify | Fresh verifier, PASS on current commit | Verifier and freshness | LLM report; spec and baseline writable; exit code ignored |
| 6 Review | No unresolved high findings | `review-pr` and `diff_stats` | Selection uses the unstaged diff; reviewers can edit; stats are advisory |
| 7 Security | No critical/high, no secrets | Vendored hooks and reviewers | Patterns are bypassable; risk is self-declared; audit is instructed |
| 8 PR/CI | CI green | Tests and CI | Only tests rerun; no re-verification |
| 9 Deploy | Go-ahead, smoke test | User | Nothing mechanical |
| 10 Operate | Signals within threshold | User | Thinnest stage; no integrations |
| 11 Learn | Lessons linked, `CLAUDE.md` ≤ 60 | Doctor warns | Warn-only; retros are never loaded |

---

## What holds up

- **Baseline-aware verification** (only new failures fail a round) is the right model for
  brownfield repositories.
- **A fresh verifier per round**, explicitly barred from verifying inline, is a sound
  independence design.
- **The git-tree freshness check** is stronger than watching Edit/Write hooks: it catches
  formatters, Bash edits, and external tools.
- **Setup's lock, file ownership, and migration hygiene** (hashes, CRLF handling, never
  overwriting user-edited files) is careful work.
- **Tests run hooks as subprocesses** the way Claude Code does, and the per-capability
  "Known gaps" sections are more candid than most projects'.

## Recommended sequence

1. **Seal the verification round** (PIPE-01). Hash the spec, baseline, config and verified
   commit into the report; invalidate the round on any change. This closes the goalpost-moving
   and self-authorization holes together.
2. **Re-verify after post-Stage-5 edits** (PIPE-02). Track the verified commit and block
   Stage 8 when the diff since it is non-empty unless a fresh verifier round covers it.
   Move `code-simplifier` before final review.
3. **Fix the review input and role permissions** (PIPE-03, PIPE-04). Use `Base:`/merge-base for
   review selection, add explicit `tools:` to every agent, and add the missing model-router
   tests.
4. **Add CI** (PIPE-10) on Linux and Windows, then fix the Git Bash resolution so the suite is
   green in the environment where it runs.
5. **Tighten setup and the trust boundary** (PIPE-07, PIPE-08). Execute commands once at
   setup; list and gate non-`sdlc-*` hookify rules.

## Out of scope

- Behavior of the vendored security-guidance hooks (no tests in this repository; upstream
  behavior).
- Live model behavior for gate compliance, subagent independence, and instruction-following.
- External integrations (GitHub MCP, Linear, Sentry, Vercel, Playwright) and deploy paths.
- Performance of hooks on very large repositories.
