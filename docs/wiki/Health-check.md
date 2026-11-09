# Health check

Run `/sdlc:doctor` when something feels off, after installing or upgrading, or before onboarding a teammate. It changes nothing; it prints one row per check with ✅ / ⚠️ / ❌ and, for anything not ok, the fix and the [Troubleshooting](Troubleshooting.md) procedure that covers it. The same report from a shell: `python3 <plugin>/scripts/doctor.py --format md` (exit 1 if anything fails).

| Group | What it checks |
|---|---|
| environment | Python ≥ 3.9, a Python 3 the hooks' launcher (`hooks/sg-python.sh`) finds, git, gh, jq, the security reviewer's environment (built in the state directory on first session) |
| plugin | version; every script `hooks.json` references exists |
| repo | setup state and version drift; config and lock parse; plugin files missing or hand-edited; project commands defined (per package), their tools on PATH, and whether they have run; in a spec-backed repo (its own `criteria.lock.json` or `acceptance/manifest.json`) `accept.start` and `accept.base_url`; the `AGENTS.md` block; baseline present (brownfield); old layout; `.sdlc/.work/` and the contract files git-ignored; design system present when the repo has UI files; impeccable installed when the design mode is impeccable; rules whose `paths:` match no files; hookify rules that don't parse or have a bad regex; CLAUDE.md over 60 lines; broken links in `knowledge/index.md`; state files missing `Status:`/`Current:`, or several active; corrupt freshness state, or a freshness hook run that failed |

Not covered by doctor: whether the plugin is enabled (`/plugin`).
