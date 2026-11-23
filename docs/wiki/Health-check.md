# Health check

Run `/sdlc:doctor` when something feels off, after installing or upgrading, or before onboarding a teammate. It **changes nothing**. It prints one row per check (✅ / ⚠️ / ❌) and, for each problem, the fix and the [Troubleshooting](Troubleshooting.md) procedure that covers it.

From a shell: `python3 <plugin>/scripts/doctor.py --format md` (exits 1 if anything fails). Without `--format md` it prints JSON: each check has a stable `code` (such as `repo.commands`), and the problems are listed again under `problems`, each with its `fix`.

| Group | Checks |
|---|---|
| **environment** | Python ≥ 3.9, a Python 3 that `hooks/sg-python.sh` finds, git, gh, jq, the security reviewer's environment |
| **plugin** | Version; every script that `hooks.json` references exists |
| **repo: setup** | Setup state and version drift; the mode (full with any skipped steps, or advisory, where missing commands and guardrails are expected); config and lock parse; plugin files missing, hand-edited, or reached through a link outside the project; old layout; `.sdlc/.work/` and contract files git-ignored; the `AGENTS.md` block |
| **repo: commands** | Commands defined (per package), their tools on PATH, whether they've run; baseline present (brownfield). Spec-backed repo: `accept.start` and `accept.base_url` |
| **repo: content** | Design system present if there are UI files; impeccable installed if in that mode; rules whose `paths:` match nothing; hookify rules that don't parse or have a bad regex; CLAUDE.md over 60 lines; broken links in `knowledge/index.md` |
| **repo: state** | State files missing `Status:`/`Current:`, or several active; corrupt freshness state, or a failed freshness-hook run |

Not covered: whether the plugin is enabled (check `/plugin`).
