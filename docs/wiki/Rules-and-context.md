# Rules and context

## 12. Turn a correction into a rule

If you've corrected the same thing twice **and** a pattern in a command, file edit, prompt or stop can catch it, write a hookify rule instead of more prose.

1. `/sdlc:hookify` with a description, or with no arguments to scan the session for candidates (with `sdlc-extras` installed, its `conversation-analyzer` agent does the scan).
2. Rules live in `.claude/hookify/<name>.md` (committed, team) or `.claude/hookify.<name>.local.md` (personal, git-ignored).
3. A rule has an `event` (`bash`, `file`, `stop`, `prompt`, `all`), an `action` (`warn` or `block`) and conditions. Syntax: the `sdlc:hookify` skill's `references/rule-syntax.md`.
4. With `sdlc-extras` installed, `/sdlc-extras:hookify-list` shows what's active and `/sdlc-extras:hookify-configure` turns rules on or off. Without it, edit `enabled:` in the rule file.

Start with `warn`. Move to `block` once the pattern has no false positives.

## 13. Keep always-loaded context small

- `CLAUDE.md` over about 60 lines: `/sdlc:knowledge-audit` proposes moves (file → tier, with a reason) and shows the line count before and after. Nothing is applied without your OK.
- After a feature, `/sdlc:revise-claude-md` collects lessons from the session and files each in the right tier.
- Every call also carries every enabled plugin's skills, agents and commands. `/sdlc:context-diet` estimates the cost per source and, after your OK, turns off what this project doesn't use (this project only), including the standalone copies of plugins sdlc bundles. Personal skills can only be moved into the projects that use them; synced claude.ai plugins are managed in claude.ai. Check `/context` in a new session for the real numbers.
- Rule of thumb: tier 1 (`CLAUDE.md`) only what nearly every task needs; area guidance in tier 2 (`.claude/rules/` with `paths:`); everything else in tier 3, linked from `knowledge/index.md`.
