# Install

In Claude Code:

```
/plugin marketplace add tammai/sdlc
/plugin install sdlc@sdlc
```

Restart the session so the commands and hooks load. `/plugin` lists installed plugins and whether sdlc is enabled.

Optional companions from the same marketplace (`/sdlc:setup` offers them):

- `sdlc-extras@sdlc`: the Ralph loop, hookify commands and extra review agents.
- `sdlc-stepper@sdlc`: a bar above the prompt showing which phase the active feature is in ([README](../../plugins/sdlc-stepper/README.md)).

Using sdlc in Claude Code on the web or a routine? Cloud sessions don't install plugins from a repo's settings: see [Cloud sessions](Cloud-sessions.md).

## Requirements

Your project needs nothing extra. Your machine needs:

| Need | For |
|---|---|
| `git` | worktrees, freshness hook, commit and PR commands |
| `gh` | `/sdlc:code-review` and PR commands |
| Python 3.9+ | all hooks (started through `hooks/sg-python.sh`, which finds `python3`, `python` or `py -3`) and `scripts/` (stdlib only; macOS system 3.9 works) |
| `jq` | the Ralph loop's stop hook (the optional `sdlc-extras` plugin) |
| Node | brainstorming visual companion |
| `typescript-language-server`, `typescript` | TypeScript code intelligence (`npm i -g typescript-language-server typescript`) |

## Other coding agents (experimental)

| Agent | Install |
|---|---|
| Codex | `codex plugin marketplace add tammai/sdlc`, then `codex plugin add sdlc@sdlc` |
| Cursor | Customize → Import from Repo with `https://github.com/tammai/sdlc` |
| Antigravity | `python3 scripts/hosts.py dist antigravity <folder>` in a clone, then `agy plugin install <folder>` |

What works there and what doesn't: [Limitations](Limitations.md).

## Check the install

In a scratch repo:

1. `/sdlc:doctor`: no ❌. Expected warnings: the repo isn't set up yet, and (before the first session finishes) the reviewer environment.
2. `/sdlc:setup` with a one-line description: it proposes a stack, and after your OK writes `.sdlc/config.json` and the rest on a `sdlc/setup` branch. `/sdlc:doctor` again: the repo checks are ✅.
3. `/sdlc:start` with a tiny request creates `.sdlc/state/<feature>.md` and announces the track, risk and top model tier.

Something wrong: [Health check](Health-check.md), then [Troubleshooting](Troubleshooting.md).

## Update and uninstall

- **Update:** update the marketplace and the plugin from `/plugin`, restart, then run `/sdlc:upgrade` in each repo ([Setup and upgrade](Setup-and-upgrade.md#16-upgrade-after-a-plugin-update)).
- **Uninstall:** run `/sdlc:eject` in each repo ([Setup and upgrade](Setup-and-upgrade.md#17-remove-sdlc-from-a-repo)), then `/plugin uninstall sdlc`.

Working on the plugin itself: see [CONTRIBUTING](../../CONTRIBUTING.md).
