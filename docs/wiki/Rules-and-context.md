# Rules and context

## 12. Turn a correction into a rule

**When:** you've corrected the same thing twice, **and** a pattern in a command, file edit, prompt or stop can catch it. Write a hookify rule instead of more prose.

1. Run `/sdlc:hookify <description>`, or run it with no arguments to scan the session for candidates (with `sdlc-extras`, its `conversation-analyzer` agent does the scan).
2. Rules live in `.claude/hookify/<name>.md` (team, committed) or `.claude/hookify.<name>.local.md` (personal, git-ignored).
3. A rule has an `event` (`bash`, `file`, `stop`, `prompt`, `all`), an `action` (`warn` or `block`) and conditions. For syntax, see the `sdlc:hookify` skill's `references/rule-syntax.md`.
4. To manage rules: with `sdlc-extras`, `/sdlc-extras:hookify-list` and `/sdlc-extras:hookify-configure`. Without it, edit `enabled:` in the file.

**Start with `warn`.** Switch to `block` once the pattern has no false positives. Rule not firing? [R7](Troubleshooting.md#r7-a-hookify-rule-doesnt-fire-or-fires-too-much).

## 13. Keep always-loaded context small

Every token in tier 1, and every enabled plugin's skills, agents and commands, is paid on every call. The [three tiers](Where-things-live.md#three-tier-knowledge) keep it small.

| Problem | Command | What it does |
|---|---|---|
| `CLAUDE.md` over ~60 lines | `/sdlc:knowledge-audit` | Proposes moves (file → tier, with a reason) and shows line counts before and after. Nothing applied without your OK |
| Lessons from a finished feature | `/sdlc:revise-claude-md` | Files each lesson in the right tier |
| Too many plugins/skills loaded | `/sdlc:context-diet` | Estimates cost per source and, after your OK, turns off what this project doesn't use (this project only), including standalone copies of plugins sdlc bundles. Personal skills can only be moved into the projects that use them; synced claude.ai plugins are managed in claude.ai |

Check `/context` in a new session for the real numbers.
