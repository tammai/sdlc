# Upgrade

Brings a project's scaffold from its `scaffold_version` to the installed plugin's version. Generic material (templates, stage rules, agent prompts) already updated with the plugin; this only patches what lives in the project.

```bash
$S status          # drift must be "behind"
$S upgrade-plan    # add / regenerate / replace / review / restore / template_gone + pending_migrations
```

Summarize the plan for the user in a few lines (counts per bucket, each migration's summary). If a feature is mid-stage (a feature state file, `.sdlc/state/*.md` or the old `.sdlc/*/state.md`, with `Status: active` past Stage 3), recommend finishing it first; continue only if the user confirms. `--dry-run` requested → stop after the summary.

Clean working tree, then branch `sdlc/upgrade-<from>-<to>`. One commit per bucket.

0. **Add** (policy rules and guardrails new in this plugin version): `$S render <template> <path> --class <class>` for each; list them in the report. One with `exists: true` means a file the plugin never wrote is in the way: show the user both and ask, never overwrite. If the user doesn't want a new one, `$S forget <path>` declines it for good.
1. **Regenerate** (generated files): `$S render <template> <path>` for each. No questions.
2. **Replace** (seeded, unedited, template changed): `$S render <template> <path> --class seeded --if-unchanged` for each. No questions; list them in the report.
3. **Review** (seeded, edited by the user): for each, show the user's file next to `$S preview <template>` and propose a merge that keeps their edits and brings in the new template's changes. The user picks:
   - **apply merge** → write it, then `$S record seeded <path> --template <template>`. For a guardrail (`.claude/hookify/sdlc-*.md`) you can't write it: the `sdlc-protect-guardrails-*` rules block Claude from editing the rules that constrain it, on purpose. Show the merged text and ask the user to apply it, then record it.
   - **skip this time** → leave it; it comes back next upgrade
   - **keep mine** → `$S forget <path>`: the plugin stops managing it for good, and future upgrades won't re-add it
4. **Restore** (seeded, deleted by the user): offer once; yes → `$S render … --class seeded`, no → `$S forget <path>`.
5. **Template gone** (the plugin no longer ships it): ask whether to delete the file; either way `$S forget <path>`.
6. **Keyed merges:** re-run the `allowlist` and `gitignore` steps (and `enable-plugin` if the user approved it at setup) from `SKILL.md`; they only add what's missing.
7. **Commands:** `$S contract`. A newly required command missing → propose it in `.sdlc/config.json` (diff, approved). Commands changed since setup → the CI workflow shows up under *replace* or *review* above (it's generated from them), and a changed command's old run no longer counts (`contract` drops it from `runs`). If `runs` lacks any command (changed, or the repo was set up before runs were recorded), run `$S run-commands` and report any under `not_runnable` to the user.
8. **Migrations**, in the order listed: read `${CLAUDE_PLUGIN_ROOT}/<path>` for each, apply its steps as diffs the user approves, then `$S migration <id> --applied`. Declined → `$S migration <id> --skipped "<reason>"`; it's never asked again unless the user runs upgrade with `--revisit` (`$S migrations --revisit` lists them).
9. **Version:** `$S set-version <plugin version> --min-plugin <highest min_plugin_version among applied migrations, if any>`.
10. Final commit, then **ask**: open a PR or merge locally.

Report: from → to, files per bucket, migrations applied/skipped (with reasons), anything left for review next time.
