# Contributing

How the plugin is laid out, how to run and test it from a checkout, and how to ship a change. Day-to-day operations (health check, fixing hooks) are in the [runbook](docs/runbook.md); why things are built the way they are is in the [ADRs](docs/adr/README.md); what the plugin must do is in the [PRD](docs/prd.md) and the per-capability [specs](docs/specs/README.md), each requirement tied to the test that proves it.

## Layout

```
sdlc/
├── .claude-plugin/
│   ├── plugin.json          name, version (repos record it at setup and upgrade)
│   └── marketplace.json     marketplace entry for /plugin install
├── .codex-plugin/, .agents/plugins/, .cursor-plugin/, plugin.json, hooks.json, hosts/
│                            Codex, Cursor and Antigravity manifests, Cursor agents, hosts/skills (the commands as skills)
│                            and hosts/<host>/hooks.json, root hooks.json (Antigravity's): built by scripts/hosts.py, never edited;
│                            `hosts.py dist antigravity` builds Antigravity's install copy. hosts/hook.py (hand-written) runs
│                            the hooks under Codex, Cursor and Antigravity
├── agents/                  subagents: verifier, reviewers, code-explorer/architect, simplifier, …
├── commands/                slash commands (/sdlc:start, setup, upgrade, eject, doctor, status, prune, deploy, context-diet, review-pr, …)
├── skills/                  skills; orchestrator/ is the conductor (a short core plus references/ read per phase), setting-up-projects/ runs setup/upgrade/eject
├── hooks/
│   ├── hooks.json           which script runs on which event
│   ├── verify_freshness.py  Prove (Stage 5; old Lite features: 5–6) stale/fresh test tracking (original)
│   ├── model_router.py      checks each subagent dispatch's model, logs dispatches (original)
│   ├── role_guard.py        keeps the plugin's agents to their role's file access (original)
│   ├── prove_budget.py      kills non-project shell commands at 120 s in Prove, no background runs (original)
│   ├── trust_anchor.py      shows the user changes to what verification trusts (original)
│   ├── pretooluse.py, stop.py, userpromptsubmit.py   hookify entry points (vendored)
│   ├── stop-hook.sh         ralph-loop (vendored)
│   ├── security_reminder_hook.py + modules, sg-python.sh   security-guidance (vendored; patched to ask sdlc_review_gate.py)
│   └── sdlc_review_gate.py  one commit security review per review-ready diff while a feature is active (original)
├── core/                    hookify rule loader and engine (vendored, patched; see NOTICE.md)
├── matchers/, utils/        empty hookify packages (vendored)
├── knowledge/, .claude/rules/   this repo's own knowledge, same 3-tier spec as projects (sdlc:managing-knowledge)
├── scripts/
│   ├── scaffold.py          setup/upgrade/eject bookkeeping: lock, file classes, commands, CI generator
│   ├── doctor.py            read-only health check
│   ├── diff_stats.py        review facts for Prove, Public Surface check
│   ├── hosts.py             builds the other agents' manifests from .claude-plugin/ and agents/ (CI checks them)
│   ├── backlog.py           the next ready slice of a feature's backlog.md
│   ├── state.py             every state change in one call: state.md plus the control contract (beside it, git-ignored)
│   ├── autopilot.py         runs a backlog one fresh headless claude session per slice (opt-in)
│   ├── context_diet.py      per-source estimate of what Claude Code lists every call (/sdlc:context-diet)
│   └── setup-ralph-loop.sh  (vendored)
├── templates/
│   ├── spec/design/checklist/constitution-template.md   used by the Define skills
│   ├── backlog-template.md  a feature's backlog of slices (orchestrator)
│   ├── design-system-template.md   setup's design-system step (UI projects)
│   ├── knowledge/           OKF templates for tier 2/3 knowledge
│   └── project/             what setup places in a repo: config defaults, rules/, hookify/, lint/, agents/ (the AGENTS.md workflow section), baseline.md
├── migrations/              <version>-<slug>.md steps that /sdlc:upgrade applies to project-owned files
├── examples/hookify/        sample rules
├── tests/                   stdlib unittest suite (helpers.py + one file per hook or script)
├── .github/workflows/ci.yml the suite on Linux and Windows, plus `claude plugin validate`, on push and PR
├── docs/
│   ├── guidebook.md, playbook.md, runbook.md
│   ├── prd.md               product requirements
│   ├── specs/               one spec per capability, requirements tagged [enforced]/[instructed]/[vendored]
│   ├── adr/                 architecture decision records
│   └── diagrams/
├── licenses/                third-party license texts
├── CHANGELOG.md  NOTICE.md  LICENSE  README.md
```

