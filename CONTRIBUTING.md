# Contributing

How the plugin is laid out, how to run and test it from a checkout, and how to ship a change. Day-to-day operations (health check, fixing hooks) are in the [runbook](docs/runbook.md); why things are built the way they are is in the [ADRs](docs/adr/README.md); what the plugin must do is in the [PRD](docs/prd.md) and the per-capability [specs](docs/specs/README.md), each requirement tied to the test that proves it.

## Layout

```
sdlc/
├── .claude-plugin/
│   ├── plugin.json          name, version (repos record it at setup and upgrade)
│   └── marketplace.json     marketplace entry for /plugin install
├── agents/                  subagents: verifier, reviewers, code-explorer/architect, simplifier, …
├── commands/                slash commands (/sdlc:start, setup, upgrade, eject, doctor, status, review-pr, …)
├── skills/                  skills; orchestrator/ is the conductor, setting-up-projects/ runs setup/upgrade/eject
├── hooks/
│   ├── hooks.json           which script runs on which event
│   ├── verify_freshness.py  Stage 5 stale/fresh test tracking (original)
│   ├── pretooluse.py, stop.py, userpromptsubmit.py   hookify entry points (vendored)
│   ├── posttooluse.py       hookify, kept for parity with upstream but not registered
│   ├── stop-hook.sh         ralph-loop (vendored)
│   └── security_reminder_hook.py + modules, sg-python.sh   security-guidance (vendored)
├── core/                    hookify rule loader and engine (vendored, patched; see NOTICE.md)
├── matchers/, utils/        empty hookify packages (vendored)
├── scripts/
│   ├── scaffold.py          setup/upgrade/eject bookkeeping: lock, file classes, commands, CI generator
│   ├── doctor.py            read-only health check
│   ├── diff_stats.py        Stage 6 review facts, Public Surface check
│   └── setup-ralph-loop.sh  (vendored)
├── templates/
│   ├── spec/design/checklist/constitution-template.md   used by the Stage 1–2 skills
│   ├── knowledge/           OKF templates for tier 2/3 knowledge
│   └── project/             what setup places in a repo: config defaults, rules/, hookify/, lint/, baseline.md
├── examples/hookify/        sample rules
├── tests/                   stdlib unittest suite (helpers.py + one file per hook or script)
├── docs/
│   ├── guidebook.md, playbook.md, runbook.md
│   ├── prd.md               product requirements
│   ├── specs/               one spec per capability, requirements tagged [enforced]/[instructed]/[vendored]
│   ├── adr/                 architecture decision records
│   └── diagrams/
├── licenses/                third-party license texts
├── CHANGELOG.md  NOTICE.md  LICENSE  README.md
```

Original to this plugin: the orchestrator and setting-up-projects skills, `managing-knowledge`, the `verifier` agent, `verify_freshness.py`, everything in `scripts/` except the ralph script, `templates/project/`, `templates/knowledge/`, `tests/`, `docs/`. Everything else is vendored; `NOTICE.md` says what came from where and what was changed.

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
| A stage, gate or track | `skills/orchestrator/SKILL.md`, then the files in the [runbook table](docs/runbook.md#add-or-change-a-stage-rule) |
| Anything a set-up repo receives (`templates/project/`, generated CI, config defaults) | `tests/test_project_templates.py`; a migration if projects own the affected file (see Releasing) |
| A decision about how the plugin works | a new ADR in `docs/adr/` (never rewrite an accepted one) |
| User-visible behavior | `README.md`, the relevant doc, the capability's spec in `docs/specs/`, and `CHANGELOG.md` under Unreleased |
| Vendored code | re-copy from upstream, re-apply the renames (`superpowers:` → `sdlc:`, paths → `.sdlc/`) and the patches listed in `NOTICE.md`, run the tests |

Keep it lean: the plugin's own code-style rule applies here too (why-only comments, the smallest change that works, no abstraction without a second use).

## Releasing

Follow [Release a new version](docs/runbook.md#release-a-new-version) in the runbook: tests and validate, bump `version`, add a migration if projects need one, move the changelog notes under the version, commit, pass the [smoke test](docs/runbook.md#smoke-test-before-a-release) in real sessions, then `claude plugin tag . --push`.