Original to this plugin: the orchestrator and setting-up-projects skills, `managing-knowledge`, `trimming-context`, the `verifier`, `qa-tester` and `ui-reviewer` agents, `verify_freshness.py`, `sdlc_review_gate.py`, `model_router.py`, `role_guard.py`, `prove_budget.py`, `trust_anchor.py`, `commands/deploy.md`, everything in `scripts/` except the ralph script, `templates/project/`, `templates/knowledge/`, `templates/design-system-template.md`, `templates/backlog-template.md`, `migrations/`, `tests/`, `docs/`. Everything else is vendored; `NOTICE.md` says what came from where and what was changed.

## Dev loop

```bash
claude plugin validate .                          # manifest and components parse
claude --plugin-dir .                             # load this checkout for one session
python3 -m unittest discover -s tests -t tests    # full suite, stdlib only
python3 scripts/doctor.py --format md             # health check against the current repo
```

- Tests must pass on Python 3.9 (macOS's system `python3`) as well as current versions: no `match`, no `X | Y` type unions, stdlib only.
- Each test runs a hook or script as a subprocess against a throwaway project directory, the way Claude Code runs them. Add a test with every behavior change; a bug fix starts with a failing test.
- `claude plugin test` doesn't apply: it only runs TypeScript hook modules.

## Making changes

| Change | Also update |
|---|---|
| A phase, gate or track | `skills/orchestrator/SKILL.md`, then the files in the [runbook table](docs/runbook.md#add-or-change-a-phase-rule) |
| Anything a set-up repo receives (`templates/project/`, generated CI, config defaults) | `tests/test_project_templates.py`; a migration if projects own the affected file (see Releasing) |
| A decision about how the plugin works | a new ADR in `docs/adr/` (never rewrite an accepted one) |
| User-visible behavior | `README.md`, the relevant doc, the capability's spec in `docs/specs/`, and `CHANGELOG.md` under Unreleased |
| Vendored code | re-copy from upstream, re-apply the renames (`superpowers:` → `sdlc:`, paths → `.sdlc/`) and the patches listed in `NOTICE.md`, run the tests |

### Stale-docs audit

After adding or changing a plugin feature (a hook, command, skill, agent, script, state.md field or rule), and before calling it done:

1. List the names the change adds or renames (file names, hook names, fields, commands, phrases it replaces).
2. Grep each across `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `knowledge/`, `.claude/rules/`, `docs/` (guidebook, playbook, runbook, prd, specs, ADRs) and the `<desc>` and labels of `docs/diagrams/*.svg`. Also grep the old wording the change replaces.
3. Check the lists that enumerate the plugin: README "Always on", the guidebook Hooks table and `state.md` block, the CONTRIBUTING layout tree and "Original to this plugin", the runbook procedures and "Add or change a phase rule" table, the prd capability table, and the spec's Source line, requirements and Known gaps.
4. Fix what's stale, or name what you left (e.g. an SVG that needs relayout) in your report.

Keep it lean: the plugin's own code-style rule applies here too (why-only comments, the smallest change that works, no abstraction without a second use).

## Releasing

Follow [Release a new version](docs/runbook.md#release-a-new-version) in the runbook: tests and validate, bump `version`, add a migration if projects need one, move the changelog notes under the version, distill the cycle's lessons with `sdlc:managing-knowledge` (`CLAUDE.md`, `.claude/rules/`, `knowledge/`), commit, pass the [smoke test](docs/runbook.md#smoke-test-before-a-release) in real sessions, then `claude plugin tag . --push` and publish the GitHub release with `gh release create`.
